"""Application factory for visualization."""
import os
import dash
import dash_bootstrap_components as dbc

prefix = os.getenv("DASH_URL_PREFIX", "/")

from .callbacks import register_callbacks
from .data import build_context, load_runtime_data, load_static_data
from .graphs import build_static_graph_elements
from .layout import build_layout
from .styles import overall_stylesheet


def create_app(
    data_path: str = "data/processed_runtime_data.csv",
    static_data_path: str = "data/processed_static_data.csv",
):
    runtime_data = load_runtime_data(data_path)
    static_data = load_static_data(static_data_path)
    static_elements = build_static_graph_elements(static_data)
    context = build_context(runtime_data, static_data)

    app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    app.layout = build_layout(context, overall_stylesheet)
    register_callbacks(app, runtime_data, static_elements, overall_stylesheet)
    return app