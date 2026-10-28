# Citadel Securities Trading Challenge Toolkit

Pre-built tools for a 2-hour market-making / trading challenge. **Pure Python stdlib — no installs needed** (Python 3.8+).

## Quick start (do this before the game)
```bash
git clone https://github.com/amanislamm/Citadel-Trading.git && cd Citadel-Trading
python3 tests/test_all.py        # everything should PASS
python3 drill.py                 # warm up: timed questions, answers checked exactly
python3 game.py                  # practice round: ETF + components, news, arbs
python3 live.py                  # live console — keep open all game
```

## What's here
| Path | Use it for |
|---|---|
| `live.py` | **Live console.** Log fills (`b X 10 34`), PnL table with realized/unrealized, skewed quotes (`q X`), take-or-pass (`t X 33 34`), card counter (`seen K 7 A`, `cards 2`), instant markets (`mkt dice 3`, `mkt fermi 1k 100k`), news updates (`news X -8 0.7`), dice/options/arb calcs in one line. Reloads `fills.csv` if you restart |
| `drill.py` | **Timed practice.** Dice, cards, expectations, probability, options, arb, market-making and mental-math questions; scores accuracy and speed per category (`python3 drill.py 30 dice cards`) |
| `game.py` | **Practice game.** ETF = 2A+B+C with news shocks, lagging quotes and planted ETF mispricings; trade or post your own market, settle at true value |
| `tt/probability.py` | Exact dice/card distributions (instant for any number of dice), `Deck` card counter, Monte Carlo, conditioning on reveals, order stats, binomial/Poisson/hypergeometric, Bayes, Fermi estimates |
| `tt/quoting.py` | Bid/ask from fair+std with inventory skew, take-or-pass, Kelly sizing, adverse-selection updates |
| `tt/book.py` | Positions, average entry price, realized/unrealized PnL, limits, CSV save/load |
| `tt/arb.py` | ETF vs basket, put-call parity, conversions/reversals, box, call-spread & butterfly bounds, triangular FX, crossed markets, binary ladders |
| `tt/options.py` | Black-Scholes price/greeks, fast implied vol, binomial (American), digitals, IV smile outlier scan, portfolio greeks |
| `tt/orderbook.py` | Local order book, microprice, imbalance, sweep cost, VWAP |
| `tt/signals.py` | EMA, rolling z-score, OLS/hedge ratio, pairs signal, realized vol, mean-reversion half-life |
| `tt/fundamentals.py` | DCF, Gordon growth, CAPM/WACC, NPV/IRR, multiples, earnings-surprise & news fair-value updates |
| `bots/adapter.py` | Fill in when organizers give an API: REST and WebSocket templates, plus `RiskGuard` to block limit breaches and fat fingers |
| `bots/strategies.py` | MarketMaker, ETFArb, Flattener + run loop |
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
