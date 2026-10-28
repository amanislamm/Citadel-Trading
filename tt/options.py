"""Black-Scholes, greeks, implied vol, binomial tree, digitals. Stdlib only."""
import math

__all__ = ["bs_price", "bs_greeks", "implied_vol", "binomial_price", "digital_price",
           "straddle_approx", "delta_hedge_qty", "expected_move", "smile_scan", "portfolio_greeks"]

N = lambda x: 0.5 * (1 + math.erf(x / math.sqrt(2)))
n = lambda x: math.exp(-x * x / 2) / math.sqrt(2 * math.pi)

def _d1d2(S, K, T, r, sigma, q=0.0):
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    return d1, d1 - sigma * math.sqrt(T)

def bs_price(S, K, T, r, sigma, kind="call", q=0.0):
    if T <= 0 or sigma <= 0:
        return max(0.0, S - K) if kind == "call" else max(0.0, K - S)
    d1, d2 = _d1d2(S, K, T, r, sigma, q)
    if kind == "call":
        return S * math.exp(-q * T) * N(d1) - K * math.exp(-r * T) * N(d2)
    return K * math.exp(-r * T) * N(-d2) - S * math.exp(-q * T) * N(-d1)

def bs_greeks(S, K, T, r, sigma, kind="call", q=0.0):
    if T <= 0 or sigma <= 0:                                  # expired: delta is 0/±1, rest 0
        itm = S > K if kind == "call" else S < K
        return {"delta": (1.0 if kind == "call" else -1.0) if itm else 0.0,
                "gamma": 0.0, "vega": 0.0, "theta_per_day": 0.0, "rho": 0.0}
    d1, d2 = _d1d2(S, K, T, r, sigma, q)
    disc_q, disc_r = math.exp(-q * T), math.exp(-r * T)
    delta = disc_q * N(d1) if kind == "call" else disc_q * (N(d1) - 1)
    gamma = disc_q * n(d1) / (S * sigma * math.sqrt(T))
    vega = S * disc_q * n(d1) * math.sqrt(T) / 100           # per 1 vol point
    if kind == "call":
        theta = (-S * disc_q * n(d1) * sigma / (2 * math.sqrt(T)) - r * K * disc_r * N(d2) + q * S * disc_q * N(d1)) / 365
        rho = K * T * disc_r * N(d2) / 100
    else:
        theta = (-S * disc_q * n(d1) * sigma / (2 * math.sqrt(T)) + r * K * disc_r * N(-d2) - q * S * disc_q * N(-d1)) / 365
        rho = -K * T * disc_r * N(-d2) / 100
    return {"delta": delta, "gamma": gamma, "vega": vega, "theta_per_day": theta, "rho": rho}

def implied_vol(price, S, K, T, r, kind="call", q=0.0, tol=1e-8):
    """Newton (fast) with bisection fallback. Returns None if price is outside no-arb bounds."""
    lo_b = max(0.0, S * math.exp(-q * T) - K * math.exp(-r * T)) if kind == "call" else \
           max(0.0, K * math.exp(-r * T) - S * math.exp(-q * T))
    hi_b = S * math.exp(-q * T) if kind == "call" else K * math.exp(-r * T)
    if T <= 0 or price < lo_b - 1e-12 or price > hi_b + 1e-12:
        return None
    sig = 0.3
    for _ in range(20):
        diff = bs_price(S, K, T, r, sig, kind, q) - price
        if abs(diff) < tol: return sig
        d1 = _d1d2(S, K, T, r, sig, q)[0]
        v = S * math.exp(-q * T) * n(d1) * math.sqrt(T)
        if v < 1e-8: break
        sig -= diff / v
        if not 1e-4 < sig < 5.0: break
    lo, hi = 1e-4, 5.0
    for _ in range(100):
        m = (lo + hi) / 2
        if bs_price(S, K, T, r, m, kind, q) < price: lo = m
        else: hi = m
    return (lo + hi) / 2

def binomial_price(S, K, T, r, sigma, kind="call", steps=200, american=False, q=0.0):
    dt = T / steps; u = math.exp(sigma * math.sqrt(dt)); d = 1 / u
    p = (math.exp((r - q) * dt) - d) / (u - d); disc = math.exp(-r * dt)
    pay = (lambda s: max(0.0, s - K)) if kind == "call" else (lambda s: max(0.0, K - s))
    vals = [pay(S * u ** j * d ** (steps - j)) for j in range(steps + 1)]
    for i in range(steps - 1, -1, -1):
        vals = [disc * (p * vals[j + 1] + (1 - p) * vals[j]) for j in range(i + 1)]
        if american:
            vals = [max(v, pay(S * u ** j * d ** (i - j))) for j, v in enumerate(vals)]
    return vals[0]

