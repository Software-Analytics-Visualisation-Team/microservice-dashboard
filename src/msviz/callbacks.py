"""Dash callback registrations."""

import pandas as pd
from dash import Input, Output, State

from .graphs import (
    build_all_event_code_histogram,
    build_edge_event_code_histogram,
    build_event_table,
    build_overall_graph_elements,
    build_selected_edge_violinplot,
    build_service_heatmap_figure,
    build_span_elements,
    build_trace_elements,
    get_global_incoming_range,
)


def register_callbacks(app, data, overall_stylesheet):
    global_min_count, global_max_count = get_global_incoming_range(data)

    def _is_empty_figure(figure):
        return isinstance(figure, dict) and not figure

    @app.callback(
        [
            Output("cytoscape-graph", "elements"),
            Output("cytoscape-graph", "stylesheet"),
            Output("event-table", "children"),
            Output("overall-cytoscape-graph", "elements"),
        ],
        [Input("trace-id-dropdown", "value"), Input("time-range-slider", "value")],
    )
    def update_dashboard(selected_trace_id, time_range):
        start_dt = pd.to_datetime(time_range[0], unit="s")
        end_dt = pd.to_datetime(time_range[1], unit="s")

        filtered_data = data[
            (data["timestamp"] >= start_dt) & (data["timestamp"] <= end_dt)
        ]

        if not selected_trace_id:
            return [], overall_stylesheet, "No trace_id selected.", []

        df = filtered_data[filtered_data["trace_id"] == selected_trace_id]

        elements = build_trace_elements(df)
        table_html = build_event_table(df)
        overall_elements = build_overall_graph_elements(
            filtered_data, global_min_count, global_max_count, selected_trace_id
        )

        return elements, overall_stylesheet, table_html, overall_elements

    @app.callback(
        Output("slider-tooltip", "children"), Input("time-range-slider", "value")
    )
    def update_slider_tooltip(value):
        start = pd.to_datetime(value[0], unit="s").strftime("%Y-%m-%d %H:%M:%S")
        end = pd.to_datetime(value[1], unit="s").strftime("%Y-%m-%d %H:%M:%S")
        return f"{start}  to  {end}"

    @app.callback(
        Output("event-code-histogram", "figure"),
        Input("overall-cytoscape-graph", "tapEdgeData"),
    )
    def update_event_code_histogram(_edge_data):
        return build_all_event_code_histogram(data)

    @app.callback(
        Output("span-id-dropdown", "options"), Input("trace-id-dropdown", "value")
    )
    def update_span_id_dropdown(selected_trace_id):
        if not selected_trace_id:
            return []

        filtered_df = data[data["trace_id"] == selected_trace_id]
        span_ids = filtered_df["transaction_id"].dropna().unique()
        return [
            {
                "label": (
                    f"{str(span_id)[:12]}..." if len(str(span_id)) > 12 else str(span_id)
                ),
                "value": span_id,
            }
            for span_id in span_ids
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

        df = data[
            (data["transaction_id"] == selected_span_id)
            & (data["timestamp"] >= start_dt)
            & (data["timestamp"] <= end_dt)
        ].copy()

        if df.empty:
            return [], overall_stylesheet, "No data for selected span."

        elements = build_span_elements(df)
        table_html = build_event_table(df)
        return elements, overall_stylesheet, table_html

    @app.callback(
        Output("heatmap-graph", "figure"),
        [Input("service-name-dropdown", "value"), Input("time-range-slider", "value")],
    )
    def update_heatmap(selected_service, time_range):
        start_dt = pd.to_datetime(time_range[0], unit="s")
        end_dt = pd.to_datetime(time_range[1], unit="s")
        filtered_data = data[
            (data["timestamp"] >= start_dt) & (data["timestamp"] <= end_dt)
        ]
        return build_service_heatmap_figure(filtered_data, selected_service)

    @app.callback(
        [
            Output("edge-histogram-modal", "is_open"),
            Output("edge-eventcode-histogram", "figure"),
        ],
        [Input("overall-cytoscape-graph", "tapEdgeData")],
        [State("edge-histogram-modal", "is_open")],
    )
    def show_edge_histogram(edge_data, is_open):
        _ = is_open
        if edge_data:
            source = edge_data["source"]
            target = edge_data["target"]
            fig = build_edge_event_code_histogram(data, source, target)
            if not _is_empty_figure(fig):
                return True, fig
        return False, {}

    @app.callback(
        [Output("selected-edge-modal", "is_open"), Output("selected-edge-violinplot", "figure")],
        [Input("cytoscape-graph", "tapEdgeData")],
        [
            State("selected-edge-modal", "is_open"),
            State("trace-id-dropdown", "value"),
            State("time-range-slider", "value"),
        ],
    )
    def show_selected_edge_violinplot(
        edge_data, is_open, selected_trace_id, time_range
    ):
        _ = is_open
        if edge_data and selected_trace_id:
            source = edge_data["source"]
            target = edge_data["target"]
            start_dt = pd.to_datetime(time_range[0], unit="s")
            end_dt = pd.to_datetime(time_range[1], unit="s")

            filtered_df = data[
                (data["trace_id"] == selected_trace_id)
                & (data["service_name"] == source)
                & (data["callee"] == target)
                & (data["timestamp"] >= start_dt)
                & (data["timestamp"] <= end_dt)
            ]
            fig = build_selected_edge_violinplot(filtered_df, source, target)
            if not _is_empty_figure(fig):
                return True, fig
        return False, {}
