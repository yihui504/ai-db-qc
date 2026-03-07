"""DB profile loader."""

from __future__ import annotations

import yaml
from pathlib import Path

from contracts.db_profiles.schema import DBProfile


def load_profile(path: str | Path) -> DBProfile:
    """Load a database profile from YAML file."""
    data = yaml.safe_load(Path(path).read_text())
    return DBProfile(**data)
