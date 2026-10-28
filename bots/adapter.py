"""Exchange adapter template. When the organizers hand you an API, implement THESE methods only;
the strategies in bots/strategies.py call them and never touch the API directly.

Common shapes you'll see:
  * REST:      requests.post(f"{URL}/orders", json={...}, headers={"X-API-Key": KEY})
  * WebSocket: websocket-client / websockets, JSON messages for book + fills
  * Python SDK: `from exchange import Client` — wrap its methods below
"""
import time

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
