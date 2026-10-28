# Scenario Playbook — "if you see X, do Y"

Open this the moment the rules are announced. Find your scenario, follow the steps.
Commands in `code` are typed into `live.py` unless they start with `python3`.

---

## 0. The first 3 minutes (every format)
0. `python3 go.py` — runs every test, says whether RIT is running, and gives a menu of every tool.
1. **Laptops / pre-written code allowed?** If not → close the laptop. Use `docs/CHEATSHEET.md` printed, mental math, and section 4.
2. Write down: products, **position limits**, **settlement rule**, fees/rebates, scoring (PnL? rank? penalties?), round lengths.
3. One person: `python3 live.py`, then `lim SYM N` for every product, `f SYM FAIR STD` for anything you can price.
4. Decide roles (Trader / Analyst-Risk, see `GAMEPLAN.md`). Say the quote format out loud once: "bid at ask, size".

## 1. Which platform is it?
| You see | Go to |
|---|---|
| "RIT", "Rotman Interactive Trader", a client app with an API key | §2 |
| Another web/desktop exchange **with** API docs | §3 |
| A GUI exchange, **no** API | §4b (click-trade, log in `live.py`) |
| Verbal / open-outcry / "make me a market" | §4a |
| Company packet, valuation, pitch | §6 |

## 2. RIT (Rotman Interactive Trader)
**Rehearse now:** `python3 sim/fake_rit.py` in one terminal, then `RIT_KEY=KEY python3 bots/run_rit.py --check` in another.
The fake server speaks the same API (book, orders, tenders, news, 429s), so steps 2–5 can be practiced end to end.

1. In the RIT client: log in, open the API panel, copy the key.
2. `export RIT_KEY=<key>` then `python3 bots/run_rit.py --check`. You should see case, securities, limits.
   - `401` → wrong key. `cannot reach RIT` → client not open / not logged in / different port (edit `BASE_URL`).
3. Edit CONFIG at the top of `bots/run_rit.py` from the case brief: `MAX_ORDER_SIZE`, `MAX_POS`, tickers.
4. Run **paper** first: `python3 bots/run_rit.py`. Watch 30 seconds of decisions. Then `--live`.
   Trading by hand instead? Terminal 1: `python3 bots/rit_dash.py` (watch). Terminal 2: `python3 bots/rit_console.py` (orders: `b CRZY 5000`, `s CRZY 2000 24.95`, `x`, `ten`, `ta 7`).
5. **Ctrl-C stops and cancels all orders.** Emergency flat: `python3 -c "from bots.rit import RIT; RIT('<key>').flatten()"`.

### RIT case types
| Case | What wins | Tools |
|---|---|---|
| **Liability trading / tenders** (client offers a block at a price) | Accept only if unwinding into visible depth beats the tender price; then unwind **gradually**, don't market-dump | dashboard shows ACCEPT/DECLINE live; console `ta ID`, then `unwind CRZY 0 60 2000` (passive when on schedule, crosses only when behind) |
| **Algorithmic market making** (rebates for passive, fees for aggressive) | Quote both sides inside the spread, small size, skew hard on inventory, never sit at the limit | `MM_TICKERS` in runner; tune `width_k`, `size`, `max_pos` |
| **Merger arbitrage** (news changes deal odds) | Fair = p·offer + (1−p)·standalone; trade the gap; stock deals hedge with `ratio` × acquirer | `deal 50 30 46 0.85` → implied p and edge |
| **Volatility trading** (options + underlying, vol news) | Compare forecast vol to implied; buy options if forecast > IV, sell if <; **delta-hedge** every few ticks | `iv`, `py smile_scan(...)`; console `hedge RTM 0.25 0.08` (underlying, vol, years left) hedges once; `DeltaHedger` for a loop. Option tickers parsed like `RTM1C45` / `RTM48P` |
| **ETF / basket arbitrage** | ETF vs weighted basket outside costs → trade both legs at once | `etf ...`, runner `ETF = (...)` |
| **Commodities / refinery / conversion** | Value output − input − conversion cost; arb when spread > cost | `py` + `sum_of_parts` |

## 3. Other API
1. Read the docs for: get book, get position, place, cancel, cancel all. Map them onto `RestAdapter` / `WsAdapter` in `bots/adapter.py` (only that file).
2. Wrap in `RiskGuard(...)` with the official limits, then `PaperAdapter` for a dry run.
3. Reuse `MarketMaker`, `ETFArb`, `run_loop(strats, ex=ex)` (Ctrl-C cancels all).

