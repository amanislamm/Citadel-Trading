#!/usr/bin/env python3
"""LIVE GAME CONSOLE — keep this open during the game. Autosaves fills to fills.csv and
RELOADS them on restart (use `reset` to start fresh; the old file is backed up).

Commands (case-insensitive; numbers like 10k / 1.5m work):
 POSITIONS
  b SYM QTY PX [FEE]     log a BUY fill            s SYM QTY PX [FEE]   log a SELL fill
  m SYM PX               set mark for PnL          p                    positions + PnL table
  lim SYM N              set position limit        undo                 remove last fill
  reset                  clear book (backs up fills.csv)
 FAIR VALUE / QUOTING
  f SYM FAIR STD         set model fair & std      q SYM [WIDTH_K]      suggested bid/ask (skewed by pos)
  t SYM BID ASK [K]      take-or-pass vs your fair (edge > K*std, default 0.25)
  gm SYM PX [TRUST]      someone traded at PX -> shift fair toward it (default trust 0.3)
  fairs                  table of all fairs, quotes, positions
 PROBABILITY
  dice N [SIDES] [sum|max|min]                     cards N [sum|max|min]  (uses remaining deck)
  deck | seen V1 V2 .. | unsee V1 .. | newdeck     card counter (A=1 .. K=13; J Q K A ok)
  reveal N_UNKNOWN [v1 v2 ...]  (dice sum w/ revealed values)
 OPTIONS / ARB
  bs S K T r SIGMA [call|put]   option price+greeks
  iv PRICE S K T r [call|put]   implied vol
  etf ETF_BID ETF_ASK w1 b1 a1 w2 b2 a2 ...       ETF vs basket arb
  pcp C P S K [r T]             put-call parity mispricing
  ladder p1 p2 ...              binary ladder (should sum to 1 / 100)
  kelly EDGE STD BANKROLL       fractional Kelly size
 MISC
  py EXPR | py x = EXPR         run Python with tt.* (variables persist; e.g. py coupon_collector(6))
  save | load | help | quit
"""
import os, sys, shlex, shutil, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tt import *  # noqa
import tt

try:
    import readline  # noqa: F401  (up-arrow history on mac/linux)
except ImportError:
    pass

SAVE = "fills.csv"
book = Book(); marks = {}; fairs = {}; deck = Deck()
ns = dict(vars(tt)); ns.update(book=book, marks=marks, fairs=fairs)
CARD = {"A": 1, "J": 11, "Q": 12, "K": 13, "T": 10}

def num(x):
    """'10k' -> 10000, '1.5m' -> 1.5e6."""
    x = x.lower().replace(",", "")
    mult = {"k": 1e3, "m": 1e6, "b": 1e9}.get(x[-1:], None)
    return float(x[:-1]) * mult if mult else float(x)

def card(x):
    return CARD.get(x.upper(), None) or int(x)

def show_pos():
    book.report(marks)

def show_fairs():
    if not fairs: print("no fairs set (f SYM FAIR STD)"); return
    print(f"{'sym':<6}{'fair':>9}{'std':>8}{'pos':>7}{'bid':>9}{'ask':>9}")
    for s, (f, sd) in fairs.items():
        b, a = quote(f, sd, book.pos[s], book.limits.get(s, 100))
        print(f"{s:<6}{f:>9.2f}{sd:>8.2f}{book.pos[s]:>7g}{b:>9g}{a:>9g}")

def rebuild(fills):
    lim = book.limits; book.__init__(lim)
    for x in fills: book.fill(x["sym"], x["side"], x["qty"], x["px"], x["fee"])

