"""Exchange adapter template. When the organizers hand you an API, implement THESE methods only;
the strategies in bots/strategies.py call them and never touch the API directly.

Common shapes you'll see:
  * REST:      requests.post(f"{URL}/orders", json={...}, headers={"X-API-Key": KEY})
  * WebSocket: websocket-client / websockets, JSON messages for book + fills
  * Python SDK: `from exchange import Client` — wrap its methods below
"""
import json, threading, time

class Adapter:
    def get_book(self, sym):            # -> (best_bid, bid_sz, best_ask, ask_sz)
        raise NotImplementedError
    def get_position(self, sym):        # -> int
        raise NotImplementedError
    def place(self, sym, side, qty, px):  # -> order_id
        raise NotImplementedError
    def cancel(self, order_id):
        raise NotImplementedError
    def cancel_all(self, sym=None):
        raise NotImplementedError
    def symbols(self):
        raise NotImplementedError

class RestAdapter(Adapter):
    """Fill in endpoints once you see the docs."""
    def __init__(self, base_url, api_key, rate_limit_per_s=10):
        import requests  # pip install requests
        self.s = requests.Session(); self.s.headers.update({"X-API-Key": api_key})
        self.url = base_url.rstrip("/"); self.min_dt = 1 / rate_limit_per_s; self._t = 0
    def _throttle(self):
        dt = time.time() - self._t
        if dt < self.min_dt: time.sleep(self.min_dt - dt)
        self._t = time.time()
    def get_book(self, sym):
        self._throttle(); j = self.s.get(f"{self.url}/book/{sym}").json()
        b, a = j["bids"][0], j["asks"][0]                      # <-- adjust to real schema
        return b["price"], b["qty"], a["price"], a["qty"]
    def get_position(self, sym):
        self._throttle(); return self.s.get(f"{self.url}/positions").json().get(sym, 0)
    def place(self, sym, side, qty, px):
        self._throttle()
        return self.s.post(f"{self.url}/orders", json={"symbol": sym, "side": side,
                           "qty": qty, "price": px, "type": "limit"}).json().get("id")
    def cancel(self, oid):
        self._throttle(); self.s.delete(f"{self.url}/orders/{oid}")
    def cancel_all(self, sym=None):
        self._throttle(); self.s.delete(f"{self.url}/orders", params={"symbol": sym} if sym else None)
    def symbols(self):
        return self.s.get(f"{self.url}/symbols").json()


class RiskGuard(Adapter):
    """Wrap ANY adapter: blocks orders that could breach position limits or fat-finger size,
    and rate-limits. ex = RiskGuard(RestAdapter(...), max_pos={"X": 100}, max_qty=20)"""
    def __init__(self, inner, max_pos=None, max_qty=50, default_max_pos=100, max_orders_per_s=20,
                 price_band=None):
        self.inner, self.max_pos, self.max_qty = inner, max_pos or {}, max_qty
        self.default_max_pos, self.min_dt, self._t = default_max_pos, 1 / max_orders_per_s, 0.0
        self.price_band = price_band            # e.g. 0.1 -> reject orders >10% away from mid
        self.open = {}                          # oid -> (sym, side, qty)
        self.blocked = 0
    def get_book(self, sym): return self.inner.get_book(sym)
    def get_position(self, sym): return self.inner.get_position(sym)
    def symbols(self): return self.inner.symbols()
    def place(self, sym, side, qty, px):
        lim = self.max_pos.get(sym, self.default_max_pos)
        pos = self.inner.get_position(sym)
        pend = sum(q if sd == "buy" else -q for s, sd, q in self.open.values() if s == sym)
        worst = pos + pend + (qty if side == "buy" else -qty)
        if qty <= 0 or qty > self.max_qty or abs(worst) > lim:
            self.blocked += 1; print(f"RiskGuard blocked {side} {qty} {sym} @ {px} (pos {pos}, pending {pend})")
            return None
        if self.price_band:
            b, _, a, _ = self.inner.get_book(sym)
            if b is not None and a is not None and abs(px - (b + a) / 2) > self.price_band * (b + a) / 2:
                self.blocked += 1; print(f"RiskGuard blocked off-market px {px} for {sym}"); return None
        dt = time.time() - self._t
        if dt < self.min_dt: time.sleep(self.min_dt - dt)
        self._t = time.time()
        oid = self.inner.place(sym, side, qty, px)
        if oid is not None: self.open[oid] = (sym, side, qty)
        return oid
    def cancel(self, oid):
        self.open.pop(oid, None); return self.inner.cancel(oid)
    def cancel_all(self, sym=None):
        for k in [k for k, v in self.open.items() if sym is None or v[0] == sym]: self.open.pop(k)
        return self.inner.cancel_all(sym)
    def on_fill(self, oid, qty):
        """Call from your fill handler so pending exposure stays accurate."""
        if oid in self.open:
            s, sd, q = self.open[oid]
            if q - qty > 0: self.open[oid] = (s, sd, q - qty)
            else: self.open.pop(oid)

class WsAdapter(Adapter):
    """WebSocket template (pip install websocket-client). A background thread keeps the latest
    book / positions in memory, so get_book() is instant. Adjust _on_message to the real schema."""
    def __init__(self, url, api_key=None):
        import websocket  # pip install websocket-client
        self.books, self.positions, self._ids, self._lock = {}, {}, 0, threading.Lock()
        hdr = [f"X-API-Key: {api_key}"] if api_key else None
        self.ws = websocket.WebSocketApp(url, header=hdr, on_message=lambda w, m: self._on_message(m))
        threading.Thread(target=self.ws.run_forever, daemon=True).start()
        time.sleep(1.0)
    def _send(self, **msg): self.ws.send(json.dumps(msg))
    def _on_message(self, raw):
        m = json.loads(raw)                                     # <-- adjust to real schema
        with self._lock:
            if m.get("type") == "book":
                b, a = m["bids"], m["asks"]
                self.books[m["symbol"]] = (b[0][0] if b else None, b[0][1] if b else 0,
                                           a[0][0] if a else None, a[0][1] if a else 0)
            elif m.get("type") == "fill":
                s = 1 if m["side"] == "buy" else -1
                self.positions[m["symbol"]] = self.positions.get(m["symbol"], 0) + s * m["qty"]
    def get_book(self, sym):
        with self._lock: return self.books.get(sym, (None, 0, None, 0))
    def get_position(self, sym):
        with self._lock: return self.positions.get(sym, 0)
    def place(self, sym, side, qty, px):
        self._ids += 1
        self._send(type="order", id=self._ids, symbol=sym, side=side, qty=qty, price=px); return self._ids
    def cancel(self, oid): self._send(type="cancel", id=oid)
    def cancel_all(self, sym=None): self._send(type="cancel_all", symbol=sym)
    def symbols(self):
        with self._lock: return list(self.books)
