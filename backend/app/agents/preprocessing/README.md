# Preprocessing Agent

This document records the preprocessing agent implementation in this repository.
It is intended to make the work easy to review, continue, hand off, and keep
separate from the Planner, Analysis, Interpretation, Critic, and Chat agents.

## Ownership Boundary

This implementation belongs to the **Preprocessing Agent**.

The agent receives a dataset reference and a validated list of preprocessing
steps. It returns a processed dataset reference and a preprocessing report.

The agent does not:

- understand or rewrite the user's analytical question;
- create analysis plans;
- choose statistical methods;
- calculate statistics;
- interpret results;
- critique conclusions;
- control the complete workflow;
- manage LangGraph routing, retries, checkpoints, or interrupts;
- execute arbitrary Python, SQL, or filesystem operations.

The harness is responsible for workflow control. Registered tools are
responsible for deterministic data transformations.

## What Was Implemented

The current implementation executes validated CSV preprocessing steps and also
supports the case where a valid plan contains no preprocessing steps.

For an empty plan, the agent:

1. Accepts a `DatasetReference`.
2. Preserves the exact input dataset reference.
3. Does not create or modify a dataset file.
4. Keeps the dataset version unchanged.
5. Keeps the row count unchanged.
6. Returns an empty list of changes.
7. Returns an empty list of affected columns.
8. Sets `no_changes` to `true`.
9. Returns the result using Pydantic models.

For a non-empty CSV plan, the agent validates registered tool arguments and
executes steps in dependency order. The nine canonical tools are
`handle_missing_values`, `remove_duplicates`, `change_datatypes`,
`encode_categorical`, `scale_features`, `filter_rows`, `select_columns`,
`normalize_values`, and `handle_outliers`.
Unknown tools, columns, invalid arguments, unsupported conversions, missing
dependencies, and dependency cycles are rejected.

Datatype conversion supports integer, float, string, boolean, date, and
currency values. Numeric conversion recognizes common currency symbols and
comma/dot separators; date conversion accepts common formats including
day-first numeric dates. `normalize_values` trims and collapses whitespace,
applies case rules, and supports explicit case-insensitive value maps.

Each non-empty run writes a derived CSV, creates a new content-addressed
dataset version, and records the input version as its parent. The raw input
file is never overwritten.

## File Structure

```text
backend/app/tools/
├── preprocessing.py                 # Backward-compatible public exports
└── preprocessing_tools/
    ├── core.py                       # Shared contracts, schemas, constants
    ├── cleaning.py                   # Missing values, normalization, types
    ├── row_operations.py              # Filtering, duplicate/column selection
    ├── features.py                    # Encoding, scaling, outlier handling
    ├── csv_dataset.py                 # CSV I/O and metadata
    ├── registry.py                    # Validated dispatch and tool registry
    └── __init__.py                    # Public exports

backend/app/agents/preprocessing/
├── __init__.py
├── README.md
├── idun.py
├── node.py
├── prompt.md
└── schemas.py
```

Related shared contracts and tests are located here:

```text
backend/app/models/
├── __init__.py
├── dataset.py
├── plan.py
└── results.py

backend/tests/
└── test_preprocessing_agent.py
```

## File Responsibilities

### `prompt.md`

Contains the behavior instructions for the Idun-backed plan generator. It
defines the role boundary and argument contracts for each registered
preprocessing operation.

The prompt explicitly states that:

- raw datasets are immutable;
- only registered tools may be used;
- unsupported steps must be rejected;
- preprocessing must not perform analysis;
- the harness controls workflow behavior;
- outputs must conform to `PreprocessingOutput`.

The model proposes steps only; the local executor validates and runs them.

### `schemas.py`

Defines the preprocessing-specific input and output models:

- `PreprocessingInput`
- `PreprocessingOutput`

`PreprocessingInput` contains:

```python
class PreprocessingInput(BaseModel):
    dataset: DatasetReference
    steps: list[PlanStep]
```

`steps` defaults to an empty list. The `from_values` class method keeps the
public Python API convenient while ensuring the sequence is converted into a
validated list.

`PreprocessingOutput` contains:

```python
class PreprocessingOutput(BaseModel):
    processed_dataset: DatasetReference
    report: PreprocessingReport
```

### Tool module ownership