## 4. No-API formats
### 4a. Verbal / "make me a market" / estimation
1. Price it: `mkt dice 3`, `mkt cards 2` (after `seen ...`), `mkt fermi 1k 100k`, or `mkt FAIR STD`.
2. Open **wide** (first line), tighten as info arrives. Say it with size: "9 at 12, 10 up".
3. Someone keeps lifting you → `gm X <price>` moves your fair toward them. Repeated one-way flow = you're wrong.
4. Reveals: `seen K 7` then `mkt cards N` again. Dice reveals: `reveal N_UNKNOWN v1 v2`.
5. Log every fill (`b X 10 34`), check `p` after each trade, never exceed limits.

### 4b. GUI exchange, no API
1. Trader clicks; Analyst logs fills in `live.py` and watches `fairs` and `p`.
2. Every few minutes: compare `p` with the official position screen. Fix with `b`/`s`/`undo`.
3. News → `news X impact% p_true priced_in`, then **pick off stale quotes first**, then requote.

## 5. Special situations
| Situation | Do this |
|---|---|
| A product's fair is unclear | Quote very wide or don't trade it. Uncertainty is a reason for width, not for guessing |
| Planted arb (ETF/basket, PCP, box, ladder sums ≠ 1) | `etf`, `pcp`, `ladder`, `py box_spread(...)`. Execute **both legs** quickly; size within limits |
| Binary contracts on outcomes | Prices = probabilities; `ladder p1 p2 ...`; buy all if sum < 100, sell all if > 100 |
| Options chain given | `py smile_scan(S, T, r, {K: px, ...})` → trade RICH/CHEAP strikes, hedge delta |
| Settlement value known before the end | `settle X PX`; buy below / sell above it up to limits; no reason to flatten |
| Settlement uncertain | Flatten toward the end, but **not** at panic prices in the last seconds |
| Near a limit | `fairs` shows room; skew quotes harder; a breach usually costs more than the trade earns |
| Bot misbehaving | Ctrl-C (cancels all). Then `--check` and paper mode before going live again |
| Laptop crash | Rerun `python3 live.py`: fills reload. Partner keeps trading meanwhile |
| Brainteaser mid-game ("expected flips until HTH?") | `wait HTH`, `race THH HHT`, `ruin 3 10`; answers table in `CHEATSHEET.md` |
| No laptops allowed | Print `docs/print.html` beforehand (cheat sheet + playbook + game plan, 2 pages) |
| Teammates disagree on fair | Use the average and quote wider; check fills afterward to see who was right |

## 6. Fundamental Analyst Challenge
1. Skim the packet for: price, shares, net debt, last revenue, growth/margin guidance, peers' multiples, EPS, 52-week range.
2. Fill `INPUTS` in `valuation.py`, run `python3 valuation.py` (prints DCF, WACC×g grid, comps, reverse DCF, football field, pitch outline).
3. Sanity checks before you speak:
   - Terminal value > 80% of EV → say your answer hinges on g/WACC and show the grid.
   - DCF vs comps disagree by > 30% → explain why (growth, margins, leverage) or adjust inputs.
   - Reverse DCF: "the price implies X% growth forever; we think that's too high/low because …" is a strong pitch line.
4. Pitch structure (60–90 s): recommendation + target → valuation (3 methods) → what the market believes → 2–3 drivers → catalysts → risks + downside value.
5. Likely judge questions — have one-sentence answers:
   - Why this WACC / beta? (CAPM build; peers' unlevered beta re-levered: `py relever_beta(unlever_beta(b, de, t), de2, t)`)
   - What breaks the thesis? (name the input and its value in the grid where you'd flip)
   - Why will the market re-rate it, and when? (catalyst)
   - How would you size / hedge the position? (sector or peer short; position size as % of book)
6. News during the round: `py earnings_surprise_move(actual, consensus, price, pe=...)` and `news_fair_update(...)`.

## 7. Last 5 minutes (any game)
1. Know the settlement rule cold. Recheck positions vs the official screen.
2. Cancel stale orders. Reduce positions you can't defend at settlement.
3. Don't start new complex trades. A small sure profit beats a large risky one now.
