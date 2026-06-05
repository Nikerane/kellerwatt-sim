"""A7 — export. Assemble a schema-validated results document and emit two separate
artifacts: dist/real/sim_results.json (never committed/public) and
dist/sanitized/sim_results.json (public). Sanitization never publishes a real
IRR/payback value. `python -m engine.export` runs the real backtest and writes both.

Resolution of the B3-vs-B6 tension (flagged for confirmation): the sanitized bundle
KEEPS the public-market-derived ceilings + causal estimate (the honest finding the
page shows); the leak scan targets genuinely-confidential business inputs.
"""
from __future__ import annotations

import json
import subprocess
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator

from engine import contracts, dispatch, economics, metrics, solver
from engine.params import Params

UTC = timezone.utc
SCHEMA_PATH = Path(__file__).resolve().parent / "schema" / "sim_results.schema.json"
DIST_DIR = Path(__file__).resolve().parents[1] / "dist"
PROJECT_HORIZON_YEARS = 10
# Confidential markers that must never appear in the public bundle (B6 leak scan).
DEFAULT_FORBIDDEN = ("capex_eur", "real_fee_rate", "term_sheet")

_CEILING_LABEL = "perfect-foresight day-ahead upper bound (cyclic, capped)"
_CAUSAL_LABEL = "causal walk-forward (28-day trailing thresholds, continuous SoC)"


def _round(v, n):
    return None if v is None else round(v, n)


def _year_result(sy, *, is_ceiling):
    spread = _round(sy.implied_spread, 1)
    return {
        "year": sy.year,
        "ceiling_eur_mwh": spread if is_ceiling else None,
        "causal_eur_mwh": None if is_ceiling else spread,
        "cycles_ac": _round(sy.cycles_ac, 3),
        "cycles_cell": _round(sy.cycles_cell, 3),
        "gross_eur": _round(sy.gross_eur, 0),
        "mwh_discharged": _round(sy.mwh_discharged, 2),
        "day_count": sy.day_count,
        "simul_max": _round(sy.simul_max, 9),
    }


def _scenario(scn, all_days, params, *, representative_year, capex_eur):
    cz = dispatch.run_causal_walkforward(
        all_days, params.battery, cycle_cap=params.cycle_cap_per_day,
        grid_fee_charge=scn.grid_energy_fee_eur_mwh_charge,
    )
    py = cz.per_year().get(representative_year)
    if py and py["dis"]:
        net = py["net"]
        net_spread = net / py["dis"]
    else:
        net = net_spread = None
    irr = metrics.project_irr(capex_eur, net, PROJECT_HORIZON_YEARS)
    payback = metrics.simple_payback(capex_eur, net)
    return {
        "id": scn.id,
        "label": scn.label,
        "grid_energy_fee_eur_mwh_charge": scn.grid_energy_fee_eur_mwh_charge,
        "net_annual_eur": _round(net, 0),
        "implied_spread": contracts.metric(
            _round(net_spread, 1), "eur_mwh",
            f"{_CAUSAL_LABEL}, net of grid fee ({representative_year})",
            contracts.STATUS_ESTIMATE,
        ),
        "irr": irr,
        "payback_years": payback,
    }


