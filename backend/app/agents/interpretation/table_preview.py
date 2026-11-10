"""Bound grouped tables in model context while retaining explicit preview scope."""

import json

from .schema import InterpretationContext, ResultEvidence, TablePreview

MAX_PREVIEW_ROWS = 50


def bound_grouped_tables(
    context: InterpretationContext, max_characters: int
) -> InterpretationContext:
    """Return an independent projection; full workflow results remain unchanged.

    Only oversized contexts receive previews. Other evidence, metadata and
    warnings are retained. The serialization guard still rejects contexts that
    cannot fit even after table previews, rather than dropping other evidence.
    """
    bounded = context.model_copy(deep=True)
    while len(bounded.model_dump_json()) > max_characters:
        candidates = [
            result for result in bounded.evidence.results if _can_preview(result)
        ]
        if not candidates:
            break
        largest = max(candidates, key=lambda item: len(json.dumps(item.values)))
        _preview_table(bounded, largest)
    return bounded


def _can_preview(result: ResultEvidence) -> bool:
    groups = result.values.get("groups")
    return (
        result.method == "group_aggregate"
        and isinstance(groups, list)
        and len(groups) > 1
    )


def _preview_table(context: InterpretationContext, result: ResultEvidence) -> None:
    groups = result.values["groups"]
    if not isinstance(groups, list):
        raise ValueError("Grouped evidence requires table rows")
    total = result.table_preview.total_rows if result.table_preview else len(groups)
    if result.values.get("group_count") != total:
        raise ValueError("Grouped evidence count does not match its table")
    sizes = result.values.get("group_sizes")
    if sizes is not None and (not isinstance(sizes, list) or len(sizes) != len(groups)):
        raise ValueError("Grouped evidence sizes do not match its table")
    if result.table_preview is not None:
        context.evidence.required_limitations.remove(_limitation(result))
    shown = min(MAX_PREVIEW_ROWS, len(groups) // 2)
    result.values["groups"] = groups[:shown]
    if isinstance(sizes, list):
        result.values["group_sizes"] = sizes[:shown]
    result.table_preview = TablePreview(shown_rows=shown, total_rows=total)
    context.evidence.required_limitations.append(_limitation(result))


def _limitation(result: ResultEvidence) -> str:
    preview = result.table_preview
    if preview is None:
        raise ValueError("Table preview metadata is required")
    return (
        f"Interpretation evidence for result '{result.result_id}' is a preview of "
        f"the first {preview.shown_rows} of {preview.total_rows} groups in table order. "
        "The complete table is retained in the analysis results. "
        "This preview cannot establish rankings or comparisons across omitted groups."
    )
