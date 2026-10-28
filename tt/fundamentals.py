"""Fundamental Analyst Challenge helpers: valuation + news impact."""
__all__ = ["dcf", "gordon_growth", "pe_value", "ev_ebitda_value", "earnings_surprise_move",
           "news_fair_update", "wacc", "capm", "npv", "irr", "eps_from_guidance",
           "dcf_build", "sensitivity", "print_grid", "comps_value", "implied_terminal_growth",
           "implied_wacc", "football_field", "unlever_beta", "relever_beta",
           "merger_value", "implied_deal_prob", "stock_offer_value"]

def _seq(x, n):
    """Scalar -> [x]*n; short list -> padded with its last value."""
    if isinstance(x, (int, float)): return [float(x)] * n
    x = list(x); return (x + [x[-1]] * n)[:n]

def npv(rate, cashflows, t0=0):
    return sum(cf / (1 + rate) ** (i + t0) for i, cf in enumerate(cashflows))

def irr(cashflows, lo=-0.99, hi=10.0):
    f = lambda r: sum(cf / (1 + r) ** i for i, cf in enumerate(cashflows))
    for _ in range(200):
        m = (lo + hi) / 2
        if f(lo) * f(m) <= 0: hi = m
        else: lo = m
    return (lo + hi) / 2

def gordon_growth(next_cf, r, g):
    """Terminal value = CF_{t+1} / (r - g)."""
    assert r > g, "discount rate must exceed growth"
    return next_cf / (r - g)

def dcf(fcfs, r, g_terminal, net_debt=0.0, shares=1.0):
    """fcfs: projected free cash flows years 1..N. Returns per-share equity value."""
    pv = sum(cf / (1 + r) ** (i + 1) for i, cf in enumerate(fcfs))
    tv = gordon_growth(fcfs[-1] * (1 + g_terminal), r, g_terminal) / (1 + r) ** len(fcfs)
    return (pv + tv - net_debt) / shares

def capm(rf, beta, mrp):
    return rf + beta * mrp

def wacc(E, D, re, rd, tax):
    V = E + D
    return E / V * re + D / V * rd * (1 - tax)

def pe_value(eps, pe): return eps * pe

def ev_ebitda_value(ebitda, multiple, net_debt, shares):
    return (ebitda * multiple - net_debt) / shares

def eps_from_guidance(revenue, margin, shares, tax=0.21):
    return revenue * margin * (1 - tax) / shares

def earnings_surprise_move(actual, consensus, price, pe=None, sensitivity=1.0):
    """Crude: price moves ~ sensitivity * % surprise (or re-rate at constant P/E)."""
    surprise = (actual - consensus) / abs(consensus)
    if pe is not None:
        return price + pe * (actual - consensus) * sensitivity
    return price * (1 + sensitivity * surprise)

def news_fair_update(fair, impact_pct, prob_true=1.0, already_priced=0.0):
    """Shift fair by impact * P(true) * (1 - fraction already priced in)."""
    return fair * (1 + impact_pct * prob_true * (1 - already_priced))

def dcf_build(revenue0, growth, ebit_margin, wacc, g, years=5, tax=0.25, da_pct=0.04, capex_pct=0.05,
              nwc_pct=0.10, net_debt=0.0, shares=1.0, mid_year=False, exit_multiple=None, verbose=True):
    """Unlevered FCF DCF from a handful of drivers (each can be a number or a per-year list).
    FCF = EBIT(1-t) + D&A - Capex - dNWC, with D&A/Capex as % of revenue and NWC as % of revenue.
    Terminal: Gordon growth on next-year FCF, or exit_multiple x final-year EBITDA if given.
    Returns dict: per_share, ev, equity, pv_fcf, pv_tv, tv_pct, rows."""
    gr, mg = _seq(growth, years), _seq(ebit_margin, years)
    rev_prev, nwc_prev, rows, pv = revenue0, revenue0 * nwc_pct, [], 0.0
    for t in range(1, years + 1):
        rev = rev_prev * (1 + gr[t - 1]); ebit = rev * mg[t - 1]
        da, capex, nwc = rev * da_pct, rev * capex_pct, rev * nwc_pct
        fcf = ebit * (1 - tax) + da - capex - (nwc - nwc_prev)
        df = 1 / (1 + wacc) ** (t - 0.5 if mid_year else t); pv += fcf * df
        rows.append({"year": t, "revenue": rev, "ebit": ebit, "fcf": fcf, "pv": fcf * df})
        rev_prev, nwc_prev = rev, nwc
    last = rows[-1]
    if exit_multiple is not None:
        tv = exit_multiple * (last["ebit"] + last["revenue"] * da_pct)
    else:
        assert wacc > g, "WACC must exceed terminal growth"
        tv = last["fcf"] * (1 + g) / (wacc - g)
    pv_tv = tv / (1 + wacc) ** (years - 0.5 if mid_year else years)
    ev = pv + pv_tv; eq = ev - net_debt
    out = {"per_share": eq / shares, "ev": ev, "equity": eq, "pv_fcf": pv, "pv_tv": pv_tv,
           "tv_pct": pv_tv / ev if ev else None, "rows": rows}
    if verbose:
        print(f"{'yr':>3}{'revenue':>12}{'ebit':>11}{'fcf':>11}{'pv':>11}")
        for r in rows: print(f"{r['year']:>3}{r['revenue']:>12.1f}{r['ebit']:>11.1f}{r['fcf']:>11.1f}{r['pv']:>11.1f}")
        print(f"PV(FCF) {pv:.1f} + PV(TV) {pv_tv:.1f} = EV {ev:.1f}  (TV is {out['tv_pct']:.0%} of EV)"
              f" - net debt {net_debt:.1f} = equity {eq:.1f}  ->  {out['per_share']:.2f}/share")
        if out["tv_pct"] and out["tv_pct"] > 0.8: print("  note: >80% of value is terminal: the answer is mostly your g / WACC choice")
    return out

