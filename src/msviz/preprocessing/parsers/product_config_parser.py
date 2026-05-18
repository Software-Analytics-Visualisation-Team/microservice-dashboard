from dataclasses import dataclass
from typing import Any

from msviz.data import StaticDataModel


@dataclass(frozen=True)
class ProductConfigYamlParser:
    """Parser for product config YAML containing a top-level Product mapping."""

    def parse(self, raw: dict[str, Any]) -> StaticDataModel:
        product = raw.get("Product", {})
        if not isinstance(product, dict):
            return StaticDataModel(microservices=[], packages=[], functions=[])

        microservices: list[dict[str, Any]] = []

        for name, config in product.items():
            if not isinstance(name, str) or not isinstance(config, dict):
                continue

            dependencies = _extract_dependency_services(config.get("Dependencies", {}))
            interfaces = _as_string_list(config.get("Interfaces"))

            microservices.append(
                {
                    "name": name,
                    "dependencies": dependencies,
                    "interfaces": interfaces,
                    "parameters": config.get("Parameters", {}),
                }
            )

        return StaticDataModel(
            microservices=microservices,
            packages=[],
            functions=[],
        )

def _extract_dependency_services(value: Any) -> list[str]:
    if not isinstance(value, dict):
        return []

    services: set[str] = set()
    for dep in value.values():
        if not isinstance(dep, dict):
            continue
        direct = dep.get("ServiceName")
        if isinstance(direct, str):
            services.add(direct)
            continue

        nested = dep.get("Service")
        if isinstance(nested, dict):
            nested_name = nested.get("Name")
            if isinstance(nested_name, str):
                services.add(nested_name)
    return list(services)

def _as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [entry for entry in value if isinstance(entry, str)]
