#!/usr/bin/env python3
"""RIT ORDER CONSOLE — type orders faster than clicking. Orders are split to the per-order cap.

  RIT_KEY=<key> python3 bots/rit_console.py [--max-order 5000] [--confirm 10000]

  b SYM QTY [PX]        buy  (limit at PX, or MARKET if no PX)     s SYM QTY [PX]   sell
  x [SYM]               cancel all (or one ticker)                 flat [SYM]       market out of positions
  pos | o               positions | open orders                    book SYM [N]     depth
  ten                   tenders with ACCEPT/DECLINE verdicts       ta ID [PX] | td ID   accept / decline
  unwind SYM [TARGET] [STEPS] [CLIP]   work position to TARGET (default 0) over STEPS loops
  hedge UND VOL T_YEARS [BAND]         one delta-hedge of options on UND (tickers like RTM1C45)
  dash | news | help | quit
Orders above --confirm shares ask y/n first (fat-finger guard).
"""
import os, shlex, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bots.rit import RIT, RITError
from bots.strategies import Unwinder, DeltaHedger
from bots.rit_dash import render
from tt.arb import tender_eval

def arg(argv, name, default):
    return int(argv[argv.index(name) + 1]) if name in argv else default

class Console:
    def __init__(self, ex, confirm=10000, ask=input):
        self.ex, self.confirm, self.ask = ex, confirm, ask

    def ok_size(self, qty):
        return qty <= self.confirm or self.ask(f"  {qty:g} shares is large. Send? [y/N] ").strip().lower() == "y"

    def run(self, line):
        p = shlex.split(line)
        if not p: return True
        c, a, ex = p[0].lower(), p[1:], self.ex
        if c in ("b", "s", "buy", "sell"):
            side = "buy" if c[0] == "b" else "sell"; sym, qty = a[0].upper(), float(a[1])
            if not self.ok_size(qty): print("  cancelled"); return True
            if len(a) > 2: oid = ex.place(sym, side, qty, float(a[2])); print(f"  LIMIT {side} {qty:g} {sym} @ {a[2]} -> id {oid}")
            else: ids = ex.market(sym, side, qty); print(f"  MARKET {side} {qty:g} {sym} -> {len(ids)} order(s)")
        elif c == "x": ex.cancel_all(a[0].upper() if a else None); print("  cancelled", a[0].upper() if a else "ALL")
        elif c == "flat":
            if self.ask("  market out of " + (a[0].upper() if a else "EVERYTHING") + "? [y/N] ").strip().lower() == "y":
                ex.flatten([a[0].upper()] if a else None); print("  flattened")
        elif c == "pos": print("  " + "  ".join(f"{k}:{v:g}" for k, v in ex.positions().items()))
        elif c == "o":
            for o in ex.orders() or []: print(f"  {o.get('order_id')}: {o.get('action')} {o.get('quantity')} {o.get('ticker')} @ {o.get('price')}")
        elif c == "book":
            bk = ex.book(a[0].upper(), limit=int(a[1]) if len(a) > 1 else 5)
            for (bp, bq), (ap, aq) in zip(bk["bids"], bk["asks"]): print(f"  {bq:>8g} {bp:>9.2f} | {ap:<9.2f} {aq:<8g}")
        elif c == "ten":
            for t in ex.tenders() or []:
                if t.get("price") is None: print(f"  {t['tender_id']}: {t['action']} {t['quantity']} {t['ticker']} (set price)"); continue
                r = tender_eval(t["action"].lower(), t["quantity"], t["price"], ex.book(t["ticker"], limit=50))
                print(f"  {t['tender_id']}: {t['action']} {t['quantity']} {t['ticker']} @ {t['price']} -> {r['verdict']} ({r['edge_per_share']:+.3f}/sh)")
        elif c == "ta": ex.accept_tender(int(a[0]), float(a[1]) if len(a) > 1 else None); print("  accepted", a[0])
        elif c == "td": ex.decline_tender(int(a[0])); print("  declined", a[0])
        elif c == "unwind":
            sym = a[0].upper(); tgt = float(a[1]) if len(a) > 1 else 0
            u = Unwinder(ex, sym, tgt, int(a[2]) if len(a) > 2 else 60, int(a[3]) if len(a) > 3 else 1000)
            print(f"  unwinding {sym} to {tgt:g} (Ctrl-C to stop)")
            try:
                while not u.done() and ex.is_active():
                    u.step(); print(f"  pos {ex.get_position(sym):g}", end="\r"); time.sleep(0.5)
            except KeyboardInterrupt:
                pass
            finally:
                ex.cancel_all(sym); print(f"\n  stopped at pos {ex.get_position(sym):g}")
        elif c == "hedge":
            und, vol, T = a[0].upper(), float(a[1]), float(a[2])
            h = DeltaHedger(ex, und, lambda: T, lambda: vol, band=float(a[3]) if len(a) > 3 else 50)
            h.step(); print(f"  portfolio delta before hedge {h.last_delta:+.0f}")
        elif c == "dash": print(render(ex))
        elif c == "news":
            for n in (ex.news() or [])[:10]: print(f"  t{n.get('tick')}: {n.get('headline')}")
        elif c in ("help", "h", "?"): print(__doc__)
        elif c in ("quit", "exit", "q"): return False
        else: print("  unknown; type help")
        return True

def main(argv):
    ex = RIT(os.environ.get("RIT_KEY", "KEY"), os.environ.get("RIT_URL", "http://localhost:9999/v1"),
             max_order_size=arg(argv, "--max-order", 5000))
    con = Console(ex, confirm=arg(argv, "--confirm", 10000))
    print(__doc__)
    try: print(render(ex))
    except RITError as e: print("RIT not reachable yet:", e)
    while True:
        try:
            if not con.run(input("rit> ")): break
        except (EOFError, KeyboardInterrupt): print(); break
        except RITError as e: print("  RIT:", e)
        except (IndexError, ValueError) as e: print("  bad args:", e, "(help)")

if __name__ == "__main__":
    main(sys.argv[1:])
