# Backend

Python agents, analysis tools, tests, and example data live here.

NTNU/IDUN models require the NTNU network or an active NTNU VPN connection.
When the model endpoint cannot be reached, model clients limit each connection
attempt to five seconds (or the configured timeout if shorter), independently
of the generation/read timeout. LangGraph still owns bounded transient retries.
The browser distinguishes network connection failures from slow model generation
and explains the network/VPN requirement. No alternative model or fabricated
answer is substituted when the service is unavailable.

```text
backend/
├── app/       # Application and agent code
├── data/      # Local example datasets
├── tests/     # Backend tests
├── pyproject.toml
└── uv.lock
```

From the repository root, install dependencies with `uv sync --project backend`.

Missing-value questions use the read-only `missing_values_summary` analysis tool.
It accepts a nonempty `columns` list of any datatypes and records missing counts,
observed counts, and missing rates (null for an empty dataset). Plans must contain
an executable preprocessing or analysis step; inspection metadata alone is not
final analysis evidence.

Cleaning-only plans finish from the recorded preprocessing report and still pass
through Interpretation and Critic. Their analysis report has outcome
`not_required`, with no analysis results or completed analysis step IDs.

Charts with aggregation dependencies use the dependent table even when aggregate
aliases match raw column names. An explicit `source_result_id` in a plan must name
a `group_aggregate` dependency step, rather than an invented future result ID.

The web server executes registered analysis tools in spawned worker processes.
The execution deadline includes worker startup; timed-out workers are terminated
and joined before retrying. Injected test registries can use in-process callables;
set `isolate_execution=True` for production registries with importable tool
functions. Tool outputs must have valid execution metadata and finite JSON values.

CSV uploads and preprocessing share blank-line parsing, including BOM headers.
Declared datatype conversions are preserved in output metadata, and analysis
preserves declared text columns when reading CSVs. Existing registered raw uploads
are reused after restart and cannot be overwritten by restoration requests.

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

| Endpoint                           | JSON body                            | Purpose                                                    |
| ---------------------------------- | ------------------------------------ | ---------------------------------------------------------- |
| `POST /api/datasets`               | Raw CSV body (`text/csv`)            | Register an immutable dataset                              |
| `POST /api/workflows`              | `dataset_id`, `question`             | Start a background run and return its ID and snapshot      |
| `POST /api/workflows/status`       | `run_id`                             | Read persisted progress, results, charts, and final answer |
| `POST /api/workflows/resume`       | `run_id`, `checkpoint_id`, `answer`  | Answer a pending Planner clarification in the same run     |
| `POST /api/workflows/messages`     | `run_id`, `checkpoint_id`, `message` | Send a follow-up message to a completed run                |
| `POST /api/workflows/retry-review` | `run_id`, `checkpoint_id`            | Recover a failed review using the saved analysis           |

The browser polls status while the run is active. The run reads the registered
CSV from backend storage; a start or resume request cannot replace its contents. It never posts plans, calculated
results, interpretations, or critique decisions back into the harness. A snapshot
replaces the previous view so a revision cannot leave stale dependent outputs on
screen. Clarification is limited to three replies. A stale or duplicate
clarification or message submission is rejected.

### Follow-up dialogue

A completed run waits for follow-up messages while `accepts_messages` is true.
The Chat agent answers questions about the process and results from the recorded
plan, preprocessing report, results, critique, and revisions. It cannot calculate
anything itself. When a message needs new calculations, the agent writes a
self-contained request and the same run starts a new analysis round on the
source dataset. The previous question, answer, and dialogue become the Planner's
conversation context. The snapshot's `dialogue` and `analysis_round` record the
conversation; each run accepts up to 20 messages. A failed chat reply is
recorded as a failed turn and leaves the completed analysis unchanged.

SQLite checkpoints and per-run worker locks live under
`backend/data/uploads/.workflows/`. This directory is ignored by Git. Completed
runs, pending clarifications, and follow-up dialogue survive backend restarts. If the backend exits
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

All LLM adapters read the same validated settings. SDK retries are disabled;
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

## Analysis and chart reference

See [Descriptive charts and grouped results](../docs/charts.md) for chart labels,
units, aggregation behavior, sample sizes, and interpretation limits.

## Recovering malformed model output and failed Critic reviews

Planner and Critic requests use constrained JSON schemas and validate their output.
Malformed or truncated plans and reviews receive at most two LangGraph-owned format
corrections with safe validation feedback (`RunControl.max_output_repairs`,
maximum three). These corrections preserve the plan, dataset versions, tool
results, and interpretation. They do not consume the methodology revision or
transient retry budget and never substitute an approval. Invalid inputs,
unsupported tools, and plan dependencies are not eligible for format correction.

The Planner can perform at most five inspection rounds and twenty inspection
calls per attempt. Once that budget is used, it receives one final response slot
with tools disabled to return a complete plan or clarification. Generated plan
schemas name only registered execution tools. Exploratory plotting first checks
metadata and favors a compact set of plots using observed, varying measurements.

If the review still fails or the model service is unavailable, the webapp keeps
the analysis and offers **Retry review**. The recovery endpoint
`POST /api/workflows/retry-review` accepts only `run_id` and `checkpoint_id`;
it validates the saved failure and current checkpoint, acquires the per-run
lease, and schedules Critic through LangGraph without rerunning completed stages.
Errors remain recorded in checkpoints, with safe output-validation categories in
structured logs. Answers are presented as completed only after Critic approval.

Warnings accompany the current execution evidence. Replacing a plan, preprocessing
report, or analysis removes warnings owned by the superseded outputs before merging
the new warnings. Interpretation-only revisions retain current warnings. Historical
outputs and warnings remain available in durable checkpoints, rather than being
reinserted into the revised answer.
