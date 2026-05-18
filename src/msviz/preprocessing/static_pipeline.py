"""Static-data preprocessing orchestration."""

from __future__ import annotations

from pathlib import Path

from msviz.data import StaticDataModel, StaticPreprocessResult
from .io import (
    read_static_mapping,
    resolve_static_output_csv_path,
    write_static_entities_csv,
)
from .parsers.cpp_symbol_parser import CppSymbolGraphJsonParser
from .parsers.product_config_parser import ProductConfigYamlParser


def run_static_preprocessing(
    input_path: str | Path,
    output_csv: str | Path | None = None,
    source_type: str | None = None,
    symbol_data_dir: str | Path | None = None,
) -> StaticPreprocessResult:
    path = Path(input_path)
    output_path = resolve_static_output_csv_path(path, output_csv)
    raw = read_static_mapping(path)

    resolved_source_type = source_type or "product-config-yaml"
    if resolved_source_type != "product-config-yaml":
        raise ValueError(
            "run_static_preprocessing expects a product config YAML as entrypoint. "
        )

    product_parser = ProductConfigYamlParser()
    symbol_parser = CppSymbolGraphJsonParser()

    service_model = product_parser.parse(raw)
    microservices = list(service_model.microservices)

    package_entries: set[tuple[str, str]] = set()
    function_entries: set[tuple[str, str, str]] = set()

    for service in microservices:
        service_name = service.get("name")
        if not isinstance(service_name, str):
            continue

        symbol_path = _resolve_symbol_path(
            service_name=service_name,
            base_input_path=path,
            symbol_data_dir=symbol_data_dir,
        )
        if symbol_path is None or not symbol_path.exists():
            continue

        symbol_raw = read_static_mapping(symbol_path)
        symbol_model = symbol_parser.parse(symbol_raw)

        for package in symbol_model.packages:
            package_name = package.get("name")
            if isinstance(package_name, str):
                package_entries.add((service_name, package_name))

        for function in symbol_model.functions:
            function_name = function.get("name")
            function_parent = function.get("parent")
            if isinstance(function_name, str) and isinstance(function_parent, str):
                function_entries.add((service_name, function_parent, function_name))

    packages = [
        {"service": service_name, "name": package_name}
        for service_name, package_name in sorted(package_entries)
    ]
    functions = [
        {"service": service_name, "parent": parent, "name": function_name}
        for service_name, parent, function_name in sorted(function_entries)
    ]
    data_model = StaticDataModel(
        microservices=microservices,
        packages=packages,
        functions=functions,
    )
    write_static_entities_csv(data_model, output_path)

    return StaticPreprocessResult(
        input_path=path,
        output_path=output_path,
        source_type=resolved_source_type,
        data_model=data_model,
    )


def _resolve_symbol_path(
    service_name: str,
    base_input_path: Path,
    symbol_data_dir: str | Path | None,
) -> Path | None:

    base_dir = Path(symbol_data_dir) if symbol_data_dir else base_input_path.parent
    candidate = base_dir / f"{service_name}.json"
    if candidate.exists():
        return candidate
    return None
