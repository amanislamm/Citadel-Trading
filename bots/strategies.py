"""Strategies that run against any Adapter (real exchange or sim.MockExchange)."""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tt.quoting import quote
from tt.orderbook import microprice
from tt.signals import EMA

class MarketMaker:
    """Quote both sides around blended fair (model + microprice EMA), skewed by inventory.
    Also takes clearly mispriced quotes. Hard position limits."""
    def __init__(self, ex, sym, model_fair=None, std=1.0, max_pos=100, size=5,
                 width_k=0.5, take_k=0.5, blend=0.5, tick=0.01):
        self.ex, self.sym = ex, sym
        self.model_fair, self.std = model_fair, std
        self.max_pos, self.size, self.width_k, self.take_k = max_pos, size, width_k, take_k
        self.blend, self.tick = blend, tick
        self.ema = EMA(0.2); self.live = []

    def fair(self, b, bs, a, as_):
        m = self.ema.update(microprice(b, a, bs, as_))
        return m if self.model_fair is None else self.blend * self.model_fair + (1 - self.blend) * m

    def step(self):
        b, bs, a, as_ = self.ex.get_book(self.sym)
        if b is None or a is None: return
        pos = self.ex.get_position(self.sym)
        f = self.fair(b, bs, a, as_)
        for oid in self.live: self.ex.cancel(oid)        # cancel EVERYTHING we left resting
        self.live = []
        # worst case all our orders fill: keep that inside +/- max_pos
        room_buy, room_sell = self.max_pos - pos, self.max_pos + pos
        # 1) take
        if a < f - self.take_k * self.std and room_buy > 0:
            q = min(self.size, room_buy, as_ or self.size); room_buy -= q
            self.live.append(self.ex.place(self.sym, "buy", q, a))
        if b > f + self.take_k * self.std and room_sell > 0:
            q = min(self.size, room_sell, bs or self.size); room_sell -= q
            self.live.append(self.ex.place(self.sym, "sell", q, b))
        # 2) make
        bid, ask = quote(f, self.std, pos, self.max_pos, self.width_k, tick=self.tick)
        if room_buy > 0:  self.live.append(self.ex.place(self.sym, "buy", min(self.size, room_buy), bid))
        if room_sell > 0: self.live.append(self.ex.place(self.sym, "sell", min(self.size, room_sell), ask))
        self.live = [o for o in self.live if o is not None]

class ETFArb:
    """Trade ETF vs basket when the gap exceeds threshold; hedge legs immediately."""
    def __init__(self, ex, etf, comps, weights, threshold=0.0, size=1, max_pos=50):
        self.ex, self.etf, self.comps, self.w = ex, etf, comps, weights
        self.th, self.size, self.max_pos = threshold, size, max_pos

    def step(self):
        eb, _, ea, _ = self.ex.get_book(self.etf)
        books = [self.ex.get_book(c) for c in self.comps]
        if eb is None or ea is None or any(bk[0] is None or bk[2] is None for bk in books): return
        basket_ask = sum(w * bk[2] for w, bk in zip(self.w, books))
        basket_bid = sum(w * bk[0] for w, bk in zip(self.w, books))
        pos = self.ex.get_position(self.etf)
        if eb - basket_ask > self.th and pos > -self.max_pos:
            self.ex.place(self.etf, "sell", self.size, eb)
            for c, w, bk in zip(self.comps, self.w, books): self.ex.place(c, "buy", self.size * w, bk[2])
        elif basket_bid - ea > self.th and pos < self.max_pos:
            self.ex.place(self.etf, "buy", self.size, ea)
            for c, w, bk in zip(self.comps, self.w, books): self.ex.place(c, "sell", self.size * w, bk[0])

class Flattener:
    """Emergency: cross the spread to get flat (use near the end if settlement is risky)."""
    def __init__(self, ex, syms): self.ex, self.syms = ex, syms
    def step(self):
        for s in self.syms:
            p = self.ex.get_position(s); b, _, a, _ = self.ex.get_book(s)
            if p > 0 and b is not None: self.ex.place(s, "sell", p, b)
            elif p < 0 and a is not None: self.ex.place(s, "buy", -p, a)

def run_loop(strats, dt=0.25, duration=None, ex=None, max_errors=20):
    """Ctrl-C to stop: cancels all resting orders on `ex` on the way out.
    Stops if a strategy raises `max_errors` times in a row (don't spin on a broken API)."""
    t0, errs = time.time(), 0
    try:
        while duration is None or time.time() - t0 < duration:
            for s in strats:
                try: s.step(); errs = 0
                except Exception as e:
                    errs += 1; print("strategy error:", repr(e))
                    if errs >= max_errors: print("too many errors, stopping"); return
            time.sleep(dt)
    except KeyboardInterrupt:
        print("stopped")
    finally:
        if ex is not None:
            try: ex.cancel_all(); print("cancelled all orders")
            except Exception as e: print("cancel_all failed:", e)
