"""Tests for Planner LLM response parsing."""

from types import SimpleNamespace
from unittest.mock import Mock

import httpx2
import pytest
from openai import APIConnectionError, APITimeoutError

from backend.app.agents.planner.agent import PlannerContext
from backend.app.agents.planner.llm import PlannerLLM
from backend.app.contracts.models import DatasetReference
from backend.app.tools.registry import ToolRegistry

PLANNER_OUTPUT_JSON = """
{
  "plan": {
    "plan_id": "plan-1",
    "objective": "Compute descriptive statistics for body mass.",
    "required_columns": ["body_mass_g"],
    "preprocessing_steps": [],
    "analysis_steps": [],
    "expected_outputs": ["Descriptive statistics"],
    "assumptions": []
  },
  "clarification": null
}
"""


def test_parse_output_accepts_plain_json():
    output = PlannerLLM._parse_output(PLANNER_OUTPUT_JSON)

    assert output.plan is not None
    assert output.plan.plan_id == "plan-1"
    assert output.clarification is None


def test_parse_output_accepts_json_code_block():
    content = f"""```json
{PLANNER_OUTPUT_JSON}
```"""

    output = PlannerLLM._parse_output(content)

    assert output.plan is not None
    assert output.plan.plan_id == "plan-1"
    assert output.clarification is None


@pytest.mark.parametrize(
    "failure,expected",
    [(APITimeoutError, TimeoutError), (APIConnectionError, ConnectionError)],
)
def test_provider_transient_errors_are_normalized_for_harness(
    monkeypatch, failure, expected
):
    request = httpx2.Request("POST", "https://provider.invalid/v1")
    completion = Mock(side_effect=failure(request=request))
    factory = Mock(
        return_value=SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=completion))
        )
    )
    monkeypatch.setattr("backend.app.agents.planner.llm.OpenAI", factory)
    for name, value in {
        "NTNU_LLM_API_KEY": "test",
        "NTNU_LLM_MODEL": "test",
        "NTNU_LLM_BASE_URL": "https://provider.invalid/v1",
    }.items():
        monkeypatch.setenv(name, value)
    model = PlannerLLM(ToolRegistry())
    context = PlannerContext(
        "Describe age",
        DatasetReference(dataset_id="d", version="v1", storage_ref="unused", schema={}),
        [],
        None,
        [],
    )

    with pytest.raises(expected):
        model("Plan", context)

    completion.assert_called_once()
    assert factory.call_args.kwargs["max_retries"] == 0
