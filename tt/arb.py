"""Arbitrage / consistency checks. Designers love to plant these."""
import math

__all__ = ["etf_arb", "put_call_parity", "box_spread", "triangular_fx", "crossed",
           "sum_of_parts", "conversion_arb", "call_spread_bounds", "butterfly_check",
           "futures_fair", "binary_ladder_check", "tender_eval"]

def etf_arb(etf_bid, etf_ask, comp_quotes, weights, fee=0.0, conv_fee=0.0):
    """comp_quotes: [(bid, ask), ...]. Profit per ETF unit after fees."""
    b_ask = sum(w * a for w, (b, a) in zip(weights, comp_quotes))
    b_bid = sum(w * b for w, (b, a) in zip(weights, comp_quotes))
    out = []
    if etf_bid - b_ask > fee + conv_fee:
        out.append(("SELL ETF, BUY basket (create)", etf_bid - b_ask - fee - conv_fee))
    if b_bid - etf_ask > fee + conv_fee:
        out.append(("BUY ETF, SELL basket (redeem)", b_bid - etf_ask - fee - conv_fee))
    return out or [("no arb", 0.0)]

def put_call_parity(C, P, S, K, r=0.0, T=0.0, q=0.0):
    """Returns (C-P) - (S e^{-qT} - K e^{-rT}). >0 => calls rich: sell call, buy put, buy stock."""
    return (C - P) - (S * math.exp(-q * T) - K * math.exp(-r * T))

def conversion_arb(call_bid, call_ask, put_bid, put_ask, S_bid, S_ask, K, r=0.0, T=0.0):
    """Tradeable version of PCP using bid/ask."""
    pv = K * math.exp(-r * T)
    conv = call_bid - put_ask - S_ask + pv       # sell C, buy P, buy S
    rev = -call_ask + put_bid + S_bid - pv        # buy C, sell P, short S
    return {"conversion (sell C, buy P, buy S)": conv, "reversal (buy C, sell P, sell S)": rev}

def box_spread(c1, c2, p1, p2, K1, K2, r=0.0, T=0.0):
    """Long box = (C(K1)-C(K2)) + (P(K2)-P(K1)) should = (K2-K1)e^{-rT}. Returns mispricing."""
    return (c1 - c2 + p2 - p1) - (K2 - K1) * math.exp(-r * T)

def call_spread_bounds(cK1, cK2, K1, K2):
    """0 <= C(K1)-C(K2) <= K2-K1 for K1<K2."""
    d = cK1 - cK2
    if d < 0: return f"VIOLATION: buy C({K1}) sell C({K2}), free {-d}"
    if d > K2 - K1: return f"VIOLATION: sell C({K1}) buy C({K2}), free {d - (K2 - K1)}"
    return "ok"

def butterfly_check(c_lo, c_mid, c_hi):
    """Equally spaced strikes: c_lo - 2c_mid + c_hi >= 0 (convexity)."""
    v = c_lo - 2 * c_mid + c_hi
    return "ok" if v >= 0 else f"VIOLATION: buy butterfly, get paid {-v}"

def triangular_fx(ab, bc, ac):
    """Rates: A->B, B->C, A->C. Returns profit per 1 A of going A->B->C->A."""
    return ab * bc / ac - 1

def crossed(quotes):
    """quotes: {venue_or_player: (bid, ask)}. Finds best bid > best ask across all."""
    bb = max(quotes.items(), key=lambda kv: kv[1][0])
    ba = min(quotes.items(), key=lambda kv: kv[1][1])
    if bb[1][0] > ba[1][1]:
        return f"ARB: buy @ {ba[0]} {ba[1][1]}, sell @ {bb[0]} {bb[1][0]}, edge {bb[1][0]-ba[1][1]}"
    return "no cross"

def sum_of_parts(total_quote, part_fairs):
    """Market on A+B+C vs fair of parts."""
    f = sum(part_fairs); b, a = total_quote
    if a < f: return f"BUY total @ {a} (parts fair {f})"
    if b > f: return f"SELL total @ {b} (parts fair {f})"
    return "fair"

def futures_fair(S, r, T, q=0.0, carry=0.0):
    return S * math.exp((r - q + carry) * T)

def binary_ladder_check(probs):
    """Binary contracts on mutually exclusive, exhaustive outcomes priced as probabilities
    (0-1 or 0-100 scale, auto-detected). They must sum to 1 (or 100).
    Pass mids to spot it; pass asks to check 'buy all' and bids to check 'sell all' tradeably."""
    s = sum(probs)
    full = 100.0 if max(probs) > 1 else 1.0
    tol = 1e-4 * full
    return s, ("sell all (sum > %g)" % full if s > full + tol else
               "buy all (sum < %g)" % full if s < full - tol else "ok")

def tender_eval(action, qty, price, book, fee_per_share=0.0, min_edge=0.0, fair=None):
    """Should you accept a tender (client block trade)?
    action: 'buy' = you BUY qty at price from the client (then sell it into the bids),
            'sell' = you SELL qty at price (then buy it back from the asks).
    book: {'bids': [(px, qty), ...], 'asks': [...]} best first (RIT.book(sym) gives this).
    Unwind is priced by sweeping visible depth; any unfilled part is marked at `fair` (or the
    worst level swept) and flagged, because you'd have to work it over time.
    Returns dict with profit, per-share edge, filled, verdict."""
    levels = book["bids"] if action == "buy" else book["asks"]
    rem, cost = qty, 0.0
    for px, sz in levels:
        take = min(rem, sz); cost += take * px; rem -= take
        if rem <= 0: break
    filled = qty - rem
    worst = levels[-1][0] if levels else (fair if fair is not None else price)   # all depth used if rem > 0
    rest_px = fair if fair is not None else worst
    unwind = cost + rem * rest_px
    sgn = 1 if action == "buy" else -1
    profit = sgn * (unwind - qty * price) - fee_per_share * qty * 2
    edge = profit / qty if qty else 0.0
    verdict = "ACCEPT" if edge > min_edge else "DECLINE"
    if rem > 0 and verdict == "ACCEPT": verdict = "ACCEPT (only %g of %g unwindable now; work the rest)" % (filled, qty)
    return {"profit": profit, "edge_per_share": edge, "unwind_avg": unwind / qty if qty else None,
            "filled_now": filled, "verdict": verdict}
