from dataclasses import dataclass
from typing import Any

from msviz.data import StaticDataModel

IGNORE_LIST = tuple(["std/"])


@dataclass(frozen=True)
class CppSymbolGraphJsonParser:
    """Parser for symbol-graph style JSON."""

    def parse(self, raw: dict[str, Any]) -> StaticDataModel:
        function_declarations = raw.get("functionDeclarations")
        containment = raw.get("containment")

        parents: set[str] = set()
        functions: set[tuple[str, str]] = set()
        _collect_from_m3_section(containment, parents, functions)
        _collect_from_m3_section(function_declarations, parents, functions)

        packages_rows = [{"name": parent} for parent in sorted(parents)]
        function_rows = [
            {"name": name, "parent": parent} for parent, name in sorted(functions)
        ]
        return StaticDataModel(
            microservices=[],
            packages=packages_rows,
            functions=function_rows,
        )


def _collect_from_m3_section(
    m3_section: Any,
    parents: set[str],
    functions: set[tuple[str, str]],
) -> None:
    if not isinstance(m3_section, list):
        return

    for item in m3_section:
        if not (isinstance(item, list) and len(item) == 2):
            continue
        source, target = item[0], item[1]
        if not isinstance(source, str) or not isinstance(target, str):
            continue

        for symbol in (source, target):
            if not _is_method_or_func(symbol):
                continue
            if _is_on_ignore_list(symbol):
                continue
            parent, name = _extract_symbol_scope_and_name(symbol)
            if parent:
                parents.add(parent)
            if parent and name:
                functions.add((parent, name))


def _is_method_or_func(symbol: str) -> bool:
    func_marker = "cpp+function:///"
    method_marker = "cpp+method:///"

    return symbol.startswith(func_marker) or symbol.startswith(method_marker)

def _is_on_ignore_list(symbol: str) -> bool:
    for keyword in IGNORE_LIST:
        if keyword in symbol:
            return True
    
    return False


def _extract_symbol_scope_and_name(symbol: str) -> tuple[str | None, str | None]:
    marker = ":///"
    if marker not in symbol:
        return None, None
    tail = symbol.split(marker, maxsplit=1)[1]
    if not tail:
        return None, None
    split_symbol = tail.rsplit("/", maxsplit=1)
    if len(split_symbol) != 2:
        return None, None
    return split_symbol[0], split_symbol[1]
