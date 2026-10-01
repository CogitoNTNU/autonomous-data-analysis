"""Heatmap of how many rows fall in each pair of x and y."""

from pathlib import Path

import pandas as pd
from matplotlib.axes import Axes

from backend.app.contracts.models import DatasetReference
from backend.app.tools.registry import Tool
from backend.app.tools.visualization.figure import save_chart
from backend.app.tools.visualization.inputs import (
    NUMERIC_DTYPES,
    AxesInput,
    parse_chart,
)
from backend.app.tools.visualization.load import (
    failed,
    read_dataset,
    runtime_source_rows,
)


def run(
    dataset: DatasetReference, output_dir: Path | None = None, **kwargs: object
) -> dict[str, object]:
    spec = parse_chart(AxesInput, kwargs)
    frame = read_dataset(dataset, runtime_source_rows(kwargs))
    if len(frame) == 0:
        return failed("INSUFFICIENT_DATA", "no rows")
    # antall rader i hvert x/y-par, ikke en tredje verdikolonne
    counts = pd.crosstab(frame[spec.x], frame[spec.y])
    return save_chart(spec, len(frame), output_dir, lambda ax: _draw(ax, counts))


def _draw(ax: Axes, counts: pd.DataFrame) -> None:
    image = ax.imshow(counts.to_numpy())
    ax.set_xticks(
        range(len(counts.columns)), labels=[str(name) for name in counts.columns]
    )
    ax.set_yticks(range(len(counts.index)), labels=[str(name) for name in counts.index])
    ax.figure.colorbar(image, ax=ax)


TOOL = Tool(
    name="heatmap",
    description="Heatmap of row counts for each x and y pair. Required: x, y.",
    input_model=AxesInput,
    accepted_dtypes=NUMERIC_DTYPES,
    run=run,
)
