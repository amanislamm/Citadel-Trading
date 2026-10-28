"""Time-series signals: EMA, z-scores, pairs trading, regression, momentum/mean-reversion."""
import math, statistics
from collections import deque

__all__ = ["EMA", "RollingZ", "ols", "hedge_ratio", "pairs_signal", "corr",
           "returns", "realized_vol", "half_life", "momentum"]

class EMA:
    def __init__(self, alpha=0.1): self.a = alpha; self.v = None
    def update(self, x):
        self.v = x if self.v is None else self.a * x + (1 - self.a) * self.v
        return self.v

class RollingZ:
    def __init__(self, n=50): self.q = deque(maxlen=n)
    def update(self, x):
        self.q.append(x)
        if len(self.q) < 3: return 0.0
        m = statistics.mean(self.q); s = statistics.pstdev(self.q)
        return 0.0 if s == 0 else (x - m) / s

def ols(x, y):
    """y = a + b x. Returns (a, b, r2)."""
    mx, my = statistics.mean(x), statistics.mean(y)
    sxx = sum((xi - mx) ** 2 for xi in x); sxy = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    b = sxy / sxx if sxx else 0.0; a = my - b * mx
    ss_res = sum((yi - a - b * xi) ** 2 for xi, yi in zip(x, y)); ss_tot = sum((yi - my) ** 2 for yi in y)
    return a, b, (1 - ss_res / ss_tot) if ss_tot else 0.0

def hedge_ratio(px_a, px_b):
    """Units of B to short per unit of A long."""
    return ols(px_b, px_a)[1]

def pairs_signal(px_a, px_b, entry=2.0, exit=0.5):
    """Spread = A - beta*B. z>entry: SELL A/BUY B. z<-entry: BUY A/SELL B. |z|<exit: flatten."""
    a, b, _ = ols(px_b, px_a)
    spread = [pa - b * pb for pa, pb in zip(px_a, px_b)]
    m, s = statistics.mean(spread), statistics.pstdev(spread)
    z = (spread[-1] - m) / s if s else 0.0
    sig = "SELL A / BUY B" if z > entry else "BUY A / SELL B" if z < -entry else "FLATTEN" if abs(z) < exit else "HOLD"
    return {"beta": b, "z": z, "signal": sig}

def corr(x, y):
    mx, my = statistics.mean(x), statistics.mean(y)
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    den = math.sqrt(sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in y))
    return num / den if den else 0.0

def returns(px):
    return [px[i] / px[i - 1] - 1 for i in range(1, len(px))]

def realized_vol(px, periods_per_year=252):
    r = [math.log(px[i] / px[i - 1]) for i in range(1, len(px))]
    return statistics.pstdev(r) * math.sqrt(periods_per_year) if len(r) > 1 else 0.0

def half_life(series):
    """Mean-reversion half-life via AR(1) on deltas. Small = fast reversion."""
    lag = series[:-1]; d = [series[i] - series[i - 1] for i in range(1, len(series))]
    _, b, _ = ols(lag, d)
    return -math.log(2) / b if b < 0 else float("inf")

def momentum(px, lookback=10):
    return 0.0 if len(px) <= lookback else px[-1] / px[-1 - lookback] - 1
