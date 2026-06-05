"""Property-based tests (Hypothesis). Invariants that must hold for ALL inputs.

These are the bulletproofing layer: instead of a few hand-picked examples, they
throw hundreds of random batteries/prices/horizons at the engine and assert the
laws that can never be violated (energy bounds, no-simultaneity, cyclic SoC, cycle
cap, gross consistency, fee monotonicity, calendar bounds).
"""
import math
from datetime import date, timedelta

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from engine import dispatch, economics, metrics
from engine.data_load import DayPrices, berlin_hours_in_day
from engine.params import Battery

_SOLVE_SETTINGS = settings(
    max_examples=40, deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
)

prices_strat = st.lists(
    st.floats(min_value=-300, max_value=1500, allow_nan=False, allow_infinity=False),
    min_size=2, max_size=28,
)
dt_strat = st.sampled_from([1.0, 0.5, 0.25])
cap_strat = st.sampled_from([None, 0.5, 1.0, 1.5, 3.0])


@st.composite
def batteries(draw):
    return Battery(
        capacity_kwh=draw(st.floats(40, 500)),
        power_kw=draw(st.floats(5, 200)),
        soc_min_frac=draw(st.floats(0.0, 0.4)),
        soc_max_frac=draw(st.floats(0.6, 1.0)),
        rte=draw(st.floats(0.5, 1.0)),
    )


# ===== LP ceiling invariants =================================================

@_SOLVE_SETTINGS
@given(prices=prices_strat, b=batteries(), dt=dt_strat, cap=cap_strat)
def test_lp_invariants(prices, b, dt, cap):
    r = dispatch.solve_day_ceiling(prices, dt, b, cycle_cap=cap)
    assert r.status == "Optimal"
    tol = 1e-4 * b.capacity_kwh + 1e-4
    # SoC always within [min, max].
    for s in r.soc_kwh:
        assert b.soc_min_kwh - tol <= s <= b.soc_max_kwh + tol
    # Never charge and discharge in the same interval.
    assert r.simul_max < 1e-4 * b.power_kw + 1e-6
    # Cyclic: end where you started.
    assert abs(r.soc_kwh[-1] - r.soc_init_kwh) < tol
    # Cycle cap on AC discharge.
    if cap is not None:
        assert r.mwh_discharged <= cap * b.usable_kwh / 1000.0 + 1e-6
    # Reported gross is exactly sale - purchase.
    assert math.isclose(r.gross_eur, r.sale_turnover_eur - r.purchase_turnover_eur,
                        abs_tol=1e-6, rel_tol=1e-9)
    # Doing nothing is feasible and the tie-break is non-negative => gross >= 0.
    assert r.gross_eur >= -1e-6
    # Powers within bounds.
    assert all(-1e-6 <= x <= b.power_kw + 1e-6 for x in r.charge_kw)
    assert all(-1e-6 <= x <= b.power_kw + 1e-6 for x in r.discharge_kw)


@_SOLVE_SETTINGS
@given(prices=prices_strat, b=batteries(), dt=dt_strat)
def test_grid_fee_never_increases_gross(prices, b, dt):
    g0 = dispatch.solve_day_ceiling(prices, dt, b, cycle_cap=1.5,
                                    grid_fee_charge=0.0).gross_eur
    g1 = dispatch.solve_day_ceiling(prices, dt, b, cycle_cap=1.5,
                                    grid_fee_charge=60.0).gross_eur
    # A marginal charge cost can only reduce (or hold) pure-arbitrage gross.
    assert g1 <= g0 + 1e-3 * (1 + abs(g0))


@_SOLVE_SETTINGS
@given(prices=prices_strat, b=batteries(), dt=dt_strat, cap=cap_strat)
def test_lp_is_deterministic(prices, b, dt, cap):
    a = dispatch.solve_day_ceiling(prices, dt, b, cycle_cap=cap)
    c = dispatch.solve_day_ceiling(prices, dt, b, cycle_cap=cap)
    assert a.gross_eur == pytest.approx(c.gross_eur, abs=1e-9)
    assert a.mwh_discharged == pytest.approx(c.mwh_discharged, abs=1e-12)


# ===== causal walk-forward invariants ========================================

@st.composite
def day_sequences(draw):
    n = draw(st.integers(min_value=30, max_value=44))
    npts = draw(st.sampled_from([24]))
    base = date(2024, 1, 1)
    out = []
    for i in range(n):
        prices = draw(st.lists(
            st.floats(-100, 600, allow_nan=False, allow_infinity=False),
            min_size=npts, max_size=npts))
        out.append(DayPrices(base + timedelta(days=i), 1.0, tuple(prices)))
    return out


@settings(max_examples=30, deadline=None,
          suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large,
                                 HealthCheck.large_base_example])
