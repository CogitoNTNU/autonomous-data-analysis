"""Small datasets and capture of the figures actually exported by chart tools."""

from pathlib import Path

import pytest
from matplotlib.figure import Figure

from backend.app.contracts.models import DatasetReference

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures"


@pytest.fixture
def dataset() -> DatasetReference:
    return DatasetReference(
        dataset_id="charts",
        version="v1",
        storage_ref=str(FIXTURES / "charts.csv"),
        schema={
            "city": {"datatype": "string"},
            "sales": {"datatype": "integer"},
            "month": {"datatype": "integer"},
        },
    )


@pytest.fixture
def saved_figures(monkeypatch: pytest.MonkeyPatch) -> list[Figure]:
    figures: list[Figure] = []
    save = Figure.savefig

    def capture(figure: Figure, *args, **kwargs) -> None:
        figures.append(figure)
        save(figure, *args, **kwargs)

    monkeypatch.setattr(Figure, "savefig", capture)
    return figures
