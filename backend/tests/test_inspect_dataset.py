from backend.app.tools.inspect_dataset import DEFAULT_DATASET, inspect_dataset


def test_inspect_example_dataset():
    result = inspect_dataset(DEFAULT_DATASET)

    assert result["number_of_columns"] == 8
    assert result["number_of_rows"] == 344
    assert result["missing_values"] == 19
    assert result["duplicate_rows"] == 0
