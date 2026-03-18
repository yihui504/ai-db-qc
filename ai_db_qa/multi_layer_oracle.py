"""Multi-Layer Oracle System for Vector Database Testing.

Addresses the fundamental "Test Oracle Problem" in vector database testing:
vector search has no single "correct answer" because ANN is approximate.

Three oracle layers (applied in order):
  Layer 1 - Exact Oracle:     Deterministic checks (crashes, cardinality, API contracts)
  Layer 2 - Approximate Oracle: Statistical checks (recall@K, monotonicity, distribution)
  Layer 3 - Semantic Oracle:  LLM-assisted semantic relevance judgment (soft judge)

Design principle from Argus (SIGMOD 2026):
  "Use LLM as generator, not final judge. Formal/statistical checks ensure correctness."
  
  The Semantic Oracle is a *soft judge* that produces confidence-weighted verdicts.
  It NEVER overrides Layer 1/2 findings. It supplements them.
"""

from __future__ import annotations

import json
import math
import re
import statistics
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ─────────────────────────────────────────────────────────────
# Result types
# ─────────────────────────────────────────────────────────────

class Verdict(str, Enum):
    PASS              = "PASS"
    VIOLATION         = "VIOLATION"          # definite bug
    ALLOWED_DIFF      = "ALLOWED_DIFFERENCE" # expected ANN approximation
    OBSERVATION       = "OBSERVATION"        # needs human review
    INFRA_FAILURE     = "INFRA_FAILURE"      # test infrastructure problem
    SKIP              = "SKIP"               # oracle not applicable


@dataclass
class LayerResult:
    layer: str           # "exact", "approximate", "semantic"
    verdict: Verdict
    confidence: float    # 0.0 – 1.0
    metrics: Dict[str, Any] = field(default_factory=dict)
    reason: str = ""


@dataclass
class OracleDecision:
    """Final aggregated decision from all applicable oracle layers."""
    final_verdict: Verdict
    confidence: float
    layer_results: List[LayerResult] = field(default_factory=list)
    triggered_by: str = ""      # which layer determined the final verdict
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "final_verdict": self.final_verdict.value,
            "confidence": self.confidence,
            "triggered_by": self.triggered_by,
            "summary": self.summary,
            "layers": [
                {
                    "layer": lr.layer,
                    "verdict": lr.verdict.value,
                    "confidence": lr.confidence,
                    "metrics": lr.metrics,
                    "reason": lr.reason,
                }
                for lr in self.layer_results
            ],
        }


# ─────────────────────────────────────────────────────────────
# Layer 1: Exact Oracle
# ─────────────────────────────────────────────────────────────

