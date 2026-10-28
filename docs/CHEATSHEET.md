# Cheat Sheet

## Numbers to know cold
| Thing | Mean | Var | Std |
|---|---|---|---|
| 1 die | 3.5 | 35/12 ≈ 2.92 | 1.71 |
| n dice sum | 3.5n | 2.92n | 1.71√n |
| 1 card (A=1..K=13) | 7 | 14 | 3.74 |
| n cards sum (no replacement, 52) | 7n | 14n·(52−n)/51 | — |
| Uniform[0,1] | 1/2 | 1/12 | 0.289 |
| Max of n U[0,1] | n/(n+1) | | |
| Coin flips n | n/2 | n/4 | √n/2 |

- 2d6: P(7)=1/6, P(≥10)=1/6, P(doubles)=1/6
- Max of 2d6: E = 161/36 ≈ 4.47; max of 3d6 ≈ 4.96
- Expected rolls until a 6: 6; until two 6s in a row: 42; until "5 then 6": 36
- Coupon collector (6 faces): 14.7 rolls
- Normal: ±1σ 68%, ±1.645σ 90%, ±1.96σ 95%, ±2.58σ 99%
- √2≈1.414, √3≈1.732, √10≈3.162, ln2≈0.693, e≈2.718
- ATM call ≈ 0.4·S·σ·√T; ATM straddle ≈ 0.8·S·σ·√T
- Rule of 72: doubling time ≈ 72 / (rate in %)

## Market-making rules of thumb
1. Quote around fair, width ∝ uncertainty. Tighten as info arrives.
2. Skew against inventory. Long → lower bid AND ask.
3. Getting filled is information (adverse selection). Repeated lifts = you're too low.
4. Size small when unsure, bigger when edge is clear (fractional Kelly).
5. Spread × volume is the business; don't turn into a directional gambler.
6. Linked products must be consistent — check every one.
7. Know your position at all times.

## Common traps
- Quoting a market your partner already crossed
- Forgetting fees / contract multipliers
- Settlement defined differently than you assumed (read it!)
- Drawing cards **without** replacement — use `card_draw_dist`, not dice math
- Chasing news that's already priced in
- Panic-flattening at bad prices in the last minute

## live.py quick reference
| Situation | Type |
|---|---|
| Set fair and limit | `f X 35 5` then `lim X 100` |
| What should I quote? | `q X` (skewed by your position) or `fairs` for every product |
| Someone offers 33 / 34, trade? | `t X 33 34` |
| Got lifted/hit at 38, update fair | `gm X 38` |
| Log fills | `b X 10 34`, `s X 4 37` (`10k` / `1.5m` ok), `undo` if wrong |
| Where am I? | `p` (pos, avg, realized, unrealized, limit warnings) |
| Cards seen (no replacement) | `seen K 7 A`, then `cards 2` for fair of 2 more cards |
| Probability ladder sums | `ladder 30 25 50` |
| Anything else | `py x = dcf([10,11,12], 0.1, 0.02)` then `py x` |
| Console crashed | rerun `python3 live.py`; fills reload automatically |
