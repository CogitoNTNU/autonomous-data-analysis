"""Every chart artifact describes its axes, summaries, groups, and color scale."""

from pathlib import Path

import pytest
from matplotlib.figure import Figure
from pydantic import ValidationError

from backend.app.contracts.models import DatasetReference, PlanStep
from backend.app.tools.analysis.descriptive import default_registry
from backend.app.tools.registry import execute_step
from backend.app.tools.visualization.catalog import TOOLS
from backend.app.tools.visualization.inputs import ChartInput

CASES = [
    (
        "bar_chart",
        {"x": "city"},
        "City",
        "Number of observations",
        "Observation counts",
    ),
    (
        "bar_chart",
        {"x": "city", "y": "sales"},
        "City",
        "Mean of Sales",
        "Mean of Sales",
    ),
    (
        "line_chart",
        {"x": "month", "y": "sales"},
        "Month",
        "Mean of Sales",
        "Mean of Sales",
    ),
    (
        "scatter_plot",
        {"x": "month", "y": "sales"},
        "Month",
        "Sales",
        "Each point represents",
    ),
    ("histogram", {"x": "sales"}, "Sales", "Number of observations", "Each bar counts"),
    ("boxplot", {"x": "city", "y": "sales"}, "City", "Sales", "line: median"),
    (
        "heatmap",
        {"x": "city", "y": "month"},
        "City",
        "Month",
        "Color shows observation counts",
    ),
]


@pytest.mark.parametrize("tool_name,arguments,x_label,y_label,description", CASES)
def test_every_chart_saves_descriptive_axes_and_operation(
    dataset: DatasetReference,
    saved_figures: list[Figure],
    tmp_path: Path,
    tool_name: str,
    arguments: dict[str, str],
    x_label: str,
    y_label: str,
    description: str,
) -> None:
    tool = next(tool for tool in TOOLS if tool.name == tool_name)

    payload = tool.run(
        dataset, output_dir=tmp_path, title="Sales overview", **arguments
    )

    axes = saved_figures[0].axes[0]
    assert axes.get_title().startswith("Sales overview\n")
    assert description in axes.get_title()
    assert axes.get_xlabel() == x_label
    assert axes.get_ylabel() == y_label
    if tool_name == "bar_chart":
        assert all(label.get_rotation() == 0 for label in axes.get_xticklabels())
    assert (
        Path(payload["artifacts"][0]["storage_ref"]).read_bytes().startswith(b"\x89PNG")
    )


@pytest.mark.parametrize(
    "tool_name", ["bar_chart", "line_chart", "scatter_plot", "histogram"]
)
def test_grouped_charts_explain_the_series_legend(
    dataset: DatasetReference,
    saved_figures: list[Figure],
    tmp_path: Path,
    tool_name: str,
) -> None:
    tool = next(tool for tool in TOOLS if tool.name == tool_name)
    arguments = (
        {"x": "sales"} if tool_name == "histogram" else {"x": "month", "y": "sales"}
    )

    tool.run(
        dataset,
        output_dir=tmp_path,
        title="Sales by city",
        group="city",
        group_label="Store location",
        **arguments,
    )

    legend = saved_figures[0].axes[0].get_legend()
    assert legend is not None
    assert legend.get_title().get_text() == "Store location"
    assert {item.get_text() for item in legend.get_texts()} == {"Oslo", "Bergen"}


def test_heatmap_labels_match_category_axes_and_count_color_scale(
    dataset: DatasetReference, saved_figures: list[Figure], tmp_path: Path
) -> None:
    tool = next(tool for tool in TOOLS if tool.name == "heatmap")

    tool.run(dataset, output_dir=tmp_path, title="Transactions", x="city", y="month")

    axes = saved_figures[0].axes[0]
    assert [label.get_text() for label in axes.get_xticklabels()] == ["Bergen", "Oslo"]
    assert [label.get_text() for label in axes.get_yticklabels()] == ["1", "2"]
    colorbar = axes.images[0].colorbar
    assert colorbar.ax.get_ylabel() == "Number of observations"
    assert all(float(tick).is_integer() for tick in colorbar.get_ticks())


def test_readable_labels_and_units_do_not_become_column_references(
    dataset: DatasetReference,
    saved_figures: list[Figure],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "backend.app.tools.visualization.figure.DEFAULT_ARTIFACTS", tmp_path
    )

    result = execute_step(
        PlanStep(
            step_id="plot",
            tool_name="line_chart",
            arguments={
                "title": "Mean monthly sales",
                "x": "month",
                "y": "sales",
                "x_label": "Month of year",
                "y_label": "Sales (NOK)",
            },
        ),
        dataset,
        default_registry(),
    )

    assert result.values["status"] != "failed"
    axes = saved_figures[0].axes[0]
    assert axes.get_xlabel() == "Month of year"
    assert axes.get_ylabel() == "Mean of Sales (NOK)"


