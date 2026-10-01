"""Line chart of mean y against x, split by group when one is given."""

from pathlib import Path

import pandas as pd

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
    table = _table(loaded, spec)
    return save_chart(spec, len(loaded), output_dir, lambda ax: table.plot(ax=ax))


def _table(frame: pd.DataFrame, spec: YNumericAxesInput) -> pd.Series | pd.DataFrame:
    # snitt av y per x, sortert så linja går i rekkefølge. group er en linje hver
    keys = [spec.x, spec.group] if spec.group else [spec.x]
    means = frame.groupby(keys, dropna=False)[spec.y].mean()
    ordered = means.sort_index()
    return ordered.unstack() if spec.group else ordered


TOOL = Tool(
    name="line_chart",
    description="Line chart of mean y for each x. Required: x, y. Optional: group.",
    input_model=YNumericAxesInput,
    accepted_dtypes=NUMERIC_DTYPES,
    run=run,
)
