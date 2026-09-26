from datetime import datetime, timezone
import csv
import json
import os
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.app.agents.preprocessing import (
    IdunPreprocessingPlanner,
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


def _run_step(dataset, tmp_path, csv_text, tool_name, arguments):
    source = tmp_path / "input.csv"
    source.write_text(csv_text, encoding="utf-8")
    with source.open(encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        headers = reader.fieldnames or []
        row_count = sum(1 for _ in reader)
    input_dataset = dataset.model_copy(
        update={
            "uri": str(source),
            "metadata": dataset.metadata.model_copy(
                update={"row_count": row_count, "column_count": len(headers)}
            ),
        }
    )
    result = PreprocessingAgent().run(
        input_dataset,
        [PlanStep(step_id="step", tool_name=tool_name, arguments=arguments)],
    )
    with Path(result.processed_dataset.uri).open(encoding="utf-8", newline="") as csv_file:
        output_reader = csv.DictReader(csv_file)
        output_headers = output_reader.fieldnames or []
        output_rows = list(output_reader)
    return result, source, output_headers, output_rows


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


def test_idun_plan_is_validated_and_can_be_run_locally(dataset, tmp_path):
    source = tmp_path / "input.csv"
    source.write_text("score,private_value\nNA,do-not-send\n2,also-private\n", encoding="utf-8")
    input_dataset = dataset.model_copy(
        update={
            "uri": str(source),
            "metadata": dataset.metadata.model_copy(
                update={"row_count": 2, "column_count": 2, "missing_value_count": 1}
            ),
        }
    )
    arguments = json.dumps(
        {
            "steps": [
                {
                    "step_id": "drop_missing_score",
                    "tool_name": "handle_missing_values",
                    "arguments": {"columns": ["score"], "strategy": "drop_rows"},
                }
            ]
        }
    )
    calls = []

    def create_completion(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        tool_calls=[
                            SimpleNamespace(
                                function=SimpleNamespace(
                                    name="submit_preprocessing_plan",
                                    arguments=arguments,
                                )
                            )
                        ]
                    )
                )
            ]
        )

    client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=create_completion),
        )
    )
    agent = PreprocessingAgent(planner=IdunPreprocessingPlanner(client=client))

    steps = agent.plan(input_dataset, "Drop rows with a missing score.")
    result = agent.run(input_dataset, steps)

    assert len(steps) == 1
    assert steps[0].tool_name == "handle_missing_values"
    assert result.report.rows_after == 1
    assert source.read_text(encoding="utf-8").endswith("2,also-private\n")
    request_context = calls[0]["messages"][1]["content"]
    assert "do-not-send" not in request_context
    assert "also-private" not in request_context
    assert "private_value" in request_context


