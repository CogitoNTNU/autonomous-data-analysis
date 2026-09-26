"""Result kept by the analysis node. It is not written onto AgentState."""

from dataclasses import dataclass, field

from backend.app.contracts.models import AnalysisUpdates
from backend.app.contracts.responses import AgentResponse


@dataclass
class EngineResult:
    response: AgentResponse[AnalysisUpdates]
    missing_steps: list[str]
    execution_log: list[str] = field(default_factory=list)
