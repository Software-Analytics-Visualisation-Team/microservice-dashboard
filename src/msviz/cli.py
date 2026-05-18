"""Top-level CLI for visualization and preprocessing."""

import argparse
import sys
from collections.abc import Sequence

from .preprocessing import run_preprocessing, run_static_preprocessing

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="msviz")
    subparsers = parser.add_subparsers(dest="command")

    serve_parser = subparsers.add_parser("serve", help="Start the Dash application")
    serve_parser.add_argument("--host", default="0.0.0.0")
    serve_parser.add_argument("--port", type=int, default=8050)
    serve_parser.add_argument("--debug", action="store_true")
    serve_parser.add_argument("--data_path", default="data/processed_runtime_data.csv")

    preprocess_parser = subparsers.add_parser(
        "preprocess", help="Run data preprocessing pipeline"
    )
    preprocess_parser.add_argument("--input_csv", default=None)
    preprocess_parser.add_argument("--output_csv", default=None)
    
    
    static_preprocess_parser = subparsers.add_parser(
        "preprocess_static", help="Run static data preprocessing pipeline"
    )
    static_preprocess_parser.add_argument("--service_config_yml", default=None)
    static_preprocess_parser.add_argument("--symbol_data_path", default=None)
    static_preprocess_parser.add_argument("--output_csv", default=None)

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
            "Preprocessing complete: \n"
            f"{result.input_rows} rows -> {result.output_rows} rows, \n"
            f"output={result.output_path}"
        )
        return 0
    
    if args.command == "preprocess_static":
        result = run_static_preprocessing(
            input_path=args.service_config_yml,
            output_csv=args.output_csv,
            symbol_data_dir=args.symbol_data_path,
        )
        data_model = result.data_model
        print(
            "Static Data Preprocessing complete: \n"
            f"Microservices: {len(data_model.microservices)} "
            f"Packages: {len(data_model.packages)} "
            f"Functions: {len(data_model.functions)}\n"
            f"output={result.output_path}"
        )
        return 0

    parser.error("Please specify one of: serve, preprocess, preprocess_static")
    return 2
