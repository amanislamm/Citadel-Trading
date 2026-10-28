"""Turning fair value into quotes and sizes."""
import math

__all__ = ["quote", "edge", "kelly_size", "kelly_binary", "spread_for_adverse_selection",
           "should_trade", "glosten_milgrom_update"]

def quote(fair, std, position=0, max_pos=100, width_k=0.5, skew_k=1.0, tick=1.0, min_width=None):
    """Bid/ask around fair.
    width = width_k*std (wide when uncertain, tighten as info arrives).
    skew  = shift both quotes AGAINST inventory (long -> lower quotes -> you sell more)."""
    half = max(tick if min_width is None else min_width / 2, width_k * std)
    mid = fair - skew_k * half * (position / max_pos if max_pos else 0)
    r = lambda x: round(x / tick) * tick
    bid, ask = r(mid - half), r(mid + half)
    if ask <= bid:
        ask = bid + tick
    return bid, ask

def edge(fair, price, side):
    """Expected profit per unit. side in {'buy','sell'}."""
    return fair - price if side == "buy" else price - fair

def kelly_size(edge_per_unit, std, bankroll, frac=0.25):
    """Fractional Kelly (normal approx): units = frac * bankroll * edge / var."""
    return 0 if std <= 0 else frac * bankroll * edge_per_unit / std ** 2

def kelly_binary(p, odds):
    """Binary bet paying `odds`:1 with win prob p -> fraction of bankroll."""
    return max(0.0, (p * (odds + 1) - 1) / odds)

def spread_for_adverse_selection(p_informed, info_move):
    """Rough half-spread to break even vs informed flow: p_informed * expected informed move."""
    return p_informed * info_move

def should_trade(fair, std, bid, ask, threshold_k=0.25):
    """Cross the spread only if edge > threshold_k * std."""
    if ask < fair - threshold_k * std:
        return "BUY", fair - ask
    if bid > fair + threshold_k * std:
        return "SELL", bid - fair
    return "PASS", 0.0

def glosten_milgrom_update(fair, std, trade_px, side, trust=0.3):
    """Counterparty traded -> shift fair toward their price; shrink std slightly."""
    return fair + trust * (trade_px - fair), std * math.sqrt(1 - trust / 2)
