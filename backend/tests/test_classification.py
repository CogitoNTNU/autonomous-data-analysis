from pathlib import Path

import pandas as pd
import pytest
from pydantic import ValidationError

from backend.app.contracts.models import DatasetReference, PlanStep
from backend.app.tools.analysis.descriptive import default_registry
from backend.app.tools.ml.classification import (
    TrainClassificationInput,
    load_training_data,
    resolve_feature_columns,
    split_training_data,
)
from backend.app.tools.registry import Tool, execute_step, validate_call

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_resolve_feature_columns_defaults_to_all_except_target() -> None:
    request = TrainClassificationInput(target_column="species")

    result = resolve_feature_columns(
        request,
        ["bill_length_mm", "body_mass_g", "species"],
    )

    assert result == ["bill_length_mm", "body_mass_g"]


def test_resolve_feature_columns_uses_requested_columns() -> None:
    request = TrainClassificationInput(
        target_column="species",
        feature_columns=["body_mass_g"],
    )

    result = resolve_feature_columns(
        request,
        ["bill_length_mm", "body_mass_g", "species"],
    )

    assert result == ["body_mass_g"]


def test_resolve_feature_columns_rejects_unknown_target() -> None:
    request = TrainClassificationInput(target_column="unknown")

    with pytest.raises(ValueError, match="Unknown target column"):
        resolve_feature_columns(request, ["body_mass_g", "species"])


def test_resolve_feature_columns_reject_unknown_feature() -> None:
    request = TrainClassificationInput(
        target_column="species",
        feature_columns=["unknown"],
    )

    with pytest.raises(ValueError, match="Unknown feature columns"):
        resolve_feature_columns(request, ["body_mass_g", "species"])


@pytest.mark.parametrize(
    "feature_columns",
    [
        [],
        ["body_mass_g", "body_mass_g"],
        ["species"],
    ],
)
def test_input_rejects_invalid_feature_lists(
    feature_columns: list[str],
) -> None:
    with pytest.raises(ValidationError):
        TrainClassificationInput(
            target_column="species",
            feature_columns=feature_columns,
        )


def test_resolve_feature_columns_rejects_dataset_with_only_target() -> None:
    request = TrainClassificationInput(target_column="species")

    with pytest.raises(ValueError, match="At least one feature column"):
        resolve_feature_columns(request, ["species"])


def _classification_tool() -> Tool:
    return Tool(
        name="train_classification",
        description="Train a classification model.",
        input_model=TrainClassificationInput,
        accepted_dtypes=frozenset(),
        run=lambda dataset, **arguments: {},
    )


def _classification_dataset() -> DatasetReference:
    return DatasetReference(
        dataset_id="penguins",
        version="v1",
        storage_ref="unused.csv",
        schema={
            "species": {"datatype": "string"},
            "body_mass_g": {"datatype": "float"},
        },
    )


def test_registry_rejects_unknown_classification_target() -> None:
    step = PlanStep(
        step_id="classify",
        tool_name="train_classification",
        arguments={"target_column": "unknown"},
    )

    problem = validate_call(
        step,
        _classification_dataset(),
        _classification_tool(),
    )

    assert problem is not None
    assert problem[0] == "MISSING_COLUMN"


def test_registry_rejects_unknown_classification_feature() -> None:
    step = PlanStep(
        step_id="classify",
        tool_name="train_classification",
        arguments={
            "target_column": "species",
            "feature_columns": ["unknown"],
        },
    )

    problem = validate_call(
        step,
        _classification_dataset(),
        _classification_tool(),
    )

    assert problem is not None
    assert problem[0] == "MISSING_COLUMN"


def _fixture_dataset(filename: str) -> DatasetReference:
    return DatasetReference(
        dataset_id="classification-test",
        version="v1",
        storage_ref=str(FIXTURES / filename),
        schema={
            "age": {"datatype": "integer"},
            "score": {"datatype": "float"},
        },
    )


