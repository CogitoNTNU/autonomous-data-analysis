"""Heatmap of how many rows fall in each pair of x and y."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from matplotlib.axes import Axes

from backend.app.contracts.models import DatasetReference
from backend.app.tools.registry import Tool
from backend.app.tools.visualization.figure import save_chart
from backend.app.tools.visualization.inputs import (
    NUMERIC_DTYPES,
    HeatmapInput,
    parse_chart,
)
from backend.app.tools.visualization.load import (
    observation_count,
    failed,
    read_dataset,
    runtime_source_rows,
)
from backend.app.tools.visualization.presentation import category_label


def run(
    dataset: DatasetReference, output_dir: Path | None = None, **kwargs: object
) -> dict[str, object]:
    spec = parse_chart(HeatmapInput, kwargs)
    frame = read_dataset(dataset, runtime_source_rows(kwargs))
    if len(frame) == 0:
        return failed("INSUFFICIENT_DATA", "no rows")
    # antall rader i hvert x/y-par, ikke en tredje verdikolonne
    counts = pd.crosstab(frame[spec.y], frame[spec.x])
    if counts.empty:
        return failed("INSUFFICIENT_DATA", "no observed category pairs")
    return save_chart(
        spec,
        observation_count(kwargs, len(frame)),
        output_dir,
        lambda ax: _draw(ax, counts),
        input_row_count=len(frame),
        kind="heatmap",
        dataset=dataset,
        pre_aggregated=runtime_source_rows(kwargs) is not None,
    )


def _draw(ax: Axes, counts: pd.DataFrame) -> None:
    values = counts.to_numpy()
    image = ax.imshow(values, vmin=0, vmax=max(1, int(values.max())))
    ax.set_xticks(
        range(len(counts.columns)),
        labels=[category_label(name) for name in counts.columns],
    )
    ax.set_yticks(
        range(len(counts.index)), labels=[category_label(name) for name in counts.index]
    )
    ax.figure.colorbar(image, ax=ax)


TOOL = Tool(
    name="heatmap",
    description="Heatmap of row counts for each x and y pair. Required: x, y.",
    input_model=HeatmapInput,
    accepted_dtypes=NUMERIC_DTYPES,
    run=run,
)
