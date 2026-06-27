"""Dash callback registrations."""

import base64
import json

import pandas as pd
from copy import deepcopy
from dash import Input, Output, State, ctx, html
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc

from .data import _graph_to_runtime_df, _graph_to_static_dict
from .graphs import (
    build_all_event_code_histogram,
    build_edge_event_code_histogram,
    build_event_table,
    build_overall_graph_elements,
    build_selected_edge_violinplot,
    build_service_heatmap_figure,
    build_span_elements,
    build_static_graph_elements,
    build_trace_elements,
    get_global_incoming_range,
)


_SHOW = {"display": "block"}
_HIDE = {"display": "none"}

_SECTION_TAB_RUNTIME = "runtime-dependency-graph"
_SECTION_TAB_TRACE_GRAPH = "selected-trace-graph"
_SECTION_TAB_SPAN_GRAPH = "selected-span-graph"
_SECTION_TAB_HEATMAP = "call-duration-heatmap"
_SECTION_TAB_EVENT_TABLE = "event-table"
_SECTION_TAB_TRACE_REPLAY = "trace-replay"
_SECTION_TABS = {
    "slider-section": {_SECTION_TAB_RUNTIME, _SECTION_TAB_TRACE_GRAPH, _SECTION_TAB_SPAN_GRAPH, _SECTION_TAB_HEATMAP, _SECTION_TAB_EVENT_TABLE},
    "trace-section": {_SECTION_TAB_TRACE_GRAPH, _SECTION_TAB_SPAN_GRAPH, _SECTION_TAB_EVENT_TABLE, _SECTION_TAB_TRACE_REPLAY},
    "span-section": {_SECTION_TAB_SPAN_GRAPH},
    "heatmap-section": {_SECTION_TAB_HEATMAP},
    "static-toggle-section": {_SECTION_TAB_RUNTIME},
}

_REPLAY_STYLESHEET = [
    {
        "selector": "node",
        "style": {
            "label": "data(label)",
            "background-color": "#0074D9",
            "color": "#fff",
            "text-valign": "center",
            "text-halign": "center",
            "font-size": "12px",
            "width": "50px",
            "height": "50px",
        },
    },
    {
        "selector": "edge",
        "style": {
            "curve-style": "bezier",
            "target-arrow-shape": "triangle",
        },
    },
    {
        "selector": "edge.edge-future",
        "style": {
            "line-color": "#adb5bd",
            "target-arrow-color": "#adb5bd",
            "width": 2,
            "opacity": 0.3,
        },
    },
    {
        "selector": "edge.edge-active",
        "style": {
            "line-color": "#fd7e14",
            "target-arrow-color": "#fd7e14",
            "width": 5,
            "opacity": 1.0,
            "label": "data(label)",
            "font-size": "11px",
            "color": "#fd7e14",
            "text-background-color": "#fff",
            "text-background-opacity": 0.8,
            "text-background-padding": "3px",
        },
    },
    {
        "selector": "edge.edge-completed",
        "style": {
            "line-color": "#198754",
            "target-arrow-color": "#198754",
            "width": 2,
            "opacity": 0.8,
        },
    },
]


def _parse_store(store_data):
    """Return (runtime_df, static_elements) from the data store."""
    if not store_data:
        return pd.DataFrame(), []
    records = store_data.get("runtime_records", [])
    df = pd.DataFrame(records)
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df["call_duration"] = pd.to_numeric(df["call_duration"], errors="coerce")
    return df, store_data.get("static_elements", [])


