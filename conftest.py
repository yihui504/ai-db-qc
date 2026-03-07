"""Pytest configuration for ai-db-qc project."""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def pytest_configure(config):
    """Pytest hook to configure the test environment."""
    # Double-check that project root is in path
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
