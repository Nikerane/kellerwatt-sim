"""Single source of truth for the KellerWatt wire format — IDs, fee bases, the
status vocabulary, and the locked validated ceilings.

Imported by the engine, the export producer, the schema test, and the
React-consumer parse test, so the contract is defined in exactly one place
(Codex 5/6/7). The JSON Schema in ``engine/schema/sim_results.schema.json``
mirrors these enums; ``test_contracts.py`` asserts they never drift apart.
"""
from __future__ import annotations

SCHEMA_VERSION = "1.1.0"

# --- Strategy IDs (A0 / Codex 1,3) -------------------------------------------
# lp_ceiling          : perfect-foresight LP upper bound — the ONLY validated figure.
# causal_walkforward  : 28-day trailing-threshold causal benchmark — an *estimate*
#                       (null until the walk-forward is implemented & backtested).
STRATEGY_LP_CEILING = "lp_ceiling"
STRATEGY_CAUSAL_WALKFORWARD = "causal_walkforward"
STRATEGY_IDS = (STRATEGY_LP_CEILING, STRATEGY_CAUSAL_WALKFORWARD)

# --- Scenario (grid-fee) IDs (A0 / Codex 9) ----------------------------------
# Binary §118(6) EnWG cases, NOT a slider:
#   retained : grid energy fee on charge = 0
#   lost     : an energy fee (€/MWh) applies to charged energy
# Ancillary (FCR/aFRR) defaults to 0 in BOTH.
SCENARIO_EXEMPTION_RETAINED = "causal_exemption_retained"
SCENARIO_EXEMPTION_LOST = "causal_exemption_lost"
SCENARIO_IDS = (SCENARIO_EXEMPTION_RETAINED, SCENARIO_EXEMPTION_LOST)

# --- Metric status vocabulary (A0) -------------------------------------------
STATUS_VALIDATED = "validated"      # backtested on real prices, locked fixture
STATUS_ESTIMATE = "estimate"        # computed but not yet validated as firm
STATUS_PROVISIONAL = "provisional"  # blocked on external diligence (#8 fee, #9 legal)
STATUSES = (STATUS_VALIDATED, STATUS_ESTIMATE, STATUS_PROVISIONAL)

# --- BKV fee bases (A0 / Codex 4,14) -----------------------------------------
# All three are implemented & tested; the actual basis comes from the aggregator
# term sheet (#8). Where marginal, the fee sits INSIDE the dispatch objective.
FEE_BASIS_GROSS_TURNOVER = "gross_turnover"  # |buy| + |sell| AC turnover
FEE_BASIS_SALE_TURNOVER = "sale_turnover"    # discharge (sale) turnover only
FEE_BASIS_NET_MARGIN = "net_margin"          # gross arbitrage margin only
FEE_BASES = (FEE_BASIS_GROSS_TURNOVER, FEE_BASIS_SALE_TURNOVER, FEE_BASIS_NET_MARGIN)

# --- Locked, validated per-year ceilings (€/MWh, capped @1.5 cyc/day) ---------
# The ONLY validated figures (non-negotiable guardrail). The engine must COMPUTE
# these independently from real prices; it must never import these literals to
# produce output — only the integration test compares against them.
YEARS = (2023, 2024, 2025)
VALIDATED_CEILING_EUR_MWH = {2023: 61.1, 2024: 68.3, 2025: 77.3}
CEILING_TOLERANCE_EUR_MWH = 0.2  # tight tolerance for the A8 fixture assertions


def metric(value, unit, methodology_label, status):
    """Build a metric envelope. Every reported metric carries its provenance:
    what it means (``methodology_label``) and how firm it is (``status``)."""
    if status not in STATUSES:
        raise ValueError(f"unknown status {status!r}; expected one of {STATUSES}")
    return {
        "value": value,
        "unit": unit,
        "methodology_label": methodology_label,
        "status": status,
    }


def minimal_example():
    """A minimal document that validates against the schema — used by the schema
    tests and as living documentation of the shape. Not real data."""
    return {
        "schema_version": SCHEMA_VERSION,
        "provenance": {
            "price_zone": "DE-LU",
            "data_source": "Energy-Charts",
            "source_url": "https://api.energy-charts.info/price",
            "years": list(YEARS),
            "generated_utc": "2026-06-04T00:00:00Z",
            "git_commit": None,
            "note": "minimal schema example",
        },
        "solver": {
            "name": "HiGHS",
            "version": "1.14.0",
            "status": "Optimal",
            "mip_gap_tolerance": 0.0,
        },
        "assumptions": {
            "battery": {
                "capacity_kwh": 200.0,
                "power_kw": 50.0,
                "soc_min_frac": 0.10,
                "soc_max_frac": 1.00,
                "usable_kwh": 180.0,
                "rte": 0.90,
                "eta_one_way": 0.9486832980505138,
            },
            "business_plan": {
                "assumed_spread_eur_mwh": 80.0,
                "assumed_cycles_per_day": 1.5,
                "assumed_gross_eur": 9947.0,
            },
            "cycle_cap_per_day": 1.5,
            "operating_days": 365,
            "ancillary_eur": 0.0,
            "fees": {
                "bkv_fee_basis": FEE_BASIS_NET_MARGIN,
                "bkv_fee_rate": 0.0,
                "grid_energy_fee_eur_mwh_charge": 0.0,
            },
        },
        "strategies": [
            {
                "id": STRATEGY_LP_CEILING,
                "methodology_label": "perfect-foresight day-ahead upper bound",
                "status": STATUS_VALIDATED,
                "years": [
                    {
                        "year": 2024,
                        "ceiling_eur_mwh": 68.3,
                        "causal_eur_mwh": None,
                        "cycles_ac": 1.37,
                        "cycles_cell": 1.30,
                        "gross_eur": 6148.0,
                        "mwh_discharged": 90.0,
                        "day_count": 366,
                        "simul_max": 0.0,
                        "neg_price_cashflow_eur": 120.0,
                    }
                ],
            }
        ],
        "market": [
            {
                "year": 2024,
                "negative_intervals": 457,
                "price_min": -135.4,
                "price_max": 936.3,
                "day_count": 366,
            }
        ],
        "scenarios": [
            {
                "id": SCENARIO_EXEMPTION_RETAINED,
                "label": "§118(6) exemption retained (grid fee on charge = 0)",
                "grid_energy_fee_eur_mwh_charge": 0.0,
                "net_annual_eur": 6148.0,
                "implied_spread": metric(
                    68.3, "eur_mwh", "gross / MWh discharged", STATUS_VALIDATED
                ),
                "irr": metric(
                    None, "ratio", "constant-EBITDA project IRR", STATUS_PROVISIONAL
                ),
                "payback_years": metric(
                    None, "years", "constant-EBITDA payback", STATUS_PROVISIONAL
                ),
            }
        ],
    }
