import os, sys, math, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tt import *
from sim.mock_exchange import backtest
from bots.strategies import MarketMaker, ETFArb, Flattener
from bots.adapter import RiskGuard

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

def test_fast_dice_and_deck():
    import itertools
    from collections import Counter
    brute = Counter(sum(r) for r in itertools.product(range(1, 7), repeat=4))
    fast = dice_dist(4)
    assert all(approx(fast[k], v / 6 ** 4, 1e-12) for k, v in brute.items())
    assert approx(stats(dice_dist(50))["mean"], 175)                 # instant, used to be impossible
    assert approx(stats(dice_dist(3, func=max))["mean"], 119 / 24)
    assert approx(stats(dice_dist(3, func=min))["mean"], 49 / 24)
    assert approx(sum(dist_of_sum([{0: .5, 1: .5}] * 10).values()), 1)
    d = Deck(); d.seen(13, 13, 13, 13)
    assert len(d) == 48 and approx(d.p(lambda c: c == 13), 0)
    mu, sd = d.sum_fair(2); ex = stats(d.draw_dist(2))
    assert approx(mu, ex["mean"]) and approx(sd, ex["std"], 1e-9)
    assert binom_pmf(-1, 5, .5) == 0 and binom_pmf(6, 5, .5) == 0
    assert binary_ladder_check([30, 30, 30])[1].startswith("buy all")
    assert binary_ladder_check([0.5, 0.6])[1].startswith("sell all")
    assert binary_ladder_check([50, 50])[1] == "ok"

def test_book_realized():
    bk = Book(); bk.fill("X", "buy", 10, 34); bk.fill("X", "buy", 10, 36)
    assert approx(bk.avg_cost("X"), 35)
    bk.fill("X", "sell", 5, 40)
    assert approx(bk.realized["X"], 25) and approx(bk.avg_cost("X"), 35)
    bk.fill("X", "sell", 20, 30)                                     # flip to short 5 @ 30
    assert bk.pos["X"] == -5 and approx(bk.avg_cost("X"), 30) and approx(bk.realized["X"], 25 - 75)
    assert approx(bk.realized["X"] + bk.unrealized("X", 31), bk.pnl({"X": 31}))
    bk.report({"X": 31})

def test_options_extras():
    assert implied_vol(0.001, 100, 100, 1, 0.0) is not None
    assert implied_vol(200, 100, 100, 1, 0.0) is None                 # above no-arb bound
    for sig in (0.05, 0.2, 0.8, 2.0):
        p = bs_price(100, 120, 0.5, 0.01, sig, "put")
        iv = implied_vol(p, 100, 120, 0.5, 0.01, "put")             # deep ITM low vol is ill-conditioned:
        assert approx(bs_price(100, 120, 0.5, 0.01, iv, "put"), p, 1e-6)  # check the price round-trips
    assert bs_greeks(110, 100, 0, 0, 0.2)["delta"] == 1.0
    quotes = {K: bs_price(100, K, 0.25, 0, 0.2 + 0.0004 * (K - 100) ** 2) for K in range(80, 121, 5)}
    quotes[105] += 1.0                                               # plant a rich strike
    flags = {K: fl for K, _, _, _, fl in smile_scan(100, 0.25, 0, quotes)}
    assert flags[105] == "RICH" and sum(1 for f in flags.values() if f) == 1
    g = portfolio_greeks(100, 0, [(1, 100, 1, .2, "call"), (-0.5, None, None, None, "stock")])
    assert abs(g["delta"] - (bs_greeks(100, 100, 1, 0, .2)["delta"] - .5)) < 1e-12

def test_bots_respect_limits():
    from sim.mock_exchange import MockExchange
    for sd in range(5):
        r = backtest(lambda ex: MarketMaker(ex, "X", std=1.0, size=3, max_pos=10), steps=500, seed=sd)
        assert abs(r["pos"]["X"]) <= 10, r
    ex = MockExchange(); mm = MarketMaker(ex, "X", std=1.0, size=1, max_pos=20)
    for _ in range(50): mm.step(); ex.tick()
    assert len(ex.orders) <= 4                                       # no leaked resting orders
    g = RiskGuard(MockExchange(), max_pos={"X": 5}, max_qty=3)
    assert g.place("X", "buy", 3, 100) is not None and g.place("X", "buy", 3, 100) is None  # pending counts
    assert g.place("X", "buy", 4, 100) is None and g.blocked == 2

