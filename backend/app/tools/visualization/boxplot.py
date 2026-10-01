"""Box plot of numeric y, one box per x category when x is given."""

from pathlib import Path

import pandas as pd
from matplotlib.axes import Axes

from backend.app.contracts.models import DatasetReference
from backend.app.tools.registry import Tool
from backend.app.tools.visualization.figure import save_chart
from backend.app.tools.visualization.inputs import (
    NUMERIC_DTYPES,
    YNumericAxesInput,
    parse_chart,
)
from backend.app.tools.visualization.load import prepare_numeric, runtime_source_rows


def run(
    dataset: DatasetReference, output_dir: Path | None = None, **kwargs: object
) -> dict[str, object]:
    spec = parse_chart(YNumericAxesInput, kwargs)
    loaded = prepare_numeric(dataset, [spec.y], runtime_source_rows(kwargs))
    if isinstance(loaded, dict):
        return loaded
    return save_chart(spec, len(loaded), output_dir, lambda ax: _draw(ax, loaded, spec))


def _draw(ax: Axes, frame: pd.DataFrame, spec: YNumericAxesInput) -> None:
    # en boks per kategori i x, y er selve fordelingen
    grouped = frame.groupby(spec.x, dropna=False)[spec.y]
    series = [part.dropna() for _, part in grouped]
    ax.boxplot(series)
    ax.set_xticklabels([str(name) for name, _ in grouped])


TOOL = Tool(
    name="boxplot",
    description="Box plot of numeric y for each x. Required: x, y.",
    input_model=YNumericAxesInput,
    accepted_dtypes=NUMERIC_DTYPES,
    run=run,
)
