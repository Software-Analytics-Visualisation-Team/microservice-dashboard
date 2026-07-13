"""I/O and path resolution for preprocessing."""

import csv
import json
from pathlib import Path
from typing import Any

from msviz.data import StaticDataModel
import pandas as pd
import yaml


def resolve_input_csv_path(input_csv: str | None = None) -> Path:
    if input_csv:
        return Path(input_csv)
    package_root = Path(__file__).resolve().parents[2]
    return package_root / "data/raw_runtime_data.csv"


def resolve_output_csv_path(output_csv: str | None = None) -> Path:
    if output_csv:
        return Path(output_csv)
    package_root = Path(__file__).resolve().parents[2]
    return package_root / "data/processed_runtime_data.csv"


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def read_yml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise TypeError(f"Expected YAML mapping, got {type(data).__name__}")
    return data


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise TypeError(f"Expected JSON mapping, got {type(data).__name__}")
    return data


def read_static_mapping(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix in {".yml", ".yaml"}:
        return read_yml(path)
    if suffix == ".json":
        return read_json(path)
    raise ValueError(
        f"Unsupported static input extension '{path.suffix}'. Use .yml, .yaml or .json."
    )


def resolve_static_output_csv_path(
    input_path: Path, output_csv: str | Path | None = None
) -> Path:
    if output_csv:
        return Path(output_csv)
    return input_path.parent / "processed_static_data.csv"


def write_static_entities_csv(model: StaticDataModel, output_path: Path) -> None:
    rows = _build_static_entity_rows(model)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["name", "type", "properties"])
        writer.writeheader()
        writer.writerows(rows)


def _build_static_entity_rows(model: StaticDataModel) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    for microservice in model.microservices:
        name = microservice.get("name")
        if not isinstance(name, str):
            continue
        properties = {k: v for k, v in microservice.items() if k != "name"}
        rows.append(
            {
                "name": name,
                "type": "microservice",
                "properties": json.dumps(properties, ensure_ascii=True, sort_keys=True),
            }
        )

    for package in model.packages:
        name = package.get("name")
        if not isinstance(name, str):
            continue
        parent = package.get("service")
        properties = {"parent": parent} if isinstance(parent, str) else {}
        for key, value in package.items():
            if key not in {"name", "service"}:
                properties[key] = value
        rows.append(
            {
                "name": name,
                "type": "package",
                "properties": json.dumps(properties, ensure_ascii=True, sort_keys=True),
            }
        )

    for function in model.functions:
        name = function.get("name")
        if not isinstance(name, str):
            continue
        parent = function.get("parent")
        if not isinstance(parent, str):
            service = function.get("service")
            parent = service if isinstance(service, str) else None
        properties: dict[str, Any] = {"parent": parent} if isinstance(parent, str) else {}
        for key, value in function.items():
            if key not in {"name", "parent", "service"}:
                properties[key] = value
        rows.append(
            {
                "name": name,
                "type": "function",
                "properties": json.dumps(properties, ensure_ascii=True, sort_keys=True),
            }
        )

    return rows


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
