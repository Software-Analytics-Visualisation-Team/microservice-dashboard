from dataclasses import dataclass
from typing import Any
from pathlib import Path

@dataclass(frozen=True)
class StaticDataModel:
    """Canonical model consumed by static preprocessing steps."""

    microservices: list[dict[str, Any]]
    packages: list[dict[str, Any]]
    functions: list[dict[str, Any]]
    
@dataclass(frozen=True)
class StaticPreprocessResult:
    """Data class representing the result of the static data preprocessing."""
    input_path: Path
    output_path: Path
    source_type: str
    data_model: StaticDataModel