"""Fair value + uncertainty for 'make me a market on X' games."""
import itertools, math, random, statistics
from collections import Counter
from fractions import Fraction

__all__ = ["dice_dist", "stats", "card_deck", "card_draw_dist", "mc_dist", "mc_mean",
           "sum_of_iid", "UNIFORM_DIE", "CARD_1_13", "condition", "reveal_sum",
           "expected_max_uniform", "expected_min_uniform", "order_stat_uniform",
           "coupon_collector", "geometric_mean_trials", "binom_pmf", "binom_dist",
           "poisson_pmf", "hypergeom_pmf", "normal_cdf", "normal_ppf", "prob_between",
           "ev", "bayes", "expected_rolls_until", "conf_interval", "fermi"]

def dice_dist(n_dice=2, sides=6, func=sum):
    """Exact distribution of func(roll) over n fair dice. func: sum, max, min, lambda r: ..."""
    c = Counter(func(r) for r in itertools.product(range(1, sides + 1), repeat=n_dice))
    tot = sides ** n_dice
    return {k: v / tot for k, v in sorted(c.items())}

def stats(dist):
    """mean, std, percentiles of a {value: prob} dict."""
    mu = sum(k * p for k, p in dist.items())
    sd = math.sqrt(max(0.0, sum(p * (k - mu) ** 2 for k, p in dist.items())))
    qs, acc, out = [0.05, 0.10, 0.25, 0.5, 0.75, 0.90, 0.95], 0.0, {}
    for k, p in sorted(dist.items()):
        acc += p
        for q in qs:
            if q not in out and acc >= q - 1e-12:
                out[q] = k
    return {"mean": mu, "std": sd, **{f"p{int(q*100)}": v for q, v in out.items()}}

def card_deck(values=range(1, 14), suits=4):
    """Default: A=1..K=13, 4 suits. Pass values=[...] for custom decks."""
    return [v for v in values for _ in range(suits)]

def card_draw_dist(n_draw, deck=None, func=sum, exact_limit=3_000_000):
    """Draw without replacement. Exact if small, else Monte Carlo."""
    deck = list(deck) if deck is not None else card_deck()
    if math.comb(len(deck), n_draw) > exact_limit:
        return mc_dist(lambda: func(random.sample(deck, n_draw)))
    c = Counter(func(h) for h in itertools.combinations(deck, n_draw))
    tot = sum(c.values())
    return {k: v / tot for k, v in sorted(c.items())}

def mc_dist(sampler, n=200_000):
    """Monte Carlo any game: sampler() returns one outcome."""
    c = Counter(sampler() for _ in range(n))
    return {k: v / n for k, v in sorted(c.items())}

def mc_mean(sampler, n=200_000):
    xs = [sampler() for _ in range(n)]
    return statistics.mean(xs), statistics.pstdev(xs)

def sum_of_iid(mean, var, n):
    """CLT: sum of n iid -> (mean, std)."""
    return n * mean, math.sqrt(n * var)

UNIFORM_DIE = (3.5, 35 / 12)
CARD_1_13 = (7.0, 14.0)

def condition(sampler, observed_fn, target_fn, n=300_000):
    """E[target | observed] by rejection sampling -> (mean, std, accepted_count)."""
    vals = []
    for _ in range(n):
        w = sampler()
        if observed_fn(w):
            vals.append(target_fn(w))
    if not vals:
        return None
    return statistics.mean(vals), (statistics.pstdev(vals) if len(vals) > 1 else 0.0), len(vals)

def reveal_sum(revealed, n_unknown, per_unit=UNIFORM_DIE):
    """Sum game with some parts revealed: (fair, std). For cards w/o replacement use condition()."""
    m, v = per_unit
    return sum(revealed) + n_unknown * m, math.sqrt(n_unknown * v)

# Continuous uniform order statistics on [0,1]: E[X_(k)] = k/(n+1)
def expected_max_uniform(n, lo=0.0, hi=1.0):
    return lo + (hi - lo) * n / (n + 1)

def expected_min_uniform(n, lo=0.0, hi=1.0):
    return lo + (hi - lo) / (n + 1)

def order_stat_uniform(k, n, lo=0.0, hi=1.0):
    return lo + (hi - lo) * k / (n + 1)

def coupon_collector(n):
    """Expected draws to see all n types: n * H_n."""
    return n * sum(1 / i for i in range(1, n + 1))

def geometric_mean_trials(p):
    """Expected trials until first success."""
    return 1 / p

def expected_rolls_until(pattern, sides=6, n=100_000):
    """MC: expected rolls until a sequence appears (e.g. (6,6) -> 42, (5,6) -> 36)."""
    k = len(pattern); tot = 0
    for _ in range(n):
        hist = []; c = 0
        while True:
            c += 1; hist.append(random.randint(1, sides))
            if tuple(hist[-k:]) == tuple(pattern):
                break
        tot += c
    return tot / n

def binom_pmf(k, n, p):
    return math.comb(n, k) * p ** k * (1 - p) ** (n - k)

def binom_dist(n, p):
    return {k: binom_pmf(k, n, p) for k in range(n + 1)}

def poisson_pmf(k, lam):
    return math.exp(-lam) * lam ** k / math.factorial(k)

def hypergeom_pmf(k, N, K, n):
    """P(k successes in n draws from N with K successes)."""
    return math.comb(K, k) * math.comb(N - K, n - k) / math.comb(N, n)

def normal_cdf(x, mu=0.0, sd=1.0):
    return 0.5 * (1 + math.erf((x - mu) / (sd * math.sqrt(2))))

def normal_ppf(p, mu=0.0, sd=1.0):
    """Inverse normal CDF via bisection (no scipy needed)."""
    lo, hi = -12.0, 12.0
    for _ in range(100):
        m = (lo + hi) / 2
        if normal_cdf(m) < p: lo = m
        else: hi = m
    return mu + sd * (lo + hi) / 2

def prob_between(a, b, mu, sd):
    return normal_cdf(b, mu, sd) - normal_cdf(a, mu, sd)

def ev(outcomes):
    """outcomes: list of (prob, payoff) -> expected value."""
    return sum(p * x for p, x in outcomes)

def bayes(prior, likelihoods):
    """prior: {h: p}, likelihoods: {h: P(data|h)} -> posterior."""
    post = {h: prior[h] * likelihoods.get(h, 0) for h in prior}
    z = sum(post.values())
    return {h: v / z for h, v in post.items()} if z else prior

def conf_interval(mean, sd, conf=0.9):
    z = normal_ppf(0.5 + conf / 2)
    return mean - z * sd, mean + z * sd

def fermi(low, high):
    """Estimation markets ('how many X in Y'): use geometric mean of your 90% bounds.
    Returns (fair, rough_std_in_log_space_multiplier)."""
    g = math.sqrt(low * high)
    return g, math.sqrt(high / low) ** (1 / 1.645)
