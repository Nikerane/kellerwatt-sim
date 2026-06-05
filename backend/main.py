"""KellerWatt engine API — FastAPI server for the interactive playground.

Deployed to Hugging Face Spaces (free Docker tier). The engine and cached
price data are bundled in the Docker image so no live API calls are needed.
"""
from __future__ import annotations

from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from engine.backtest import run_backtest
from engine.contracts import SCHEMA_VERSION
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
