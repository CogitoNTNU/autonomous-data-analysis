"""Shared chart inputs. `columns` is what the registry checks before a call."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

NUMERIC_DTYPES = frozenset({"integer", "float"})
ChartText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
ChartKind = Literal[
    "bar_chart", "line_chart", "scatter_plot", "histogram", "boxplot", "heatmap"
]


class ChartInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: ChartText
    x: str = Field(min_length=1)
    y: str | None = None
    group: str | None = None
    source_result_id: str | None = None
    x_label: ChartText | None = Field(
        default=None, description="Readable x-axis measure, including known units."
    )
    y_label: ChartText | None = Field(
        default=None,
        description="Readable y-axis measure, including known units; counts and means are labeled automatically.",
    )
    group_label: ChartText | None = Field(
        default=None, description="Readable title for the grouping legend."
    )

    @model_validator(mode="after")
    def validate_group_label(self) -> "ChartInput":
        if self.group_label is not None and self.group is None:
            raise ValueError("group_label requires a group column")
        return self

    @property
    def columns(self) -> list[str]:
        # registry sjekker bare et felt som heter columns, så x/y/group samles her
        names = [self.x]
        if self.y is not None:
            names.append(self.y)
        if self.group is not None:
            names.append(self.group)
        return names

    @property
    def numeric_columns(self) -> list[str]:
        return []


class BarChartInput(ChartInput):
    @property
    def numeric_columns(self) -> list[str]:
        return [self.y] if self.y is not None else []


class HistogramInput(ChartInput):
    y: None = None

    @property
    def numeric_columns(self) -> list[str]:
        return [self.x]


class AxesInput(ChartInput):
    y: str = Field(min_length=1)


class YNumericAxesInput(AxesInput):
    @property
    def numeric_columns(self) -> list[str]:
        return [self.y]


class XYNumericAxesInput(AxesInput):
    @property
    def numeric_columns(self) -> list[str]:
        return [self.x, self.y]


class BoxPlotInput(YNumericAxesInput):
    group: None = None


class HeatmapInput(AxesInput):
    group: None = None


def parse_chart(model: type[ChartInput], kwargs: dict[str, object]) -> ChartInput:
    # execute_step dytter inn random_state etter validering, den hører ikke til diagrammet
    skipped = {"_source_rows", "_source_sample_size", "random_state", "output_dir"}
    payload = {key: value for key, value in kwargs.items() if key not in skipped}
    return model.model_validate(payload)
