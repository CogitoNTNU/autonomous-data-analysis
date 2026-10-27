"""Run the Critic Agent evaluation."""

from collections.abc import Sequence

from backend.app.agents.critic.agent import CriticModel
from backend.app.agents.critic.llm import CriticLLM
from backend.app.agents.critic.node import critic_node
from backend.app.contracts.models import Critique, DatasetReference, Plan, PlanStep
from backend.app.contracts.state import create_initial_state
from backend.scripts.critic_eval_cases import EvalCase, build_cases
from backend.scripts.critic_llm_smoke import configure_llm


def evaluate_case(case: EvalCase, model: CriticModel) -> Critique:
    """Run one case without sending its expected decision or review notes to the model."""
    dataset = DatasetReference(
        dataset_id=case.domain,
        version=f"{case.domain}-v1",
        storage_ref=f"synthetic://{case.domain}",
        schema={},
    )
    state = create_initial_state(case.user_query, dataset)
    state["plan"] = Plan(
        plan_id=f"{case.domain}-plan",
        objective=case.user_query,
        analysis_steps=[
            PlanStep(step_id=r.step_id, tool_name=r.method, arguments=r.parameters)
            for r in case.results
        ],
    )
    state["analysis_results"] = [r.model_copy(deep=True) for r in case.results]
    state["interpretation"] = case.interpretation.model_copy(deep=True)
    response = critic_node(state, model)
    if response.error is not None:
        raise ValueError(f"{response.error.code}: {response.error.message}")
    if response.updates.critique is None:
        raise ValueError("No critique returned")
    return response.updates.critique


def run_evaluation(cases: Sequence[EvalCase], model: CriticModel) -> int:
    """Run the cases and report decisions and errors."""
    completed = correct = false_approvals = false_revisions = errors = 0
    for case in cases:
        try:
            critique = evaluate_case(case, model)
        except Exception as exc:  # Report failures and keep evaluating other cases.
            errors += 1
            print(f"\n{case.name}: execution error ({type(exc).__name__}: {exc})")
            continue
        completed += 1
        correct += critique.decision == case.expected
        false_approvals += case.expected == "revise" and critique.decision == "approved"
        false_revisions += case.expected == "approved" and critique.decision == "revise"
        print(f"\n{case.name}: {critique.decision} (expected {case.expected})")
        for issue in critique.issues:
            print(
                f"  Issue ({issue.severity}, {issue.target_agent}): {issue.description}"
            )
            print(f"  References: {', '.join(issue.related_ids) or 'none'}")
        for change in critique.required_changes:
            print(f"  Required change: {change}")
        print(f"  Manual review: {case.review_note}")

    accuracy = f"{correct / completed:.1%}" if completed else "n/a"
    print(f"\nDecision accuracy: {accuracy} ({correct}/{completed} valid responses)")
    print(f"False approvals: {false_approvals}")
    print(f"False revisions: {false_revisions}")
    print(f"Execution errors: {errors}/{len(cases)}")
    print("Feedback quality: manual review only; see scripts/README.md.")
    return int(errors > 0 or correct != completed)


def main() -> int:
    configure_llm()
    return run_evaluation(build_cases(), CriticLLM())


if __name__ == "__main__":
    raise SystemExit(main())