Put shared argument schemas and low-level validation in
`backend/app/tools/preprocessing_tools/core.py`. Add a transformation to the
closest domain module (`cleaning.py`, `row_operations.py`, or `features.py`),
then register its argument model and callable in `registry.py` and export it
from `preprocessing_tools/__init__.py`. Keep file loading, derived CSV writing,
hashing, and metadata inference in `csv_dataset.py`.

`backend/app/tools/preprocessing.py` remains as a compatibility facade for
older imports. New internal code should import from `preprocessing_tools`.

### `node.py`

Contains the deterministic execution logic:

- `run_preprocessing(input_data)` is the node-style entry point.
- `PreprocessingAgent.run(dataset, steps)` is a compatibility facade for the
  earlier object-style API.

The compatibility facade is kept so existing imports and tests do not break
while the package adopts the `prompt.md`, `node.py`, and `schemas.py` layout.

### `__init__.py`

Exports the public preprocessing API:

```python
from backend.app.agents.preprocessing import (
    PreprocessingAgent,
    PreprocessingInput,
    PreprocessingOutput,
    run_preprocessing,
)
```

### `backend/app/models/dataset.py`

Contains shared dataset contracts:

- `ColumnMetadata`
- `DatasetMetadata`
- `DatasetReference`

`DatasetReference` points to data rather than storing the complete dataset.
It contains the dataset identity, version, URI, format, content hash, parent
version, and metadata.

### `backend/app/models/plan.py`

Contains the shared `PlanStep` contract. A step identifies a tool, its
arguments, and any dependencies.

The deterministic node executes registered steps through the local CSV tools.
The optional Idun planner proposes steps from a request and dataset schema;
callers can inspect them before passing them to `PreprocessingAgent.run`.

### `backend/app/models/results.py`

Contains preprocessing result contracts:

- `PreprocessingChange`
- `PreprocessingReport`
- `PreprocessingResult`

The agent-specific `PreprocessingOutput` wraps the same result information in
the `node.py` interface.

## Data Flow

```text
validated DatasetReference + PlanStep list
                    |
                    v
          PreprocessingInput
                    |
                    v
          run_preprocessing()
                    |
       +------------+------------+
       |                         |
   empty steps              non-empty steps
       |                         |
       v                         v
 preserve input          execute registered tools
 reference and report    and create derived reference
       |                         |
       +------------+------------+
                    v
            PreprocessingOutput
```

For the supported empty-plan path:

```text
input_dataset.version == output_dataset.version
input_dataset is output_dataset
rows_before == rows_after
changes == []
affected_columns == []
no_changes == True
```

## Contract Details

### Dataset reference

The current shared contract is:

```python
DatasetReference(
    dataset_id: str,
    version: str,
    uri: str,
    format: Literal["csv", "parquet", "database"],
    content_hash: str,
    parent_version: str | None,
    metadata: DatasetMetadata,
)
```

The model is configured as frozen. The preprocessing agent therefore treats
the reference as immutable and returns the same reference for the no-op path.

### Dataset metadata

The no-op agent uses `metadata.row_count` to populate both report row counts.
It does not inspect the underlying CSV or calculate any new metadata.

### Plan step

A plan step contains:

```python
PlanStep(
    step_id: str,
    tool_name: str,
    arguments: dict[str, Any],
    depends_on: list[str],
)
```

The executor rejects duplicate step IDs, unknown dependencies, and cycles. It
executes valid steps in dependency order, validates tool arguments with
Pydantic models, and propagates updated column names between steps.

### Preprocessing report

The no-op report contains:

```python
PreprocessingReport(
    input_dataset_version=dataset.version,
    output_dataset_version=dataset.version,
    changes=[],
    affected_columns=[],
    rows_before=dataset.metadata.row_count,
    rows_after=dataset.metadata.row_count,
    quality_warnings=[],
    no_changes=True,
)
```

This makes the absence of preprocessing explicit and auditable.

## Public Usage

### Object-style API

```python
from backend.app.agents.preprocessing import PreprocessingAgent

result = PreprocessingAgent().run(dataset, steps=[])
```

### Idun planning

Set `IDUN_API_KEY` in the shell and optionally set `IDUN_MODEL` or
`IDUN_BASE_URL`. The defaults are `openai/gpt-oss-120b` and
`https://llm.hpc.ntnu.no/v1`.

