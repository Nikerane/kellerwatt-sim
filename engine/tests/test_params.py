"""A1 — params. The physical/economic constants must match the validated spike
(scripts/validate_number.py): 200 kWh / 50 kW / 4h, SoC 10-100%, RTE 0.90 applied
once (eta = sqrt(0.90)). Business-plan assumptions and fee defaults are pinned here.
"""
import math

from engine import params
from engine.contracts import FEE_BASIS_NET_MARGIN, FEE_BASES


def test_battery_defaults_match_spike():
    b = params.Battery()
    assert b.capacity_kwh == 200.0
    assert b.power_kw == 50.0
    assert b.soc_min_frac == 0.10
    assert b.soc_max_frac == 1.00
    assert b.rte == 0.90


def test_battery_derived_quantities():
    b = params.Battery()
    assert b.soc_min_kwh == 20.0          # 0.10 * 200
    assert b.soc_max_kwh == 200.0         # 1.00 * 200
    assert b.usable_kwh == 180.0          # max - min
    assert b.usable_mwh == 0.180
    # RTE applied ONCE in the SoC balance => one-way eta is sqrt(RTE).
    assert math.isclose(b.eta_one_way, math.sqrt(0.90), rel_tol=0, abs_tol=1e-12)


def test_business_plan_assumptions():
    bp = params.BusinessPlan()
    assert bp.assumed_spread_eur_mwh == 80.0
    assert bp.assumed_cycles_per_day == 1.5
    assert bp.operating_days == 365
    # The deck's headline gross — carried for contrast; it does NOT reconcile with
    # the identity spread*usable*cyc*days (Codex 7). metrics computes the identity.
    assert bp.deck_claimed_gross_eur == 9947.0


def test_default_fees_are_zero_and_net_margin_basis():
    f = params.Fees()
    assert f.bkv_fee_basis in FEE_BASES
    assert f.bkv_fee_basis == FEE_BASIS_NET_MARGIN
    assert f.bkv_fee_rate == 0.0
    assert f.grid_energy_fee_eur_mwh_charge == 0.0   # retained-exemption default
    assert f.degradation_eur_mwh_throughput == 0.0


def test_cycle_cap_default():
    assert params.DEFAULT_CYCLE_CAP_PER_DAY == 1.5