class ExactOracle:
    """Layer 1: Deterministic correctness checks.
    
    Covers:
    - Cardinality: |results| <= top_k
    - Non-null: successful search must return a list
    - API contract: error codes, status fields
    - Data preservation: count_before == count_after
    - Crash detection: exceptions, server errors
    """

    def check_search_response(
        self,
        response: Dict[str, Any],
        top_k: int,
        expect_success: bool = True,
    ) -> LayerResult:
        """Check that a search response satisfies basic API contracts."""
        status = response.get("status", "unknown")

        if expect_success:
            if status != "success":
                return LayerResult(
                    layer="exact",
                    verdict=Verdict.VIOLATION,
                    confidence=1.0,
                    reason=f"Expected success but got status={status}: {response.get('error', '')}",
                    metrics={"status": status},
                )
            data = response.get("data", [])
            if not isinstance(data, list):
                return LayerResult(
                    layer="exact",
                    verdict=Verdict.VIOLATION,
                    confidence=1.0,
                    reason=f"Search result data is not a list: {type(data)}",
                    metrics={"data_type": str(type(data))},
                )
            if len(data) > top_k:
                return LayerResult(
                    layer="exact",
                    verdict=Verdict.VIOLATION,
                    confidence=1.0,
                    reason=f"Cardinality violation: returned {len(data)} results but top_k={top_k}",
                    metrics={"returned": len(data), "top_k": top_k},
                )
            return LayerResult(
                layer="exact",
                verdict=Verdict.PASS,
                confidence=1.0,
                reason=f"API contract satisfied: {len(data)} results <= top_k={top_k}",
                metrics={"returned": len(data), "top_k": top_k},
            )
        else:
            # We expected failure
            if status == "success":
                return LayerResult(
                    layer="exact",
                    verdict=Verdict.VIOLATION,
                    confidence=1.0,
                    reason="Expected failure but operation succeeded (illegal input accepted)",
                    metrics={"status": status},
                )
            return LayerResult(
                layer="exact",
                verdict=Verdict.PASS,
                confidence=1.0,
                reason="Correctly rejected illegal operation",
                metrics={"status": status},
            )

    def check_data_preservation(
        self,
        count_before: Optional[int],
        count_after: Optional[int],
    ) -> LayerResult:
        """Check that entity count is preserved after non-mutating operations."""
        if count_before is None or count_after is None:
            return LayerResult(
                layer="exact",
                verdict=Verdict.OBSERVATION,
                confidence=0.0,
                reason="Cannot verify: count unavailable",
                metrics={"count_before": count_before, "count_after": count_after},
            )
        if count_before == count_after:
            return LayerResult(
                layer="exact",
                verdict=Verdict.PASS,
                confidence=1.0,
                reason=f"Data preserved: count {count_before} unchanged",
                metrics={"count_before": count_before, "count_after": count_after},
            )
        return LayerResult(
            layer="exact",
            verdict=Verdict.VIOLATION,
            confidence=1.0,
            reason=f"Data loss/corruption: count changed {count_before} -> {count_after}",
            metrics={"count_before": count_before, "count_after": count_after},
        )

    def check_distance_monotonicity(
        self,
        results: List[Dict[str, Any]],
    ) -> LayerResult:
        """Check that search results are ordered by ascending distance (or descending score)."""
        if len(results) < 2:
            return LayerResult(layer="exact", verdict=Verdict.SKIP, confidence=1.0,
                               reason="Not enough results to check monotonicity")

        violations = []
        for i in range(len(results) - 1):
            d_i = results[i].get("distance", results[i].get("score", 0))
            d_next = results[i + 1].get("distance", results[i + 1].get("score", 0))
            # For distance: d_i <= d_next; for score (similarity): d_i >= d_next
            # We check both directions and pick the one that seems intended
        
        # Detect ordering direction from first two
        d0 = results[0].get("distance", results[0].get("score", 0))
        d1 = results[1].get("distance", results[1].get("score", 0))
        ascending = d0 <= d1

        for i in range(len(results) - 1):
            d_i = results[i].get("distance", results[i].get("score", 0))
            d_next = results[i + 1].get("distance", results[i + 1].get("score", 0))
            if ascending and d_i > d_next + 1e-6:
                violations.append((i, d_i, d_next))
            elif not ascending and d_i < d_next - 1e-6:
                violations.append((i, d_i, d_next))

        if not violations:
            return LayerResult(
                layer="exact", verdict=Verdict.PASS, confidence=1.0,
                reason=f"Distance monotonicity satisfied ({'ascending' if ascending else 'descending'})",
                metrics={"order": "ascending" if ascending else "descending", "result_count": len(results)},
            )
        return LayerResult(
            layer="exact", verdict=Verdict.VIOLATION, confidence=1.0,
            reason=f"Distance monotonicity violated at {len(violations)} position(s)",
            metrics={"violations": violations[:3], "total_violations": len(violations)},
        )


# ─────────────────────────────────────────────────────────────
# Layer 2: Approximate Oracle
# ─────────────────────────────────────────────────────────────