```python
from backend.app.agents.preprocessing import PreprocessingAgent

agent = PreprocessingAgent()
steps = agent.plan(dataset, "Drop rows missing bill_length_mm or sex.")
# Inspect or approve the proposed PlanStep list before execution.
result = agent.run(dataset, steps)
```

The planner sends column names and aggregate metadata, not CSV rows. Only the
registered preprocessing tool names are accepted, and execution stays local.
The plan request requires NTNU network or VPN access.

### Node-style API

```python
from backend.app.agents.preprocessing import (
    PreprocessingInput,
    run_preprocessing,
)

input_data = PreprocessingInput(dataset=dataset, steps=[])
result = run_preprocessing(input_data)
```

### Reading the result

```python
result.processed_dataset
result.report.input_dataset_version
result.report.output_dataset_version
result.report.rows_before
result.report.rows_after
result.report.changes
result.report.affected_columns
result.report.quality_warnings
result.report.no_changes
```

## Current Tests

The focused test file is:

```text
backend/tests/test_preprocessing_agent.py
```

It covers:

1. Empty plans preserve the exact dataset object.
2. The input and output versions remain equal.
3. Row counts remain unchanged.
4. No changes are recorded for an empty plan.
5. Each canonical preprocessing tool is exercised against a CSV.
6. Transformations that add or remove columns propagate their headers.
7. Source files remain unchanged and results use derived dataset versions.
8. Dependency ordering and invalid plans are checked.
9. Mocked Idun tool calls produce validated steps without sending CSV row data.

The intended test command from the repository documentation is:

```bash
uv run --project backend pytest backend/tests
```

To call Idun as part of the opt-in live integration test, first export
`IDUN_API_KEY`, then run:

```bash
RUN_IDUN_INTEGRATION=1 uv run --project backend pytest \
    backend/tests/test_preprocessing_agent.py -k idun -q
```

The normal test suite does not call Idun. The live request is opt-in and
requires `IDUN_API_KEY`, NTNU network access or VPN, and
`RUN_IDUN_INTEGRATION=1`.

## Dependency Note

`pydantic>=2.0` provides the shared and agent-specific data contracts.
`openai>=1.0` provides the OpenAI-compatible Idun API client.

The repository declares Python 3.12 or newer.

## What This Does Not Implement Yet

The following are outside this preprocessing-agent milestone:

- LangGraph node registration;
- retries and checkpointing;
- API endpoints;
- human approval UI for proposed plans.

Idun proposes plans only. The caller remains responsible for reviewing the
steps before passing them to the deterministic executor.

## Remaining Work

- Register the preprocessing node in the LangGraph workflow.
- Add a user-facing approval step before running model-proposed plans.
- Replace local derived-file storage with persistent dataset storage if needed.

## Ownership and Non-Overlap Checklist

This work should be considered preprocessing-specific when reviewing changes.

### Files owned by this work

- `backend/app/agents/preprocessing/prompt.md`
- `backend/app/agents/preprocessing/idun.py`
- `backend/app/agents/preprocessing/node.py`
- `backend/app/agents/preprocessing/schemas.py`
- `backend/app/agents/preprocessing/__init__.py`
- `backend/tests/test_preprocessing_agent.py`

### Shared files touched

- `backend/app/models/dataset.py`
- `backend/app/models/plan.py`
- `backend/app/models/results.py`
- `backend/pyproject.toml`

These shared files may overlap with the teammate implementing Phase 1
contracts. Coordinate before merging conflicting model definitions.

### Files not implemented here

- Planner prompt, node, or schemas;
- Analysis prompt, node, or schemas;
- Interpretation prompt, node, or schemas;
- Critic prompt, node, or schemas;
- Chat prompt, node, or schemas;
- LangGraph graph builder;
- API routes;
- frontend code.

## Handoff Summary

The preprocessing package now has the requested agent shape:

```text
preprocessing/
├── prompt.md   # Idun plan-generation instructions
├── idun.py     # API client and validated plan generation
├── node.py     # deterministic execution entry point
└── schemas.py  # typed input and output
```

Idun proposes plans only. Callers can inspect `PlanStep`s and then pass them to
the deterministic executor; the source CSV is never overwritten.
