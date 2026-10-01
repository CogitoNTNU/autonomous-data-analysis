"""Bar chart: counts per category, or the mean of a numeric column."""

from pathlib import Path

import pandas as pd

from backend.app.contracts.models import DatasetReference
from backend.app.tools.registry import Tool
from backend.app.tools.visualization.figure import save_chart
from backend.app.tools.visualization.inputs import DTYPES, ChartInput, parse_chart
from backend.app.tools.visualization.load import failed, prepare_numeric, read_dataset


def run(
    dataset: DatasetReference, output_dir: Path | None = None, **kwargs: object
) -> dict[str, object]:
    spec = parse_chart(ChartInput, kwargs)
    loaded = _frame(dataset, spec)
    if isinstance(loaded, dict):
        return loaded
    table = _table(loaded, spec)
    return save_chart(
        spec, len(loaded), output_dir, lambda ax: table.plot(kind="bar", ax=ax)
    )


def _frame(
    dataset: DatasetReference, spec: ChartInput
) -> pd.DataFrame | dict[str, object]:
    if spec.y is None:
        frame = read_dataset(dataset)
        if len(frame) == 0:
            return failed("INSUFFICIENT_DATA", "no rows")
        return frame
    return prepare_numeric(dataset, [spec.y])


def _table(frame: pd.DataFrame, spec: ChartInput) -> pd.Series | pd.DataFrame:
    # uten y teller vi rader, med y tar vi snittet. group blir egne serier
    keys = [spec.x, spec.group] if spec.group else [spec.x]
    if spec.y is None:
        counts = frame.groupby(keys, dropna=False).size()
        return counts.unstack(fill_value=0) if spec.group else counts
    means = frame.groupby(keys, dropna=False)[spec.y].mean()
    return means.unstack() if spec.group else means


TOOL = Tool(
    name="bar_chart",
    description="Bar chart of counts, or mean of y, for each x. Optional: y, group.",
    input_model=ChartInput,
    accepted_dtypes=DTYPES,
    run=run,
)
