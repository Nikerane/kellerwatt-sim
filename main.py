"""KellerWatt engine API — FastAPI server for the interactive playground.

Deployed to Hugging Face Spaces (free Docker tier). The engine and cached
price data are bundled in the Docker image so no live API calls are needed.
"""
from __future__ import annotations

from datetime import date as DateType
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from engine.backtest import run_backtest
from engine.contracts import SCHEMA_VERSION
from engine.data_load import load_year
from engine.dispatch import solve_day_ceiling
from engine.metrics import assumed_case_gross
from engine.params import Battery, Params

app = FastAPI(title="KellerWatt Engine", version=SCHEMA_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


class BatteryRequest(BaseModel):
    capacity_kwh: float
    power_kw: float
    rte: float


class SolveRequest(BaseModel):
    battery: BatteryRequest
    assumed_spread_eur_mwh: float
    cycles_per_day: float
    grid_fee_eur_mwh: float
    exemption: Literal["retained", "lost"]


@app.post("/solve")
async def solve(req: SolveRequest):
    b = req.battery
    battery = Battery(
        capacity_kwh=b.capacity_kwh,
        power_kw=b.power_kw,
        rte=b.rte,
    )
    usable_mwh = battery.usable_mwh

    grid_fee = req.grid_fee_eur_mwh

    # Ceiling: always solved with grid_fee=0 (retained). The ceiling is the
    # perfect-foresight upper bound; grid fees only apply in the causal walk-forward.
    params_ret = Params(battery=battery, cycle_cap_per_day=req.cycles_per_day)
    bt_ret = run_backtest(
        params=params_ret, grid_fee_charge=0,
        use_cache=True, allow_fetch=False,
    )

    # Causal for the "lost" scenario: solve with the grid fee on charge
    if req.exemption == "lost" and grid_fee > 0:
        bt_lost = run_backtest(
            params=Params(battery=battery, cycle_cap_per_day=req.cycles_per_day),
            grid_fee_charge=grid_fee, use_cache=True, allow_fetch=False,
        )
    else:
        bt_lost = bt_ret

    years = list(bt_ret.years)

    def _ceiling_dict(bt):
        return {
            str(y): {
                "spread_eur_mwh": round(bt.ceiling[y].implied_spread, 1),
                "gross_eur": round(bt.ceiling[y].gross_eur, 0),
                "cycles_ac": round(bt.ceiling[y].cycles_ac, 3),
            }
            for y in years
        }

    def _causal_dict(bt):
        return {
            str(y): {
                "spread_eur_mwh": (
                    round(bt.causal[y].implied_spread, 1) if y in bt.causal else None
                ),
                "gross_eur": (
                    round(bt.causal[y].gross_eur, 0) if y in bt.causal else None
                ),
                "cycles_ac": (
                    round(bt.causal[y].cycles_ac, 3) if y in bt.causal else None
                ),
            }
            for y in years
        }

    assumed_gross = round(
        assumed_case_gross(
            req.assumed_spread_eur_mwh, usable_mwh, req.cycles_per_day, 365,
        ),
        0,
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "years": years,
        "assumed": {
            "spread_eur_mwh": req.assumed_spread_eur_mwh,
            "gross_eur": assumed_gross,
            "cycles_per_day": req.cycles_per_day,
        },
        "ceiling": _ceiling_dict(bt_ret),
        "causal_retained": _causal_dict(bt_ret),
        "causal_lost": _causal_dict(bt_lost),
    }


class DayDetailRequest(BaseModel):
    date: str  # "2025-03-14"
    battery: BatteryRequest
    grid_fee_eur_mwh: float


@app.post("/day-detail")
async def day_detail(req: DayDetailRequest):
    target_date = DateType.fromisoformat(req.date)
    year = target_date.year
    b = req.battery
    battery = Battery(
        capacity_kwh=b.capacity_kwh,
        power_kw=b.power_kw,
        rte=b.rte,
    )
    grid_fee = req.grid_fee_eur_mwh

    # Load year's price data
    year_data = load_year(year, allow_fetch=False)
    target_day = None
    for day in year_data.days:
        if day.day == target_date:
            target_day = day
            break
    if target_day is None:
        raise HTTPException(status_code=404, detail=f"no price data for {req.date}")

    # Solve ceiling LP for that single day
    ceil = solve_day_ceiling(
        list(target_day.prices), target_day.dt_h, battery,
        cycle_cap=None, grid_fee_charge=grid_fee,
    )

    # Run full backtest to get causal day arrays (mostly cached)
    bt = run_backtest(
        years=(year,),
        params=Params(battery=battery),
        grid_fee_charge=grid_fee,
        use_cache=True, allow_fetch=False,
    )
    causal_days = bt.causal_result.days if bt.causal_result else ()
    causal_day = None
    for cd in causal_days:
        if cd.day == target_date:
            causal_day = cd
            break

    def _avg_price(mwh: float, turnover: float) -> Optional[float]:
        if mwh > 0 and turnover > 0:
            return round(turnover / mwh, 1)
        return None

    def _ceil_detail(day_dispatch):
        return {
            "gross_eur": round(day_dispatch.gross_eur, 2),
            "mwh_discharged": round(day_dispatch.mwh_discharged, 3),
            "mwh_charged": round(day_dispatch.mwh_charged, 3),
            "avg_buy_price": _avg_price(day_dispatch.mwh_charged, day_dispatch.purchase_turnover_eur),
            "avg_sell_price": _avg_price(day_dispatch.mwh_discharged, day_dispatch.sale_turnover_eur),
            "charge_kw": [round(v, 2) for v in day_dispatch.charge_kw] if day_dispatch.charge_kw else [],
            "discharge_kw": [round(v, 2) for v in day_dispatch.discharge_kw] if day_dispatch.discharge_kw else [],
            "soc_kwh": [round(v, 2) for v in day_dispatch.soc_kwh] if day_dispatch.soc_kwh else [],
        }

    def _causal_detail(cday):
        if cday is None:
            return {
                "gross_eur": 0.0, "mwh_discharged": 0.0, "mwh_charged": 0.0,
                "avg_buy_price": None, "avg_sell_price": None,
                "charge_kw": [], "discharge_kw": [], "soc_kwh": [],
            }
        return {
            "gross_eur": round(cday.gross_eur, 2),
            "mwh_discharged": round(cday.mwh_discharged, 3),
            "mwh_charged": round(cday.mwh_charged, 3),
            "avg_buy_price": _avg_price(cday.mwh_charged, cday.purchase_turnover_eur),
            "avg_sell_price": _avg_price(cday.mwh_discharged, cday.sale_turnover_eur),
            "charge_kw": [round(v, 2) for v in cday.charge_kw] if cday.charge_kw else [],
            "discharge_kw": [round(v, 2) for v in cday.discharge_kw] if cday.discharge_kw else [],
            "soc_kwh": [round(v, 2) for v in cday.soc_kwh] if cday.soc_kwh else [],
        }

    # Pre-compute best/worst ceiling days (by gross) across the year
    best_date = None
    worst_date = None
    best_gross = -float("inf")
    worst_gross = float("inf")
    for day in year_data.days:
        d = solve_day_ceiling(
            list(day.prices), day.dt_h, battery,
            cycle_cap=None, grid_fee_charge=grid_fee,
        )
        if d.gross_eur > best_gross:
            best_gross = d.gross_eur
            best_date = day.day.isoformat()
        if d.gross_eur < worst_gross:
            worst_gross = d.gross_eur
            worst_date = day.day.isoformat()

    available_dates = [d.day.isoformat() for d in year_data.days]

    return {
        "date": req.date,
        "num_intervals": len(target_day.prices),
        "dt_h": target_day.dt_h,
        "prices": [round(p, 1) for p in target_day.prices],
        "best_date": best_date or req.date,
        "worst_date": worst_date or req.date,
        "available_dates": available_dates,
        "ceiling": _ceil_detail(ceil),
        "causal": _causal_detail(causal_day),
    }
