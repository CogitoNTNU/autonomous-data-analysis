from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from backend.app.agents.preprocessing.workflow import run_shared_preprocessing
from backend.app.contracts.models import PlanStep
from backend.app.storage.datasets import HOSTED_UPLOADS, create_dataset_reference
from backend.app.tools.dataset.inspection import get_metadata
from backend.app.tools.analysis.categorical import run as categorical


def test_bom_csv_keeps_column_names_through_preprocessing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("backend.app.storage.datasets.ALLOWED", (tmp_path,))
    path = tmp_path / "bom.csv"
    original = b"\xef\xbb\xbfage,score\r\n10,2\r\n20,3\r\n"
    path.write_bytes(original)
    source = create_dataset_reference(path)

    processed, report = run_shared_preprocessing(
        source,
        [
            PlanStep(
                step_id="select",
                tool_name="select_columns",
                arguments={"columns": ["age"]},
            ),
        ],
    )

    assert set(processed.dataset_schema) == {"age"}
    assert report.rows_after == 2
    assert processed.version != source.version
    assert path.read_bytes() == original


def test_planner_can_inspect_registered_hosted_upload() -> None:
    HOSTED_UPLOADS.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=HOSTED_UPLOADS) as directory:
        path = Path(directory) / "data.csv"
        path.write_text("age\n10\n20\n", encoding="utf-8")
        dataset = create_dataset_reference(path)

        result = get_metadata(dataset)

    assert result["row_count"] == 2
    assert result["columns"][0]["name"] == "age"


@pytest.mark.parametrize(
    "content",
    [
        " \n\nage,score\n \n10,2\n\n20,3\n",
        "\ufeffage,score\r\n10,2\r\n\r\n20,3\r\n",
    ],
)
def test_blank_lines_do_not_change_preprocessing_row_counts(
    tmp_path, monkeypatch, content
):
    monkeypatch.setattr("backend.app.storage.datasets.ALLOWED", (tmp_path,))
    path = tmp_path / "blank.csv"
    path.write_text(content, encoding="utf-8")
    source = create_dataset_reference(path)

    processed, report = run_shared_preprocessing(source, [])

    assert report.rows_before == report.rows_after == 2
    assert processed.dataset_schema == source.dataset_schema


def test_noop_preprocessing_preserves_all_missing_numeric_schema(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.app.storage.datasets.ALLOWED", (tmp_path,))
    path = tmp_path / "empty-column.csv"
    path.write_text("age,score\n,2\n,3\n")
    source = create_dataset_reference(path)

    processed, report = run_shared_preprocessing(source, [])

    assert source.dataset_schema["age"]["datatype"] == "float"
    assert processed.dataset_schema == source.dataset_schema


def test_declared_string_conversion_survives_csv_type_inference(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.app.storage.datasets.ALLOWED", (tmp_path,))
    monkeypatch.setattr(
        "backend.app.tools.analysis.files.ALLOWED_DATA_DIRECTORIES", (tmp_path,)
    )
    path = tmp_path / "codes.csv"
    path.write_text("code\n10\n20\n")
    source = create_dataset_reference(path)

    processed, report = run_shared_preprocessing(
        source,
        [
            PlanStep(
                step_id="cast",
                tool_name="change_datatypes",
                arguments={"conversions": {"code": "string"}},
            )
        ],
    )

    assert processed.dataset_schema["code"]["datatype"] == "string"
    payload = categorical(processed, column="code", normalize=False)
    assert payload["categories"] == [
        {"value": "10", "count": 1},
        {"value": "20", "count": 1},
    ]
