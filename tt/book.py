"""Position / PnL / risk tracking. Log every fill."""
from collections import Counter, defaultdict
import csv, time

__all__ = ["Book"]

class Book:
    def __init__(self, limits=None):
        self.pos = Counter(); self.cash = 0.0; self.fills = []
        self.limits = limits or {}          # {sym: max_abs_position}
        self.fees = 0.0
        self.realized = Counter()           # realized PnL per sym (average-cost method, net of fees)
        self._cost = Counter()              # avg entry price of the open position

    def fill(self, sym, side, qty, px, fee=0.0):
        s = 1 if side.lower() in ("buy", "b") else -1
        old = self.pos[sym]; new = old + s * qty
        if old == 0 or (old > 0) == (s > 0):                     # opening / adding
            self._cost[sym] = (self._cost[sym] * abs(old) + px * qty) / abs(new)
        else:                                                     # reducing / flipping
            closed = min(qty, abs(old))
            self.realized[sym] += closed * (px - self._cost[sym]) * (1 if old > 0 else -1)
            if abs(s * qty) > abs(old): self._cost[sym] = px       # flipped: new position at px
            elif new == 0: self._cost[sym] = 0.0
        self.realized[sym] -= fee
        self.pos[sym] = new
        self.cash -= s * qty * px + fee
        self.fees += fee
        self.fills.append({"t": time.time(), "sym": sym, "side": "buy" if s > 0 else "sell",
                           "qty": qty, "px": px, "fee": fee})
        lim = self.limits.get(sym)
        if lim is not None and abs(self.pos[sym]) > lim:
            print(f"!! LIMIT BREACH {sym}: pos {self.pos[sym]} > {lim}")

    def avg_cost(self, sym):
        """Average entry price of the CURRENT open position (None if flat)."""
        return self._cost[sym] if self.pos[sym] else None

    def unrealized(self, sym, mark):
        return self.pos[sym] * (mark - self._cost[sym]) if self.pos[sym] else 0.0

    def breakeven(self, sym):
        """Price at which closing the whole position makes total PnL on sym = 0 (net cash / net qty)."""
        q = c = 0.0
        for f in self.fills:
            if f["sym"] != sym: continue
            s = 1 if f["side"] == "buy" else -1
            q += s * f["qty"]; c += s * f["qty"] * f["px"] + f["fee"]
        return c / q if q else None

    def pnl(self, marks):
        return self.cash + sum(self.pos[s] * marks.get(s, 0) for s in self.pos)

    def pnl_by_sym(self, marks):
        cash = defaultdict(float)
        for f in self.fills:
            s = 1 if f["side"] == "buy" else -1
            cash[f["sym"]] -= s * f["qty"] * f["px"] + f["fee"]
        return {s: cash[s] + self.pos[s] * marks.get(s, 0) for s in cash}

    def exposure(self, marks, betas=None):
        """Net delta exposure in $; betas maps sym -> hedge ratio vs a common factor."""
        betas = betas or {}
        return sum(self.pos[s] * marks.get(s, 0) * betas.get(s, 1) for s in self.pos)

    def report(self, marks=None):
        marks = marks or {}
        syms = sorted(set(self.pos) | set(self.realized))
        print(f"{'sym':<6}{'pos':>8}{'avg':>10}{'mark':>10}{'real':>10}{'unreal':>10}{'total':>10}")
        for k in syms:
            m = marks.get(k); ac = self.avg_cost(k)
            u = self.unrealized(k, m) if m is not None else None
            tot = self.realized[k] + (u or 0.0)
            f = lambda x: f"{x:>10.2f}" if x is not None else f"{'-':>10}"
            lim = self.limits.get(k)
            warn = "  !! AT LIMIT" if lim and abs(self.pos[k]) >= lim else ""
            print(f"{k:<6}{self.pos[k]:>8g}{f(ac)}{f(m)}{f(self.realized[k])}{f(u)}{f(tot)}{warn}")
        missing = [k for k in syms if self.pos[k] and k not in marks]
        line = f"Cash {self.cash:.2f} | fees {self.fees:.2f}"
        if not missing: line += f" | TOTAL MTM PnL {self.pnl(marks):.2f}"
        else: line += f" | (no mark for {missing}: set with m SYM PX)"
        print(line)

    def save(self, path="fills.csv"):
        with open(path, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["t", "sym", "side", "qty", "px", "fee"])
            w.writeheader(); w.writerows(self.fills)

    def load(self, path="fills.csv"):
        with open(path) as fh:
            for r in csv.DictReader(fh):
                self.fill(r["sym"], r["side"], float(r["qty"]), float(r["px"]), float(r["fee"]))
