"""Tests for the Critic evaluation cases and runner."""

import csv
import json
from collections import Counter
from types import SimpleNamespace

import pytest

from backend.app.agents.critic.agent import CriticContext
from backend.app.agents.critic.llm import CriticLLM
from backend.app.contracts.models import CriticUpdates, Critique, PlanStep
from backend.app.contracts.responses import AgentResponse
from backend.app.storage.datasets import create_dataset_reference
from backend.app.tools.analysis.descriptive import default_registry
from backend.app.tools.registry import execute_step
from backend.scripts import critic_eval
from backend.scripts.critic_eval import evaluate_case, run_evaluation
from backend.scripts.critic_eval_cases import build_cases


def test_cases_are_balanced_across_domains() -> None:
    cases = build_cases()
    assert len({case.name for case in cases}) == 12
    assert Counter((case.domain, case.expected) for case in cases) == {
        (domain, decision): 2
        for domain in ("penguins", "sales", "traffic")
        for decision in ("approved", "revise")
    }


def test_evidence_matches_real_tool_outputs(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("backend.app.storage.datasets.ALLOWED", (tmp_path,))
    monkeypatch.setattr(
        "backend.app.tools.analysis.files.ALLOWED_DATA_DIRECTORIES", (tmp_path,)
    )
    data = {
        "penguins": (
            ["body_mass_g"],
            [[v] for v in [3000] * 40 + [4000] * 20 + [6000] * 20 + [None] * 20],
        ),
        "sales": (
            ["region", "order_value_usd"],
            [["North", v] for v in [200] * 20 + [400] * 20]
            + [["South", v] for v in [200] * 10 + [400] * 10],
        ),
        "traffic": (
            ["channel"],
            [[v] for v in ["organic"] * 36 + ["paid"] * 24 + [None] * 40],
        ),
    }
    for domain, (columns, rows) in data.items():
        with (tmp_path / f"{domain}.csv").open(
            "w", newline="", encoding="utf-8"
        ) as stream:
            csv.writer(stream).writerows([columns, *rows])
    evidence = {
        result.result_id: (case.domain, result)
        for case in build_cases()
        for result in case.results
    }
    for domain, expected in evidence.values():
        dataset = create_dataset_reference(
            tmp_path / f"{domain}.csv", version=expected.dataset_version
        )
        actual = execute_step(
            PlanStep(
                step_id=expected.step_id,
                tool_name=expected.method,
                arguments=expected.parameters,
            ),
            dataset,
            default_registry(),
        )
        assert actual.sample_size == expected.sample_size
        assert actual.warnings == expected.warnings
        if expected.method == "descriptive_statistics":
            assert actual.values["status"] == expected.values["status"]
            for column, stats in expected.values["columns"].items():
                assert actual.values["columns"][column] == pytest.approx(stats)
        else:
            assert actual.values == expected.values


def test_provider_payload_has_warnings_without_evaluation_labels(monkeypatch) -> None:
    case = build_cases()[-1]
    captured = []

    def completion(**kwargs):
        captured.append(json.loads(kwargs["messages"][1]["content"]))
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    finish_reason="stop",
                    message=SimpleNamespace(
                        content=Critique(decision="approved").model_dump_json()
                    ),
                )
            ]
        )

    for name, value in {
        "NTNU_LLM_MODEL": "test",
        "NTNU_LLM_API_KEY": "test",
        "NTNU_LLM_BASE_URL": "https://example.invalid/v1",
    }.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(
        "backend.app.agents.critic.llm.OpenAI",
        lambda **kwargs: SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=completion))
        ),
    )
    evaluate_case(case, CriticLLM())
    payload = captured[0]
    assert payload["analysis_results"][0]["warnings"][0]["code"] == "HIGH_MISSING_RATE"
    assert payload["analysis_results"][0]["values"]["missing_count"] == 40
    assert payload["interpretation"]["limitations"] == []
    assert set(payload) == {
        "user_query",
        "plan",
        "analysis_results",
        "interpretation",
        "preprocessing_report",
        "analysis_execution_report",
        "warnings",
    }
    assert case.name not in json.dumps(payload)
    assert case.review_note not in json.dumps(payload)


def test_runner_separates_wrong_decisions_from_errors_and_continues(capsys) -> None:
    replies = iter(
        [
            Critique(decision="approved"),
            Critique(decision="revise"),
            Critique(decision="approved"),
            RuntimeError("unavailable"),
            Critique(decision="approved"),
        ]
    )

    def fake_model(prompt: str, context: CriticContext) -> Critique:
        reply = next(replies)
        if isinstance(reply, Exception):
            raise reply
        return reply

    assert run_evaluation(build_cases()[:5], fake_model) == 1
    output = capsys.readouterr().out
    assert "Decision accuracy: 50.0% (2/4 valid responses)" in output
    assert "False approvals: 1" in output
    assert "False revisions: 1" in output
    assert "Execution errors: 1/5" in output
    assert "sales_totals: approved" in output
    assert "===" not in output


def test_runner_succeeds_without_automatically_grading_feedback(capsys) -> None:
    cases = build_cases()
    replies = iter(Critique(decision=case.expected) for case in cases)
    assert run_evaluation(cases, lambda prompt, context: next(replies)) == 0
    output = capsys.readouterr().out
    assert "Decision accuracy: 100.0% (12/12 valid responses)" in output
    assert "Execution errors: 0/12" in output
    assert "Feedback quality: manual review only" in output


@pytest.mark.parametrize("failure", ["invalid_output", "missing_critique"])
def test_all_execution_failures_have_no_decision_accuracy(
    failure, monkeypatch, capsys
) -> None:
    if failure == "missing_critique":
        monkeypatch.setattr(
            critic_eval,
            "critic_node",
            lambda state, model: AgentResponse[CriticUpdates](
                status="success", updates=CriticUpdates()
            ),
        )

    def fake_model(prompt: str, context: CriticContext) -> Critique:
        raise ValueError("invalid JSON")

    assert run_evaluation(build_cases()[:1], fake_model) == 1
    output = capsys.readouterr().out
    assert "Decision accuracy: n/a (0/0 valid responses)" in output
    assert "Execution errors: 1/1" in output
    assert "False approvals: 0" in output
    assert "False revisions: 0" in output


def test_unexpected_cannot_complete_is_incorrect_without_becoming_a_revision(
    capsys,
) -> None:
    assert (
        run_evaluation(
            build_cases()[:1],
            lambda prompt, context: Critique(decision="cannot_complete"),
        )
        == 1
    )
    output = capsys.readouterr().out
    assert "Decision accuracy: 0.0% (0/1 valid responses)" in output
    assert "False revisions: 0" in output
    assert "Execution errors: 0/1" in output