def test_load_training_data_returns_features_and_target() -> None:
    features, target = load_training_data(
        _fixture_dataset("clean.csv"),
        TrainClassificationInput(target_column="score"),
    )

    assert list(features.columns) == ["age"]
    assert features["age"].tolist() == [10, 20, 30]
    assert target.tolist() == [1.5, 2.5, 3.5]


def test_load_training_data_rejects_missing_target_values() -> None:
    with pytest.raises(ValueError, match="Target column contains missing values"):
        load_training_data(
            _fixture_dataset("missing.csv"),
            TrainClassificationInput(target_column="score"),
        )


def test_load_training_data_rejects_empty_dataset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "backend.app.tools.ml.classification.pd.read_csv",
        lambda _path: pd.DataFrame(),
    )

    with pytest.raises(ValueError, match="Dataset contains no rows"):
        load_training_data(
            _fixture_dataset("clean.csv"),
            TrainClassificationInput(target_column="score"),
        )


def test_split_training_data_is_reproducible_and_stratified() -> None:
    features = pd.DataFrame({"measurement": range(24)})
    target = pd.Series(["Adelie"] * 12 + ["Chinstrap"] * 12, name="species")
    request = TrainClassificationInput(
        target_column="species",
        test_size=0.25,
        random_state=17,
    )

    first_split = split_training_data(features, target, request)
    second_split = split_training_data(features, target, request)

    pd.testing.assert_frame_equal(first_split[0], second_split[0])
    pd.testing.assert_frame_equal(first_split[1], second_split[1])
    pd.testing.assert_series_equal(first_split[2], second_split[2])
    pd.testing.assert_series_equal(first_split[3], second_split[3])
    assert first_split[2].value_counts().to_dict() == {
        "Adelie": 9,
        "Chinstrap": 9,
    }
    assert first_split[3].value_counts().to_dict() == {
        "Adelie": 3,
        "Chinstrap": 3,
    }


def test_split_training_data_rejects_single_class() -> None:
    features = pd.DataFrame({"measurement": range(4)})
    target = pd.Series(["Adelie"] * 4, name="species")
    request = TrainClassificationInput(target_column="species")

    with pytest.raises(ValueError, match="at least two classes"):
        split_training_data(features, target, request)


def test_split_training_data_rejects_class_with_single_sample() -> None:
    features = pd.DataFrame({"measurement": range(6)})
    target = pd.Series(["Adelie"] * 5 + ["Chinstrap"], name="species")
    request = TrainClassificationInput(target_column="species")

    with pytest.raises(ValueError, match="at least two samples"):
        split_training_data(features, target, request)


def test_train_classification_handles_mixed_features(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = pd.DataFrame(
        {
            "measurement": [
                *range(20),
                *range(100, 120),
            ],
            "island": ["Torgersen"] * 20 + ["Biscoe"] * 20,
            "species": ["Adelie"] * 20 + ["Chinstrap"] * 20,
        }
    )
    rows.loc[[0, 11], "measurement"] = None
    rows.loc[[1, 21], "island"] = None
    csv_path = tmp_path / "classification.csv"
    rows.to_csv(csv_path, index=False)
    monkeypatch.setattr(
        "backend.app.tools.ml.classification.resolve_csv",
        lambda _storage_ref: csv_path,
    )
    dataset = DatasetReference(
        dataset_id="classification-test",
        version="v1",
        storage_ref="classification.csv",
        schema={
            "measurement": {"datatype": "float"},
            "island": {"datatype": "string"},
            "species": {"datatype": "string"},
        },
    )
    step = PlanStep(
        step_id="train",
        tool_name="train_classification",
        arguments={
            "target_column": "species",
            "test_size": 0.25,
            "random_state": 7,
        },
    )

    result = execute_step(step, dataset, default_registry())

    assert result.values["status"] == "ok"
    assert result.values["model"] == "logistic_regression"
    assert result.values["metrics"]["accuracy"] >= 0.9
    assert result.values["train_size"] == 30
    assert result.values["test_size"] == 10
    assert result.sample_size == 40
