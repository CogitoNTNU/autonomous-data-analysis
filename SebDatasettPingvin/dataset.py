"""Load a CSV dataset and inspect missing values, rows, and columns."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

DEFAULT_DATASET = Path(__file__).resolve().parent / "penguins.csv"


@dataclass(frozen=True)
class DatasetProfile:
    """Summary of a dataset's structure and data quality."""

    n_rows: int
    n_columns: int
    column_names: list[str]
    dtypes: dict[str, str]
    missing_by_column: dict[str, int]
    missing_pct_by_column: dict[str, float]
    columns_with_missing: list[str]
    total_missing: int
    rows_with_missing: int
    empty_rows: int
    duplicate_rows: int


def load_dataset(path: str | Path) -> pd.DataFrame:
    """Load a CSV file into a pandas DataFrame."""
    csv_path = Path(path)
    if not csv_path.is_file():
        raise FileNotFoundError(f"Dataset not found: {csv_path}")
    return pd.read_csv(csv_path)


def inspect_dataset(df: pd.DataFrame) -> DatasetProfile:
    """Profile a DataFrame: shape, missing values, empty and duplicate rows."""
    missing_by_column = df.isna().sum().astype(int).to_dict()
    n_rows = int(df.shape[0])
    missing_pct_by_column = {
        column: (count / n_rows * 100.0 if n_rows else 0.0)
        for column, count in missing_by_column.items()
    }
    return DatasetProfile(
        n_rows=n_rows,
        n_columns=int(df.shape[1]),
        column_names=list(df.columns),
        dtypes={column: str(dtype) for column, dtype in df.dtypes.items()},
        missing_by_column=missing_by_column,
        missing_pct_by_column=missing_pct_by_column,
        columns_with_missing=[
            column for column, count in missing_by_column.items() if count > 0
        ],
        total_missing=int(df.isna().sum().sum()),
        rows_with_missing=int(df.isna().any(axis=1).sum()),
        empty_rows=int(df.isna().all(axis=1).sum()),
        duplicate_rows=int(df.duplicated().sum()),
    )


def format_inspection(profile: DatasetProfile) -> str:
    """Render a human-readable inspection report."""
    lines = [
        "Dataset inspection",
        "==================",
        f"Shape: {profile.n_rows} rows × {profile.n_columns} columns",
        f"Column names: {', '.join(profile.column_names)}",
        "",
        "Dtypes",
        "------",
    ]
    for column in profile.column_names:
        lines.append(f"  {column}: {profile.dtypes[column]}")

    lines.extend(
        [
            "",
            "Missing values",
            "--------------",
            f"Total missing cells: {profile.total_missing}",
            f"Rows with missing values: {profile.rows_with_missing}",
            f"Completely empty rows: {profile.empty_rows}",
            f"Duplicate rows: {profile.duplicate_rows}",
        ]
    )

    if profile.columns_with_missing:
        lines.append("Missing by column:")
        for column in profile.columns_with_missing:
            count = profile.missing_by_column[column]
            pct = profile.missing_pct_by_column[column]
            lines.append(f"  {column}: {count} ({pct:.1f}%)")
    else:
        lines.append("No missing values found.")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Load a CSV dataset and inspect missing values, rows, and columns."
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=str(DEFAULT_DATASET),
        help=f"Path to a CSV file (default: {DEFAULT_DATASET})",
    )
    args = parser.parse_args(argv)
    print(format_inspection(inspect_dataset(load_dataset(args.path))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
