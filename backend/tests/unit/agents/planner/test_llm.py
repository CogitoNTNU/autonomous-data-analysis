"""The Planner requests JSON while retaining bounded read-only inspection."""

import json
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from backend.app.agents.planner.agent import PlannerContext
from backend.app.agents.planner.llm import MAX_TOOL_ROUNDS, PlannerLLM
from backend.app.contracts.models import DatasetReference
from backend.app.tools.dataset.inspection import inspection_registry
from backend.app.tools.registry import ToolRegistry

OUTPUT = json.dumps({"plan": None, "clarification": {"question": "Which column?"}})


@pytest.fixture
def context() -> PlannerContext:
    return PlannerContext(
        "Describe age",
        DatasetReference(dataset_id="d", version="v1", storage_ref="a.csv", schema={}),
        [],
        None,
        [],
    )


@pytest.fixture
def adapter(monkeypatch):
    for name, value in {
        "NTNU_LLM_API_KEY": "test",
        "NTNU_LLM_MODEL": "test",
        "NTNU_LLM_BASE_URL": "https://provider.invalid/v1",
    }.items():
        monkeypatch.setenv(name, value)
    create = Mock()
    monkeypatch.setattr(
        "backend.app.agents.planner.llm.OpenAI",
        lambda **kwargs: SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=create))
        ),
    )
    return PlannerLLM(inspection_registry()), create


def _choice(*, content=OUTPUT, tool_calls=None, finish_reason="stop", refusal=None):
    return SimpleNamespace(
        finish_reason=finish_reason,
        message=SimpleNamespace(
            content=content, tool_calls=tool_calls, refusal=refusal
        ),
    )


def test_requests_output_schema_without_removing_registered_inspection_tools(
    adapter, context
):
    model, create = adapter
    create.return_value = SimpleNamespace(choices=[_choice()])

    output = model("Plan the analysis.", context)

    assert output.clarification.question == "Which column?"
    request = create.call_args.kwargs
    response_format = request["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["name"] == "planner_output"
    assert response_format["json_schema"]["strict"] is False
    schema = response_format["json_schema"]["schema"]
    assert schema["required"] == ["plan", "clarification"]
    assert schema["oneOf"] == [
        {
            "required": ["plan"],
            "properties": {
                "plan": {"type": "object"},
                "clarification": {"type": "null"},
            },
        },
        {
            "required": ["clarification"],
            "properties": {
                "plan": {"type": "null"},
                "clarification": {"type": "object"},
            },
        },
    ]
    assert schema["$defs"]["PlanStep"]["properties"]["arguments"][
        "additionalProperties"
    ]
    assert {tool["function"]["name"] for tool in request["tools"]} == {
        "get_metadata",
        "inspect_schema",
        "preview_data",
        "column_profile",
    }
    create.assert_called_once()


def test_schema_request_preserves_open_tool_arguments_in_a_plan(adapter, context):
    model, create = adapter
    plan = {
        "plan_id": "p1",
        "objective": "Describe age",
        "analysis_steps": [
            {
                "step_id": "describe",
                "tool_name": "descriptive_statistics",
                "arguments": {"columns": ["age"]},
            }
        ],
    }
    create.return_value = SimpleNamespace(
        choices=[_choice(content=json.dumps({"plan": plan, "clarification": None}))]
    )

    output = model("Plan the analysis.", context)

    assert output.plan.analysis_steps[0].arguments == {"columns": ["age"]}
    assert output.clarification is None
    create.assert_called_once()


@pytest.mark.parametrize(
    "choices",
    [
        [],
        [_choice(), _choice()],
        [_choice(finish_reason="length")],
        [_choice(finish_reason="content_filter")],
        [_choice(finish_reason=None)],
        [_choice(refusal="Cannot comply")],
        [_choice(content=None)],
        [_choice(content="not JSON")],
        [_choice(content='{"plan": null, "clarification": null}')],
        [
            _choice(
                content=json.dumps(
                    {
                        "plan": {"plan_id": "p1", "objective": "Describe age"},
                        "clarification": {"question": "Which column?"},
                    }
                )
            )
        ],
        [_choice(finish_reason="tool_calls")],
    ],
)
def test_invalid_responses_fail_once_without_attempting_plan_repair(
    adapter, context, choices
):
    model, create = adapter
    create.return_value = SimpleNamespace(choices=choices)

    with pytest.raises(ValueError):
        model("Plan the analysis.", context)

    create.assert_called_once()


def _tool_call(name="get_metadata", arguments="{}"):
    payload = {
        "id": "inspect-1",
        "type": "function",
        "function": {"name": name, "arguments": arguments},
    }
    return SimpleNamespace(
        id="inspect-1",
        function=SimpleNamespace(name=name, arguments=arguments),
        model_dump=lambda: payload,
    )


def test_inspection_result_precedes_final_json_response(adapter, context):
    model, create = adapter
    inspect = Mock(return_value={"row_count": 3})
    registry = ToolRegistry()
    registry.register(
        replace(model.inspection_registry.get("get_metadata"), run=inspect)
    )
    model.inspection_registry = registry
    create.side_effect = [
        SimpleNamespace(
            choices=[
                _choice(
                    content=None, tool_calls=[_tool_call()], finish_reason="tool_calls"
                )
            ]
        ),
        SimpleNamespace(choices=[_choice()]),
    ]

    output = model("Plan the analysis.", context)

    assert output.clarification is not None
    assert create.call_count == 2
    inspect.assert_called_once_with(context.dataset)
    messages = create.call_args.kwargs["messages"]
    assert messages[-1] == {
        "role": "tool",
        "tool_call_id": "inspect-1",
        "content": '{"row_count": 3}',
    }


def test_inspection_round_limit_is_unchanged(adapter, context):
    model, create = adapter
    registry = ToolRegistry()
    registry.register(
        replace(
            model.inspection_registry.get("get_metadata"), run=Mock(return_value={})
        )
    )
    model.inspection_registry = registry
    create.return_value = SimpleNamespace(
        choices=[
            _choice(content=None, tool_calls=[_tool_call()], finish_reason="tool_calls")
        ]
    )

    with pytest.raises(RuntimeError, match="maximum number of tool rounds"):
        model("Plan the analysis.", context)

    assert create.call_count == MAX_TOOL_ROUNDS


@pytest.mark.parametrize(
    "tool",
    [
        _tool_call("remove_duplicates"),
        _tool_call("preview_data", '{"limit": "invalid"}'),
    ],
)
def test_unregistered_or_invalid_inspections_are_rejected(adapter, context, tool):
    model, create = adapter
    create.return_value = SimpleNamespace(
        choices=[_choice(content=None, tool_calls=[tool], finish_reason="tool_calls")]
    )

    with pytest.raises(ValueError):
        model("Plan the analysis.", context)

    create.assert_called_once()
