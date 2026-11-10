"""Histogram artifacts explain their count axis, including grouped charts."""

from pathlib import Path

import pytest
from matplotlib.figure import Figure

from backend.app.contracts.models import DatasetReference, PlanStep
from backend.app.tools.analysis.descriptive import default_registry
from backend.app.tools.registry import execute_step
from backend.app.tools.visualization.histogram import run

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures"


def _dataset() -> DatasetReference:
    return DatasetReference(
        dataset_id="charts",
        version="v1",
        storage_ref=str(FIXTURES / "charts.csv"),
        schema={
            "city": {"datatype": "string"},
            "sales": {"datatype": "integer"},
        },
    )


@pytest.mark.parametrize("group", [None, "city"])
def test_saved_histogram_labels_its_count_axis(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, group: str | None
) -> None:
    saved_labels: list[tuple[str, str, str]] = []
    original_save = Figure.savefig

    def save_figure(figure: Figure, *args, **kwargs) -> None:
        axes = figure.axes[0]
        saved_labels.append((axes.get_title(), axes.get_xlabel(), axes.get_ylabel()))
        assert all(float(tick).is_integer() for tick in axes.get_yticks())
        original_save(figure, *args, **kwargs)

    monkeypatch.setattr(Figure, "savefig", save_figure)

    payload = run(
        _dataset(),
        output_dir=tmp_path,
        title="Distribution of Sales",
        x="sales",
        group=group,
    )

    title, x_label, y_label = saved_labels[0]
    assert title.startswith("Distribution of Sales\n")
    assert "Each bar counts observations" in title
    assert x_label == "Sales"
    assert y_label == "Number of observations"
    artifact = Path(payload["artifacts"][0]["storage_ref"])
    assert artifact.read_bytes().startswith(b"\x89PNG")


def test_histogram_rejects_a_y_column_that_could_mislabel_counts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "backend.app.tools.visualization.figure.DEFAULT_ARTIFACTS", tmp_path
    )

    result = execute_step(
        PlanStep(
            step_id="histogram",
            tool_name="histogram",
            arguments={"title": "Sales", "x": "sales", "y": "sales"},
        ),
        _dataset(),
        default_registry(),
    )

    assert result.values["code"] == "INVALID_DATA"
    assert list(tmp_path.glob("*.png")) == []


def test_grouped_histogram_uses_shared_bin_ranges(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bin_ranges: list[list[float]] = []
    original_save = Figure.savefig

    def save_figure(figure: Figure, *args, **kwargs) -> None:
        patches = figure.axes[0].patches
        bin_ranges.extend(
            [
                [patch.get_x() for patch in patches[:10]],
                [patch.get_x() for patch in patches[10:]],
            ]
        )
        original_save(figure, *args, **kwargs)

    monkeypatch.setattr(Figure, "savefig", save_figure)

    run(
        _dataset(),
        output_dir=tmp_path,
        title="Sales by city",
        x="sales",
        group="city",
    )

    assert len(bin_ranges[0]) == len(bin_ranges[1]) == 10
    assert bin_ranges[0] == bin_ranges[1]
