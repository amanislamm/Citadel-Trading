# Citadel Securities Trading Challenge Toolkit

Pre-built tools for a 2-hour market-making / trading challenge. **Pure Python stdlib — no installs needed** (Python 3.8+).

## Quick start (do this before the game)
```bash
git clone https://github.com/amanislamm/Citadel-Trading.git && cd Citadel-Trading
python3 go.py                    # preflight + menu for every tool (start here)
python3 tests/test_all.py        # everything should PASS
python3 drill.py                 # warm up: timed questions, answers checked exactly
python3 game.py                  # practice round: ETF + components, news, arbs
python3 live.py                  # live console — keep open all game
```

## What's here
| Path | Use it for |
|---|---|
| `live.py` | **Live console.** Log fills (`b X 10 34`), PnL table with realized/unrealized, skewed quotes (`q X`), take-or-pass (`t X 33 34`), card counter (`seen K 7 A`, `cards 2`), instant markets (`mkt dice 3`, `mkt fermi 1k 100k`), news updates (`news X -8 0.7`), dice/options/arb calcs in one line. Reloads `fills.csv` if you restart |
| `go.py` | **Start here.** Preflight (Python, all tests, RIT reachable?) + menu that launches every tool |
| `docs/print.html` | 2-page printout of cheat sheet + playbook + game plan (rebuild: `python3 tools/print_docs.py`) |
| `docs/PLAYBOOK.md` | **Open first on game day.** Scenario → steps: platform decision tree, RIT case types, verbal markets, special situations, Fundamental Analyst pitch, last 5 minutes |
| `valuation.py` | **Fundamental Analyst template.** Fill inputs → DCF build, WACC×g grid, comps, reverse DCF, football field, pitch outline |
| `bots/run_rit.py` | **RIT bot runner** (`--check`, paper by default, `--live`): news, tender evaluation, market making, ETF arb, Ctrl-C cancels all |
| `drill.py` | **Timed practice.** Make-a-market questions graded on width (`python3 drill.py 20 make`), dice, cards, expectations, probability, options, arb, market-making and mental-math questions; scores accuracy and speed per category (`python3 drill.py 30 dice cards`) |
| `game.py` | **Practice game.** ETF = 2A+B+C with news shocks, lagging quotes and planted ETF mispricings; trade or post your own market, settle at true value |
| `tt/probability.py` | Exact dice/card distributions (instant for any number of dice), `Deck` card counter, exact Markov solver (`pattern_wait`, `pattern_race`, `gamblers_ruin`, `optimal_stopping`), Monte Carlo, conditioning on reveals, order stats, binomial/Poisson/hypergeometric, Bayes, Fermi estimates |
| `tt/quoting.py` | Bid/ask from fair+std with inventory skew, take-or-pass, Kelly sizing, adverse-selection updates |
| `tt/book.py` | Positions, average entry price, realized/unrealized PnL, limits, CSV save/load |
| `tt/arb.py` | ETF vs basket, put-call parity, conversions/reversals, box, call-spread & butterfly bounds, triangular FX, crossed markets, binary ladders |
| `tt/options.py` | Black-Scholes price/greeks, fast implied vol, binomial (American), digitals, IV smile outlier scan, portfolio greeks |
| `tt/orderbook.py` | Local order book, microprice, imbalance, sweep cost, VWAP |
| `tt/signals.py` | EMA, rolling z-score, OLS/hedge ratio, pairs signal, realized vol, mean-reversion half-life |
| `tt/fundamentals.py` | DCF build from drivers, sensitivity grids, comps, reverse DCF, football field, CAPM/WACC, beta (un)levering, merger arb, NPV/IRR, news updates |
| `bots/rit_dash.py` | Read-only RIT dashboard: positions, quotes, P&L, limit usage bars, tenders with ACCEPT/DECLINE, news |
| `bots/rit_console.py` | Fast RIT order entry: `b/s SYM QTY [PX]`, cancel, flatten, tenders, `unwind`, `hedge`; fat-finger confirm |
| `bots/rit.py` | Stdlib-only Rotman Interactive Trader adapter: book, orders (auto-split), cancel, tenders, news, limits, flatten, 429 retry |
| `bots/adapter.py` | Fill in when organizers give another API: REST and WebSocket templates, `RiskGuard` (blocks limit breaches and fat fingers), `PaperAdapter` (dry run) |
| `sim/fake_rit.py` | Fake RIT server to rehearse the RIT flow offline |
| `bots/strategies.py` | MarketMaker, ETFArb, Flattener, Unwinder (work off a block on schedule), DeltaHedger (vol cases), run loop |
| `sim/mock_exchange.py` | Toy exchange with noise + informed traders to tune bots (`python3 sim/mock_exchange.py`) |
| `docs/GAMEPLAN.md` | Team roles, timeline, playbook per game type |
| `docs/CHEATSHEET.md` | Numbers to know cold, market-making rules, common traps |

## Python usage
```python
python3 -i -c "from tt import *"
>>> stats(dice_dist(3, func=max))
>>> quote(fair=35, std=5.4, position=40, max_pos=100)
>>> condition(lambda: [random.randint(1,6) for _ in range(3)], lambda w: w[0]==6, sum)
>>> etf_arb(101, 102, [(49,49.5),(49.8,50.2)], [1,1])
>>> d = Deck(); d.seen(13, 13, 1); d.sum_fair(2)        # fair & std of 2 more cards
>>> smile_scan(100, 0.25, 0, {90: 11.2, 95: 7.1, 100: 4.0, 105: 3.1, 110: 0.9})
```

> Check the event rules on laptops/pre-written code before using any of this during the game.
