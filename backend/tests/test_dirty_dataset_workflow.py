import csv
from pathlib import Path

from backend.app.agents.preprocessing import run_shared_preprocessing
from backend.app.contracts.models import PlanStep
from backend.app.storage.datasets import create_dataset_reference

DATA = Path(__file__).resolve().parents[1] / "data"


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as csv_file:
        return list(csv.DictReader(csv_file))


def test_cleaning_normalizes_text_before_removing_logical_duplicates() -> None:
    source = DATA / "sample-dirty-data.csv"
    expected = DATA / "sample-dirty-data-clean.csv"
    dataset = create_dataset_reference(source)
    steps = [
        PlanStep(
            step_id="drop_missing",
            tool_name="handle_missing_values",
            arguments={"strategy": "drop_rows"},
        ),
        PlanStep(
            step_id="normalize_names",
            tool_name="normalize_values",
            arguments={"column": "Full Name", "case": "title"},
            depends_on=["drop_missing"],
        ),
        PlanStep(
            step_id="normalize_emails",
            tool_name="normalize_values",
            arguments={"column": "email", "case": "lower"},
            depends_on=["normalize_names"],
        ),
        PlanStep(
            step_id="normalize_countries",
            tool_name="normalize_values",
            arguments={
                "column": "country",
                "case": "title",
                "value_map": {
                    "USA": "United States",
                    "U.S.A.": "United States",
                    "DE": "Germany",
                    "UK": "United Kingdom",
                },
            },
            depends_on=["normalize_emails"],
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
            depends_on=["normalize_countries"],
        ),
        PlanStep(
            step_id="remove_duplicates",
            tool_name="remove_duplicates",
            arguments={
                "subset": ["email", "signup date", "amount", "is_active"]
            },
            depends_on=["convert_types"],
        ),
    ]

    processed, report = run_shared_preprocessing(dataset, steps)
    output = Path(processed.storage_ref)

    try:
        assert _rows(output) == _rows(expected)
        assert report.rows_before == 15
        assert report.rows_after == 9
    finally:
        output.unlink(missing_ok=True)
