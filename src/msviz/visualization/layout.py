"""Dash layout builder."""

import dash_bootstrap_components as dbc
import dash_cytoscape as cyto
import plotly.express as px
from dash import dcc, html


def build_layout(context, data, overall_stylesheet):
    sidebar = dbc.Col(
        [
            html.H5("Controls", className="mb-3"),
            html.Div(f"Total records: {context.num_records}"),
            html.Div(f"Start time: {context.first_timestamp}"),
            html.Div(f"End time: {context.last_timestamp}"),
            html.Label("Select Time Range:", style={"marginTop": "40px"}),
            html.Div(
                id="slider-tooltip",
                style={"marginBottom": "10px", "fontWeight": "bold"},
            ),
            dcc.RangeSlider(
                id="time-range-slider",
                min=context.min_timestamp,
                max=context.max_timestamp,
                value=[context.min_timestamp, context.max_timestamp],
                marks={
                    context.min_timestamp: context.first_timestamp,
                    context.max_timestamp: context.last_timestamp,
                },
                step=1,
            ),
            html.Label("Select Trace ID:", style={"marginTop": "40px"}),
            dcc.Dropdown(
                id="trace-id-dropdown",
                options=[
                    {
                        "label": (f"{str(tid)[:8]}..." if len(str(tid)) > 8 else str(tid)),
                        "value": tid,
                    }
                    for tid in context.trace_ids
                ],
                value=context.trace_ids[0] if context.trace_ids else None,
                placeholder="Select a trace_id",
            ),
            html.Label("Select Span ID:", style={"marginTop": "40px"}),
            dcc.Dropdown(
                id="span-id-dropdown",
                options=[],
                value=None,
                placeholder="Select a transaction_id (Span ID)",
            ),
            html.H5("Heatmap controls", style={"marginTop": "40px"}),
            html.Label("Select Service Name:"),
            dcc.Dropdown(
                id="service-name-dropdown",
                options=[{"label": name, "value": name} for name in context.service_names],
                value=context.service_names[0] if context.service_names else None,
                placeholder="Select a service_name",
            ),
        ],
        width=2,
        style={
            "height": "100vh",
            "overflowY": "auto",
            "background": "#f8f9fa",
            "padding": "25px",
        },
    )

    main_content = dbc.Col(
        [
            dcc.Tabs(
                [
                    dcc.Tab(
                        label="Runtime Dependency Graph",
                        children=[
                            html.H4(
                                "Overall Service to Callee Service Graph (All Data)",
                                style={"marginTop": "40px"},
                            ),
                            html.Div(
                                cyto.Cytoscape(
                                    id="overall-cytoscape-graph",
                                    layout={
                                        "name": "breadthfirst",
                                        "directed": True,
                                        "padding": 10,
                                    },
                                    style={"width": "100%", "height": "800px"},
                                    elements=[],
                                    stylesheet=overall_stylesheet,
                                ),
                                style={
                                    "border": "2px solid #0074D9",
                                    "borderRadius": "8px",
                                    "padding": "10px",
                                    "background": "#fff",
                                },
                            ),
                            dbc.Modal(
                                [
                                    dbc.ModalHeader(dbc.ModalTitle("Call Counts Histogram")),
                                    dbc.ModalBody(dcc.Graph(id="edge-eventcode-histogram")),
                                ],
                                id="edge-histogram-modal",
                                size="lg",
                                is_open=False,
                            ),
                        ],
                    ),
                    dcc.Tab(
                        label="Selected Trace Graph",
                        children=[
                            html.H4(
                                "Service to Callee Service Graph (Selected trace_id)",
                                style={"marginTop": "40px"},
                            ),
                            html.Div(
                                cyto.Cytoscape(
                                    id="cytoscape-graph",
                                    layout={
                                        "name": "breadthfirst",
                                        "directed": True,
                                        "padding": 10,
                                    },
                                    style={"width": "100%", "height": "800px"},
                                    elements=[],
                                    stylesheet=overall_stylesheet,
                                ),
                                style={
                                    "border": "2px solid #0074D9",
                                    "borderRadius": "8px",
                                    "padding": "10px",
                                    "background": "#fff",
                                },
                            ),
                            dbc.Modal(
                                [
                                    dbc.ModalHeader(
                                        dbc.ModalTitle("Call Duration Violin Plot")
                                    ),
                                    dbc.ModalBody(dcc.Graph(id="selected-edge-violinplot")),
                                ],
                                id="selected-edge-modal",
                                size="lg",
                                is_open=False,
                            ),
                        ],
                    ),
                    dcc.Tab(
                        label="Selected Span Graph",
                        children=[
                            html.H4(
                                "Service to Callee Service Graph (Selected span_id)",
                                style={"marginTop": "40px"},
                            ),
                            html.Div(
                                cyto.Cytoscape(
                                    id="span-cytoscape-graph",
                                    layout={
                                        "name": "breadthfirst",
                                        "directed": True,
                                        "padding": 10,
                                    },
                                    style={"width": "100%", "height": "800px"},
                                    elements=[],
                                    stylesheet=overall_stylesheet,
                                ),
                                style={
                                    "border": "2px solid #0074D9",
                                    "borderRadius": "8px",
                                    "padding": "10px",
                                    "background": "#fff",
                                },
                            ),
                            html.Div(id="span-event-table"),
                        ],
                    ),
                    dcc.Tab(
                        label="Call Counts Histogram",
                        children=[
                            html.H4("Call Counts Histogram (All Data)", style={"marginTop": "40px"}),
                            dcc.Graph(
                                id="event-code-histogram",
                                figure=px.histogram(data, x="event_code", title="Call Counts"),
                                style={"height": "600px"},
                            ),
                        ],
                    ),
                    dcc.Tab(
                        label="Call Duration Heatmap",
                        children=[
                            html.H4(
                                "Call Duration Heatmap (Selected Service)",
                                style={"marginTop": "40px"},
                            ),
                            dcc.Graph(id="heatmap-graph", style={"height": "800px"}),
                        ],
                    ),
                    dcc.Tab(
                        label="Event Table",
                        children=[
                            html.H4("Event Table (Selected Trace)", style={"marginTop": "40px"}),
                            html.Div(id="event-table"),
                        ],
                    ),
                ]
            )
        ],
        width=10,
    )

    return dbc.Container(
        [dbc.Row([sidebar, main_content], style={"margin": "0", "height": "100vh"})],
        fluid=True,
    )
