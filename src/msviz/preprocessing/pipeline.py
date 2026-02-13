"""Preprocessing pipeline orchestration."""

from dataclasses import dataclass
from pathlib import Path

from .io import read_csv, resolve_input_csv_path, resolve_output_csv_path, write_csv
from .steps import (
    add_call_duration,
    add_callee_column,
    drop_missing_call_duration,
    filter_client_rows,
)


@dataclass(frozen=True)
class PreprocessResult:
    input_path: Path
    output_path: Path
    input_rows: int
    output_rows: int


def run_preprocessing(
    input_csv: str | None = None,
    output_csv: str | None = None,
) -> PreprocessResult:
    input_path = resolve_input_csv_path(input_csv)
    output_path = resolve_output_csv_path(output_csv)

    raw_df = read_csv(input_path)
    filtered_df = filter_client_rows(raw_df)
    with_callee_df = add_callee_column(filtered_df)
    with_duration_df = add_call_duration(with_callee_df)
    final_df = drop_missing_call_duration(with_duration_df)

    write_csv(final_df, output_path)

    return PreprocessResult(
        input_path=input_path,
        output_path=output_path,
        input_rows=len(raw_df),
        output_rows=len(final_df),
    )
