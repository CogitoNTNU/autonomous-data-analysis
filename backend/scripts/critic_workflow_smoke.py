"""Run the existing analysis workflow and evaluate real results with Critic."""

from backend.app.agents.critic.llm import CriticLLM
from backend.app.agents.critic.node import critic_node
from backend.app.agents.planner.llm import PlannerLLM
from backend.app.agents.preprocessing import register_preprocessing_tools
from backend.app.contracts.models import Finding, Interpretation
from backend.app.contracts.state import create_initial_state
from backend.app.graph.nodes import (
    analysis_graph_node,
    planner_graph_node,
    preprocessing_graph_node,
)
from backend.app.graph.responses import translate_agent_response
from backend.app.storage.datasets import create_dataset_reference
from backend.app.tools.analysis.descriptive import default_registry
from backend.app.tools.dataset.inspection import inspection_registry
from backend.scripts.planner_llm_smoke import _configure_planner


def main() -> int:
    _configure_planner()

    question = (
        "Remove rows where body_mass_g is missing, then group by "
        "species and calculate the mean body_mass_g for each species."
    )

    dataset = create_dataset_reference("data/penguins.csv")
    registry = register_preprocessing_tools(default_registry())
    state = create_initial_state(question, dataset)

    # Run the existing pipeline.
    state.update(
        planner_graph_node(
            state,
            registry,
            PlannerLLM(inspection_registry=inspection_registry()),
        )
    )

    if state["plan"] is None:
        print("Planner did not produce a plan.")
        print("Clarification:", state["clarification_question"])
        print("Errors:", state["errors"])
        return 1

    state.update(preprocessing_graph_node(state))
    if state["errors"]:
        print("Preprocessing errors:", state["errors"])
        return 1

    state.update(analysis_graph_node(state, registry))
    if state["errors"]:
        print("Analysis errors:", state["errors"])
        return 1

    # Extract the actual calculated group means.
    result = next(
        (r for r in state["analysis_results"] if r.method == "group_aggregate"),
        None,
    )

    if result is None or not isinstance(result.values, dict):
        print("Expected group_aggregate result was not found.")
        return 1

    groups = result.values.get("groups", [])
    means = {row["species"]: row["mean_body_mass_g"] for row in groups}

    if not {"Adelie", "Chinstrap", "Gentoo"} <= means.keys():
        print("Expected penguin species not found:", means)
        return 1

    correct = (
        f"After removing missing weights, the mean body masses "
        f"(n={result.sample_size}) are: "
        f"Adelie: {means['Adelie']} g; "
        f"Chinstrap: {means['Chinstrap']} g; "
        f"Gentoo: {means['Gentoo']} g."
    )

    # Intentionally replace the Gentoo mean with the Adelie mean.
    incorrect = correct.replace(
        f"Gentoo: {means['Gentoo']} g",
        f"Gentoo: {means['Adelie']} g",
    )

    model = CriticLLM()

    for label, summary, expected in [
        ("CORRECT", correct, "approved"),
        ("INCORRECT", incorrect, "revise"),
    ]:
        state["interpretation"] = Interpretation(
            summary=summary,
            findings=[Finding(claim=summary, result_ids=[result.result_id])],
        )
        state["critique"] = None

        print(f"\n=== {label} INTERPRETATION ===")
        print(summary)

        state.update(translate_agent_response(state, critic_node(state, model)))

        if state["errors"]:
            print("Critic errors:", state["errors"])
            return 1

        critique = state["critique"]
        if critique is None:
            print("Critic returned no critique.")
            return 1

        print(critique.model_dump_json(indent=2))
        print(
            "PASS"
            if critique.decision == expected
            else f"REVIEW: Expected {expected}, got {critique.decision}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
