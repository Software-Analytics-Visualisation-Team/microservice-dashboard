"""Composable preprocessing steps."""

from datetime import datetime

import numpy as np
import pandas as pd


def filter_client_rows(df: pd.DataFrame) -> pd.DataFrame:
    messages = df.get("message", pd.Series(dtype=str)).fillna("")
    mask = messages.str.contains("-> Client", regex=False) | messages.str.contains(
        "<- Client", regex=False
    )
    return df.loc[mask].copy()


def add_callee_column(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()

    def extract_callee(msg):
        if isinstance(msg, str):
            parts = msg.split(":")
            if len(parts) >= 3:
                return parts[1]
        return np.nan

    result["callee"] = result["message"].apply(extract_callee)
    return result


def add_call_duration(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    parsed = pd.to_datetime(
        result["timestamp"], format="%b %d, %Y @ %H:%M:%S.%f", errors="coerce"
    )
    result["timestamp"] = parsed.dt.strftime("%Y-%m-%d %H:%M:%S:%f").str[:-3]
    result["call_duration"] = pd.NA

    outgoing = result["message"].fillna("").str.contains("->", regex=False)
    incoming = result["message"].fillna("").str.contains("<-", regex=False)
    fmt = "%Y-%m-%d %H:%M:%S:%f"

    for idx, row in result.loc[outgoing].iterrows():
        provider = row["event_provider"]
        t1 = row["timestamp"]

        if pd.isna(t1):
            continue

        dt1 = datetime.strptime(t1, fmt)

        mask = (result.index > idx) & incoming & (result["event_provider"] == provider)
        next_rows = result.loc[mask]
        if next_rows.empty:
            continue

        t2 = next_rows.iloc[0]["timestamp"]
        if pd.isna(t2):
            continue

        dt2 = datetime.strptime(t2, fmt)
        result.at[idx, "call_duration"] = (dt2 - dt1).total_seconds()

    return result


def drop_missing_call_duration(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result["call_duration"] = pd.to_numeric(result["call_duration"], errors="coerce")
    return result[result["call_duration"].notna()].copy()