def run(cmd):
    parts = shlex.split(cmd)
    if not parts: return
    c, a = parts[0].lower(), parts[1:]
    if c in ("b", "s", "buy", "sell"):
        book.fill(a[0].upper(), "buy" if c[0] == "b" else "sell", num(a[1]), num(a[2]),
                  num(a[3]) if len(a) > 3 else 0.0)
        marks.setdefault(a[0].upper(), num(a[2]))
        book.save(SAVE); show_pos()
    elif c == "m": marks[a[0].upper()] = num(a[1]); show_pos()
    elif c == "p": show_pos()
    elif c == "f":
        s = a[0].upper(); fairs[s] = (num(a[1]), num(a[2])); marks[s] = num(a[1])
        print("set", s, fairs[s])
    elif c == "q":
        sym = a[0].upper(); f, sd = fairs[sym]
        wk = float(a[1]) if len(a) > 1 else 0.5
        print("quote:", quote(f, sd, book.pos[sym], book.limits.get(sym, 100), width_k=wk),
              f"(fair {f}, pos {book.pos[sym]:g})")
    elif c == "t":
        sym = a[0].upper(); f, sd = fairs[sym]
        k = float(a[3]) if len(a) > 3 else 0.25
        print(should_trade(f, sd, num(a[1]), num(a[2]), k))
    elif c == "gm":
        sym = a[0].upper(); f, sd = fairs[sym]
        tr = float(a[2]) if len(a) > 2 else 0.3
        fairs[sym] = glosten_milgrom_update(f, sd, num(a[1]), None, tr); marks[sym] = fairs[sym][0]
        print(f"{sym} fair {f:.3f} -> {fairs[sym][0]:.3f}, std {sd:.3f} -> {fairs[sym][1]:.3f}")
    elif c == "fairs": show_fairs()
    elif c == "lim": book.limits[a[0].upper()] = num(a[1]); print("limits", book.limits)
    elif c == "undo":
        if book.fills:
            f = book.fills[-1]; rebuild(book.fills[:-1]); book.save(SAVE)
            print("undid", f); show_pos()
    elif c == "reset":
        if os.path.exists(SAVE):
            bk = f"fills_{time.strftime('%H%M%S')}.csv"; shutil.copy(SAVE, bk); print("backed up to", bk)
        book.__init__(book.limits); marks.clear(); book.save(SAVE); print("book cleared")
    elif c == "dice":
        n = int(a[0]); sides = int(a[1]) if len(a) > 1 else 6
        fn = {"sum": sum, "max": max, "min": min}[a[2] if len(a) > 2 else "sum"]
        print(stats(dice_dist(n, sides, fn)))
    elif c == "cards":
        fn = {"sum": sum, "max": max, "min": min}[a[1] if len(a) > 1 else "sum"]
        n = int(a[0])
        print(stats(deck.draw_dist(n, fn)), f"[{len(deck)} cards left]")
        if fn is sum: print("exact (mean, std) of sum:", deck.sum_fair(n))
    elif c == "deck": print(deck, deck.counts())
    elif c == "seen": deck.seen(*map(card, a)); print(deck)
    elif c == "unsee": deck.unsee(*map(card, a)); print(deck)
    elif c == "newdeck": deck.__init__(); print(deck)
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
    elif c == "ladder": print(binary_ladder_check(list(map(float, a))))
    elif c == "kelly": print("units:", kelly_size(*map(num, a)))
    elif c == "py":
        src = cmd.split(None, 1)[1] if len(parts) > 1 else ""
        try: print(eval(src, ns))
        except SyntaxError: exec(src, ns)
    elif c == "save": book.save(SAVE); print("saved", SAVE)
    elif c == "load": rebuild([]); book.load(SAVE); show_pos()
    elif c in ("help", "h", "?"): print(__doc__)
    elif c in ("quit", "exit"): sys.exit(0)
    else: print("unknown; type help")

if __name__ == "__main__":
    print(__doc__)
    if os.path.exists(SAVE):
        try:
            book.load(SAVE)
            for x in book.fills: marks[x["sym"]] = x["px"]        # last traded px as provisional mark
            if book.fills: print(f"reloaded {len(book.fills)} fills from {SAVE} (type reset to start fresh)"); show_pos()
        except Exception as e:
            print("could not reload fills:", e)
    while True:
        try: run(input("tt> "))
        except (EOFError, KeyboardInterrupt): print(); break
        except SystemExit: break
        except KeyError as e: print("unknown symbol/option:", e, "(set fair first with f SYM FAIR STD?)")
        except (IndexError, ValueError) as e: print("bad args:", e, "- type help")
        except Exception as e: print("error:", repr(e))