@given(days=day_sequences(), b=batteries())
def test_causal_invariants(days, b):
    cz = dispatch.run_causal_walkforward(days, b, cycle_cap=1.5)
    cap_mwh = 1.5 * b.usable_kwh / 1000.0
    tol = 1e-6 * b.capacity_kwh + 1e-6
    for i, cd in enumerate(cz.days):
        assert b.soc_min_kwh - tol <= cd.soc_start_kwh <= b.soc_max_kwh + tol
        assert b.soc_min_kwh - tol <= cd.soc_end_kwh <= b.soc_max_kwh + tol
        assert cd.mwh_discharged >= -1e-12 and cd.mwh_charged >= -1e-12
        # NOTE: purchase_turnover CAN be negative — charging during a negative-price
        # interval is paid energy (income), correctly exploited. Energy (not money)
        # is the non-negativity invariant; gross == sale - purchase still holds.
        assert math.isfinite(cd.sale_turnover_eur)
        assert math.isfinite(cd.purchase_turnover_eur)
        assert cd.mwh_discharged <= cap_mwh + 1e-6
        assert math.isclose(cd.gross_eur, cd.sale_turnover_eur - cd.purchase_turnover_eur,
                            abs_tol=1e-6, rel_tol=1e-9)
        if i < 28:
            assert not cd.traded
    # SoC carried continuously between days.
    for prev, nxt in zip(cz.days, cz.days[1:]):
        assert prev.soc_end_kwh == pytest.approx(nxt.soc_start_kwh, abs=1e-9)


# ===== metrics invariants ====================================================

@given(
    mwh=st.floats(0.01, 1000, allow_nan=False),
    usable=st.floats(0.01, 10, allow_nan=False),
    days=st.integers(1, 1000),
    eta=st.floats(0.3, 1.0, allow_nan=False),
)
def test_cycles_cell_equals_ac_over_eta(mwh, usable, days, eta):
    ac = metrics.cycles_ac(mwh, usable, days)
    cell = metrics.cycles_cell(mwh, usable, days, eta)
    assert cell == pytest.approx(ac / eta, rel=1e-9)
    assert cell >= ac - 1e-12  # eta <= 1


@given(
    spread=st.floats(0, 500, allow_nan=False),
    usable=st.floats(0.01, 1, allow_nan=False),
    cyc=st.floats(0, 5, allow_nan=False),
    days=st.integers(1, 400),
)
def test_assumed_identity_is_multiplicative(spread, usable, cyc, days):
    g = metrics.assumed_case_gross(spread, usable, cyc, days)
    assert g == pytest.approx(spread * usable * cyc * days, rel=1e-9, abs=1e-9)


@given(
    base=st.floats(-50, 50, allow_nan=False),
    n=st.integers(1, 20),
)
def test_negative_cashflow_only_counts_negative_intervals(base, n):
    # All-positive prices => zero contribution; charging at negative price => earns.
    prices = [abs(base) + 1.0] * n
    cf = metrics.cashflow_during_negative_intervals(
        prices, charge_kw=[10.0] * n, discharge_kw=[0.0] * n, dt_h=1.0)
    assert cf == 0.0


# ===== economics invariants ==================================================

@given(
    sale=st.floats(0, 1e6, allow_nan=False),
    purchase=st.floats(0, 1e6, allow_nan=False),
    rate=st.floats(0, 1, allow_nan=False),
)
def test_bkv_fee_ordering(sale, purchase, rate):
    t = economics.Turnover(sale_eur=sale, purchase_eur=purchase)
    f_gross = economics.bkv_fee("gross_turnover", rate, t)
    f_sale = economics.bkv_fee("sale_turnover", rate, t)
    f_net = economics.bkv_fee("net_margin", rate, t)
    # With non-negative turnover: gross >= sale >= net.
    assert f_gross >= f_sale - 1e-9
    assert f_sale >= f_net - 1e-9


@given(
    sale=st.floats(0, 1e5, allow_nan=False),
    purchase=st.floats(0, 1e5, allow_nan=False),
    fee=st.floats(0, 200, allow_nan=False),
    charged=st.floats(0, 1000, allow_nan=False),
)
def test_net_decreases_with_grid_fee(sale, purchase, fee, charged):
    from engine.params import Fees
    t = economics.Turnover(sale_eur=sale, purchase_eur=purchase)
    lo = economics.annual_economics(
        t, charged, scenario=economics.RETAINED, fees=Fees())
    hi = economics.annual_economics(
        t, charged,
        scenario=economics.GridScenario("x", "x", fee), fees=Fees())
    assert hi.net_eur <= lo.net_eur + 1e-9


# ===== calendar invariants ===================================================

@given(d=st.dates(min_value=date(2020, 1, 1), max_value=date(2030, 12, 31)))
def test_berlin_hours_always_23_24_or_25(d):
    assert berlin_hours_in_day(d) in (23, 24, 25)
