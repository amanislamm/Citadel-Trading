#!/usr/bin/env python3
"""RIT live dashboard. Refreshes every second: positions, quotes, P&L, limit usage, news, tenders
(each with an ACCEPT/DECLINE verdict from unwinding into visible depth).

  RIT_KEY=<key> python3 bots/rit_dash.py           (RIT_URL=... if not localhost:9999)
  RIT_KEY=<key> python3 bots/rit_dash.py --once    print once and exit
Read-only: never sends orders. Run it on the second laptop / second terminal.
"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bots.rit import RIT, RITError
from tt.arb import tender_eval

def connect():
    return RIT(os.environ.get("RIT_KEY", "KEY"), os.environ.get("RIT_URL", "http://localhost:9999/v1"))

def fmt(x, w=9, d=2):
    return f"{x:>{w}.{d}f}" if isinstance(x, (int, float)) else f"{'-' if x is None else x:>{w}}"

def render(ex, news_n=5):
    out = []
    c = ex.case()
    out.append(f"{c.get('name', '?')}  period {c.get('period')}/{c.get('total_periods', '?')}  "
               f"tick {c.get('tick')}/{c.get('ticks_per_period', '?')}  {c.get('status')}")
    try:
        tr = ex.trader(); out.append(f"NLV {fmt(tr.get('nlv'), 12)}")
    except RITError:
        pass
    out.append(f"{'ticker':<8}{'pos':>9}{'bid':>9}{'ask':>9}{'sprd':>7}{'last':>9}{'unreal':>10}{'real':>10}")
    for s in ex.securities():
        b, a = s.get("bid"), s.get("ask")
        sp = (a - b) if isinstance(a, (int, float)) and isinstance(b, (int, float)) else None
        out.append(f"{s.get('ticker', '?'):<8}{fmt(s.get('position'), 9, 0)}{fmt(b)}{fmt(a)}{fmt(sp, 7)}"
                   f"{fmt(s.get('last'))}{fmt(s.get('unrealized'), 10)}{fmt(s.get('realized'), 10)}")
    try:
        for L in ex.limits() or []:
            for kind in ("gross", "net"):
                used, lim = L.get(kind), L.get(f"{kind}_limit")
                if isinstance(used, (int, float)) and lim:
                    pct = abs(used) / lim
                    bar = "#" * int(min(pct, 1) * 20)
                    warn = "  !! NEAR LIMIT" if pct >= 0.8 else ""
                    out.append(f"limit {L.get('name', '')} {kind:<5} {used:>9.0f}/{lim:<9.0f} [{bar:<20}] {pct:4.0%}{warn}")
    except RITError:
        pass
    try:
        ten = ex.tenders() or []
    except RITError:
        ten = []
    for t in ten:
        px = t.get("price")
        if px is None:
            out.append(f"TENDER {t.get('tender_id')}: {t.get('action')} {t.get('quantity')} {t.get('ticker')} (you set price)")
            continue
        r = tender_eval(t["action"].lower(), t["quantity"], px, ex.book(t["ticker"], limit=50))
        out.append(f"TENDER {t.get('tender_id')}: {t['action']} {t['quantity']} {t['ticker']} @ {px} -> "
                   f"{r['verdict']}  edge {r['edge_per_share']:+.3f}/sh  P&L {r['profit']:+.0f}  (expires {t.get('expires')})")
    try:
        news = (ex.news() or [])[:news_n]
    except RITError:
        news = []
    for n in news:
        out.append(f"news t{n.get('tick')}: {n.get('headline')}")
    return "\n".join(out)

def main(argv):
    ex = connect()
    if "--once" in argv: print(render(ex)); return
    try:
        while True:
            try: screen = render(ex)
            except RITError as e: screen = f"RIT error: {e}"
            print("\033[2J\033[H" + time.strftime("%H:%M:%S") + "\n" + screen, flush=True)
            time.sleep(1.0)
    except KeyboardInterrupt:
        print()

if __name__ == "__main__":
    main(sys.argv[1:])
