"""Data loading and metadata helpers."""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class DataContext:
    num_records: int
    trace_ids: list
    service_names: list
    first_timestamp: str
    last_timestamp: str
    min_timestamp: int
    max_timestamp: int


def load_data(csv_path: str = "data/inputs.csv") -> pd.DataFrame:
    path = Path(csv_path)
    if not path.is_absolute() and not path.exists():
        package_root = Path(__file__).resolve().parent.parent
        candidate_paths = [
            package_root.parent / csv_path,
            Path(__file__).resolve().parent / csv_path,
            package_root / "inputs.csv",
        ]

        for candidate in candidate_paths:
            if candidate.exists():
                path = candidate
                break

    data = pd.read_csv(path)
    data["call_duration"] = pd.to_numeric(data["call_duration"] * 1000, errors="coerce")
    data["timestamp"] = pd.to_datetime(
        data["timestamp"], format="%Y-%m-%d %H:%M:%S:%f", errors="coerce"
    )
    return data


def build_context(data: pd.DataFrame) -> DataContext:
    min_ts = data["timestamp"].min()
    max_ts = data["timestamp"].max()
    trace_ids = data["trace_id"].dropna().unique().tolist()
    service_names = sorted(data["service_name"].dropna().unique().tolist())

    return DataContext(
        num_records=len(data),
        trace_ids=trace_ids,
        service_names=service_names,
        first_timestamp=min_ts.strftime("%Y-%m-%d %H:%M:%S"),
        last_timestamp=max_ts.strftime("%Y-%m-%d %H:%M:%S"),
        min_timestamp=int(min_ts.timestamp()),
        max_timestamp=int(max_ts.timestamp()),
    )
