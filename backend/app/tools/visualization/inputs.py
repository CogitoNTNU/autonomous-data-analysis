"""Shared chart inputs. `columns` is what the registry checks before a call."""

from pydantic import BaseModel, ConfigDict, Field

DTYPES = frozenset({"string", "integer", "float"})


class ChartInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    x: str = Field(min_length=1)
    y: str | None = None
    group: str | None = None
    source_result_id: str | None = None

    @property
    def columns(self) -> list[str]:
        # registry sjekker bare et felt som heter columns, så x/y/group samles her
        names = [self.x]
        if self.y is not None:
            names.append(self.y)
        if self.group is not None:
            names.append(self.group)
        return names


class AxesInput(ChartInput):
    y: str = Field(min_length=1)


def parse_chart(model: type[ChartInput], kwargs: dict[str, object]) -> ChartInput:
    # execute_step dytter inn random_state etter validering, den hører ikke til diagrammet
    skipped = {"_source_rows", "random_state", "output_dir"}
    payload = {key: value for key, value in kwargs.items() if key not in skipped}
    return model.model_validate(payload)
