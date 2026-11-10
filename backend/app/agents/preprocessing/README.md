# Preprocessing executor

Preprocessing executes the validated preprocessing steps produced by Planner.
It uses deterministic CSV tools, preserves the source file, and returns a
processed dataset reference and a report. LangGraph controls routing, retries,
checkpointing, and limits; the browser workflow runs without stage approvals.

## Workflow contract

[`preprocessing_node(state)`](workflow.py) reads the registered dataset and
`plan.preprocessing_steps` from `AgentState`. It returns
`AgentResponse[PreprocessingUpdates]` containing `processed_dataset`,
`preprocessing_report`, and warnings. A missing plan returns a nonretryable
`INVALID_DATA` error.

```python
from backend.app.agents.preprocessing import preprocessing_node

# state is a validated AgentState containing a dataset and plan.
response = preprocessing_node(state)
if response.status == "success":
    processed_dataset = response.updates.processed_dataset
    report = response.updates.preprocessing_report
```

[`workflow.py`](workflow.py) converts the shared contracts in
[`app/contracts/`](../../contracts/) into the executor's local contracts in
[`app/models/`](../../models/), then maps the output back. The graph adapter in
[`app/graph/nodes.py`](../../graph/nodes.py) merges the typed response into state.
Analysis consumes the processed dataset and the plan's analysis steps.

Analysis steps may depend on completed preprocessing steps. Preprocessing steps
cannot depend on analysis steps. The shared registry validates tool phases,
arguments, and referenced columns before a plan is accepted.

## Execution and tools

The registered operations are `handle_missing_values`, `remove_duplicates`,
`change_datatypes`, `encode_categorical`, `scale_features`, `filter_rows`,
`select_columns`, `normalize_values`, and `handle_outliers`.

Nonempty plans execute in dependency order and write a derived CSV with a
content-based version and a parent-version reference. The report records each
step, affected columns, row counts, quality warnings, and whether values changed.
An empty plan preserves the local input reference and version, creates no file,
and reports `no_changes=True`.

| Module                                                         | Responsibility                                        |
| -------------------------------------------------------------- | ----------------------------------------------------- |
| [node.py](node.py)                                             | Deterministic execution and dependency resolution     |
| [schemas.py](schemas.py)                                       | `PreprocessingInput` and `PreprocessingOutput`        |
| [workflow.py](workflow.py)                                     | Shared-state contract conversion and error responses  |
| [registry.py](registry.py)                                     | Registration with the shared ToolRegistry             |
| [tools/preprocessing_tools/](../../tools/preprocessing_tools/) | Argument validation, transformations, and CSV storage |
| [idun.py](idun.py), [prompt.md](prompt.md)                     | Legacy standalone plan generator                      |

Keep transformations in the relevant tool module (`cleaning.py`,
`row_operations.py`, or `features.py`). CSV loading, writing, hashing, and
metadata inference belong in `csv_dataset.py`. The older
`tools/preprocessing.py` module remains a compatibility facade.

## Direct executor contract

`run_preprocessing(input_data: PreprocessingInput) -> PreprocessingOutput`
accepts a local `DatasetReference` and a list of local `PlanStep` models.
`steps` defaults to an empty list. Output contains `processed_dataset` and
`report`; complete data remains in external CSV storage.

```python
from backend.app.agents.preprocessing import PreprocessingInput, run_preprocessing

# dataset is a local app.models.dataset.DatasetReference for an approved CSV.
result = run_preprocessing(PreprocessingInput(dataset=dataset, steps=[]))
assert result.processed_dataset is dataset
assert result.report.no_changes
```

`PreprocessingAgent().run(dataset, steps)` provides the same execution through
an older object-style API. Its optional `plan(dataset, request)` method uses
`IdunPreprocessingPlanner` to propose local steps; the main workflow uses the
shared Planner instead. Standalone callers inspect the proposed steps before
passing them to `run`. This legacy planner reads `IDUN_API_KEY`, with optional
`IDUN_MODEL` and `IDUN_BASE_URL`, from its environment. See the
[running guide](../../../../RUNNING.md#start-the-local-app) for loading a root
`.env` file with `uv run --env-file .env`.

## Errors

Duplicate step IDs, unknown dependencies, cycles, unsupported formats, unknown
tools, invalid arguments, and invalid columns fail explicitly. A tool rejection
raises `PreprocessingStepError` with its step ID, tool name, and structured
reason. The workflow adapter maps validation and unavailable-data failures to
nonretryable `INVALID_DATA`; storage permission errors become `TOOL_FAILURE`.
Repairable step failures carry Planner repair metadata for LangGraph routing.
The executor does not select replacement tools or silently change the plan.

## Tests

From the repository root:

```bash
uv run --project backend pytest -q backend/tests/test_preprocessing_agent.py backend/tests/test_preprocessing_workflow.py
```

These tests cover empty plans, transformations, immutable source files, derived
versions, dependency validation, and the handoff to Analysis using model fakes.
The legacy Idun live test is opt-in: export `IDUN_API_KEY` and set
`RUN_IDUN_INTEGRATION=1` when running `test_preprocessing_agent.py -k idun`.
See the [running guide](../../../../RUNNING.md#run-the-automated-tests) for the
complete backend and frontend checks.
