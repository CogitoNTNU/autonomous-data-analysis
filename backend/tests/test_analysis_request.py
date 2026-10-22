"""Reviewed plans can be analyzed without calling another model."""

import json
from pathlib import Path

from backend.app.api.planner_server import PlannerApp, dispatch
from backend.app.services.analysis_request import analyze_plan
from backend.app.storage.datasets import create_dataset_reference
from backend.app.tools.registry import ToolRegistry

DATASET_ID = "55555555-5555-4555-8555-555555555555"
CSV = "age,score\n10,\n20,3\n"


def test_hosted_figures_can_be_read_back() -> None:
    from backend.app.services.analysis_request import READABLE_FIGURES
    from backend.app.tools.visualization.load import HOSTED_ARTIFACTS

    assert HOSTED_ARTIFACTS.resolve() in READABLE_FIGURES


def test_analyze_plan_summarizes_the_remaining_row() -> None:
    dataset, path = _dataset()
    try:
        payload = analyze_plan(dataset, _plan())
    finally:
        _cleanup(path)

    assert payload["status"] == "success"
    results = payload["results"]
    assert results[0]["method"] == "descriptive_statistics"
    assert results[0]["values"]["columns"]["age"]["mean"] == 20
    assert payload["figures"] == []
    assert "storage_ref" not in json.dumps(payload)


def test_analyze_plan_allows_a_plan_with_no_analysis_steps() -> None:
    dataset, path = _dataset()
    try:
        payload = analyze_plan(dataset, {**_plan(), "analysis_steps": []})
    finally:
        _cleanup(path)

    assert payload["results"] == []
    assert payload["warnings"] == []


def test_analyze_plan_rejects_an_invalid_plan() -> None:
    dataset, path = _dataset()
    try:
        try:
            analyze_plan(dataset, {"objective": "Summarize"})
        except ValueError as exc:
            assert str(exc) == "The plan is not valid"
        else:
            raise AssertionError("expected an invalid plan to be rejected")
    finally:
        _cleanup(path)


def test_analysis_route_returns_the_calculated_result() -> None:
    dataset, path = _dataset()
    app = PlannerApp(path.parent, ToolRegistry(), lambda: None)
    app.paths[dataset.dataset_id] = path
    try:
        status, payload = dispatch(
            app,
            "/api/analysis",
            json.dumps({"dataset_id": dataset.dataset_id, "plan": _plan()}).encode(),
            {},
        )
    finally:
        _cleanup(path)

    assert status == 200
    assert payload["results"][0]["step_id"] == "summarize"


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
        "plan_id": "analysis-1",
        "objective": "Summarize the complete rows",
        "required_columns": ["age", "score"],
        "preprocessing_steps": [
            {
                "step_id": "drop_missing",
                "tool_name": "handle_missing_values",
                "arguments": {"columns": ["age", "score"], "strategy": "drop_rows"},
                "depends_on": [],
            }
        ],
        "analysis_steps": [
            {
                "step_id": "summarize",
                "tool_name": "descriptive_statistics",
                "arguments": {"columns": ["age", "score"]},
                "depends_on": [],
            }
        ],
        "expected_outputs": [],
        "assumptions": [],
    }
