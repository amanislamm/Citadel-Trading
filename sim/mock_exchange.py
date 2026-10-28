"""Toy exchange to test bots before the game. Hidden fair value random-walks; noise traders
hit random quotes, informed traders trade toward the true fair. Implements bots.adapter.Adapter."""
import random, itertools

class MockExchange:
    def __init__(self, syms=("X",), start=100.0, vol=0.2, spread=0.5, p_informed=0.2, seed=0):
        random.seed(seed)
        self.true = {s: start for s in syms}; self.vol = vol; self.spread = spread
        self.p_inf = p_informed; self.pos = {s: 0 for s in syms}; self.cash = 0.0
        self.orders = {}; self.ids = itertools.count(1); self.trades = 0

    # --- Adapter interface ---
    def symbols(self): return list(self.true)
    def get_book(self, sym):
        f = self.true[sym] + random.gauss(0, self.vol)       # noisy displayed market
        return round(f - self.spread, 2), random.randint(1, 20), round(f + self.spread, 2), random.randint(1, 20)
    def get_position(self, sym): return self.pos[sym]
    def place(self, sym, side, qty, px):
        oid = next(self.ids); self.orders[oid] = (sym, side, qty, px); return oid
    def cancel(self, oid): self.orders.pop(oid, None)
    def cancel_all(self, sym=None):
        for k in [k for k, v in self.orders.items() if sym is None or v[0] == sym]: self.orders.pop(k)

    # --- simulation ---
    def _fill(self, oid):
        sym, side, qty, px = self.orders.pop(oid)
        s = 1 if side == "buy" else -1
        self.pos[sym] += s * qty; self.cash -= s * qty * px; self.trades += 1

    def tick(self):
        for s in self.true: self.true[s] += random.gauss(0, self.vol)
        for oid, (sym, side, qty, px) in list(self.orders.items()):
            f = self.true[sym]
            if side == "buy" and px >= f + self.spread: self._fill(oid); continue   # marketable
            if side == "sell" and px <= f - self.spread: self._fill(oid); continue
            if random.random() < self.p_inf:               # informed: only hit you if you're wrong
                if (side == "buy" and px > f) or (side == "sell" and px < f): self._fill(oid)
            elif random.random() < 0.3:                    # noise: hit if quote near market
                if abs(px - f) < 3 * self.spread: self._fill(oid)

    def pnl(self):
        return self.cash + sum(self.pos[s] * self.true[s] for s in self.true)

def backtest(make_strategy, steps=2000, **kw):
    ex = MockExchange(**kw); strat = make_strategy(ex)
    for _ in range(steps):
        strat.step(); ex.tick()
    return {"pnl": round(ex.pnl(), 2), "pos": ex.pos, "trades": ex.trades}

if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from bots.strategies import MarketMaker
    for wk in (0.3, 0.5, 1.0, 2.0):
        r = backtest(lambda ex: MarketMaker(ex, "X", std=1.0, width_k=wk, size=1, max_pos=20))
        print(f"width_k={wk}: {r}")