def digital_price(S, K, T, r, sigma, kind="call", payout=1.0):
    """Cash-or-nothing: pays `payout` if S_T > K (call)."""
    _, d2 = _d1d2(S, K, T, r, sigma)
    return payout * math.exp(-r * T) * (N(d2) if kind == "call" else N(-d2))

def straddle_approx(S, T, sigma):
    """ATM straddle ≈ 0.8 * S * sigma * sqrt(T). ATM call ≈ 0.4 * S * sigma * sqrt(T)."""
    return 0.8 * S * sigma * math.sqrt(T)

def expected_move(S, sigma, T):
    """1-std move over T years."""
    return S * sigma * math.sqrt(T)

def delta_hedge_qty(option_qty, delta, multiplier=1):
    """Shares to trade to be delta-neutral (negative = sell)."""
    return -option_qty * delta * multiplier

def smile_scan(S, T, r, quotes, kind="call", q=0.0, z_thresh=1.5):
    """quotes: {strike: price}. Fits IV vs strike with a quadratic (smile) and flags outliers.
    Returns [(K, iv, fitted_iv, resid_vol_pts, flag)], flag in {"RICH","CHEAP",""}."""
    pts = [(K, implied_vol(px, S, K, T, r, kind, q)) for K, px in sorted(quotes.items())]
    pts = [(K, v) for K, v in pts if v is not None]
    if len(pts) < 4:
        return [(K, v, None, None, "") for K, v in pts]
    out = []
    for i, (K, v) in enumerate(pts):                    # leave-one-out so the outlier can't hide
        rest = pts[:i] + pts[i + 1:]
        fit = _quadfit([k for k, _ in rest], [iv for _, iv in rest])
        out.append((K, v, fit(K), (v - fit(K)) * 100))
    res = [o[3] for o in out]
    sd = (sum(x * x for x in res) / len(res)) ** 0.5 or 1e-9
    med = sorted(abs(x) for x in res)[len(res) // 2] or 1e-9
    scale = min(sd, 1.4826 * med * 1.5)                  # robust-ish scale
    return [(K, v, f, rv, "RICH" if rv > z_thresh * scale else "CHEAP" if rv < -z_thresh * scale else "")
            for K, v, f, rv in out]

def _quadfit(x, y):
    """Least-squares y = a + b x + c x^2 (normal equations, 3x3 Cramer)."""
    m = sum(x) / len(x); xs = [xi - m for xi in x]           # centre for conditioning
    S = [sum(xi ** k for xi in xs) for k in range(5)]
    T = [sum(yi * xi ** k for xi, yi in zip(xs, y)) for k in range(3)]
    A = [[S[0], S[1], S[2]], [S[1], S[2], S[3]], [S[2], S[3], S[4]]]
    det = lambda M: (M[0][0] * (M[1][1] * M[2][2] - M[1][2] * M[2][1]) - M[0][1] * (M[1][0] * M[2][2] - M[1][2] * M[2][0])
                     + M[0][2] * (M[1][0] * M[2][1] - M[1][1] * M[2][0]))
    D = det(A)
    if abs(D) < 1e-12:                                        # degenerate -> flat line at mean
        mu = sum(y) / len(y); return lambda K: mu
    coef = []
    for j in range(3):
        M = [row[:] for row in A]
        for i in range(3): M[i][j] = T[i]
        coef.append(det(M) / D)
    a, b, c = coef
    return lambda K: a + b * (K - m) + c * (K - m) ** 2

def portfolio_greeks(S, r, legs, q=0.0):
    """legs: [(qty, K, T, sigma, kind), ...] (qty<0 = short). Shares: (qty, None, None, None, 'stock').
    Returns summed delta/gamma/vega/theta and total value."""
    tot = {"value": 0.0, "delta": 0.0, "gamma": 0.0, "vega": 0.0, "theta_per_day": 0.0}
    for qty, K, T, sig, kind in legs:
        if kind == "stock":
            tot["value"] += qty * S; tot["delta"] += qty; continue
        g = bs_greeks(S, K, T, r, sig, kind, q)
        tot["value"] += qty * bs_price(S, K, T, r, sig, kind, q)
        for k in ("delta", "gamma", "vega", "theta_per_day"): tot[k] += qty * g[k]
    return tot
