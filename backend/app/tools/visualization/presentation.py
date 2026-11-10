"""Apply descriptive labels and readable layout to every supported chart."""

from __future__ import annotations

import re
from textwrap import fill
from typing import TYPE_CHECKING

import pandas as pd

from backend.app.contracts.models import DatasetReference
from backend.app.tools.visualization.inputs import ChartInput, ChartKind

if TYPE_CHECKING:
    from matplotlib.axes import Axes


def readable_name(column: str) -> str:
    """Expand column identifiers without guessing their units or meaning."""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", column.replace("_", " "))
    label = " ".join(spaced.split())
    return label[:1].upper() + label[1:]


def category_label(value: object) -> str:
    """Describe missing scalar categories without rewriting literal strings."""
    if not isinstance(value, str) and pd.isna(value):
        return "Missing (no value)"
    return str(value)


def label_table_categories(
    table: pd.Series | pd.DataFrame, *, categorical_x: bool = False
) -> pd.Series | pd.DataFrame:
    """Format categories after aggregation while retaining numeric/time axes."""
    if categorical_x or not (
        pd.api.types.is_numeric_dtype(table.index)
        or isinstance(
            table.index, (pd.DatetimeIndex, pd.TimedeltaIndex, pd.PeriodIndex)
        )
    ):
        table = table.rename(index=category_label)
    if isinstance(table, pd.DataFrame):
        table = table.rename(columns=category_label)
    return table


def describe_chart(
    axes: Axes,
    spec: ChartInput,
    kind: ChartKind,
    dataset: DatasetReference,
    *,
    pre_aggregated: bool = False,
    mean_applied: bool = False,
) -> None:
    """Label the actual operation, both axes, groups, and any count scale."""
    from matplotlib.ticker import MaxNLocator

    x_label = _column_label(spec.x, spec.x_label, dataset)
    measure = _column_label(spec.y, spec.y_label, dataset) if spec.y else ""
    count_label = "Number of groups" if pre_aggregated else "Number of observations"
    count_axis = kind == "histogram" or (kind == "bar_chart" and spec.y is None)
    if count_axis:
        y_label = f"{spec.y_label} (count)" if spec.y_label else count_label
        axes.yaxis.set_major_locator(MaxNLocator(integer=True))
    elif mean_applied:
        y_label = f"Mean of {measure}"
    else:
        y_label = measure
    if not x_label.strip() or not y_label.strip():
        raise ValueError("Charts require descriptive labels for both axes")
    description = _description(
        kind, x_label, measure, count_axis, pre_aggregated, mean_applied
    )
    axes.set_title(f"{fill(spec.title, 65)}\n{fill(description, 75)}", pad=12)
    axes.set_xlabel(fill(x_label, 55), labelpad=8)
    axes.set_ylabel(fill(y_label, 55), labelpad=8)
    _describe_legend(axes, spec, dataset)
    if kind == "heatmap":
        colorbar = axes.images[0].colorbar
        colorbar.set_label(count_label, labelpad=10)
        colorbar.locator = MaxNLocator(integer=True)
        colorbar.update_ticks()
    _readable_ticks(axes)


def _description(
    kind: ChartKind,
    x_label: str,
    measure: str,
    count_axis: bool,
    pre_aggregated: bool,
    mean_applied: bool,
) -> str:
    counted = "groups" if pre_aggregated else "observations"
    match kind:
        case "histogram":
            return f"Histogram • Each bar counts {counted} within a value range"
        case "bar_chart" if count_axis:
            return f"Bar chart • {'Group' if pre_aggregated else 'Observation'} counts by {x_label}"
        case "bar_chart" | "line_chart":
            if mean_applied:
                return f"Mean of {measure} for each {x_label}"
            return f"Aggregated values of {measure} for each {x_label}"
        case "scatter_plot":
            if pre_aggregated:
                return "Scatter plot • Each point represents one aggregated group"
            return "Scatter plot • Each point represents one observation"
        case "boxplot":
            scope = "Aggregated groups • " if pre_aggregated else ""
            return f"{scope}Box: middle 50%; line: median; whiskers: up to 1.5×IQR; dots: outliers"
        case "heatmap":
            return f"Heatmap • Color shows {'group' if pre_aggregated else 'observation'} counts for each category pair"
    raise ValueError(f"Unsupported chart kind: {kind}")


def _column_label(column: str, supplied: str | None, dataset: DatasetReference) -> str:
    if supplied is not None:
        return supplied
    label = readable_name(column)
    metadata = dataset.dataset_schema.get(column)
    if isinstance(metadata, dict):
        known_label = metadata.get("label")
        if isinstance(known_label, str) and known_label.strip():
            label = known_label.strip()
        unit = metadata.get("unit")
        if isinstance(unit, str) and unit.strip():
            label = f"{label} ({unit.strip()})"
    return label


def _describe_legend(axes: Axes, spec: ChartInput, dataset: DatasetReference) -> None:
    if spec.group is None:
        legend = axes.get_legend()
        if legend is not None:
            legend.remove()
        return
    handles, labels = axes.get_legend_handles_labels()
    if not handles:
        raise ValueError("Grouped charts require labeled series")
    axes.legend(
        handles,
        [fill(label, 28) for label in labels],
        title=fill(_column_label(spec.group, spec.group_label, dataset), 28),
        loc="upper left",
        bbox_to_anchor=(1.02, 1),
    )


def _readable_ticks(axes: Axes) -> None:
    labels = axes.get_xticklabels()
    crowded_categories = len(labels) > 8 and any(
        not _numeric_tick(label.get_text()) for label in labels
    )
    rotate = crowded_categories or any(len(label.get_text()) > 12 for label in labels)
    for label in labels:
        label.set_rotation(40 if rotate else 0)
        label.set_ha("right" if rotate else "center")


def _numeric_tick(text: str) -> bool:
    try:
        float(text.replace("−", "-"))
    except ValueError:
        return False
    return True
