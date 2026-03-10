"""Oracle for SCH006B-001.

SCH-006b: Filter Semantics Verification Oracle

Classification Logic:
1. PASS: Filter returns correct entity count
2. BUG_CANDIDATE: Filter returns incorrect count (data exists but filter wrong)
3. OBSERVATION: Filter executes but behavior is unexpected (document)
4. EXPERIMENT_DESIGN_ISSUE: Data insertion failed or test setup broken

Evidence Hierarchy:
- Baseline verification: total_entity_count must match expectations
- Filter verification: filtered_entity_count compared to expectations
"""

from typing import Dict, Any, Optional


class Sch006b001Oracle:
    """Oracle for evaluating SCH006B-001 test results."""

    def evaluate(self, result: Dict[str, Any], contract: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate test result against contract.

        Args:
            result: Test execution result with execution_trace
            contract: Contract specification

        Returns:
            Oracle evaluation with classification and reasoning
        """
        expectations = result.get("oracle_expectations", {})
        trace = result.get("execution_trace", [])

        # Extract verification results from trace
        total_count = None
        filtered_count = None
        filter_expression = None
        baseline_verified = False

        for step in trace:
            op = step.get("operation", "")

            # Step 1: Baseline - count total entities
            if op == "query" and step.get("params", {}).get("filter_expression") is None:
                result_data = step.get("result", {})
                total_count = result_data.get("count", len(result_data.get("results", [])))
                if total_count == expectations.get("total_entity_count"):
                    baseline_verified = True

            # Step 2: Filter - count filtered entities
            elif op == "query":
                params = step.get("params", {})
                if params.get("filter_expression"):
                    filter_expression = params.get("filter_expression")
                    result_data = step.get("result", {})
                    filtered_count = result_data.get("count", len(result_data.get("results", [])))

        # Decision tree
        if total_count is None:
            return {
                "classification": "EXPERIMENT_DESIGN_ISSUE",
                "satisfied": False,
                "reasoning": "Baseline query failed - cannot verify filter semantics without confirming data exists",
                "evidence": {
                    "total_count": total_count,
                    "filtered_count": filtered_count,
                    "expected_total": expectations.get("total_entity_count"),
                    "issue": "baseline_query_missing_or_failed"
                }
            }

        if not baseline_verified:
            return {
                "classification": "EXPERIMENT_DESIGN_ISSUE",
                "satisfied": False,
                "reasoning": f"Data insertion incomplete - expected {expectations.get('total_entity_count')} entities, got {total_count}",
                "evidence": {
                    "total_count": total_count,
                    "expected_total": expectations.get("total_entity_count"),
                    "filtered_count": filtered_count,
                    "issue": "insert_verification_failed"
                }
            }

        if filtered_count is None:
            return {
                "classification": "EXPERIMENT_DESIGN_ISSUE",
                "satisfied": False,
                "reasoning": "Filter query failed - cannot determine if filter works",
                "evidence": {
                    "total_count": total_count,
                    "baseline_verified": True,
                    "filtered_count": None,
                    "filter_expression": filter_expression,
                    "issue": "filter_query_failed"
                }
            }

        # At this point: baseline verified, filter query executed
        expected_min = expectations.get("expected_min_count", 0)
        expected_max = expectations.get("expected_max_count", float('inf'))

        if expected_min <= filtered_count <= expected_max:
            return {
                "classification": "PASS",
                "satisfied": True,
                "reasoning": f"Filter works correctly - returned {filtered_count} entities (expected {expected_min}-{expected_max})",
                "evidence": {
                    "total_count": total_count,
                    "filtered_count": filtered_count,
                    "expected_range": f"{expected_min}-{expected_max}",
                    "filter_expression": filter_expression,
                    "filter_field": expectations.get("filter_field"),
                    "filter_value": expectations.get("filter_value")
                }
            }

        # Check if filter returned MORE than expected (false positives)
        if filtered_count > expected_max:
            return {
                "classification": "BUG_CANDIDATE",
                "satisfied": False,
                "reasoning": f"Filter returned too many entities - got {filtered_count}, expected max {expected_max}. Filter may not be working correctly.",
                "evidence": {
                    "total_count": total_count,
                    "filtered_count": filtered_count,
                    "expected_max": expected_max,
                    "issue": "filter_false_positive"
                }
            }

        # Check if filter returned FEWER than expected (false negatives)
        if filtered_count < expected_min:
            # Special case: if expected > 0 but got 0, could be filter not working
            if expected_min > 0 and filtered_count == 0:
                return {
                    "classification": "BUG_CANDIDATE",
                    "satisfied": False,
                    "reasoning": f"Filter returned 0 entities when {expected_min} were expected. Filter may not be working on dynamic scalar fields.",
                    "evidence": {
                        "total_count": total_count,
                        "filtered_count": filtered_count,
                        "expected_min": expected_min,
                        "issue": "filter_false_negative_zero",
                        "baseline_verified": True,
                        "note": "Data exists but filter returns nothing - filter not working?"
                    }
                }

            return {
                "classification": "OBSERVATION",
                "satisfied": False,
                "reasoning": f"Filter returned fewer entities than expected - got {filtered_count}, expected min {expected_min}. Partial filter behavior?",
                "evidence": {
                    "total_count": total_count,
                    "filtered_count": filtered_count,
                    "expected_min": expected_min,
                    "issue": "filter_partial_match"
                }
            }

        # Fallback
        return {
            "classification": "OBSERVATION",
            "satisfied": False,
            "reasoning": f"Filter behavior unexpected - total: {total_count}, filtered: {filtered_count}",
            "evidence": {
                "total_count": total_count,
                "filtered_count": filtered_count
            }
        }
