"""Metrics — spreads, the reconciled assumed case, AC vs cell cycles, the
negative-price cashflow metric, and provisional IRR/payback.

Every economically firm metric is computed from the SAME equations (Codex 7); the
deck's stored constants are never trusted. IRR/payback are labelled
"constant-EBITDA" and carry status "provisional" until #8 (fee basis) and #9
(grid-fee scenario value) land (Codex 13).
"""
from __future__ import annotations

from typing import Sequence

import numpy_financial as npf

from engine import contracts


def implied_spread(gross_eur: float, mwh_discharged: float) -> float:
    """Captured spread = gross / MWh discharged (Codex 5)."""
    return gross_eur / mwh_discharged if mwh_discharged else 0.0


def assumed_case_gross(
    spread_eur_mwh: float,
    usable_mwh: float,
    cycles_per_day: float,
    operating_days: int,
    *,
    ancillary_eur: float = 0.0,
    fees_eur: float = 0.0,
) -> float:
    """Assumed-case identity (Codex 7): reconcile the assumed gross from the same
    equation rather than a stored constant. Ancillary added and fees subtracted as
    clearly separated lines."""
    return spread_eur_mwh * usable_mwh * cycles_per_day * operating_days + ancillary_eur - fees_eur


def cycles_ac(mwh_discharged: float, usable_mwh: float, day_count: int) -> float:
    """AC-delivered equivalent full cycles = AC discharge / (usable x days)."""
    denom = usable_mwh * day_count
    return mwh_discharged / denom if denom else 0.0


def cell_throughput_mwh(mwh_discharged: float, eta_one_way: float) -> float:
    """Cell-side (DC) discharge throughput. To deliver E_ac the cell loses E_ac/eta."""
    return mwh_discharged / eta_one_way


def cycles_cell(
    mwh_discharged: float, usable_mwh: float, day_count: int, eta_one_way: float
) -> float:
    """Cell-throughput equivalent full cycles (Codex 11) — use for degradation /
    lifetime claims. Exceeds cycles_ac by 1/eta (the cell works harder than the AC
    output)."""
    denom = usable_mwh * day_count
    return cell_throughput_mwh(mwh_discharged, eta_one_way) / denom if denom else 0.0


def cashflow_during_negative_intervals(
    prices: Sequence[float],
    charge_kw: Sequence[float],
    discharge_kw: Sequence[float],
    dt_h: float,
) -> float:
    """Net AC cashflow occurring while the price is negative (Codex 12). This is a
    factual 'cashflow during negative-price intervals', NOT a causal attribution of
    profit to negative prices."""
    return sum(
        (p / 1000.0) * (discharge_kw[t] - charge_kw[t]) * dt_h
        for t, p in enumerate(prices)
        if p < 0
    )


def project_irr(capex_eur, annual_ebitda_eur, years) -> dict:
    """UNLEVERED (all-equity) constant-EBITDA project IRR — provisional (Codex 13).

    IRR([-capex, ebitda, ...]) carries no debt: a levered/equity IRR needs a
    financing structure (debt fraction, rate, tenor) and would typically be higher
    under positive leverage. Null until a real annual cashflow model (degradation,
    replacement, terminal value) and the diligence inputs (#8 fee basis, #9
    grid-fee value) exist."""
    if capex_eur is None or annual_ebitda_eur is None or years is None:
        value = None
    else:
        cashflows = [-capex_eur] + [annual_ebitda_eur] * int(years)
        irr = npf.irr(cashflows)
        value = None if irr is None or (irr != irr) else float(irr)  # NaN-safe
    return contracts.metric(
        value, "ratio", "unlevered constant-EBITDA project IRR", contracts.STATUS_PROVISIONAL
    )


def simple_payback(capex_eur, annual_ebitda_eur) -> dict:
    """Simple payback = CapEx / annual EBITDA — provisional, same caveats as IRR."""
    if capex_eur is None or not annual_ebitda_eur:
        value = None
    else:
        value = float(capex_eur) / float(annual_ebitda_eur)
    return contracts.metric(
        value, "years", "unlevered constant-EBITDA payback", contracts.STATUS_PROVISIONAL
    )
