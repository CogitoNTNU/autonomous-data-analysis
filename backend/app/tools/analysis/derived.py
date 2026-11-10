"""Schemas for tabular outputs produced by analysis tools."""

from collections.abc import Mapping
from typing import Any

VISUALIZATION_TOOL_NAMES = frozenset(
    {
        "bar_chart",
        "boxplot",
        "heatmap",
        "histogram",
        "line_chart",
        "scatter_plot",
    }
)


def group_aggregate_schema(
    arguments: Mapping[str, Any], source_schema: dict[str, Any]
) -> dict[str, Any]:
    """Describe the columns emitted by a group_aggregate step."""
    schema = {
        column: source_schema[column]
        for column in arguments.get("group_by", [])
        if column in source_schema
    }
    for aggregation in arguments.get("aggregations", []):
        if not isinstance(aggregation, Mapping):
            continue
        alias = aggregation.get("alias")
        column = aggregation.get("column")
        function = aggregation.get("function")
        if not isinstance(alias, str) or not isinstance(column, str):
            continue
        source = source_schema.get(column)
        source_datatype = source.get("datatype") if isinstance(source, dict) else None
        if function == "count":
            datatype = "integer"
        elif function in {"mean", "median", "std"}:
            datatype = "float"
        else:
            datatype = source_datatype or "float"
        schema[alias] = {"datatype": datatype, "missing_count": 0}
        if isinstance(source, dict):
            source_label = source.get("label", column.replace("_", " "))
            prefixes = {
                "count": "Number of nonmissing values of",
                "mean": "Mean",
                "median": "Median",
                "sum": "Total",
                "min": "Minimum",
                "max": "Maximum",
                "std": "Standard deviation of",
            }
            schema[alias]["label"] = (
                f"{prefixes.get(function, function)} {source_label}"
            )
            if function != "count" and "unit" in source:
                schema[alias]["unit"] = source["unit"]
    return schema
