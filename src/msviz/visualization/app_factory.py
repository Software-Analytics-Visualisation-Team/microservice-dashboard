"""Application factory for visualization."""

import dash
import dash_bootstrap_components as dbc

from .callbacks import register_callbacks
from .data import build_context, load_data
from .layout import build_layout
from .styles import overall_stylesheet


def create_app(data_path: str = "data/processed_data.csv"):
    data = load_data(data_path)
    context = build_context(data)

    app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    app.layout = build_layout(context, data, overall_stylesheet)
    register_callbacks(app, data, overall_stylesheet)
    return app
