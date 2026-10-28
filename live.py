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
  fairs                  table of all fairs, quotes, positions, room left under limits
  mkt dice N [SIDES] [sum|max|min] [as SYM]    instant market from a distribution
  mkt cards N [sum|max|min] [as SYM]           (uses remaining deck)
  mkt fermi LO HI [as SYM]                     estimation market from your 90% bounds
  news SYM IMPACT% [P_TRUE] [PRICED_IN]        e.g. news X -8 0.7 0.25 -> fair moves -4.2%
  settle SYM PX          settlement known: mark at PX and show final PnL
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
import math, os, sys, shlex, shutil, time
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
    print(f"{'sym':<6}{'fair':>10}{'std':>10}{'pos':>7}{'bid':>10}{'ask':>10}{'room buy/sell':>15}")
    for s, (f, sd) in fairs.items():
        lim = book.limits.get(s, 100); p = book.pos[s]
        b, a = quote(f, sd, p, lim, tick=tick_for(sd))
        print(f"{s:<6}{f:>10.6g}{sd:>10.4g}{p:>7g}{b:>10.6g}{a:>10.6g}{f'{lim - p:g}/{lim + p:g}':>15}")

def tick_for(sd):
    """Sensible quoting tick: whole numbers for wide markets, finer when std is small."""
    return 1.0 if sd >= 5 else 0.5 if sd >= 2 else 0.1 if sd >= 0.3 else 0.01

def market(fair, sd, sym=None):
    """Print what to say out loud for a 'make me a market' question."""
    t = tick_for(sd)
    r = lambda x: round(x / t) * t
    lo, hi = conf_interval(fair, sd, 0.9)
    print(f"fair {fair:.3f}  std {sd:.3f}  90% [{lo:.2f}, {hi:.2f}]")
    for k, label in ((1.0, "opening (wide)"), (0.5, "normal"), (0.25, "tight / confident")):
        print(f"  {label:<18} {r(fair - k * sd):g} @ {r(fair + k * sd):g}")
    if sym:
        fairs[sym] = (fair, sd); marks[sym] = fair; print(f"set fair for {sym}")

def rebuild(fills):
    lim = book.limits; book.__init__(lim)
    for x in fills: book.fill(x["sym"], x["side"], x["qty"], x["px"], x["fee"])

def run(cmd):
    parts = shlex.split(cmd)
    if not parts: return
    c, a = parts[0].lower(), parts[1:]
    if c in ("b", "s", "buy", "sell"):
        sym, q = a[0].upper(), num(a[1]); lim = book.limits.get(sym)
        newpos = book.pos[sym] + (q if c[0] == "b" else -q)
        if lim is not None and abs(newpos) > lim:
            print(f"!!!!!! THIS FILL PUTS {sym} AT {newpos:g}, LIMIT {lim:g}. GET BACK INSIDE NOW !!!!!!")
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
        print("quote:", quote(f, sd, book.pos[sym], book.limits.get(sym, 100), width_k=wk, tick=tick_for(sd)),
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
    elif c == "mkt":
        sym = None
        if len(a) >= 2 and a[-2].lower() == "as": sym = a[-1].upper(); a = a[:-2]
        kind, rest = a[0].lower(), a[1:]
        if kind == "dice":
            n = int(rest[0]); sides = int(rest[1]) if len(rest) > 1 else 6
            fn = {"sum": sum, "max": max, "min": min}[rest[2] if len(rest) > 2 else "sum"]
            st = stats(dice_dist(n, sides, fn))
        elif kind == "cards":
            fn = {"sum": sum, "max": max, "min": min}[rest[1] if len(rest) > 1 else "sum"]
            st = stats(deck.draw_dist(int(rest[0]), fn))
        elif kind == "fermi":                                      # quote multiplicatively
            g, mult = fermi(num(rest[0]), num(rest[1])); sig = lambda x: float(f"{x:.3g}")
            print(f"fair (geo mean) {sig(g):g}; 90% [{sig(num(rest[0])):g}, {sig(num(rest[1])):g}]")
            for k, label in ((1.0, "opening (wide)"), (0.5, "normal"), (0.25, "tight / confident")):
                print(f"  {label:<18} {sig(g / mult ** k):g} @ {sig(g * mult ** k):g}")
            if sym: fairs[sym] = (g, g * (mult - 1)); marks[sym] = g; print(f"set fair for {sym}")
            return
        else:
            st = {"mean": num(a[0]), "std": num(a[1])}
        market(st["mean"], st["std"], sym)
    elif c == "news":
        sym = a[0].upper(); f, sd = fairs[sym]
        pt = float(a[2]) if len(a) > 2 else 1.0; pr = float(a[3]) if len(a) > 3 else 0.0
        nf = news_fair_update(f, float(a[1]) / 100, pt, pr)
        fairs[sym] = (nf, sd); marks[sym] = nf
        print(f"{sym} fair {f:.3f} -> {nf:.3f} ({(nf / f - 1) * 100:+.2f}%)."
              f" Pick off stale quotes first, then requote: {quote(nf, sd, book.pos[sym], book.limits.get(sym, 100), tick=tick_for(sd))}")
    elif c == "fermi":
        lo, hi = num(a[0]), num(a[1]); g, mult = fermi(lo, hi)
        print(f"fair (geo mean) {g:.4g}; 1-sd range x/÷{mult:.2f} -> [{g / mult:.4g}, {g * mult:.4g}]")
    elif c == "settle":
        sym = a[0].upper(); marks[sym] = num(a[1]); show_pos()
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
