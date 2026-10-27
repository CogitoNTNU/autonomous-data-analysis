"""Smoke reporting and verification use the compiled graph with deterministic models."""

from unittest.mock import Mock

import pytest

from backend.app.contracts.models import Critique, DatasetReference
from backend.scripts import graph_llm_smoke as smoke


def test_smoke_runner_reports_full_workflow_and_validates_citations(
    pipeline_dataset: DatasetReference,
    pipeline_models: tuple[Mock, Mock, Mock],
    capsys: pytest.CaptureFixture[str],
) -> None:
    run = smoke.run_workflow(
        *pipeline_models, dataset_path=pipeline_dataset.storage_ref
    )

    valid = smoke.valid_interpretation(run.state)
    smoke.report_result(run, valid)

    assert smoke.smoke_passed(run, valid)
    assert run.path == [
        "start_run",
        "planner",
        "preprocessing",
        "analysis",
        "interpretation",
        "critic",
        "finish_run",
    ]
    output = capsys.readouterr().out
    assert "Final status: completed" in output
    assert "Revision count: 0" in output
    assert "Critic decision: approved" in output
    assert "Errors: 0" in output
    run.state["interpretation"].findings[0].result_ids = ["unknown-result"]
    assert not smoke.valid_interpretation(run.state)


def test_controlled_smoke_requires_rejection_and_observed_feedback(
    pipeline_dataset: DatasetReference,
    pipeline_models: tuple[Mock, Mock, Mock],
    revision_critique: Critique,
    capsys: pytest.CaptureFixture[str],
) -> None:
    pipeline_models[2].side_effect = [revision_critique, Critique(decision="approved")]

    run = smoke.run_workflow(
        *pipeline_models, dataset_path=pipeline_dataset.storage_ref, controlled=True
    )
    valid = smoke.valid_interpretation(run.state)
    smoke.report_result(run, valid)

    assert smoke.smoke_passed(run, valid)
    assert run.feedback_received
    assert run.decisions == ["revise", "approved"]
    assert run.state["control"].revision_count == 1
    pipeline_models[1].assert_called_once()
    context = pipeline_models[1].call_args.args[1]
    assert "-999999" in context.previous_interpretation.summary
    assert context.revision_feedback
    assert "Feedback reached the next Interpretation: True" in capsys.readouterr().out


def test_controlled_smoke_fails_if_critic_approves_injected_error(
    pipeline_dataset: DatasetReference,
    pipeline_models: tuple[Mock, Mock, Mock],
) -> None:
    run = smoke.run_workflow(
        *pipeline_models, dataset_path=pipeline_dataset.storage_ref, controlled=True
    )

    valid = smoke.valid_interpretation(run.state)

    assert valid  # Structural validity alone cannot establish numerical fidelity.
    assert run.state["critique"].decision == "approved"
    assert not smoke.smoke_passed(run, valid)
    assert not run.feedback_received
    pipeline_models[1].assert_not_called()


def test_smoke_failure_report_does_not_print_provider_details_or_credentials(
    pipeline_dataset: DatasetReference,
    pipeline_models: tuple[Mock, Mock, Mock],
    capsys: pytest.CaptureFixture[str],
) -> None:
    pipeline_models[0].side_effect = RuntimeError(
        "private-provider-details secret-test-key"
    )

    run = smoke.run_workflow(
        *pipeline_models, dataset_path=pipeline_dataset.storage_ref
    )
    valid = smoke.valid_interpretation(run.state)
    smoke.report_result(run, valid)

    output = capsys.readouterr().out
    assert "Execution exception: RuntimeError" in output
    assert "START -> start_run -> ABORTED" in output
    assert "Smoke result: FAIL" in output
    assert "private-provider-details" not in output
    assert "secret-test-key" not in output
    assert not smoke.smoke_passed(run, valid)


def test_smoke_cli_reuses_configuration_and_reports_actual_outcome(
    pipeline_dataset: DatasetReference,
    pipeline_models: tuple[Mock, Mock, Mock],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("NTNU_LLM_API_KEY", "secret-test-key")
    models = Mock(return_value=pipeline_models)
    monkeypatch.setattr(smoke, "_real_models", models)

    code = smoke.main(["--dataset", pipeline_dataset.storage_ref])

    assert code == 0
    settings = models.call_args.args[0]
    assert settings.api_key.get_secret_value() == "secret-test-key"
    output = capsys.readouterr().out
    assert "FULLY REAL LLM" in output
    assert "Smoke result: PASS" in output
    assert "secret-test-key" not in output


def test_smoke_missing_configuration_never_constructs_clients(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("NTNU_LLM_API_KEY", raising=False)
    models = Mock()
    monkeypatch.setattr(smoke, "_real_models", models)

    assert smoke.main([]) == 2

    models.assert_not_called()
    assert "NTNU_LLM_API_KEY" in capsys.readouterr().out
