"""State adapter a LangGraph node can call. The graph itself lives in app/graph."""

from backend.app.agents.analysis.agent import run_analysis
from backend.app.contracts.errors import AgentError
from backend.app.contracts.models import AnalysisUpdates, Plan, PlanStep
from backend.app.contracts.responses import AgentResponse
from backend.app.contracts.state import AgentState
from backend.app.tools.registry import ToolRegistry

SOURCE = "analysis"


def analysis_node(
    state: AgentState,
    registry: ToolRegistry | None = None,
) -> AgentResponse[AnalysisUpdates]:
    dataset = state["processed_dataset"]
    plan = state["plan"]

    if dataset is None or plan is None:
        return AgentResponse[AnalysisUpdates](
            status="error",
            updates=AnalysisUpdates(),
            error=AgentError(
                code="INVALID_DATA",
                message="Analysis requires a plan and processed dataset.",
                source="analysis",
                retryable=False,
            ),
        )

    engine = run_analysis(
        dataset,
        _ready_analysis_steps(plan),
        state["preprocessing_report"],
        registry,
    )

    return engine.response


def _ready_analysis_steps(plan: Plan) -> list[PlanStep]:
    completed = {step.step_id for step in plan.preprocessing_steps}
    return [
        step.model_copy(
            update={
                "depends_on": [
                    dependency
                    for dependency in step.depends_on
                    if dependency not in completed
                ]
            }
        )
        for step in plan.analysis_steps
    ]
