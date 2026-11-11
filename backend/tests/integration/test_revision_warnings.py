"""Replaced execution warnings cannot force an unresolvable Critic loop."""

import pytest

from backend.app.agents.planner.schema import PlannerOutput
from backend.app.contracts.models import Critique, CritiqueIssue, WarningEvent
from backend.app.contracts.state import create_initial_state
from backend.app.graph import nodes
from backend.app.graph.limits import workflow_recursion_limit


@pytest.mark.parametrize("target", ["planner", "preprocessing", "analysis"])
def test_replaced_execution_warnings_do_not_reappear_in_revised_interpretation(
    pipeline_graph, pipeline_dataset, pipeline_models, monkeypatch, target
):
    old_warning = WarningEvent(
        code="CONSTANT_COLUMN",
        source="descriptive_statistics",
        step_id="describe-age",
        message="A limitation of the superseded execution.",
    )
    original = nodes.analysis_node
    attempts = 0

    def analyze(state, registry):
        nonlocal attempts
        response = original(state, registry)
        attempts += 1
        if attempts == 1:
            response.updates.analysis_results[0].warnings.append(old_warning)
            response.warnings.append(old_warning)
        return response

    feedback = Critique(
        decision="revise",
        issues=[
            CritiqueIssue(
                code="REPLACE_EXECUTION",
                severity="error",
                description="Replace the affected execution.",
                target_agent=target,
            )
        ],
    )
    pipeline_models[2].side_effect = [feedback, Critique(decision="approved")]
    monkeypatch.setattr(nodes, "analysis_node", analyze)
    state = create_initial_state("Describe age", pipeline_dataset, max_revisions=1)

    result = pipeline_graph.invoke(
        state, config={"recursion_limit": workflow_recursion_limit(state["control"])}
    )

    first_context = pipeline_models[1].call_args_list[0].args[1]
    revised_context = pipeline_models[1].call_args_list[1].args[1]
    assert old_warning in first_context.evidence.warnings
    assert old_warning not in revised_context.evidence.warnings
    assert old_warning not in result["warnings"]
    assert all(
        "superseded" not in item for item in result["interpretation"].limitations
    )
    assert result["control"].status == "completed"
    assert result["control"].revision_count == 1
    assert result["revision_history"][0].critique == feedback
    assert result["warnings"]  # Current small-sample warnings are still required.


def test_replanning_removes_warnings_from_retired_preprocessing_steps(
    pipeline_graph, pipeline_dataset, pipeline_models, pipeline_plan, monkeypatch
):
    warning = WarningEvent(
        code="PREPROCESSING_WARNING",
        source="preprocessing",
        step_id="drop-missing",
        message="A limitation of the retired preprocessing step.",
    )
    original = nodes.preprocessing_node
    attempts = 0

    def preprocess(state):
        nonlocal attempts
        response = original(state)
        attempts += 1
        if attempts == 1:
            response.updates.preprocessing_report.warnings.append(warning)
            response.warnings.append(warning)
        return response

    revised = pipeline_plan.model_copy(deep=True)
    revised.plan_id = "no-preprocessing"
    revised.preprocessing_steps = []
    revised.analysis_steps[0].depends_on = []
    pipeline_models[0].side_effect = [
        PlannerOutput(plan=pipeline_plan),
        PlannerOutput(plan=revised),
    ]
    pipeline_models[2].side_effect = [
        Critique(
            decision="revise",
            issues=[
                CritiqueIssue(
                    code="RAW_DATA",
                    severity="error",
                    description="Describe the original observations without dropping rows.",
                    target_agent="planner",
                )
            ],
        ),
        Critique(decision="approved"),
    ]
    monkeypatch.setattr(nodes, "preprocessing_node", preprocess)

    result = pipeline_graph.invoke(
        create_initial_state("Describe age", pipeline_dataset)
    )

    assert result["control"].status == "completed"
    assert warning not in result["warnings"]
    assert all(
        "retired preprocessing" not in x for x in result["interpretation"].limitations
    )
    assert result["preprocessing_report"].rows_after == 3
