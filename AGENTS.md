# Repository Engineering Instructions

These rules apply to every contributor and coding agent. Instructions in a
more specific `AGENTS.md` add to these rules for files below that directory.

## Working agreement

- Read the relevant code, tests, and scoped instructions before editing.
- Make the smallest change that fully solves the assigned problem.
- Do not combine features, refactors, formatting, and dependency upgrades in
  one change unless they are inseparable.
- Preserve unrelated work and never silently rewrite another contributor's
  changes.
- Prefer established project patterns over introducing new abstractions.
- Record important architectural decisions in `docs/architecture/`.

## Maintainability limits

- Keep hand-written source files at or below 150 lines. Split a file before
  exceeding the limit. Generated files, lockfiles, migrations, fixtures, and
  declarative configuration are exempt.
- A file should have one clear responsibility.
- Prefer functions below 25 lines. Extract named helpers when a function mixes
  validation, orchestration, transformation, and presentation.
- Prefer no more than four parameters. Use a typed request object when inputs
  naturally belong together.
- Avoid nesting deeper than three levels. Use guard clauses and early returns.
- Do not create generic `utils.py`, `helpers.py`, or `common.py` dumping
  grounds. Name modules after their domain responsibility.
- Delete dead code instead of commenting it out.

## Code clarity

- Choose descriptive domain names; avoid unexplained abbreviations.
- Keep side effects visible and localized.
- Separate pure calculations from I/O, storage, model calls, and UI behavior.
- Replace unexplained literals with named constants or configuration.
- Add comments for reasoning, constraints, and non-obvious tradeoffs—not for
  restating the code.
- Public contracts and non-obvious behavior require concise documentation.

## Architecture boundaries

- Shared models define communication between components.
- Agents communicate through typed state and contracts, not direct imports of
  other agents.
- Tools perform calculations and transformations; language models do not.
- The workflow harness handles routing, state, limits, retries, and loops. It
  must not contain calculation or presentation logic.
- API and UI layers call application services rather than tools or agents
  directly.
- Depend on interfaces at storage and model-provider boundaries.

## Reliability and security

- Validate data at system boundaries and reject invalid states early.
- Raise specific exceptions; never use a bare `except` or silently swallow an
  error.
- Log identifiers and outcomes, not datasets, credentials, or sensitive values.
- Never commit secrets, local environments, generated artifacts, or caches.
- Avoid arbitrary code execution and unrestricted SQL or filesystem access.
- Make retries bounded and use them only for transient failures.
- Every loop must have an explicit termination condition.

## Testing and delivery

- Add or update tests for every behavior change and bug fix.
- Test public behavior, boundaries, failure cases, and routing decisions.
- Keep tests deterministic; mock network, model-provider, time, and external
  storage boundaries.
- Run the smallest relevant checks while developing, then the full affected
  test suite before handoff.
- Do not declare success while relevant tests, linting, formatting, lockfile
  checks, or builds fail.
- Use Conventional Commit titles: `type(scope): concise imperative summary`.
- Keep commits focused and PRs small enough to review confidently.
