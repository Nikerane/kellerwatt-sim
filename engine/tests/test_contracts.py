"""A0 — contracts. The wire format (JSON Schema) and the canonical IDs/fee bases
are defined in exactly one place and must agree. These tests fail loudly if the
schema is malformed, if an ID drifts from the schema enum, or if the schema stops
rejecting a malformed document (a schema that accepts everything is no contract).
"""
import json
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from engine import contracts

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schema" / "sim_results.schema.json"


@pytest.fixture(scope="module")
def schema():
    return json.loads(SCHEMA_PATH.read_text())


def test_schema_file_exists():
    assert SCHEMA_PATH.is_file(), f"missing schema at {SCHEMA_PATH}"


def test_schema_is_a_valid_draft_2020_12_schema(schema):
    # Raises SchemaError if the schema itself is malformed.
    Draft202012Validator.check_schema(schema)


def test_schema_pins_a_version(schema):
    assert schema.get("$schema", "").endswith("2020-12/schema")


def test_strategy_ids_match_schema_enum(schema):
    enum = schema["$defs"]["strategy"]["properties"]["id"]["enum"]
    assert set(enum) == set(contracts.STRATEGY_IDS)


def test_scenario_ids_match_schema_enum(schema):
    enum = schema["$defs"]["scenario"]["properties"]["id"]["enum"]
    assert set(enum) == set(contracts.SCENARIO_IDS)


def test_status_vocabulary_matches_schema_enum(schema):
    enum = schema["$defs"]["status"]["enum"]
    assert set(enum) == set(contracts.STATUSES)


def test_fee_bases_match_schema_enum(schema):
    enum = schema["$defs"]["fee_basis"]["enum"]
    assert set(enum) == set(contracts.FEE_BASES)


def test_locked_ceilings_cover_every_year():
    assert set(contracts.VALIDATED_CEILING_EUR_MWH) == set(contracts.YEARS)
    # The validated guardrail values, never to drift silently.
    assert contracts.VALIDATED_CEILING_EUR_MWH == {2023: 61.1, 2024: 68.3, 2025: 77.3}


def test_minimal_valid_document_passes(schema):
    Draft202012Validator(schema).validate(contracts.minimal_example())


def test_schema_rejects_unknown_strategy_id(schema):
    doc = deepcopy(contracts.minimal_example())
    doc["strategies"][0]["id"] = "not_a_real_strategy"
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(doc)


def test_schema_rejects_missing_required_top_level_field(schema):
    doc = deepcopy(contracts.minimal_example())
    del doc["solver"]
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(doc)


def test_schema_rejects_bad_metric_status(schema):
    doc = deepcopy(contracts.minimal_example())
    doc["scenarios"][0]["irr"]["status"] = "totally_firm"
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(doc)
