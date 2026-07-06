"""Build a knowledge graph JSON from the two processed CSV files.

Reads processed_runtime_data.csv and processed_static_data.csv and produces
knowledge_graph.json — a single graph that can be loaded into Neo4J or used
by the visualization layer.

Node types : System, Service, Module, Structure, Operation,
             ExecutionTrace, RuntimeInvocation

Edge types and their extra properties:
  CONTAINS   — source_type (static / dynamic)
  DEPENDS_ON — source_type (dynamic)
  EXECUTES   — source_type (dynamic), duration (seconds), frequency
  NEXT       — source_type (dynamic), order (int, position within trace)

Mapping from original data:
  microservice row  -> Service node
  event_code parts  -> Module (package chain) + Structure (interface) + Operation (function)
  caller/callee pair-> Service -DEPENDS_ON-> Service
  runtime row       -> RuntimeInvocation node
  trace_id group    -> ExecutionTrace node
"""

from datetime import datetime
import json
from collections import defaultdict
from pathlib import Path

import pandas as pd


NODE_COLORS = {
    "System":            "#4a90d9",
    "Service":           "#7bc67e",
    "Module":            "#9b59b6",
    "Structure":         "#e74c3c",
    "Operation":         "#1abc9c",
    "ExecutionTrace":    "#34495e",
    "RuntimeInvocation": "#95a5a6",
}

def _parse_static_name(name: str):
    """Split a static name into its parts by '/'."""
    parts = name.split("/")
    return parts

def _define_node_type(part: str):
    """Determine the node type based on the part name."""
    if part.find("service") != -1:
        return "Service"
    if part.find("package") != -1:
        return "Module"
    elif part.find("interface") != -1:
        return "Structure"
    elif part.find("function") != -1:
        return "Operation"
    raise ValueError(f"Unknown node type for part: {part}")

def _define_node_id(part: str):
    """Determine the node ID based on the part name."""
    if part.find("service") != -1:
        return f"service:{part}"
    if part.find("package") != -1:
        return f"module:{part}"
    elif part.find("interface") != -1:
        return f"structure:{part}"
    elif part.find("function") != -1:
        return f"operation:{part}"
    raise ValueError(f"Unknown node ID for part: {part}")

