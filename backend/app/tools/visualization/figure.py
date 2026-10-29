"""Write one PNG and the artifact reference the analysis agent stores."""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from matplotlib.axes import Axes

from backend.app.contracts.models import Artifact, VisualizationResult, WarningEvent
from backend.app.tools.visualization.inputs import ChartInput
from backend.app.tools.visualization.load import (
    DEFAULT_ARTIFACTS,
    HOSTED_ARTIFACTS,
    SOURCE,
)


def save_chart(
    spec: ChartInput,
    sample_size: int,
    output_dir: Path | None,
    draw: Callable[[Axes], None],
    *,
    input_row_count: int,
) -> dict[str, object]:
    # png-en lagres utenfor state, bare referansen sendes videre
    directory = output_dir if output_dir is not None else _default_directory()
    artifact = _write_png(draw, spec, directory)
    result = VisualizationResult(
        sample_size=sample_size,
        input_row_count=input_row_count,
        source_result_ids=_sources(spec),
        artifacts=[artifact],
        warnings=_warnings(sample_size),
    )
    return result.model_dump()


def _default_directory() -> Path:
    if os.getenv("VERCEL"):
        return HOSTED_ARTIFACTS
    return DEFAULT_ARTIFACTS


def _write_png(
    draw: Callable[[Axes], None], spec: ChartInput, directory: Path
) -> Artifact:
    directory.mkdir(parents=True, exist_ok=True)
    artifact_id = str(uuid4())
    path = directory / f"{artifact_id}.png"
    plt = _pyplot()
    figure, axes = plt.subplots()
    try:
        draw(axes)
        axes.set_title(spec.title)
        axes.set_xlabel(spec.x)
        if spec.y is not None:
            axes.set_ylabel(spec.y)
        figure.savefig(path, bbox_inches="tight")
    finally:
        plt.close(figure)
    return Artifact(artifact_id=artifact_id, type="figure", storage_ref=str(path))


def _pyplot():
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
    os.environ.setdefault("MPLBACKEND", "Agg")
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    return plt


def _sources(spec: ChartInput) -> list[str]:
    if spec.source_result_id is None:
        return []
    return [spec.source_result_id]


def _warnings(sample_size: int) -> list[WarningEvent]:
    # samme tommelfingerregel som descriptive: under 30 rader er tynt
    if sample_size < 30:
        message = f"n={sample_size}"
        return [WarningEvent(code="LOW_SAMPLE_SIZE", message=message, source=SOURCE)]
    return []
