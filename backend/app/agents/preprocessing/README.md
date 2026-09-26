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

For a non-empty CSV plan, the agent executes registered tools in the order
provided by the plan. The current tools are `handle_missing_values` with
`drop_rows` or `fill` strategies, `convert_types` for integer, float, string,
or boolean values, and `remove_duplicates` with optional key columns. Unknown
tools, columns, strategies, and invalid conversions are rejected.

Each non-empty run writes a derived CSV, creates a new content-addressed
dataset version, and records the input version as its parent. The raw input
file is never overwritten.

## File Structure

```text
backend/app/agents/preprocessing/
├── __init__.py
├── README.md
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

Contains the behavior instructions for a future model-backed preprocessing
agent. It defines the role boundary, dataset immutability rules, permitted
operations, error behavior, output contract, and final verification checklist.

The prompt explicitly states that:

- raw datasets are immutable;
- only registered tools may be used;
- unsupported steps must be rejected;
- preprocessing must not perform analysis;
- the harness controls workflow behavior;
- outputs must conform to `PreprocessingOutput`.

The prompt is instruction text. It is not executed by the current deterministic
node.

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

The preprocessing node receives these steps but does not currently execute
non-empty steps because the tool registry and transformation tools are not yet
part of this implementation.

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

Dependency graph validation and tool argument validation belong to the plan
validation and registry layers. They are not duplicated inside the no-op node.

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
5. Non-empty plans are rejected until tools exist.
6. The typed node input produces a typed output.

The intended test command from the repository documentation is:

```bash
uv run --project backend pytest backend/tests
```

The local environment used during implementation did not have `uv` or
`pytest` available, so the focused test suite could not be run there. The
following checks did pass:

```bash
python3 -m compileall -q \
  backend/app/agents/preprocessing \
  backend/tests/test_preprocessing_agent.py
```

A direct runtime smoke test also passed for:

- importing the preprocessing package;
- constructing a `DatasetReference`;
- executing an empty preprocessing plan;
- preserving the dataset reference;
- returning `no_changes=True`;
- rejecting a non-empty unsupported step.

Editor diagnostics reported no errors in the preprocessing node, schemas, or
tests.

## Dependency Note

`pydantic>=2.0` was added to `backend/pyproject.toml` because the shared and
agent-specific contracts use Pydantic models.

The repository declares Python 3.12 or newer. The available local `python3`
interpreter was older, so optional annotations in the shared models use a
compatibility-friendly form where needed.

## What This Does Not Implement Yet

The following are intentionally outside the current milestone:

- tool registry integration;
- `handle_missing_values`;
- `remove_duplicates`;
- `change_datatypes`;
- `filter_rows`;
- `select_columns`;
- dataset file reading and writing;
- content-hash generation for processed data;
- processed dataset version generation;
- persistent dataset storage;
- artifact storage;
- LangGraph node registration;
- retries and checkpointing;
- preprocessing failure models;
- API endpoints;
- model calls.

Do not add these implicitly to the no-op node. They should be introduced as
separate, tested changes behind explicit interfaces.

## Recommended Next Implementation Steps

When the team is ready to continue preprocessing, use this order:

### 1. Confirm shared contracts

Coordinate with whoever owns Phase 1. Avoid creating duplicate versions of
`DatasetReference`, `PlanStep`, and `PreprocessingReport`. Adapt imports if the
team's final shared model locations or field names change.

### 2. Add the tool interface and registry

The node should receive a registry abstraction rather than importing concrete
transformation functions directly. The registry must validate:

- tool name;
- input arguments;
- approved dataset access;
- output type;
- dependency behavior.

### 3. Add dataset storage

Introduce a `DatasetStore` abstraction with operations for reading references,
saving processed versions, and verifying hashes. The raw file must remain
untouched.

### 4. Implement one transformation at a time

Recommended first tool: `remove_duplicates` or
`handle_missing_values`. Each tool should have:

- an input model;
- an output model;
- deterministic execution;
- a new dataset version;
- a `PreprocessingChange` record;
- warnings where relevant;
- success and failure tests.

### 5. Execute dependencies explicitly

Replace the current empty-plan guard with dependency ordering only after the
registry and tool contracts exist. A failed dependency must prevent downstream
steps from running.

### 6. Add failure contracts

Use structured errors that identify the node, step, category, message, and
retryability. Keep stack traces and storage paths out of user-facing output.

### 7. Integrate with LangGraph

Register the preprocessing node with the harness only after its standalone
contract tests pass. LangGraph should own routing, retries, step limits, and
checkpointing.

## Ownership and Non-Overlap Checklist

This work should be considered preprocessing-specific when reviewing changes.

### Files owned by this work

- `backend/app/agents/preprocessing/prompt.md`
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
├── prompt.md   # behavior and boundaries
├── node.py     # deterministic execution entry point
└── schemas.py  # typed input and output
```

It is safe to use for the no-op Phase 4 contract. It is not yet a general
preprocessing engine. The next contributor should add registered transformation
tools and dataset version storage without changing the agent's ownership
boundary or silently mutating raw data.
