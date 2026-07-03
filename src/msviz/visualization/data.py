"""Data loading and metadata helpers for visualization."""

from dataclasses import dataclass

import pandas as pd

from ..analysis.neo4j_client import Neo4jClient


@dataclass(frozen=True)
class DataContext:
    num_records: int
    first_timestamp: str
    last_timestamp: str
    min_timestamp: int
    max_timestamp: int


def build_context() -> DataContext:
    """Build the sidebar/slider metadata directly from Neo4j."""
    bounds = Neo4jClient.retrieve_time_bounds()
    min_ts = pd.to_datetime(bounds["min_timestamp"])
    max_ts = pd.to_datetime(bounds["max_timestamp"])

    return DataContext(
        num_records=bounds["count"],
        first_timestamp=min_ts.strftime("%Y-%m-%d %H:%M:%S"),
        last_timestamp=max_ts.strftime("%Y-%m-%d %H:%M:%S"),
        min_timestamp=int(min_ts.timestamp()),
        max_timestamp=int(max_ts.timestamp()),
    )
