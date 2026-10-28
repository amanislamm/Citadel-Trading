#!/usr/bin/env python3
"""LIVE GAME CONSOLE — keep this open during the game. Autosaves fills to fills.csv.

Commands (case-insensitive):
  b SYM QTY PX [FEE]     log a BUY fill            s SYM QTY PX [FEE]   log a SELL fill
  m SYM PX               set mark/fair for PnL     p                    positions + PnL
  f SYM FAIR STD         set model fair & std      q SYM [WIDTH_K]      suggested bid/ask (skewed by pos)
  lim SYM N              set position limit        undo                 remove last fill
  dice N [SIDES] [sum|max|min]                     cards N [sum|max|min]
  reveal N_UNKNOWN [v1 v2 ...]  (dice sum w/ revealed values)
  bs S K T r SIGMA [call|put]   option price+greeks
  iv PRICE S K T r [call|put]   implied vol
  etf ETF_BID ETF_ASK w1 b1 a1 w2 b2 a2 ...       ETF vs basket arb
  pcp C P S K [r T]             put-call parity mispricing
  kelly EDGE STD BANKROLL        fractional Kelly size
  py EXPR                        evaluate any Python using tt.*   (e.g. py coupon_collector(6))
  save | load | help | quit
"""
import os, sys, shlex
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tt import *  # noqa
import tt

book = Book(); marks = {}; fairs = {}
SAVE = "fills.csv"

def show_pos():
    book.report(marks if marks else None)
    for s, (f, sd) in fairs.items():
        print(f"  {s}: fair {f} ± {sd}  pos {book.pos[s]}  breakeven {book.avg_cost(s)}")

def run(cmd):
    parts = shlex.split(cmd)
    if not parts: return
    c, a = parts[0].lower(), parts[1:]
    if c in ("b", "s", "buy", "sell"):
        book.fill(a[0].upper(), "buy" if c[0] == "b" else "sell", float(a[1]), float(a[2]),
                  float(a[3]) if len(a) > 3 else 0.0)
        book.save(SAVE); show_pos()
    elif c == "m": marks[a[0].upper()] = float(a[1]); show_pos()
    elif c == "p": show_pos()
    elif c == "f":
        fairs[a[0].upper()] = (float(a[1]), float(a[2])); marks.setdefault(a[0].upper(), float(a[1]))
        print("set", a[0].upper(), fairs[a[0].upper()])
    elif c == "q":
        sym = a[0].upper(); f, sd = fairs[sym]
        wk = float(a[1]) if len(a) > 1 else 0.5
        lim = book.limits.get(sym, 100)
        print("quote:", quote(f, sd, book.pos[sym], lim, width_k=wk))
    elif c == "lim": book.limits[a[0].upper()] = float(a[1]); print("limits", book.limits)
    elif c == "undo":
        if book.fills:
            f = book.fills.pop(); fl = book.fills[:]; book.__init__(book.limits)
            for x in fl: book.fill(x["sym"], x["side"], x["qty"], x["px"], x["fee"])
            print("undid", f); show_pos()
    elif c == "dice":
        n = int(a[0]); sides = int(a[1]) if len(a) > 1 else 6
        fn = {"sum": sum, "max": max, "min": min}[a[2] if len(a) > 2 else "sum"]
        if sides ** n <= 2_000_000: print(stats(dice_dist(n, sides, fn)))
        else:
            import random
            print(stats(mc_dist(lambda: fn(random.randint(1, sides) for _ in range(n)))))
    elif c == "cards":
        fn = {"sum": sum, "max": max, "min": min}[a[1] if len(a) > 1 else "sum"]
        print(stats(card_draw_dist(int(a[0]), func=fn)))
    elif c == "reveal": print(reveal_sum([float(x) for x in a[1:]], int(a[0])))
    elif c == "bs":
        S, K, T, r, sg = map(float, a[:5]); k = a[5] if len(a) > 5 else "call"
        print("price", bs_price(S, K, T, r, sg, k), bs_greeks(S, K, T, r, sg, k))
    elif c == "iv":
        p, S, K, T, r = map(float, a[:5]); k = a[5] if len(a) > 5 else "call"
        print("iv", implied_vol(p, S, K, T, r, k))
    elif c == "etf":
        eb, ea = float(a[0]), float(a[1]); rest = list(map(float, a[2:]))
        ws = rest[0::3]; comps = list(zip(rest[1::3], rest[2::3]))
        print(etf_arb(eb, ea, comps, ws))
    elif c == "pcp":
        v = list(map(float, a)); print("mispricing (C-P)-(S-PV(K)):", put_call_parity(*v))
    elif c == "kelly": print("units:", kelly_size(*map(float, a)))
    elif c == "py": print(eval(" ".join(a), vars(tt)))
    elif c == "save": book.save(SAVE); print("saved", SAVE)
    elif c == "load": book.__init__(book.limits); book.load(SAVE); show_pos()
    elif c in ("help", "h", "?"): print(__doc__)
    elif c in ("quit", "exit"): sys.exit(0)
    else: print("unknown; type help")

if __name__ == "__main__":
    print(__doc__)
    while True:
        try: run(input("tt> "))
        except (EOFError, KeyboardInterrupt): print(); break
        except SystemExit: break
        except Exception as e: print("error:", e)
