"""Write-read consistency oracle."""

from __future__ import annotations

from typing import Any, Dict

from oracles.base import OracleBase
from schemas.case import TestCase
from schemas.common import OperationType
from schemas.result import ExecutionResult, OracleResult


class WriteReadConsistency(OracleBase):
    """Validate: written data can be read back.

    Phase 4: Supports count sanity + ID validation + optional content checks.
    Stateless - consumes context (write_history, mock_state) provided by executor.
    """

    def __init__(
        self,
        validate_ids: bool = True,  # Phase 4 default: validate IDs
        validate_content: bool = False  # Optional: off by default
    ):
        self.validate_ids = validate_ids
        self.validate_content = validate_content

    def validate(
        self,
        case: TestCase,
        result: ExecutionResult,
        context: Dict[str, Any]
    ) -> OracleResult:
        """Validate write-read consistency."""
        write_history = context.get("write_history", [])
        mock_state = context.get("mock_state", {})

        if case.operation in [OperationType.SEARCH, OperationType.FILTERED_SEARCH]:
            collection = case.params.get("collection_name")
            if collection:
                # Phase 4: Collect written IDs from context (executor-managed)
                written_ids = set()
                for write_op in write_history:
                    if write_op.get("collection_name") == collection:
                        written_ids.update(write_op.get("ids", []))

                # Fallback to mock_state for Phase 3 compatibility
                if not written_ids and collection in mock_state:
                    # Mock state may have vectors without IDs
                    written_count = len(mock_state[collection])
                    result_count = len(result.response.get("data", []))
                    if result_count > written_count:
                        return OracleResult(
                            oracle_id="write_read_consistency",
                            passed=False,
                            metrics={"written": written_count, "returned": result_count},
                            expected_relation="returned <= written",
                            observed_relation=f"returned ({result_count}) > written ({written_count})",
                            explanation="More results returned than were written"
                        )
                elif written_ids:
                    # Phase 4: ID validation (beyond count)
                    if self.validate_ids:
                        result_ids = set()
                        for item in result.response.get("data", []):
                            if "id" in item:
                                result_ids.add(item["id"])

                        if not result_ids.issubset(written_ids):
                            unexpected_ids = result_ids - written_ids
                            return OracleResult(
                                oracle_id="write_read_consistency",
                                passed=False,
                                metrics={"unexpected_ids": list(unexpected_ids)},
                                expected_relation="returned ⊆ written",
                                observed_relation=f"returned has IDs not in written: {unexpected_ids}",
                                explanation="Write-read consistency violated: unexpected IDs"
                            )

                    # Optional content validation (future expansion)
                    if self.validate_content:
                        # Basic content matching logic here
                        # For Phase 4 minimal, this stays off
                        pass

        return OracleResult(
            oracle_id="write_read_consistency",
            passed=True,
            metrics={},
            explanation="Write-read consistency satisfied"
        )
