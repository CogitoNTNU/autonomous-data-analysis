"""Histogram of one numeric column, overlaid per group when one is given."""

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
    HistogramInput,
    parse_chart,
)
from backend.app.tools.visualization.load import (
    observation_count,
    prepare_numeric,
    runtime_source_rows,
)


def run(
    dataset: DatasetReference, output_dir: Path | None = None, **kwargs: object
) -> dict[str, object]:
    spec = parse_chart(HistogramInput, kwargs)
    loaded = prepare_numeric(dataset, [spec.x], runtime_source_rows(kwargs))
    if isinstance(loaded, dict):
        return loaded
    return save_chart(
        spec,
        observation_count(kwargs, len(loaded)),
        output_dir,
        lambda ax: _draw(ax, loaded, spec),
        input_row_count=len(loaded),
    )


def _draw(ax: Axes, frame: pd.DataFrame, spec: HistogramInput) -> None:
    # group legger fordelingene oppå hverandre så de kan sammenlignes
    if spec.group is None:
        ax.hist(frame[spec.x].dropna())
        return
    for name, part in frame.groupby(spec.group, dropna=False):
        ax.hist(part[spec.x].dropna(), alpha=0.5, label=str(name))
    ax.legend()


TOOL = Tool(
    name="histogram",
    description="Histogram of numeric x. Required: x. Optional: group.",
    input_model=HistogramInput,
    accepted_dtypes=NUMERIC_DTYPES,
    run=run,
)
