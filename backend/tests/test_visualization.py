from pathlib import Path

from backend.app.agents.analysis import execute_step, run_analysis
from backend.app.agents.preprocessing import register_preprocessing_tools
from backend.app.contracts.models import DatasetReference, PlanStep
from backend.app.tools.analysis.descriptive import default_registry
from backend.app.tools.registry import ToolRegistry
from backend.app.tools.visualization.bar_chart import run as run_bar
from backend.app.tools.visualization.catalog import TOOLS, register_visualization

FIXTURES = Path(__file__).resolve().parent / "fixtures"
SCHEMA = {
    "city": {"datatype": "string"},
    "sales": {"datatype": "integer"},
    "month": {"datatype": "integer"},
}
CHARTS = {
    "bar_chart": {"title": "Sales", "x": "city", "y": "sales"},
    "line_chart": {"title": "Sales", "x": "month", "y": "sales"},
    "scatter_plot": {"title": "Sales", "x": "month", "y": "sales"},
    "histogram": {"title": "Sales", "x": "sales"},
    "boxplot": {"title": "Sales", "x": "city", "y": "sales"},
    "heatmap": {"title": "Sales", "x": "city", "y": "month"},
}


def _dataset() -> DatasetReference:
    return DatasetReference(
        dataset_id="charts",
        version="v1",
        storage_ref=str(FIXTURES / "charts.csv"),
        schema=SCHEMA,
    )


def _registry() -> ToolRegistry:
    registry = ToolRegistry()
    register_visualization(registry)
    return registry


def test_each_chart_writes_a_png(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "backend.app.tools.visualization.figure.DEFAULT_ARTIFACTS", tmp_path
    )
    for tool in TOOLS:
        payload = tool.run(_dataset(), output_dir=tmp_path, **CHARTS[tool.name])
        path = Path(payload["artifacts"][0]["storage_ref"])
        assert path.read_bytes().startswith(b"\x89PNG")
        assert payload["artifacts"][0]["type"] == "figure"
        assert any(item["code"] == "LOW_SAMPLE_SIZE" for item in payload["warnings"])


def test_bar_chart_records_the_source_result_id(tmp_path):
    payload = run_bar(
        _dataset(),
        output_dir=tmp_path,
        title="Sales",
        x="city",
        y="sales",
        source_result_id="r1",
    )
    assert payload["source_result_ids"] == ["r1"]


def test_bar_chart_counts_categories_when_y_is_absent(tmp_path):
    payload = run_bar(_dataset(), output_dir=tmp_path, title="Cities", x="city")
    assert Path(payload["artifacts"][0]["storage_ref"]).is_file()


def test_heatmap_requires_y():
    result = execute_step(
        PlanStep(
            step_id="draw",
            tool_name="heatmap",
            arguments={"title": "Sales", "x": "city"},
        ),
        _dataset(),
        _registry(),
    )
    assert result.values["code"] == "INVALID_DATA"


def test_bar_chart_rejects_a_string_measure(tmp_path):
    payload = run_bar(
        _dataset(), output_dir=tmp_path, title="Sales", x="month", y="city"
    )
    assert payload["code"] == "INVALID_DATA"
    assert list(tmp_path.glob("*.png")) == []


def test_unknown_column_is_rejected_before_the_chart_is_drawn():
    result = execute_step(
        PlanStep(
            step_id="draw",
            tool_name="bar_chart",
            arguments={"title": "Sales", "x": "missing"},
        ),
        _dataset(),
        _registry(),
    )
    assert result.values["code"] == "MISSING_COLUMN"


def test_analysis_agent_runs_a_registered_bar_chart(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "backend.app.tools.visualization.figure.DEFAULT_ARTIFACTS", tmp_path
    )
    engine = run_analysis(
        _dataset(),
        [
            PlanStep(
                step_id="draw",
                tool_name="bar_chart",
                arguments=CHARTS["bar_chart"],
            )
        ],
    )
    results = engine.response.updates.analysis_results
    assert results[0].method == "bar_chart"
    assert engine.response.updates.artifacts[0].type == "figure"
    assert Path(engine.response.updates.artifacts[0].storage_ref).is_file()


def test_composed_workflow_registry_runs_visualization(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "backend.app.tools.visualization.figure.DEFAULT_ARTIFACTS", tmp_path
    )
    registry = register_preprocessing_tools(default_registry())

    engine = run_analysis(
        _dataset(),
        [
            PlanStep(
                step_id="draw",
                tool_name="bar_chart",
                arguments=CHARTS["bar_chart"],
            )
        ],
        registry=registry,
    )

    result = engine.response.updates.analysis_results[0]
    assert result.values["status"] == "partial"
    assert engine.response.updates.artifacts[0].type == "figure"


def test_analysis_rejects_unknown_source_result(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "backend.app.tools.visualization.figure.DEFAULT_ARTIFACTS", tmp_path
    )
    arguments = {**CHARTS["bar_chart"], "source_result_id": "missing-result"}

    engine = run_analysis(
        _dataset(),
        [
            PlanStep(
                step_id="draw",
                tool_name="bar_chart",
                arguments=arguments,
            )
        ],
    )

    result = engine.response.updates.analysis_results[0]
    assert result.values["code"] == "INVALID_DATA"
    assert "source_result_id" in result.values["error"]
    assert engine.response.updates.artifacts == []
    assert list(tmp_path.glob("*.png")) == []


def test_bar_chart_consumes_group_aggregate_output(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "backend.app.tools.visualization.figure.DEFAULT_ARTIFACTS", tmp_path
    )
    engine = run_analysis(
        _dataset(),
        [
            PlanStep(
                step_id="aggregate",
                tool_name="group_aggregate",
                arguments={
                    "group_by": ["city"],
                    "aggregations": [
                        {
                            "column": "sales",
                            "function": "mean",
                            "alias": "mean_sales",
                        }
                    ],
                },
            ),
            PlanStep(
                step_id="draw",
                tool_name="bar_chart",
                arguments={
                    "title": "Average sales by city",
                    "x": "city",
                    "y": "mean_sales",
                    "source_result_id": "aggregate",
                },
                depends_on=["aggregate"],
            ),
        ],
    )

    aggregate, chart = engine.response.updates.analysis_results
    assert aggregate.values["status"] == "partial"
    assert chart.values["status"] == "partial"
    assert chart.values["source_result_ids"] == [aggregate.result_id]
    artifact = engine.response.updates.artifacts[0]
    assert Path(artifact.storage_ref).read_bytes().startswith(b"\x89PNG")
