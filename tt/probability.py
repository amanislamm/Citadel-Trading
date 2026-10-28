"""Fair value + uncertainty for 'make me a market on X' games."""
import itertools, math, random, statistics
from collections import Counter
from fractions import Fraction

__all__ = ["dice_dist", "stats", "card_deck", "card_draw_dist", "mc_dist", "mc_mean",
           "sum_of_iid", "UNIFORM_DIE", "CARD_1_13", "condition", "reveal_sum",
           "expected_max_uniform", "expected_min_uniform", "order_stat_uniform",
           "coupon_collector", "geometric_mean_trials", "binom_pmf", "binom_dist",
           "poisson_pmf", "hypergeom_pmf", "normal_cdf", "normal_ppf", "prob_between",
           "ev", "bayes", "expected_rolls_until", "conf_interval", "fermi", "Deck",
           "convolve", "dist_of_sum", "markov_expected_steps", "markov_absorb_probs",
           "pattern_wait", "pattern_race", "gamblers_ruin", "optimal_stopping", "Fraction"]

def convolve(d1, d2):
    """Distribution of X+Y for independent {value: prob} dicts."""
    out = {}
    for a, pa in d1.items():
        for b, pb in d2.items():
            out[a + b] = out.get(a + b, 0.0) + pa * pb
    return dict(sorted(out.items()))

def dist_of_sum(dists):
    """Exact distribution of a sum of independent pieces (mix dice, coins, custom games)."""
    out = {0: 1.0}
    for d in dists:
        out = convolve(out, d)
    return out

def dice_dist(n_dice=2, sides=6, func=sum):
    """Exact distribution of func(roll) over n fair dice. func: sum, max, min, lambda r: ...
    sum/max/min are computed in closed form / by convolution, so 50 dice is instant."""
    if func is sum:
        return dist_of_sum([{v: 1 / sides for v in range(1, sides + 1)}] * n_dice)
    if func in (max, min):
        cdf = lambda k: (k / sides) ** n_dice                     # P(max <= k)
        sf = lambda k: ((sides - k + 1) / sides) ** n_dice        # P(min >= k)
        if func is max:
            return {k: cdf(k) - cdf(k - 1) for k in range(1, sides + 1)}
        return {k: sf(k) - sf(k + 1) for k in range(1, sides + 1)}
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

class Deck:
    """Card counter: remove cards as they're seen, then price the rest.
    d = Deck(); d.seen(13, 13, 1); d.mean(); stats(d.draw_dist(2))"""
    def __init__(self, values=range(1, 14), suits=4):
        self.cards = card_deck(values, suits)
    def seen(self, *vals):
        for v in vals:
            try: self.cards.remove(v)
            except ValueError: print(f"!! {v} not left in deck")
        return self
    def unsee(self, *vals):
        self.cards.extend(vals); return self
    def __len__(self): return len(self.cards)
    def mean(self): return statistics.mean(self.cards) if self.cards else None
    def counts(self): return dict(sorted(Counter(self.cards).items()))
    def p(self, pred):
        """P(next card satisfies pred), e.g. d.p(lambda c: c >= 10)."""
        return sum(1 for c in self.cards if pred(c)) / len(self.cards)
    def draw_dist(self, n, func=sum): return card_draw_dist(n, self.cards, func)
    def sum_fair(self, n):
        """(mean, std) of the sum of n more draws without replacement (exact, finite-pop correction)."""
        N = len(self.cards); mu = statistics.mean(self.cards); var = statistics.pvariance(self.cards)
        fpc = (N - n) / (N - 1) if N > 1 else 0.0
        return n * mu, math.sqrt(n * var * fpc)
    def __repr__(self): return f"Deck({len(self)} left, mean {self.mean()})"

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
    if k < 0 or k > n: return 0.0
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
    """Inverse normal CDF (stdlib statistics.NormalDist, no scipy needed)."""
    return statistics.NormalDist(mu, sd).inv_cdf(p)

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

# ---------------- exact Markov chains (brainteasers) ----------------
def _solve(A, b):
    """Gauss-Jordan; exact if entries are Fractions."""
    exact = all(not isinstance(x, float) for row in A for x in row) and all(not isinstance(x, float) for x in b)
    cv = Fraction if exact else float
    n = len(A); M = [[cv(x) for x in row] + [cv(b[i])] for i, row in enumerate(A)]
    for c in range(n):
        piv = next(r for r in range(c, n) if M[r][c] != 0)
        M[c], M[piv] = M[piv], M[c]
        pv = M[c][c]; M[c] = [x / pv for x in M[c]]
        for r in range(n):
            if r != c and M[r][c] != 0:
                f = M[r][c]; M[r] = [x - f * y for x, y in zip(M[r], M[c])]
    return [M[i][n] for i in range(n)]

