"""Economics — BKV fee bases, named grid-fee scenarios, FCR/aFRR scaffolding.

- BKV fee on three bases (Codex 4,14): sale-turnover, gross-turnover, net-margin.
  net-margin scales the dispatch objective uniformly, so it is NON-marginal (does
  not change the optimal dispatch); the other two are marginal.
- Grid fee as two NAMED scenarios, not a slider (Codex 9): §118(6) exemption
  retained (fee 0) or lost (an energy fee per MWh charged). The lost-case value is
  PROVISIONAL pending the §118(6) legal memo (#9).
- FCR/aFRR ancillary defaults to 0; a guard forbids reserving full capacity for
  ancillary AND using full capacity for arbitrage at the same time.
"""
from __future__ import annotations

from dataclasses import dataclass

from engine import contracts
from engine.params import Battery, Fees

# PROVISIONAL — pending the §118(6) EnWG legal memo (#9). Representative German
# low-voltage grid energy charge on charged energy for a storage unit that LOSES
# the exemption. Not legal advice; the honesty page labels every figure that
# depends on this as "provisional".
PROVISIONAL_GRID_ENERGY_FEE_EUR_MWH_CHARGE = 30.0

_EPS = 1e-9


class EconomicsError(RuntimeError):
    """Raised on an economically invalid configuration (e.g. double-counted power)."""


@dataclass(frozen=True)
class Turnover:
    sale_eur: float       # revenue from discharging
    purchase_eur: float   # cost of charging (signed)

    @property
    def net_margin(self) -> float:
        return self.sale_eur - self.purchase_eur

    @property
    def gross_turnover(self) -> float:
        # |buy| + |sell| traded value. Magnitudes matter because charging during
        # negative-price intervals makes purchase_eur negative (paid energy).
        return abs(self.sale_eur) + abs(self.purchase_eur)


def bkv_fee(basis: str, rate: float, turnover: Turnover) -> float:
    """BKV fee for the given basis. Tested for all three bases."""
    if basis == contracts.FEE_BASIS_SALE_TURNOVER:
        base = turnover.sale_eur
    elif basis == contracts.FEE_BASIS_GROSS_TURNOVER:
        base = turnover.gross_turnover
    elif basis == contracts.FEE_BASIS_NET_MARGIN:
        base = turnover.net_margin
    else:
        raise ValueError(
            f"unknown BKV fee basis {basis!r}; expected one of {contracts.FEE_BASES}"
        )
    return rate * base


def is_marginal_basis(basis: str) -> bool:
    """True if the basis re-shapes the optimal dispatch (so the fee must sit inside
    the objective). net-margin is a uniform scaling -> non-marginal."""
    if basis == contracts.FEE_BASIS_NET_MARGIN:
        return False
    if basis in (contracts.FEE_BASIS_SALE_TURNOVER, contracts.FEE_BASIS_GROSS_TURNOVER):
        return True
    raise ValueError(f"unknown BKV fee basis {basis!r}")


# ---- grid-fee scenarios (named, not a slider) -------------------------------

@dataclass(frozen=True)
class GridScenario:
    id: str
    label: str
    grid_energy_fee_eur_mwh_charge: float


RETAINED = GridScenario(
    id=contracts.SCENARIO_EXEMPTION_RETAINED,
    label="§118(6) exemption retained — grid energy fee on charge = 0",
    grid_energy_fee_eur_mwh_charge=0.0,
)
LOST = GridScenario(
    id=contracts.SCENARIO_EXEMPTION_LOST,
    label="§118(6) exemption lost — provisional grid energy fee on charge (pending #9)",
    grid_energy_fee_eur_mwh_charge=PROVISIONAL_GRID_ENERGY_FEE_EUR_MWH_CHARGE,
)
SCENARIOS = (RETAINED, LOST)


@dataclass(frozen=True)
class AnnualEconomics:
    gross_arbitrage_eur: float   # net margin from the (scenario-shaped) dispatch
    grid_fee_cost_eur: float
    bkv_fee_eur: float
    ancillary_eur: float

    @property
    def net_eur(self) -> float:
        return (
            self.gross_arbitrage_eur
            - self.grid_fee_cost_eur
            - self.bkv_fee_eur
            + self.ancillary_eur
        )


def annual_economics(
    turnover: Turnover,
    charged_mwh: float,
    *,
    scenario: GridScenario,
    fees: Fees,
    ancillary_eur: float = 0.0,
) -> AnnualEconomics:
    """Combine a (scenario-specific) dispatch turnover with the BKV fee, the grid
    energy fee on charged energy, and any ancillary revenue into a net annual figure.

    `turnover` and `charged_mwh` must come from a dispatch run UNDER this scenario's
    grid fee (the fee is marginal and re-shapes dispatch). The grid-fee cost is then
    accounted explicitly here (dispatch gross is pure arbitrage).
    """
    grid_cost = scenario.grid_energy_fee_eur_mwh_charge * charged_mwh
    fee = bkv_fee(fees.bkv_fee_basis, fees.bkv_fee_rate, turnover)
    return AnnualEconomics(
        gross_arbitrage_eur=turnover.net_margin,
        grid_fee_cost_eur=grid_cost,
        bkv_fee_eur=fee,
        ancillary_eur=ancillary_eur,
    )


# ---- FCR/aFRR ancillary (default 0) -----------------------------------------

@dataclass(frozen=True)
class AncillaryReservation:
    reserved_power_kw: float = 0.0
    reserved_energy_kwh: float = 0.0
    availability_hours: float = 0.0
    capacity_price_eur_mw_h: float = 0.0  # availability/capacity price

    def revenue_eur(self) -> float:
        # Default 0: ancillary is OUT of the headline. When shown, revenue is
        # availability (capacity) price x reserved MW x available hours.
        return (
            self.capacity_price_eur_mw_h
            * (self.reserved_power_kw / 1000.0)
            * self.availability_hours
        )


def validate_ancillary_vs_arbitrage(
    reserved_power_kw: float, arbitrage_power_kw: float, battery: Battery
) -> None:
    """Forbid reserving full ancillary power AND using full arbitrage power: the
    same kW cannot be sold twice (Codex / A4 no-double-counting)."""
    if reserved_power_kw + arbitrage_power_kw > battery.power_kw + _EPS:
        raise EconomicsError(
            f"ancillary {reserved_power_kw} kW + arbitrage {arbitrage_power_kw} kW "
            f"exceeds battery power {battery.power_kw} kW (double-counted capacity)"
        )
