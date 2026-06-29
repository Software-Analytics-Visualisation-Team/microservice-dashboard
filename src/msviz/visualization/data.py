"""Data loading and metadata helpers for visualization."""

from dataclasses import dataclass
import json
import os
from pathlib import Path

import pandas as pd


# ---------------------------------------------------------------------------
# Knowledge-graph loading
# ---------------------------------------------------------------------------

def load_graph(json_path: str | Path) -> dict:
    """Load a knowledge_graph.json file and return the dict."""
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _graph_to_runtime_df(graph: dict) -> pd.DataFrame:
    """Reconstruct the runtime DataFrame from RuntimeInvocation nodes.

    Every RuntimeInvocation node stores the original CSV columns, so we can
    rebuild a DataFrame that is identical to what load_runtime_data returns
    when reading straight from the CSV.
    """
    rows = []
    for node in graph["nodes"]:
        if node["label"] != "RuntimeInvocation":
            continue
        rows.append({
            "timestamp":      node.get("timestamp", ""),
            "service_name":   node.get("service_name", ""),
            "event_code":     node.get("event_code", ""),
            "trace_id":       node.get("trace_id", "-"),
            "transaction_id": node.get("transaction_id", ""),
            "callee":         node.get("callee", ""),
            "call_duration":  node.get("call_duration", 0.0),
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # call_duration is stored in seconds (raw CSV unit); convert to ms for the UI
    df["call_duration"] = pd.to_numeric(df["call_duration"] * 1000, errors="coerce")
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    return df


def _graph_to_static_dict(graph: dict) -> dict:
    """Reconstruct the static data dict from Service, Module, and Operation nodes.

    Returns the same shape as load_static_data:
      {"static_services": {...}, "packages": {...}, "functions": {...}}
    """
    nodes_by_id = {node["id"]: node for node in graph["nodes"]}

    static_services = {}
    for node in graph["nodes"]:
        if node["label"] == "Service":
            static_services[node["name"]] = {"dependencies": []}

    packages = {}
    functions = {}

    for edge in graph["edges"]:
        if edge["type"] == "DEPENDS_ON":
            src, tgt = edge["source"], edge["target"]
            if src in static_services and tgt in static_services:
                static_services[src]["dependencies"].append(tgt)

        elif edge["type"] == "CONTAINS":
            src_node = nodes_by_id.get(edge["source"])
            tgt_node = nodes_by_id.get(edge["target"])
            if not src_node or not tgt_node:
                continue

            if tgt_node["label"] == "Module":
                parent = src_node["name"] if src_node["label"] == "Service" else None
                packages[tgt_node["name"]] = {"parent": parent}

            elif tgt_node["label"] == "Operation":
                parent = src_node["name"] if src_node["label"] == "Structure" else None
                op_key = tgt_node.get("event_code", tgt_node["name"])
                functions[op_key] = {"parent": parent}

    return {
        "static_services": static_services,
        "packages": packages,
        "functions": functions,
    }


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
    neo4j_uri = os.getenv("NEO4J_URI")
    if neo4j_uri:
        from ..neo4j_client import load_graph_from_neo4j
        auth = (os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", ""))
        print("[i] Using runtime data from neo4j using " + neo4j_uri)
        return _graph_to_runtime_df(load_graph_from_neo4j(neo4j_uri, auth))

    path = Path(csv_path)
    if not path.is_absolute() or not path.exists():
        package_root = Path(__file__).resolve().parent.parent.parent.parent
        candidate_paths = [
            package_root / csv_path,
            package_root / "data" / "processed_runtime_data.csv",
        ]
        for candidate in candidate_paths:
            if candidate.exists():
                path = candidate
                break

    # If a knowledge graph JSON exists next to the CSV, prefer it
    graph_path = path.parent / "knowledge_graph.json"
    if graph_path.exists():
        print("[i] Using runtime data from knowledge_graph.json")
        return _graph_to_runtime_df(load_graph(graph_path))

    data = pd.read_csv(path)
    data["call_duration"] = pd.to_numeric(data["call_duration"] * 1000, errors="coerce")
    data["timestamp"] = pd.to_datetime(
        data["timestamp"], format="%Y-%m-%d %H:%M:%S:%f", errors="coerce"
    )
    print("[i] Using runtime data from " + path)
    return data


def load_static_data(
    csv_path: str = "data/processed_static_data.csv",
) -> dict:
    neo4j_uri = os.getenv("NEO4J_URI")
    if neo4j_uri:
        from ..neo4j_client import load_graph_from_neo4j
        auth = (os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", ""))
        print("[i] Using static data from neo4j using " + neo4j_uri)
        return _graph_to_static_dict(load_graph_from_neo4j(neo4j_uri, auth))

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

    # If a knowledge graph JSON exists next to the CSV, prefer it
    graph_path = path.parent / "knowledge_graph.json"
    if graph_path.exists():
        print("[i] Using static data from knowledge_graph.json")
        return _graph_to_static_dict(load_graph(graph_path))

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

    print("[i] Using static data from " + path)
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
