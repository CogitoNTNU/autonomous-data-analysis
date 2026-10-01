# Running the project

This guide describes the runnable parts of the project on the current branch.
Run every command from the repository root unless noted otherwise.

## Current scope

The currently integrated workflow is:

```text
Planner -> Preprocessing -> Analysis
```

The repository does not yet contain the LangGraph harness, interpretation,
critic, chat, HTTP API, or frontend application. The live smoke test below is
therefore the closest available end-to-end run.

## Prerequisites

- Python 3.12.13
- uv 0.11.21 or a compatible version

Install the backend dependencies:

```bash
uv sync --project backend
```

There is no need to activate a virtual environment. `uv` creates and uses
`backend/.venv` for the backend project.

## Run the automated tests

Run the complete backend test suite:

```bash
uv run --project backend pytest -q backend/tests
```

Run the deterministic Planner -> Preprocessing -> Analysis integration test:

```bash
uv run --project backend pytest -q backend/tests/test_preprocessing_workflow.py
```

Run only the group aggregation tests:

```bash
uv run --project backend pytest -q backend/tests/test_group_aggregate.py
```

Run the visualization tests:

```bash
uv run --project backend pytest -q backend/tests/test_visualization.py
```

The visualization tools write PNG artifacts under `backend/data/artifacts/`.
Generated PNG files are ignored by Git.

## Inspect an example dataset

Inspect the included penguins dataset:

```bash
uv run --project backend python -m backend.app.tools.inspect_dataset
```

## Run the live workflow

The live Planner requires access to the NTNU/IDUN LLM endpoint. Set one of the
supported API-key environment variables without committing the key to Git:

```bash
export NTNU_LLM_API_KEY="your-key"
```

Run the smoke workflow with the included penguins dataset:

```bash
uv run --project backend python -m backend.scripts.planner_llm_smoke \
  --dataset data/penguins.csv \
  --prompt "Remove rows where body_mass_g is missing, then group by species and calculate the mean body_mass_g for each species."
```

The command prints the generated plan, preprocessing report, analysis results,
and warnings. Always use `python -m backend.scripts.planner_llm_smoke`; running
`backend/scripts/planner_llm_smoke.py` directly does not put the repository root
on Python's import path.

## Run group aggregation directly

This example bypasses the LLM and executes the registered deterministic tool:

```bash
uv run --project backend python - <<'PY'
from pprint import pprint

from backend.app.contracts.models import PlanStep
from backend.app.storage.datasets import create_dataset_reference
from backend.app.tools.analysis.descriptive import default_registry
from backend.app.tools.registry import execute_step

dataset = create_dataset_reference("data/penguins.csv")

step = PlanStep(
    step_id="group-test",
    tool_name="group_aggregate",
    arguments={
        "group_by": ["species"],
        "aggregations": [
            {
                "column": "body_mass_g",
                "function": "mean",
                "alias": "average_body_mass_g",
            }
        ],
    },
)

result = execute_step(step, dataset, default_registry())
pprint(result.model_dump())
PY
```

Supported aggregation functions are `count`, `mean`, `median`, `sum`, `min`,
`max`, and `std`.

## Use another CSV dataset

Dataset access is intentionally restricted. Put CSV files under
`backend/data/` or `backend/tests/fixtures/`.

For example, after adding `backend/data/sales.csv`, use:

```text
--dataset data/sales.csv
```

When running a tool directly, create its reference with:

```python
dataset = create_dataset_reference("data/sales.csv")
```

Use the CSV's exact column names in the prompt or tool arguments. Numeric
aggregations require a column inferred as `integer` or `float`.

## Troubleshooting

### `ModuleNotFoundError: No module named 'backend'`

Run scripts as modules from the repository root:

```bash
uv run --project backend python -m backend.scripts.planner_llm_smoke --help
```

Do not run `python backend/scripts/planner_llm_smoke.py` directly.

### `VIRTUAL_ENV` does not match `backend/.venv`

An unrelated environment is active. Exit it and let uv select the backend
environment:

```bash
deactivate
uv run --project backend pytest -q backend/tests
```

### Missing API key

If the live workflow reports `Set NTNU_LLM_API_KEY or IDUN_API_KEY`, export a
valid key before running it:

```bash
export NTNU_LLM_API_KEY="your-key"
```

The deterministic automated tests and direct analysis tools do not require an
API key.
