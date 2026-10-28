"""Position / PnL / risk tracking. Log every fill."""
from collections import Counter, defaultdict
import csv, time

__all__ = ["Book"]

class Book:
    def __init__(self, limits=None):
        self.pos = Counter(); self.cash = 0.0; self.fills = []
        self.limits = limits or {}          # {sym: max_abs_position}
        self.fees = 0.0

    def fill(self, sym, side, qty, px, fee=0.0):
        s = 1 if side.lower() in ("buy", "b") else -1
        self.pos[sym] += s * qty
        self.cash -= s * qty * px + fee
        self.fees += fee
        self.fills.append({"t": time.time(), "sym": sym, "side": "buy" if s > 0 else "sell",
                           "qty": qty, "px": px, "fee": fee})
        lim = self.limits.get(sym)
        if lim is not None and abs(self.pos[sym]) > lim:
            print(f"!! LIMIT BREACH {sym}: pos {self.pos[sym]} > {lim}")

    def avg_cost(self, sym):
        q = c = 0.0
        for f in self.fills:
            if f["sym"] != sym: continue
            s = 1 if f["side"] == "buy" else -1
            q += s * f["qty"]; c += s * f["qty"] * f["px"]
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
        print("Positions:", {k: v for k, v in self.pos.items() if v}, "| Cash:", round(self.cash, 2))
        if marks:
            print("MTM PnL:", round(self.pnl(marks), 2), "| by sym:",
                  {k: round(v, 2) for k, v in self.pnl_by_sym(marks).items()})

    def save(self, path="fills.csv"):
        with open(path, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["t", "sym", "side", "qty", "px", "fee"])
            w.writeheader(); w.writerows(self.fills)

    def load(self, path="fills.csv"):
        with open(path) as fh:
            for r in csv.DictReader(fh):
                self.fill(r["sym"], r["side"], float(r["qty"]), float(r["px"]), float(r["fee"]))
