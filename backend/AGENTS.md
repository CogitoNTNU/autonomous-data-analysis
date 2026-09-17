# Backend Engineering Instructions

Follow the repository-level `AGENTS.md` in addition to these Python rules.

## Python style

- Support only the Python version pinned in the repository `.python-version`.
- Manage dependencies and commands with uv. Keep `pyproject.toml`, `uv.lock`,
  and the exported `requirements.txt` synchronized.
- Use Ruff for formatting and linting. Do not manually fight its output.
- Add type annotations to public functions, methods, and shared state.
- Use Pydantic models for external boundaries and cross-component contracts.
  Use dataclasses or typed dictionaries only for internal structures where
  runtime validation is unnecessary.
- Use `pathlib.Path`, context managers, and timezone-aware datetimes.
- Prefer immutable inputs and explicit return values over hidden mutation.
- Avoid module-level mutable state and import-time I/O.

## Module design

- Place shared domain contracts in `app/models/`.
- Place deterministic computation and transformation in `app/tools/`.
- Place agent-specific reasoning, prompts, and adapters in `app/agents/`.
- Place LangGraph construction and routing in `app/graph/`.
- Place storage protocols and implementations in `app/storage/`.
- Place application use-case coordination in `app/services/`.
- Place HTTP behavior in `app/api/`.
- Keep provider SDKs behind small adapters so tests do not require live APIs.

## Function design

- A function should either validate, calculate, orchestrate, persist, or
  present. Split functions that do several of these.
- Make dependencies explicit through parameters or constructors.
- Return structured domain results instead of loosely shaped dictionaries.
- Keep functions deterministic unless their name and location clearly indicate
  I/O or another side effect.
- Never pass a full DataFrame through LangGraph state. Store a versioned dataset
  reference or artifact reference instead.

## Agents and tools

- Agents may import models and interfaces, but must not import other agents.
- Preprocessing and analysis agents execute registered tools; they do not
  calculate results with a language model.
- Every tool has a unique name, validated input model, validated output model,
  and focused unit tests.
- Preserve raw data. Transformations create a new dataset version and report.
- Every analysis result records its step ID, dataset version, parameters,
  sample size, and warnings.
- Interpretations must reference supporting result IDs.
- Critic and clarification loops must have configurable maximum counts.

## Exceptions and logging

- Define domain exceptions in `app/core/exceptions.py`.
- Convert domain exceptions to transport responses only in the API layer.
- Preserve exception context with `raise ... from error`.
- Use structured logging with request, workflow, plan, step, and execution IDs.
- Never expose stack traces or internal paths in user-facing responses.

## Required checks

From the repository root, run:

```bash
uv lock --project backend --check
uv run --project backend pytest backend/tests
```

Run the configured pre-commit hooks before submitting broad changes.

