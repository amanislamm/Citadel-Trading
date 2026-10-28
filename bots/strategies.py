"""Strategies that run against any Adapter (real exchange or sim.MockExchange)."""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tt.quoting import quote
from tt.orderbook import microprice
from tt.signals import EMA
from tt.options import bs_greeks
import re

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

class Unwinder:
    """Work a big position (e.g. after accepting a tender) down to `target` over `steps` loops
    without dumping it. Each step: if we're behind schedule, cross the spread for one clip;
    otherwise rest a passive order at the touch (earning the spread / rebate).
    Typical use: Unwinder(ex, "CRZY", target=0, steps=60, clip=2000)."""
    def __init__(self, ex, sym, target=0, steps=60, clip=1000, slack=1.0):
        self.ex, self.sym, self.target, self.steps, self.clip, self.slack = ex, sym, target, steps, clip, slack
        self.k = 0; self.start = None; self.live = []
    def done(self): return self.start is not None and self.ex.get_position(self.sym) == self.target
    def step(self):
        pos = self.ex.get_position(self.sym)
        if self.start is None: self.start = pos
        for oid in self.live: self.ex.cancel(oid)
        self.live = []
        rem = pos - self.target
        if rem == 0: return
        self.k += 1
        frac_left = max(0.0, 1 - self.k / self.steps)
        allowed = abs(self.start - self.target) * frac_left        # schedule: linear to 0
        side = "sell" if rem > 0 else "buy"
        b, _, a, _ = self.ex.get_book(self.sym)
        if b is None or a is None: return
        q = min(self.clip, abs(rem))
        if abs(rem) > allowed + self.slack * self.clip or self.k >= self.steps:   # behind: cross
            self.live.append(self.ex.place(self.sym, side, q, b if side == "sell" else a))
        else:                                                                     # on track: passive
            self.live.append(self.ex.place(self.sym, side, q, a if side == "sell" else b))
        self.live = [o for o in self.live if o is not None]

OPTION_PATTERNS = [r"^(?P<und>[A-Z]+?)\d*(?P<kind>[CP])(?P<K>\d+(?:\.\d+)?)$",    # RTM1C45, AAPLC150
                   r"^(?P<und>[A-Z]+?)(?P<K>\d+(?:\.\d+)?)(?P<kind>[CP])$"]       # RTM48P, RTM45C

def parse_option_ticker(t, patterns=None):
    """'RTM1C45' / 'RTM48P' -> ('RTM', 'call'/'put', strike). Add a regex to OPTION_PATTERNS if the
    case names options differently (named groups und, kind, K)."""
    for pat in patterns or OPTION_PATTERNS:
        m = re.match(pat, t)
        if m: return m.group("und"), "call" if m.group("kind") == "C" else "put", float(m.group("K"))
    return None

class DeltaHedger:
    """Keep portfolio delta inside +/- band by trading the underlying (volatility cases).
    options: {ticker: (K, kind)} or None to auto-parse every ticker with parse_option_ticker.
    S_fn() -> underlying price; T_fn() -> years to expiry; vol_fn() -> vol to compute delta with."""
    def __init__(self, ex, underlying, T_fn, vol_fn, options=None, r=0.0, multiplier=100, band=50,
                 max_trade=5000):
        self.ex, self.u, self.T_fn, self.vol_fn, self.r = ex, underlying, T_fn, vol_fn, r
        self.opts, self.mult, self.band, self.max_trade = options, multiplier, band, max_trade
        self.last_delta = 0.0
    def _options(self):
        if self.opts is not None: return self.opts
        out = {}
        for t in self.ex.symbols():
            p = parse_option_ticker(t)
            if p and p[0] == self.u and t != self.u: out[t] = (p[2], p[1])
        return out
    def portfolio_delta(self, S):
        d = self.ex.get_position(self.u); T = max(self.T_fn(), 1e-6); vol = self.vol_fn()
        for t, (K, kind) in self._options().items():
            q = self.ex.get_position(t)
            if q: d += q * self.mult * bs_greeks(S, K, T, self.r, vol, kind)["delta"]
        return d
    def step(self):
        b, _, a, _ = self.ex.get_book(self.u)
        if b is None or a is None: return
        S = (b + a) / 2; d = self.portfolio_delta(S); self.last_delta = d
        if abs(d) <= self.band: return
        q = min(self.max_trade, round(abs(d)))
        if d > 0: self.ex.place(self.u, "sell", q, b)
        else: self.ex.place(self.u, "buy", q, a)

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
