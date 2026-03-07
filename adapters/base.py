"""Base adapter interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class AdapterBase(ABC):
    """Abstract base class for database adapters."""

    @abstractmethod
    def execute(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a request and return raw response."""
        pass

    def health_check(self) -> bool:
        """Check if adapter is healthy."""
        return True
