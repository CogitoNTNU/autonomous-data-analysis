from pathlib import Path

from backend.app.agents.analysis import execute_step, run_analysis
from backend.app.contracts.models import DatasetReference, PlanStep
from backend.app.tools.analysis.categorical import TOOL, run
from backend.app.tools.registry import ToolRegistry

FIXTURES = Path(__file__).resolve().parent / "fixtures"
SCHEMA = {
    "city": {"datatype": "string"},
    "status": {"datatype": "string"},
    "blank": {"datatype": "string"},
}


def _dataset() -> DatasetReference:
    return DatasetReference(
        dataset_id="categories",
        version="v1",
        storage_ref=str(FIXTURES / "categories.csv"),
        schema=SCHEMA,
    )


def _registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(TOOL)
    return registry


def test_counts_each_category():
    payload = run(_dataset(), column="city", normalize=False)
    assert payload["categories"] == [
        {"value": "Bergen", "count": 2},
        {"value": "Oslo", "count": 2},
    ]
    assert payload["missing_count"] == 0


def test_normalize_returns_proportions():
    payload = run(_dataset(), column="city", normalize=True)
    assert payload["categories"] == [
        {"value": "Bergen", "proportion": 0.5},
        {"value": "Oslo", "proportion": 0.5},
    ]


def test_unknown_column_is_rejected_before_the_file_is_read():
    dataset = DatasetReference(
        dataset_id="missing-file",
        version="v1",
        storage_ref="/tmp/categorical-analysis-missing.csv",
        schema=SCHEMA,
    )
    result = execute_step(
        PlanStep(
            step_id="cats",
            tool_name="categorical_analysis",
            arguments={"column": "missing", "normalize": False},
        ),
        dataset,
        _registry(),
    )
    assert result.values["code"] == "MISSING_COLUMN"


def test_empty_column_is_insufficient_data():
    payload = run(_dataset(), column="blank", normalize=False)
    assert payload["categories"] == []
    assert any(item.code == "INSUFFICIENT_DATA" for item in payload["warnings"])


def test_constant_column_is_flagged():
    payload = run(_dataset(), column="status", normalize=False)
    assert payload["n_categories"] == 1
    assert any(item.code == "CONSTANT_COLUMN" for item in payload["warnings"])


def test_analysis_agent_runs_categorical_analysis():
    engine = run_analysis(
        _dataset(),
        [
            PlanStep(
                step_id="cats",
                tool_name="categorical_analysis",
                arguments={"column": "city", "normalize": False},
            )
        ],
    )
    results = engine.response.updates.analysis_results
    assert results[0].method == "categorical_analysis"
    assert results[0].values["categories"][0]["value"] == "Bergen"