@pytest.mark.parametrize("field", ["title", "x_label", "y_label", "group_label"])
def test_blank_chart_descriptions_are_rejected(field: str) -> None:
    arguments = {"title": "Sales", "x": "sales", "group": "city", field: "   "}

    with pytest.raises(ValidationError):
        ChartInput.model_validate(arguments)


def test_a_legend_label_requires_a_group_column() -> None:
    with pytest.raises(ValidationError, match="group_label requires"):
        ChartInput(title="Sales", x="sales", group_label="City")


@pytest.mark.parametrize("tool_name", ["boxplot", "heatmap"])
def test_unsupported_grouping_cannot_be_silently_omitted(tool_name: str) -> None:
    tool = next(tool for tool in TOOLS if tool.name == tool_name)

    with pytest.raises(ValidationError):
        tool.input_model.model_validate(
            {"title": "Sales", "x": "city", "y": "sales", "group": "month"}
        )


@pytest.mark.parametrize("tool_name", ["bar_chart", "line_chart"])
def test_precomputed_totals_are_not_labeled_as_means(
    dataset: DatasetReference,
    saved_figures: list[Figure],
    tmp_path: Path,
    tool_name: str,
) -> None:
    tool = next(tool for tool in TOOLS if tool.name == tool_name)

    tool.run(
        dataset,
        output_dir=tmp_path,
        title="Total sales by city",
        x="city",
        y="sales",
        y_label="Total sales (NOK)",
        _source_rows=[{"city": "Oslo", "sales": 40}, {"city": "Bergen", "sales": 60}],
        _source_sample_size=4,
    )

    axes = saved_figures[0].axes[0]
    assert axes.get_ylabel() == "Total sales (NOK)"
    assert "Aggregated values" in axes.get_title()


def test_averaging_multiple_aggregate_rows_is_still_labeled_as_a_mean(
    dataset: DatasetReference, saved_figures: list[Figure], tmp_path: Path
) -> None:
    tool = next(tool for tool in TOOLS if tool.name == "bar_chart")

    tool.run(
        dataset,
        output_dir=tmp_path,
        title="Mean of city totals",
        x="city",
        y="sales",
        y_label="City total",
        _source_rows=[{"city": "Oslo", "sales": 40}, {"city": "Oslo", "sales": 60}],
        _source_sample_size=4,
    )

    assert saved_figures[0].axes[0].get_ylabel() == "Mean of City total"


def test_default_labels_expand_column_names_without_inventing_units(
    dataset: DatasetReference, saved_figures: list[Figure], tmp_path: Path
) -> None:
    tool = next(tool for tool in TOOLS if tool.name == "scatter_plot")

    tool.run(
        dataset,
        output_dir=tmp_path,
        title="Price and order size",
        x="unit_price",
        y="orderQuantity",
        _source_rows=[{"unit_price": 10, "orderQuantity": 2}],
        _source_sample_size=1,
    )

    axes = saved_figures[0].axes[0]
    assert axes.get_xlabel() == "Unit price"
    assert axes.get_ylabel() == "Order Quantity"


def test_derived_histogram_describes_group_counts_instead_of_source_rows(
    dataset: DatasetReference, saved_figures: list[Figure], tmp_path: Path
) -> None:
    tool = next(tool for tool in TOOLS if tool.name == "histogram")

    payload = tool.run(
        dataset,
        output_dir=tmp_path,
        title="Distribution of group totals",
        x="sales",
        _source_rows=[{"sales": 40}, {"sales": 60}],
        _source_sample_size=342,
    )

    axes = saved_figures[0].axes[0]
    assert axes.get_ylabel() == "Number of groups"
    assert "Each bar counts groups" in axes.get_title()
    assert payload["sample_size"] == 342
    assert payload["input_row_count"] == 2


def test_long_chart_descriptions_wrap_and_category_ticks_rotate(
    dataset: DatasetReference, saved_figures: list[Figure], tmp_path: Path
) -> None:
    tool = next(tool for tool in TOOLS if tool.name == "bar_chart")
    title = "Monthly sales for stores with lengthy geographic descriptions " * 3

    tool.run(
        dataset,
        output_dir=tmp_path,
        title=title,
        x="city",
        y="sales",
        x_label="Geographic location of the store reporting each monthly sales total",
        _source_rows=[
            {"city": "Bergen metropolitan area", "sales": 20},
            {"city": "Oslo metropolitan area", "sales": 30},
        ],
        _source_sample_size=4,
    )

    axes = saved_figures[0].axes[0]
    assert max(len(line) for line in axes.get_title().splitlines()) <= 75
    assert "\n" in axes.get_xlabel()
    assert all(label.get_rotation() == 40 for label in axes.get_xticklabels())