@pytest.mark.parametrize(
    ("csv_text", "tool_name", "arguments", "expected_headers", "expected_rows"),
    [
        (
            "score,group\n1,A\nNA,A\n3,B\n",
            "handle_missing_values",
            {"columns": ["score"], "strategy": "mean"},
            ["score", "group"],
            [{"score": "1", "group": "A"}, {"score": "2", "group": "A"}, {"score": "3", "group": "B"}],
        ),
        (
            "score,group\n1,A\nNA,A\n3,B\n",
            "handle_missing_values",
            {"columns": ["score"], "strategy": "drop"},
            ["score", "group"],
            [{"score": "1", "group": "A"}, {"score": "3", "group": "B"}],
        ),
        (
            "id,label\n1,old\n1,new\n2,last\n",
            "remove_duplicates",
            {"subset": ["id"], "keep": "last"},
            ["id", "label"],
            [{"id": "1", "label": "new"}, {"id": "2", "label": "last"}],
        ),
        (
            "value,count\n1.5,1\nbad,2\n",
            "change_datatypes",
            {
                "conversions": {"value": "float", "count": "integer"},
                "invalid_value_strategy": "null",
            },
            ["value", "count"],
            [{"value": "1.5", "count": "1"}, {"value": "", "count": "2"}],
        ),
        (
            "color\nred\nblue\nNA\n",
            "encode_categorical",
            {"columns": ["color"], "strategy": "one_hot"},
            ["color", "color__blue", "color__red"],
            [
                {"color": "red", "color__blue": "0", "color__red": "1"},
                {"color": "blue", "color__blue": "1", "color__red": "0"},
                {"color": "NA", "color__blue": "0", "color__red": "0"},
            ],
        ),
        (
            "score\n1\n2\n3\n",
            "scale_features",
            {"columns": ["score"], "method": "min_max"},
            ["score"],
            [{"score": "0"}, {"score": "0.5"}, {"score": "1"}],
        ),
        (
            "score,label\n1,a\n2,b\n3,c\n",
            "filter_rows",
            {"conditions": [{"column": "score", "operator": "gte", "value": 2}]},
            ["score", "label"],
            [{"score": "2", "label": "b"}, {"score": "3", "label": "c"}],
        ),
        (
            "score,label\n1,a\n2,b\n",
            "select_columns",
            {"columns": ["label"]},
            ["label"],
            [{"label": "a"}, {"label": "b"}],
        ),
        (
            "score\n1\n2\n2\n2\n3\n100\n",
            "handle_outliers",
            {"columns": ["score"], "method": "iqr", "strategy": "clip"},
            ["score"],
            [
                {"score": "1"},
                {"score": "2"},
                {"score": "2"},
                {"score": "2"},
                {"score": "3"},
                {"score": "3.875"},
            ],
        ),
    ],
)
def test_registered_preprocessing_tools_transform_csv(
    dataset, tmp_path, csv_text, tool_name, arguments, expected_headers, expected_rows
):
    result, source, output_headers, output_rows = _run_step(
        dataset, tmp_path, csv_text, tool_name, arguments
    )

    assert output_headers == expected_headers
    assert output_rows == expected_rows
    assert result.report.changes[0].tool_name == tool_name
    assert source.read_text(encoding="utf-8") == csv_text


def test_normalize_values_and_locale_aware_conversions(dataset, tmp_path):
    source = tmp_path / "input.csv"
    source.write_text(
        "Full Name,email,country,signup date,amount,is_active\n"
        '  JOHN   SMITH ,JOHN.SMITH@EXAMPLE.COM ,U.S.A.,05/01/2026,"$1,200.00",Yes\n'
        'jane doe,jane@example.com,Spain,"Jan 5, 2026",€750.5,1\n',
        encoding="utf-8",
    )
    input_dataset = dataset.model_copy(
        update={
            "uri": str(source),
            "metadata": dataset.metadata.model_copy(
                update={"row_count": 2, "column_count": 6}
            ),
        }
    )
    steps = [
        PlanStep(
            step_id="normalize_name",
            tool_name="normalize_values",
            arguments={"column": "Full Name", "case": "title"},
        ),
        PlanStep(
            step_id="normalize_email",
            tool_name="normalize_values",
            arguments={"column": "email", "case": "lower"},
        ),
        PlanStep(
            step_id="normalize_country",
            tool_name="normalize_values",
            arguments={
                "column": "country",
                "value_map": {"USA": "United States", "U.S.A.": "United States"},
            },
        ),
        PlanStep(
            step_id="convert_types",
            tool_name="change_datatypes",
            arguments={
                "conversions": {
                    "signup date": "date",
                    "amount": "currency",
                    "is_active": "boolean",
                }
            },
        ),
    ]

    result = PreprocessingAgent().run(input_dataset, steps)

    with Path(result.processed_dataset.uri).open(encoding="utf-8", newline="") as csv_file:
        rows = list(csv.DictReader(csv_file))
    assert rows == [
        {
            "Full Name": "John Smith",
            "email": "john.smith@example.com",
            "country": "United States",
            "signup date": "2026-01-05",
            "amount": "1200",
            "is_active": "true",
        },
        {
            "Full Name": "Jane Doe",
            "email": "jane@example.com",
            "country": "Spain",
            "signup date": "2026-01-05",
            "amount": "750.5",
            "is_active": "true",
        },
    ]
    column_types = {
        column.name: column.data_type
        for column in result.processed_dataset.metadata.columns
    }
    assert column_types["signup date"] == "date"
    assert column_types["amount"] == "float"
    assert column_types["is_active"] == "boolean"
    assert source.read_text(encoding="utf-8").startswith("Full Name,email,country")


