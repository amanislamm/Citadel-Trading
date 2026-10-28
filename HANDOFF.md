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
- Repo is built, committed locally on `main`, and **all tests pass** (`python3 tests/test_all.py`).
- GitHub repo `amanislamm/Citadel-Trading` **exists (public) but holds only an auto-created README**.
  The Cowork GitHub connector was read-only (403), so the push never happened.
- **First thing to do in Claude Code:**
  ```bash
  git remote add origin https://github.com/amanislamm/Citadel-Trading.git   # if not set
  git push -u origin main --force    # overwrites the auto README; needs gh auth login or credentials
  ```
- Pure Python stdlib, Python 3.8+. No dependencies (`bots/adapter.py`'s RestAdapter imports `requests` lazily).

## Layout
| Path | Purpose |
|---|---|
| `live.py` | Live console used during the game: log fills (`b X 10 34`), PnL (`p`), skewed quotes (`q X`), dice/cards/BS/IV/ETF/PCP/Kelly; `py EXPR` evaluates anything in `tt`. Autosaves `fills.csv` |
| `tt/probability.py` | Exact dice/card distributions, Monte Carlo, `condition()` (rejection sampling), `reveal_sum`, order stats, binomial/Poisson/hypergeometric, normal cdf/ppf, Bayes, Fermi estimates |
| `tt/quoting.py` | `quote()` with width ∝ std and inventory skew, `should_trade`, Kelly, adverse-selection update |
| `tt/book.py` | `Book`: positions, cash, MTM PnL, PnL by symbol, limits, CSV save/load |
| `tt/arb.py` | ETF vs basket, put-call parity, conversion/reversal, box, call-spread/butterfly bounds, triangular FX, crossed markets, binary ladders, futures fair value |
| `tt/options.py` | Black-Scholes price and greeks, implied vol (bisection), binomial (American), digitals |
| `tt/orderbook.py` | `OrderBook`, microprice, imbalance, sweep cost, VWAP |
| `tt/signals.py` | EMA, rolling z-score, OLS, hedge ratio, pairs signal, realized vol, half-life, momentum |
| `tt/fundamentals.py` | NPV/IRR, DCF, Gordon growth, CAPM/WACC, multiples, earnings-surprise and news fair-value updates |
| `bots/adapter.py` | `Adapter` interface plus a `RestAdapter` template. **The only file to edit when an API shows up** |
| `bots/strategies.py` | `MarketMaker` (take + make, skewed, hard limits), `ETFArb`, `Flattener`, `run_loop` |
| `sim/mock_exchange.py` | Toy exchange (random-walk fair, noise and informed flow) plus `backtest()`; `python3 sim/mock_exchange.py` sweeps quote width |
| `tests/test_all.py` | Plain-assert tests; run directly or with pytest |
| `docs/GAMEPLAN.md` | First-10-minute checklist, 2-person roles, playbooks (outcry, electronic, news, options), risk rules |
| `docs/CHEATSHEET.md` | Numbers to memorize, market-making rules, common traps |
| `push_to_github.sh` | `gh repo create` + push (already superseded, since the repo now exists) |

## Known limitations / ideas for next steps (priority order)
1. **Push to GitHub** (above). Optionally add the teammate as collaborator:
   `gh api -X PUT repos/amanislamm/Citadel-Trading/collaborators/<USERNAME>`.
2. `Book.avg_cost` returns net breakeven (net cash ÷ net qty), not FIFO cost. It's fine for the game; FIFO would be a nice addition.
3. `MockExchange` is crude: fills ignore queue position and size, and the book is regenerated each tick. Its PnL is only a rough guide.
4. No WebSocket adapter yet. Add `WsAdapter` in `bots/adapter.py` if the game uses one.
5. Possible extras: a hotkey/quick-quote mode in `live.py`; a multi-product fair-value table; an options-chain IV
   smile scanner (flag strikes whose IV is an outlier); and a card counter that updates distributions as cards are seen
   (use `card_draw_dist` with the remaining deck).
6. Once the real rules and API docs are posted, adapt `bots/adapter.py` and retune `MarketMaker` (`width_k`, `take_k`, `size`, `max_pos`).

## Conventions
- Keep it stdlib-only so it runs on any laptop without installs.
- Every new function goes in `tt/*` with an entry in that module's `__all__`, plus a test in `tests/test_all.py`.
- Run `python3 tests/test_all.py` before each commit.