def _transients(trans, absorbing):
    states = set(trans) | {t for v in trans.values() for t, _ in v}
    return sorted((s for s in states if s not in absorbing), key=str)

def markov_expected_steps(trans, absorbing, start):
    """trans: {state: [(next, p), ...]}; absorbing: set. Expected steps from start to absorption.
    Use Fraction probabilities for exact answers."""
    if start in absorbing: return 0
    T = _transients(trans, absorbing); ix = {s: i for i, s in enumerate(T)}
    A = [[(1 if i == j else 0) for j in range(len(T))] for i in range(len(T))]; b = [1] * len(T)
    for s in T:
        for t, p in trans.get(s, []):
            if t in ix: A[ix[s]][ix[t]] -= p
    return _solve(A, b)[ix[start]]

def markov_absorb_probs(trans, absorbing, start):
    """{absorbing_state: P(end there)} from start."""
    if start in absorbing: return {a: (1 if a == start else 0) for a in absorbing}
    T = _transients(trans, absorbing); ix = {s: i for i, s in enumerate(T)}; out = {}
    for a in absorbing:
        A = [[(1 if i == j else 0) for j in range(len(T))] for i in range(len(T))]; b = [0] * len(T)
        for s in T:
            for t, p in trans.get(s, []):
                if t in ix: A[ix[s]][ix[t]] -= p
                elif t == a: b[ix[s]] += p
        out[a] = _solve(A, b)[ix[start]]
    return out

def _alphabet(probs):
    if probs is None: return {"H": Fraction(1, 2), "T": Fraction(1, 2)}
    if isinstance(probs, int): return {i: Fraction(1, probs) for i in range(1, probs + 1)}   # fair die
    return probs

def _suffix_state(hist, patterns):
    """Longest suffix of hist that is a prefix of some pattern."""
    for k in range(len(hist), -1, -1):
        suf = hist[len(hist) - k:]
        if any(tuple(p[:k]) == suf for p in patterns): return suf
    return ()

def _pattern_chain(patterns, probs):
    probs = _alphabet(probs); pats = [tuple(p) for p in patterns]
    trans, todo, seen = {}, [()], {()}
    while todo:
        s = todo.pop()
        if s in pats: continue
        trans[s] = []
        for sym, p in probs.items():
            nxt = s + (sym,)
            hit = next((q for q in pats if nxt[len(nxt) - len(q):] == q), None)
            t = hit if hit is not None else _suffix_state(nxt, pats)
            trans[s].append((t, p))
            if t not in seen: seen.add(t); todo.append(t)
    return trans, set(pats)

def pattern_wait(pattern, probs=None):
    """Exact expected trials until `pattern` appears. probs: None = fair coin ('H','T'),
    6 = fair die (faces 1..6), or {symbol: p}. pattern_wait('HH') -> 6; pattern_wait((6, 6), 6) -> 42."""
    trans, ab = _pattern_chain([pattern], probs)
    return markov_expected_steps(trans, ab, ())

def pattern_race(p1, p2, probs=None):
    """Penney's game: P(p1 appears before p2). pattern_race('THH', 'HHT') -> 3/4."""
    trans, ab = _pattern_chain([p1, p2], probs)
    return markov_absorb_probs(trans, ab, ())[tuple(p1)]

def gamblers_ruin(start, target, p=Fraction(1, 2)):
    """P(reach target before 0) starting at `start`, win each bet with prob p, +-1 steps.
    Returns (prob_win, expected_bets)."""
    trans = {i: [(i + 1, p), (i - 1, 1 - p)] for i in range(1, target)}
    return markov_absorb_probs(trans, {0, target}, start)[target], markov_expected_steps(trans, {0, target}, start)

def optimal_stopping(values, probs=None, rounds=2, cost=0):
    """Draw from `values` (equally likely, or with probs) up to `rounds` times, keep any draw;
    each extra draw costs `cost`. Returns (EV, thresholds) where you keep a draw >= threshold[k]
    when k draws remain after it. Die with one reroll: optimal_stopping(range(1,7), rounds=2) -> 4.25."""
    vals = list(values); ps = probs or [Fraction(1, len(vals))] * len(vals)
    ev = sum(v * p for v, p in zip(vals, ps)); thresholds = [None]
    for _ in range(rounds - 1):
        cont = ev - cost; thresholds.append(cont)
        ev = sum(max(v, cont) * p for v, p in zip(vals, ps))
    return ev, thresholds
