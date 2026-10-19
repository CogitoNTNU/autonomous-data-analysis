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
