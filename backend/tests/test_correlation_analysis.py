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


@pytest.mark.parametrize("method", ["pearson", "spearman"])
def test_correlation_analysis_reports_strong_pair(method):
    payload = run(
        _ref(
            "clean.csv",
            {"age": {"datatype": "integer"}, "score": {"datatype": "float"}},
        ),
        columns=["age", "score"],
        method=method,
        threshold=0.9,
    )

    assert payload["method"] == method
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


@pytest.mark.parametrize("method", ["pearson", "spearman"])
def test_correlation_analysis_rejects_non_numeric_column(method):
    dataset = _ref(
        "mixed.csv",
        {"age": {"datatype": "integer"}, "city": {"datatype": "string"}},
    )
    result = execute_step(
        PlanStep(
            step_id="correlate",
            tool_name="correlation_analysis",
            arguments={"columns": ["age", "city"], "method": method},
        ),
        dataset,
        default_registry(),
    )

    assert result.values["status"] == "failed"
    assert result.values["code"] == "INVALID_DATA"
    assert "city has dtype string" in result.values["error"]


@pytest.mark.parametrize("method", ["pearson", "spearman"])
def test_correlation_analysis_marks_pair_with_too_few_values_undefined(method):
    payload = run(
        _ref(
            "missing.csv",
            {"age": {"datatype": "integer"}, "score": {"datatype": "float"}},
        ),
        columns=["age", "score"],
        method=method,
    )

    assert payload["pairs"][0]["coefficient"] is None
    assert payload["pairs"][0]["sample_size"] == 1
    assert payload["strong_pairs"] == []
    assert "INSUFFICIENT_DATA" in {warning.code for warning in payload["warnings"]}


def test_spearman_executes_through_registry_without_a_tool_failure():
    result = execute_step(
        PlanStep(
            step_id="correlate-sensors",
            tool_name="correlation_analysis",
            arguments={"columns": ["age", "score"], "method": "spearman"},
        ),
        _ref(
            "clean.csv",
            {"age": {"datatype": "integer"}, "score": {"datatype": "float"}},
        ),
        default_registry(),
    )

    assert (
        result.values["status"] == "partial"
    )  # Three rows retain the sample-size warning.
    assert "error" not in result.values
    assert result.values["method"] == "spearman"
    assert result.values["pairs"][0]["coefficient"] == pytest.approx(1.0)
    assert result.sample_size == 3


def test_spearman_handles_ties_and_pairwise_missing_values(monkeypatch):
    import pandas as pd

    monkeypatch.setattr(
        "backend.app.tools.analysis.correlation.pd.read_csv",
        lambda *args, **kwargs: pd.DataFrame(
            {
                "age": [1, 2, 2, 3, 99, None],
                "score": [4, 1, 1, 2, None, 50],
            }
        ),
    )

    payload = run(
        _ref("clean.csv", {}),
        columns=["age", "score"],
        method="spearman",
        threshold=0.3,
    )

    assert payload["pairs"][0]["coefficient"] == pytest.approx(-1 / 3)
    assert payload["pairs"][0]["sample_size"] == 4
    assert payload["sample_size"] == 6
    assert payload["strong_pairs"] == payload["pairs"]


def test_spearman_retains_constant_column_warnings(monkeypatch):
    import pandas as pd

    monkeypatch.setattr(
        "backend.app.tools.analysis.correlation.pd.read_csv",
        lambda *args, **kwargs: pd.DataFrame({"age": [1, 1, 1], "score": [4, 5, 6]}),
    )

    payload = run(_ref("clean.csv", {}), columns=["age", "score"], method="spearman")

    assert payload["pairs"][0]["coefficient"] is None
    assert payload["strong_pairs"] == []
    assert {"CONSTANT_COLUMN", "INSUFFICIENT_DATA"} <= {
        warning.code for warning in payload["warnings"]
    }
