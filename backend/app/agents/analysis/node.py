"""State adapter a LangGraph node can call. The graph itself lives in app/graph."""

from backend.app.agents.analysis.agent import run_analysis
from backend.app.contracts.models import WarningEvent
from backend.app.contracts.state import AgentState
from backend.app.tools.registry import ToolRegistry

SOURCE = "analysis"


def analysis_node(
    state: AgentState,
    registry: ToolRegistry | None = None,
) -> dict[str, object]:
    dataset = state["processed_dataset"]
    plan = state["plan"]
    if dataset is None or plan is None:
        return {"warnings": [*state["warnings"], _missing_input(state)]}
    engine = run_analysis(
        dataset,
        plan.analysis_steps,
        state["preprocessing_report"],
        registry,
    )
    updates = engine.response.updates
    return {
        "analysis_results": updates.analysis_results,
        "artifacts": updates.artifacts,
        "warnings": [*state["warnings"], *engine.response.warnings],
    }


def _missing_input(state: AgentState) -> WarningEvent:
    missing = "processed_dataset" if state["processed_dataset"] is None else "plan"
    return WarningEvent(
        code="INVALID_DATA",
        message=f"analysis node missing {missing}",
        source=SOURCE,
    )
