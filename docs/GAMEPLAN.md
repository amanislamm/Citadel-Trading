# Game Plan

## Warm-up (the hour before)
- [ ] `python3 tests/test_all.py` on BOTH laptops (all PASS)
- [ ] `python3 drill.py 30` once each; redo your weakest category (`python3 drill.py 20 expect cards`)
- [ ] Play `python3 game.py 20` together with `live.py` open: one trades, one logs and calls arbs. Swap roles and replay
- [ ] Agree on the out-loud quoting format: "bid at ask, size" ("34 at 38, 10 up")

## First 10 minutes (before trading)
- [ ] Read rules: **position limits, settlement method, fees, scoring (PnL? Sharpe? rank?), penalties for breaching limits**
- [ ] List every product. Write fair value + std for each in `live.py` (`f SYM FAIR STD`, `lim SYM N`)
- [ ] Look for **linked products** (ETF/basket, sum/parts, call/put, spreads) — planted arbs
- [ ] Assign roles (below). Agree on hand signals / shorthand

## Roles (2 people)
- **Trader (voice/clicks):** quotes, executes, keeps eyes on market
- **Analyst/Risk:** logs every fill in `live.py`, updates fair as info drops, calls out position & limits, hunts arbs

Swap if one person is clearly faster at mental math.

## Playbooks by game type

### A. Open-outcry "make me a market" (dice, cards, estimation)
1. Fair = expectation, width ≈ 0.5–1 std early. Say it confidently: "34 at 38, 10 up."
2. Each reveal → recompute (`reveal`, `condition`). Tighten width as std shrinks.
3. If someone lifts your offer repeatedly, **they think it's higher** — shift up, don't keep selling.
4. Inventory: if long, lower both quotes. Never let one position dominate.
5. Estimation (Fermi) markets: geometric mean of your 90% bounds; quote very wide; trade on others' info.

### B. Electronic exchange (GUI/API) with multiple products
1. Market-make the liquid products with tight but skewed quotes.
2. Run arb checks continuously (ETF vs basket, PCP). Execute both legs fast.
3. Hit stale quotes after news. Cancel your own stale quotes FIRST.
4. Near end: flatten if settlement is uncertain; hold if you know settlement value and price is wrong.

### C. News / Fundamental Analyst round
1. For each headline: direction, magnitude (% fair change), probability it's real, how much is priced in → `news_fair_update`.
2. Trade the **surprise vs expectations**, not the headline.
3. Be first or be skeptical: if price already moved fully, don't chase.
4. Valuation questions: DCF/multiples in `tt/fundamentals.py`. Sanity check vs comparable multiples.

### D. Options round
1. Price with BS; get IV from market quotes. Compare IVs across strikes — outliers are trades.
2. Check PCP, call-spread bounds, butterflies. Violations = free money.
3. Delta-hedge large option positions with the underlying (`delta_hedge_qty`).

## Risk rules (write them on paper)
- Max loss per product before you stop and re-think: ____
- Never exceed limits — breaches usually cost more than any trade earns
- If confused about a product, **quote wide or don't trade it**
- Recheck position vs official screen every ~10 min
