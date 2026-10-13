"""Adapt shared workflow state to a typed interpretation attempt."""

from backend.app.contracts.errors import AgentError
from backend.app.contracts.models import DatasetReference, InterpretationUpdates
from backend.app.contracts.responses import AgentResponse
from backend.app.contracts.state import AgentState

from .agent import run_interpretation
from .schema import InterpretationInput, InterpretationModel


def build_interpretation_input(state: AgentState) -> InterpretationInput:
    """Read required fields and return an independent, validated input.

    A processed dataset reference is required even for no-op preprocessing;
    missing workflow output must not fall back to the source dataset.
    Missing keys raise KeyError; missing or invalid values raise ValueError.
    """
    dataset = state["processed_dataset"]
    if dataset is None or state["plan"] is None:
        raise ValueError("Interpretation requires a plan and processed dataset")
    dataset = DatasetReference.model_validate(
        dataset.model_dump(by_alias=True)
        if isinstance(dataset, DatasetReference)
        else dataset
    )
    return InterpretationInput(
        run_id=state["run_id"],
        user_query=state["user_query"],
        plan=state["plan"],
        dataset_version=dataset.version,
        analysis_results=state["analysis_results"],
        artifacts=state["artifacts"],
        preprocessing_report=state["preprocessing_report"],
        warnings=state["warnings"],
        previous_interpretation=state["interpretation"],
        critique=state["critique"],
    ).model_copy(deep=True)


def interpretation_node(
    state: AgentState,
    model: InterpretationModel,
) -> AgentResponse[InterpretationUpdates]:
    """Return typed updates without mutating state or controlling the workflow.

    The harness merges updates, records errors and warnings, and decides routing
    and retries. Failure explicitly clears the interpretation update so a merge
    using exclude_unset=True cannot silently retain an older draft.
    """
    try:
        request = build_interpretation_input(state)
    except (KeyError, ValueError):
        return AgentResponse[InterpretationUpdates](
            status="error",
            updates=InterpretationUpdates(interpretation=None),
            error=AgentError(
                code="INVALID_DATA",
                message="Workflow state is missing or invalid for interpretation.",
                source="interpretation",
            ),
        )

    response = run_interpretation(request, model)
    if response.status != "success":
        return response.model_copy(
            update={"updates": InterpretationUpdates(interpretation=None)}
        )
    return response
