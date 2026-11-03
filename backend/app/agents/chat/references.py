"""IDs a chat reply may cite: the run's plan, steps, results, and artifacts."""

from .schema import ChatContext


def known_ids(context: ChatContext) -> set[str]:
    ids = {result.result_id for result in context.analysis_results}
    ids |= {artifact.artifact_id for artifact in context.artifacts}
    if context.plan is not None:
        steps = [*context.plan.preprocessing_steps, *context.plan.analysis_steps]
        ids |= {context.plan.plan_id, *(step.step_id for step in steps)}
    return ids
