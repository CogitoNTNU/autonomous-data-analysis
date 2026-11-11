from pathlib import Path

import pytest

from backend.app.services.dataset_lookup import resolve_dataset


@pytest.mark.parametrize("replacement", [None, "value\n999\n"])
def test_persisted_upload_survives_loss_of_process_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, replacement: str | None
) -> None:
    monkeypatch.setattr("backend.app.storage.datasets.ALLOWED", (tmp_path,))
    identifier = "b4b1d847-4e5a-49e0-ab49-9edf98f0e6fe"
    path = tmp_path / f"{identifier}.csv"
    original = b"value\n1\n"
    path.write_bytes(original)
    paths = {}
    request = {"dataset_id": identifier}
    if replacement is not None:
        request["csv"] = replacement

    restored = resolve_dataset(tmp_path, paths, request)

    assert restored == path
    assert path.read_bytes() == original
    assert paths == {identifier: path}


def test_lookup_rejects_unregistered_path_identifier(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Unknown dataset"):
        resolve_dataset(tmp_path, {}, {"dataset_id": "../data", "csv": "x\n1\n"})
