import pytest
from pydantic import ValidationError

from backend.app.contracts.models import DatasetReference
from backend.app.tools.analysis.correlation import CorrelationInput, run


@pytest.fixture
def penguins_dataset() -> DatasetReference:
    return DatasetReference(
        dataset_id="penguins",
        version="1",
        storage_ref="penguins.csv",
        schema={
            "bill_length_mm": {"datatype": "float"},
            "bill_depth_mm": {"datatype": "float"},
            "flipper_length_mm": {"datatype": "integer"},
            "body_mass_g": {"datatype": "integer"},
        },
    )


def test_correlation_returns_matrix(penguins_dataset: DatasetReference) -> None:
    result = run(
        penguins_dataset,
        columns=["flipper_length_mm", "body_mass_g"],
    )

    assert result["method"] == "pearson"
    assert result["sample_size"] > 0

    correlations = result["correlations"]

    assert correlations["flipper_length_mm"]["flipper_length_mm"] == pytest.approx(1.0)
    assert correlations["body_mass_g"]["body_mass_g"] == pytest.approx(1.0)

    assert correlations["flipper_length_mm"]["body_mass_g"] == pytest.approx(
        correlations["body_mass_g"]["flipper_length_mm"]
    )


def test_correlation_supports_spearman(
    penguins_dataset: DatasetReference,
) -> None:
    result = run(
        penguins_dataset,
        columns=["bill_length_mm", "body_mass_g"],
        method="spearman",
    )

    assert result["method"] == "spearman"
    assert result["correlations"]["bill_length_mm"]["body_mass_g"] is not None


def test_correlation_requires_two_columns() -> None:
    with pytest.raises(ValidationError):
        CorrelationInput(columns=["body_mass_g"])