def test_preprocessing_steps_run_after_their_dependencies(dataset, tmp_path):
    source = tmp_path / "input.csv"
    source.write_text("score,label\n1,a\n2,b\n3,c\n", encoding="utf-8")
    input_dataset = dataset.model_copy(update={"uri": str(source)})
    steps = [
        PlanStep(
            step_id="select_label",
            tool_name="select_columns",
            arguments={"columns": ["label"]},
            depends_on=["filter_high_scores"],
        ),
        PlanStep(
            step_id="filter_high_scores",
            tool_name="filter_rows",
            arguments={
                "conditions": [{"column": "score", "operator": "gte", "value": 2}]
            },
        ),
    ]

    result = PreprocessingAgent().run(input_dataset, steps)

    with Path(result.processed_dataset.uri).open(encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        assert reader.fieldnames == ["label"]
        assert list(reader) == [{"label": "b"}, {"label": "c"}]
    assert [change.step_id for change in result.report.changes] == [
        "filter_high_scores",
        "select_label",
    ]


@pytest.mark.parametrize(
    ("steps", "message"),
    [
        (
            [PlanStep(step_id="same", tool_name="select_columns", arguments={"columns": ["x"]})]
            * 2,
            "must be unique",
        ),
        (
            [
                PlanStep(
                    step_id="one",
                    tool_name="select_columns",
                    arguments={"columns": ["x"]},
                    depends_on=["missing"],
                )
            ],
            "unknown dependencies",
        ),
        (
            [
                PlanStep(step_id="one", tool_name="select_columns", arguments={"columns": ["x"]}, depends_on=["two"]),
                PlanStep(step_id="two", tool_name="select_columns", arguments={"columns": ["x"]}, depends_on=["one"]),
            ],
            "dependency cycle",
        ),
    ],
)
def test_invalid_preprocessing_dependencies_are_rejected(dataset, steps, message):
    with pytest.raises(ValueError, match=message):
        PreprocessingAgent().run(dataset, steps)


def test_tool_argument_schemas_reject_unsupported_values(dataset, tmp_path):
    source = tmp_path / "input.csv"
    source.write_text("value\n1\n", encoding="utf-8")
    input_dataset = dataset.model_copy(update={"uri": str(source)})

    with pytest.raises(ValueError, match="Invalid arguments"):
        PreprocessingAgent().run(
            input_dataset,
            [
                PlanStep(
                    step_id="invalid_filter",
                    tool_name="filter_rows",
                    arguments={
                        "conditions": [{"column": "value", "operator": "exec", "value": "x"}]
                    },
                )
            ],
        )


@pytest.mark.skipif(
    os.getenv("RUN_IDUN_INTEGRATION") != "1",
    reason="Set RUN_IDUN_INTEGRATION=1 to call the live Idun API",
)
def test_idun_live_plan_and_preprocessing_run(dataset, tmp_path):
    original = Path(__file__).resolve().parents[1] / "data" / "penguins.csv"
    source = tmp_path / "penguins.csv"
    shutil.copyfile(original, source)
    original_bytes = source.read_bytes()
    input_dataset = dataset.model_copy(update={"uri": str(source)})
    agent = PreprocessingAgent()

    steps = agent.plan(
        input_dataset,
        "Drop rows missing bill_length_mm or sex. Use only the "
        "handle_missing_values tool with strategy drop_rows.",
    )
    print("Proposed preprocessing steps:")
    print(json.dumps([step.model_dump() for step in steps], indent=2))
    assert steps
    assert all(step.tool_name == "handle_missing_values" for step in steps)
    assert all(step.arguments.get("strategy") == "drop_rows" for step in steps)
    planned_columns = {
        column
        for step in steps
        for column in step.arguments.get("columns", [])
    }
    assert {"bill_length_mm", "sex"}.issubset(planned_columns)

    result = agent.run(input_dataset, steps)
    print("Preprocessing agent output:")
    print(result.model_dump_json(indent=2))

    assert result.report.rows_after < result.report.rows_before
    assert result.processed_dataset.parent_version == input_dataset.version
    assert source.read_bytes() == original_bytes
