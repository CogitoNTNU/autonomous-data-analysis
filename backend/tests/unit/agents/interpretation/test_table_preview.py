"""Large grouped evidence is bounded explicitly without changing source results."""

import pytest

from backend.app.agents.interpretation.context import serialize_context
from backend.app.agents.interpretation.schema import (
    InterpretationContext,
    InterpretationEvidence,
    ResultEvidence,
)
from backend.app.agents.interpretation.table_preview import bound_grouped_tables
from backend.app.contracts.models import WarningEvent


def context_with_tables(count: int = 1, rows: int = 200) -> InterpretationContext:
    warning = WarningEvent(
        code="HIGH_MISSING_RATE",
        source="analysis",
        message="Missing values were excluded",
    )
    return InterpretationContext(
        user_query="Compare groups",
        objective="Compare groups",
        assumptions=[],
        expected_outputs=[],
        evidence=InterpretationEvidence(
            results=[
                ResultEvidence(
                    result_id=f"r{index}",
                    step_id=f"s{index}",
                    dataset_version="v1",
                    method="group_aggregate",
                    parameters={},
                    sample_size=rows,
                    values={
                        "status": "partial",
                        "group_count": rows,
                        "group_sizes": [1] * rows,
                        "groups": [
                            {"name": f"Group {row}", "mean": row} for row in range(rows)
                        ],
                    },
                    warnings=[warning],
                )
                for index in range(count)
            ],
            warnings=[warning],
            required_limitations=["Existing qualification"],
        ),
        artifacts=[],
    )


def test_small_tables_remain_complete_without_preview_limitations():
    context = context_with_tables(rows=3)

    bounded = bound_grouped_tables(context, 64_000)

    assert bounded == context
    assert bounded.evidence.results[0].table_preview is None


def test_bounds_multiple_tables_and_preserves_metadata_warnings_and_source():
    context = context_with_tables(count=3)
    original = context.model_dump()

    bounded = bound_grouped_tables(context, 6_000)

    serialize_context(bounded, max_characters=6_000)
    for result in bounded.evidence.results:
        preview = result.table_preview
        assert preview is not None
        assert preview.total_rows == result.values["group_count"] == 200
        assert (
            preview.shown_rows
            == len(result.values["groups"])
            == len(result.values["group_sizes"])
        )
        assert preview.selection == "first_rows"
        assert result.values["groups"][0] == {"name": "Group 0", "mean": 0}
        assert result.sample_size == 200
        assert result.warnings == context.evidence.results[0].warnings
    assert bounded.evidence.warnings == context.evidence.warnings
    assert len(bounded.evidence.required_limitations) == 4
    assert bounded.evidence.required_limitations[0] == "Existing qualification"
    assert context.model_dump() == original


@pytest.mark.parametrize("problem", ["count", "sizes"])
def test_rejects_misaligned_group_metadata_instead_of_presenting_a_preview(problem):
    context = context_with_tables()
    result = context.evidence.results[0]
    if problem == "count":
        result.values["group_count"] = 999
    else:
        result.values["group_sizes"] = [1]

    with pytest.raises(ValueError, match="does not match|do not match"):
        bound_grouped_tables(context, 2_000)


def test_unfit_single_row_context_still_fails_instead_of_dropping_evidence():
    context = context_with_tables(rows=1)
    context.user_query = "x" * 2_000

    bounded = bound_grouped_tables(context, 2_000)

    assert bounded == context
    with pytest.raises(ValueError, match="exceeds"):
        serialize_context(bounded, max_characters=2_000)
