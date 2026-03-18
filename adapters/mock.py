"""Mock adapter for testing."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from adapters.base import AdapterBase, OperationNotSupportedError
from schemas.common import ObservedOutcome
from schemas.result import OracleResult


class ResponseMode(str, Enum):
    """Mock response modes."""
    SUCCESS = "success"
    FAILURE = "failure"
    CRASH = "crash"
    HANG = "hang"
    TIMEOUT = "timeout"


class DiagnosticQuality(str, Enum):
    """Error message diagnostic quality."""
    FULL = "full"
    PARTIAL = "partial"
    NONE = "none"


class MockAdapter(AdapterBase):
    """Mock adapter for controllable test behavior."""

    def __init__(
        self,
        response_mode: ResponseMode = ResponseMode.SUCCESS,
        diagnostic_quality: DiagnosticQuality = DiagnosticQuality.FULL,
        mock_oracle_result: Optional[OracleResult] = None,
        result_id_start: int = 1,
        result_count: int = 5,
        filter_reduction_factor: float = 0.5
    ):
        self.response_mode = response_mode
        self.diagnostic_quality = diagnostic_quality
        self.mock_oracle_result = mock_oracle_result
        self.result_id_start = result_id_start
        self.result_count = result_count
        self.filter_reduction_factor = filter_reduction_factor
        self._current_data: Optional[list] = None

        # Define supported operations for MockAdapter
        self._supported_operations = [
            "create_collection",
            "insert",
            "insert_unique",
            "search",
            "search_exact",
            "build_index",
            "load",
            "filtered_search",
            "drop_collection",
            "delete",
            "release",
            "reload",
            "count",
            "wait"
        ]

    def execute(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Execute request and return simulated response."""
        operation = request.get("operation", "unknown")
        params = request.get("params", {})

        if self.response_mode == ResponseMode.SUCCESS:
            # Generate results with IDs for subset validation
            data = [
                {"id": self.result_id_start + i, "score": 0.9 - i * 0.1}
                for i in range(self.result_count)
            ]

            # Apply filter reduction if filter parameter present
            filter_expr = params.get("filter", "")
            if filter_expr and self.filter_reduction_factor < 1.0:
                # Reduce result count based on filter
                filtered_count = max(1, int(len(data) * self.filter_reduction_factor))
                data = data[:filtered_count]

            # Cache data for potential oracle validation
            self._current_data = data

            return {
                "status": "success",
                "data": data,
                "operation": operation
            }

        elif self.response_mode == ResponseMode.FAILURE:
            return self._build_error_response(operation)

        elif self.response_mode == ResponseMode.CRASH:
            return {
                "status": "crash",
                "error": "Process crashed",
                "operation": operation
            }

        elif self.response_mode == ResponseMode.HANG:
            return {
                "status": "hang",
                "error": "Operation hung",
                "operation": operation
            }

        elif self.response_mode == ResponseMode.TIMEOUT:
            return {
                "status": "timeout",
                "error": "Operation timed out",
                "operation": operation
            }

        return {"status": "unknown"}

    def _build_error_response(self, operation: str) -> Dict[str, Any]:
        """Build error response based on diagnostic quality."""
        if self.diagnostic_quality == DiagnosticQuality.FULL:
            # Detailed diagnostic information - include specific parameter name
            # Map operation to relevant parameter
            param_map = {
                "search": "top_k",
                "create_collection": "dimension",
                "insert": "vectors",
                "filtered_search": "filter"
            }
            param_name = param_map.get(operation, "parameter")
            return {
                "status": "error",
                "error": f"Parameter '{param_name}' has invalid value",
                "operation": operation,
                "error_details": {
                    "parameter": param_name,
                    "issue": "out_of_range"
                }
            }

        elif self.diagnostic_quality == DiagnosticQuality.PARTIAL:
            # Some diagnostic info, missing key slots (parameter name)
            return {
                "status": "error",
                "error": "Invalid parameter value",
                "operation": operation
            }

        else:  # NONE
            # No diagnostic information
            return {
                "status": "error",
                "error": "Error",
                "operation": operation
            }

    def get_runtime_snapshot(self) -> Dict[str, Any]:
        """Get runtime state for PreconditionEvaluator.

        Returns mock state for testing.
        """
        return {
            "collections": ["mock_collection_1", "mock_collection_2"],
            "indexed_collections": ["mock_collection_1"],
            "loaded_collections": ["mock_collection_1"],
            "connected": True,
            "supported_features": ["search", "filtered_search", "insert", "create_collection"],
            "memory_stats": {}
        }

    def supported_operations(self) -> List[str]:
        """Return list of operations supported by MockAdapter."""
        return self._supported_operations
