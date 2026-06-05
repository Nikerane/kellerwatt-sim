#!/usr/bin/env python3
"""Precompute daily dispatch arrays for the offline lookup table.

Iterates a grid of (capacity_kwh, power_kw, rte, grid_fee) combos, runs
ceiling LP + causal walk-forward for each, and writes one JSON file per
capacity value to web/public/data/dispatch/.

Usage:
    python scripts/precompute_dispatch.py

The ceiling day-solves are cached to disk (engine/data/cache/), so re-runs
are fast after the cache is warm.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import date

# Ensure the repo root is on sys.path so engine/ imports work.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from engine.backtest import _solve_ceiling_days, run_backtest
from engine.data_load import load_year
from engine.dispatch import solve_day_ceiling
from engine.params import Battery, Params

# ---- grid definition ----
CAPACITIES = [50, 100, 175, 250, 350, 450, 500]
POWERS = [25, 50, 100, 150, 200, 250]
RTES = [0.75, 0.80, 0.85, 0.90, 0.95]
GRID_FEES = [0, 10, 20, 30, 50]

# Fixed seasonal dates (always 2025, the most recent full year).
SPRING = date(2025, 3, 21)
SUMMER = date(2025, 6, 21)
WINTER = date(2025, 1, 15)

OUT_DIR = os.path.join(REPO_ROOT, "web", "public", "data", "dispatch")


def combo_key(power_kw: int, rte: float, grid_fee: int) -> str:
    return f"{power_kw}_{rte}_{grid_fee}"


def avg_price(mwh: float, turnover: float) -> float | None:
    if mwh > 0 and turnover > 0:
        return round(turnover / mwh, 1)
    return None


def strategy_detail(day_dispatch) -> dict:
    """Convert a ceiling or causal day result to the JSON-serialisable format."""
    return {
        "gross_eur": round(day_dispatch.gross_eur, 2),
        "mwh_discharged": round(day_dispatch.mwh_discharged, 3),
        "mwh_charged": round(day_dispatch.mwh_charged, 3),
        "avg_buy_price": avg_price(
            day_dispatch.mwh_charged, day_dispatch.purchase_turnover_eur
        ),
        "avg_sell_price": avg_price(
            day_dispatch.mwh_discharged, day_dispatch.sale_turnover_eur
        ),
        "charge_kw": [round(v, 2) for v in day_dispatch.charge_kw]
        if day_dispatch.charge_kw
        else [],
        "discharge_kw": [round(v, 2) for v in day_dispatch.discharge_kw]
        if day_dispatch.discharge_kw
        else [],
        "soc_kwh": [round(v, 2) for v in day_dispatch.soc_kwh]
        if day_dispatch.soc_kwh
        else [],
    }


def empty_detail() -> dict:
    return {
        "gross_eur": 0.0,
        "mwh_discharged": 0.0,
        "mwh_charged": 0.0,
        "avg_buy_price": None,
        "avg_sell_price": None,
        "charge_kw": [],
        "discharge_kw": [],
        "soc_kwh": [],
    }


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    year_data = load_year(2025, allow_fetch=False)
    days_list = list(year_data.days)
    day_map = {d.day: d for d in days_list}

    total_combos = len(CAPACITIES) * len(POWERS) * len(RTES) * len(GRID_FEES)
    done = 0
    t0 = time.monotonic()

    for cap in CAPACITIES:
        file_data: dict = {
            "capacity_kwh": cap,
            "days": {},
            "combos": {},
        }

        for power in POWERS:
            for rte in RTES:
                for grid_fee in GRID_FEES:
                    battery = Battery(capacity_kwh=cap, power_kw=power, rte=rte)
                    ck = combo_key(power, rte, grid_fee)

                    # ---- find best/worst from cached ceiling aggregates ----
                    ceil_aggs = _solve_ceiling_days(
                        year_data, battery,
                        cycle_cap=None, grid_fee=grid_fee,
                        deg=0.0, tiebreak=0.01,
                        use_cache=True, solver=None,
                    )
                    best_date = None
                    worst_date = None
                    best_gross = -float("inf")
                    worst_gross = float("inf")
                    for i, d in enumerate(days_list):
                        gross = ceil_aggs[i].gross_eur
                        if gross > best_gross:
                            best_gross = gross
                            best_date = d.day
                        if gross < worst_gross:
                            worst_gross = gross
                            worst_date = d.day

                    # ---- 5 target dates ----
                    target_dates: list[date] = [
                        best_date, worst_date, SPRING, SUMMER, WINTER
                    ]
                    seen = set()
                    unique_dates = []
                    for d in target_dates:
                        if d not in seen:
                            seen.add(d)
                            unique_dates.append(d)

                    # ---- run causal walk-forward for this combo ----
                    bt = run_backtest(
                        years=(2025,),
                        params=Params(battery=battery),
                        grid_fee_charge=grid_fee,
                        use_cache=True, allow_fetch=False,
                    )
                    causal_by_date = {}
                    if bt.causal_result:
                        for cd in bt.causal_result.days:
                            causal_by_date[cd.day] = cd

                    # ---- solve each target date ----
                    combo_ceiling: dict[str, dict] = {}
                    combo_causal: dict[str, dict] = {}

                    for d in unique_dates:
                        ds = d.isoformat()
                        td = day_map[d]

                        # Prices — store once per date at file level.
                        if ds not in file_data["days"]:
                            file_data["days"][ds] = {
                                "prices": [round(p, 1) for p in td.prices],
                                "dt_h": td.dt_h,
                            }

                        # Ceiling — full solve for per-interval arrays.
                        ceil = solve_day_ceiling(
                            list(td.prices), td.dt_h, battery,
                            cycle_cap=None, grid_fee_charge=grid_fee,
                        )
                        combo_ceiling[ds] = strategy_detail(ceil)

                        # Causal — from walk-forward result.
                        cday = causal_by_date.get(d)
                        combo_causal[ds] = strategy_detail(cday) if cday else empty_detail()

                    file_data["combos"][ck] = {
                        "best_date": best_date.isoformat(),
                        "worst_date": worst_date.isoformat(),
                        "ceiling": combo_ceiling,
                        "causal": combo_causal,
                    }

                    done += 1
                    elapsed = time.monotonic() - t0
                    if done % 20 == 0:
                        rate = done / elapsed if elapsed > 0 else 0
                        eta = (total_combos - done) / rate if rate > 0 else 0
                        print(f"  {done}/{total_combos} combos | {rate:.1f}/s | "
                              f"ETA {eta/60:.0f}m | cap={cap}kW power={power}kW "
                              f"rte={rte} fee={grid_fee}")

        # Write per-capacity file.
        out_path = os.path.join(OUT_DIR, f"cap_{cap:03d}.json")
        with open(out_path, "w") as f:
            json.dump(file_data, f)
        fsize = os.path.getsize(out_path) / (1024 * 1024)
        print(f"  Wrote cap_{cap:03d}.json — {len(file_data['combos'])} combos, "
              f"{len(file_data['days'])} days, {fsize:.1f} MB")

    elapsed = time.monotonic() - t0
    print(f"\nDone — {total_combos} combos in {elapsed/60:.0f}m "
          f"({total_combos/elapsed:.1f} combos/s)")


if __name__ == "__main__":
    main()
