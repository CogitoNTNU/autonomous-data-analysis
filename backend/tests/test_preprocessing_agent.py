from datetime import datetime, timezone

import pytest

from backend.app.agents.preprocessing import (
    PreprocessingAgent,
    PreprocessingInput,
    run_preprocessing,
)
from backend.app.models.dataset import DatasetMetadata, DatasetReference
from backend.app.models.plan import PlanStep


@pytest.fixture
def dataset() -> DatasetReference:
    return DatasetReference(
        dataset_id="penguins",
        version="raw-v1",
        uri="data/penguins.csv",
        format="csv",
        content_hash="abc123",
        metadata=DatasetMetadata(
            row_count=344,
            column_count=8,
            columns=[],
            missing_value_count=19,
            duplicate_row_count=0,
            created_at=datetime.now(timezone.utc),
        ),
    )


def test_empty_plan_preserves_dataset_and_reports_no_changes(dataset):
    result = PreprocessingAgent().run(dataset)

    assert result.processed_dataset is dataset
    assert result.report.input_dataset_version == "raw-v1"
    assert result.report.output_dataset_version == "raw-v1"
    assert result.report.rows_before == 344
    assert result.report.rows_after == 344
    assert result.report.changes == []
    assert result.report.no_changes is True


def test_preprocessing_tools_create_a_versioned_dataset(dataset, tmp_path):
    source = tmp_path / "input.csv"
    source.write_text(
        "name,score,group\n"
        "a,1,A\n"
        "b,NA,B\n"
        "b,NA,B\n",
        encoding="utf-8",
    )
    input_dataset = dataset.model_copy(
        update={
            "uri": str(source),
            "metadata": dataset.metadata.model_copy(update={"row_count": 3}),
        }
    )
    steps = [
        PlanStep(
            step_id="fill_score",
            tool_name="handle_missing_values",
            arguments={"columns": ["score"], "strategy": "fill", "value": "0"},
        ),
        PlanStep(
            step_id="convert_score",
            tool_name="convert_types",
            arguments={"column": "score", "target_type": "integer"},
        ),
        PlanStep(
            step_id="remove_duplicates",
            tool_name="remove_duplicates",
            arguments={"columns": ["name", "score", "group"]},
        ),
    ]

    result = PreprocessingAgent().run(input_dataset, steps)

    assert result.processed_dataset.parent_version == "raw-v1"
    assert result.processed_dataset.version.startswith("preprocessed-")
    assert result.report.rows_before == 3
    assert result.report.rows_after == 2
    assert result.report.no_changes is False
    assert [change.tool_name for change in result.report.changes] == [
        "handle_missing_values",
        "convert_types",
        "remove_duplicates",
    ]
    assert source.read_text(encoding="utf-8") == (
        "name,score,group\n"
        "a,1,A\n"
        "b,NA,B\n"
        "b,NA,B\n"
    )


def test_unknown_preprocessing_tool_is_rejected(dataset, tmp_path):
    source = tmp_path / "input.csv"
    source.write_text("value\n1\n", encoding="utf-8")
    input_dataset = dataset.model_copy(update={"uri": str(source)})
    step = PlanStep(step_id="unknown", tool_name="not_registered")

    with pytest.raises(ValueError, match="Unknown preprocessing tool"):
        PreprocessingAgent().run(input_dataset, [step])


def test_node_accepts_typed_input_and_returns_typed_output(dataset):
    result = run_preprocessing(PreprocessingInput(dataset=dataset))

    assert result.processed_dataset is dataset
    assert result.report.no_changes is True
