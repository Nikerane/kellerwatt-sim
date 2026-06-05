"""A6 — backtest. 2023-2025, day-by-day, cached LP dispatch, BOTH strategies.

Aggregation is factored into pure functions tested with synthetic dispatches (no
solving). A slower @network test runs the real LP backtest for one year and checks
the validated ceiling (the full per-year fixture lock-in lives in A8).
"""
import pytest

from engine import backtest as bt
from engine import dispatch
from engine.params import Battery, Params
from engine.metrics import implied_spread, cycles_ac, cycles_cell


def _fake_day(gross, dis, chg, sale, purchase, simul=0.0):
    return dispatch.DayDispatch(
        gross_eur=gross, mwh_discharged=dis, mwh_charged=chg,
        sale_turnover_eur=sale, purchase_turnover_eur=purchase,
        simul_max=simul, status="Optimal",
        charge_kw=(), discharge_kw=(), soc_kwh=(), soc_init_kwh=0.0,
    )


def test_aggregate_ceiling_sums_and_derives():
    b = Battery()
    days = [
        _fake_day(100.0, 1.0, 1.1, 120.0, 20.0),
        _fake_day(50.0, 0.5, 0.55, 60.0, 10.0),
    ]
    sy = bt.aggregate_ceiling(days, b, year=2024, day_count=2)
    assert sy.gross_eur == pytest.approx(150.0)
    assert sy.mwh_discharged == pytest.approx(1.5)
    assert sy.mwh_charged == pytest.approx(1.65)
    assert sy.sale_turnover_eur == pytest.approx(180.0)
    assert sy.purchase_turnover_eur == pytest.approx(30.0)
    assert sy.simul_max == pytest.approx(0.0)
    assert sy.implied_spread == pytest.approx(implied_spread(150.0, 1.5))
    assert sy.cycles_ac == pytest.approx(cycles_ac(1.5, b.usable_mwh, 2))
    assert sy.cycles_cell == pytest.approx(cycles_cell(1.5, b.usable_mwh, 2, b.eta_one_way))
    assert sy.cycles_cell > sy.cycles_ac


def test_aggregate_ceiling_propagates_simul_max():
    b = Battery()
    days = [_fake_day(1.0, 0.1, 0.1, 1.0, 0.0, simul=0.0),
            _fake_day(1.0, 0.1, 0.1, 1.0, 0.0, simul=1e-7)]
    sy = bt.aggregate_ceiling(days, b, year=2024, day_count=2)
    assert sy.simul_max == pytest.approx(1e-7)


def test_aggregate_causal_per_year():
    b = Battery()
    # Two-day causal result spanning one year.
    from datetime import date
    cd = [
        dispatch.CausalDay(date(2024, 1, 1), 30.0, 28.0, 0.3, 0.33, 40.0, 10.0, 20.0, 50.0, True),
        dispatch.CausalDay(date(2024, 1, 2), 20.0, 19.0, 0.2, 0.22, 25.0, 5.0, 50.0, 30.0, True),
    ]
    cz = dispatch.CausalResult(tuple(cd), 20.0, 30.0, 0.0, 50.0)
    by_year = bt.aggregate_causal(cz, b, {2024: 2})
    sy = by_year[2024]
    assert sy.gross_eur == pytest.approx(50.0)
    assert sy.mwh_discharged == pytest.approx(0.5)
    assert sy.simul_max == 0.0
    assert sy.implied_spread == pytest.approx(implied_spread(50.0, 0.5))


@pytest.mark.network
def test_real_backtest_one_year_matches_validated_ceiling():
    res = bt.run_backtest(years=(2024,), params=Params())
    sy = res.ceiling[2024]
    assert sy.implied_spread == pytest.approx(68.3, abs=0.2)
    assert sy.day_count == 366
    assert sy.simul_max < 1e-6
    # Causal is a (lower) benchmark, reported as an estimate.
    assert res.causal[2024].gross_eur < sy.gross_eur


def test_aggregate_ceiling_sums_neg_price_cashflow():
    b = Battery()
    days = [_fake_day(100.0, 1.0, 1.1, 120.0, 20.0), _fake_day(50.0, 0.5, 0.55, 60.0, 10.0)]
    sy = bt.aggregate_ceiling(days, b, year=2024, day_count=2)
    assert sy.neg_price_cashflow_eur == pytest.approx(0.0)