def test_live_console():
    import io, contextlib, tempfile, live
    d = tempfile.mkdtemp(); live.SAVE = os.path.join(d, "f.csv")
    with contextlib.redirect_stdout(io.StringIO()):
        for cmd in ["b X 10 34", "s X 4 37", "f X 35 5", "q X", "t X 20 21", "gm X 40", "fairs",
                    "seen K K A 7", "cards 2", "dice 10", "ladder 30 30 30", "py y = 2", "py y + 1",
                    "b Y 1k 1.5", "undo", "p"]:
            live.run(cmd)
    assert live.book.pos["X"] == 6 and "Y" not in {k for k, v in live.book.pos.items() if v}
    assert len(live.deck) == 48 and live.ns["y"] == 2 and live.fairs["X"][0] > 35
    assert live.num("1.5m") == 1.5e6

def test_drills_answers_valid():
    import drill
    drill.R.seed(0)
    for cat, gen in drill.CATS.items():
        for _ in range(60):
            prompt, truth, tol, _ = gen()
            assert isinstance(prompt, str) and math.isfinite(truth) and tol > 0, (cat, prompt)
            assert drill.ok(truth, truth, tol)
    assert approx(drill._reroll_ev(2), 4.25) and approx(drill._reroll_ev(3), 14 / 3)
    assert drill.parse("7/2") == 3.5 and drill.parse("35%") == 0.35 and drill.parse("-1.5") == -1.5
    assert drill.ok(35, 0.35, 0.005) and not drill.ok(0.5, 0.35, 0.005)

def test_game_oracle_profits():
    import game
    for sd in range(5):                       # trading toward TRUE value must make money; doing nothing = 0
        g = game.Game(30, seed=sd)
        while g.t < g.turns:
            g.step_world(); q = g.quotes()
            for s in ["A", "B", "C", "ETF"]:
                tv = g.etf_true() if s == "ETF" else g.true[s]; b, a = q[s]; p = g.book.pos[s]
                if a < tv - 0.2 and p < 40: g.trade(s, "buy", 5, a)
                elif b > tv + 0.2 and p > -40: g.trade(s, "sell", 5, b)
            g.flow_vs_mm(); g.check_limits()
        assert g.settle()[0] > 0 and g.penalties == 0
        idle = game.Game(10, seed=sd)
        while idle.t < idle.turns: idle.step_world(); idle.quotes(); idle.flow_vs_mm()
        assert idle.settle()[0] == 0

def test_live_new_commands():
    import io, contextlib, tempfile, live
    live.SAVE = os.path.join(tempfile.mkdtemp(), "f.csv")
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        for cmd in ["mkt dice 3 as D3", "mkt fermi 100 10000 as F", "mkt 35 5", "f N 100 2",
                    "news N -10 0.5 0", "fermi 10 1000", "lim N 3", "b N 5 95", "settle N 90"]:
            live.run(cmd)
    assert approx(live.fairs["D3"][0], 10.5) and approx(live.fairs["F"][0], 1000)
    assert approx(live.fairs["N"][0], 95) and "GET BACK INSIDE" in out.getvalue()
    assert live.marks["N"] == 90 and live.tick_for(10) == 1.0 and live.tick_for(0.1) == 0.01

def test_tender_eval():
    book = {"bids": [(10.0, 500), (9.9, 500)], "asks": [(10.1, 500), (10.2, 500)]}
    r = tender_eval("buy", 1000, 9.80, book)                         # unwind avg 9.95 -> +0.15/sh
    assert approx(r["edge_per_share"], 0.15) and r["verdict"] == "ACCEPT"
    assert tender_eval("sell", 1000, 10.05, book)["verdict"] == "DECLINE"   # buy back avg 10.15 > 10.05
    r = tender_eval("buy", 2000, 9.50, book, fair=9.7)                # only 1000 visible
    assert r["filled_now"] == 1000 and "work the rest" in r["verdict"]
    assert approx(r["profit"], 500 * 10 + 500 * 9.9 + 1000 * 9.7 - 2000 * 9.5)

