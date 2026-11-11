"""CSV records with consistent blank-line handling at ingestion and execution."""

import csv
from collections.abc import Iterator
from io import StringIO


def csv_records(text: str) -> Iterator[list[str]]:
    lines = list(StringIO(text, newline=""))
    reader = csv.reader(lines, strict=True)
    start = 0
    for row in reader:
        end = reader.line_num
        if "".join(lines[start:end]).strip():
            yield row
        start = end
