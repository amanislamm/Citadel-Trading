"""Fundamental Analyst Challenge helpers: valuation + news impact."""
__all__ = ["dcf", "gordon_growth", "pe_value", "ev_ebitda_value", "earnings_surprise_move",
           "news_fair_update", "wacc", "capm", "npv", "irr", "eps_from_guidance"]

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