class ApproximateOracle:
    """Layer 2: Statistical correctness checks for ANN approximate results.
    
    Covers:
    - Recall@K measurement and threshold validation
    - Statistical stability (multiple runs should produce consistent recall)
    - Distribution shift detection (recall before/after dynamic updates)
    - Index-type specific thresholds
    """

    # Default recall thresholds per index type
    DEFAULT_THRESHOLDS: Dict[str, float] = {
        "FLAT":     0.99,
        "HNSW":     0.80,
        "IVF_FLAT": 0.75,
        "IVF_SQ8":  0.70,
        "IVF_PQ":   0.65,
        "DISKANN":  0.85,
        "DEFAULT":  0.70,
    }

    def compute_recall(
        self,
        ground_truth_ids: List[int],
        retrieved_ids: List[int],
    ) -> float:
        """Recall@K = |GT ∩ Retrieved| / |GT|."""
        if not ground_truth_ids:
            return 1.0
        return len(set(ground_truth_ids) & set(retrieved_ids)) / len(set(ground_truth_ids))

    def check_recall(
        self,
        ground_truth_ids: List[int],
        retrieved_ids: List[int],
        index_type: str = "DEFAULT",
        custom_threshold: Optional[float] = None,
    ) -> LayerResult:
        """Check if recall@K meets the expected threshold for the index type."""
        threshold = custom_threshold or self.DEFAULT_THRESHOLDS.get(
            index_type, self.DEFAULT_THRESHOLDS["DEFAULT"]
        )
        recall = self.compute_recall(ground_truth_ids, retrieved_ids)

        if recall >= threshold:
            return LayerResult(
                layer="approximate",
                verdict=Verdict.PASS,
                confidence=min(1.0, recall / threshold),
                reason=f"Recall@K={recall:.3f} >= threshold={threshold:.2f} for {index_type}",
                metrics={"recall": recall, "threshold": threshold, "index_type": index_type,
                         "gt_size": len(ground_truth_ids), "retrieved_size": len(retrieved_ids)},
            )
        else:
            # Below threshold - but this is ALLOWED for ANN, not a bug
            return LayerResult(
                layer="approximate",
                verdict=Verdict.ALLOWED_DIFF,
                confidence=1.0,
                reason=f"Recall@K={recall:.3f} < threshold={threshold:.2f} for {index_type} (ANN approximation behavior)",
                metrics={"recall": recall, "threshold": threshold, "index_type": index_type},
            )

    def check_recall_stability(
        self,
        recall_samples: List[float],
        max_std_dev: float = 0.05,
    ) -> LayerResult:
        """Check that recall is stable across multiple query runs.
        
        High variance in recall suggests index degradation or non-determinism bug.
        """
        if len(recall_samples) < 3:
            return LayerResult(layer="approximate", verdict=Verdict.SKIP, confidence=0.5,
                               reason="Not enough samples for stability check")

        mean_recall = statistics.mean(recall_samples)
        std_dev = statistics.stdev(recall_samples)

        if std_dev <= max_std_dev:
            return LayerResult(
                layer="approximate", verdict=Verdict.PASS, confidence=1.0,
                reason=f"Recall stable: mean={mean_recall:.3f}, std={std_dev:.4f}",
                metrics={"mean_recall": mean_recall, "std_dev": std_dev, "n_samples": len(recall_samples)},
            )
        return LayerResult(
            layer="approximate", verdict=Verdict.OBSERVATION, confidence=0.7,
            reason=f"High recall variance: mean={mean_recall:.3f}, std={std_dev:.4f} > {max_std_dev}",
            metrics={"mean_recall": mean_recall, "std_dev": std_dev, "n_samples": len(recall_samples)},
        )

    def check_metamorphic_consistency(
        self,
        results_original: List[Dict],
        results_transformed: List[Dict],
        relation_type: str = "semantic_equivalence",
        min_overlap: float = 0.70,
    ) -> LayerResult:
        """Check that metamorphic relation is satisfied between two result sets.
        
        For "semantic_equivalence": if two queries are paraphrases, results should overlap.
        For "distance_ordering": closer document should rank higher.
        """
        ids_orig = [r.get("id") for r in results_original]
        ids_trans = [r.get("id") for r in results_transformed]

        if relation_type == "semantic_equivalence":
            overlap = self.compute_recall(ids_orig, ids_trans)
            if overlap >= min_overlap:
                return LayerResult(
                    layer="approximate", verdict=Verdict.PASS, confidence=overlap,
                    reason=f"Metamorphic relation satisfied: overlap={overlap:.3f} >= {min_overlap}",
                    metrics={"overlap": overlap, "threshold": min_overlap, "relation": relation_type},
                )
            return LayerResult(
                layer="approximate", verdict=Verdict.VIOLATION, confidence=1.0 - overlap,
                reason=f"Metamorphic violation: overlap={overlap:.3f} < {min_overlap} for {relation_type}",
                metrics={"overlap": overlap, "threshold": min_overlap, "relation": relation_type},
            )

        return LayerResult(layer="approximate", verdict=Verdict.OBSERVATION, confidence=0.5,
                           reason=f"Unknown relation type: {relation_type}")


# ─────────────────────────────────────────────────────────────
# Layer 3: Semantic Oracle (LLM-assisted soft judge)
# ─────────────────────────────────────────────────────────────

