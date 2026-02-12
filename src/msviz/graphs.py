"""Plot and graph builders."""

from collections import defaultdict, deque

import dash_bootstrap_components as dbc
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import pandas as pd
import plotly.express as px


def _compute_node_depth(df: pd.DataFrame):
    edges = [
        (row["service_name"], row["callee"])
        for _, row in df.iterrows()
        if pd.notna(row["callee"])
    ]

    children = defaultdict(list)
    parents = set()
    for src, tgt in edges:
        children[src].append(tgt)
        parents.add(tgt)

    roots = [n for n in set(df["service_name"]) if n not in parents]
    node_depth = {}
    queue = deque([(root, 0) for root in roots])

    while queue:
        node, depth = queue.popleft()
        if node not in node_depth or depth < node_depth[node]:
            node_depth[node] = depth
            for child in children.get(node, []):
                queue.append((child, depth + 1))
    return node_depth


def build_trace_elements(df: pd.DataFrame):
    node_depth = _compute_node_depth(df)
    cy_nodes = []
    for node in set(df["service_name"]).union(set(df["callee"].dropna())):
        cy_nodes.append(
            {
                "data": {"id": node, "label": node},
                "position": {
                    "x": 100 * node_depth.get(node, 0),
                    "y": 200 * node_depth.get(node, 0),
                },
            }
        )

    cy_edges = []
    if not df.empty:
        edge_groups = (
            df.dropna(subset=["callee"])
            .groupby(["service_name", "callee", "event_code"])["call_duration"]
            .mean()
            .reset_index()
        )
        for _, row in edge_groups.iterrows():
            cy_edges.append(
                {
                    "data": {
                        "source": row["service_name"],
                        "target": row["callee"],
                        "label": f"{row['event_code']} (avg: {row['call_duration']:.1f}ms)",
                    }
                }
            )

    return cy_nodes + cy_edges


def build_span_elements(df: pd.DataFrame):
    node_depth = _compute_node_depth(df)
    all_nodes = list(set(df["service_name"]).union(set(df["callee"].dropna())))

    cy_nodes = []
    for idx, node in enumerate(all_nodes):
        cy_nodes.append(
            {
                "data": {"id": node, "label": node},
                "position": {"x": 150 * node_depth.get(node, 0), "y": 120 * idx},
            }
        )

    edge_groups = (
        df.dropna(subset=["callee"])
        .groupby(["service_name", "callee", "event_code"])["call_duration"]
        .mean()
        .reset_index()
    )
    cy_edges = []
    for _, row in edge_groups.iterrows():
        cy_edges.append(
            {
                "data": {
                    "source": row["service_name"],
                    "target": row["callee"],
                    "label": f"{row['event_code']} (avg: {row['call_duration']:.1f}ms)",
                }
            }
        )
    return cy_nodes + cy_edges


def build_service_heatmap_figure(df: pd.DataFrame, service_name: str):
    if not service_name:
        return {}

    filtered = df[df["service_name"] == service_name].copy()
    if filtered.empty:
        return {}

    fig = px.density_heatmap(
        filtered,
        x="event_code",
        y="callee",
        z="call_duration",
        color_continuous_scale="YlOrRd",
        histfunc="avg",
        labels={
            "call_duration": "call duration (ms)",
            "callee": "Callee",
            "event_code": "Event Code",
        },
    )
    fig.update_layout(
        title=f"Call Duration Heatmap for {service_name}",
        xaxis_title="Event Code",
        yaxis_title="Callee Service",
    )
    return fig


def build_event_table(df: pd.DataFrame):
    table_df = df[["service_name", "callee", "event_code", "call_duration"]]
    return dbc.Table.from_dataframe(table_df, striped=True, bordered=True, hover=True)


def get_global_incoming_range(data: pd.DataFrame):
    grouped = (
        data.dropna(subset=["service_name", "callee"])
        .groupby(["service_name", "callee"])
        .size()
        .reset_index(name="count")
    )
    incoming_counts = grouped.groupby("callee")["count"].sum().to_dict()
    if not incoming_counts:
        return 0, 1
    return min(incoming_counts.values()), max(incoming_counts.values())


def build_overall_graph_elements(
    filtered_data: pd.DataFrame,
    global_min_count: int,
    global_max_count: int,
    selected_trace_id=None,
):
    df_grouped = (
        filtered_data.dropna(subset=["service_name", "callee"])
        .groupby(["service_name", "callee"])
        .size()
        .reset_index(name="count")
    )
    incoming_counts = df_grouped.groupby("callee")["count"].sum().to_dict()

    selected_edges = set()
    selected_nodes = set()
    if selected_trace_id:
        df_selected = filtered_data[filtered_data["trace_id"] == selected_trace_id]
        selected_edges = set(zip(df_selected["service_name"], df_selected["callee"]))
        selected_nodes = set(df_selected["service_name"]).union(
            set(df_selected["callee"].dropna())
        )

    nodes = set(df_grouped["service_name"]).union(set(df_grouped["callee"]))
    norm = mcolors.Normalize(vmin=global_min_count, vmax=global_max_count)
    cmap = cm.get_cmap("coolwarm")

    cy_nodes = []
    for node in nodes:
        node_data = {"id": node, "label": node}
        count = incoming_counts.get(node, 0)
        hex_color = mcolors.rgb2hex(cmap(norm(count)))
        classes = "selected" if node in selected_nodes else ""
        cy_nodes.append(
            {
                "data": node_data,
                "classes": classes,
                "style": {"background-color": hex_color},
            }
        )

    cy_edges = []
    for _, row in df_grouped.iterrows():
        classes = "selected" if (row["service_name"], row["callee"]) in selected_edges else ""
        cy_edges.append(
            {
                "data": {
                    "source": row["service_name"],
                    "target": row["callee"],
                    "label": f"Calls: {row['count']}",
                },
                "classes": classes,
            }
        )

    return cy_nodes + cy_edges


def build_all_event_code_histogram(data: pd.DataFrame):
    event_counts = (
        data.groupby("event_code")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )

    fig = px.bar(event_counts, x="event_code", y="count", title="Call Counts")
    fig.update_layout(height=800)
    return fig


def build_selected_edge_violinplot(
    filtered_data: pd.DataFrame, source: str, target: str
):
    df_edge = filtered_data[
        (filtered_data["service_name"] == source) & (filtered_data["callee"] == target)
    ]
    if df_edge.empty:
        return {}

    fig = px.violin(
        df_edge,
        x="event_code",
        y="call_duration",
        points="all",
        box=True,
        title=f"Call Duration Violin Plot: {source} -> {target}",
    )
    fig.update_layout(height=500)
    return fig


def build_edge_event_code_histogram(data: pd.DataFrame, source: str, target: str):
    df_edge = data[(data["service_name"] == source) & (data["callee"] == target)]
    if df_edge.empty:
        return {}

    event_counts = (
        df_edge.groupby("event_code")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )

    fig = px.bar(
        event_counts,
        x="event_code",
        y="count",
        title=f"Call Counts for {source} -> {target}",
    )
    fig.update_layout(height=800)
    return fig