def test_rit_adapter_against_fake_server():
    import socket
    from sim.fake_rit import serve
    from bots.rit import RIT, RITError
    with socket.socket() as sk: sk.bind(("127.0.0.1", 0)); port = sk.getsockname()[1]
    srv, st = serve(port=port, key="K", background=True)
    try:
        url = f"http://127.0.0.1:{port}/v1"
        try: RIT("WRONG", url).case(); assert False
        except RITError as e: assert "401" in str(e)
        ex = RIT("K", url, max_order_size=300)
        for _ in range(30): ex.case()                                    # crosses a 429 -> retried
        assert ex.is_active() and set(ex.symbols()) == {"CRZY", "TAME"}
        b, bs, a, as_ = ex.get_book("CRZY"); assert b < a and bs > 0
        oid = ex.place("CRZY", "buy", 700, 9.5)                          # split 300/300/100
        assert len(st.orders) == 3 and max(o["quantity"] for o in st.orders.values()) == 300
        ex.cancel(oid); assert len(st.orders) == 2
        ex.cancel_all(); assert not st.orders
        ex.market("TAME", "sell", 400); assert ex.get_position("TAME") == -400
        ex.flatten(); assert ex.positions()["TAME"] == 0
        assert ex.news()[0]["headline"] and ex.news(since=1) == []
        import bots.run_rit as runner
        runner.TENDER_MIN_EDGE = 0.0
        with contextlib_quiet(): runner.handle_tenders(ex, set(), live=True)
        assert st.accepted == [7] and ex.get_position("CRZY") == 1000
        try: RIT("K", "http://127.0.0.1:1/v1", timeout=0.2).case(); assert False
        except RITError as e: assert "Is the RIT client open" in str(e)
    finally:
        srv.shutdown()

def test_valuation_kit():
    # flat business: no growth, FCF = EBIT(1-t) when D&A = capex and NWC flat -> perpetuity
    r = dcf_build(1000, 0.0, 0.2, 0.10, 0.0, years=5, tax=0.25, da_pct=0.05, capex_pct=0.05, nwc_pct=0.0, verbose=False)
    assert approx(r["ev"], 150 / 0.10, 1e-6)
    r2 = dcf_build(1000, 0.0, 0.2, 0.10, 0.0, years=5, tax=0.25, da_pct=0.05, capex_pct=0.05, nwc_pct=0.0,
                   exit_multiple=8, verbose=False)
    assert approx(r2["pv_tv"], 8 * 250 / 1.1 ** 5, 1e-6)
    g = sensitivity(lambda a, b: a * 10 + b, [1, 2], [3, 4]); assert g == [[13, 14], [23, 24]]
    c = comps_value(100, [8, 10, 12], net_debt=200, shares=10); assert c["median"] == 80 and c["low"] == 60
    assert comps_value(2, [15, 20], ev_based=False)["median"] == 35
    vf = lambda gg: dcf_build(1000, 0.05, 0.2, 0.09, gg, verbose=False)["per_share"]
    ig = implied_terminal_growth(vf(0.03), vf, hi=0.085); assert approx(ig, 0.03, 1e-6)
    assert approx(relever_beta(unlever_beta(1.2, 0.5, 0.25), 0.5, 0.25), 1.2)
    with contextlib_quiet():
        print_grid(g, [1, 2], [3, 4], pct=False, mark=15); football_field({"a": (1, 2), "b": (1.5, 3)}, price=2)
        import valuation; valuation.main()

def test_merger_and_live_deal():
    assert approx(merger_value(50, 30, 0.8), 46) and approx(implied_deal_prob(46, 50, 30), 0.8)
    assert approx(stock_offer_value(0.5, 80, 5), 45)
    import io, contextlib, live
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        live.run("deal 50 30 46 0.9"); live.run("tender buy 1000 9.8 10 500 9.9 500")
    assert "80.0%" in out.getvalue() and "BUY" in out.getvalue() and "ACCEPT" in out.getvalue()

def contextlib_quiet():
    import contextlib, io
    return contextlib.redirect_stdout(io.StringIO())

if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"): fn(); print("PASS", name)
