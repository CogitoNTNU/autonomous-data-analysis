"""Planner responses must not reveal secrets or accept another site's browser."""

import json
from pathlib import Path

import pytest

from backend.app.api.origins import require_site_origin
from backend.app.api.planner_server import PlannerApp, dispatch
from backend.app.api.redact import redact
from backend.app.services.uploads import store_named_csv
from backend.app.storage.datasets import create_dataset_reference
from backend.app.tools.registry import ToolRegistry

SECRET = "sk-test-private-key-value"
DATASET_ID = "33333333-3333-4333-8333-333333333333"


def test_redact_removes_secret_values_and_key_shaped_text(monkeypatch) -> None:
    monkeypatch.setenv("NTNU_LLM_API_KEY", SECRET)

    assert redact(f"provider said {SECRET}") == "provider said [redacted]"
    assert redact("Incorrect API key provided: sk-abcdefghijklmnop") == (
        "Incorrect API key provided: [redacted]"
    )
    assert redact("The question is empty") == "The question is empty"


def test_empty_environment_values_are_not_treated_as_secrets(monkeypatch) -> None:
    monkeypatch.setenv("NTNU_LLM_API_KEY", "")
    monkeypatch.delenv("IDUN_API_KEY", raising=False)

    assert redact("The question is empty") == "The question is empty"


def test_dispatch_hides_a_provider_error(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("NTNU_LLM_API_KEY", SECRET)
    monkeypatch.delenv("VERCEL", raising=False)
    path = tmp_path / "rows.csv"
    path.write_text("species,body_mass_g\nAdelie,1\n", encoding="utf-8")
    app = PlannerApp(tmp_path, ToolRegistry(), _explode)
    app.paths["local"] = path

    status, payload = dispatch(
        app,
        "/api/planner",
        json.dumps({"dataset_id": "local", "question": "Compare mass"}).encode(),
        {},
    )

    assert status == 200
    assert SECRET not in json.dumps(payload)
    assert payload["message"] == "provider said [redacted]"


def test_hosted_requests_must_come_from_the_same_site(monkeypatch) -> None:
    monkeypatch.setenv("VERCEL", "1")
    headers = {"Origin": "https://app.vercel.app", "X-Forwarded-Host": "app.vercel.app"}

    require_site_origin(headers)

    with pytest.raises(ValueError, match="this site"):
        require_site_origin(
            {"Origin": "https://evil.example", "Host": "app.vercel.app"}
        )


def test_local_requests_skip_the_hosted_origin_check(monkeypatch) -> None:
    monkeypatch.delenv("VERCEL", raising=False)

    require_site_origin({"Origin": "https://evil.example"})


def test_named_csv_keeps_the_dataset_id_and_rejects_paths(tmp_path: Path) -> None:
    path = store_named_csv(tmp_path, DATASET_ID, b"species,body_mass_g\nAdelie,1\n")

    assert path.name == f"{DATASET_ID}.csv"
    with pytest.raises(ValueError, match="Unknown dataset"):
        store_named_csv(tmp_path, "../secret", b"species,body_mass_g\nAdelie,1\n")
    assert list(tmp_path.iterdir()) == [path]


def test_hosted_upload_directory_can_be_read() -> None:
    directory = Path("/tmp/ada-uploads")
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{DATASET_ID}.csv"
    path.write_text("species,body_mass_g\nAdelie,1\n", encoding="utf-8")
    try:
        dataset = create_dataset_reference(path)
    finally:
        path.unlink(missing_ok=True)

    assert dataset.dataset_id == DATASET_ID


def _explode() -> None:
    raise RuntimeError(f"provider said {SECRET}")
