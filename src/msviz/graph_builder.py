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


def _parse_event_code(event_code: str):
    """Split a dotted event code into (module_path, structure_name, operation_name).

    Convention:
      last segment      = operation (function)
      second-to-last    = structure (interface)
      everything before = module path (package chain, may be empty)

    Examples:
      'pkg1.pkg2.interface_1.function_1' -> ('pkg1.pkg2', 'interface_1', 'function_1')
      'pkg1.interface_2.function_2'      -> ('pkg1', 'interface_2', 'function_2')
      'interface_3.function_3'           -> (None, 'interface_3', 'function_3')
      'function_4'                       -> (None, None, 'function_4')
    """
    parts = event_code.split(".")
    if len(parts) == 1:
        return None, None, parts[0]
    if len(parts) == 2:
        return None, parts[0], parts[1]
    return ".".join(parts[:-2]), parts[-2], parts[-1]


def build_graph(runtime_csv: str | Path, static_csv: str | Path) -> dict:
    """Read the two processed CSVs and return a knowledge graph as a plain dict.

    Returns {"nodes": [...], "edges": [...]}.
    Every node has at minimum: id, label, color, name.
    Every edge has at minimum: source, target, type, source_type.
    """
    runtime_df = pd.read_csv(runtime_csv)
    static_df = pd.read_csv(static_csv)

    nodes = {}       # node_id -> node dict; Python dicts preserve insertion order
    edges = []       # list of edge dicts
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

    # --- Service nodes: one per microservice row in the static CSV ---
    for _, row in static_df.iterrows():
        print(row)
        if str(row.get("type", "")).strip().lower() == "microservice":
            svc_id = str(row["name"]).strip()
            add_node(svc_id, "Service", name=svc_id)
            add_edge("system", svc_id, "CONTAINS")

    # --- Structural nodes (Module, Structure, Operation) from runtime event codes ---
    # Each unique event_code gives us one Operation and its containing chain.
    for _, row in runtime_df.iterrows():
        event_code = str(row.get("event_code", "")).strip()
        service_name = str(row.get("service_name", "")).strip()

        module_path, structure_name, operation_name = _parse_event_code(event_code)

        module_id    = f"module:{module_path}" if module_path else None
        struct_key   = f"{module_path}.{structure_name}" if module_path else structure_name
        structure_id = f"structure:{struct_key}" if structure_name else None
        operation_id = f"operation:{event_code}"

        if module_id:
            add_node(module_id, "Module", name=module_path)
        if structure_id:
            add_node(structure_id, "Structure", name=structure_name)
        add_node(operation_id, "Operation", name=operation_name, event_code=event_code)

        # Service -CONTAINS-> Module
        # When there is no module layer, link Service directly to Structure instead.
        # (Component level is skipped — direct Service-to-Module links are allowed.)
        if service_name in nodes:
            if module_id:
                add_edge(service_name, module_id, "CONTAINS")
            elif structure_id:
                add_edge(service_name, structure_id, "CONTAINS")

        # Module -CONTAINS-> Structure
        if module_id and structure_id:
            add_edge(module_id, structure_id, "CONTAINS")

        # Structure -CONTAINS-> Operation
        if structure_id:
            add_edge(structure_id, operation_id, "CONTAINS")

    # --- Service -DEPENDS_ON-> Service from caller/callee pairs ---
    for _, row in runtime_df.iterrows():
        src = str(row.get("service_name", "")).strip()
        tgt = str(row.get("callee", "")).strip()
        if src and tgt and tgt not in ("nan", "-", ""):
            add_edge(src, tgt, "DEPENDS_ON", source_type="dynamic")

    # --- RuntimeInvocation nodes (one per row, in original CSV order) ---
    # All rows become RuntimeInvocation nodes regardless of whether they have a trace.
    # The node stores every original CSV field so the DataFrame can be reconstructed later.
    for idx, row in runtime_df.iterrows():
        inv_id     = f"invocation:{idx}"
        event_code = str(row.get("event_code", "")).strip()
        raw_dur    = row.get("call_duration")
        duration   = float(raw_dur) if pd.notna(raw_dur) else 0.0

        add_node(
            inv_id,
            "RuntimeInvocation",
            name=inv_id,
            timestamp=str(row.get("timestamp", "")),
            service_name=str(row.get("service_name", "")),
            event_code=event_code,
            trace_id=str(row.get("trace_id", "-")),
            transaction_id=str(row.get("transaction_id", "")),
            callee=str(row.get("callee", "")),
            call_duration=duration,   # seconds — same unit as raw CSV
        )

        # Every invocation executes a specific Operation
        operation_id = f"operation:{event_code}"
        if operation_id in nodes:
            add_edge(
                inv_id, operation_id, "EXECUTES",
                source_type="dynamic",
                duration=duration,
                frequency=1,
            )

    # --- ExecutionTrace nodes + CONTAINS + NEXT edges ---
    # Group invocations by trace_id; rows with "-" have no trace.
    trace_rows = defaultdict(list)
    for idx, row in runtime_df.iterrows():
        tid = str(row.get("trace_id", "-")).strip()
        trace_rows[tid].append(idx)

    for trace_id, inv_indices in trace_rows.items():
        if trace_id == "-":
            continue

        trace_node_id = f"trace:{trace_id}"
        add_node(trace_node_id, "ExecutionTrace", name=trace_id)

        prev_inv_id = None
        for order, idx in enumerate(inv_indices):
            inv_id = f"invocation:{idx}"
            add_edge(trace_node_id, inv_id, "CONTAINS", source_type="dynamic")
            if prev_inv_id:
                add_edge(prev_inv_id, inv_id, "NEXT", source_type="dynamic", order=order)
            prev_inv_id = inv_id

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
