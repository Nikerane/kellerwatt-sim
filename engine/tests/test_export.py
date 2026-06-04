"""A7 — export (Codex 2,6,13).

Producer builds a schema-validated results doc; two separate artifacts are emitted
(dist/real never committed, dist/sanitized public). The consumer-contract test
asserts the exact shape the React honesty page will read. Sanitization never
publishes a real IRR/payback value, and a leak scan guards the sanitized bundle.
"""
import json
from datetime import datetime, timezone

import pytest
from jsonschema import Draft202012Validator

from engine import export, contracts
from engine.backtest import BacktestResult, StrategyYear
from engine.data_load import YearData, DayPrices
from engine.params import Params

UTC = timezone.utc
FIXED_TS = "2026-06-04T12:00:00Z"


def _strategy_year(year, gross, dis, spread, day_count):
    return StrategyYear(
        year=year, day_count=day_count, gross_eur=gross, mwh_discharged=dis,
        mwh_charged=dis * 1.1, sale_turnover_eur=gross * 1.2,
        purchase_turnover_eur=gross * 0.2, cycles_ac=1.3, cycles_cell=1.4,
        simul_max=0.0, implied_spread=spread,
    )


def _fake_year_data(year, day_count):
    # A minimal YearData stub (only the fields the export reads).
    return YearData(
        year=year, days=(), nulls_dropped=0, points_per_day_histogram={24: day_count},
        price_min=-50.0, price_max=500.0, negative_intervals=300,
        resolution_transition=None,
    )


def _fake_backtest():
    years = (2023, 2024, 2025)
    ceiling = {
        2023: _strategy_year(2023, 5403.0, 88.0, 61.1, 365),
        2024: _strategy_year(2024, 6148.0, 90.0, 68.3, 366),
        2025: _strategy_year(2025, 7030.0, 91.0, 77.3, 365),
    }
    causal = {
        2023: _strategy_year(2023, 1719.0, 46.0, 37.7, 365),
        2024: _strategy_year(2024, 2355.0, 46.0, 51.3, 366),
        2025: _strategy_year(2025, 3276.0, 57.0, 57.1, 365),
    }
    yd = {y: _fake_year_data(y, dc) for y, dc in [(2023, 365), (2024, 366), (2025, 365)]}
    return BacktestResult(years=years, ceiling=ceiling, causal=causal,
                          causal_terminal_value_eur=11.2, year_data=yd)


@pytest.fixture(scope="module")
def schema():
    return json.loads((export.SCHEMA_PATH).read_text())


@pytest.fixture
def results():
    return export.build_results(_fake_backtest(), Params(), generated_utc=FIXED_TS,
                                git_commit="deadbeef")


def test_build_results_validates_against_schema(results, schema):
    Draft202012Validator(schema).validate(results)


def test_strategies_carry_status_and_locked_ceilings(results):
    by_id = {s["id"]: s for s in results["strategies"]}
    assert by_id["lp_ceiling"]["status"] == contracts.STATUS_VALIDATED
    assert by_id["causal_walkforward"]["status"] == contracts.STATUS_ESTIMATE
    ceil = {yr["year"]: yr["ceiling_eur_mwh"] for yr in by_id["lp_ceiling"]["years"]}
    assert ceil == {2023: 61.1, 2024: 68.3, 2025: 77.3}
    # causal strategy carries causal_eur_mwh, ceiling is null on that strategy.
    cz = {yr["year"]: yr["causal_eur_mwh"] for yr in by_id["causal_walkforward"]["years"]}
    assert cz[2024] == 51.3
    assert by_id["causal_walkforward"]["years"][0]["ceiling_eur_mwh"] is None


def test_scenarios_irr_payback_are_provisional(results):
    for sc in results["scenarios"]:
        assert sc["irr"]["status"] == contracts.STATUS_PROVISIONAL
        assert sc["payback_years"]["status"] == contracts.STATUS_PROVISIONAL
        assert "constant-EBITDA" in sc["irr"]["methodology_label"]
    ids = {sc["id"] for sc in results["scenarios"]}
    assert ids == set(contracts.SCENARIO_IDS)


def test_assumed_gross_is_reconciled_identity_not_deck_claim(results):
    # 80 * 0.180 * 1.5 * 365 = 7884, NOT the deck's 9947 (Codex 7).
    assert results["assumptions"]["business_plan"]["assumed_gross_eur"] == pytest.approx(7884.0)


def test_sanitize_never_publishes_real_irr(schema):
    real = export.build_results(_fake_backtest(), Params(), generated_utc=FIXED_TS,
                                capex_eur=100000.0)
    san = export.sanitize(real)
    Draft202012Validator(schema).validate(san)        # still valid
    for sc in san["scenarios"]:
        assert sc["irr"]["value"] is None             # nulled in public bundle
        assert sc["payback_years"]["value"] is None


def test_leak_scan_flags_confidential_markers():
    text = json.dumps({"capex_eur": 123456, "ok": 1})
    found = export.scan_for_leaks(text, forbidden=("capex_eur",))
    assert "capex_eur" in found
    clean = export.scan_for_leaks(json.dumps({"ok": 1}), forbidden=("capex_eur",))
    assert clean == []


def test_consumer_contract_fields(results):
    # Exactly what the React honesty page reads — guard the consumer side.
    assert results["schema_version"] == contracts.SCHEMA_VERSION
    assert results["provenance"]["price_zone"] == "DE-LU"
    assert results["solver"]["name"] == "HiGHS"
    for s in results["strategies"]:
        for yr in s["years"]:
            assert set(["year", "ceiling_eur_mwh", "causal_eur_mwh", "cycles_ac",
                        "cycles_cell", "gross_eur", "mwh_discharged", "day_count",
                        "simul_max"]).issubset(yr)


def test_write_artifacts_emits_both(tmp_path, results, schema):
    paths = export.write_artifacts(results, out_dir=tmp_path)
    real = json.loads((tmp_path / "real" / "sim_results.json").read_text())
    san = json.loads((tmp_path / "sanitized" / "sim_results.json").read_text())
    Draft202012Validator(schema).validate(real)
    Draft202012Validator(schema).validate(san)
    assert paths["real"].name == "sim_results.json"
