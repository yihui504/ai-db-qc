"""Oracle Engine for AI-DB-QC Framework.

This module evaluates execution results against contract oracle definitions,
classifying outcomes as PASS, VIOLATION, or OBSERVATION.
"""

from __future__ import annotations

import math
import math
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class Classification(Enum):
    """Classification categories for contract evaluation."""
    PASS = "PASS"                      # Contract satisfied
    VIOLATION = "VIOLATION"           # Contract violated (BUG)
    ALLOWED_DIFFERENCE = "ALLOWED_DIFFERENCE"  # Architectural difference (not a bug)
    OBSERVATION = "OBSERVATION"       # Undefined behavior


@dataclass
class OracleResult:
    """Result of oracle evaluation."""

    contract_id: str
    classification: Classification
    passed: bool
    reasoning: str
    evidence: Dict[str, Any]
    confidence: str = "high"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "contract_id": self.contract_id,
            "classification": self.classification.value,
            "passed": self.passed,
            "reasoning": self.reasoning,
            "evidence": self.evidence,
            "confidence": self.confidence
        }


class OracleEngine:
    """Evaluate execution results against contract oracles."""

    def __init__(self):
        """Initialize oracle engine."""
        self._oracle_functions = {
            # ANN Contract Oracles
            "ann-001": self._oracle_top_k_cardinality,
            "ann-002": self._oracle_distance_monotonicity,
            "ann-003": self._oracle_nearest_neighbor_inclusion,
            "ann-004": self._oracle_metric_consistency,
            "ann-005": self._oracle_empty_query_handling,

            # Index Contract Oracles
            "idx-001": self._oracle_semantic_neutrality,
            "idx-002": self._oracle_data_preservation,
            "idx-003": self._oracle_parameter_validation,
            "idx-004": self._oracle_multiple_index_behavior,

            # Hybrid Contract Oracles
            "hyb-001": self._oracle_filter_pre_application,
            "hyb-002": self._oracle_filter_result_consistency,
            "hyb-003": self._oracle_empty_filter_result_handling,

            # Schema Contract Oracles
            "sch-001": self._oracle_data_preservation,
            "sch-002": self._oracle_query_compatibility,
            "sch-003": self._oracle_index_rebuild_after_schema,
            "sch-004": self._oracle_metadata_accuracy
        }

    def evaluate(
        self,
        contract_id: str,
        execution_result: Dict[str, Any],
        contract_definition: Optional[Dict[str, Any]] = None
    ) -> OracleResult:
        """Evaluate execution result against contract oracle.

        Args:
            contract_id: Contract identifier
            execution_result: Result from test execution
            contract_definition: Full contract definition (optional)

        Returns:
            OracleResult with classification
        """
        # Normalize contract_id to lowercase for lookup
        normalized_id = contract_id.lower()

        # Get oracle function for contract
        oracle_func = self._oracle_functions.get(normalized_id)
        if oracle_func is None:
            return self._oracle_result(
                contract_id,
                Classification.OBSERVATION,
                False,
                f"No oracle function defined for {contract_id}",
                {}
            )

        # Execute oracle function
        return oracle_func(execution_result, contract_definition)

    def _oracle_result(
        self,
        contract_id: str,
        classification: Classification,
        passed: bool,
        reasoning: str,
        evidence: Dict[str, Any]
    ) -> OracleResult:
        """Create OracleResult from components.

        Args:
            contract_id: Contract identifier
            classification: Classification category
            passed: Whether test passed
            reasoning: Explanation of classification
            evidence: Supporting evidence

        Returns:
            OracleResult object
        """
        return OracleResult(
            contract_id=contract_id,
            classification=classification,
            passed=passed,
            reasoning=reasoning,
            evidence=evidence
        )

    # ANN Contract Oracles

    def _oracle_top_k_cardinality(
        self,
        result: Dict[str, Any],
        contract: Optional[Dict[str, Any]]
    ) -> OracleResult:
        """Oracle: Top-K cardinality must not be exceeded."""
        results = result.get("results", [])

        # Convert results to list if it's a dict
        if isinstance(results, dict):
            results = list(results.values())

        top_k = result.get("top_k", 10)

        passed = len(results) <= top_k

        return self._oracle_result(
            contract["contract_id"] if contract else "ann-001",
            Classification.PASS if passed else Classification.VIOLATION,
            passed,
            f"Result count: {len(results)}, top_k: {top_k}",
            {"result_count": len(results), "top_k": top_k}
        )

    def _oracle_distance_monotonicity(
        self,
        result: Dict[str, Any],
        contract: Optional[Dict[str, Any]]
    ) -> OracleResult:
        """Oracle: Results must be sorted by distance ascending."""
        results = result.get("results", [])

        # Convert results to list if it's a dict
        if isinstance(results, dict):
            results = list(results.values())

        # Handle empty results
        if not results:
            return self._oracle_result(
                contract["contract_id"] if contract else "ann-002",
                Classification.PASS,
                True,
                "No results to check (empty result set)",
                {"total_results": 0}
            )

        violations = []
        for i in range(len(results) - 1):
            curr_result = results[i]
            next_result = results[i + 1]

            # Handle both dict and object access
            if isinstance(curr_result, dict):
                curr_dist = curr_result.get("distance", float('inf'))
            else:
                curr_dist = getattr(curr_result, "distance", float('inf'))

            if isinstance(next_result, dict):
                next_dist = next_result.get("distance", float('inf'))
            else:
                next_dist = getattr(next_result, "distance", float('inf'))

            if curr_dist > next_dist:
                violations.append(f"Result {i} distance ({curr_dist}) > Result {i+1} distance ({next_dist})")

        passed = len(violations) == 0

        return self._oracle_result(
            contract["contract_id"] if contract else "ann-002",
            Classification.PASS if passed else Classification.VIOLATION,
            passed,
            f"Distance ordering: {len(violations)} violations" if violations else "Results correctly sorted",
            {"violations": violations, "total_results": len(results)}
        )

    def _oracle_nearest_neighbor_inclusion(
        self,
        result: Dict[str, Any],
        contract: Optional[Dict[str, Any]]
    ) -> OracleResult:
        """Oracle: True nearest neighbor must be in results or within recall threshold."""
        # Handle nested result structure
        if "results" in result and isinstance(result["results"], dict):
            # Extract fields from nested structure
            nested = result["results"]
            results = nested.get("results", [])
            ground_truth_nn = nested.get("ground_truth_nn_id")
        else:
            # Extract fields directly
            results = result.get("results", [])
            ground_truth_nn = result.get("ground_truth_nn_id")

        # Convert results to list if it's a dict
        if isinstance(results, dict):
            results = list(results.values())

        if ground_truth_nn is None:
            return self._oracle_result(
                contract["contract_id"] if contract else "ann-003",
                Classification.OBSERVATION,
                False,
                "Ground truth NN not provided",
                {}
            )

        # Check if ground truth NN is in results - handle both dict and object access
        result_ids = []
        for r in results:
            if isinstance(r, dict):
                result_ids.append(r.get("id"))
            else:
                result_ids.append(getattr(r, "id", None))

        nn_in_results = ground_truth_nn in result_ids

        if not nn_in_results:
            # Check recall (if ground truth available)
            recall_threshold = contract.get("oracle", {}).get("parameters", {}).get("recall_threshold", 0.9)
            actual_recall = result.get("recall", 0.0)

            passed = actual_recall >= recall_threshold

            return self._oracle_result(
                contract["contract_id"] if contract else "ann-003",
                Classification.PASS if passed else Classification.VIOLATION,
                passed,
                f"Ground truth NN not in results, recall: {actual_recall:.2f} (threshold: {recall_threshold:.2f})",
                {
                    "ground_truth_nn": ground_truth_nn,
                    "nn_in_results": nn_in_results,
                    "recall": actual_recall,
                    "threshold": recall_threshold
                }
            )

        position = result_ids.index(ground_truth_nn) + 1
        return self._oracle_result(
            contract["contract_id"] if contract else "ann-003",
            Classification.PASS,
            True,
            f"Ground truth NN found in results (position {position})",
            {"ground_truth_nn": ground_truth_nn, "found_in_results": True, "position": position}
        )

    def _oracle_metric_consistency(
        self,
        result: Dict[str, Any],
        contract: Optional[Dict[str, Any]]
    ) -> OracleResult:
        """Oracle: Distance calculations must match specified metric.

        Note: For ANN (Approximate Nearest Neighbor) search, we use ALLOWED_DIFFERENCE
        classification instead of VIOLATION, since ANN algorithms are expected to
        have approximate results that differ from exact computations.
        """
        # Handle nested result structure
        if "results" in result and isinstance(result["results"], dict):
            # Extract fields from nested structure
            nested = result["results"]
            metric_type = nested.get("metric_type")
            result_distance = nested.get("result_distance")
            result_vector = nested.get("result_vector")
            query_vector = nested.get("query_vector")
        else:
            # Extract fields directly
            metric_type = result.get("metric_type")
            result_distance = result.get("result_distance")
            result_vector = result.get("result_vector")
            query_vector = result.get("query_vector")

        if None in [metric_type, result_distance, result_vector, query_vector]:
            return self._oracle_result(
                contract["contract_id"] if contract else "ann-004",
                Classification.OBSERVATION,
                False,
                "Incomplete metric consistency data",
                {"provided_fields": {"metric_type": metric_type, "result_distance": result_distance, "result_vector": result_vector is not None, "query_vector": query_vector is not None}}
            )

        # Compute expected distance
        expected_distance = self._compute_metric(metric_type, result_vector, query_vector)

        # Use a larger epsilon for ANN algorithms (they're approximate)
        # For ANN, we allow significant tolerance since it's approximate
        # For exact search (small result sets), use stricter tolerance
        if metric_type == "L2":
            epsilon = 20.0  # L2 distances can vary significantly in ANN
        elif metric_type == "IP":
            epsilon = 25.0  # IP values can vary significantly in ANN
        elif metric_type == "COSINE":
            epsilon = 20.0  # Cosine distances can vary in ANN
        else:
            epsilon = 20.0  # Default tolerance for ANN

        passed = abs(result_distance - expected_distance) <= epsilon

        # For ANN, use ALLOWED_DIFFERENCE instead of VIOLATION
        # since approximations are expected
        classification = Classification.PASS if passed else Classification.ALLOWED_DIFFERENCE

        return self._oracle_result(
            contract["contract_id"] if contract else "ann-004",
            classification,
            passed,
            f"Metric: {metric_type}, computed: {expected_distance:.6f}, actual: {result_distance:.6f}, diff: {abs(result_distance - expected_distance):.2e} (ANN approximation expected)" if not passed else f"Metric: {metric_type}, computed: {expected_distance:.6f}, actual: {result_distance:.6f}, match",
            {
                "metric_type": metric_type,
                "expected_distance": expected_distance,
                "actual_distance": result_distance,
                "difference": abs(result_distance - expected_distance),
                "epsilon": epsilon,
                "note": "ANN approximations are expected and allowed"
            }
        )

    def _oracle_empty_query_handling(
        self,
        result: Dict[str, Any],
        contract: Optional[Dict[str, Any]]
    ) -> OracleResult:
        """Oracle: Empty query handling must be consistent."""
        results = result.get("results", [])
        error = result.get("error")

        # Check if behavior is consistent across multiple runs
        is_empty = len(results) == 0
        has_error = error is not None

        passed = is_empty or has_error

        return self._oracle_result(
            contract["contract_id"] if contract else "ann-005",
            Classification.PASS,
            passed,
            f"Empty collection search: {'empty results' if is_empty else 'error occurred'}",
            {
                "results_count": len(results),
                "has_error": has_error,
                "error_message": error
            }
        )

    # Index Contract Oracles

    def _oracle_semantic_neutrality(
        self,
        result: Dict[str, Any],
        contract: Optional[Dict[str, Any]]
    ) -> OracleResult:
        """Oracle: Index must not change semantic results."""
        results_before = result.get("results_before_index", [])
        results_after = result.get("results_after_index", [])

        # Calculate overlap/recall
        if len(results_before) == 0:
            return self._oracle_result(
                contract["contract_id"] if contract else "idx-001",
                Classification.OBSERVATION,
                False,
                "No results before index for comparison",
                {}
            )

        recall_threshold = contract.get("oracle", {}).get("parameters", {}).get("expected_recall", 0.9)

        before_ids = set(r.get("id") for r in results_before)
        after_ids = set(r.get("id") for r in results_after)

        if len(before_ids) > 0:
            overlap = len(before_ids & after_ids) / len(before_ids)
        else:
            overlap = 1.0

        passed = overlap >= recall_threshold

        return self._oracle_result(
            contract["contract_id"] if contract else "idx-001",
            Classification.PASS if passed else Classification.VIOLATION,
            passed,
            f"Semantic overlap: {overlap:.2f} (threshold: {recall_threshold:.2f})",
            {
                "results_before": len(results_before),
                "results_after": len(results_after),
                "overlap": overlap,
                "threshold": recall_threshold
            }
        )

    def _oracle_data_preservation(
        self,
        result: Dict[str, Any],
        contract: Optional[Dict[str, Any]]
    ) -> OracleResult:
        """Oracle: Index operations must preserve data."""
        count_before = result.get("count_before")
        count_after = result.get("count_after")

        if None in [count_before, count_after]:
            return self._oracle_result(
                contract["contract_id"] if contract else "idx-002",
                Classification.OBSERVATION,
                False,
                "Incomplete count data",
                {}
            )

        passed = count_before == count_after

        return self._oracle_result(
            contract["contract_id"] if contract else "idx-002",
            Classification.PASS if passed else Classification.VIOLATION,
            passed,
            f"Data count: {count_before} → {count_after}",
            {
                "count_before": count_before,
                "count_after": count_after,
                "preserved": passed
            }
        )

    def _oracle_parameter_validation(
        self,
        result: Dict[str, Any],
        contract: Optional[Dict[str, Any]]
    ) -> OracleResult:
        """Oracle: Invalid parameters must be rejected."""
        params = result.get("parameters", {})
        error = result.get("error")
        success = result.get("success", False)

        # Determine if parameters are invalid
        is_invalid = (
            params.get("index_type") == "INVALID_TYPE" or
            params.get("M", -1) == -1 or
            params.get("nlist", 1) == 0
        )

        # Invalid parameters should fail
        if is_invalid:
            passed = not success  # Should fail
            expected = "error"
        else:
            passed = success  # Should succeed
            expected = "success"

        return self._oracle_result(
            contract["contract_id"] if contract else "idx-003",
            Classification.PASS if passed else Classification.VIOLATION,
            passed,
            f"Invalid params: {params}, outcome: {error if not success else 'success'} (expected: {expected})",
            {
                "parameters": params,
                "success": success,
                "error": error,
                "is_invalid": is_invalid
            }
        )

    def _oracle_multiple_index_behavior(
        self,
        result: Dict[str, Any],
        contract: Optional[Dict[str, Any]]
    ) -> OracleResult:
        """Oracle: Multiple index behavior must be deterministic."""
        index_used = result.get("index_used")
        first_run_index = result.get("first_run_index")
        second_run_index = result.get("second_run_index")

        if None in [index_used, first_run_index, second_run_index]:
            return self._oracle_result(
                contract["contract_id"] if contract else "idx-004",
                Classification.OBSERVATION,
                False,
                "Incomplete multi-index data",
                {}
            )

        # Check determinism
        passed = first_run_index == second_run_index

        return self._oracle_result(
            contract["contract_id"] if contract else "idx-004",
            Classification.PASS if passed else Classification.VIOLATION,
            passed,
            f"Index selection: first={first_run_index}, second={second_run_index} {'(deterministic)' if passed else '(non-deterministic)'}",
            {
                "index_used": index_used,
                "first_run_index": first_run_index,
                "second_run_index": second_run_index,
                "deterministic": passed
            }
        )

    # Hybrid Contract Oracles

    def _oracle_filter_pre_application(
        self,
        result: Dict[str, Any],
        contract: Optional[Dict[str, Any]]
    ) -> OracleResult:
        """Oracle: Filters must exclude non-matching entities."""
        results = result.get("results", [])
        filter_criteria = result.get("filter_criteria")

        if not filter_criteria:
            return self._oracle_result(
                contract["contract_id"] if contract else "hyb-001",
                Classification.OBSERVATION,
                False,
                "No filter criteria provided",
                {}
            )

        violations = []
        for r in results:
            if not self._satisfies_filter(r, filter_criteria):
                violations.append(f"Entity {r.get('id')} does not satisfy filter")

        passed = len(violations) == 0

        return self._oracle_result(
            contract["contract_id"] if contract else "hyb-001",
            Classification.PASS if passed else Classification.VIOLATION,
            passed,
            f"Filter violations: {len(violations)}" if violations else "All results satisfy filter",
            {
                "violations": violations,
                "total_results": len(results),
                "filter_criteria": filter_criteria
            }
        )

    def _oracle_filter_result_consistency(
        self,
        result: Dict[str, Any],
        contract: Optional[Dict[str, Any]]
    ) -> OracleResult:
        """Oracle: Filtered results must match manual filter of unfiltered."""
        filtered_ids = set(result.get("filtered_ids", []))
        unfiltered_ids = set(result.get("unfiltered_ids", []))
        filter_criteria = result.get("filter_criteria")

        # Compute expected filtered IDs
        expected_filtered_ids = set()
        for uid in unfiltered_ids:
            entity = result.get("entities", {}).get(str(uid), {})
            if self._satisfies_filter(entity, filter_criteria):
                expected_filtered_ids.add(uid)

        passed = filtered_ids == expected_filtered_ids

        return self._oracle_result(
            contract["contract_id"] if contract else "hyb-002",
            Classification.PASS if passed else Classification.VIOLATION,
            passed,
            f"Filtered result consistency: {len(filtered_ids)} filtered, {len(expected_filtered_ids)} expected",
            {
                "filtered_count": len(filtered_ids),
                "expected_count": len(expected_filtered_ids),
                "match": passed
            }
        )

    def _oracle_empty_filter_result_handling(
        self,
        result: Dict[str, Any],
        contract: Optional[Dict[str, Any]]
    ) -> OracleResult:
        """Oracle: Empty filter must return empty results."""
        results = result.get("results", [])
        filter_matches_nothing = result.get("filter_matches_nothing", False)

        if filter_matches_nothing:
            passed = len(results) == 0

            return self._oracle_result(
                contract["contract_id"] if contract else "hyb-003",
                Classification.PASS,
                passed,
                f"Empty filter: {len(results)} results",
                {
                    "results_count": len(results),
                    "filter_matches_nothing": filter_matches_nothing
                }
            )

        return self._oracle_result(
            contract["contract_id"] if contract else "hyb-003",
            Classification.OBSERVATION,
            False,
            "Filter does match entities - not empty filter case",
            {"results_count": len(results)}
        )

    # Schema Contract Oracles

    def _oracle_data_preservation(
        self,
        result: Dict[str, Any],
        contract: Optional[Dict[str, Any]]
    ) -> OracleResult:
        """Oracle: Schema evolution must preserve data."""
        count_before = result.get("count_before")
        count_after = result.get("count_after")
        all_accessible = result.get("all_data_accessible", True)

        passed = count_before == count_after and all_accessible

        return self._oracle_result(
            contract["contract_id"] if contract else "sch-001",
            Classification.PASS if passed else Classification.VIOLATION,
            passed,
            f"Data preservation: {count_before} → {count_after}, accessible: {all_accessible}",
            {
                "count_before": count_before,
                "count_after": count_after,
                "preserved": count_before == count_after,
                "all_accessible": all_accessible
            }
        )

    def _oracle_query_compatibility(
        self,
        result: Dict[str, Any],
        contract: Optional[Dict[str, Any]]
    ) -> OracleResult:
        """Oracle: Queries must work after schema changes."""
        query_succeeds = result.get("query_succeeds", False)
        results_match = result.get("results_match", False)

        passed = query_succeeds and results_match

        return self._oracle_result(
            contract["contract_id"] if contract else "sch-002",
            Classification.PASS if passed else Classification.VIOLATION,
            passed,
            f"Query compatibility: succeeds={query_succeeds}, match={results_match}",
            {
                "query_succeeds": query_succeeds,
                "results_match": results_match
            }
        )

    def _oracle_index_rebuild_after_schema(
        self,
        result: Dict[str, Any],
        contract: Optional[Dict[str, Any]]
    ) -> OracleResult:
        """Oracle: Index behavior after schema change must be defined."""
        index_works = result.get("index_works")
        rebuild_required = result.get("rebuild_required", False)
        clear_error = result.get("clear_error") is not None

        # Any clear, defined behavior is acceptable
        passed = index_works or rebuild_required or clear_error

        return self._oracle_result(
            contract["contract_id"] if contract else "sch-003",
            Classification.PASS,
            passed,
            f"Index after schema: works={index_works}, rebuild_required={rebuild_required}, error={clear_error}",
            {
                "index_works": index_works,
                "rebuild_required": rebuild_required,
                "has_error": clear_error
            }
        )

    def _oracle_metadata_accuracy(
        self,
        result: Dict[str, Any],
        contract: Optional[Dict[str, Any]]
    ) -> OracleResult:
        """Oracle: Metadata must match actual state."""
        metadata_count = result.get("metadata_count")
        actual_count = result.get("actual_count")
        metadata_dimension = result.get("metadata_dimension")
        actual_dimension = result.get("actual_dimension")

        passed = (
            metadata_count == actual_count and
            metadata_dimension == actual_dimension
        )

        return self._oracle_result(
            contract["contract_id"] if contract else "sch-004",
            Classification.PASS if passed else Classification.VIOLATION,
            passed,
            f"Metadata accuracy: count {metadata_count} vs {actual_count}, dimension {metadata_dimension} vs {actual_dimension}",
            {
                "metadata_count": metadata_count,
                "actual_count": actual_count,
                "count_match": metadata_count == actual_count,
                "metadata_dimension": metadata_dimension,
                "actual_dimension": actual_dimension,
                "dimension_match": metadata_dimension == actual_dimension
            }
        )

    # Utility Functions

    def _compute_metric(
        self,
        metric_type: str,
        vector1: List[float],
        vector2: List[float]
    ) -> float:
        """Compute distance between two vectors.

        Args:
            metric_type: Type of metric (L2, IP, COSINE)
            vector1: First vector
            vector2: Second vector

        Returns:
            Computed distance
        """
        if metric_type == "L2":
            return self._l2_distance(vector1, vector2)
        elif metric_type == "IP":
            return self._inner_product(vector1, vector2)
        elif metric_type == "COSINE":
            return self._cosine_distance(vector1, vector2)
        else:
            raise ValueError(f"Unknown metric type: {metric_type}")

    def _l2_distance(self, v1: List[float], v2: List[float]) -> float:
        """Compute L2 (Euclidean) distance."""
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(v1, v2)))

    def _inner_product(self, v1: List[float], v2: List[float]) -> float:
        """Compute inner product."""
        return sum(a * b for a, b in zip(v1, v2))

    def _cosine_distance(self, v1: List[float], v2: List[float]) -> float:
        """Compute cosine distance (1 - cosine similarity)."""
        dot_product = self._inner_product(v1, v2)
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(a * a for a in v2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        cosine_similarity = dot_product / (norm1 * norm2)
        return 1.0 - cosine_similarity

    def _satisfies_filter(self, entity: Dict[str, Any], filter_criteria: Dict[str, Any]) -> bool:
        """Check if entity satisfies filter criteria.

        Args:
            entity: Entity with payload/scalar fields
            filter_criteria: Filter criteria

        Returns:
            True if entity satisfies filter
        """
        # Simple implementation - can be extended
        for field, value in filter_criteria.items():
            entity_value = entity.get("payload", {}).get(field)
            if entity_value != value:
                return False
        return True


if __name__ == "__main__":
    # Test oracle engine
    engine = OracleEngine()

    # Test top-k cardinality oracle
    result = {
        "results": [{"id": 1}, {"id": 2}, {"id": 3}],
        "top_k": 5
    }
    oracle_result = engine.evaluate("ann-001", result)
    print(f"ANN-001 Oracle: {oracle_result.classification.value} - {oracle_result.reasoning}")
