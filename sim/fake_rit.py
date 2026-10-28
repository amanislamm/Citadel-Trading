"""Fake RIT REST server (stdlib) for testing bots/rit.py offline, and for rehearsing:

  python3 sim/fake_rit.py                 serves http://localhost:9999/v1 with key KEY
  RIT_KEY=KEY python3 bots/run_rit.py --check

Implements the endpoints bots/rit.py uses, with a random-walking mid, a 5-level book,
one tender, a news item, and a 429 on every 25th request so retry logic gets exercised."""
import json, random, threading, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

class State:
    def __init__(self, tickers=("CRZY", "TAME"), seed=0):
        self.r = random.Random(seed); self.tick = 1; self.status = "ACTIVE"; self.n = 0
        self.mid = {t: 10.0 for t in tickers}; self.pos = {t: 0 for t in tickers}
        self.orders = {}; self.next_id = 1; self.tenders = {7: {"tender_id": 7, "ticker": tickers[0], "quantity": 1000,
                         "action": "BUY", "price": 9.80, "is_fixed_bid": True, "expires": 60}}
        self.accepted = []; self.lock = threading.Lock(); self.cash = 0.0
        self.news = [{"news_id": 1, "tick": 1, "ticker": tickers[0], "headline": "Case started", "body": ""}]

    def book(self, t, limit=5):
        m = self.mid[t]
        mk = lambda px, q, side: {"price": round(px, 2), "quantity": q, "quantity_filled": 0, "status": "OPEN", "action": side}
        return {"bids": [mk(m - 0.01 * (i + 1), 400 * (i + 1), "BUY") for i in range(limit)],
                "asks": [mk(m + 0.01 * (i + 1), 400 * (i + 1), "SELL") for i in range(limit)]}

def make_handler(state, key):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def _send(self, code, obj):
            b = json.dumps(obj).encode(); self.send_response(code)
            self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b)))
            self.end_headers(); self.wfile.write(b)
        def _route(self, method):
            u = urllib.parse.urlparse(self.path); q = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
            p = u.path[len("/v1"):] if u.path.startswith("/v1") else u.path
            if self.headers.get("X-API-Key") != key: return self._send(401, {"code": "UNAUTHORIZED"})
            with state.lock:
                state.n += 1
                if state.n % 25 == 0: return self._send(429, {"code": "TOO_MANY_REQUESTS", "wait": 0.01})
                s = state
                if p == "/case": return self._send(200, {"name": "FAKE", "tick": s.tick, "period": 1, "status": s.status, "ticks_per_period": 300})
                if p == "/securities":
                    rows = [{"ticker": t, "position": s.pos[t], "bid": round(s.mid[t] - .01, 2), "ask": round(s.mid[t] + .01, 2),
                             "last": s.mid[t]} for t in s.mid if "ticker" not in q or q["ticker"] == t]
                    return self._send(200, rows)
                if p == "/securities/book": return self._send(200, s.book(q["ticker"], int(q.get("limit", 5))))
                if p == "/trader": return self._send(200, {"trader_id": "me", "nlv": round(sum(s.pos[t] * s.mid[t] for t in s.mid) + s.cash, 2)})
                if p == "/limits": return self._send(200, [{"name": "LIMIT-1", "gross": sum(map(abs, s.pos.values())), "gross_limit": 50000}])
                if p == "/news": return self._send(200, [n for n in s.news if n["news_id"] > int(q.get("since", 0))])
                if p == "/orders" and method == "POST":
                    oid = s.next_id; s.next_id += 1
                    o = {"order_id": oid, "ticker": q["ticker"], "type": q["type"], "quantity": int(q["quantity"]),
                         "action": q["action"], "price": float(q["price"]) if "price" in q else None, "status": "OPEN"}
                    t, sg, m = q["ticker"], (1 if q["action"] == "BUY" else -1), s.mid[q["ticker"]]
                    touch = m + 0.01 if sg > 0 else m - 0.01
                    crosses = q["type"] == "MARKET" or (sg > 0 and o["price"] >= touch) or (sg < 0 and o["price"] <= touch)
                    if crosses:                                    # marketable: fill now at the touch
                        s.pos[t] += sg * o["quantity"]; s.cash -= sg * o["quantity"] * touch; o["status"] = "TRANSACTED"
                    else: s.orders[oid] = o
                    return self._send(200, o)
                if p == "/orders": return self._send(200, [o for o in s.orders.values() if o["status"] == q.get("status", "OPEN")])
                if p.startswith("/orders/") and method == "DELETE":
                    s.orders.pop(int(p.rsplit("/", 1)[1]), None); return self._send(200, {"success": True})
                if p == "/commands/cancel":
                    for k in [k for k, o in s.orders.items() if "all" in q or o["ticker"] == q.get("ticker")]: s.orders.pop(k)
                    return self._send(200, {"cancelled_order_ids": []})
                if p == "/tenders": return self._send(200, list(s.tenders.values()))
                if p.startswith("/tenders/"):
                    tid = int(p.rsplit("/", 1)[1]); t = s.tenders.pop(tid, None)
                    if t and method == "POST":
                        s.accepted.append(tid); s.pos[t["ticker"]] += t["quantity"] * (1 if t["action"] == "BUY" else -1)
                    return self._send(200, {"success": t is not None})
            return self._send(404, {"code": "NOT_FOUND", "path": p})
        def do_GET(self): self._route("GET")
        def do_POST(self): self._route("POST")
        def do_DELETE(self): self._route("DELETE")
    return H

def serve(port=9999, key="KEY", state=None, background=False):
    state = state or State()
    srv = ThreadingHTTPServer(("127.0.0.1", port), make_handler(state, key))
    if background:
        threading.Thread(target=srv.serve_forever, daemon=True).start(); return srv, state
    print(f"fake RIT on http://localhost:{port}/v1  key={key}  (Ctrl-C to stop)")
    def walk():
        import time
        while True:
            time.sleep(1)
            with state.lock:
                state.tick += 1
                for t in state.mid: state.mid[t] = round(state.mid[t] + state.r.gauss(0, 0.02), 2)
    threading.Thread(target=walk, daemon=True).start()
    try: srv.serve_forever()
    except KeyboardInterrupt: pass

if __name__ == "__main__":
    serve()
