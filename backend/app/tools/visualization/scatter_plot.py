"""Scatter plot of numeric x and y, colored by group when one is given."""

from pathlib import Path

import pandas as pd
from matplotlib.axes import Axes

from backend.app.contracts.models import DatasetReference
from backend.app.tools.registry import Tool
from backend.app.tools.visualization.figure import save_chart
from backend.app.tools.visualization.inputs import (
    NUMERIC_DTYPES,
    XYNumericAxesInput,
    parse_chart,
)
from backend.app.tools.visualization.load import prepare_numeric, runtime_source_rows


def run(
    dataset: DatasetReference, output_dir: Path | None = None, **kwargs: object
) -> dict[str, object]:
    spec = parse_chart(XYNumericAxesInput, kwargs)
    loaded = prepare_numeric(dataset, [spec.x, spec.y], runtime_source_rows(kwargs))
    if isinstance(loaded, dict):
        return loaded
    return save_chart(spec, len(loaded), output_dir, lambda ax: _draw(ax, loaded, spec))


def _draw(ax: Axes, frame: pd.DataFrame, spec: XYNumericAxesInput) -> None:
    # ett punkt per rad. group bare fargelegger, den aggregerer ikke
    if spec.group is None:
        ax.scatter(frame[spec.x], frame[spec.y])
        return
    for name, part in frame.groupby(spec.group, dropna=False):
        ax.scatter(part[spec.x], part[spec.y], label=str(name))
    ax.legend()


TOOL = Tool(
    name="scatter_plot",
    description="Scatter plot of numeric x and y. Required: x, y. Optional: group.",
    input_model=XYNumericAxesInput,
    accepted_dtypes=NUMERIC_DTYPES,
    run=run,
)
