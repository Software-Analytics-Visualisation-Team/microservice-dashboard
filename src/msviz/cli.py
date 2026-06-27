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

    build_graph_parser = subparsers.add_parser(
        "build_graph", help="Build knowledge graph JSON from the two processed CSVs"
    )
    build_graph_parser.add_argument(
        "--runtime_csv", default=None,
        help="Path to processed_runtime_data.csv (default: data/processed_runtime_data.csv)",
    )
    build_graph_parser.add_argument(
        "--static_csv", default=None,
        help="Path to processed_static_data.csv (default: data/processed_static_data.csv)",
    )
    build_graph_parser.add_argument(
        "--output", default=None,
        help="Output JSON path (default: data/knowledge_graph.json)",
    )

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

    if args.command == "build_graph":
        from pathlib import Path as _Path
        from .graph_builder import build_graph, save_graph, default_output_path

        # Resolve default CSV paths relative to this file (repo_root/data/)
        _data_dir = _Path(__file__).resolve().parent.parent.parent / "data"
        runtime_csv = _Path(args.runtime_csv) if args.runtime_csv else _data_dir / "processed_runtime_data.csv"
        static_csv  = _Path(args.static_csv)  if args.static_csv  else _data_dir / "processed_static_data.csv"
        output_path = _Path(args.output)       if args.output       else default_output_path(runtime_csv)

        graph = build_graph(runtime_csv, static_csv)
        save_graph(graph, output_path)

        n_nodes = len(graph["nodes"])
        n_edges = len(graph["edges"])
        print(
            f"Knowledge graph built: {n_nodes} nodes, {n_edges} edges\n"
            f"Output: {output_path}"
        )
        return 0

    parser.error("Please specify one of: serve, preprocess, preprocess_static, build_graph")
    return 2
