from pathlib import Path

import pytest

from backend.app.agents.analysis import execute_step
from backend.app.contracts.models import DatasetReference, PlanStep
from backend.app.tools.analysis.correlation import run
from backend.app.tools.analysis.descriptive import default_registry

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _ref(name: str, schema: dict[str, dict[str, str]]) -> DatasetReference:
    return DatasetReference(
        dataset_id="fixture",
        version="v1",
        storage_ref=str(FIXTURES / name),
        schema=schema,
    )


def test_correlation_analysis_reports_strong_pair():
    payload = run(
        _ref(
            "clean.csv",
            {"age": {"datatype": "integer"}, "score": {"datatype": "float"}},
        ),
        columns=["age", "score"],
        threshold=0.9,
    )

    assert payload["method"] == "pearson"
    assert payload["sample_size"] == 3
    assert payload["pairs"] == [
        {
            "column_x": "age",
            "column_y": "score",
            "coefficient": pytest.approx(1.0),
            "sample_size": 3,
        }
    ]
    assert payload["strong_pairs"] == payload["pairs"]


def test_correlation_analysis_rejects_non_numeric_column():
    dataset = _ref(
        "mixed.csv",
        {"age": {"datatype": "integer"}, "city": {"datatype": "string"}},
    )
    result = execute_step(
        PlanStep(
            step_id="correlate",
            tool_name="correlation_analysis",
            arguments={"columns": ["age", "city"]},
        ),
        dataset,
        default_registry(),
    )

    assert result.values["status"] == "failed"
    assert result.values["code"] == "INVALID_DATA"
    assert "city has dtype string" in result.values["error"]


def test_correlation_analysis_marks_pair_with_too_few_values_undefined():
    payload = run(
        _ref(
            "missing.csv",
            {"age": {"datatype": "integer"}, "score": {"datatype": "float"}},
        ),
        columns=["age", "score"],
    )

    assert payload["pairs"][0]["coefficient"] is None
    assert payload["pairs"][0]["sample_size"] == 1
    assert payload["strong_pairs"] == []
    assert "INSUFFICIENT_DATA" in {warning.code for warning in payload["warnings"]}
