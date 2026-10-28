import os, sys, math, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tt import *
from sim.mock_exchange import backtest
from bots.strategies import MarketMaker, ETFArb, Flattener

def approx(a, b, tol=1e-6): return abs(a - b) < tol

def test_probability():
    assert approx(stats(dice_dist(2))["mean"], 7)
    assert approx(stats(dice_dist(1))["std"] ** 2, 35 / 12)
    assert approx(stats(card_draw_dist(2))["mean"], 14)
    assert approx(coupon_collector(6), 14.7, 1e-9)
    assert approx(normal_ppf(0.975), 1.959964, 1e-4)
    assert approx(sum(binom_dist(10, 0.3).values()), 1)
    assert approx(bayes({"a": .5, "b": .5}, {"a": 1, "b": 0})["a"], 1)
    assert reveal_sum([6, 5], 8)[0] == 39
    random.seed(1)
    m, _, _ = condition(lambda: [random.randint(1, 6) for _ in range(3)], lambda w: w[0] == 6, sum, 60_000)
    assert abs(m - 13) < 0.1

def test_quoting():
    b, a = quote(35, 5.4); assert b < 35 < a
    b2, a2 = quote(35, 5.4, position=60); assert b2 < b and a2 < a
    assert should_trade(10, 1, 11, 9)[0] == "BUY"
    assert approx(kelly_binary(0.6, 1), 0.2)

def test_book():
    bk = Book(); bk.fill("X", "buy", 10, 34); bk.fill("X", "sell", 4, 37)
    assert bk.pos["X"] == 6 and approx(bk.pnl({"X": 35}), 18)

def test_arb():
    assert etf_arb(101, 102, [(49, 49.5), (49.8, 50.2)], [1, 1])[0][0].startswith("SELL ETF")
    assert approx(put_call_parity(7, 2, 103, 100), 2)
    assert "ARB" in crossed({"A": (10, 11), "B": (12, 13)})
    assert butterfly_check(10, 5, 1) == "ok" and "VIOLATION" in butterfly_check(10, 6, 1)

def test_options():
    c = bs_price(100, 100, 1, 0.05, 0.2); p = bs_price(100, 100, 1, 0.05, 0.2, "put")
    assert approx(c, 10.4506, 1e-3)
    assert approx(put_call_parity(c, p, 100, 100, 0.05, 1), 0, 1e-9)
    assert approx(implied_vol(c, 100, 100, 1, 0.05), 0.2, 1e-4)
    assert abs(binomial_price(100, 100, 1, 0.05, 0.2, steps=500) - c) < 0.02
    assert 0.6 < bs_greeks(100, 100, 1, 0.05, 0.2)["delta"] < 0.65

def test_orderbook_signals():
    ob = OrderBook(); ob.update("bid", 99, 10); ob.update("ask", 101, 2); ob.update("ask", 102, 5)
    assert ob.mid() == 100 and ob.microprice() > 100 and ob.imbalance() > 0
    assert ob.sweep_cost("buy", 4)[0] == (2 * 101 + 2 * 102) / 4
    a, b, r2 = ols([1, 2, 3, 4], [2, 4, 6, 8]); assert approx(b, 2) and approx(r2, 1)

def test_fundamentals():
    assert approx(gordon_growth(5, 0.1, 0.05), 100)
    assert approx(npv(0.1, [-100, 110]), 0)
    assert approx(irr([-100, 110]), 0.1, 1e-6)
    assert dcf([10, 10, 10], 0.1, 0.02, net_debt=0, shares=1) > 0

def test_bots_run():
    r = backtest(lambda ex: MarketMaker(ex, "X", std=1.0, size=1, max_pos=20), steps=300)
    assert abs(r["pos"]["X"]) <= 21
    from sim.mock_exchange import MockExchange
    ex = MockExchange(syms=("E", "A", "B")); ETFArb(ex, "E", ["A", "B"], [1, 1]).step(); Flattener(ex, ["E"]).step()

if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"): fn(); print("PASS", name)
