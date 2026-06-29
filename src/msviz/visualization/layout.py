"""Dash layout builder."""

import dash_bootstrap_components as dbc
import dash_cytoscape as cyto
from dash import dcc, html


def build_layout(context, overall_stylesheet, initial_data=None):
    sidebar = dbc.Col(
        [
            html.Div(
                id="upload-section",
                children=[
                    html.H6("Knowledge Graph", style={"marginBottom": "8px", "fontWeight": "600"}),
                    dcc.Upload(
                        id="graph-upload",
                        children=html.Div([
                            "Drag & Drop or ",
                            html.A("Browse", style={"color": "#0074D9", "cursor": "pointer"}),
                        ]),
                        style={
                            "width": "100%",
                            "padding": "12px 6px",
                            "borderWidth": "2px",
                            "borderStyle": "dashed",
                            "borderColor": "#adb5bd",
                            "borderRadius": "6px",
                            "textAlign": "center",
                            "fontSize": "13px",
                            "cursor": "pointer",
                        },
                        accept=".json",
                    ),
                    html.Div(
                        id="upload-status",
                        style={"fontSize": "12px", "marginTop": "6px", "color": "#198754"},
                    ),
                ],
                style={
                    "marginBottom": "20px",
                    "paddingBottom": "16px",
                    "borderBottom": "1px solid #dee2e6",
                },
            ),
            html.H5("Controls", className="mb-3"),
            html.Div(id="meta-records", children=f"Total records: {context.num_records}"),
            html.Div(id="meta-start", children=f"Start time: {context.first_timestamp}"),
            html.Div(id="meta-end", children=f"End time: {context.last_timestamp}"),
            html.Div(
                id="slider-section",
                children=[
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
                ],
            ),
            html.Div(
                id="trace-section",
                children=[
                    html.Label("Select Trace ID:", style={"marginTop": "40px"}),
                    dcc.Dropdown(
                        id="trace-id-dropdown",
                        options=[],
                        value=None,
                        placeholder="Select a trace_id",
                    ),
                ],
            ),
            html.Div(
                id="span-section",
                children=[
                    html.Label("Select Span ID:", style={"marginTop": "40px"}),
                    dcc.Dropdown(
                        id="span-id-dropdown",
                        options=[],
                        value=None,
                        placeholder="Select a transaction_id (Span ID)",
                    ),
                ],
            ),
            html.Div(
                id="heatmap-section",
                children=[
                    html.H5("Heatmap controls", style={"marginTop": "40px"}),
                    html.Label("Select Service Name:"),
                    dcc.Dropdown(
                        id="service-name-dropdown",
                        options=[],
                        value=None,
                        placeholder="Select a service_name",
                    ),
                ],
            ),
            html.Div(
                id="static-toggle-section",
                children=[
                    dbc.Switch(
                        id="static-edges-toggle",
                        label="Show static dependencies",
                        value=False,
                        style={"marginTop": "20px"},
                    ),
                ],
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
                                        "name": "preset",
                                        "animate": False,
                                        "padding": 30,
                                    },
                                    style={"width": "100%", "height": "max(600px, calc(100vh - 114px - 68px - 40px))"},
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
                            dbc.Modal(
                                [
                                    dbc.ModalHeader(dbc.ModalTitle(id="service-modal-title")),
                                    dbc.ModalBody(
                                        dbc.Row([
                                            dbc.Col(html.Div(id="service-info-panel"), width=4),
                                            dbc.Col(html.Div(id="service-hierarchy-panel"), width=8),
                                        ])
                                    ),
                                ],
                                id="service-detail-modal",
                                size="xl",
                                is_open=False,
                                scrollable=True,
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
                                    style={"width": "100%", "height": "max(600px, calc(100vh - 114px - 68px - 40px))"},
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
                                    style={"width": "100%", "height": "max(600px, calc(100vh - 114px - 68px - 40px))"},
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
                            dcc.Graph(id="heatmap-graph", style={"height": "max(600px, calc(100vh - 114px - 68px - 40px))"}),
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
                    dcc.Tab(
                        label="Trace Replay",
                        value="trace-replay",
                        children=[
                            html.H4("Trace Replay (Selected Trace)", style={"marginTop": "40px"}),
                            html.Div(
                                id="replay-step-label",
                                children="Select a trace to start replay",
                                style={
                                    "fontSize": "16px",
                                    "fontWeight": "bold",
                                    "textAlign": "center",
                                    "marginBottom": "8px",
                                },
                            ),
                            html.Div(
                                [
                                    dbc.Button("< Prev", id="replay-prev-btn", color="secondary", size="sm", style={"marginRight": "6px"}),
                                    dbc.Button("Play", id="replay-play-btn", color="primary", size="sm", style={"marginRight": "6px"}),
                                    dbc.Button("Next >", id="replay-next-btn", color="secondary", size="sm"),
                                ],
                                style={"textAlign": "center", "marginBottom": "12px"},
                            ),
                            html.Div(
                                dcc.Slider(
                                    id="replay-step-slider",
                                    min=0,
                                    max=0,
                                    value=0,
                                    marks={0: "1"},
                                    step=1,
                                ),
                                style={"marginBottom": "20px"},
                            ),
                            html.Div(
                                cyto.Cytoscape(
                                    id="trace-replay-graph",
                                    layout={
                                        "name": "circle",
                                        "padding": 40,
                                        "animate": False,
                                    },
                                    style={"width": "100%", "height": "max(440px, calc(100vh - 240px - 114px - 68px - 40px))"},
                                    elements=[],
                                    stylesheet=[],
                                ),
                                style={
                                    "border": "2px solid #0074D9",
                                    "borderRadius": "8px",
                                    "padding": "10px",
                                    "background": "#fff",
                                },
                            ),
                            html.Div(id="replay-info-panel"),
                        ],
                    ),
                ],
            )
        ],
        width=10,
    )

    return dbc.Container(
        [
            dcc.Store(id="data-store", data=initial_data),
            dcc.Store(id="replay-step", data=0),
            dcc.Interval(id="replay-interval", interval=1000, disabled=True),
            dbc.Row([sidebar, main_content], style={"margin": "0", "height": "100vh"}),
        ],
        fluid=True,
    )
