# Hand-off: Citadel Securities Trading Challenge Toolkit

## Context
- **Who:** Aman (UChicago 1st-year math), GitHub `amanislamm`, plus a teammate.
- **Event:** Citadel Securities Trading Challenge on the UChicago campus, **today (2026-10-28)**, 2 hours.
- **Likely format** (based on other schools' listings; no official rulebook was found): a **Market Making Game** and a
  **Fundamental Analyst Challenge**, played in teams. It could be open-outcry/verbal, a GUI exchange, or have an API.
  Check the rules on laptops and pre-written code before using any of this.
- **Goal:** be ready for anything: fast fair-value math, quoting, position/PnL tracking, arb checks, options,
  news/valuation, and bots in case an API is provided.

## Current state
- Code is on GitHub at `amanislamm/Citadel-Trading` (`main`), and **all tests pass** (`python3 tests/test_all.py`).
- Pure Python stdlib, Python 3.8+. No dependencies (`RestAdapter` imports `requests` lazily, `WsAdapter` imports `websocket-client` lazily).

## Layout
| Path | Purpose |
|---|---|
| `live.py` | Live console used during the game: log fills (`b X 10 34`), PnL (`p`), skewed quotes (`q X`), dice/cards/BS/IV/ETF/PCP/Kelly; `py EXPR` evaluates anything in `tt`. Autosaves `fills.csv` and reloads it on restart; card counter (`seen`/`cards`), take-or-pass (`t`), fair updates (`gm`), `fairs` table, `mkt` (instant market from dice/cards/Fermi bounds, multiplicative for Fermi), `news`, `fermi`, `settle`, loud pre-trade limit warning |
| `drill.py` | Timed practice questions in 8 categories; answers computed with `tt`, so they're exact. `python3 drill.py [N] [cats...]` |
| `game.py` | Turn-based practice game: ETF = 2A+B+C, news shocks, lagging bot quotes, planted ETF mispricings, limit penalties, settle at true value |
| `tt/probability.py` | Exact dice/card distributions (sum/max/min by convolution, so 100 dice is instant), `Deck` card counter, `dist_of_sum`, Monte Carlo, `condition()` (rejection sampling), `reveal_sum`, order stats, binomial/Poisson/hypergeometric, normal cdf/ppf, Bayes, Fermi estimates |
| `tt/quoting.py` | `quote()` with width ∝ std and inventory skew, `should_trade`, Kelly, adverse-selection update |
| `tt/book.py` | `Book`: positions, average entry price, realized/unrealized PnL per symbol, limits, CSV save/load, table report |
| `tt/arb.py` | ETF vs basket, put-call parity, conversion/reversal, box, call-spread/butterfly bounds, triangular FX, crossed markets, binary ladders, futures fair value |
| `tt/options.py` | Black-Scholes price and greeks, implied vol (Newton with bisection fallback, `None` outside no-arb bounds), binomial (American), digitals, `smile_scan` (flags RICH/CHEAP strikes), `portfolio_greeks` |
| `tt/orderbook.py` | `OrderBook`, microprice, imbalance, sweep cost, VWAP |
| `tt/signals.py` | EMA, rolling z-score, OLS, hedge ratio, pairs signal, realized vol, half-life, momentum |
| `tt/fundamentals.py` | NPV/IRR, DCF, Gordon growth, CAPM/WACC, multiples, earnings-surprise and news fair-value updates |
| `bots/adapter.py` | `Adapter` interface, `RestAdapter` and `WsAdapter` templates, and `RiskGuard` (wraps any adapter to enforce position, size, rate and price-band limits). **The only file to edit when an API shows up** |
| `bots/strategies.py` | `MarketMaker` (take + make, skewed, hard limits), `ETFArb`, `Flattener`, `run_loop` (cancels all orders on Ctrl-C and stops after repeated errors) |
| `sim/mock_exchange.py` | Toy exchange (random-walk fair, noise and informed flow) plus `backtest()`; `python3 sim/mock_exchange.py` sweeps quote width |
| `tests/test_all.py` | Plain-assert tests; run directly or with pytest |
| `docs/GAMEPLAN.md` | First-10-minute checklist, 2-person roles, playbooks (outcry, electronic, news, options), risk rules |
| `docs/CHEATSHEET.md` | Numbers to memorize, market-making rules, common traps |

## Known limitations / ideas for next steps
1. `MockExchange` is crude: fills ignore queue position and size, and the book is regenerated each tick. Its PnL is only a rough guide.
2. `RestAdapter` and `WsAdapter` use guessed schemas. Once the real API docs are posted, adapt them, wrap them in `RiskGuard`, and retune `MarketMaker` (`width_k`, `take_k`, `size`, `max_pos`) with `python3 sim/mock_exchange.py`.
3. Optional teammate access: `gh api -X PUT repos/amanislamm/Citadel-Trading/collaborators/<USERNAME>`.

## Conventions
- Keep it stdlib-only so it runs on any laptop without installs.
- Every new function goes in `tt/*` with an entry in that module's `__all__`, plus a test in `tests/test_all.py`.
- Run `python3 tests/test_all.py` before each commit.
