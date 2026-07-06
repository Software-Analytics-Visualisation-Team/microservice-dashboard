"""Dash callback registrations."""

import pandas as pd
from copy import deepcopy
from dash import Input, Output, State, ctx, html
import dash_bootstrap_components as dbc

from msviz.analysis.neo4j_client import Neo4jClient

from .graphs import (
    build_all_event_code_histogram,
    build_edge_event_code_histogram,
    build_event_table,
    build_full_hierarchy_elements,
    build_selected_edge_violinplot,
    build_service_heatmap_figure,
    build_service_hierarchy_panel,
    build_span_elements,
    build_trace_elements,
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
    "trace-section": {_SECTION_TAB_RUNTIME, _SECTION_TAB_TRACE_GRAPH, _SECTION_TAB_SPAN_GRAPH, _SECTION_TAB_EVENT_TABLE, _SECTION_TAB_TRACE_REPLAY},
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
            "line-color": "#8c9197",
            "target-arrow-color": "#8c9197",
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


def _rows_to_df(rows):
    """Return a runtime DataFrame from a list of Neo4jClient invocation rows."""
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["call_duration"] = pd.to_numeric(df["call_duration"], errors="coerce") * 1000
    return df


def register_callbacks(app, overall_stylesheet):

    # ------------------------------------------------------------------ #
    # Dropdown population                                                #
    # ------------------------------------------------------------------ #

    @app.callback(
        [
            Output("trace-id-dropdown", "options"),
            Output("trace-id-dropdown", "value")
        ],
        Input("time-range-slider", "value")
    )
    def update_trace_dropdown(time_range):
        start_dt = pd.to_datetime(time_range[0], unit="s")
        end_dt = pd.to_datetime(time_range[1], unit="s")

        data = Neo4jClient.retrieve_trace_ids(start_dt, end_dt)

        elements = [{"label": (f"{str(trace_id)[:8]}..." if len(str(trace_id)) > 8 else str(trace_id)), "value": trace_id} for trace_id in data]
        return elements, "-"

    @app.callback(
        [Output("service-name-dropdown", "options"), Output("service-name-dropdown", "value")],
        Input("time-range-slider", "value"),
    )
    def update_service_dropdown(time_range):
        start_dt = pd.to_datetime(time_range[0], unit="s")
        end_dt = pd.to_datetime(time_range[1], unit="s")

        service_names = Neo4jClient.retrieve_service_names(start_dt, end_dt)
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
        ],
    )
    def update_dashboard(selected_trace_id, time_range, _active_tab):
        if not selected_trace_id or selected_trace_id == "-":
            return [], "No trace_id selected."

        start_dt = pd.to_datetime(time_range[0], unit="s")
        end_dt = pd.to_datetime(time_range[1], unit="s")

        rows = Neo4jClient.retrieve_trace_invocations(selected_trace_id, start_dt, end_dt)
        df = _rows_to_df(rows)
        if df.empty:
            return [], "No data for selected trace."

        return build_trace_elements(df), build_event_table(df)

    # ------------------------------------------------------------------ #
    # Graph: Runtime Dependency (all data)                               #
    # ------------------------------------------------------------------ #

    @app.callback(
        Output("overall-cytoscape-graph", "elements"),
        [
            Input("trace-id-dropdown", "value"),
            Input("time-range-slider", "value"),
            Input("main-tabs", "value")
        ],
    )
    def update_overall_graph(selected_trace_id, time_range, _active_tab):
        start_dt = pd.to_datetime(time_range[0], unit="s")
        end_dt = pd.to_datetime(time_range[1], unit="s")
        
        data = Neo4jClient.retrieve_full_dependency_graph(start_dt, end_dt)
        
        elements = []
        for service in data['nodes']:
            is_parent = service["properties"]["moduleCount"] > 0
            hex_color = "#5bc0de" if is_parent else "#f0ad4e"

            elements.append({
                'data': {
                    'id': service['id'],
                    'label': service['name'],
                },
                'style': {
                    'background-color': hex_color,
                    'shape': 'rectangle' if is_parent else 'circle'
                }
            })
        
        for edge in data['edges']:
            edge_props = edge.get('properties', {})

            classes = 'flow' if edge['source_type'] == 'dynamic' else 'static-edge'
            classes += ' selected' if edge_props.get('trace_ids') and selected_trace_id in edge_props.get('trace_ids', []) else ''
            
            elements.append({
                'data': {
                    'source': edge['source'],
                    'target': edge['target'],
                    'label': f"Calls: {edge_props.get('call_count', 0)}"
                },
                'classes': classes
            })

        return elements

    # ------------------------------------------------------------------ #
    # Graph: Full Hierarchy                                              #
    # ------------------------------------------------------------------ #

    @app.callback(
        Output("hierarchy-cytoscape-graph", "elements"),
        Input("main-tabs", "value"),
    )
    def update_full_hierarchy_graph(_active_tab):
        graph = Neo4jClient.retrieve_full_hierarchy_graph()
        return build_full_hierarchy_elements(graph)

    # ------------------------------------------------------------------ #
    # Graph: Span                                                        #
    # ------------------------------------------------------------------ #

    @app.callback(
        Output("span-id-dropdown", "options"),
        Input("trace-id-dropdown", "value"),
    )
    def update_span_id_dropdown(selected_trace_id):
        if not selected_trace_id or selected_trace_id == "-":
            return []
        span_ids = Neo4jClient.retrieve_span_ids(selected_trace_id)
        return [
            {
                "label": (f"{str(s)[:12]}..." if len(str(s)) > 12 else str(s)),
                "value": s,
            }
            for s in span_ids
            if s
        ]

    @app.callback(
        [
            Output("span-cytoscape-graph", "elements"),
            Output("span-cytoscape-graph", "stylesheet"),
            Output("span-event-table", "children"),
        ],
        [Input("span-id-dropdown", "value"), Input("time-range-slider", "value")],
    )
    def update_span_graph(selected_span_id, time_range):
        if not selected_span_id:
            return [], overall_stylesheet, "No span_id selected."

        start_dt = pd.to_datetime(time_range[0], unit="s")
        end_dt = pd.to_datetime(time_range[1], unit="s")

        rows = Neo4jClient.retrieve_span_invocations(selected_span_id, start_dt, end_dt)
        df = _rows_to_df(rows)
        if df.empty:
            return [], overall_stylesheet, "No runtime_data for selected span."

        return build_span_elements(df), overall_stylesheet, build_event_table(df)

    # ------------------------------------------------------------------ #
    # Heatmap                                                            #
    # ------------------------------------------------------------------ #

    @app.callback(
        Output("heatmap-graph", "figure"),
        [Input("service-name-dropdown", "value"), Input("time-range-slider", "value")],
    )
    def update_heatmap(selected_service, time_range):
        if not selected_service:
            return {}
        start_dt = pd.to_datetime(time_range[0], unit="s")
        end_dt = pd.to_datetime(time_range[1], unit="s")

        rows = Neo4jClient.retrieve_service_invocations(selected_service, start_dt, end_dt)
        df = _rows_to_df(rows)
        if df.empty:
            return {}
        return build_service_heatmap_figure(df, selected_service)

    # ------------------------------------------------------------------ #
    # Histograms                                                         #
    # ------------------------------------------------------------------ #

    @app.callback(
        Output("event-code-histogram", "figure"),
        [Input("time-range-slider", "value"), Input("main-tabs", "value")],
    )
    def update_event_code_histogram(time_range, _active_tab):
        start_dt = pd.to_datetime(time_range[0], unit="s")
        end_dt = pd.to_datetime(time_range[1], unit="s")

        rows = Neo4jClient.retrieve_all_invocations(start_dt, end_dt)
        df = _rows_to_df(rows)
        if df.empty:
            return {}
        return build_all_event_code_histogram(df)

    @app.callback(
        [
            Output("edge-histogram-modal", "is_open"),
            Output("edge-eventcode-histogram", "figure"),
        ],
        [Input("overall-cytoscape-graph", "tapEdgeData")],
        [State("edge-histogram-modal", "is_open"), State("time-range-slider", "value")],
    )
    def show_edge_histogram(edge_data, is_open, time_range):
        _ = is_open
        if edge_data:
            start_dt = pd.to_datetime(time_range[0], unit="s")
            end_dt = pd.to_datetime(time_range[1], unit="s")
            rows = Neo4jClient.retrieve_invocations_between_services(
                edge_data["source"], edge_data["target"], start_dt, end_dt
            )
            df = _rows_to_df(rows)
            if not df.empty:
                source_name = df["service_name"].iloc[0]
                target_name = df["callee"].iloc[0]
                fig = build_edge_event_code_histogram(df, source_name, target_name)
                if not isinstance(fig, dict):
                    return True, fig
        return False, {}

    @app.callback(
        [
            Output("service-detail-modal", "is_open"),
            Output("service-modal-title", "children"),
            Output("service-info-panel", "children"),
            Output("service-hierarchy-panel", "children"),
        ],
        Input("overall-cytoscape-graph", "tapNodeData"),
        State("time-range-slider", "value"),
        prevent_initial_call=True,
    )
    def show_service_detail(node_data, time_range):
        if not node_data:
            return False, "", [], []

        service_id = node_data["id"]
        service_name = node_data.get("label", service_id)
        start_dt = pd.to_datetime(time_range[0], unit="s")
        end_dt = pd.to_datetime(time_range[1], unit="s")
        detail = Neo4jClient.retrieve_service_detail(service_id, start_dt, end_dt)

        # ── Info panel ──────────────────────────────────────────────────
        deps = detail["dependencies"]
        info = [
            html.H5(service_name, className="mb-3"),
            html.P([html.Strong("Outgoing calls: "), str(detail["outgoing"])]),
            html.P([html.Strong("Incoming calls: "), str(detail["incoming"])]),
            html.P(html.Strong("Static dependencies:")),
            html.Ul([html.Li(d) for d in deps]) if deps else html.P("None", className="text-muted"),
        ]

        # ── Hierarchy panel ──────────────────────────────────────────────
        hierarchy = build_service_hierarchy_panel(detail["hierarchy"])

        return True, service_name, info, hierarchy

    @app.callback(
        [Output("selected-edge-modal", "is_open"), Output("selected-edge-violinplot", "figure")],
        [Input("cytoscape-graph", "tapEdgeData")],
        [
            State("selected-edge-modal", "is_open"),
            State("trace-id-dropdown", "value"),
            State("time-range-slider", "value"),
        ],
    )
    def show_selected_edge_violinplot(edge_data, is_open, selected_trace_id, time_range):
        _ = is_open
        if edge_data and selected_trace_id:
            source = edge_data["source"]
            target = edge_data["target"]
            start_dt = pd.to_datetime(time_range[0], unit="s")
            end_dt = pd.to_datetime(time_range[1], unit="s")
            rows = Neo4jClient.retrieve_trace_edge_invocations(
                selected_trace_id, source, target, start_dt, end_dt
            )
            df = _rows_to_df(rows)
            if not df.empty:
                fig = build_selected_edge_violinplot(df, source, target)
                if not isinstance(fig, dict):
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
        ],
        prevent_initial_call=True,
    )
    def reset_replay_on_trace_change(trace_id):
        data = Neo4jClient.retrieve_call_graph_for_trace(trace_id)
        edges = data["edges"]

        N = len(edges) if edges else 0
        max_step = max(N - 1, 0)
        marks = {0: "1", max_step: str(N)} if N > 0 else {0: "0"}
        return {"step": 0, "trace_id": trace_id}, 0, max_step, marks, 0, True, "Play"

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
        ],
        prevent_initial_call=True,
    )
    def handle_replay_controls(_prev, _next, _play, _n_intervals, slider_val, current_step_data, interval_disabled, trace_id):
        triggered = ctx.triggered_id

        data = Neo4jClient.retrieve_call_graph_for_trace(trace_id)
        edges = data["edges"]

        N = len(edges) if edges else 0

        step = (current_step_data or {}).get("step", 0)
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

        return {"step": step, "trace_id": trace_id}, disabled, play_label

    @app.callback(
        [
            Output("trace-replay-graph", "elements"),
            Output("trace-replay-graph", "stylesheet"),
            Output("replay-step-label", "children"),
            Output("replay-info-panel", "children"),
        ],
        [
            Input("replay-step", "data"),
        ],
        prevent_initial_call=True,
    )
    def render_replay_graph(step_data):
        step_data = step_data or {}
        trace_id = step_data.get("trace_id")
        step = step_data.get("step", 0)

        if not trace_id or trace_id == "-":
            return [], _REPLAY_STYLESHEET, "No trace selected", ""

        data = Neo4jClient.retrieve_call_graph_for_trace(trace_id)
        nodes = data["nodes"]
        edges = data["edges"]

        if len(nodes) == 0 or len(edges) == 0:
            return [], _REPLAY_STYLESHEET, "No calls for this trace", ""

        cy_nodes = []
        for node in nodes:
            cy_nodes.append({
                "data": {
                    "id": node["id"],
                    "label": node["name"],
                },
                "classes": "node",
            })

        N = len(edges)
        step = min(step or 0, N - 1)

        active_edge = None
        cy_edges = []
        for i, edge in enumerate(edges):
            if i < step:
                cls = "edge-completed"
            elif i == step:
                active_edge = edge
                cls = "edge-active"
            else:
                cls = "edge-future"
            cy_edges.append({
                "data": {
                    "id": f"replay-edge-{trace_id}-{i}",
                    "source": edge["source"],
                    "target": edge["target"],
                    "label": edge["label"],
                },
                "classes": cls,
            })

        duration_str = f"{active_edge['properties']['duration']:.1f}ms" if active_edge and pd.notna(active_edge['properties'].get("duration")) else "N/A"
        ts_str = str(active_edge['properties']['timestamp'])[:19] if active_edge and pd.notna(active_edge['properties'].get("timestamp")) else "N/A"
        info_panel = dbc.Card(
            dbc.CardBody([
                html.H6(f"{active_edge['source']} -> {active_edge['target']}", className="card-title mb-1"),
                html.Code(
                    str(active_edge['label']),
                    style={"fontSize": "12px", "display": "block", "marginBottom": "4px"},
                ),
                html.Small(f"Time: {ts_str}  |  Duration: {duration_str}", className="text-muted"),
            ]),
            style={"marginTop": "10px"},
        )

        return cy_nodes + cy_edges, _REPLAY_STYLESHEET, f"Step {step + 1} / {N}", info_panel
