"""Physical and economic parameters — single place, frozen dataclasses.

Mirrors the validated spike (scripts/validate_number.py): 200 kWh / 50 kW / 4h,
SoC 10-100%, round-trip efficiency 0.90 applied ONCE in the SoC balance, so the
one-way efficiency is sqrt(0.90). All cashflows are AC-side.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from engine.contracts import FEE_BASIS_NET_MARGIN

DEFAULT_CYCLE_CAP_PER_DAY = 1.5  # business-plan cycle cap; the ceiling is reported capped


@dataclass(frozen=True)
class Battery:
    capacity_kwh: float = 200.0
    power_kw: float = 50.0
    soc_min_frac: float = 0.10
    soc_max_frac: float = 1.00
    rte: float = 0.90  # round-trip efficiency, applied once

    @property
    def soc_min_kwh(self) -> float:
        return self.soc_min_frac * self.capacity_kwh

    @property
    def soc_max_kwh(self) -> float:
        return self.soc_max_frac * self.capacity_kwh

    @property
    def usable_kwh(self) -> float:
        return self.soc_max_kwh - self.soc_min_kwh

    @property
    def usable_mwh(self) -> float:
        return self.usable_kwh / 1000.0

    @property
    def eta_one_way(self) -> float:
        # RTE applied once => charge and discharge each carry sqrt(RTE).
        return math.sqrt(self.rte)


@dataclass(frozen=True)
class BusinessPlan:
    assumed_spread_eur_mwh: float = 80.0
    assumed_cycles_per_day: float = 1.5
    operating_days: int = 365
    # The deck's headline gross. Kept for contrast only: it does NOT reconcile
    # with the identity spread*usable_MWh*cyc*days (Codex 7) — metrics computes
    # the reconciled assumed case and the honesty page shows the discrepancy.
    deck_claimed_gross_eur: float = 9947.0


@dataclass(frozen=True)
class Fees:
    """Marginal and fixed trading charges.

    Where a charge is *marginal* (changes the optimal dispatch) it must sit inside
    the dispatch objective (Codex 4): grid energy fee on charge, degradation per
    MWh of throughput. The BKV fee basis is parameterised over the three bases
    (Codex 4,14); the actual basis/rate comes from the aggregator term sheet (#8).
    """
    bkv_fee_basis: str = FEE_BASIS_NET_MARGIN
    bkv_fee_rate: float = 0.0                      # fraction of the chosen basis
    grid_energy_fee_eur_mwh_charge: float = 0.0    # 0 when §118(6) exemption retained
    degradation_eur_mwh_throughput: float = 0.0    # marginal cell-degradation cost


@dataclass(frozen=True)
class Params:
    """Bundle handed to the dispatch/economics layers."""
    battery: Battery = Battery()
    business_plan: BusinessPlan = BusinessPlan()
    fees: Fees = Fees()
    cycle_cap_per_day: float | None = DEFAULT_CYCLE_CAP_PER_DAY
    ancillary_eur: float = 0.0  # FCR/aFRR default 0 in both scenarios
