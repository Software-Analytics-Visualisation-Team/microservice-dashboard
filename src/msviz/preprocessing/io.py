"""I/O and path resolution for preprocessing."""

from pathlib import Path

import pandas as pd


def resolve_input_csv_path(input_csv: str | None = None) -> Path:
    if input_csv:
        return Path(input_csv)
    package_root = Path(__file__).resolve().parents[2]
    return package_root / "data/raw_data.csv"


def resolve_output_csv_path(output_csv: str | None = None) -> Path:
    if output_csv:
        return Path(output_csv)
    package_root = Path(__file__).resolve().parents[2]
    return package_root / "data/processed_data.csv"


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
