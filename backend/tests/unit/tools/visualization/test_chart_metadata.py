"""Known measure names and units remain descriptive through chart dependencies."""

from pathlib import Path

import pytest
from matplotlib.figure import Figure

from backend.app.agents.analysis import run_analysis
from backend.app.contracts.models import DatasetReference, PlanStep
from backend.app.tools.visualization.line_chart import run


def test_chart_uses_known_metadata_without_planner_label_overrides(
    dataset: DatasetReference, saved_figures: list[Figure], tmp_path: Path
) -> None:
    dataset.dataset_schema["sales"].update({"label": "Gross sales", "unit": "NOK"})
    dataset.dataset_schema["month"]["label"] = "Calendar month"

    run(dataset, output_dir=tmp_path, title="Monthly sales", x="month", y="sales")

    axes = saved_figures[0].axes[0]
    assert axes.get_xlabel() == "Calendar month"
    assert axes.get_ylabel() == "Mean of Gross sales (NOK)"


@pytest.mark.parametrize(
    "function,expected_label",
    [
        ("sum", "Total Sales (NOK)"),
        ("mean", "Mean Sales (NOK)"),
        ("count", "Number of nonmissing values of Sales"),
    ],
)
def test_aggregate_chart_preserves_measure_names_and_applicable_units(
    dataset: DatasetReference,
    saved_figures: list[Figure],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    function: str,
    expected_label: str,
) -> None:
    dataset.dataset_schema["sales"].update({"label": "Sales", "unit": "NOK"})
    monkeypatch.setattr(
        "backend.app.tools.visualization.figure.DEFAULT_ARTIFACTS", tmp_path
    )

    engine = run_analysis(
        dataset,
        [
            PlanStep(
                step_id="aggregate",
                tool_name="group_aggregate",
                arguments={
                    "group_by": ["city"],
                    "aggregations": [
                        {"column": "sales", "function": function, "alias": "amount"}
                    ],
                },
            ),
            PlanStep(
                step_id="chart",
                tool_name="bar_chart",
                arguments={"title": "Sales by city", "x": "city", "y": "amount"},
                depends_on=["aggregate"],
            ),
        ],
    )

    assert engine.response.updates.execution_report.outcome == "complete"
    assert saved_figures[0].axes[0].get_ylabel() == expected_label