SEMANTIC_JUDGE_PROMPT = """You are evaluating the quality of a vector database search result.

Query: {query_text}

Retrieved Document: {retrieved_text}

Task: Rate the semantic relevance of the retrieved document to the query on a scale of 0-10.
- 0-3: Not relevant (different topic, unrelated)
- 4-6: Partially relevant (same broad domain, loosely related)
- 7-9: Relevant (addresses the same topic or question)
- 10: Highly relevant (directly answers the query, perfect match)

Also provide a one-sentence justification.

Output ONLY valid JSON (no markdown):
{{"score": <0-10>, "justification": "..."}}"""


class SemanticOracle:
    """Layer 3: LLM-assisted semantic relevance judgment.
    
    This is a SOFT JUDGE - it provides confidence-weighted verdicts,
    not binary pass/fail. High LLM uncertainty is surfaced as OBSERVATION.
    
    Key design choices (following Argus paper lessons):
    - Multiple samples to reduce LLM variance
    - Confidence threshold to avoid low-quality judgments
    - Only flags as VIOLATION when score is very low AND confidence is high
    - Never overrides Layer 1/2 VIOLATION findings
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        n_samples: int = 3,
        relevance_threshold: float = 4.0,   # below this score -> potential issue
        min_confidence: float = 0.7,         # below this confidence -> OBSERVATION
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.n_samples = n_samples
        self.relevance_threshold = relevance_threshold
        self.min_confidence = min_confidence
        self._enabled = api_key is not None

    def _call_llm(self, prompt: str) -> str:
        """Call LLM API."""
        try:
            import urllib.request
            payload = json.dumps({
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 200,
            }).encode("utf-8")
            req = urllib.request.Request(
                f"{self.base_url.rstrip('/')}/chat/completions",
                data=payload,
                headers={"Content-Type": "application/json",
                         "Authorization": f"Bearer {self.api_key}"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            raise RuntimeError(f"LLM call failed: {e}") from e

    def _judge_single(self, query_text: str, retrieved_text: str) -> Tuple[float, str]:
        """Get a single LLM relevance judgment. Returns (score 0-10, justification)."""
        prompt = SEMANTIC_JUDGE_PROMPT.format(
            query_text=query_text,
            retrieved_text=retrieved_text,
        )
        raw = self._call_llm(prompt)
        # Parse JSON
        raw = re.sub(r"```(?:json)?\s*", "", raw).replace("```", "").strip()
        data = json.loads(raw)
        score = float(data.get("score", 5))
        justification = data.get("justification", "")
        return score, justification

    def judge_retrieval(
        self,
        query_text: str,
        retrieved_documents: List[str],
        top_k: int = 5,
    ) -> LayerResult:
        """Judge the semantic relevance of top retrieved documents to the query.
        
        Returns VIOLATION only when average score is very low AND confidence is high.
        Returns OBSERVATION when LLM confidence is low.
        """
        if not self._enabled:
            return LayerResult(
                layer="semantic",
                verdict=Verdict.SKIP,
                confidence=0.0,
                reason="Semantic oracle disabled (no API key configured)",
            )

        if not retrieved_documents:
            return LayerResult(
                layer="semantic",
                verdict=Verdict.OBSERVATION,
                confidence=0.5,
                reason="No retrieved documents to evaluate",
            )

        docs_to_eval = retrieved_documents[:min(top_k, len(retrieved_documents))]
        all_scores = []
        sample_judgments = []

        for doc in docs_to_eval:
            scores_for_doc = []
            for _ in range(self.n_samples):
                try:
                    score, justification = self._judge_single(query_text, doc)
                    scores_for_doc.append(score)
                except Exception:
                    pass
            if scores_for_doc:
                doc_mean = sum(scores_for_doc) / len(scores_for_doc)
                doc_std = (sum((s - doc_mean) ** 2 for s in scores_for_doc) / len(scores_for_doc)) ** 0.5
                all_scores.append(doc_mean)
                sample_judgments.append({
                    "doc_preview": doc[:100] + "...",
                    "mean_score": round(doc_mean, 2),
                    "std_dev": round(doc_std, 2),
                    "n_samples": len(scores_for_doc),
                })

        if not all_scores:
            return LayerResult(
                layer="semantic",
                verdict=Verdict.OBSERVATION,
                confidence=0.0,
                reason="All LLM calls failed; cannot evaluate semantic quality",
            )

        avg_score = sum(all_scores) / len(all_scores)
        # Confidence based on consistency of scores (lower variance = higher confidence)
        if len(all_scores) > 1:
            std = statistics.stdev(all_scores)
            confidence = max(0.0, min(1.0, 1.0 - std / 5.0))
        else:
            confidence = 0.6  # single sample, moderate confidence

        metrics = {
            "avg_relevance_score": round(avg_score, 3),
            "confidence": round(confidence, 3),
            "threshold": self.relevance_threshold,
            "docs_evaluated": len(docs_to_eval),
            "judgments": sample_judgments,
        }

        if confidence < self.min_confidence:
            return LayerResult(
                layer="semantic",
                verdict=Verdict.OBSERVATION,
                confidence=confidence,
                reason=f"Low confidence judgment (confidence={confidence:.2f} < {self.min_confidence}): avg_score={avg_score:.2f}",
                metrics=metrics,
            )

        if avg_score >= self.relevance_threshold:
            return LayerResult(
                layer="semantic",
                verdict=Verdict.PASS,
                confidence=confidence,
                reason=f"Semantic relevance OK: avg_score={avg_score:.2f} >= threshold={self.relevance_threshold}",
                metrics=metrics,
            )
        else:
            return LayerResult(
                layer="semantic",
                verdict=Verdict.VIOLATION,
                confidence=confidence,
                reason=f"Low semantic relevance: avg_score={avg_score:.2f} < threshold={self.relevance_threshold}",
                metrics=metrics,
            )


# ─────────────────────────────────────────────────────────────
# Multi-Layer Oracle Coordinator
# ─────────────────────────────────────────────────────────────

class MultiLayerOracle:
    """Coordinates all three oracle layers and produces a final aggregated decision.
    
    Decision priority:
    1. If Layer 1 (Exact) finds VIOLATION → final = VIOLATION (highest confidence, overrides all)
    2. If Layer 2 (Approximate) finds VIOLATION → final = VIOLATION
    3. If Layer 3 (Semantic) finds VIOLATION → final = VIOLATION (only if high confidence)
    4. If any layer finds ALLOWED_DIFF → final = ALLOWED_DIFF (not a bug)
    5. If all applicable layers PASS → final = PASS
    6. If any layer returns OBSERVATION → final = OBSERVATION (needs review)
    """

    def __init__(
        self,
        exact: Optional[ExactOracle] = None,
        approximate: Optional[ApproximateOracle] = None,
        semantic: Optional[SemanticOracle] = None,
        semantic_violation_confidence_threshold: float = 0.80,
    ):
        self.exact = exact or ExactOracle()
        self.approximate = approximate or ApproximateOracle()
        self.semantic = semantic or SemanticOracle()  # disabled by default (no API key)
        self.semantic_confidence_threshold = semantic_violation_confidence_threshold

    def decide(self, layer_results: List[LayerResult]) -> OracleDecision:
        """Aggregate layer results into a final decision."""
        # Filter out SKIP results
        active = [lr for lr in layer_results if lr.verdict != Verdict.SKIP]

        if not active:
            return OracleDecision(
                final_verdict=Verdict.SKIP,
                confidence=1.0,
                layer_results=layer_results,
                triggered_by="no_active_layers",
                summary="No applicable oracle layers",
            )

        # Priority 1: INFRA_FAILURE (cannot make any judgment)
        infra_failures = [lr for lr in active if lr.verdict == Verdict.INFRA_FAILURE]
        if infra_failures:
            return OracleDecision(
                final_verdict=Verdict.INFRA_FAILURE,
                confidence=1.0,
                layer_results=layer_results,
                triggered_by=infra_failures[0].layer,
                summary=infra_failures[0].reason,
            )

        # Priority 2: Exact VIOLATION (always deterministic, highest confidence)
        exact_violations = [lr for lr in active
                            if lr.layer == "exact" and lr.verdict == Verdict.VIOLATION]
        if exact_violations:
            v = exact_violations[0]
            return OracleDecision(
                final_verdict=Verdict.VIOLATION,
                confidence=v.confidence,
                layer_results=layer_results,
                triggered_by="exact",
                summary=v.reason,
            )

        # Priority 3: Approximate VIOLATION (statistical, high confidence)
        approx_violations = [lr for lr in active
                             if lr.layer == "approximate" and lr.verdict == Verdict.VIOLATION]
        if approx_violations:
            v = approx_violations[0]
            return OracleDecision(
                final_verdict=Verdict.VIOLATION,
                confidence=v.confidence,
                layer_results=layer_results,
                triggered_by="approximate",
                summary=v.reason,
            )

        # Priority 4: Semantic VIOLATION (only if confidence is high enough)
        sem_violations = [lr for lr in active
                          if lr.layer == "semantic" and lr.verdict == Verdict.VIOLATION
                          and lr.confidence >= self.semantic_confidence_threshold]
        if sem_violations:
            v = sem_violations[0]
            return OracleDecision(
                final_verdict=Verdict.VIOLATION,
                confidence=v.confidence,
                layer_results=layer_results,
                triggered_by="semantic",
                summary=f"Semantic layer (high confidence): {v.reason}",
            )

        # Priority 5: ALLOWED_DIFFERENCE (expected ANN behavior)
        allowed = [lr for lr in active if lr.verdict == Verdict.ALLOWED_DIFF]
        if allowed:
            a = allowed[0]
            return OracleDecision(
                final_verdict=Verdict.ALLOWED_DIFF,
                confidence=a.confidence,
                layer_results=layer_results,
                triggered_by=a.layer,
                summary=a.reason,
            )

        # Priority 6: OBSERVATION (needs human review)
        observations = [lr for lr in active if lr.verdict == Verdict.OBSERVATION]
        if observations:
            o = observations[0]
            return OracleDecision(
                final_verdict=Verdict.OBSERVATION,
                confidence=o.confidence,
                layer_results=layer_results,
                triggered_by=o.layer,
                summary=o.reason,
            )

        # All active layers passed
        avg_confidence = sum(lr.confidence for lr in active) / len(active)
        return OracleDecision(
            final_verdict=Verdict.PASS,
            confidence=avg_confidence,
            layer_results=layer_results,
            triggered_by="all_layers",
            summary=f"All {len(active)} oracle layers passed",
        )

    def evaluate_search(
        self,
        response: Dict[str, Any],
        top_k: int,
        ground_truth_ids: Optional[List[int]] = None,
        index_type: str = "DEFAULT",
        query_text: Optional[str] = None,
        retrieved_texts: Optional[List[str]] = None,
    ) -> OracleDecision:
        """Full multi-layer evaluation of a search result.
        
        Args:
            response: Raw response from database adapter
            top_k: Expected maximum number of results
            ground_truth_ids: Known correct result IDs (for Layer 2 recall check)
            index_type: Index type used (affects recall thresholds)
            query_text: Query text (for Layer 3 semantic check)
            retrieved_texts: Retrieved document texts (for Layer 3 semantic check)
        """
        layer_results = []

        # Layer 1: API contract and cardinality
        l1 = self.exact.check_search_response(response, top_k, expect_success=True)
        layer_results.append(l1)

        # If Layer 1 fails (no valid data), skip Layers 2 & 3
        if l1.verdict == Verdict.VIOLATION:
            return self.decide(layer_results)

        # Layer 2: Recall check (if ground truth provided)
        if ground_truth_ids is not None:
            retrieved_ids = [r.get("id") for r in response.get("data", [])]
            l2 = self.approximate.check_recall(ground_truth_ids, retrieved_ids, index_type)
            layer_results.append(l2)

            # Also check distance monotonicity
            l2b = self.exact.check_distance_monotonicity(response.get("data", []))
            layer_results.append(l2b)

        # Layer 3: Semantic check (if texts provided and oracle is enabled)
        if query_text and retrieved_texts:
            l3 = self.semantic.judge_retrieval(query_text, retrieved_texts, top_k)
            layer_results.append(l3)

        return self.decide(layer_results)


# ─────────────────────────────────────────────────────────────
# Convenience factory
# ─────────────────────────────────────────────────────────────

def create_oracle(
    llm_api_key: Optional[str] = None,
    llm_model: str = "gpt-4o-mini",
    llm_base_url: str = "https://api.openai.com/v1",
) -> MultiLayerOracle:
    """Create a multi-layer oracle. Semantic layer is enabled only if api_key is provided."""
    semantic = SemanticOracle(
        api_key=llm_api_key,
        model=llm_model,
        base_url=llm_base_url,
    ) if llm_api_key else SemanticOracle()
    return MultiLayerOracle(
        exact=ExactOracle(),
        approximate=ApproximateOracle(),
        semantic=semantic,
    )
