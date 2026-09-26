"""Tests for Planner LLM response parsing."""

from backend.app.agents.planner.llm import PlannerLLM


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
