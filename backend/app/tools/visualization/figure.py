"""Write one PNG and the artifact reference the analysis agent stores."""

from collections.abc import Callable
from pathlib import Path
from uuid import uuid4

import matplotlib

matplotlib.use("Agg")  # ingen GUI, vi skriver bare en fil
from matplotlib import pyplot as plt
from matplotlib.axes import Axes

from backend.app.contracts.models import Artifact
from backend.app.tools.visualization.inputs import ChartInput
from backend.app.tools.visualization.load import DEFAULT_ARTIFACTS, SOURCE


def save_chart(
    spec: ChartInput,
    sample_size: int,
    output_dir: Path | None,
    draw: Callable[[Axes], None],
) -> dict[str, object]:
    # png-en lagres utenfor state, bare referansen sendes videre
    directory = output_dir if output_dir is not None else DEFAULT_ARTIFACTS
    artifact = _write_png(draw, spec, directory)
    return {
        "sample_size": sample_size,
        "source_result_ids": _sources(spec),
        "artifacts": [artifact.model_dump()],
        "warnings": _warnings(sample_size),
    }


def _write_png(
    draw: Callable[[Axes], None], spec: ChartInput, directory: Path
) -> Artifact:
    directory.mkdir(parents=True, exist_ok=True)
    artifact_id = str(uuid4())
    path = directory / f"{artifact_id}.png"
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


def _sources(spec: ChartInput) -> list[str]:
    if spec.source_result_id is None:
        return []
    return [spec.source_result_id]


def _warnings(sample_size: int) -> list[dict[str, str]]:
    # samme tommelfingerregel som descriptive: under 30 rader er tynt
    if sample_size < 30:
        message = f"n={sample_size}"
        return [{"code": "LOW_SAMPLE_SIZE", "message": message, "source": SOURCE}]
    return []
