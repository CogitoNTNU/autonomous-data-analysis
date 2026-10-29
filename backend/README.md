# Backend

Python agents, analysis tools, tests, and example data live here.

```text
backend/
├── app/       # Application and agent code
├── data/      # Local example datasets
├── tests/     # Backend tests
├── pyproject.toml
└── uv.lock
```

From the repository root, install dependencies with `uv sync --project backend`.

## Chat workflow API

Start the persistent backend from the repository root:

```bash
uv run --project backend --env-file .env python -m backend.app.api.planner_server
```

Start the frontend with `npm --prefix frontend run dev`. The Vite proxy sends
`/api` requests to the backend on port 8000.

The chat uses one LangGraph run for the complete analysis. Planner, Preprocessing,
Analysis, Interpretation, Critic, and final Chat presentation run automatically.
Critic revisions and transient retries follow the harness routing and budgets.
The final answer opens automatically; no stage approval is required.

| Endpoint                     | JSON body                           | Purpose                                                    |
| ---------------------------- | ----------------------------------- | ---------------------------------------------------------- |
| `POST /api/datasets`         | Raw CSV body (`text/csv`)           | Register an immutable dataset                              |
| `POST /api/workflows`        | `dataset_id`, `question`            | Start a background run and return its ID and snapshot      |
| `POST /api/workflows/status` | `run_id`                            | Read persisted progress, results, charts, and final answer |
| `POST /api/workflows/resume` | `run_id`, `checkpoint_id`, `answer` | Answer a pending Planner clarification in the same run     |

The browser polls status while the run is active. The run reads the registered
CSV from backend storage; a start or resume request cannot replace its contents. It never posts plans, calculated
results, interpretations, or critique decisions back into the harness. A snapshot
replaces the previous view so a revision cannot leave stale dependent outputs on
screen. Clarification is the only user interrupt and is limited to three replies.
A stale or duplicate clarification submission is rejected.

SQLite checkpoints and per-run worker locks live under
`backend/data/uploads/.workflows/`. This directory is ignored by Git. Completed
runs and pending clarifications survive backend restarts. If the backend exits
mid-execution, status reports an interrupted run explicitly; it does not silently
repeat tool executions. Closing or replacing a chat stops browser polling but does
not cancel an already executing backend run.

Deployment requires a long-running backend with durable local storage for both
checkpoints and datasets. Vercel's ephemeral Python functions cannot keep these
background workers or files alive across requests. Host the frontend on Vercel
and proxy `/api/datasets` and `/api/workflows*` to the persistent backend; the
bundled workflow functions return an explicit 503 until this routing is configured.
The earlier individual-agent endpoints remain for compatibility, but the chat no
longer uses them.

## Model latency and request budgets

All three LLM adapters read the same validated settings. SDK retries are disabled;
LangGraph owns retries, with one retry for transient failures in a web run. A
failed Interpretation retry reuses its client and calculated evidence; it does
not repeat preprocessing or analysis.

| Setting                     | Default                       | Meaning                                                                      |
| --------------------------- | ----------------------------- | ---------------------------------------------------------------------------- |
| `NTNU_LLM_TIMEOUT_SECONDS`  | `120`                         | Timeout for model HTTP operations, including the response read               |
| `NTNU_LLM_MAX_TOKENS`       | `4096`                        | Completion budget, including generated reasoning where supported             |
| `NTNU_LLM_REASONING_EFFORT` | `low` for GLM-5.3 and GPT-OSS | Reasoning effort; other model families receive no override unless configured |

GLM-5.3 defaults to maximum reasoning when effort is omitted; its supported
values are `low`, `high`, and `max` (see the
[model card](https://huggingface.co/Inferact/GLM-5.3-NVFP4#note)). Low effort is
appropriate for explaining already calculated results and reviewing them. The
application preserves evidence and required limitations. A response cut short by
the completion budget still fails validation explicitly; it is never presented
as a complete answer. These request controls do not remove provider queueing.

The backend console logs JSON events with run ID, agent, attempt number, duration,
and error category. Look for `workflow.node_started` and
`workflow.node_finished` to distinguish model latency from repeated attempts.
Prompts, raw data, and credentials are excluded from these timing records.
Restart the backend after changing environment settings.

## Counts in grouped results and charts

`group_aggregate` reports the number of source observations as `sample_size`,
the number of output groups as `group_count`, and row counts for each group as
`group_sizes` (aligned with `groups`). Group row counts are not per-column
nonmissing counts. A chart consuming those groups retains the source
`sample_size` and records its aggregate input rows separately as `input_row_count`.
A three-bar chart based on 342 observations therefore reports 342 observations,
not a sample of three. Data-quality warnings use the observation count.

The browser displays the calculated group table and available group counts in
the Analysis details and final answer. Interpretation and Critic constrain group
comparisons to the observed groups; descriptive differences alone do not imply
statistical significance. Workflow execution is partial only when steps failed
or were skipped; result warnings are preserved separately.
