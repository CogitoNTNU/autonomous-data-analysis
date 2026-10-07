"""Keep the prompt's output example compatible with the shared contract."""

import json
from pathlib import Path

from backend.app.contracts.models import Interpretation

PROMPT_PATH = (
    Path(__file__).resolve().parents[4] / "app/agents/interpretation/prompt.md"
)


def test_documented_output_example_validates_against_current_contract():
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    example = prompt.split("```json\n", 1)[1].split("```", 1)[0]

    interpretation = Interpretation.model_validate_json(example)

    assert interpretation.model_dump(mode="json") == json.loads(example)
    assert interpretation.summary.strip()
    assert interpretation.findings
    assert interpretation.limitations
    assert all(finding.claim.strip() for finding in interpretation.findings)
