# Backend Test Instructions

Follow the root and backend instructions in addition to these test rules.

## Test organization

- Mirror the application structure under `tests/unit/`.
- Use `tests/integration/` for component boundaries such as graph plus agents or
  tools plus storage.
- Use `tests/end_to_end/` only for complete user workflows.
- Put reusable builders and sample data in `tests/fixtures/` or `conftest.py`.
- Do not put production behavior in test helpers.

## Test quality

- Follow arrange, act, assert with visually distinct sections when useful.
- Give tests behavioral names such as
  `test_planner_requests_clarification_when_target_is_ambiguous`.
- Test one behavior per test. Multiple assertions are fine when they verify one
  coherent result.
- Test successful behavior, validation failures, boundary values, and expected
  warnings.
- Assert observable outputs and state transitions rather than implementation
  details or private methods.
- Keep fixtures minimal and explicit. Prefer small synthetic datasets over the
  full example dataset for unit tests.

## Isolation

- Unit tests must not call live LLMs, databases, networks, or system time.
- Inject fakes at provider and storage boundaries.
- Use temporary directories for files and artifacts.
- Do not depend on test execution order or shared mutable state.
- Give graph tests explicit recursion and revision limits.
- Add a regression test before or with every bug fix.

