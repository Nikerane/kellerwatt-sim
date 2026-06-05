"""A6 — backtest. Run BOTH strategies over 2023-2025, day by day.

The LP ceiling is solved per delivery day (cached to disk so re-runs are instant).
The causal walk-forward runs once, continuously across the whole horizon (SoC
carried between years), and is aggregated per year. Aggregation is factored into
pure functions so it can be unit-tested without solving.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from engine import dispatch
from engine.data_load import CACHE_DIR, YearData, load_year
from engine.metrics import cycles_ac, cycles_cell, implied_spread
from engine.params import Battery, Params


@dataclass(frozen=True)
class StrategyYear:
    year: int
    day_count: int
    gross_eur: float
    mwh_discharged: float
    mwh_charged: float
    sale_turnover_eur: float
    purchase_turnover_eur: float
    cycles_ac: float
    cycles_cell: float
    simul_max: float
    implied_spread: float
    traded_days: int | None = None  # causal only; None for the always-on ceiling
    neg_price_cashflow_eur: float | None = None  # ceiling only (Codex 12)


@dataclass(frozen=True)
class BacktestResult:
    years: tuple
    ceiling: dict
    causal: dict
    causal_terminal_value_eur: float
    year_data: dict  # year -> YearData (for negative-price metrics etc.)
    causal_result: dispatch.CausalResult | None = None  # raw per-day causal data


# ---- pure aggregation -------------------------------------------------------

def aggregate_ceiling(days, battery: Battery, year: int, day_count: int) -> StrategyYear:
    gross = sum(d.gross_eur for d in days)
    mdis = sum(d.mwh_discharged for d in days)
    mchg = sum(d.mwh_charged for d in days)
    sale = sum(d.sale_turnover_eur for d in days)
    purchase = sum(d.purchase_turnover_eur for d in days)
    simul = max((d.simul_max for d in days), default=0.0)
    neg_cf = sum(d.neg_price_cashflow_eur for d in days)
    return StrategyYear(
        year=year,
        day_count=day_count,
        gross_eur=gross,
        mwh_discharged=mdis,
        mwh_charged=mchg,
        sale_turnover_eur=sale,
        purchase_turnover_eur=purchase,
        cycles_ac=cycles_ac(mdis, battery.usable_mwh, day_count),
        cycles_cell=cycles_cell(mdis, battery.usable_mwh, day_count, battery.eta_one_way),
        simul_max=simul,
        implied_spread=implied_spread(gross, mdis),
        neg_price_cashflow_eur=neg_cf,
    )


def aggregate_causal(causal: dispatch.CausalResult, battery: Battery,
                     day_counts: dict) -> dict:
    out = {}
    for year, agg in causal.per_year().items():
        dc = day_counts.get(year, agg["days"])
        out[year] = StrategyYear(
            year=year,
            day_count=dc,
            gross_eur=agg["gross"],
            mwh_discharged=agg["dis"],
            mwh_charged=agg["chg"],
            sale_turnover_eur=agg["sale"],
            purchase_turnover_eur=agg["purchase"],
            cycles_ac=cycles_ac(agg["dis"], battery.usable_mwh, dc),
            cycles_cell=cycles_cell(agg["dis"], battery.usable_mwh, dc, battery.eta_one_way),
            simul_max=0.0,  # causal is mutually exclusive by construction
            implied_spread=implied_spread(agg["gross"], agg["dis"]),
            traded_days=agg["traded_days"],
        )
    return out


# ---- cached LP day-solves ---------------------------------------------------

def _ceiling_signature(battery: Battery, cycle_cap, grid_fee, deg, tiebreak) -> str:
    payload = json.dumps({
        "cap_kwh": battery.capacity_kwh, "power": battery.power_kw,
        "smin": battery.soc_min_frac, "smax": battery.soc_max_frac, "rte": battery.rte,
        "cycle_cap": cycle_cap, "grid_fee": grid_fee, "deg": deg, "tie": tiebreak,
        "cache_v": 2,  # bumped when the cached row schema changes (neg_cf added)
    }, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def _solve_ceiling_days(year_data: YearData, battery: Battery, *, cycle_cap, grid_fee,
                        deg, tiebreak, use_cache, solver):
    sig = _ceiling_signature(battery, cycle_cap, grid_fee, deg, tiebreak)
    cache_path = CACHE_DIR / f"ceiling_{year_data.year}_{sig}.json"
    if use_cache and cache_path.is_file():
        rows = json.loads(cache_path.read_text())
        return [
            dispatch.DayDispatch(
                gross_eur=r["gross"], mwh_discharged=r["dis"], mwh_charged=r["chg"],
                sale_turnover_eur=r["sale"], purchase_turnover_eur=r["purchase"],
                neg_price_cashflow_eur=r.get("neg_cf", 0.0),
                simul_max=r["simul"], status="Optimal",
                charge_kw=(), discharge_kw=(), soc_kwh=(), soc_init_kwh=0.0,
            )
            for r in rows
        ]
    days = []
    rows = []
    for day in year_data.days:
        r = dispatch.solve_day_ceiling(
            list(day.prices), day.dt_h, battery, cycle_cap=cycle_cap,
            grid_fee_charge=grid_fee, degradation_discharge=deg,
            tiebreak=tiebreak, solver=solver,
        )
        days.append(r)
        rows.append({"gross": r.gross_eur, "dis": r.mwh_discharged,
                     "chg": r.mwh_charged, "sale": r.sale_turnover_eur,
                     "purchase": r.purchase_turnover_eur, "simul": r.simul_max,
                     "neg_cf": r.neg_price_cashflow_eur})
    if use_cache:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(rows))
    return days


# ---- orchestration ----------------------------------------------------------

def run_backtest(
    years=(2023, 2024, 2025),
    *,
    params: Params = Params(),
    grid_fee_charge: float = 0.0,
    degradation_discharge: float = 0.0,
    causal_params: dispatch.CausalParams = dispatch.CausalParams(),
    use_cache: bool = True,
    allow_fetch: bool = True,
    solver=None,
) -> BacktestResult:
    """Run both strategies over `years`. The causal walk is continuous across all
    requested years (sorted), so SoC carries between them."""
    battery = params.battery
    year_data = {y: load_year(y, allow_fetch=allow_fetch) for y in years}

    ceiling = {}
    for y in years:
        day_solves = _solve_ceiling_days(
            year_data[y], battery, cycle_cap=params.cycle_cap_per_day,
            grid_fee=grid_fee_charge, deg=degradation_discharge,
            tiebreak=dispatch.DEFAULT_TIEBREAK_EUR_MWH, use_cache=use_cache, solver=solver,
        )
        ceiling[y] = aggregate_ceiling(day_solves, battery, y, year_data[y].day_count)

    all_days = sorted(
        (d for yd in year_data.values() for d in yd.days), key=lambda x: x.day
    )
    causal_result = dispatch.run_causal_walkforward(
        all_days, battery, cycle_cap=params.cycle_cap_per_day, params=causal_params,
        grid_fee_charge=grid_fee_charge, degradation_discharge=degradation_discharge,
    )
    day_counts = {y: year_data[y].day_count for y in years}
    causal = aggregate_causal(causal_result, battery, day_counts)

    return BacktestResult(
        years=tuple(years),
        ceiling=ceiling,
        causal=causal,
        causal_terminal_value_eur=causal_result.terminal_value_eur,
        year_data=year_data,
        causal_result=causal_result,
    )
