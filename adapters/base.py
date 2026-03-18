"""Base adapter interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class OperationNotSupportedError(Exception):
    """Raised when an operation is not supported by the adapter."""
    pass


class AdapterBase(ABC):
    """Abstract base class for database adapters.

    All adapters must implement the required methods. Optional methods
    have default implementations but should be overridden for better
    error reporting and capabilities discovery.
    """

    @abstractmethod
    def execute(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a request and return raw response."""
        pass

    @abstractmethod
    def get_runtime_snapshot(self) -> Dict[str, Any]:
        """Get current runtime state of the adapter.

        Returns:
            Dict with keys:
                - collections: List of collection names
                - connection_status: str ("connected", "disconnected", "error")
                - metadata: Optional dict with additional info
        """
        pass

    @abstractmethod
    def supported_operations(self) -> List[str]:
        """Return list of operations supported by this adapter.

        This allows dynamic capability discovery instead of hardcoding
        operation support per database.

        Returns:
            List of operation names (e.g., ["search", "filtered_search", "build_index"])
        """
        pass

    def health_check(self) -> bool:
        """Check if adapter is healthy."""
        return True