def sensitivity(f, row_vals, col_vals):
    """grid[i][j] = f(row_vals[i], col_vals[j]). E.g. rows=WACC, cols=terminal g."""
    return [[f(r, c) for c in col_vals] for r in row_vals]

def print_grid(grid, row_vals, col_vals, row_name="wacc", col_name="g", fmt="{:>9.2f}", pct=True, mark=None):
    """Print a sensitivity table; mark=(price) highlights cells above market with '*'."""
    lab = (lambda v: f"{v:.1%}") if pct else (lambda v: f"{v:g}")
    print(f"{row_name + ' / ' + col_name:>12}" + "".join(f"{lab(c):>10}" for c in col_vals))
    for r, row in zip(row_vals, grid):
        cells = "".join((fmt.format(v) + ("*" if mark is not None and v > mark else " ")) for v in row)
        print(f"{lab(r):>12}" + cells)
    if mark is not None: print(f"  * = above market price {mark}")

def comps_value(metric, peer_multiples, net_debt=0.0, shares=1.0, ev_based=True):
    """Value from peer multiples. ev_based: EV/EBITDA or EV/Sales (subtract net debt);
    else P/E-style (metric = EPS or net income, no net debt). Returns low/median/high per share."""
    ms = sorted(peer_multiples); med = ms[len(ms) // 2] if len(ms) % 2 else (ms[len(ms) // 2 - 1] + ms[len(ms) // 2]) / 2
    to_ps = (lambda m: (metric * m - net_debt) / shares) if ev_based else (lambda m: metric * m / shares)
    return {"low": to_ps(ms[0]), "median": to_ps(med), "high": to_ps(ms[-1]), "multiples": (ms[0], med, ms[-1])}

def implied_terminal_growth(price, value_fn, lo=-0.05, hi=None):
    """Reverse DCF: the g at which value_fn(g) == price. value_fn(g) -> per-share value.
    Use it in the pitch: 'the market is pricing in X% growth forever'."""
    hi = hi if hi is not None else 0.2
    f = lambda gg: value_fn(gg) - price
    if f(lo) * f(hi) > 0: return None
    for _ in range(100):
        m = (lo + hi) / 2
        if f(lo) * f(m) <= 0: hi = m
        else: lo = m
    return (lo + hi) / 2

def implied_wacc(price, value_fn, lo=0.01, hi=0.40):
    """Discount rate at which value_fn(wacc) == price (a return you'd earn buying at price)."""
    return implied_terminal_growth(price, value_fn, lo, hi)

def football_field(ranges, price=None, width=50):
    """ranges: {'DCF': (lo, hi), 'EV/EBITDA comps': (lo, hi), '52w': (lo, hi)}. ASCII chart."""
    allv = [v for r in ranges.values() for v in r] + ([price] if price else [])
    lo, hi = min(allv), max(allv); sc = lambda v: int((v - lo) / (hi - lo or 1) * (width - 1))
    for name, (a, b) in ranges.items():
        line = [" "] * width
        for i in range(sc(a), sc(b) + 1): line[i] = "="
        if price is not None: line[sc(price)] = "|"
        print(f"{name:<18} {a:>8.2f} {''.join(line)} {b:<8.2f}")
    if price is not None: print(f"{'':<18} {'':>8} {' ' * sc(price)}^ price {price}")

def unlever_beta(beta_l, de, tax):
    return beta_l / (1 + (1 - tax) * de)

def relever_beta(beta_u, de, tax):
    return beta_u * (1 + (1 - tax) * de)

def merger_value(offer, standalone, p_close):
    """Target fair value in a pending deal: p * offer + (1-p) * standalone (price if deal breaks)."""
    return p_close * offer + (1 - p_close) * standalone

def implied_deal_prob(price, offer, standalone):
    """Deal probability the market is pricing: (price - standalone) / (offer - standalone)."""
    return (price - standalone) / (offer - standalone)

def stock_offer_value(ratio, acquirer_px, cash=0.0):
    """Offer per target share for a stock (+cash) deal. Hedge: short `ratio` acquirer per target long."""
    return ratio * acquirer_px + cash
