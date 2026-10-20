# Critic evaluation

The 12 cases in `critic_eval_cases.py` use synthetic penguin, sales, and website
traffic data. Each domain has two approved and two revise cases. Tests compare
the analysis results with outputs from the project's analysis tools.

| Case                           | Expected decision | Review focus                                    |
| ------------------------------ | ----------------- | ----------------------------------------------- |
| `penguins_units`               | approved          | Unit conversion and number of recorded weights  |
| `penguins_multiple_statistics` | approved          | Median and range                                |
| `penguins_wrong_count`         | revise            | Observed weights versus dataset rows            |
| `penguins_missing_reference`   | revise            | Citation of a result that does not exist        |
| `sales_totals`                 | approved          | Revenue sums and order counts                   |
| `sales_multiple_results`       | approved          | Findings citing different results               |
| `sales_unrelated_reference`    | revise            | Overall statistics cited for regional totals    |
| `sales_unsupported_causality`  | revise            | Causal claim without supporting evidence        |
| `traffic_counts`               | approved          | Channel counts with missing values acknowledged |
| `traffic_proportions`          | approved          | Shares among sessions with recorded channels    |
| `traffic_wrong_denominator`    | revise            | Observed shares applied to all sessions         |
| `traffic_ignored_warning`      | revise            | Warning about missing channels ignored          |

Run local tests without model calls:

```bash
uv run --project backend --no-sync --offline pytest -q backend/tests/unit/scripts/test_critic_eval.py
```

To evaluate against a live model, set `NTNU_LLM_API_KEY` (or `IDUN_API_KEY`).
You can also set `NTNU_LLM_BASE_URL` and `NTNU_LLM_MODEL`. This command calls the LLM:

```bash
uv run --project backend python -m backend.scripts.critic_eval
```

Decision accuracy counts only calls that return a valid critique. A false approval
is an `approved` decision for a case that should be revised; a false revision is
the reverse. Failed calls are reported separately as execution errors. A
`cannot_complete` decision counts as incorrect, but not as a false approval or
false revision. Accuracy is `n/a` if no valid critiques are returned. The script
exits with a nonzero status if any call fails or any decision is incorrect.

Review feedback manually using the printed issues, requested changes, and notes.
If useful, give one point each for identifying the problem, using the supplied
results, proposing a clear correction, and avoiding unnecessary changes (0-4).
Approved cases do not need feedback. The script does not score feedback.

Analysis results sent to the Critic include warnings. Case names, expected
decisions, and review notes are not sent to the model. The Critic is not given
raw data, preprocessing reports, or artifact contents.

## LangGraph LLM smoke test

Run from the repository root with the existing NTNU configuration:

```bash
uv run --project backend --env-file backend/.env python -m backend.scripts.graph_llm_smoke
```

`NTNU_LLM_API_KEY` is required. Optional settings are `NTNU_LLM_BASE_URL`,
`NTNU_LLM_MODEL`, and `NTNU_LLM_TIMEOUT_SECONDS`; defaults come from
`app/core/llm_config.py`. Omit `--env-file backend/.env` if these variables are
already exported. The endpoint may require NTNU network/VPN access.

The default run uses `tests/fixtures/clean.csv` and descriptive statistics for
`age`. All three reasoning models are real LLM implementations. The script
streams the compiled graph, reports completed nodes, status, revisions, review
decisions, interpretation validity, and error codes. It succeeds only with a
valid cited interpretation and an approved critique. HTTP requests use the
configured timeout without SDK retries.

Run the separate controlled revision scenario with:

```bash
uv run --project backend --env-file backend/.env python -m backend.scripts.graph_llm_smoke --controlled-revision
```

This scenario injects an incorrect first Interpretation claiming a mean of
`-999999`. Planner and Critic remain real LLMs, and subsequent Interpretation
attempts delegate to the real LLM. Success additionally requires a real Critic
rejection and feedback reaching the next Interpretation attempt. The script
does not force approval or revise agent prompts to obtain a passing result.

Use `--dataset`, `--column`, and `--max-revisions` to change the input or budget.
Credentials and raw provider exceptions are never printed.
