"""Core contract loader."""

from __future__ import annotations

import yaml
from pathlib import Path

from contracts.core.schema import CoreContract


def load_contract(path: str | Path) -> CoreContract:
    """Load a core contract from YAML file."""
    data = yaml.safe_load(Path(path).read_text())
    return CoreContract(**data)


def get_default_contract() -> CoreContract:
    """Get the default core contract."""
    return load_contract(Path(__file__).parent / "default_contract.yaml")
