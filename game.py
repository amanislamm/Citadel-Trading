#!/usr/bin/env python3
"""PRACTICE GAME — multi-product market making with an ETF, news, stale quotes and planted arbs.
Everything settles at TRUE value at the end. Rehearse with live.py open beside it.

  python3 game.py [TURNS] [--seed N]       (default 30 turns)

Each turn you see the market. Commands (several per turn, Enter alone = next turn):
  buy SYM QTY | sell SYM QTY        cross the displayed ask / bid
  mm SYM BID ASK [SIZE]             post your own market for this turn (bots may hit it)
  pos | help | quit
ETF = 2*A + 1*B + 1*C. Position limit 50 per product (penalty 5 per unit over, per turn).
"""
import os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tt import Book

W = {"A": 2, "B": 1, "C": 1}
LIMIT, PENALTY, SPREAD = 50, 5.0, 0.4
NEWS = [("{s}: earnings beat, guidance raised", +1), ("{s}: CEO resigns unexpectedly", -1),
        ("{s}: wins large government contract", +1), ("{s}: regulator opens investigation", -1),
        ("{s}: rumour of takeover bid (unconfirmed)", +0.5), ("{s}: analyst downgrade", -0.5)]

class Game:
    def __init__(self, turns=30, seed=None):
        self.r = random.Random(seed); self.turns = turns; self.t = 0
        self.true = {"A": 50.0, "B": 30.0, "C": 20.0}
        self.disp = dict(self.true)          # what the bots *think* (lags after news)
        self.book = Book(limits={s: LIMIT for s in list(W) + ["ETF"]})
        self.mm = {}; self.penalties = 0.0; self.etf_err = 0.0; self.log = []

    def etf_true(self, px=None):
        px = px or self.true; return sum(w * px[s] for s, w in W.items())

    def quotes(self):
        q = {}
        for s in W:
            m = self.disp[s] + self.r.gauss(0, 0.1)
            q[s] = (round(m - SPREAD, 2), round(m + SPREAD, 2))
        m = self.etf_true(self.disp) + self.etf_err + self.r.gauss(0, 0.1)
        q["ETF"] = (round(m - 2 * SPREAD, 2), round(m + 2 * SPREAD, 2))
        return q

    def step_world(self):
        self.t += 1; msgs = []
        for s in W: self.true[s] += self.r.gauss(0, 0.25)
        for s in W:                                  # bots catch up halfway to true each turn
            self.disp[s] += 0.5 * (self.true[s] - self.disp[s])
        if self.r.random() < 0.25:                   # news shock: true moves now, bots lag
            s = self.r.choice(list(W)); txt, d = self.r.choice(NEWS)
            mv = d * self.r.uniform(1.5, 4.0)
            if abs(d) == 0.5 and self.r.random() < 0.5: mv = 0.0   # rumours/downgrades often nothing
            self.true[s] += mv; msgs.append("NEWS  " + txt.format(s=s))
        self.etf_err *= 0.3
        if self.r.random() < 0.15:                   # planted ETF mispricing
            self.etf_err = self.r.choice([-1, 1]) * self.r.uniform(2.5, 4.5)   # beats both spreads
        return msgs

    def trade(self, sym, side, qty, px):
        self.book.fill(sym, side, qty, px); self.log.append((self.t, sym, side, qty, px))

    def flow_vs_mm(self):
        """Bots hit your posted markets: informed if you're off true, noise otherwise."""
        out = []
        for s, (b, a, sz) in self.mm.items():
            tv = self.etf_true() if s == "ETF" else self.true[s]
            if a < tv and self.r.random() < 0.8: self.trade(s, "sell", sz, a); out.append(f"lifted {sz} {s} @ {a}")
            elif b > tv and self.r.random() < 0.8: self.trade(s, "buy", sz, b); out.append(f"hit {sz} {s} @ {b}")
            elif self.r.random() < max(0.0, 0.6 - 0.15 * (a - b)):   # noise, more if you're tight
                side = self.r.choice(["buy", "sell"])
                self.trade(s, side, sz, b if side == "buy" else a)
                out.append(f"noise {'hit' if side == 'buy' else 'lifted'} {sz} {s} @ {b if side == 'buy' else a}")
        self.mm = {}
        return out

    def check_limits(self):
        for s, p in self.book.pos.items():
            if abs(p) > LIMIT: self.penalties += PENALTY * (abs(p) - LIMIT); print(f"  !! {s} over limit: penalty")

    def settle(self):
        marks = dict(self.true); marks["ETF"] = self.etf_true()
        return self.book.pnl(marks) - self.penalties, marks

def show(g, q):
    print(f"\n=== turn {g.t}/{g.turns} " + "=" * 40)
    for s in ["A", "B", "C", "ETF"]:
        b, a = q[s]; p = g.book.pos[s]
        print(f"  {s:<4} {b:>8.2f} @ {a:<8.2f}  pos {p:>5g}")
    bb = sum(w * q[s][0] for s, w in W.items()); ba = sum(w * q[s][1] for s, w in W.items())
    print(f"  basket (2A+B+C) {bb:.2f} @ {ba:.2f}   <- compare with ETF")

def main(argv):
    turns = next((int(x) for x in argv if x.isdigit()), 30)
    seed = int(argv[argv.index("--seed") + 1]) if "--seed" in argv else None
    g = Game(turns, seed); print(__doc__)
    while g.t < g.turns:
        for m in g.step_world(): print(m)
        q = g.quotes(); show(g, q)
        while True:
            try: cmd = input("game> ").split()
            except EOFError: cmd = ["quit"]
            if not cmd: break
            c = cmd[0].lower()
            try:
                if c in ("buy", "sell"):
                    s, n = cmd[1].upper(), float(cmd[2]); b, a = q[s]
                    g.trade(s, c, n, a if c == "buy" else b); print(f"  {c} {n:g} {s} @ {a if c == 'buy' else b}")
                elif c == "mm":
                    s = cmd[1].upper(); g.mm[s] = (float(cmd[2]), float(cmd[3]), float(cmd[4]) if len(cmd) > 4 else 5)
                    print(f"  posted {s} {cmd[2]} @ {cmd[3]}")
                elif c == "pos": g.book.report({k: (b + a) / 2 for k, (b, a) in q.items()})
                elif c == "help": print(__doc__)
                elif c == "quit": g.t = g.turns; break
                else: print("  ? (help)")
            except (IndexError, KeyError, ValueError): print("  bad command (help)")
        for m in g.flow_vs_mm(): print("  " + m)
        g.check_limits()
    pnl, marks = g.settle()
    print("\n=== SETTLEMENT at true values:", {k: round(v, 2) for k, v in marks.items()})
    g.book.report(marks)
    print(f"Penalties {g.penalties:.2f}   FINAL SCORE {pnl:.2f}   trades {len(g.log)}")
    return pnl

if __name__ == "__main__":
    try: main(sys.argv[1:])
    except KeyboardInterrupt: print()
