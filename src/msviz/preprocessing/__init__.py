"""Preprocessing package."""

from .pipeline import run_preprocessing
from .static_pipeline import run_static_preprocessing

__all__ = [
    "run_preprocessing",
    "run_static_preprocessing",
]
