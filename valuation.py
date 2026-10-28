#!/usr/bin/env python3
"""FUNDAMENTAL ANALYST TEMPLATE. Fill in INPUTS from the case packet, run `python3 valuation.py`.
Prints: DCF build, WACC x g sensitivity, comps, reverse DCF (what the price implies),
football field, and a pitch outline with your numbers filled in. ~5 minutes from packet to pitch.
Unknown input? Leave the default and SAY it's an assumption in the pitch.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tt.fundamentals import (dcf_build, sensitivity, print_grid, comps_value, implied_terminal_growth,
                             football_field, capm, wacc as wacc_fn)

# ======================= INPUTS (edit these) =======================
COMPANY      = "ExampleCo"
PRICE        = 42.00          # current share price
SHARES       = 100.0          # diluted shares (same units as $ figures / price)
NET_DEBT     = 300.0          # debt - cash
REVENUE0     = 1000.0         # last fiscal year revenue
GROWTH       = [0.12, 0.10, 0.08, 0.06, 0.05]   # per-year revenue growth (or one number)
EBIT_MARGIN  = [0.15, 0.16, 0.17, 0.18, 0.18]   # per-year EBIT margin (or one number)
TAX          = 0.25
DA_PCT, CAPEX_PCT, NWC_PCT = 0.04, 0.05, 0.10   # % of revenue
TERMINAL_G   = 0.025
# WACC: either set directly, or build it from CAPM below
RF, BETA, MRP, COST_DEBT = 0.043, 1.1, 0.055, 0.06
WACC         = None           # e.g. 0.09 to override
EBITDA_LTM   = 190.0          # for comps
PEER_EV_EBITDA = [8.5, 9.0, 10.5, 11.0, 12.5]
EPS_LTM      = 1.95
PEER_PE      = [16, 18, 20, 22]
RANGE_52W    = (31.0, 47.5)
# ===================================================================

def main():
    E = PRICE * SHARES; D = max(NET_DEBT, 0.0)
    w = WACC if WACC is not None else wacc_fn(E, D, capm(RF, BETA, MRP), COST_DEBT, TAX)
    print(f"=== {COMPANY} ===   price {PRICE}   WACC {w:.2%} {'(given)' if WACC else '(CAPM build)'}   g {TERMINAL_G:.1%}\n")
    base = dcf_build(REVENUE0, GROWTH, EBIT_MARGIN, w, TERMINAL_G, years=len(GROWTH) if isinstance(GROWTH, list) else 5,
                     tax=TAX, da_pct=DA_PCT, capex_pct=CAPEX_PCT, nwc_pct=NWC_PCT, net_debt=NET_DEBT, shares=SHARES)
    val = lambda ww, gg: dcf_build(REVENUE0, GROWTH, EBIT_MARGIN, ww, gg, tax=TAX, da_pct=DA_PCT, capex_pct=CAPEX_PCT,
                                   nwc_pct=NWC_PCT, net_debt=NET_DEBT, shares=SHARES, verbose=False)["per_share"]
    ws = [w - 0.02, w - 0.01, w, w + 0.01, w + 0.02]; gs = [TERMINAL_G - 0.01, TERMINAL_G - 0.005, TERMINAL_G, TERMINAL_G + 0.005, TERMINAL_G + 0.01]
    print("\nDCF value per share, WACC (rows) x terminal g (cols):")
    grid = sensitivity(val, ws, gs); print_grid(grid, ws, gs, mark=PRICE)
    flat = [v for row in grid for v in row]

    ev_c = comps_value(EBITDA_LTM, PEER_EV_EBITDA, NET_DEBT, SHARES)
    pe_c = comps_value(EPS_LTM * SHARES, PEER_PE, shares=SHARES, ev_based=False)
    print(f"\nComps EV/EBITDA {ev_c['multiples']}: {ev_c['low']:.2f} / {ev_c['median']:.2f} / {ev_c['high']:.2f}")
    print(f"Comps P/E       {pe_c['multiples']}: {pe_c['low']:.2f} / {pe_c['median']:.2f} / {pe_c['high']:.2f}")

    ig = implied_terminal_growth(PRICE, lambda gg: val(w, gg), lo=-0.05, hi=w - 0.001)
    print(f"\nReverse DCF: at {PRICE} the market implies terminal growth of "
          + (f"{ig:.2%}" if ig is not None else "n/a (outside -5%..WACC)") + f" vs your {TERMINAL_G:.1%}")

    print("\nFootball field:")
    football_field({"DCF (sens. grid)": (min(flat), max(flat)), "EV/EBITDA comps": (ev_c["low"], ev_c["high"]),
                    "P/E comps": (pe_c["low"], pe_c["high"]), "52-week range": RANGE_52W}, price=PRICE)

    tgt = (base["per_share"] + ev_c["median"] + pe_c["median"]) / 3
    up = tgt / PRICE - 1
    rec = "BUY / LONG" if up > 0.10 else "SELL / SHORT" if up < -0.10 else "HOLD / NEUTRAL"
    print(f"""
=== PITCH OUTLINE (60-90 seconds) ===
1. Recommendation: {rec} {COMPANY}, target {tgt:.2f} ({up:+.0%} vs {PRICE}).
2. Valuation: DCF {base['per_share']:.2f} (WACC {w:.1%}, g {TERMINAL_G:.1%}; terminal value {base['tv_pct']:.0%} of EV),
   EV/EBITDA comps median {ev_c['median']:.2f}, P/E comps median {pe_c['median']:.2f}. Target = average of the three.
3. What the market believes: price implies {('%.1f%%' % (ig * 100)) if ig is not None else 'n/a'} perpetual growth; we think {TERMINAL_G:.1%} because <reason>.
4. Thesis (2-3 drivers): <revenue driver>, <margin driver>, <capital/balance-sheet point>.
5. Catalysts & timing: <earnings date / product / regulation>.
6. Risks & what would change our mind: <top 2 risks>; value at WACC +1% / g -0.5% is {val(w + 0.01, TERMINAL_G - 0.005):.2f}.
""")

if __name__ == "__main__":
    main()
