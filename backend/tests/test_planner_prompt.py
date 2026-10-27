"""Require a fitting chart in analysis plans, and none for cleaning only."""

from pathlib import Path

PROMPT_PATH = Path(__file__).resolve().parents[1] / "app/agents/planner/prompt.md"


def test_prompt_requires_a_fitting_chart_except_for_cleaning_only():
    prompt = PROMPT_PATH.read_text(encoding="utf-8")

    assert "at least one chart that fits the data" in prompt
    for tool_name in (
        "heatmap",
        "histogram",
        "boxplot",
        "bar_chart",
        "scatter_plot",
        "line_chart",
    ):
        assert f"`{tool_name}`" in prompt
    assert "counts rows for each pair" in prompt
    assert "not a correlation heatmap" in prompt
    assert "only cleans the data" in prompt
    assert "no analysis steps" in prompt
    assert "must not add a chart" in prompt