def build_results(bt_result, params: Params, *, generated_utc: str,
                  git_commit: str | None = None, capex_eur=None) -> dict:
    b = params.battery
    bp = params.business_plan
    years = list(bt_result.years)
    representative_year = max(years)
    all_days = sorted(
        (d for yd in bt_result.year_data.values() for d in yd.days),
        key=lambda x: x.day,
    )

    assumed_identity = metrics.assumed_case_gross(
        bp.assumed_spread_eur_mwh, b.usable_mwh, bp.assumed_cycles_per_day, bp.operating_days
    )

    solver_meta = solver.solver_metadata()
    solver_meta["status"] = "Optimal"  # backtest raises on any non-optimal solve

    doc = {
        "schema_version": contracts.SCHEMA_VERSION,
        "provenance": {
            "price_zone": "DE-LU",
            "data_source": "Energy-Charts",
            "source_url": "https://api.energy-charts.info/price",
            "years": years,
            "generated_utc": generated_utc,
            "git_commit": git_commit,
            "note": (
                "Ceilings are perfect-foresight upper bounds on real DE-LU prices. "
                "Causal is a backtested estimate, not a floor. Deck claimed "
                f"EUR 9,947 gross; reconciled identity at EUR 80/MWh, 1.5 cyc = "
                f"EUR {assumed_identity:,.0f} (Codex 7)."
            ),
        },
        "solver": solver_meta,
        "assumptions": {
            "battery": {
                "capacity_kwh": b.capacity_kwh, "power_kw": b.power_kw,
                "soc_min_frac": b.soc_min_frac, "soc_max_frac": b.soc_max_frac,
                "usable_kwh": b.usable_kwh, "rte": b.rte, "eta_one_way": b.eta_one_way,
            },
            "business_plan": {
                "assumed_spread_eur_mwh": bp.assumed_spread_eur_mwh,
                "assumed_cycles_per_day": bp.assumed_cycles_per_day,
                "assumed_gross_eur": round(assumed_identity, 0),
            },
            "cycle_cap_per_day": params.cycle_cap_per_day,
            "operating_days": bp.operating_days,
            "ancillary_eur": params.ancillary_eur,
            "fees": {
                "bkv_fee_basis": params.fees.bkv_fee_basis,
                "bkv_fee_rate": params.fees.bkv_fee_rate,
                "grid_energy_fee_eur_mwh_charge": params.fees.grid_energy_fee_eur_mwh_charge,
            },
        },
        "strategies": [
            {
                "id": contracts.STRATEGY_LP_CEILING,
                "methodology_label": _CEILING_LABEL,
                "status": contracts.STATUS_VALIDATED,
                "years": [_year_result(bt_result.ceiling[y], is_ceiling=True) for y in years],
            },
            {
                "id": contracts.STRATEGY_CAUSAL_WALKFORWARD,
                "methodology_label": _CAUSAL_LABEL,
                "status": contracts.STATUS_ESTIMATE,
                "years": [_year_result(bt_result.causal[y], is_ceiling=False) for y in years],
            },
        ],
        "scenarios": [
            _scenario(scn, all_days, params, representative_year=representative_year,
                      capex_eur=capex_eur)
            for scn in economics.SCENARIOS
        ],
    }
    Draft202012Validator(json.loads(SCHEMA_PATH.read_text())).validate(doc)
    return doc


def sanitize(results: dict) -> dict:
    """Public-safe copy: never publish a real IRR/payback value, and drop any
    confidential business inputs. Keeps the public ceilings + causal estimate."""
    san = deepcopy(results)
    for sc in san["scenarios"]:
        sc["irr"]["value"] = None
        sc["payback_years"]["value"] = None
    return san


def scan_for_leaks(text: str, forbidden=DEFAULT_FORBIDDEN) -> list:
    return [tok for tok in forbidden if tok in text]


def write_artifacts(results: dict, out_dir: Path = DIST_DIR) -> dict:
    out_dir = Path(out_dir)
    real_path = out_dir / "real" / "sim_results.json"
    san_path = out_dir / "sanitized" / "sim_results.json"
    real_path.parent.mkdir(parents=True, exist_ok=True)
    san_path.parent.mkdir(parents=True, exist_ok=True)
    real_path.write_text(json.dumps(results, indent=2))
    sanitized = sanitize(results)
    san_path.write_text(json.dumps(sanitized, indent=2))
    leaks = scan_for_leaks(san_path.read_text())
    if leaks:
        raise RuntimeError(f"sanitized bundle leaked confidential markers: {leaks}")
    return {"real": real_path, "sanitized": san_path}


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=Path(__file__).resolve().parents[1]
        ).decode().strip()
    except Exception:
        return None


def main():
    from engine.backtest import run_backtest
    bt_result = run_backtest()
    ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    results = build_results(bt_result, Params(), generated_utc=ts, git_commit=_git_commit())
    paths = write_artifacts(results)
    print(f"wrote {paths['real']}\nwrote {paths['sanitized']}")
    for s in results["strategies"]:
        print(f"  {s['id']:<20} [{s['status']}] "
              + " ".join(f"{yr['year']}:"
                         f"{yr['ceiling_eur_mwh'] or yr['causal_eur_mwh']}" for yr in s["years"]))


if __name__ == "__main__":
    main()
