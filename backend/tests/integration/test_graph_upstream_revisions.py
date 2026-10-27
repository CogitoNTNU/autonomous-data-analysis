"""Critic revisions rerun the earliest affected stage and its dependents."""

from copy import deepcopy
from unittest.mock import Mock

import pytest

from backend.app.agents.planner.schema import PlannerOutput
from backend.app.contracts.models import Critique, CritiqueIssue
from backend.app.contracts.state import create_initial_state
from backend.app.graph import nodes
from backend.app.graph.limits import workflow_recursion_limit


@pytest.mark.parametrize(
    "targets",
    [
        ["planner"],
        ["preprocessing"],
        ["analysis"],
        ["analysis", "interpretation"],
        ["analysis", "preprocessing"],
    ],
)
def test_revisions_preserve_unaffected_work_and_raw_dataset(
    pipeline_graph,
    pipeline_dataset,
    pipeline_models,
    pipeline_plan,
    monkeypatch,
    targets,
):
    spies = {}
    for agent in ["planner", "preprocessing", "analysis", "interpretation", "critic"]:
        spies[agent] = Mock(wraps=getattr(nodes, f"{agent}_node"))
        monkeypatch.setattr(nodes, f"{agent}_node", spies[agent])
    feedback = Critique(
        decision="revise",
        issues=[
            CritiqueIssue(
                code="REVISE",
                severity="error",
                description="Revisit this stage.",
                target_agent=target,
            )
            for target in targets
        ],
    )
    pipeline_models[2].side_effect = [feedback, Critique(decision="approved")]
    state = create_initial_state("Describe age", pipeline_dataset, max_revisions=1)
    original = deepcopy(state)

    result = pipeline_graph.invoke(
        state, config={"recursion_limit": workflow_recursion_limit(state["control"])}
    )

    order = ["planner", "preprocessing", "analysis", "interpretation", "critic"]
    earliest = min(order.index(target) for target in targets)
    assert result["control"].status == "completed"
    assert result["control"].revision_count == 1
    for index, name in enumerate(order):
        assert spies[name].call_count == (2 if index >= earliest else 1)
    assert result["dataset"] == original["dataset"]
    assert state == original
    assert result["revision_history"][0].target_agent == order[earliest]
    assert result["revision_history"][0].critique == feedback
    if "planner" in targets:
        context = pipeline_models[0].call_args_list[1].args[1]
        assert context.critique == feedback
        assert context.previous_plan == pipeline_plan
    if earliest <= order.index("analysis"):
        assert (
            pipeline_models[1].call_args_list[1].args[1].previous_interpretation is None
        )
    if "interpretation" in targets:
        assert pipeline_models[1].call_args_list[1].args[1].revision_feedback == [
            "Revisit this stage."
        ]


def test_planner_revision_changes_execution_instead_of_replaying_old_plan(
    pipeline_graph, pipeline_dataset, pipeline_models, pipeline_plan
):
    revised = pipeline_plan.model_copy(deep=True)
    revised.plan_id = "revised-plan"
    revised.analysis_steps[0].arguments = {"columns": ["score"]}
    pipeline_models[0].side_effect = [
        PlannerOutput(plan=pipeline_plan),
        PlannerOutput(plan=revised),
    ]
    pipeline_models[2].side_effect = [
        Critique(
            decision="revise",
            issues=[
                CritiqueIssue(
                    code="WRONG_METHOD",
                    severity="error",
                    description="Describe score instead.",
                    target_agent="planner",
                )
            ],
        ),
        Critique(decision="approved"),
    ]
    state = create_initial_state("Describe score", pipeline_dataset, max_revisions=1)

    result = pipeline_graph.invoke(state, config={"recursion_limit": 20})

    assert result["control"].status == "completed"
    assert result["plan"].plan_id == "revised-plan"
    assert result["analysis_results"][0].parameters["columns"] == ["score"]
    assert result["revision_history"][0].plan_id == pipeline_plan.plan_id


@pytest.mark.parametrize("target", ["planner", "preprocessing", "analysis"])
def test_upstream_rejections_share_the_revision_budget(
    pipeline_graph, pipeline_dataset, pipeline_models, target
):
    pipeline_models[2].return_value = Critique(
        decision="revise",
        issues=[
            CritiqueIssue(
                code="REVISE",
                severity="error",
                description="Retry this stage.",
                target_agent=target,
            )
        ],
    )
    state = create_initial_state("Describe age", pipeline_dataset, max_revisions=1)

    result = pipeline_graph.invoke(state, config={"recursion_limit": 20})

    assert result["control"].status == "error"
    assert result["last_node_error"].code == "REVISION_LIMIT"
    assert result["control"].revision_count == 1
    assert len(result["revision_history"]) == 1
