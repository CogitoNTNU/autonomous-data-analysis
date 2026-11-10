"""Line chart of mean y against x, split by group when one is given."""

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
    YNumericAxesInput,
    parse_chart,
)
from backend.app.tools.visualization.load import (
    observation_count,
    prepare_numeric,
    runtime_source_rows,
)
from backend.app.tools.visualization.presentation import label_table_categories


def run(
    dataset: DatasetReference, output_dir: Path | None = None, **kwargs: object
) -> dict[str, object]:
    spec = parse_chart(YNumericAxesInput, kwargs)
    source_rows = runtime_source_rows(kwargs)
    loaded = prepare_numeric(dataset, [spec.y], source_rows)
    if isinstance(loaded, dict):
        return loaded
    table = label_table_categories(_table(loaded, spec))
    keys = [spec.x, spec.group] if spec.group else [spec.x]
    return save_chart(
        spec,
        observation_count(kwargs, len(loaded)),
        output_dir,
        lambda ax: _draw(ax, table),
        input_row_count=len(loaded),
        kind="line_chart",
        dataset=dataset,
        pre_aggregated=source_rows is not None,
        mean_applied=source_rows is None or bool(loaded.duplicated(keys).any()),
    )


def _draw(ax: Axes, table: pd.Series | pd.DataFrame) -> None:
    table.plot(ax=ax)
    if (
        pd.api.types.is_object_dtype(table.index)
        or pd.api.types.is_string_dtype(table.index)
        or isinstance(table.index, pd.CategoricalIndex)
    ):
        # Explicit positions keep identically displayed category names distinct.
        ax.set_xticks(range(len(table.index)), labels=list(table.index))


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
