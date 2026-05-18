"""Data loading and metadata helpers for visualization."""

from dataclasses import dataclass
import json
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class DataContext:
    num_records: int
    trace_ids: list
    service_names: list
    static_services: dict
    packages: dict
    functions: dict
    first_timestamp: str
    last_timestamp: str
    min_timestamp: int
    max_timestamp: int


def load_runtime_data(csv_path: str = "data/processed_runtime_data.csv") -> pd.DataFrame:
    path = Path(csv_path)
    if not path.is_absolute() or not path.exists():
        package_root = Path(__file__).resolve().parent.parent.parent.parent
        candidate_paths = [
            package_root / csv_path,
            package_root / "data" / "processed_runtime_data.csv",
        ]

        for candidate in candidate_paths:
            print(candidate)
            if candidate.exists():
                path = candidate
                break
    

    data = pd.read_csv(path)
    data["call_duration"] = pd.to_numeric(data["call_duration"] * 1000, errors="coerce")
    data["timestamp"] = pd.to_datetime(
        data["timestamp"], format="%Y-%m-%d %H:%M:%S:%f", errors="coerce"
    )
    return data


def load_static_data(
    csv_path: str = "data/processed_static_data.csv",
) -> dict:
    path = Path(csv_path)
    if not path.is_absolute() or not path.exists():
        package_root = Path(__file__).resolve().parent.parent.parent.parent
        candidate_paths = [
            package_root / csv_path,
            package_root / "data" / "processed_static_data.csv",
        ]

        for candidate in candidate_paths:
            if candidate.exists():
                path = candidate
                break

    data = pd.read_csv(path)
    static_services = {}
    packages = {}
    functions = {}

    for _, row in data.iterrows():
        entity_name = str(row.get("name", "")).strip()
        entity_type = str(row.get("type", "")).strip().lower()
        properties_raw = row.get("properties")

        if not entity_name:
            continue

        properties = {}
        if pd.notna(properties_raw):
            if isinstance(properties_raw, dict):
                properties = properties_raw
            else:
                try:
                    properties = json.loads(str(properties_raw))
                except json.JSONDecodeError:
                    properties = {"raw": str(properties_raw)}

        if entity_type == "microservice":
            static_services[entity_name] = properties
        elif entity_type == "package":
            packages[entity_name] = properties
        elif entity_type == "function":
            functions[entity_name] = properties

    return {
        "static_services": static_services,
        "packages": packages,
        "functions": functions,
    }


def load_data(csv_path: str = "data/processed_runtime_data.csv") -> pd.DataFrame:
    return load_runtime_data(csv_path)


def build_context(runtime_data: pd.DataFrame, static_data: dict | None = None) -> DataContext:
    static_entities = static_data if static_data is not None else load_static_data()

    min_ts = runtime_data["timestamp"].min()
    max_ts = runtime_data["timestamp"].max()
    trace_ids = runtime_data["trace_id"].dropna().unique().tolist()
    service_names = sorted(runtime_data["service_name"].dropna().unique().tolist())

    return DataContext(
        num_records=len(runtime_data),
        trace_ids=trace_ids,
        service_names=service_names,
        static_services=static_entities.get("static_services", {}),
        packages=static_entities.get("packages", {}),
        functions=static_entities.get("functions", {}),
        first_timestamp=min_ts.strftime("%Y-%m-%d %H:%M:%S"),
        last_timestamp=max_ts.strftime("%Y-%m-%d %H:%M:%S"),
        min_timestamp=int(min_ts.timestamp()),
        max_timestamp=int(max_ts.timestamp()),
    )
