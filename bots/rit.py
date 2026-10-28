"""Rotman Interactive Trader (RIT) REST adapter — stdlib only (urllib), no pip installs.

RIT is the most common platform for university trading competitions. The client app exposes
a REST API on the laptop it runs on. In the RIT client: open the API panel, copy the key.

  from bots.rit import RIT
  ex = RIT(api_key="ABCD1234")                     # default http://localhost:9999/v1
  ex.case()            -> {'tick': 37, 'period': 1, 'status': 'ACTIVE', ...}
  ex.securities()      -> [{'ticker': 'CRZY', 'position': 0, 'bid': ..., 'ask': ...}, ...]
  ex.get_book('CRZY')  -> (best_bid, bid_sz, best_ask, ask_sz)     # Adapter interface
  ex.place('CRZY', 'buy', 100, 9.95)  /  ex.market('CRZY', 'sell', 500)
  ex.news(), ex.tenders(), ex.accept_tender(id), ex.limits()

Schemas below match the public RIT API docs as remembered. On game day, open
http://localhost:9999/v1/case in a browser (with the key header via the API docs page) and
compare. Every field access goes through _get() helpers so fixes are one-liners.
"""
import json, time, urllib.error, urllib.parse, urllib.request

from .adapter import Adapter

class RITError(Exception):
    pass

class RIT(Adapter):
    def __init__(self, api_key, base_url="http://localhost:9999/v1", max_order_size=None,
                 timeout=2.0, verbose=False):
        self.key, self.url, self.timeout, self.verbose = api_key, base_url.rstrip("/"), timeout, verbose
        self.max_order_size = max_order_size      # RIT caps size per order; set from case rules
        self._sec_cache, self._sec_t = None, 0.0

    # ---------- HTTP ----------
    def _req(self, method, path, params=None, retries=5):
        q = "?" + urllib.parse.urlencode({k: v for k, v in (params or {}).items() if v is not None}) if params else ""
        for attempt in range(retries):
            req = urllib.request.Request(self.url + path + q, method=method, headers={"X-API-Key": self.key})
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    body = r.read().decode() or "null"
                    return json.loads(body)
            except urllib.error.HTTPError as e:
                body = e.read().decode(errors="replace")
                if e.code == 429:                                   # rate limited: wait as told
                    try: wait = float(json.loads(body).get("wait", 0.2))
                    except Exception: wait = float(e.headers.get("Retry-After", 0.2) or 0.2)
                    time.sleep(min(wait, 2.0)); continue
                if e.code == 401: raise RITError("401 unauthorized: wrong API key (copy it from the RIT client)")
                raise RITError(f"{method} {path} -> {e.code}: {body[:200]}")
            except urllib.error.URLError as e:
                if attempt == retries - 1:
                    raise RITError(f"cannot reach RIT at {self.url} ({e.reason}). Is the RIT client open and logged in?")
                time.sleep(0.2)
        raise RITError(f"{method} {path}: still rate limited after {retries} tries")

    def get(self, path, **p): return self._req("GET", path, p)
    def post(self, path, **p): return self._req("POST", path, p)
    def delete(self, path, **p): return self._req("DELETE", path, p)

    # ---------- case / info ----------
    def case(self): return self.get("/case")
    def tick(self): return self.case().get("tick", 0)
    def is_active(self): return self.case().get("status") == "ACTIVE"
    def trader(self): return self.get("/trader")
    def limits(self): return self.get("/limits")
    def news(self, since=None): return self.get("/news", since=since)

    def securities(self, ticker=None, max_age=0.0):
        """Small cache (max_age seconds) so several strategies can share one call per loop."""
        if ticker: return self.get("/securities", ticker=ticker)
        if self._sec_cache is None or time.time() - self._sec_t > max_age:
            self._sec_cache, self._sec_t = self.get("/securities"), time.time()
        return self._sec_cache

    def symbols(self): return [s["ticker"] for s in self.securities()]
    def positions(self): return {s["ticker"]: s.get("position", 0) for s in self.securities()}

    # ---------- Adapter interface ----------
    def book(self, sym, limit=20):
        """Full depth: {'bids': [(px, open_qty), ...] best first, 'asks': [...]}"""
        j = self.get("/securities/book", ticker=sym, limit=limit)
        lvl = lambda side: [(o["price"], o["quantity"] - o.get("quantity_filled", 0)) for o in j.get(side, [])
                            if o.get("status", "OPEN") == "OPEN"]
        return {"bids": lvl("bids"), "asks": lvl("asks")}

    def get_book(self, sym):
        b = self.book(sym, limit=1)
        bb = b["bids"][0] if b["bids"] else (None, 0); ba = b["asks"][0] if b["asks"] else (None, 0)
        return bb[0], bb[1], ba[0], ba[1]

    def get_position(self, sym):
        s = self.securities(ticker=sym)
        s = s[0] if isinstance(s, list) else s
        return s.get("position", 0)

    def place(self, sym, side, qty, px):
        """Limit order(s). Splits into max_order_size chunks; returns last order id."""
        oid = None
        for q in self._chunks(qty):
            r = self.post("/orders", ticker=sym, type="LIMIT", quantity=q, action=side.upper(), price=round(px, 2))
            oid = r.get("order_id") if isinstance(r, dict) else None
            if self.verbose: print("LIMIT", side, q, sym, px, "->", oid)
        return oid

    def market(self, sym, side, qty):
        ids = []
        for q in self._chunks(qty):
            r = self.post("/orders", ticker=sym, type="MARKET", quantity=q, action=side.upper())
            ids.append(r.get("order_id") if isinstance(r, dict) else None)
        return ids

    def _chunks(self, qty):
        qty = int(qty); m = self.max_order_size or qty or 1
        while qty > 0:
            yield min(qty, m); qty -= m

    def orders(self, status="OPEN"): return self.get("/orders", status=status)
    def cancel(self, oid):
        if oid is not None: self.delete(f"/orders/{oid}")
    def cancel_all(self, sym=None):
        self.post("/commands/cancel", **({"ticker": sym} if sym else {"all": 1}))

    # ---------- tenders (liability trading cases) ----------
    def tenders(self): return self.get("/tenders")
    def accept_tender(self, tid, price=None): return self.post(f"/tenders/{tid}", price=price)
    def decline_tender(self, tid): return self.delete(f"/tenders/{tid}")

    # ---------- helpers ----------
    def wait_for_active(self, poll=0.5):
        print("waiting for case to start ...")
        while not self.is_active(): time.sleep(poll)
        print("case ACTIVE")

    def flatten(self, syms=None):
        """Market out of every position (end of period / emergency)."""
        for s, p in self.positions().items():
            if (syms is None or s in syms) and p:
                self.market(s, "sell" if p > 0 else "buy", abs(p))