def register_callbacks(app, overall_stylesheet):

    # ------------------------------------------------------------------ #
    # Upload                                                             #
    # ------------------------------------------------------------------ #

    @app.callback(
        [Output("data-store", "data"), Output("upload-status", "children")],
        Input("graph-upload", "contents"),
        prevent_initial_call=True,
    )
    def handle_graph_upload(contents):
        if not contents:
            raise PreventUpdate
        _, content_string = contents.split(",", 1)
        graph = json.loads(base64.b64decode(content_string))
        runtime_df = _graph_to_runtime_df(graph)
        static_dict = _graph_to_static_dict(graph)
        static_elems = build_static_graph_elements(static_dict)
        store_data = {
            "runtime_records": runtime_df.assign(
                timestamp=runtime_df["timestamp"].astype(str)
            ).to_dict("records"),
            "static_elements": static_elems,
            "service_names": sorted(runtime_df["service_name"].dropna().unique().tolist()),
            "trace_ids": runtime_df["trace_id"].dropna().unique().tolist(),
        }
        n_nodes = len(graph.get("nodes", []))
        n_edges = len(graph.get("edges", []))
        return store_data, f"✓ {n_nodes} nodes, {n_edges} edges"

    # ------------------------------------------------------------------ #
    # Dropdown population (re-runs on upload via data-store change)      #
    # ------------------------------------------------------------------ #

    @app.callback(
        [Output("trace-id-dropdown", "options"), Output("trace-id-dropdown", "value")],
        Input("data-store", "data"),
    )
    def update_trace_dropdown(store_data):
        if not store_data:
            return [], None
        trace_ids = store_data.get("trace_ids", [])
        options = [
            {"label": (f"{str(t)[:8]}..." if len(str(t)) > 8 else str(t)), "value": t}
            for t in trace_ids
        ]
        return options, (trace_ids[0] if trace_ids else None)

    @app.callback(
        [Output("service-name-dropdown", "options"), Output("service-name-dropdown", "value")],
        Input("data-store", "data"),
    )
    def update_service_dropdown(store_data):
        if not store_data:
            return [], None
        service_names = store_data.get("service_names", [])
        options = [{"label": s, "value": s} for s in service_names]
        return options, (service_names[0] if service_names else None)

    # ------------------------------------------------------------------ #
    # Sidebar visibility                                                 #
    # ------------------------------------------------------------------ #

    @app.callback(
        [
            Output("slider-section", "style"),
            Output("trace-section", "style"),
            Output("span-section", "style"),
            Output("heatmap-section", "style"),
            Output("static-toggle-section", "style"),
        ],
        Input("main-tabs", "value"),
    )
    def update_sidebar_visibility(active_tab):
        return [
            _SHOW if active_tab in tabs else _HIDE
            for tabs in _SECTION_TABS.values()
        ]

    # ------------------------------------------------------------------ #
    # Stylesheet (static-edges toggle)                                   #
    # ------------------------------------------------------------------ #

    @app.callback(
        Output("overall-cytoscape-graph", "stylesheet"),
        Input("static-edges-toggle", "value"),
    )
    def update_overall_stylesheet(show_static_dependencies):
        copied_stylesheet = deepcopy(overall_stylesheet)
        for rule in copied_stylesheet:
            if rule.get("selector") == "edge.static-edge":
                rule["style"]["display"] = "element" if show_static_dependencies else "none"
        return copied_stylesheet

    # ------------------------------------------------------------------ #
    # Slider tooltip                                                     #
    # ------------------------------------------------------------------ #

    @app.callback(
        Output("slider-tooltip", "children"),
        Input("time-range-slider", "value"),
    )
    def update_slider_tooltip(value):
        start = pd.to_datetime(value[0], unit="s").strftime("%Y-%m-%d %H:%M:%S")
        end = pd.to_datetime(value[1], unit="s").strftime("%Y-%m-%d %H:%M:%S")
        return f"{start}  to  {end}"

    # ------------------------------------------------------------------ #
    # Graph: Selected Trace + Event Table                                #
    # ------------------------------------------------------------------ #

    @app.callback(
        [
            Output("cytoscape-graph", "elements"),
            Output("event-table", "children"),
        ],
        [
            Input("trace-id-dropdown", "value"),
            Input("time-range-slider", "value"),
            Input("main-tabs", "value"),
            Input("data-store", "data"),
        ],
    )
    def update_dashboard(selected_trace_id, time_range, _active_tab, store_data):
        runtime_data, _ = _parse_store(store_data)
        if runtime_data.empty:
            return [], "No data loaded."

        start_dt = pd.to_datetime(time_range[0], unit="s")
        end_dt = pd.to_datetime(time_range[1], unit="s")
        filtered_data = runtime_data[
            (runtime_data["timestamp"] >= start_dt) & (runtime_data["timestamp"] <= end_dt)
        ]

        if not selected_trace_id:
            return [], "No trace_id selected."

        df = filtered_data[filtered_data["trace_id"] == selected_trace_id]
        return build_trace_elements(df), build_event_table(df)

    # ------------------------------------------------------------------ #
    # Graph: Runtime Dependency (all data)                               #
    # ------------------------------------------------------------------ #

    @app.callback(
        Output("overall-cytoscape-graph", "elements"),
        [
            Input("trace-id-dropdown", "value"),
            Input("time-range-slider", "value"),
            Input("main-tabs", "value"),
            Input("data-store", "data"),
        ],
    )
    def update_overall_graph(selected_trace_id, time_range, _active_tab, store_data):
        runtime_data, static_elements = _parse_store(store_data)
        if runtime_data.empty:
            return []

        start_dt = pd.to_datetime(time_range[0], unit="s")
        end_dt = pd.to_datetime(time_range[1], unit="s")
        filtered_data = runtime_data[
            (runtime_data["timestamp"] >= start_dt) & (runtime_data["timestamp"] <= end_dt)
        ]
        global_min_count, global_max_count = get_global_incoming_range(runtime_data)
        return build_overall_graph_elements(
            filtered_data,
            global_min_count,
            global_max_count,
            selected_trace_id,
            static_elements,
        )

    # ------------------------------------------------------------------ #
    # Graph: Span                                                        #
    # ------------------------------------------------------------------ #

    @app.callback(
        Output("span-id-dropdown", "options"),
        Input("trace-id-dropdown", "value"),
        State("data-store", "data"),
    )
    def update_span_id_dropdown(selected_trace_id, store_data):
        if not selected_trace_id:
            return []
        runtime_data, _ = _parse_store(store_data)
        if runtime_data.empty:
            return []
        filtered_df = runtime_data[runtime_data["trace_id"] == selected_trace_id]
        span_ids = filtered_df["transaction_id"].dropna().unique()
        return [
            {
                "label": (f"{str(s)[:12]}..." if len(str(s)) > 12 else str(s)),
                "value": s,
            }
            for s in span_ids
        ]

    @app.callback(
        [
            Output("span-cytoscape-graph", "elements"),
            Output("span-cytoscape-graph", "stylesheet"),
            Output("span-event-table", "children"),
        ],
        [Input("span-id-dropdown", "value"), Input("time-range-slider", "value")],
        State("data-store", "data"),
    )
    def update_span_graph(selected_span_id, time_range, store_data):
        if not selected_span_id:
            return [], overall_stylesheet, "No span_id selected."

        runtime_data, _ = _parse_store(store_data)
        if runtime_data.empty:
            return [], overall_stylesheet, "No data loaded."

        start_dt = pd.to_datetime(time_range[0], unit="s")
        end_dt = pd.to_datetime(time_range[1], unit="s")
        df = runtime_data[
            (runtime_data["transaction_id"] == selected_span_id)
            & (runtime_data["timestamp"] >= start_dt)
            & (runtime_data["timestamp"] <= end_dt)
        ].copy()

        if df.empty:
            return [], overall_stylesheet, "No runtime_data for selected span."

        return build_span_elements(df), overall_stylesheet, build_event_table(df)

    # ------------------------------------------------------------------ #
    # Heatmap                                                            #
    # ------------------------------------------------------------------ #

    @app.callback(
        Output("heatmap-graph", "figure"),
        [Input("service-name-dropdown", "value"), Input("time-range-slider", "value")],
        State("data-store", "data"),
    )
    def update_heatmap(selected_service, time_range, store_data):
        runtime_data, _ = _parse_store(store_data)
        if runtime_data.empty:
            return {}
        start_dt = pd.to_datetime(time_range[0], unit="s")
        end_dt = pd.to_datetime(time_range[1], unit="s")
        filtered_data = runtime_data[
            (runtime_data["timestamp"] >= start_dt) & (runtime_data["timestamp"] <= end_dt)
        ]
        return build_service_heatmap_figure(filtered_data, selected_service)

    # ------------------------------------------------------------------ #
    # Histograms                                                         #
    # ------------------------------------------------------------------ #

    @app.callback(
        Output("event-code-histogram", "figure"),
        Input("overall-cytoscape-graph", "tapEdgeData"),
        State("data-store", "data"),
    )
    def update_event_code_histogram(_edge_data, store_data):
        runtime_data, _ = _parse_store(store_data)
        return build_all_event_code_histogram(runtime_data)

    @app.callback(
        [
            Output("edge-histogram-modal", "is_open"),
            Output("edge-eventcode-histogram", "figure"),
        ],
        [Input("overall-cytoscape-graph", "tapEdgeData")],
        [State("edge-histogram-modal", "is_open"), State("data-store", "data")],
    )
    def show_edge_histogram(edge_data, is_open, store_data):
        _ = is_open
        if edge_data:
            runtime_data, _ = _parse_store(store_data)
            source = edge_data["source"]
            target = edge_data["target"]
            fig = build_edge_event_code_histogram(runtime_data, source, target)
            if isinstance(fig, dict) and fig:
                return True, fig
        return False, {}

    @app.callback(
        [Output("selected-edge-modal", "is_open"), Output("selected-edge-violinplot", "figure")],
        [Input("cytoscape-graph", "tapEdgeData")],
        [
            State("selected-edge-modal", "is_open"),
            State("trace-id-dropdown", "value"),
            State("time-range-slider", "value"),
            State("data-store", "data"),
        ],
    )
    def show_selected_edge_violinplot(edge_data, is_open, selected_trace_id, time_range, store_data):
        _ = is_open
        if edge_data and selected_trace_id:
            runtime_data, _ = _parse_store(store_data)
            source = edge_data["source"]
            target = edge_data["target"]
            start_dt = pd.to_datetime(time_range[0], unit="s")
            end_dt = pd.to_datetime(time_range[1], unit="s")
            filtered_df = runtime_data[
                (runtime_data["trace_id"] == selected_trace_id)
                & (runtime_data["service_name"] == source)
                & (runtime_data["callee"] == target)
                & (runtime_data["timestamp"] >= start_dt)
                & (runtime_data["timestamp"] <= end_dt)
            ]
            fig = build_selected_edge_violinplot(filtered_df, source, target)
            if isinstance(fig, dict) and fig:
                return True, fig
        return False, {}

    # ------------------------------------------------------------------ #
    # Trace Replay                                                        #
    # ------------------------------------------------------------------ #

    @app.callback(
        [
            Output("replay-step", "data"),
            Output("replay-step-slider", "min"),
            Output("replay-step-slider", "max"),
            Output("replay-step-slider", "marks"),
            Output("replay-step-slider", "value"),
            Output("replay-interval", "disabled"),
            Output("replay-play-btn", "children"),
        ],
        [
            Input("trace-id-dropdown", "value"),
            Input("data-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def reset_replay_on_trace_change(trace_id, store_data):
        runtime_data, _ = _parse_store(store_data)
        N = 0
        if not runtime_data.empty and trace_id:
            N = len(runtime_data[runtime_data["trace_id"] == trace_id])
        max_step = max(N - 1, 0)
        marks = {0: "1", max_step: str(N)} if N > 0 else {0: "0"}
        return 0, 0, max_step, marks, 0, True, "Play"

    @app.callback(
        [
            Output("replay-step", "data", allow_duplicate=True),
            Output("replay-interval", "disabled", allow_duplicate=True),
            Output("replay-play-btn", "children", allow_duplicate=True),
        ],
        [
            Input("replay-prev-btn", "n_clicks"),
            Input("replay-next-btn", "n_clicks"),
            Input("replay-play-btn", "n_clicks"),
            Input("replay-interval", "n_intervals"),
            Input("replay-step-slider", "value"),
        ],
        [
            State("replay-step", "data"),
            State("replay-interval", "disabled"),
            State("trace-id-dropdown", "value"),
            State("data-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def handle_replay_controls(_prev, _next, _play, _n_intervals, slider_val, current_step, interval_disabled, trace_id, store_data):
        triggered = ctx.triggered_id

        runtime_data, _ = _parse_store(store_data)
        N = 0
        if not runtime_data.empty and trace_id:
            N = len(runtime_data[runtime_data["trace_id"] == trace_id])

        step = current_step if current_step is not None else 0
        disabled = interval_disabled if interval_disabled is not None else True
        play_label = "Pause" if not disabled else "Play"

        if triggered == "replay-prev-btn":
            step = max(0, step - 1)
        elif triggered == "replay-next-btn":
            step = min(max(N - 1, 0), step + 1)
        elif triggered == "replay-play-btn":
            disabled = not disabled
            play_label = "Pause" if not disabled else "Play"
        elif triggered == "replay-interval":
            if N > 0:
                step += 1
                if step >= N:
                    step = N - 1
                    disabled = True
                    play_label = "Play"
        elif triggered == "replay-step-slider":
            step = slider_val if slider_val is not None else 0

        return step, disabled, play_label

    @app.callback(
        [
            Output("trace-replay-graph", "elements"),
            Output("trace-replay-graph", "stylesheet"),
            Output("replay-step-label", "children"),
            Output("replay-info-panel", "children"),
        ],
        [
            Input("replay-step", "data"),
            Input("trace-id-dropdown", "value"),
        ],
        State("data-store", "data"),
        prevent_initial_call=True,
    )
    def render_replay_graph(step, trace_id, store_data):
        runtime_data, _ = _parse_store(store_data)

        if runtime_data.empty or not trace_id:
            return [], _REPLAY_STYLESHEET, "No trace selected", ""

        df = (
            runtime_data[runtime_data["trace_id"] == trace_id]
            .sort_values("timestamp")
            .reset_index(drop=True)
        )

        if df.empty:
            return [], _REPLAY_STYLESHEET, "No calls for this trace", ""

        N = len(df)
        step = min(step or 0, N - 1)

        services = set(df["service_name"].dropna()) | set(df["callee"].dropna())
        cy_nodes = [{"data": {"id": s, "label": s}} for s in services]

        cy_edges = []
        for i, row in df.iterrows():
            if i < step:
                cls = "edge-completed"
            elif i == step:
                cls = "edge-active"
            else:
                cls = "edge-future"
            short_fn = row["event_code"].split(".")[-1] if pd.notna(row.get("event_code")) else ""
            cy_edges.append({
                "data": {
                    "id": f"replay-edge-{i}",
                    "source": row["service_name"],
                    "target": row["callee"],
                    "label": short_fn,
                },
                "classes": cls,
            })

        row = df.iloc[step]
        duration_str = f"{row['call_duration']:.1f}ms" if pd.notna(row.get("call_duration")) else "N/A"
        ts_str = str(row["timestamp"])[:19] if pd.notna(row.get("timestamp")) else "N/A"
        info_panel = dbc.Card(
            dbc.CardBody([
                html.H6(f"{row['service_name']} → {row['callee']}", className="card-title mb-1"),
                html.Code(
                    str(row.get("event_code", "")),
                    style={"fontSize": "12px", "display": "block", "marginBottom": "4px"},
                ),
                html.Small(f"Time: {ts_str}  |  Duration: {duration_str}", className="text-muted"),
            ]),
            style={"marginTop": "10px"},
        )

        return cy_nodes + cy_edges, _REPLAY_STYLESHEET, f"Step {step + 1} / {N}", info_panel
