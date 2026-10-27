"""CSV launcher tests never contact the provider."""

from pathlib import Path
from unittest.mock import Mock

from backend.app.agents.planner.schema import PlannerOutput
from backend.app.contracts.models import (
    Critique,
    Finding,
    Interpretation,
    Plan,
    PlanStep,
)
from backend.scripts import run_workflow


def test_csv_runs_through_real_graph_with_fake_models(monkeypatch, capsys):
    path = Path(__file__).resolve().parents[2] / "fixtures" / "clean.csv"
    plan = Plan(
        plan_id="p",
        objective="Describe age",
        analysis_steps=[
            PlanStep(
                step_id="s",
                tool_name="descriptive_statistics",
                arguments={"columns": ["age"]},
            )
        ],
    )
    client = Mock()
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=False)
    planner = Mock(return_value=PlannerOutput(plan=plan))
    planner.client = client
    monkeypatch.setattr(run_workflow, "PlannerLLM", Mock(return_value=planner))

    def interpret(prompt, context):
        result = context.evidence.results[0]
        assert result.values["columns"]["age"]["mean"] == 20.0
        return Interpretation(
            summary="Age summary",
            findings=[Finding(claim="Mean age is 20.", result_ids=[result.result_id])],
        )

    monkeypatch.setattr(run_workflow, "InterpretationLLM", Mock(return_value=interpret))
    critic = Mock(return_value=Critique(decision="approved"))
    critic.client = client
    monkeypatch.setattr(run_workflow, "CriticLLM", Mock(return_value=critic))
    monkeypatch.setenv("NTNU_LLM_API_KEY", "test-only")
    assert run_workflow.main(["--dataset", str(path), "--prompt", "Describe age"]) == 0
    output = capsys.readouterr().out
    assert "approved by Critic" in output
    assert [
        line for line in output.splitlines() if line.startswith("Completed node:")
    ] == [
        "Completed node: start_run",
        "Completed node: planner",
        "Completed node: preprocessing",
        "Completed node: analysis",
        "Completed node: interpretation",
        "Completed node: critic",
        "Completed node: finish_run",
    ]
    assert client.__exit__.call_count == 2
    critic.assert_called_once()


def test_missing_csv_does_not_create_provider(monkeypatch, capsys):
    provider = Mock()
    monkeypatch.setattr(run_workflow, "PlannerLLM", provider)
    assert (
        run_workflow.main(["--dataset", "data/nonexistent.csv", "--prompt", "describe"])
        == 2
    )
    provider.assert_not_called()
    assert "CSV" in capsys.readouterr().err


def test_clarification_is_not_presented_as_success(capsys):
    state = {
        "control": Mock(status="needs_clarification"),
        "clarification_question": "Which column?",
    }
    assert run_workflow.print_outcome(state) == 2
    assert "Which column?" in capsys.readouterr().out
