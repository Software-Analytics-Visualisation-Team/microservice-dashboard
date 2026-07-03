"""Application factory for visualization."""
import os
import dash
import dash_bootstrap_components as dbc

prefix = os.getenv("DASH_URL_PREFIX", "/")

from .callbacks import register_callbacks
from .data import build_context
from .layout import build_layout
from .styles import overall_stylesheet


def create_app():
    context = build_context()

    app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    app.layout = build_layout(context, overall_stylesheet)
    register_callbacks(app, overall_stylesheet)
    return app
