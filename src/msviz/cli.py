"""Top-level CLI for visualization and preprocessing."""

import argparse
import sys
from collections.abc import Sequence

from .preprocessing import run_preprocessing


def _add_shared_server_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8050)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--data-path", default="data/processed_data.csv")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="msviz")
    subparsers = parser.add_subparsers(dest="command")

    serve_parser = subparsers.add_parser("serve", help="Start the Dash application")
    _add_shared_server_flags(serve_parser)

    preprocess_parser = subparsers.add_parser(
        "preprocess", help="Run data preprocessing pipeline"
    )
    preprocess_parser.add_argument("--input-csv", default=None)
    preprocess_parser.add_argument("--output-csv", default=None)

    run_parser = subparsers.add_parser(
        "run", help="Run preprocessing pipeline and then start the Dash application"
    )
    run_parser.add_argument("--input-csv", default=None)
    run_parser.add_argument("--output-csv", default=None)
    _add_shared_server_flags(run_parser)

    return parser


def _run_server(host: str, port: int, debug: bool, data_path: str) -> None:
    from .visualization import create_app

    app = create_app(data_path=data_path)
    app.run(debug=debug, host=host, port=port)


def main(argv: Sequence[str] | None = None) -> int:
    args_list = list(argv) if argv is not None else list(sys.argv[1:])
    if not args_list:
        args_list = ["serve"]

    parser = build_parser()
    args = parser.parse_args(args_list)

    if args.command == "serve":
        _run_server(args.host, args.port, args.debug, args.data_path)
        return 0

    if args.command == "preprocess":
        result = run_preprocessing(args.input_csv, args.output_csv)
        print(
            "Preprocessing complete: "
            f"{result.input_rows} rows -> {result.output_rows} rows, "
            f"output={result.output_path}"
        )
        return 0

    if args.command == "run":
        result = run_preprocessing(args.input_csv, args.output_csv)
        data_path = args.data_path
        if args.output_csv:
            data_path = args.output_csv

        print(
            "Preprocessing complete: "
            f"{result.input_rows} rows -> {result.output_rows} rows, "
            f"output={result.output_path}"
        )
        _run_server(args.host, args.port, args.debug, data_path)
        return 0

    parser.error("Please specify one of: serve, preprocess, run")
    return 2
