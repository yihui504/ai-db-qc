"""Sequence assertion oracle for multi-step test validation.

This oracle validates intermediate state assertions in sequence operations,
allowing automated verification of multi-step test cases (R3 campaigns).

Key capability: converts "expected_behavior" comments in sequence templates
into executable oracle assertions, enabling automatic detection of state bugs.
"""

from __future__ import annotations

from typing import Any, Dict
import operator

from oracles.base import OracleBase
from schemas.case import TestCase
from schemas.result import ExecutionResult, OracleResult


class SequenceAssertionOracle(OracleBase):
    """Validate sequence assertions at intermediate steps.

    Parses assertion strings like "count > 0", "result_count <= 10",
    "result_ids is_empty" and validates them against execution result state.

    This enables automatic detection of sequence state bugs that were
    previously only documented in comments (e.g., seq-001 step 5:
    "Should be idempotent - second delete should not error").
    """

    # Mapping of assertion operators to Python functions
    OPERATORS = {
        "==": operator.eq,
        "!=": operator.ne,
        ">": operator.gt,
        ">=": operator.ge,
        "<": operator.lt,
        "<=": operator.le,
    }

    def __init__(self, assertion_string: str):
        """Initialize sequence assertion oracle.

        Args:
            assertion_string: Assertion string like "count > 0", "result_count <= 10"
        """
        self.assertion_string = assertion_string.strip()

    def _parse_assertion(self) -> tuple:
        """Parse assertion string into (field, operator, value).

        Returns:
            tuple: (field_path, operator_func, expected_value)
        """
        # Simple parser for "field op value" format
        parts = self.assertion_string.split()
        if len(parts) != 3:
            raise ValueError(f"Invalid assertion format: {self.assertion_string}. Expected: 'field op value'")

        field, op_str, value_str = parts

        # Map operator string to function
        op_func = self.OPERATORS.get(op_str)
        if op_func is None:
            raise ValueError(f"Unsupported operator: {op_str}. Supported: {list(self.OPERATORS.keys())}")

        # Parse value (handle ints, floats, bools, strings)
        try:
            expected_value = int(value_str)
        except ValueError:
            try:
                expected_value = float(value_str)
            except ValueError:
                if value_str.lower() == "true":
                    expected_value = True
                elif value_str.lower() == "false":
                    expected_value = False
                else:
                    # Remove quotes from string values
                    expected_value = value_str.strip('"\'')

        return field, op_func, expected_value

    def _extract_field_value(self, field_path: str, result: ExecutionResult) -> Any:
        """Extract field value from result using path like "count", "result_count".

        Supports:
        - Direct response fields: "count" -> result.response["count"]
        - Computed fields: "result_count" -> len(result.response.get("data", []))
        - State fields: "state.collection_size" -> result.sequence_state.get("collection_size")
        """
        # Check direct response field
        if result.response and field_path in result.response:
            return result.response[field_path]

        # Check computed fields
        if field_path == "result_count":
            return len(result.response.get("data", [])) if result.response else 0

        # Check state fields
        if field_path.startswith("state."):
            state_key = field_path[6:]  # Remove "state." prefix
            return result.sequence_state.get(state_key)

        # Check data array
        if result.response and "data" in result.response:
            if field_path in result.response["data"][0] if result.response["data"] else {}:
                return result.response["data"][0][field_path]

        raise ValueError(f"Field not found: {field_path}")

    def validate(
        self,
        case: TestCase,
        result: ExecutionResult,
        context: Dict[str, Any]
    ) -> OracleResult:
        """Validate sequence assertion.

        Args:
            case: Test case (may contain sequence_assertions)
            result: Execution result with sequence_state
            context: Additional context
        """
        # If case has sequence_assertions, validate them
        if case.sequence_assertions:
            for assertion in case.sequence_assertions:
                try:
                    field, op_func, expected_value = self._parse_assertion()
                    actual_value = self._extract_field_value(field, result)

                    if not op_func(actual_value, expected_value):
                        return OracleResult(
                            oracle_id="sequence_assertion",
                            passed=False,
                            metrics={
                                "assertion": assertion,
                                "field": field,
                                "actual": actual_value,
                                "expected": expected_value,
                                "operator": op_func.__name__
                            },
                            expected_relation=f"{field} {op_func.__name__} {expected_value}",
                            observed_relation=f"{field} = {actual_value}",
                            explanation=f"Sequence assertion failed: {assertion}"
                        )
                except (ValueError, KeyError) as e:
                    return OracleResult(
                        oracle_id="sequence_assertion",
                        passed=False,
                        metrics={"assertion": assertion, "error": str(e)},
                        expected_relation="Assertion should be parseable",
                        observed_relation=f"Assertion parse error: {e}",
                        explanation=f"Sequence assertion could not be evaluated: {e}"
                    )

        return OracleResult(
            oracle_id="sequence_assertion",
            passed=True,
            metrics={"assertions_validated": len(case.sequence_assertions)},
            explanation=f"All sequence assertions passed: {case.sequence_assertions}"
        )
