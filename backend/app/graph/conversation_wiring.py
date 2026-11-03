"""Wire clarification, presentation, and follow-up dialogue into an interactive graph."""

from functools import partial

from langgraph.graph import END, StateGraph

from backend.app.agents.chat.reply import ChatModel
from backend.app.contracts.dialogue import MAX_DIALOGUE_MESSAGES
from backend.app.contracts.state import AgentState

from .conversation import await_message
from .dialogue import dialogue_graph_node
from .interaction import chat_graph_node, clarify
from .observability import measured_node


def add_conversation(builder: StateGraph, chat_model: ChatModel) -> None:
    """Completed runs wait for messages until the per-run message limit is reached."""
    builder.add_node("clarification", clarify)
    builder.add_conditional_edges(
        "clarification",
        lambda state: "finish_run" if state["last_node_error"] else "planner",
        {"finish_run": "finish_run", "planner": "planner"},
    )
    builder.add_node("chat", measured_node("chat", chat_graph_node))
    builder.add_edge("chat", "finish_run")
    builder.add_node("conversation", await_message)
    builder.add_node(
        "dialogue",
        measured_node("chat", partial(dialogue_graph_node, model=chat_model)),
    )
    builder.add_conditional_edges(
        "finish_run", _after_finish, {"conversation": "conversation", "end": END}
    )
    builder.add_edge("conversation", "dialogue")
    builder.add_conditional_edges(
        "dialogue",
        _after_dialogue,
        {"planner": "planner", "conversation": "conversation", "end": END},
    )


def _after_finish(state: AgentState) -> str:
    if state["control"].status != "completed":
        return "end"
    return "conversation" if _can_ask(state) else "end"


def _after_dialogue(state: AgentState) -> str:
    last = state["dialogue"][-1]
    if last.starts_analysis and not last.failed:
        return "planner"
    return "conversation" if _can_ask(state) else "end"


def _can_ask(state: AgentState) -> bool:
    asked = sum(turn.role == "user" for turn in state.get("dialogue", []))
    return asked < MAX_DIALOGUE_MESSAGES
