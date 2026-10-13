import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    precision_recall_fscore_support,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from backend.app.contracts.models import DatasetReference, WarningEvent
from backend.app.tools.analysis.files import resolve_csv
from backend.app.tools.registry import Tool

SOURCE = "train_classification"


class TrainClassificationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_column: str = Field(min_length=1)
    feature_columns: list[str] | None = None
    test_size: float = Field(default=0.2, gt=0, lt=1)
    random_state: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_features(self) -> "TrainClassificationInput":
        if self.feature_columns is not None:
            if not self.feature_columns:
                raise ValueError("feature_columns must not be empty")
            if len(self.feature_columns) != len(set(self.feature_columns)):
                raise ValueError("feature_columns must be unique")
            if self.target_column in self.feature_columns:
                raise ValueError("target_column cannot also be a feature")
        return self


def resolve_feature_columns(
    request: TrainClassificationInput,
    available_columns: list[str],
) -> list[str]:
    if request.target_column not in available_columns:
        raise ValueError(f"Unknown target column: {request.target_column}")

    if request.feature_columns is None:
        feature_columns = [
            column for column in available_columns if column != request.target_column
        ]
    else:
        feature_columns = request.feature_columns

    missing_columns = [
        column for column in feature_columns if column not in available_columns
    ]
    if missing_columns:
        raise ValueError(f"Unknown feature columns: {', '.join(missing_columns)}")

    if not feature_columns:
        raise ValueError("At least one feature column is required")

    return feature_columns


def load_training_data(
    dataset: DatasetReference,
    request: TrainClassificationInput,
) -> tuple[pd.DataFrame, pd.Series]:
    """Load feature columns and target values from a registered CSV dataset."""
    frame = pd.read_csv(resolve_csv(dataset.storage_ref))
    if frame.empty:
        raise ValueError("Dataset contains no rows")

    feature_columns = resolve_feature_columns(request, list(frame.columns))
    if frame[request.target_column].isna().any():
        raise ValueError(
            f"Target column contains missing values: {request.target_column}"
        )

    return frame.loc[:, feature_columns], frame[request.target_column]


def split_training_data(
    features: pd.DataFrame,
    target: pd.Series,
    request: TrainClassificationInput,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Create a reproducible stratified train/test split."""
    if len(features) != len(target):
        raise ValueError("Features and target must have the same number of rows")
    if target.isna().any():
        raise ValueError("Target contains missing values")

    class_counts = target.value_counts()
    if len(class_counts) < 2:
        raise ValueError("Classification requires at least two classes")
    if class_counts.min() < 2:
        raise ValueError("Each class must have at least two samples")

    try:
        return train_test_split(
            features,
            target,
            test_size=request.test_size,
            random_state=request.random_state,
            stratify=target,
        )
    except ValueError as error:
        raise ValueError(f"Unable to create stratified split: {error}") from error


def _classifier_pipeline(features: pd.DataFrame, random_state: int) -> Pipeline:
    numeric_columns = features.select_dtypes(include=["number"]).columns.tolist()
    categorical_columns = features.select_dtypes(
        include=["object", "category", "bool", "string"]
    ).columns.tolist()
    supported_columns = set(numeric_columns) | set(categorical_columns)
    unsupported_columns = [
        column for column in features.columns if column not in supported_columns
    ]
    if unsupported_columns:
        raise ValueError(
            "Unsupported feature data types: " + ", ".join(unsupported_columns)
        )

    transformers: list[tuple[str, Pipeline, list[str]]] = []
    if numeric_columns:
        transformers.append(
            (
                "numeric",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                numeric_columns,
            )
        )
    if categorical_columns:
        transformers.append(
            (
                "categorical",
                Pipeline(
                    steps=[
                        (
                            "imputer",
                            SimpleImputer(
                                strategy="most_frequent",
                                keep_empty_features=True,
                            ),
                        ),
                        ("encoder", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical_columns,
            )
        )

    preprocessing = ColumnTransformer(transformers=transformers)
    return Pipeline(
        steps=[
            ("preprocessing", preprocessing),
            (
                "classifier",
                LogisticRegression(max_iter=1_000, random_state=random_state),
            ),
        ]
    )


def run(dataset: DatasetReference, **arguments: object) -> dict[str, object]:
    """Train and evaluate a logistic-regression classification baseline."""
    request = TrainClassificationInput.model_validate(arguments)
    features, target = load_training_data(dataset, request)
    training_features, test_features, training_target, test_target = (
        split_training_data(features, target, request)
    )

    pipeline = _classifier_pipeline(features, request.random_state)
    pipeline.fit(training_features, training_target)
    predictions = pipeline.predict(test_features)
    classes = pipeline.named_steps["classifier"].classes_
    precision, recall, f1, _ = precision_recall_fscore_support(
        test_target,
        predictions,
        labels=classes,
        average="macro",
        zero_division=0,
    )

    warnings: list[WarningEvent] = []
    if len(target) < 30:
        warnings.append(
            WarningEvent(
                code="LOW_SAMPLE_SIZE",
                message=f"Classification used only {len(target)} rows",
                source=SOURCE,
            )
        )

    return {
        "model": "logistic_regression",
        "target_column": request.target_column,
        "feature_columns": list(features.columns),
        "class_labels": [str(label) for label in classes],
        "metrics": {
            "accuracy": float(accuracy_score(test_target, predictions)),
            "precision_macro": float(precision),
            "recall_macro": float(recall),
            "f1_macro": float(f1),
        },
        "confusion_matrix": confusion_matrix(
            test_target,
            predictions,
            labels=classes,
        ).tolist(),
        "train_size": len(training_target),
        "test_size": len(test_target),
        "sample_size": len(target),
        "warnings": warnings,
    }


TOOL = Tool(
    name=SOURCE,
    description=(
        "Train a logistic-regression classifier and report stratified test metrics. "
        "Required: target_column. Optional: feature_columns, test_size, random_state."
    ),
    input_model=TrainClassificationInput,
    accepted_dtypes=frozenset(),
    run=run,
)
