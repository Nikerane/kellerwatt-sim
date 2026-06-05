"""A8 — integration (Codex 8). Lock the VALIDATED per-year ceilings to tight
fixtures on real data: 61.1 / 68.3 / 77.3 EUR/MWh, plus gross, day-count, and
simul == 0. Causal fixtures are deliberately loose (it is an ESTIMATE, not locked).
Marked @network: needs cached or fetched DE-LU prices.
"""
import json

import pytest
from jsonschema import Draft202012Validator

from engine import contracts, export
from engine.backtest import run_backtest
from engine.params import Params

EXPECTED_GROSS = {2023: 5403, 2024: 6148, 2025: 7030}
EXPECTED_DAYS = {2023: 365, 2024: 366, 2025: 365}


@pytest.fixture(scope="module")
def bt():
    return run_backtest(years=(2023, 2024, 2025), params=Params())


@pytest.mark.network
@pytest.mark.parametrize("year", [2023, 2024, 2025])
def test_validated_ceiling_locked(bt, year):
    sy = bt.ceiling[year]
    assert sy.implied_spread == pytest.approx(
        contracts.VALIDATED_CEILING_EUR_MWH[year], abs=contracts.CEILING_TOLERANCE_EUR_MWH
    )
    assert sy.gross_eur == pytest.approx(EXPECTED_GROSS[year], abs=5)
    assert sy.day_count == EXPECTED_DAYS[year]
    assert sy.simul_max < 1e-6


@pytest.mark.network
def test_causal_is_below_ceiling_and_positive(bt):
    for year in (2023, 2024, 2025):
        assert 0 < bt.causal[year].gross_eur < bt.ceiling[year].gross_eur


@pytest.mark.network
def test_real_export_validates_and_holds_ceilings(bt):
    doc = export.build_results(bt, Params(), generated_utc="2026-06-04T00:00:00Z")
    Draft202012Validator(json.loads(export.SCHEMA_PATH.read_text())).validate(doc)
    ceil = {yr["year"]: yr["ceiling_eur_mwh"]
            for s in doc["strategies"] if s["id"] == contracts.STRATEGY_LP_CEILING
            for yr in s["years"]}
    assert ceil == {2023: 61.1, 2024: 68.3, 2025: 77.3}
