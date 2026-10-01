"""Histogram of one numeric column, overlaid per group when one is given."""

from pathlib import Path

import pandas as pd
from matplotlib.axes import Axes

from backend.app.contracts.models import DatasetReference
from backend.app.tools.registry import Tool
from backend.app.tools.visualization.figure import save_chart
from backend.app.tools.visualization.inputs import DTYPES, ChartInput, parse_chart
from backend.app.tools.visualization.load import prepare_numeric


def run(
    dataset: DatasetReference, output_dir: Path | None = None, **kwargs: object
) -> dict[str, object]:
    spec = parse_chart(ChartInput, kwargs)
    loaded = prepare_numeric(dataset, [spec.x])
    if isinstance(loaded, dict):
        return loaded
    return save_chart(spec, len(loaded), output_dir, lambda ax: _draw(ax, loaded, spec))


def _draw(ax: Axes, frame: pd.DataFrame, spec: ChartInput) -> None:
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
    input_model=ChartInput,
    accepted_dtypes=DTYPES,
    run=run,
)
