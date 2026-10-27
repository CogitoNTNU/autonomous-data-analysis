# Interpretation

`run_interpretation(request, model)` performs one attempt and returns an
`AgentResponse[InterpretationUpdates]`. It prepares evidence, builds context,
loads `prompt.md`, calls the injected model, validates references, and preserves
required qualifications. A successful draft still requires Critic review.

## Shared-state adapter

`build_interpretation_input(state)` creates an independent typed input from the
current plan, processed dataset version, evidence, and revision information.
It requires `processed_dataset` even when preprocessing made no changes.

`interpretation_node(state, model)` returns `AgentResponse[InterpretationUpdates]`.
It does not mutate state, merge warnings, increment limits, or call other agents.
Missing or invalid state returns a nonretryable `INVALID_DATA` response without
calling the model. Other errors retain the runner's error and retryability.

```python
from backend.app.agents.interpretation import interpretation_node

# state is AgentState; model is an injected InterpretationModel callable.
response = interpretation_node(state, model)
```

The future LangGraph harness must consume this typed envelope and apply its
updates rather than registering it as a dictionary-returning node unchanged.
Failures explicitly include `interpretation=None` even when updates are
serialized with `exclude_unset=True`, so the harness can invalidate an older
draft. Routing, error history, warning deduplication, and invalidation of old
Critic approvals or final responses remain the harness's responsibility.

## Provider adapter

`InterpretationLLM(client, model_name, timeout_seconds=30.0)` implements the
model callable using Chat Completions. The configured endpoint and model must
support `response_format={"type": "json_object"}`. JSON mode does not guarantee
the application schema; the adapter validates output with Pydantic. It does
not silently fall back to another endpoint, model, or response format.

The application supplies an `InterpretationInput` and configures credentials
and an endpoint at startup. For example, with your own environment settings:

```python
import os

from openai import OpenAI

from backend.app.agents.interpretation.agent import run_interpretation
from backend.app.agents.interpretation.llm import InterpretationLLM

# request is a validated InterpretationInput constructed by the application.
with OpenAI(
    api_key=os.environ["NTNU_LLM_API_KEY"],
    base_url=os.environ["NTNU_LLM_BASE_URL"],
) as client:
    model = InterpretationLLM(client, os.environ["NTNU_LLM_MODEL"])
    response = run_interpretation(request, model)
```

No credentials or environment variables are read during module import. The
caller owns the injected client and closes it after use. The adapter disables
SDK retries on a client copy and applies a finite HTTP operation timeout; the
harness must enforce any overall workflow deadline and retry limits.

## Failure behavior

- Empty, malformed, truncated, refused, or schema-invalid output raises
  `ValueError`, becoming `INVALID_OUTPUT` in the agent response.
- Connection failures, rate limits, and temporary server failures are marked
  retryable through `ConnectionError`; timeouts use `TimeoutError`.
- Invalid requests, authentication failures, and exhausted quota raise
  `ModelProviderError`, becoming a nonretryable `TOOL_FAILURE`.
- Provider diagnostics are not included in response messages. Exception causes
  remain available to application error handling and must not be shown to users.
- No tool calls are sent or executed. Unexpected tool-call responses are rejected.

The HTTP adapter tests use an in-memory transport with dummy credentials. They
exercise the real SDK request and response handling without network access.
Live endpoint compatibility is not established by those tests.

Reference: [OpenAI structured output and JSON-mode documentation](https://developers.openai.com/api/docs/guides/structured-outputs).
