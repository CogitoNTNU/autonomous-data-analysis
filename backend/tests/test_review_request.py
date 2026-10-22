"""Interpretation, critic, and chat can review a calculated result."""

import json
from pathlib import Path

from backend.app.api.planner_server import PlannerApp, dispatch
from backend.app.contracts.models import Critique, Interpretation
from backend.app.services.analysis_request import analyze_plan
from backend.app.services.critic_request import critique_interpretation
from backend.app.services.interpretation_request import interpret_results
from backend.app.storage.datasets import create_dataset_reference
from backend.app.tools.registry import ToolRegistry

DATASET_ID = "66666666-6666-4666-8666-666666666666"
CSV = "age,score\n10,\n20,3\n"


def test_interpret_results_explains_the_calculated_values() -> None:
    dataset, path = _dataset()
    try:
        analyzed = analyze_plan(dataset, _plan())
        payload = interpret_results(
            dataset,
            {
                "question": "Summarize the complete rows",
                "plan": _plan(),
                "results": analyzed["results"],
                "artifacts": analyzed["artifacts"],
            },
            _interpretation,
        )
    finally:
        _cleanup(path)

    assert payload["interpretation"]["summary"] == "One complete row remains."
    assert payload["interpretation"]["limitations"]


def test_interpret_results_rejects_unknown_results() -> None:
    dataset, path = _dataset()
    try:
        try:
            interpret_results(
                dataset,
                {"plan": _plan(), "results": [{"step_id": "missing"}]},
                _interpretation,
            )
        except ValueError as exc:
            assert str(exc) == "The analysis results are not valid"
        else:
            raise AssertionError("expected invalid results to be rejected")
    finally:
        _cleanup(path)


def test_critic_approves_a_grounded_interpretation() -> None:
    payload = critique_interpretation(
        {
            "question": "Summarize the complete rows",
            "plan": _plan(),
            "results": [],
            "interpretation": {"summary": "One complete row remains."},
        },
        lambda _prompt, _context: Critique(decision="approved"),
    )

    assert payload["critique"]["decision"] == "approved"


def test_critic_route_returns_the_review() -> None:
    app = PlannerApp(
        Path("/tmp/ada-uploads"),
        ToolRegistry(),
        lambda: None,
        critic_factory=lambda: lambda _prompt, _context: Critique(decision="revise"),
    )
    status, payload = dispatch(
        app,
        "/api/critic",
        json.dumps(
            {
                "plan": _plan(),
                "results": [],
                "interpretation": {"summary": "One complete row remains."},
            }
        ).encode(),
        {},
    )

    assert status == 200
    assert payload["critique"]["decision"] == "revise"


def _interpretation(_prompt: str, _context: object) -> Interpretation:
    return Interpretation(summary="One complete row remains.")


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
        "assumptions": ["The remaining row is enough to describe the file."],
    }
