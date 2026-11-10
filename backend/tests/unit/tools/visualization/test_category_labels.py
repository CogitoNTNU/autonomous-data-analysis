"""Missing categories are readable without merging them with literal names."""

from pathlib import Path

import pandas as pd
import pytest
from matplotlib.figure import Figure

from backend.app.contracts.models import DatasetReference
from backend.app.tools.visualization.catalog import TOOLS
from backend.app.tools.visualization.presentation import category_label

MISSING = "Missing (no value)"
ROWS = [
    {"city": city, "month": index + 1, "sales": (index + 1) * 10}
    for index, city in enumerate(["Oslo", None, "nan", "None", MISSING])
]


@pytest.mark.parametrize("value", [None, float("nan"), pd.NA, pd.NaT])
def test_missing_scalars_have_a_human_readable_label(value: object) -> None:
    assert category_label(value) == MISSING


@pytest.mark.parametrize("value", ["nan", "None", "Oslo", MISSING, 10])
def test_literal_category_names_are_preserved(value: object) -> None:
    assert category_label(value) == str(value)


@pytest.mark.parametrize("tool_name", ["bar_chart", "line_chart", "boxplot"])
def test_categorical_axes_label_missing_values_after_aggregation(
    dataset: DatasetReference,
    saved_figures: list[Figure],
    tmp_path: Path,
    tool_name: str,
) -> None:
    tool = next(tool for tool in TOOLS if tool.name == tool_name)

    tool.run(
        dataset,
        output_dir=tmp_path,
        title="Sales by location",
        x="city",
        y="sales",
        _source_rows=ROWS,
        _source_sample_size=len(ROWS),
    )

    axes = saved_figures[0].axes[0]
    ticks = [label.get_text() for label in axes.get_xticklabels()]
    assert sorted(ticks) == sorted(["Oslo", MISSING, "nan", "None", MISSING])
    if tool_name == "bar_chart":
        assert sorted(patch.get_height() for patch in axes.patches) == [
            10,
            20,
            30,
            40,
            50,
        ]
    elif tool_name == "line_chart":
        assert sorted(axes.lines[0].get_ydata()) == [10, 20, 30, 40, 50]


@pytest.mark.parametrize(
    "tool_name", ["bar_chart", "line_chart", "scatter_plot", "histogram"]
)
def test_group_legends_keep_missing_and_literal_groups_distinct(
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
        title="Sales by location",
        group="city",
        _source_rows=ROWS,
        _source_sample_size=len(ROWS),
        **arguments,
    )

    legend = saved_figures[0].axes[0].get_legend()
    labels = [label.get_text() for label in legend.get_texts()]
    assert sorted(labels) == sorted(["Oslo", MISSING, "nan", "None", MISSING])
    assert len(legend.legend_handles) == 5


def test_numeric_line_coordinates_are_not_converted_to_categories(
    dataset: DatasetReference, saved_figures: list[Figure], tmp_path: Path
) -> None:
    tool = next(tool for tool in TOOLS if tool.name == "line_chart")

    tool.run(
        dataset,
        output_dir=tmp_path,
        title="Sales by month",
        x="month",
        y="sales",
        _source_rows=[{"month": 1, "sales": 10}, {"month": 10, "sales": 20}],
        _source_sample_size=2,
    )

    assert list(saved_figures[0].axes[0].lines[0].get_xdata()) == [1, 10]


def test_heatmap_preserves_literal_names_and_existing_null_exclusion(
    dataset: DatasetReference, saved_figures: list[Figure], tmp_path: Path
) -> None:
    tool = next(tool for tool in TOOLS if tool.name == "heatmap")

    tool.run(
        dataset,
        output_dir=tmp_path,
        title="Location and month counts",
        x="city",
        y="month",
        _source_rows=ROWS,
        _source_sample_size=len(ROWS),
    )

    axes = saved_figures[0].axes[0]
    assert sorted(label.get_text() for label in axes.get_xticklabels()) == sorted(
        ["Oslo", "nan", "None", MISSING]
    )
    assert axes.images[0].get_array().sum() == 4
