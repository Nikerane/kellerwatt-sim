"""A4 — economics. BKV fee on all three bases (Codex 4,14); grid fee as two NAMED
scenarios, not a slider (Codex 9); FCR/aFRR default 0 with a no-double-counting
guard forbidding full-capacity ancillary AND full-capacity arbitrage together.
"""
import pytest

from engine import economics as ec
from engine import contracts
from engine.params import Battery, Fees


# A hand-checkable turnover: sold 100 MWh-worth for €8000, bought for €5000.
TURN = ec.Turnover(sale_eur=8000.0, purchase_eur=5000.0)


def test_turnover_derived_quantities():
    assert TURN.net_margin == pytest.approx(3000.0)        # 8000 - 5000
    assert TURN.gross_turnover == pytest.approx(13000.0)   # 8000 + 5000


def test_bkv_fee_sale_turnover_basis():
    fee = ec.bkv_fee(contracts.FEE_BASIS_SALE_TURNOVER, 0.05, TURN)
    assert fee == pytest.approx(0.05 * 8000.0)


def test_bkv_fee_gross_turnover_basis():
    fee = ec.bkv_fee(contracts.FEE_BASIS_GROSS_TURNOVER, 0.05, TURN)
    assert fee == pytest.approx(0.05 * 13000.0)


def test_bkv_fee_net_margin_basis():
    fee = ec.bkv_fee(contracts.FEE_BASIS_NET_MARGIN, 0.05, TURN)
    assert fee == pytest.approx(0.05 * 3000.0)


def test_bkv_fee_unknown_basis_raises():
    with pytest.raises(ValueError):
        ec.bkv_fee("turnover_of_the_moon", 0.05, TURN)


def test_net_margin_basis_is_non_marginal_others_are():
    # net_margin scales the objective uniformly -> does not change dispatch.
    assert ec.is_marginal_basis(contracts.FEE_BASIS_NET_MARGIN) is False
    assert ec.is_marginal_basis(contracts.FEE_BASIS_SALE_TURNOVER) is True
    assert ec.is_marginal_basis(contracts.FEE_BASIS_GROSS_TURNOVER) is True


# ---- grid-fee scenarios (named, not a slider) -------------------------------

def test_two_named_scenarios_exist_with_correct_ids():
    ids = {s.id for s in ec.SCENARIOS}
    assert ids == set(contracts.SCENARIO_IDS)
    assert ec.RETAINED.grid_energy_fee_eur_mwh_charge == 0.0
    assert ec.LOST.grid_energy_fee_eur_mwh_charge > 0.0  # provisional, pending #9


def test_annual_economics_retained_equals_gross_when_no_fees():
    f = Fees()  # zero BKV, zero degradation
    a = ec.annual_economics(TURN, charged_mwh=100.0, scenario=ec.RETAINED, fees=f)
    assert a.grid_fee_cost_eur == pytest.approx(0.0)
    assert a.bkv_fee_eur == pytest.approx(0.0)
    assert a.net_eur == pytest.approx(TURN.net_margin)


def test_annual_economics_lost_subtracts_grid_fee_on_charge():
    f = Fees()
    charged = 100.0
    a = ec.annual_economics(TURN, charged_mwh=charged, scenario=ec.LOST, fees=f)
    expected_cost = ec.LOST.grid_energy_fee_eur_mwh_charge * charged
    assert a.grid_fee_cost_eur == pytest.approx(expected_cost)
    assert a.net_eur == pytest.approx(TURN.net_margin - expected_cost)


def test_annual_economics_applies_bkv_and_ancillary():
    f = Fees(bkv_fee_basis=contracts.FEE_BASIS_NET_MARGIN, bkv_fee_rate=0.10)
    a = ec.annual_economics(TURN, charged_mwh=100.0, scenario=ec.RETAINED,
                            fees=f, ancillary_eur=500.0)
    assert a.bkv_fee_eur == pytest.approx(0.10 * 3000.0)
    assert a.ancillary_eur == pytest.approx(500.0)
    assert a.net_eur == pytest.approx(3000.0 - 300.0 + 500.0)


# ---- FCR/aFRR ancillary -----------------------------------------------------

def test_ancillary_defaults_to_zero():
    res = ec.AncillaryReservation()
    assert res.reserved_power_kw == 0.0
    assert res.revenue_eur() == 0.0


def test_ancillary_full_plus_full_arbitrage_is_forbidden():
    b = Battery()  # 50 kW
    # Reserving all 50 kW for ancillary AND using all 50 kW for arbitrage is double-use.
    with pytest.raises(ec.EconomicsError):
        ec.validate_ancillary_vs_arbitrage(
            reserved_power_kw=b.power_kw, arbitrage_power_kw=b.power_kw, battery=b
        )


def test_ancillary_partial_split_is_allowed():
    b = Battery()
    # 20 kW reserved + 30 kW arbitrage == 50 kW total: allowed.
    ec.validate_ancillary_vs_arbitrage(
        reserved_power_kw=20.0, arbitrage_power_kw=30.0, battery=b
    )
