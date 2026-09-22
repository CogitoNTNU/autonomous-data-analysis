from pathlib import Path

from backend.app.agents.analysis import execute_step
from backend.app.contracts.models import DatasetReference, PlanStep
from backend.app.tools.analysis.descriptive import default_registry, run

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _ref(name: str, schema: dict) -> DatasetReference:
    return DatasetReference(
        dataset_id="fixture",
        version="v1",
        storage_ref=str(FIXTURES / name),
        schema=schema,
    )


def test_descriptive_statistics_on_clean_numeric_columns():
    payload = run(
        _ref(
            "clean.csv",
            {"age": {"datatype": "integer"}, "score": {"datatype": "float"}},
        ),
        columns=["age", "score"],
    )
    age, score = payload["columns"]["age"], payload["columns"]["score"]
    assert (
        age["n"],
        age["mean"],
        age["median"],
        age["std"],
        age["min"],
        age["max"],
    ) == (3, 20.0, 20.0, 10.0, 10.0, 30.0)
    assert (score["n"], score["mean"], score["min"], score["max"]) == (3, 2.5, 1.5, 3.5)
    assert any(warning.code == "LOW_SAMPLE_SIZE" for warning in payload["warnings"])


def test_descriptive_statistics_handles_missing_values():
    payload = run(
        _ref(
            "missing.csv",
            {"age": {"datatype": "integer"}, "score": {"datatype": "float"}},
        ),
        columns=["age", "score"],
    )
    assert payload["columns"]["age"]["n"] == 2
    assert payload["columns"]["age"]["mean"] == 20.0
    assert payload["columns"]["score"]["mean"] == 2.0
    assert {"HIGH_MISSING_RATE", "LOW_SAMPLE_SIZE"} <= {
        warning.code for warning in payload["warnings"]
    }


def test_descriptive_statistics_flags_constant_column():
    payload = run(
        _ref("constant.csv", {"age": {"datatype": "integer"}}), columns=["age"]
    )
    assert payload["columns"]["age"]["std"] == 0.0
    assert any(warning.code == "CONSTANT_COLUMN" for warning in payload["warnings"])


def test_mixed_types_numeric_column_runs_and_string_column_is_rejected():
    dataset = _ref(
        "mixed.csv", {"age": {"datatype": "integer"}, "city": {"datatype": "string"}}
    )
    registry = default_registry()
    ok = execute_step(
        PlanStep(
            step_id="num",
            tool_name="descriptive_statistics",
            arguments={"columns": ["age"]},
        ),
        dataset,
        registry,
    )
    assert ok.values["columns"]["age"]["mean"] == 15.0
    failed = execute_step(
        PlanStep(
            step_id="str",
            tool_name="descriptive_statistics",
            arguments={"columns": ["city"]},
        ),
        dataset,
        registry,
    )
    assert failed.values["code"] == "INVALID_DATA"
