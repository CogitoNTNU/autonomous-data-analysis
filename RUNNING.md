# Running the project

Run every command from the repository root unless noted otherwise.

## Current scope

The browser uploads a CSV, then LangGraph coordinates the complete workflow:

```text
Planner -> Preprocessing -> Analysis -> Interpretation -> Critic -> Chat
```

The Planner can ask for clarification. Critic revisions run automatically within
bounded limits. A completed analysis supports follow-up discussion and new
analysis rounds in the same conversation.

## Prerequisites

- Python 3.12.13
- uv 0.11.21 or a compatible version
- Node.js 22.12 or newer and npm

Install dependencies:

```bash
uv sync --project backend
npm --prefix frontend ci
```

There is no need to activate a virtual environment. `uv` creates and uses
`backend/.venv` for the backend project.

## Start the local app

The reasoning agents need a valid NTNU/IDUN API key and access to the model
endpoint, which may require the NTNU network or VPN. Put the backend settings
in a local `.env` file at the repository root; this file is ignored by Git:

```dotenv
NTNU_LLM_API_KEY=your-key
NTNU_LLM_BASE_URL=https://llm.hpc.ntnu.no/v1
NTNU_LLM_MODEL=openai/gpt-oss-120b
```

`IDUN_API_KEY` is also accepted by the web server. Keep credentials in the
backend environment; they do not belong in frontend code or `VITE_*` variables.
See [Backend model settings](backend/README.md#model-latency-and-request-budgets)
for timeout and completion-budget controls.

In one terminal, start the backend:

```bash
uv run --project backend --env-file .env python -m backend.app.api.planner_server
```

In a second terminal, start the frontend:

```bash
npm --prefix frontend run dev -- --port 5173 --strictPort
```

Open [http://localhost:5173](http://localhost:5173). The frontend's Vite proxy
sends `/api` calls to the backend on `127.0.0.1:8000`. Keep both terminals
running. If settings are already exported, omit `--env-file .env`; if the file
is elsewhere, pass its actual path. Restart the backend after changing model
settings.

## Demo walkthrough

The included `backend/data/demo_sales/sales_dirty.csv` is synthetic sales data
with 10,100 rows, 11 columns, 100 exact duplicates, missing values, and injected
data-quality defects. Amounts use fictional currency units. The adjacent
`manifest.json` records the expected source-data properties.

1. Upload `sales_dirty.csv` and check the preview shows the expected dimensions.
1. Ask: "Remove duplicate rows, summarize revenue and profit, and show a histogram
   of revenue. Leave other values unchanged."
1. If asked for clarification, answer in the message field. Let the workflow
   reach its final answer; expand the stage cards to inspect its plan, cleaning,
   calculated results, and review.
1. Open the chart to verify its title, axis labels, and explanation. Check the
   final answer's warnings and **Explore further** questions.
1. Select **Explain the most important finding** to demonstrate an evidence-based
   follow-up reply. Then ask "Compare total revenue by region and show a bar chart.
   Remove exact duplicates first and report missing region values." to start a new
   analysis round when new calculations are needed.

This fixture demonstrates cleaning and descriptive analysis. Its independently
injected defects are not evidence of returns, causation, or genuine business
trends. Model calls can take time or fail if the endpoint is unavailable; check
the backend's structured node-duration and error logs when diagnosing a run.

The current browser workspace is a local prototype. Reloading the page clears
its in-memory conversation, and the **Recent** list does not restore saved runs.
Keep the demo tab open. **New analysis** clears the conversation while retaining
the selected dataset; **Replace dataset** loads a different CSV. Closing or
replacing the browser conversation stops polling but does not cancel backend
work already in progress. Backend checkpoints and uploaded data persist under
`backend/data/uploads/`; an interrupted run is reported explicitly after a
server restart. See [workflow persistence](backend/README.md#chat-workflow-api).

## Run the automated tests

Run the complete backend test suite:

```bash
uv lock --project backend --check
uv run --project backend pytest -q backend/tests
```

Check the frontend:

```bash
npm --prefix frontend run typecheck
npm --prefix frontend test
npm --prefix frontend run build
```

These checks use deterministic tools and model fakes; no API key is required.
The production frontend build still needs a persistent backend behind `/api`.
Vite's development proxy is not part of the static build.

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

For a command-line check of the Planner, Preprocessing, and Analysis stages,
run the smoke workflow with the included penguins dataset and the same local
model settings:

```bash
uv run --project backend --env-file .env python -m backend.scripts.planner_llm_smoke \
  --dataset data/penguins.csv \
  --prompt "Remove rows where body_mass_g is missing, then group by species and calculate the mean body_mass_g for each species."
```

The command prints the generated plan, preprocessing report, analysis results,
and warnings. It does not exercise the browser or follow-up dialogue. For
additional full-graph smoke tests, see [Backend scripts](backend/scripts/README.md).
Always use `python -m backend.scripts.planner_llm_smoke`; running
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

The browser accepts CSV uploads up to 10 MB and registers them in backend
storage. For direct Python tools and smoke scripts, dataset access is
restricted to `backend/data/` and `backend/tests/fixtures/`.

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

If the live workflow reports a missing API key, check that the launcher loaded
the intended `.env` file, or export a valid key before starting the backend:

```bash
export NTNU_LLM_API_KEY="your-key"
```

The deterministic automated tests and direct analysis tools do not require an
API key.

### Frontend proxy errors

Check that the backend is still running on port 8000. Start it before asking a
question. Use the frontend URL printed by Vite; the backend has no standalone
browser interface at its root URL.

### Port already in use

Reuse the running instance or stop its terminal with Ctrl-C before restarting.
The frontend command above uses `--strictPort` to avoid silently moving the demo
to a different port.
