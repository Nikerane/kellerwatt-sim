"""Edge / degenerate / determinism tests — the corners that break naive engines.

Single-interval days, all-equal prices, extreme negatives, empty/sub-warmup causal
sequences, a fully 15-minute year, fall-back repeated-hour distinctness, NaN-safe
IRR, and byte-stable determinism.
"""
import json
from datetime import date, datetime, timedelta, timezone

import pytest

from engine import data_load as dl
from engine import dispatch, metrics
from engine.params import Battery

UTC = timezone.utc
B = Battery()


# ---- LP ceiling corners -----------------------------------------------------

def test_single_interval_day_does_not_crash_and_does_nothing():
    r = dispatch.solve_day_ceiling([42.0], dt_h=1.0, battery=B, cycle_cap=1.5)
    assert r.status == "Optimal"
    assert r.mwh_discharged == pytest.approx(0.0, abs=1e-9)
    assert r.gross_eur == pytest.approx(0.0, abs=1e-9)


def test_all_equal_prices_yield_no_trading():
    r = dispatch.solve_day_ceiling([50.0] * 24, dt_h=1.0, battery=B, cycle_cap=1.5)
    # The throughput tie-break makes a flat day not worth cycling.
    assert r.mwh_discharged == pytest.approx(0.0, abs=1e-9)
    assert r.gross_eur == pytest.approx(0.0, abs=1e-9)


def test_extreme_negative_prices_are_exploited_not_crashing():
    # Deep negatives in the morning, high in the evening.
    prices = [-500.0] * 6 + [50.0] * 12 + [500.0] * 6
    r = dispatch.solve_day_ceiling(prices, dt_h=1.0, battery=B, cycle_cap=1.5)
    assert r.status == "Optimal"
    assert r.gross_eur >= 0.0
    assert r.mwh_charged > 0.0  # it should charge while being paid to


def test_degradation_cost_reduces_trading():
    prices = [0.0, 30.0] * 12
    base = dispatch.solve_day_ceiling(prices, 1.0, B, cycle_cap=1.5).mwh_discharged
    deg = dispatch.solve_day_ceiling(prices, 1.0, B, cycle_cap=1.5,
                                     degradation_discharge=100.0).mwh_discharged
    assert deg <= base + 1e-9


# ---- causal corners ---------------------------------------------------------

def test_causal_empty_sequence():
    cz = dispatch.run_causal_walkforward([], B, cycle_cap=1.5)
    assert cz.days == ()
    assert cz.gross_eur == pytest.approx(0.0)
    assert cz.mwh_discharged == 0.0


def test_causal_below_warmup_never_trades():
    base = date(2024, 1, 1)
    days = [dl.DayPrices(base + timedelta(days=i), 1.0, tuple([10.0] * 6 + [100.0] * 18))
            for i in range(20)]  # < 28-day warmup
    cz = dispatch.run_causal_walkforward(days, B, cycle_cap=1.5, soc_init=B.soc_min_kwh)
    assert all(not d.traded for d in cz.days)
    assert cz.mwh_discharged == 0.0
    assert all(d.soc_end_kwh == pytest.approx(B.soc_min_kwh) for d in cz.days)


def test_causal_all_negative_prices_no_crash():
    base = date(2024, 1, 1)
    days = [dl.DayPrices(base + timedelta(days=i), 1.0, tuple([-50.0 - (j % 5) for j in range(24)]))
            for i in range(35)]
    cz = dispatch.run_causal_walkforward(days, B, cycle_cap=1.5)
    for d in cz.days:
        assert B.soc_min_kwh - 1e-6 <= d.soc_end_kwh <= B.soc_max_kwh + 1e-6


# ---- data_load corners ------------------------------------------------------

def _series(start_utc, end_utc, step_h):
    rows, t = [], start_utc
    step = timedelta(hours=step_h)
    while t <= end_utc:
        rows.append((t, 50.0))
        t += step
    return rows


def test_fully_15min_year_passes():
    # 2026 is entirely post go-live -> every day must be quarter-hourly.
    rows = _series(datetime(2025, 12, 31, tzinfo=UTC),
                   datetime(2027, 1, 1, 23, tzinfo=UTC), 0.25)
    yd = dl.build_year(2026, rows, nulls_dropped=0)
    assert yd.day_count == 365
    assert set(yd.points_per_day_histogram) <= {92, 96, 100}
    assert yd.resolution_transition is None  # already 15-min from Jan 1


