# Descriptive charts and grouped results

## Chart presentation

All six visualization tools use the shared chart renderer. Every exported chart
has a nonblank title, readable labels on both axes, and an explanation of what
its marks represent. Counts use integer ticks, means are labeled as means, and
grouped charts have a titled legend. Heatmaps label their count color scale and
keep category labels aligned with the correct axes. Box plots explain the
median, middle 50%, whiskers, and outlier points.

Chart arguments accept optional `x_label`, `y_label`, and `group_label` for
readable names and known units. These labels never replace the actual column
references in `x`, `y`, or `group`. The Planner must use specific chart titles
and include units only when supported by metadata or the user's request.
Without explicit labels, the renderer expands column identifiers into readable
names, or uses a column's `label` and `unit` metadata when present. Aggregate
columns retain their measure names and units; counts do not inherit measure
units. Blank descriptions are rejected. Long titles and labels wrap, and longer
category ticks rotate to remain readable.

The renderer distinguishes source observations from rows of grouped results:
for example, a histogram of group totals counts groups, not the original rows.
Bar and line charts showing existing unique group totals preserve that meaning;
if they average multiple input rows per category, the y-axis says so.

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
