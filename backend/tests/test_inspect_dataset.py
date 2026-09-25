import pytest

from backend.app.storage.datasets import create_dataset_reference
from backend.app.tools.dataset.inspection import preview_data, get_metadata
from backend.app.tools.inspect_dataset import DEFAULT_DATASET, inspect_dataset



def test_inspect_example_dataset():
    result = inspect_dataset(DEFAULT_DATASET)

    assert result["number_of_columns"] == 8
    assert result["number_of_rows"] == 344
    assert result["missing_values"] == 19
    assert result["duplicate_rows"] == 0

# get_metadata tests
def test_get_metadata_returns_dataset_counts():
    dataset = create_dataset_reference(DEFAULT_DATASET)

    result = get_metadata(dataset)

    assert result["row_count"] == 344
    assert result["column_count"] == 8
    assert result["missing_value_count"] == 19
    assert result["duplicate_row_count"] == 0


def test_get_metadata_returns_all_columns():
    dataset = create_dataset_reference(DEFAULT_DATASET)

    result = get_metadata(dataset)

    assert len(result["columns"]) == 8

    column_names = [
        column["name"]
        for column in result["columns"]
    ]

    assert column_names == [
        "species",
        "island",
        "bill_length_mm",
        "bill_depth_mm",
        "flipper_length_mm",
        "body_mass_g",
        "sex",
        "year",
    ]


def test_get_metadata_returns_column_information():
    dataset = create_dataset_reference(DEFAULT_DATASET)

    result = get_metadata(dataset)

    species = result["columns"][0]

    assert species["name"] == "species"
    assert "data_type" in species
    assert "nullable" in species
    assert "missing_count" in species
    assert "unique_count" in species
    assert "example_values" in species


# preview_data tests
def test_preview_data_returns_requested_rows():
    dataset = create_dataset_reference(DEFAULT_DATASET)

    result = preview_data(
        dataset,
        columns=None,
        limit=3,
    )

    assert result["returned_rows"] == 3
    assert len(result["rows"]) == 3


def test_preview_data_returns_requested_columns():
    dataset = create_dataset_reference(DEFAULT_DATASET)

    result = preview_data(
        dataset,
        columns=["species", "body_mass_g"],
        limit=3,
    )

    assert len(result["rows"]) == 3
    assert list(result["rows"][0].keys()) == ["species", "body_mass_g"]


def test_preview_data_rejects_unknown_columns():
    dataset = create_dataset_reference(DEFAULT_DATASET)

    with pytest.raises(ValueError):
        preview_data(
            dataset,
            columns=["does_not_exist"],
            limit=3,
        )

def test_preview_data_rejects_limit_above_maximum():
    dataset = create_dataset_reference(DEFAULT_DATASET)

    with pytest.raises(ValueError):
        preview_data(
            dataset,
            columns=None,
            limit=21,
        )

def test_preview_data_rejects_limit_below_minimum():
    dataset = create_dataset_reference(DEFAULT_DATASET)

    with pytest.raises(ValueError):
        preview_data(
            dataset,
            columns=None,
            limit=0,
        )