"""Local limit order book + microstructure features."""
import bisect

__all__ = ["OrderBook", "microprice", "imbalance", "vwap", "impact_cost"]

class OrderBook:
    """Price-level book. update(side, px, qty) with qty=0 deletes the level."""
    def __init__(self):
        self.bids = {}; self.asks = {}

    def update(self, side, px, qty):
        book = self.bids if side in ("bid", "buy", "b") else self.asks
        if qty <= 0: book.pop(px, None)
        else: book[px] = qty

    def snapshot(self, bids, asks):
        self.bids = dict(bids); self.asks = dict(asks)

    def best_bid(self): return max(self.bids) if self.bids else None
    def best_ask(self): return min(self.asks) if self.asks else None

    def mid(self):
        b, a = self.best_bid(), self.best_ask()
        return None if b is None or a is None else (b + a) / 2

    def spread(self):
        b, a = self.best_bid(), self.best_ask()
        return None if b is None or a is None else a - b

    def depth(self, side, levels=5):
        book = self.bids if side == "bid" else self.asks
        keys = sorted(book, reverse=(side == "bid"))[:levels]
        return [(k, book[k]) for k in keys]

    def microprice(self):
        b, a = self.best_bid(), self.best_ask()
        if b is None or a is None: return None
        return microprice(b, a, self.bids[b], self.asks[a])

    def imbalance(self, levels=1):
        bq = sum(q for _, q in self.depth("bid", levels)); aq = sum(q for _, q in self.depth("ask", levels))
        return imbalance(bq, aq)

    def sweep_cost(self, side, qty):
        """Avg price to market-buy (side='buy') or market-sell qty."""
        levels = self.depth("ask" if side == "buy" else "bid", 10_000)
        return impact_cost(levels, qty)

def microprice(bid, ask, bid_sz, ask_sz):
    """Size-weighted mid: leans toward the side about to be eaten."""
    return (bid * ask_sz + ask * bid_sz) / (bid_sz + ask_sz)

def imbalance(bid_sz, ask_sz):
    """-1 (all asks) .. +1 (all bids). >0 tends to predict up-ticks."""
    t = bid_sz + ask_sz
    return 0.0 if t == 0 else (bid_sz - ask_sz) / t

def vwap(trades):
    """trades: [(px, qty), ...]"""
    q = sum(t[1] for t in trades)
    return sum(p * s for p, s in trades) / q if q else None

def impact_cost(levels, qty):
    """levels: [(px, qty), ...] best-first. Returns (avg_px, filled)."""
    rem, cost = qty, 0.0
    for px, sz in levels:
        take = min(rem, sz); cost += take * px; rem -= take
        if rem <= 0: break
    filled = qty - rem
    return (cost / filled if filled else None), filled
