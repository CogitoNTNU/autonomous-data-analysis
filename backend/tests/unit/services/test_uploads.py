"""CSV registration rejects ambiguous records before storing immutable bytes."""

from pathlib import Path

import pytest

from backend.app.services.uploads import MAX_CSV_BYTES, save_csv, store_named_csv


def test_save_csv_preserves_bom_quotes_multiline_fields_and_crlf(
    tmp_path: Path,
) -> None:
    content = (
        "\ufeff region ,notes,revenue\r\n"
        'North,"Comma, and ""quoted"" text",12\r\n'
        'South,"A multiline\r\nnote",24\r\n'
    ).encode("utf-8")

    path = save_csv(tmp_path, content)

    assert path.parent == tmp_path
    assert path.suffix == ".csv"
    assert path.read_bytes() == content


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (b"revenue,revenue\n1,2\n", "unique name"),
        (b"region,\nNorth,1\n", "must have a name"),
        (b"region,  \nNorth,1\n", "must have a name"),
        (b"region,revenue\nNorth,1,extra\n", "same number of columns"),
        (b"region,revenue\nNorth\n", "same number of columns"),
        (b'region,revenue\n""\n', "same number of columns"),
        (b"region,revenue\nNorth,\xff\n", "UTF-8"),
        (b'region,revenue\n"North,1\n', "malformed quoted value"),
        (b'region,revenue\n"North"unexpected,1\n', "malformed quoted value"),
        (b"\xef\xbb\xbf", "header row"),
        (b"\r\n\t ", "empty"),
        (b"x" * (MAX_CSV_BYTES + 1), "larger than 10 MB"),
    ],
)
def test_save_csv_rejects_invalid_input_without_writing(
    tmp_path: Path, content: bytes, message: str
) -> None:
    directory = tmp_path / "uploads"

    with pytest.raises(ValueError, match=message):
        save_csv(directory, content)

    assert not directory.exists()


@pytest.mark.parametrize(
    "content",
    [
        b"region,revenue\r\n",
        b"\nregion,revenue\n\n,\n\nNorth,1\n",
        b" \r\nregion,revenue\r\n \r\nNorth,1\r\n",
        b'region,revenue\n"",""\n',
        b"region, region \nNorth,South\n",
    ],
)
def test_save_csv_accepts_header_only_and_explicit_empty_records(
    tmp_path: Path, content: bytes
) -> None:
    path = save_csv(tmp_path, content)

    assert path.read_bytes() == content


def test_save_csv_preserves_quoted_whitespace_as_a_record(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="same number of columns"):
        save_csv(tmp_path, b'region,revenue\n"   "\n')

    assert list(tmp_path.iterdir()) == []


def test_store_named_csv_uses_the_same_csv_validation(tmp_path: Path) -> None:
    dataset_id = "b4b1d847-4e5a-49e0-ab49-9edf98f0e6fe"

    with pytest.raises(ValueError, match="unique name"):
        store_named_csv(tmp_path, dataset_id, b"region,region\nNorth,South\n")

    assert not (tmp_path / f"{dataset_id}.csv").exists()


def test_store_named_csv_keeps_the_validated_identifier_and_bytes(
    tmp_path: Path,
) -> None:
    dataset_id = "b4b1d847-4e5a-49e0-ab49-9edf98f0e6fe"
    content = b"region,revenue\nNorth,1\n"

    path = store_named_csv(tmp_path, dataset_id, content)

    assert path == tmp_path / f"{dataset_id}.csv"
    assert path.read_bytes() == content


def test_store_named_csv_rejects_path_like_identifiers(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Unknown dataset"):
        store_named_csv(tmp_path, "../outside", b"region,revenue\nNorth,1\n")

    assert list(tmp_path.iterdir()) == []


def test_named_csv_restoration_is_idempotent(tmp_path: Path) -> None:
    identifier = "b4b1d847-4e5a-49e0-ab49-9edf98f0e6fe"
    content = b"value\n1\n"
    original = store_named_csv(tmp_path, identifier, content)

    restored = store_named_csv(tmp_path, identifier, content)

    assert restored == original
    assert restored.read_bytes() == content


def test_named_csv_cannot_replace_registered_raw_data(tmp_path: Path) -> None:
    identifier = "b4b1d847-4e5a-49e0-ab49-9edf98f0e6fe"
    path = store_named_csv(tmp_path, identifier, b"value\n1\n")

    with pytest.raises(ValueError, match="cannot be replaced"):
        store_named_csv(tmp_path, identifier, b"value\n2\n")

    assert path.read_bytes() == b"value\n1\n"
