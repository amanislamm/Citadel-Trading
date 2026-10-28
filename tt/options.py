"""Black-Scholes, greeks, implied vol, binomial tree, digitals. Stdlib only."""
import math

__all__ = ["bs_price", "bs_greeks", "implied_vol", "binomial_price", "digital_price",
           "straddle_approx", "delta_hedge_qty", "expected_move"]

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

def implied_vol(price, S, K, T, r, kind="call", q=0.0):
    lo, hi = 1e-4, 5.0
    for _ in range(200):
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
