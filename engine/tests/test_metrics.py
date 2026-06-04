"""A5 — metrics (Codex 5,7,11,12,13).

- implied spread = gross / MWh discharged.
- assumed-case IDENTITY: spread x usable_MWh x cyc/day x days (+ ancillary - fees);
  reconciles the deck's €9,947 to the equation (it does NOT match -> Codex 7).
- cycles_ac (AC delivered) AND cycles_cell (cell throughput, for degradation).
- "cashflow during negative-price intervals" (renamed, Codex 12).
- IRR/payback labelled constant-EBITDA + provisional (Codex 13).
"""
import math

import pytest

from engine import metrics
from engine import contracts
from engine.params import Battery, BusinessPlan


def test_implied_spread():
    assert metrics.implied_spread(6148.0, 90.0) == pytest.approx(68.31, abs=0.01)
    assert metrics.implied_spread(0.0, 0.0) == 0.0  # no discharge -> defined as 0


def test_assumed_case_identity():
    bp = BusinessPlan()
    b = Battery()
    g = metrics.assumed_case_gross(
        spread_eur_mwh=bp.assumed_spread_eur_mwh,
        usable_mwh=b.usable_mwh,
        cycles_per_day=bp.assumed_cycles_per_day,
        operating_days=bp.operating_days,
    )
    # 80 * 0.180 * 1.5 * 365
    assert g == pytest.approx(7884.0, abs=1e-6)


def test_assumed_identity_does_not_match_deck_claim():
    # The whole point of Codex 7: the deck's headline does not reconcile.
    bp = BusinessPlan()
    b = Battery()
    identity = metrics.assumed_case_gross(
        bp.assumed_spread_eur_mwh, b.usable_mwh,
        bp.assumed_cycles_per_day, bp.operating_days,
    )
    assert identity != pytest.approx(bp.deck_claimed_gross_eur, abs=100.0)


def test_assumed_case_separates_ancillary_and_fees():
    g = metrics.assumed_case_gross(80.0, 0.18, 1.5, 365,
                                   ancillary_eur=500.0, fees_eur=300.0)
    assert g == pytest.approx(7884.0 + 500.0 - 300.0)


def test_cycles_ac():
    # 0.18 MWh discharged over 0.18 usable in 1 day = exactly 1 AC cycle.
    assert metrics.cycles_ac(0.18, 0.18, 1) == pytest.approx(1.0)


def test_cycles_cell_exceeds_ac_by_one_over_eta():
    b = Battery()
    ac = metrics.cycles_ac(0.18, b.usable_mwh, 1)
    cell = metrics.cycles_cell(0.18, b.usable_mwh, 1, b.eta_one_way)
    # The cell does MORE work than the AC output (conversion losses).
    assert cell == pytest.approx(ac / b.eta_one_way)
    assert cell > ac


def test_cashflow_during_negative_intervals():
    # Charging while price is negative EARNS money (you are paid to take energy).
    prices = [-10.0, 50.0]
    charge_kw = [100.0, 0.0]
    discharge_kw = [0.0, 100.0]
    cf = metrics.cashflow_during_negative_intervals(prices, charge_kw, discharge_kw, 1.0)
    assert cf == pytest.approx(1.0)  # (-10/1000)*(0-100)*1 = +1.0


def test_project_irr_is_provisional_and_labelled():
    m = metrics.project_irr(capex_eur=100.0, annual_ebitda_eur=110.0, years=1)
    assert m["value"] == pytest.approx(0.10, abs=1e-6)   # irr([-100, 110]) = 10%
    assert m["status"] == contracts.STATUS_PROVISIONAL
    assert "constant-EBITDA" in m["methodology_label"]


def test_project_irr_null_when_inputs_missing():
    m = metrics.project_irr(capex_eur=None, annual_ebitda_eur=110.0, years=10)
    assert m["value"] is None
    assert m["status"] == contracts.STATUS_PROVISIONAL


def test_simple_payback_is_provisional():
    m = metrics.simple_payback(capex_eur=100.0, annual_ebitda_eur=25.0)
    assert m["value"] == pytest.approx(4.0)
    assert m["status"] == contracts.STATUS_PROVISIONAL
    m2 = metrics.simple_payback(capex_eur=None, annual_ebitda_eur=25.0)
    assert m2["value"] is None
