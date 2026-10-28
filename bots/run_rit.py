#!/usr/bin/env python3
"""RIT bot runner. Edit CONFIG, then:

  python3 bots/run_rit.py --check          connect, print case / securities / limits, exit
  python3 bots/run_rit.py                  PAPER mode: real data, orders only printed
  python3 bots/run_rit.py --live           real orders (Ctrl-C cancels everything and stops)

Each loop: print new news, evaluate tenders (accept if edge > TENDER_MIN_EDGE), market-make
the MM_TICKERS with inventory skew, ETF-arb if ETF is set. RiskGuard blocks limit breaches.
"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bots.rit import RIT, RITError
from bots.adapter import RiskGuard, PaperAdapter
from bots.strategies import MarketMaker, ETFArb
from tt.arb import tender_eval

# ---------------- CONFIG (edit on game day) ----------------
API_KEY = os.environ.get("RIT_KEY", "PASTE_KEY_HERE")
BASE_URL = "http://localhost:9999/v1"
MM_TICKERS = {            # ticker: dict(std=..., size=..., max_pos=..., width_k=...)
    # "CRZY": dict(std=0.05, size=500, max_pos=5000, width_k=1.0),
}
ETF = None                # e.g. ("ETF", ["A", "B"], [1, 1], 0.05)  -> (etf, comps, weights, threshold)
MAX_ORDER_SIZE = 5000     # RIT per-order cap from the case brief
MAX_POS = {}              # per-ticker hard limits for RiskGuard, e.g. {"CRZY": 25000}
DEFAULT_MAX_POS = 10000
TENDER_MIN_EDGE = 0.02    # $/share needed to accept a tender after unwinding into visible depth
LOOP_DT = 0.3
# ------------------------------------------------------------

def check(ex):
    print("case:", ex.case())
    for s in ex.securities():
        print(f"  {s.get('ticker'):<8} pos {s.get('position'):>8}  {s.get('bid')} @ {s.get('ask')}  last {s.get('last')}")
    try: print("limits:", ex.limits())
    except RITError as e: print("limits:", e)

def handle_tenders(ex, seen, live):
    for t in ex.tenders() or []:
        tid = t.get("tender_id")
        if tid in seen: continue
        seen.add(tid)
        sym, qty, px, act = t["ticker"], t["quantity"], t.get("price"), t["action"].lower()
        if px is None:
            print(f"TENDER {tid}: {act} {qty} {sym}, you choose the price (auction): decide manually"); continue
        r = tender_eval(act, qty, px, ex.book(sym, limit=50), min_edge=TENDER_MIN_EDGE)
        print(f"TENDER {tid}: {act} {qty} {sym} @ {px} -> {r['verdict']} (edge {r['edge_per_share']:.3f}/sh, profit {r['profit']:.0f})")
        if live and r["verdict"].startswith("ACCEPT"): ex.accept_tender(tid)

def main(argv):
    rit = RIT(API_KEY, BASE_URL, max_order_size=MAX_ORDER_SIZE)
    if "--check" in argv: check(rit); return
    live = "--live" in argv
    ex = RiskGuard(rit if live else PaperAdapter(rit), max_pos=MAX_POS, default_max_pos=DEFAULT_MAX_POS,
                   max_qty=MAX_ORDER_SIZE * 5, max_orders_per_s=20)
    strats = [MarketMaker(ex, s, tick=0.01, **p) for s, p in MM_TICKERS.items()]
    if ETF: strats.append(ETFArb(ex, ETF[0], ETF[1], ETF[2], threshold=ETF[3], size=MAX_ORDER_SIZE // 10))
    print("MODE:", "LIVE" if live else "PAPER (add --live to trade)")
    rit.wait_for_active()
    seen_tenders, last_news = set(), None
    try:
        while rit.is_active():
            news = rit.news(since=last_news) or []
            for n in news:
                print(f"NEWS t{n.get('tick')}: {n.get('headline')}"); last_news = max(last_news or 0, n.get("news_id", 0))
            handle_tenders(rit, seen_tenders, live)
            for s in strats:
                try: s.step()
                except RITError as e: print("error:", e)
            time.sleep(LOOP_DT)
        print("case no longer ACTIVE")
    except KeyboardInterrupt:
        print("stopping")
    finally:
        if live:
            try: rit.cancel_all(); print("cancelled all orders")
            except RITError as e: print("cancel_all failed:", e)

if __name__ == "__main__":
    main(sys.argv[1:])
