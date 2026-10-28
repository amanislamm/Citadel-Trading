#!/usr/bin/env python3
"""TIMED PRACTICE DRILLS — sharpen speed before the game. Answers are computed with tt.*, so they're exact.

  python3 drill.py                 20 mixed questions
  python3 drill.py 40 dice cards   40 questions from chosen categories
  python3 drill.py --list          show categories

Type answers as numbers or fractions (7/2, 0.35, 35%). Enter = skip, q = quit.
"make" questions want a two-sided market: type BID ASK (e.g. 9 12 or 9@12).
Score = right within tolerance; aim for < 10 s per question.
"""
import math, os, random, re, sys, time
from fractions import Fraction
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tt import *  # noqa

R = random.Random()

def q_dice():
    kind = R.choice(["sum_mean", "sum_std", "max", "min", "p_sum", "p_atleast"])
    n = R.randint(2, 4) if kind not in ("sum_mean", "sum_std") else R.randint(2, 12)
    sides = R.choice([6, 6, 6, 4, 8, 10, 20]) if kind in ("sum_mean", "max", "min") else 6
    if kind == "sum_mean":
        return f"E[sum of {n} d{sides}]?", n * (sides + 1) / 2, 0.01, f"{n} x {(sides + 1) / 2}"
    if kind == "sum_std":
        return f"Std of sum of {n} d6?", math.sqrt(n * 35 / 12), 0.05, f"sqrt({n} x 35/12)"
    if kind == "max":
        v = stats(dice_dist(n, sides, max))["mean"]
        return f"E[max of {n} d{sides}]?", v, 0.02, f"sum_k P(max>=k) = sum 1-((k-1)/{sides})^{n}"
    if kind == "min":
        v = stats(dice_dist(n, sides, min))["mean"]
        return f"E[min of {n} d{sides}]?", v, 0.02, f"sum_k P(min>=k) = sum ((s-k+1)/{sides})^{n}"
    d = dice_dist(n, 6)
    if kind == "p_sum":
        k = R.choice(list(d)[len(d) // 4: 3 * len(d) // 4])
        return f"P(sum of {n} d6 = {k})?", d[k], 0.005, f"count ways / 6^{n}"
    k = R.choice(list(d)[len(d) // 2: 4 * len(d) // 5])
    return f"P(sum of {n} d6 >= {k})?", sum(p for v, p in d.items() if v >= k), 0.005, "sum the tail"

def q_cards():
    kind = R.choice(["sum", "after_seen", "p_face", "p_pair"])
    if kind == "sum":
        n = R.randint(2, 6)
        return f"E[sum of {n} cards, A=1..K=13]?", 7 * n, 0.01, f"7 x {n}"
    if kind == "after_seen":
        seen = R.sample(card_deck(), R.randint(2, 6)); d = Deck(); d.seen(*seen); n = R.randint(1, 3)
        names = " ".join({1: "A", 11: "J", 12: "Q", 13: "K"}.get(c, str(c)) for c in seen)
        return (f"Seen {names}. E[sum of next {n} cards]?", d.sum_fair(n)[0], 0.05,
                f"{n} x (364 - {sum(seen)}) / {len(d)}")
    if kind == "p_face":
        return "P(at least one face card J/Q/K in 2 cards)?", 1 - (40 * 39) / (52 * 51), 0.005, "1 - (40/52)(39/51)"
    return "P(2 cards are a pair)?", 3 / 51, 0.002, "3/51"

def q_expect():
    pool = [
        ("Expected rolls of a d6 until first 6?", 6, 0.01, "geometric: 1/p"),
        ("Expected rolls until two 6s in a row?", 42, 0.01, "E = 6 + 6^2"),
        ("Expected rolls until 5 then 6 (in a row)?", 36, 0.01, "no self-overlap: 6^2"),
        ("Expected flips until HH?", 6, 0.01, "2 + 4"),
        ("Expected flips until HT?", 4, 0.01, "no self-overlap: 2^2"),
        ("Coupon collector: expected d6 rolls to see all faces?", coupon_collector(6), 0.05, "6 x H_6 = 14.7"),
        ("E[max of 2 uniform(0,1)]?", 2 / 3, 0.005, "n/(n+1)"),
        ("E[min of 3 uniform(0,1)]?", 1 / 4, 0.005, "1/(n+1)"),
        ("E[|X-Y|] for X,Y ~ U(0,1)?", 1 / 3, 0.005, "1/3"),
        ("Stick broken at 2 uniform points: E[longest piece]?", 11 / 18, 0.005, "11/18"),
        ("E[number of fixed points of a random permutation of 52]?", 1, 0.01, "linearity: 52 x 1/52"),
        ("You roll a d6 and may reroll once. E[value] playing optimally?", 4.25, 0.01, "keep 4+: 0.5 x 5 + 0.5 x 3.5"),
    ]
    n = R.randint(2, 5)
    pool.append((f"Roll a d6, win the face value; you may reroll up to {n - 1} times. E[value]?",
                 _reroll_ev(n), 0.01, "backward induction: keep if face > EV of continuing"))
    return R.choice(pool)

def _reroll_ev(rolls):
    ev = 3.5
    for _ in range(rolls - 1):
        ev = sum(max(f, ev) for f in range(1, 7)) / 6
    return ev

def q_prob():
    kind = R.choice(["binom", "bayes", "normal", "poisson"])
    if kind == "binom":
        n, k = R.randint(4, 10), None; p = R.choice([0.5, 0.5, 0.3, 0.2]); k = R.randint(1, n - 1)
        return f"P(exactly {k} heads in {n} flips, p={p})?", binom_pmf(k, n, p), 0.003, f"C({n},{k}) p^k q^(n-k)"
    if kind == "bayes":
        prior = R.choice([0.01, 0.02, 0.05, 0.1]); sens = R.choice([0.9, 0.95, 0.99]); fp = R.choice([0.05, 0.1])
        post = prior * sens / (prior * sens + (1 - prior) * fp)
        return (f"Disease rate {prior:.0%}, test sensitivity {sens:.0%}, false positive {fp:.0%}. "
                f"P(sick | positive)?", post, 0.005, "p*s / (p*s + (1-p)*fp)")
    if kind == "normal":
        z = R.choice([1, 1.645, 1.96, 2, 2.58]); return f"P(|Z| < {z}) for standard normal?", prob_between(-z, z, 0, 1), 0.005, "68 / 90 / 95 / 95.4 / 99"
    lam = R.choice([1, 2, 3]); k = R.randint(0, 3)
    return f"Poisson(lambda={lam}): P(X={k})?", poisson_pmf(k, lam), 0.003, "e^-l l^k / k!"

def q_options():
    kind = R.choice(["atm", "pcp", "straddle", "delta"])
    S = R.choice([50, 100, 100, 200]); sig = R.choice([0.2, 0.3, 0.4]); T = R.choice([0.25, 1.0])
    if kind == "atm":
        return f"ATM call approx: S={S}, vol={sig:.0%}, T={T}y, r=0?", 0.4 * S * sig * math.sqrt(T), 0.1, "0.4 S sigma sqrt(T)"
    if kind == "straddle":
        return f"ATM straddle approx: S={S}, vol={sig:.0%}, T={T}y?", 0.8 * S * sig * math.sqrt(T), 0.2, "0.8 S sigma sqrt(T)"
    if kind == "delta":
        return "Delta of an ATM call (approx, short-dated, r=0)?", 0.5, 0.03, "about 0.5"
    K = S + R.choice([-10, -5, 5, 10]); C = round(R.uniform(3, 15), 1)
    P = C - (S - K)
    return f"r=0. S={S}, K={K}, call={C}. Fair put?", P, 0.01, "P = C - S + K"

def q_arb():
    kind = R.choice(["etf", "ladder", "box"])
    if kind == "etf":
        comps = [round(R.uniform(20, 60), 1) for _ in range(3)]; w = [R.randint(1, 3) for _ in comps]
        fair = sum(a * b for a, b in zip(w, comps)); etf = round(fair + R.choice([-3, -2, 2, 3]) + R.uniform(-.5, .5), 1)
        legs = " + ".join(f"{a}x{b}" for a, b in zip(w, comps))
        return f"ETF = {legs}. ETF trades {etf}. Edge per ETF (ETF - basket)?", etf - fair, 0.05, "price the basket, subtract"
    if kind == "ladder":
        ps = [R.randint(10, 40) for _ in range(4)]
        return (f"Binaries on 4 exclusive outcomes (pay 100) priced {ps}. Profit from buying/selling all one each?",
                abs(100 - sum(ps)), 0.01, "|100 - sum|")
    K1, K2 = 90, 110
    return f"Box spread {K1}/{K2}, r=0. Fair value?", K2 - K1, 0.01, "K2 - K1"

def q_mm():
    kind = R.choice(["skew", "kelly", "edge"])
    if kind == "skew":
        fair, sd, pos, lim = R.choice([40, 50, 100]), R.choice([2, 4]), R.choice([-60, -30, 30, 60]), 100
        b, a = quote(fair, sd, pos, lim)
        return (f"Fair {fair}, std {sd}, pos {pos}/{lim}. Using quote() (half-width 0.5 std, skew by pos/limit): your BID?",
                b, 0.51, "mid = fair - half x pos/limit")
    if kind == "kelly":
        p = R.choice([0.55, 0.6, 0.65]); o = R.choice([1, 2])
        return f"Bet pays {o}:1, win prob {p}. Full-Kelly fraction?", kelly_binary(p, o), 0.005, "(p(b+1) - 1) / b"
    fair = R.randint(30, 70); bid = fair + R.choice([-3, -1, 2, 4]); ask = bid + 1
    side = "SELL" if bid > fair else "BUY" if ask < fair else "PASS"
    return f"Fair {fair}. Market {bid} @ {ask}. Edge per unit if you trade the right way (0 if none)?", \
        max(bid - fair, fair - ask, 0), 0.01, f"{side}"

def q_math():
    kind = R.choice(["mul", "pct", "sqrt", "div"])
    if kind == "mul":
        a, b = R.randint(12, 99), R.randint(12, 99); return f"{a} x {b}?", a * b, 0.01, ""
    if kind == "pct":
        a, b = R.randint(5, 45), R.randint(40, 900); return f"{a}% of {b}?", a * b / 100, 0.01, ""
    if kind == "sqrt":
        a = R.randint(2, 99); return f"sqrt({a}) (2 dp)?", math.sqrt(a), 0.02, ""
    a, b = R.randint(100, 999), R.randint(7, 29); return f"{a} / {b} (2 dp)?", a / b, 0.01, ""

def q_make():
    """'Make me a market' — answer with BID ASK. Graded on: fair inside, width <= 1.5 std."""
    kind = R.choice(["dice_sum", "dice_max", "cards_sum", "seen", "product", "heads", "top2", "range"])
    if kind == "dice_sum":
        n = R.randint(2, 8); st = stats(dice_dist(n)); txt = f"the sum of {n} dice"
    elif kind == "dice_max":
        n = R.randint(2, 5); st = stats(dice_dist(n, 6, max)); txt = f"the max of {n} dice"
    elif kind == "cards_sum":
        n = R.randint(2, 5); d = Deck(); mu, sd = d.sum_fair(n); st = {"mean": mu, "std": sd}; txt = f"the sum of {n} cards (A=1..K=13)"
    elif kind == "seen":
        seen = R.sample(card_deck(), 4); d = Deck(); d.seen(*seen); n = R.randint(2, 4)
        mu, sd = d.sum_fair(n); st = {"mean": mu, "std": sd}
        txt = f"the sum of the next {n} cards; already seen {' '.join(map(str, seen))}"
    elif kind == "product":
        st = stats(dice_dist(2, 6, lambda r: r[0] * r[1])); txt = "the product of 2 dice"
    elif kind == "heads":
        n = R.choice([10, 20, 50, 100]); st = {"mean": n / 2, "std": math.sqrt(n) / 2}; txt = f"the number of heads in {n} flips"
    elif kind == "top2":
        st = stats(dice_dist(3, 6, lambda r: sum(sorted(r)[1:]))); txt = "the sum of the top 2 of 3 dice"
    else:
        n = R.randint(2, 4); st = stats(dice_dist(n, 6, lambda r: max(r) - min(r))); txt = f"max minus min of {n} dice"
    return f"Make a market on {txt}.  (BID ASK)", (st["mean"], st["std"]), "market", \
        f"fair {st['mean']:.3f}, std {st['std']:.3f}"

def grade_market(ans, fair, sd):
    """-> (good, feedback). Good = bid < fair < ask and width <= 1.5 std."""
    nums = re.findall(r"-?\d+(?:\.\d+)?", ans)
    if len(nums) < 2: return False, "type two numbers: BID ASK"
    bid, ask = float(nums[0]), float(nums[1])
    if bid >= ask: return False, "bid must be below ask"
    w = (ask - bid) / sd if sd else float("inf"); mid_off = ((bid + ask) / 2 - fair) / sd if sd else 0
    inside = bid < fair < ask
    fb = f"width {ask - bid:g} = {w:.2f} std, centre off by {mid_off:+.2f} std"
    if not inside: return False, "fair is OUTSIDE your market; " + fb
    if w > 1.5: return False, "too wide (you won't trade); " + fb
    return True, fb + (" (very tight: risky if wrong)" if w < 0.3 else "")

CATS = {"make": q_make, "dice": q_dice, "cards": q_cards, "expect": q_expect, "prob": q_prob,
        "options": q_options, "arb": q_arb, "mm": q_mm, "math": q_math}

def parse(ans):
    ans = ans.strip().replace(",", "").replace(" ", "")
    pct = ans.endswith("%")
    if pct: ans = ans[:-1]
    if not re.fullmatch(r"-?[\d.]+(/[\d.]+)?", ans): raise ValueError(ans)
    v = float(Fraction(ans)) if "/" in ans and "." not in ans else (
        float(ans.split("/")[0]) / float(ans.split("/")[1]) if "/" in ans else float(ans))
    return v / 100 if pct else v

def ok(v, truth, tol):
    """Accept absolute tolerance, or 1% relative for big numbers; probabilities may be typed as %."""
    if abs(v - truth) <= tol or abs(v - truth) <= 0.01 * abs(truth): return True
    return 0 <= truth <= 1 and abs(v / 100 - truth) <= tol      # typed 35 meaning 35%

def main(argv):
    if "--list" in argv: print("categories:", ", ".join(CATS)); return
    n = next((int(x) for x in argv if x.isdigit()), 20)
    cats = [c for c in argv if c in CATS] or list(CATS)
    print(__doc__); score, times, per = 0, [], {}
    for i in range(1, n + 1):
        cat = R.choice(cats); prompt, truth, tol, why = CATS[cat]()
        t0 = time.time(); ans = input(f"[{i}/{n}] ({cat}) {prompt}  ")
        dt = time.time() - t0
        if ans.strip().lower() == "q": break
        times.append(dt); c = per.setdefault(cat, [0, 0, 0.0]); c[1] += 1; c[2] += dt
        if tol == "market":
            good, fb = grade_market(ans, *truth)
            print(f"   {'✓' if good else '✗'} {dt:.1f}s  {fb}   [{why}]")
            if good: score += 1; c[0] += 1
            continue
        try: good = ok(parse(ans), truth, tol)
        except ValueError: good = False
        if good: score += 1; c[0] += 1; print(f"   ✓ {dt:.1f}s  ({truth:.4g})")
        else: print(f"   ✗ answer {truth:.4g}   {why}")
    if times:
        print(f"\nScore {score}/{len(times)}  avg {sum(times) / len(times):.1f}s")
        for k, (g, t, s) in sorted(per.items()):
            print(f"  {k:<8} {g}/{t}  avg {s / t:.1f}s")

if __name__ == "__main__":
    try: main(sys.argv[1:])
    except (EOFError, KeyboardInterrupt): print()
