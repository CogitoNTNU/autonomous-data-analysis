"""Interactive graphs need every model that a follow-up message can reach."""

from unittest.mock import Mock

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from backend.app.graph.builder import build_graph
from backend.app.tools.registry import ToolRegistry


def test_interactive_graph_requires_a_chat_model():
    with pytest.raises(ValueError, match="chat model"):
        build_graph(
            ToolRegistry(),
            Mock(),
            interpretation_model=Mock(),
            critic_model=Mock(),
            checkpointer=InMemorySaver(),
            conversational=True,
        )


def test_interactive_graph_waits_for_messages_after_finishing():
    graph = build_graph(
        ToolRegistry(),
        Mock(),
        interpretation_model=Mock(),
        critic_model=Mock(),
        checkpointer=InMemorySaver(),
        conversational=True,
        chat_model=Mock(),
    )

    edges = {(edge.source, edge.target) for edge in graph.get_graph().edges}

    assert ("finish_run", "conversation") in edges
    assert ("conversation", "dialogue") in edges
    assert ("dialogue", "planner") in edges
