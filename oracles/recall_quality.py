"""Recall quality oracle for index parameter validation.

This oracle validates ANN search quality through recall@K metrics rather than
exact set matching. It addresses the critical blind spot of "precision degradation"
bugs where index parameters are misconfigured (e.g., HNSW ef=1, IVF nlist=0),
which pass all quantity/subset oracles but severely degrade search quality.

Key innovation: introduces statistical tolerance into oracle validation,
allowing legitimate ANN probabilistic variations while catching real bugs.
"""

from __future__ import annotations

from typing import Any, Dict, List, Set
import numpy as np

from oracles.base import OracleBase
from schemas.case import TestCase
from schemas.result import ExecutionResult, OracleResult


class RecallQualityOracle(OracleBase):
    """Validate search quality through recall@K metrics.

    Uses ground truth vectors to compute recall@K: the fraction of true top-K
    neighbors returned by the search. This tolerates ANN approximation errors
    while catching index configuration bugs.

    Thresholds:
        - Strict: recall@K >= 0.95 (for small K, exact-ish results)
        - Standard: recall@K >= 0.80 (typical ANN acceptance)
        - Relaxed: recall@K >= 0.50 (very approximate searches)
    """

    def __init__(
        self,
        ground_truth_vectors: List[List[float]],
        ground_truth_ids: List[Any],
        strict_mode: bool = False,
        k_values: List[int] = [5, 10, 20]
    ):
        """Initialize recall quality oracle.

        Args:
            ground_truth_vectors: List of vectors for computing ground truth
            ground_truth_ids: Corresponding IDs for each ground truth vector
            strict_mode: If True, use 0.95 threshold; otherwise 0.80
            k_values: K values to evaluate (e.g., [5, 10, 20])
        """
        self.ground_truth_vectors = np.array(ground_truth_vectors)
        self.ground_truth_ids = ground_truth_ids
        self.k_values = k_values
        self.recall_threshold = 0.95 if strict_mode else 0.80

    def _compute_ground_truth_neighbors(
        self,
        query_vector: np.ndarray,
        k: int
    ) -> Set[Any]:
        """Compute true top-K neighbors using exact search (brute force)."""
        # Compute cosine similarity for all ground truth vectors
        query_norm = np.linalg.norm(query_vector)
        vectors_norm = np.linalg.norm(self.ground_truth_vectors, axis=1)

        similarities = np.dot(self.ground_truth_vectors, query_vector) / (
            vectors_norm * query_norm + 1e-8
        )

        # Get top-K indices (sort descending by similarity)
        top_k_indices = np.argpartition(similarities, -k)[-k:]
        top_k_indices = top_k_indices[np.argsort(-similarities[top_k_indices])]

        return set(self.ground_truth_ids[i] for i in top_k_indices)

    def _compute_recall(
        self,
        result_ids: Set[Any],
        ground_truth_ids: Set[Any],
        k: int
    ) -> float:
        """Compute recall@K."""
        if not ground_truth_ids:
            return 1.0  # Empty ground truth: vacuously perfect

        intersection = result_ids.intersection(ground_truth_ids)
        return len(intersection) / len(ground_truth_ids)

    def validate(
        self,
        case: TestCase,
        result: ExecutionResult,
        context: Dict[str, Any]
    ) -> OracleResult:
        """Validate search quality through recall@K metrics."""
        if case.operation not in ["search", "filtered_search"]:
            return OracleResult(
                oracle_id="recall_quality",
                passed=True,
                metrics={},
                explanation="Non-search operation: recall validation skipped"
            )

        # Check if operation succeeded
        if result.status != "success":
            return OracleResult(
                oracle_id="recall_quality",
                passed=True,
                metrics={},
                explanation="Operation failed: recall validation skipped"
            )

        # Get query vector from context
        query_vector = context.get("query_vector")
        if query_vector is None:
            return OracleResult(
                oracle_id="recall_quality",
                passed=True,
                metrics={},
                explanation="No query vector in context: recall validation skipped"
            )

        query_vector = np.array(query_vector)

        # Collect returned IDs
        result_ids = set()
        for item in result.response.get("data", []):
            if "id" in item:
                result_ids.add(item["id"])

        # Compute recall for each K
        recalls = {}
        violations = []

        for k in self.k_values:
            ground_truth = self._compute_ground_truth_neighbors(query_vector, k)
            result_at_k = set(list(result_ids)[:k])  # Top-K from results

            recall = self._compute_recall(result_at_k, ground_truth, k)
            recalls[f"recall@{k}"] = recall

            if recall < self.recall_threshold:
                violations.append({
                    "k": k,
                    "recall": recall,
                    "threshold": self.recall_threshold,
                    "expected_at_least": int(self.recall_threshold * k),
                    "actual_overlap": len(result_at_k.intersection(ground_truth))
                })

        if violations:
            violation_info = "\n".join(
                f"  - K={v['k']}: recall={v['recall']:.3f} < {v['threshold']:.2f} "
                f"(expected {v['expected_at_least']}, got {v['actual_overlap']})"
                for v in violations
            )

            return OracleResult(
                oracle_id="recall_quality",
                passed=False,
                metrics=recalls,
                expected_relation=f"recall@K >= {self.recall_threshold:.2f} for K in {self.k_values}",
                observed_relation=f"Violations:\n{violation_info}",
                explanation=f"Search quality degraded: recall below threshold. "
                           f"This may indicate misconfigured index parameters "
                           f"(e.g., HNSW ef too low, IVF nprobe too small)."
            )

        return OracleResult(
            oracle_id="recall_quality",
            passed=True,
            metrics=recalls,
            explanation=f"Search quality acceptable: all recall@K >= {self.recall_threshold:.2f}"
        )