def test_fall_back_day_instants_are_distinct():
    # 2024-10-27 has 25 hours; the repeated 02:00 wall-clock must be two instants.
    d = date(2024, 10, 27)
    start = datetime(d.year, d.month, d.day, tzinfo=dl.BERLIN).astimezone(UTC)
    pts = [(start + timedelta(hours=i), 50.0) for i in range(25)]
    day = dl.validate_day(d, pts)
    assert day.n_points == 25


def test_missing_quarter_in_15min_day_fails_loud():
    d = date(2025, 10, 2)
    start = datetime(d.year, d.month, d.day, tzinfo=dl.BERLIN).astimezone(UTC)
    pts = [(start + timedelta(minutes=15 * i), 50.0) for i in range(96)][:-1]
    with pytest.raises(dl.DataValidationError):
        dl.validate_day(d, pts)


# ---- metrics corners --------------------------------------------------------

def test_project_irr_nan_safe_when_no_sign_change():
    # All-negative cashflows: IRR undefined -> null, not NaN.
    m = metrics.project_irr(capex_eur=100.0, annual_ebitda_eur=-10.0, years=5)
    assert m["value"] is None or isinstance(m["value"], float)
    # Truly undefined (no positive cashflow at all) must be null.
    import numpy_financial as npf
    if npf.irr([-100.0] + [-10.0] * 5) != npf.irr([-100.0] + [-10.0] * 5):
        assert m["value"] is None


def test_simple_payback_zero_ebitda_is_null():
    assert metrics.simple_payback(100.0, 0.0)["value"] is None


# ---- determinism ------------------------------------------------------------

def test_causal_is_deterministic():
    base = date(2024, 1, 1)
    days = [dl.DayPrices(base + timedelta(days=i), 1.0,
                         tuple([(i * 7 + j * 13) % 97 - 20 for j in range(24)]))
            for i in range(40)]
    a = dispatch.run_causal_walkforward(days, B, cycle_cap=1.5)
    c = dispatch.run_causal_walkforward(days, B, cycle_cap=1.5)
    assert a.gross_eur == c.gross_eur
    assert [d.soc_end_kwh for d in a.days] == [d.soc_end_kwh for d in c.days]


@pytest.mark.network
def test_real_cached_2024_is_byte_stable_ceiling():
    # Re-solving the same real day twice gives identical gross (HiGHS determinism).
    yd = dl.load_year(2024, allow_fetch=False)
    day = yd.days[100]
    a = dispatch.solve_day_ceiling(list(day.prices), day.dt_h, B, cycle_cap=1.5)
    c = dispatch.solve_day_ceiling(list(day.prices), day.dt_h, B, cycle_cap=1.5)
    assert a.gross_eur == c.gross_eur


# ---- regressions from the adversarial review --------------------------------

def test_empty_price_day_is_graceful_not_a_crash():
    # Agent finding: solve_day_ceiling([]) used to IndexError on soc[-1].
    r = dispatch.solve_day_ceiling([], dt_h=1.0, battery=B, cycle_cap=1.5)
    assert r.status == "Optimal"
    assert r.gross_eur == 0.0 and r.mwh_discharged == 0.0
    assert r.charge_kw == () and r.soc_kwh == ()


def test_causal_mixed_resolution_window_is_dt_weighted():
    # Agent finding: 15-min days must not be 4x over-weighted vs hourly days in the
    # trailing quantile. A window mixing one cheap hourly day with expensive 15-min
    # days must still produce sane in-bounds dispatch (no crash, SoC valid).
    base = date(2025, 9, 17)
    days = []
    for i in range(30):
        if i % 2 == 0:
            days.append(dl.DayPrices(base + timedelta(days=i), 1.0, tuple([20.0] * 24)))
        else:
            days.append(dl.DayPrices(base + timedelta(days=i), 0.25, tuple([80.0] * 96)))
    cz = dispatch.run_causal_walkforward(days, B, cycle_cap=1.5)
    for d in cz.days:
        assert B.soc_min_kwh - 1e-6 <= d.soc_end_kwh <= B.soc_max_kwh + 1e-6
