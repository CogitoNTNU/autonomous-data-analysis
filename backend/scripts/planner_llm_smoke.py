"""Manual smoke test for the Planner workflow integration."""

from pprint import pprint

from backend.app.agents.planner.llm import PlannerLLM
from backend.app.agents.planner.node import planner_node
from backend.app.contracts.state import create_initial_state
from backend.app.storage.datasets import create_dataset_reference
from backend.app.tools.analysis.descriptive import default_registry
from backend.app.tools.dataset.inspection import inspection_registry


dataset = create_dataset_reference("data/penguins.csv")

state = create_initial_state(
    user_query="Give me descriptive statistics for penguin body mass.",
    dataset=dataset,
)

model = PlannerLLM(
    inspection_registry=inspection_registry(),
)

updates = planner_node(
    state=state,
    registry=default_registry(),
    model=model,
)

pprint(updates)