def build_graph(runtime_csv: str | Path, static_csv: str | Path) -> dict:
    """Read the two processed CSVs and return a knowledge graph as a plain dict.

    Returns {"nodes": [...], "edges": [...]}.
    Every node has at minimum: id, label, color, name.
    Every edge has at minimum: source, target, type, source_type.
    """
    runtime_df = pd.read_csv(runtime_csv)
    static_df = pd.read_csv(static_csv)

    nodes = {}          # node_id -> node dict; Python dicts preserve insertion order
    edges = []          # list of edge dicts
    seen_edges = set()  # (source, target, type) to deduplicate structural edges

    def add_node(node_id, label, name=None, **extra):
        if node_id not in nodes:
            nodes[node_id] = {
                "id": node_id,
                "label": label,
                "color": NODE_COLORS.get(label, "#aaaaaa"),
                "name": name or node_id,
                **extra,
            }

    def add_edge(source, target, edge_type, source_type="static", **props):
        key = (source, target, edge_type)
        if key not in seen_edges:
            seen_edges.add(key)
            edges.append({
                "source": source,
                "target": target,
                "type": edge_type,
                "source_type": source_type,
                **props,
            })

    # --- One System node that owns all services ---
    add_node("system", "System", name="system")

    # --- Add nodes and edges from the static CSV ---
    for _, row in static_df.iterrows():
        print(row)
        static_type = str(row.get("type", "")).strip().lower()
        static_name = str(row.get("name", "")).strip()
        static_properties = row.get("properties", "{}")

        if isinstance(static_properties, str):
            static_properties = json.loads(static_properties)

        if static_type == "microservice":
            static_node_id = _define_node_id(static_name)
            add_node(static_node_id, "Service", name=static_name)
            add_edge("system", static_node_id, "CONTAINS")
            static_properties_interfaces = static_properties.get("interfaces", [])
            for interface_path in static_properties_interfaces:
                parts = interface_path.split(".")
                static_top_package_id = _define_node_id(parts[0])
                add_node(static_top_package_id, "Module", name=parts[0])
                add_edge(static_node_id, static_top_package_id, "CONTAINS")
                part_index = 0
                for part in parts[1:]:
                    previous_part_id = _define_node_id(parts[part_index])
                    part_id = _define_node_id(part)

                    add_node(part_id, _define_node_type(part), name=part)
                    add_edge(previous_part_id, part_id, "CONTAINS")
                    part_index += 1
        if static_type == "package":
            parts = _parse_static_name(static_name)
            if (len(parts) > 0):
                static_package_id = _define_node_id(parts[0])
                add_node(static_package_id, "Module", name=parts[0])
                static_properties_parent = static_properties.get("parent", "")
                if (static_properties_parent):
                    static_properties_parent_id = _define_node_id(static_properties_parent)
                    add_edge(static_properties_parent_id, static_package_id, "CONTAINS")
                part_index = 0
                for part in parts[1:]:
                    previous_part_id = _define_node_id(parts[part_index])
                    part_id = _define_node_id(part)

                    add_node(part_id, _define_node_type(part), name=part)
                    add_edge(previous_part_id, part_id, "CONTAINS")
                    part_index += 1
        if static_type == "function":
            function_name = static_name.split("(")[0]
            if (len(parts) > 0):
                add_node(function_name, "Operation", name=function_name)
                static_properties_parent = static_properties.get("parent", "")
                if (static_properties_parent):
                    parent_parts = _parse_static_name(static_properties_parent)
                    if (len(parent_parts) > 0):
                        add_edge(_define_node_id(parent_parts[-1]), function_name, "CONTAINS")

    # --- Add nodes and edges from the runtime CSV ---
    trace_rows = {}
    for _, row in runtime_df.iterrows():
        print(row)
        runtime_service_name = str(row.get("service_name", "")).strip()
        runtime_service_id = _define_node_id(runtime_service_name)
        add_node(runtime_service_id, "Service", name=runtime_service_name)
        add_edge("system", runtime_service_id, "CONTAINS", source_type="dynamic")
        runtime_event_code = str(row.get("event_code", "")).strip()
        parts = runtime_event_code.split(".")
        if (len(parts) > 0):
            runtime_event_id = _define_node_id(parts[0])
            add_node(runtime_event_id, "Module", name=parts[0])
            add_edge(runtime_service_id, runtime_event_id, "CONTAINS", source_type="dynamic")
            part_index = 0
            for part in parts[1:]:
                previous_part_id = _define_node_id(parts[part_index])
                part_id = _define_node_id(part)
                
                add_node(part_id, _define_node_type(part), name=part)
                add_edge(previous_part_id, part_id, "CONTAINS", source_type="dynamic")
                part_index += 1

        runtime_callee_name = str(row.get("callee", "")).strip()
        runtime_callee_id = _define_node_id(runtime_callee_name)
        runtime_timestamp = str(row.get("timestamp", "")).strip()
        if runtime_timestamp:
            runtime_timestamp = datetime.fromisoformat(runtime_timestamp).isoformat()

        add_node(runtime_callee_id, _define_node_type(runtime_callee_name), name=runtime_callee_name)
        if (runtime_service_id, runtime_callee_id, "DEPENDS_ON") not in seen_edges:
            add_edge(runtime_service_id, runtime_callee_id, "DEPENDS_ON", source_type="dynamic", call_count=1, timestamps=[runtime_timestamp])
        else:
            for edge in edges:
                if edge["source"] == runtime_service_id and edge["target"] == runtime_callee_id and edge["type"] == "DEPENDS_ON":
                    edge["call_count"] += 1
                    edge.setdefault("timestamps", []).append(runtime_timestamp)
                    break

        runtime_trace_id = str(row.get("trace_id", "-")).strip()
        trace_rows[runtime_trace_id] = trace_rows.get(runtime_trace_id, []) + [row]

    for trace_id, items in trace_rows.items():
        items.sort(key=lambda s: s["timestamp"])
        node_id = f"trace:{trace_id}"
        add_node(node_id, "ExecutionTrace", name=trace_id)
        for i, row in enumerate(items):
            runtime_invocation_id = f"invocation:{row['timestamp']}-{row['service_name']}-{row['event_code']}"
            runtime_timestamp = str(row.get("timestamp", "")).strip()
            if runtime_timestamp:
                runtime_timestamp = datetime.fromisoformat(runtime_timestamp).isoformat()
            
            runtime_caller_id = _define_node_id(row.get("service_name", ""))
            runtime_callee_id = _define_node_id(row.get("callee", ""))

            add_node(runtime_invocation_id, "RuntimeInvocation", name=runtime_invocation_id, timestamp=runtime_timestamp, transaction_id=row.get("transaction_id", ""), order=i, caller=runtime_caller_id, callee=runtime_callee_id)
            add_edge(node_id, runtime_invocation_id, "CONTAINS", source_type="dynamic")
            if i > 0:
                previous_row = items[i - 1]
                previous_invocation_id = f"invocation:{previous_row['timestamp']}-{previous_row['service_name']}-{previous_row['event_code']}"
                add_edge(previous_invocation_id, runtime_invocation_id, "NEXT", source_type="dynamic")
            runtime_event_code = row.get("event_code", "")
            parts = runtime_event_code.split(".")
            add_edge(runtime_invocation_id, _define_node_id(parts[-1]), "EXECUTES", source_type="dynamic", duration=row.get("call_duration", 0), frequency=row.get("call_frequency", 0))


    return {"nodes": list(nodes.values()), "edges": edges}


def save_graph(graph: dict, output_path: str | Path) -> Path:
    """Write the graph dict to a JSON file and return the resolved path."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2)
    return path


def default_output_path(runtime_csv: str | Path) -> Path:
    """Return the default output path (knowledge_graph.json next to the runtime CSV)."""
    return Path(runtime_csv).parent / "knowledge_graph.json"
