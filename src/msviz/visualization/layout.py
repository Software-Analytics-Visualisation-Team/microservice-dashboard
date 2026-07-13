"""Dash layout builder."""

import dash_bootstrap_components as dbc
import dash_cytoscape as cyto
from dash import dcc, html


def build_layout(context, overall_stylesheet, runtime_data_json=None, static_data=None):
    sidebar = dbc.Col(
        [
            html.H5("Controls", className="mb-3", style={"marginTop": "20px"}),
            html.Div(
                [
                    html.Label("Import CSV files:", style={"fontWeight": "bold", "marginBottom": "8px"}),
                    html.Div(
                        [
                            dcc.Upload(
                                id="static-data-upload",
                                children=dbc.Button(
                                    "Import static data",
                                    color="secondary",
                                    size="sm",
                                ),
                                multiple=False,
                                style={"display": "inline-block","marginBottom": "10px"},
                            ),
                        ]
                    ),
                    html.Div(
                        [
                            dcc.Upload(
                                id="runtime-data-upload",
                                children=dbc.Button(
                                    "Import runtime data",
                                    color="secondary",
                                    size="sm",
                                ),
                                multiple=False,
                                style={"display": "inline-block"},
                            ),
                        ]
                    ),
                    html.Div(
                        id="static-data-upload-status",
                        style={"marginTop": "8px", "fontSize": "0.85rem", "color": "#495057"},
                    ),
                    html.Div(
                        id="runtime-data-upload-status",
                        style={"fontSize": "0.85rem", "color": "#495057"},
                    ),
                ],
                style={"marginBottom": "20px"},
            ),
            html.Div(f"Total records: {context.num_records}", id="record-count"),
            html.Div(f"Start time: {context.first_timestamp}", id="start-time"),
            html.Div(f"End time: {context.last_timestamp}", id="end-time"),
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
            html.H5("Heatmap controls", className="mb-3", style={"marginTop": "40px"}),
            html.Label("Select Caller Service:"),
            dcc.Dropdown(
                id="service-name-dropdown",
                options=[{"label": name, "value": name} for name in context.service_names],
                value=context.service_names[0] if context.service_names else None,
                placeholder="Select a service_name",
            ),
            html.Label("Select Callee Service:"),
            dcc.Dropdown(
                id="callee-service-name-dropdown",
                options=[{"label": name, "value": name} for name in context.callee],
                value=(context.callee[0] if context.callee else None),
                placeholder="Select a service_name",
            ),
            dbc.Switch(
                id="static-edges-toggle",
                label="Show static dependencies",
                value=False,
                style={"marginTop": "20px"},
            ),
            dbc.Switch(
                id="flow-animation-toggle",
                label="Animate edge flow",
                value=False,
                style={"marginTop": "20px"},
            ),
            html.H5("Compare Trace controls", className="mb-3", style={"marginTop": "40px"}),
            dbc.Switch(
                id="selected-edges-in-both-traces-toggle",
                label="Show edges common to both traces",
                value=False,
                style={"marginTop": "20px","color": "green"},
            ),
            dbc.Switch(
                id="selected-edges-in-trace-A-toggle",
                label="Show edges only in trace A",
                value=False,
                style={"marginTop": "20px","color": "blue"},
            ),
            dbc.Switch(
                id="selected-edges-in-trace-B-toggle",
                label="Show edges only in trace B",
                value=False,
                style={"marginTop": "20px","color": "orange"},
            ),
            html.H5("Node Information", className="mb-3", style={"marginTop": "40px"}),
            html.Div(id="node-info", children="Click a node to see functions."),
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
                id="main-tabs",
                value="runtime-dependency-graph",
                children=[
                    dcc.Tab(
                        label="Runtime Dependency Graph",
                        value="runtime-dependency-graph",
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
                        value="selected-trace-graph",
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
                        label="Compare Traces",
                        value="compare-traces",
                        children=[
                            html.H4("Compare Two Traces", style={"marginTop": "40px"}),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            html.Label("Trace A:"),
                                            dcc.Dropdown(
                                                id="trace-id-a-dropdown",
                                                options=[
                                                    {
                                                        "label": (
                                                            f"{str(tid)[:8]}..."
                                                            if len(str(tid)) > 8
                                                            else str(tid)
                                                        ),
                                                        "value": tid,
                                                    }
                                                    for tid in context.trace_ids
                                                ],
                                                placeholder="Select trace A",
                                            ),
                                        ],
                                        width=6,
                                    ),
                                    dbc.Col(
                                        [
                                            html.Label("Trace B:"),
                                            dcc.Dropdown(
                                                id="trace-id-b-dropdown",
                                                options=[
                                                    {
                                                        "label": (
                                                            f"{str(tid)[:8]}..."
                                                            if len(str(tid)) > 8
                                                            else str(tid)
                                                        ),
                                                        "value": tid,
                                                    }
                                                    for tid in context.trace_ids
                                                ],
                                                placeholder="Select trace B",
                                            ),
                                        ],
                                        width=6,
                                    ),
                                ],
                                style={"marginBottom": "20px"},
                            ),
                            html.Div(
                                cyto.Cytoscape(
                                    id="trace-compare-graph",
                                    layout={
                                        "name": "breadthfirst",
                                        "directed": True,
                                        "padding": 10,
                                    },
                                    style={"width": "100%", "height": "600px"},
                                    elements=[],
                                    stylesheet=overall_stylesheet,
                                ),
                                style={
                                    "border": "2px solid #0074D9",
                                    "borderRadius": "8px",
                                    "padding": "10px",
                                    "background": "#fff",
                                    "marginBottom": "20px",
                                },
                            ),
                            html.H5("Trace Edge Differences", style={"marginTop": "30px"}),
                            html.Div(id="trace-compare-table"),
                        ],
                    ),
                    dcc.Tab(
                        label="Selected Span Graph",
                        value="selected-span-graph",
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
                        value="call-counts-histogram",
                        children=[
                            html.H4("Call Counts Histogram (All Data)", style={"marginTop": "40px"}),
                            dcc.Graph(
                                id="event-code-histogram",
                                figure={},
                                style={"height": "600px"},
                            ),
                        ],
                    ),
                    dcc.Tab(
                        label="Call Duration Heatmap",
                        value="call-duration-heatmap",
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
                        value="event-table",
                        children=[
                            html.H4("Event Table (Selected Trace)", style={"marginTop": "40px"}),
                            html.Div(id="event-table"),
                        ],
                    ),
                ],
            )
        ],
        width=10,
    )

    return dbc.Container(
        [
            dcc.Store(id="runtime-data-store", data=runtime_data_json),
            dcc.Store(id="static-data-store", data=static_data),
            dcc.Interval(id="edge-flow-interval", interval=120, n_intervals=0),
            dbc.Row([sidebar, main_content], style={"margin": "0", "height": "100vh"}),
        ],
        fluid=True,
    )
