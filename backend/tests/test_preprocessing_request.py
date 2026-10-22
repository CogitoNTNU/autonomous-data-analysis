"""The reviewed plan can be preprocessed without calling the planner model."""

import json
from pathlib import Path

from backend.app.api.planner_server import PlannerApp, dispatch
from backend.app.services.preprocessing_request import preprocess_plan
from backend.app.storage.datasets import create_dataset_reference
from backend.app.tools.registry import ToolRegistry

DATASET_ID = "44444444-4444-4444-8444-444444444444"
CSV = "age,score\n10,\n20,3\n"


def test_preprocess_plan_drops_incomplete_rows() -> None:
    dataset, path = _dataset()
    try:
        payload = preprocess_plan(dataset, _plan())
    finally:
        _cleanup(path)

    assert payload["status"] == "success"
    report = payload["report"]
    assert report["rows_before"] == 2
    assert report["rows_after"] == 1
    assert report["changes"][0].startswith("drop_missing (handle_missing_values)")


def test_preprocess_plan_leaves_a_complete_file_unchanged() -> None:
    dataset, path = _dataset()
    try:
        payload = preprocess_plan(dataset, {**_plan(), "preprocessing_steps": []})
    finally:
        _cleanup(path)

    report = payload["report"]
    assert report["rows_before"] == report["rows_after"] == 2
    assert report["changes"] == []


def test_preprocess_plan_rejects_an_invalid_plan() -> None:
    dataset, path = _dataset()
    try:
        try:
            preprocess_plan(dataset, {"objective": "Drop rows"})
        except ValueError as exc:
            assert str(exc) == "The plan is not valid"
        else:
            raise AssertionError("expected an invalid plan to be rejected")
    finally:
        _cleanup(path)


def test_preprocessing_route_accepts_the_stored_plan() -> None:
    dataset, path = _dataset()
    app = PlannerApp(path.parent, ToolRegistry(), lambda: None)
    app.paths[dataset.dataset_id] = path
    try:
        status, payload = dispatch(
            app,
            "/api/preprocessing",
            json.dumps({"dataset_id": dataset.dataset_id, "plan": _plan()}).encode(),
            {},
        )
    finally:
        _cleanup(path)

    assert status == 200
    assert payload["status"] == "success"
    assert payload["report"]["rows_after"] == 1


def _dataset():
    directory = Path("/tmp/ada-uploads")
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{DATASET_ID}.csv"
    path.write_text(CSV, encoding="utf-8")
    return create_dataset_reference(path), path


def _cleanup(path: Path) -> None:
    for child in path.parent.glob(f"{path.stem}*"):
        child.unlink(missing_ok=True)


def _plan() -> dict[str, object]:
    return {
        "plan_id": "prep-1",
        "objective": "Keep complete rows",
        "required_columns": ["age", "score"],
        "preprocessing_steps": [
            {
                "step_id": "drop_missing",
                "tool_name": "handle_missing_values",
                "arguments": {"columns": ["age", "score"], "strategy": "drop_rows"},
                "depends_on": [],
            }
        ],
        "analysis_steps": [],
        "expected_outputs": [],
        "assumptions": [],
    }
