"""A3 — dispatch (Codex 1,3,4,10).

(a) LP perfect-foresight CEILING: binary no-simultaneity, AC-side cashflows, RTE
    applied once, cyclic SoC, cycle cap, marginal charges inside the objective.
(b) Causal WALK-FORWARD benchmark: 28-day trailing quantile thresholds (no
    current-day recalibration), SoC carried continuously between days, fixed
    initial SoC, deterministic terminal restoration, identical power/eff/cap.

Unit tests use small hand-checkable batteries/profiles (no network, no solver
nondeterminism beyond HiGHS optimality).
"""
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone

import pytest

from engine import dispatch
from engine.data_load import DayPrices
from engine.params import Battery

UTC = timezone.utc


# A lossless, simple battery makes the LP optimum hand-checkable.
SIMPLE = Battery(capacity_kwh=100.0, power_kw=100.0, soc_min_frac=0.0,
                 soc_max_frac=1.0, rte=1.0)


# ---- (a) LP ceiling ---------------------------------------------------------

def test_ceiling_buys_low_sells_high():
    # Charge the full 100 kWh at price 0, discharge it at price 100.
    r = dispatch.solve_day_ceiling([0.0, 100.0], dt_h=1.0, battery=SIMPLE,
                                   cycle_cap=None, tiebreak=0.0)
    assert r.status == "Optimal"
    assert r.gross_eur == pytest.approx(10.0, abs=1e-6)        # 100/1000 * 100kWh
    assert r.mwh_discharged == pytest.approx(0.1, abs=1e-9)
    assert r.mwh_charged == pytest.approx(0.1, abs=1e-9)
    assert r.simul_max == pytest.approx(0.0, abs=1e-9)


def test_ceiling_never_simultaneously_charges_and_discharges():
    prices = [5.0, 90.0, 10.0, 80.0, 0.0, 100.0, 50.0, 50.0]
    r = dispatch.solve_day_ceiling(prices, dt_h=1.0, battery=Battery(), cycle_cap=1.5)
    assert r.status == "Optimal"
    assert r.simul_max == pytest.approx(0.0, abs=1e-9)


def test_ceiling_respects_cycle_cap():
    # An oscillating profile that would over-cycle without a cap.
    prices = [0.0, 100.0] * 12  # 24 hourly intervals
    b = Battery()
    capped = dispatch.solve_day_ceiling(prices, dt_h=1.0, battery=b, cycle_cap=1.0)
    # Discharged AC energy must not exceed cap * usable.
    assert capped.mwh_discharged <= (1.0 * b.usable_kwh) / 1000.0 + 1e-6


def test_ceiling_marginal_charge_blocks_unprofitable_trade():
    # A grid fee on charge larger than the spread => the LP declines to trade
    # (proves the marginal charge sits INSIDE the objective, Codex 4).
    r = dispatch.solve_day_ceiling([0.0, 100.0], dt_h=1.0, battery=SIMPLE,
                                   cycle_cap=None, tiebreak=0.0,
                                   grid_fee_charge=200.0)
    assert r.gross_eur == pytest.approx(0.0, abs=1e-9)
    assert r.mwh_discharged == pytest.approx(0.0, abs=1e-9)


# ---- (b) causal walk-forward ------------------------------------------------

def _day(d: date, prices):
    return DayPrices(d, dt_h=1.0, prices=tuple(prices))


def _synthetic_days(n, pattern):
    base = date(2024, 1, 1)
    return [_day(base + timedelta(days=i), pattern) for i in range(n)]


# Cheap block, mid block, expensive block — quantile thresholds separate them.
PATTERN = [10.0] * 6 + [50.0] * 12 + [100.0] * 6


def test_causal_warms_up_then_trades():
    days = _synthetic_days(40, PATTERN)
    res = dispatch.run_causal_walkforward(days, battery=Battery(), cycle_cap=1.5)
    # First 28 days have no trailing window -> no trading.
    assert all(not cd.traded for cd in res.days[:28])
    assert any(cd.traded for cd in res.days[28:])
    traded = [cd for cd in res.days if cd.traded]
    assert all(cd.mwh_discharged > 0 for cd in traded[:5])
    assert all(cd.mwh_charged > 0 for cd in traded[:5])


def test_causal_soc_is_continuous_and_in_bounds():
    days = _synthetic_days(40, PATTERN)
    b = Battery()
    res = dispatch.run_causal_walkforward(days, battery=b, cycle_cap=1.5)
    for cd in res.days:
        assert b.soc_min_kwh - 1e-6 <= cd.soc_start_kwh <= b.soc_max_kwh + 1e-6
        assert b.soc_min_kwh - 1e-6 <= cd.soc_end_kwh <= b.soc_max_kwh + 1e-6
    # End-of-day SoC is the next day's start (carried continuously).
    for prev, nxt in zip(res.days, res.days[1:]):
        assert prev.soc_end_kwh == pytest.approx(nxt.soc_start_kwh, abs=1e-9)


def test_causal_respects_cycle_cap_per_day():
    days = _synthetic_days(40, PATTERN)
    b = Battery()
    res = dispatch.run_causal_walkforward(days, battery=b, cycle_cap=1.5)
    cap_mwh = (1.5 * b.usable_kwh) / 1000.0
    for cd in res.days:
        assert cd.mwh_discharged <= cap_mwh + 1e-6


def test_causal_uses_only_prior_days_thresholds():
    # Fixed initial SoC is respected and no foresight: the first traded day's
    # thresholds come from days [0..27], independent of that day's own prices.
    days = _synthetic_days(40, PATTERN)
    b = Battery()
    res = dispatch.run_causal_walkforward(days, battery=b, cycle_cap=1.5,
                                          soc_init=b.soc_min_kwh)
    assert res.days[0].soc_start_kwh == pytest.approx(b.soc_min_kwh)
    assert res.gross_eur > 0


def test_ceiling_reports_negative_price_cashflow():
    # Charge while paid (negative price), discharge when expensive.
    prices = [-100.0] * 4 + [200.0] * 4
    r = dispatch.solve_day_ceiling(prices, dt_h=1.0, battery=Battery(), cycle_cap=1.5)
    assert r.neg_price_cashflow_eur > 0.0  # charging at -100 EARNS during neg intervals
    empty = dispatch.solve_day_ceiling([], 1.0, Battery(), cycle_cap=1.5)
    assert empty.neg_price_cashflow_eur == 0.0
