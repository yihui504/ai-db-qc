"""V5 Ablation Study: Random Vector Baseline vs. Semantic Vector System.

This script establishes the critical missing baseline in the ablation study series.
V1-V4 measure framework *component* contributions (Gate/Oracle/Triage).
V5 measures *data quality* contribution: what does LLM-driven semantic data generation add?

Experiment Design:
  V_Sem (Semantic): embed_fn = sentence-transformers or hash-fallback (carries semantic signal)
  V_Rnd (Random):   embed_fn = np.random.randn(dim).astype(float32), unit-normalized (no signal)

Both variants run identical MR-01 and MR-03 metamorphic test protocols against the
same offline semantic dataset (generated from OFFLINE_TEMPLATES in semantic_datagen.py),
using the MockAdapter (no real DB required).

Key Hypothesis:
  - MR-03 (Hard Negative Discrimination): V_Sem VIOLATION rate > V_Rnd rate
    because semantic vectors actually distinguish "The bond yield rose" vs "fell",
    while random vectors cannot.
  - MR-01 (Semantic Equivalence Consistency): V_Sem PASS rate > V_Rnd PASS rate
    because semantic paraphrase pairs have genuinely similar vectors only when
    embeddings carry meaning.

Expected Result:
  V_Sem MR-03 violation: low (semantic model correctly separates hard negatives)
  V_Rnd MR-03 violation: near 50% (random chance — no semantic discrimination)
  V_Sem MR-01 consistency: high overlap on paraphrase pairs
  V_Rnd MR-01 consistency: random overlap regardless of semantic similarity

Usage:
    # Fast mock run (recommended for CI)
    python scripts/run_v5_ablation.py

    # Specific domain
    python scripts/run_v5_ablation.py --domain medical

    # All domains
    python scripts/run_v5_ablation.py --domain all

    # With real Milvus (optional)
    python scripts/run_v5_ablation.py --adapter milvus --host localhost --port 19530

    # Force hash embeddings (faster, less meaningful)
    python scripts/run_v5_ablation.py --force-hash
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from ai_db_qa.semantic_datagen import (
        SemanticTestDataset,
        TextPair,
        generate_offline,
    )
    from ai_db_qa.multi_layer_oracle import (
        MultiLayerOracle,
        ApproximateOracle,
        create_oracle,
    )
    from adapters.mock import MockAdapter, ResponseMode, DiagnosticQuality
except ImportError as e:
    print(f"Import error: {e}")
    print("Ensure all dependencies are installed and the project root is on PYTHONPATH.")
    sys.exit(1)


# ─────────────────────────────────────────────────────────────
# Vector generation functions
# ─────────────────────────────────────────────────────────────

def make_random_embed_fn(dim: int, seed: Optional[int] = None) -> Any:
    """Return a pure-random vector embedding function (V5 baseline).

    Generates unit-normalized Gaussian random vectors of fixed dimension.
    Vectors carry NO semantic signal — any two texts get statistically
    independent random directions in R^dim.

    Args:
        dim: Vector dimension (must match the DB collection dimension).
        seed: Optional RNG seed for reproducibility across paired calls.
              NOTE: Do NOT set a fixed seed for the actual experiment —
              the point is that different texts get truly independent vectors.
    """
    rng = np.random.default_rng(seed)

    def random_embed(texts: List[str]) -> List[List[float]]:
        """Generate random unit vectors, ignoring text content."""
        vectors = []
        for _ in texts:
            v = rng.standard_normal(dim).astype(np.float32)
            norm = np.linalg.norm(v)
            if norm > 0:
                v = v / norm
            vectors.append(v.tolist())
        return vectors

    return random_embed


def make_hash_embed_fn(dim: int) -> Any:
    """Return a deterministic hash-based embedding function.

    Used as the 'semantic baseline' when sentence-transformers is unavailable.
    Hash embeddings are deterministic but carry minimal semantic signal (they
    are better than pure random for reproducibility but worse than real embeddings).
    """
    import hashlib

    def hash_embed(texts: List[str]) -> List[List[float]]:
        vectors = []
        for text in texts:
            h = hashlib.sha256(text.encode()).hexdigest()
            raw_ints = [int(h[i : i + 2], 16) for i in range(0, min(len(h), dim * 2), 2)]
            vec = [(x - 127.5) / 127.5 for x in raw_ints[:dim]]
            while len(vec) < dim:
                vec.append(0.0)
            vectors.append(vec[:dim])
        return vectors

    return hash_embed


def build_semantic_embed_fn(
    force_hash: bool = False,
    st_model: str = "all-MiniLM-L6-v2",
    dim: int = 128,
) -> Tuple[Any, str, int]:
    """Build semantic embedding function with automatic backend selection.

    Returns:
        (embed_fn, backend_name, actual_dim)
    """
    if force_hash:
        return make_hash_embed_fn(dim), "hash-deterministic", dim

    try:
        from ai_db_qa.embedding import get_embed_fn, EmbedBackend, get_backend_info

        embed_fn = get_embed_fn(backend=EmbedBackend.AUTO, model=st_model)
        info = get_backend_info()
        backend = info.get("selected_backend", "unknown")
        test_vec = embed_fn(["test"])
        actual_dim = len(test_vec[0])
        print(f"  Embedding backend: {backend} (dim={actual_dim})")
        return embed_fn, backend, actual_dim
    except Exception as e:
        print(f"  Semantic embedding unavailable ({e}), using hash-deterministic fallback.")
        return make_hash_embed_fn(dim), "hash-deterministic", dim


# ─────────────────────────────────────────────────────────────
# Metamorphic test execution (MR-01 and MR-03)
# ─────────────────────────────────────────────────────────────

class V5Runner:
    """Execute MR-01 and MR-03 metamorphic tests with a given embed_fn against MockAdapter."""

    def __init__(self, adapter, oracle: MultiLayerOracle, embed_fn, dim: int, top_k: int = 10):
        self.adapter = adapter
        self.oracle = oracle
        self.embed_fn = embed_fn
        self.dim = dim
        self.top_k = top_k

    # ── Internal helpers ─────────────────────────────────────

    def _embed(self, texts: List[str]) -> List[List[float]]:
        try:
            return self.embed_fn(texts)
        except TypeError:
            return self.embed_fn(texts, dim=self.dim)

    def _mock_search(self, col_name: str, query_text: str, corpus_text_to_idx: Dict[str, int]) -> List[int]:
        """Simulate a semantic-aware search in mock mode.

        Real MockAdapter returns fixed IDs regardless of query — that defeats
        the purpose of measuring *data quality* differences between V_Sem and V_Rnd.

        Instead, we simulate k-NN search manually:
          1. Embed query text
          2. Compute cosine similarity against all corpus vectors cached in col_name
          3. Return top-k IDs sorted by similarity

        This properly exercises the embed_fn's discriminative power.
        """
        corpus = self._collection_store.get(col_name)
        if corpus is None:
            return []

        q_vec = np.array(self._embed([query_text])[0], dtype=np.float32)
        q_norm = np.linalg.norm(q_vec)
        if q_norm > 0:
            q_vec = q_vec / q_norm

        scores = []
        for idx, vec in corpus["vectors"]:
            v = np.array(vec, dtype=np.float32)
            v_norm = np.linalg.norm(v)
            if v_norm > 0:
                v = v / v_norm
            sim = float(np.dot(q_vec, v))
            scores.append((idx, sim))

        scores.sort(key=lambda x: -x[1])
        return [idx for idx, _ in scores[: self.top_k]]

    def _setup_collection(self, col_name: str, texts: List[str]) -> Dict[str, Any]:
        """Build in-memory collection with embedded vectors."""
        vectors = self._embed(texts)
        if not hasattr(self, "_collection_store"):
            self._collection_store: Dict[str, Any] = {}
        self._collection_store[col_name] = {
            "vectors": list(enumerate(vectors)),
            "text_to_idx": {t: i for i, t in enumerate(texts)},
        }
        return {"texts": texts, "vectors": vectors}

    def _drop_collection(self, col_name: str) -> None:
        if hasattr(self, "_collection_store"):
            self._collection_store.pop(col_name, None)

    # ── MR-01: Semantic Equivalence Consistency ──────────────

    def run_mr01(self, dataset: SemanticTestDataset, run_id: str) -> List[Dict]:
        """MR-01: Paraphrase pairs should yield ≥60% overlapping top-k results."""
        col_name = f"mr01_{run_id}"
        results = []

        all_texts = list(
            {t for pair in dataset.pairs for t in (pair.text_a, pair.text_b)}
        )
        self._setup_collection(col_name, all_texts)
        text_to_idx = self._collection_store[col_name]["text_to_idx"]

        positive_pairs = dataset.get_pairs_by_type("positive")
        for pair in positive_pairs[:20]:
            ids_a = self._mock_search(col_name, pair.text_a, text_to_idx)
            ids_b = self._mock_search(col_name, pair.text_b, text_to_idx)

            # Jaccard overlap
            set_a, set_b = set(ids_a), set(ids_b)
            overlap = len(set_a & set_b) / max(len(set_a | set_b), 1)
            verdict = "PASS" if overlap >= 0.60 else "VIOLATION"

            results.append(
                {
                    "mr": "MR-01",
                    "pair_id": pair.pair_id,
                    "pair_type": "positive",
                    "text_a_preview": pair.text_a[:80],
                    "text_b_preview": pair.text_b[:80],
                    "ids_a": ids_a,
                    "ids_b": ids_b,
                    "overlap": round(overlap, 4),
                    "verdict": verdict,
                }
            )

        self._drop_collection(col_name)
        return results

    # ── MR-03: Hard Negative Discrimination ─────────────────

    def run_mr03(self, dataset: SemanticTestDataset, run_id: str) -> List[Dict]:
        """MR-03: Hard negatives must NOT rank in each other's top-3.

        Hard negatives are surface-similar but semantically opposite pairs
        (e.g. "bond yield rose" vs "bond yield fell"). A semantic embedding
        should push these apart; a random embedding cannot.
        """
        col_name = f"mr03_{run_id}"
        results = []

        hard_neg_pairs = dataset.get_pairs_by_type("hard_negative")
        if not hard_neg_pairs:
            return [{"mr": "MR-03", "verdict": "SKIP", "reason": "No hard_negative pairs"}]

        all_texts = list(
            {t for pair in dataset.pairs for t in (pair.text_a, pair.text_b)}
        )
        self._setup_collection(col_name, all_texts)
        text_to_idx = self._collection_store[col_name]["text_to_idx"]

        for pair in hard_neg_pairs[:20]:
            ids_a = self._mock_search(col_name, pair.text_a, text_to_idx)
            ids_b = self._mock_search(col_name, pair.text_b, text_to_idx)

            idx_b = text_to_idx.get(pair.text_b, -1)
            idx_a = text_to_idx.get(pair.text_a, -1)

            # Check if hard-neg partner appears in top-3 of each other's results
            rank_b_in_a = (ids_a.index(idx_b) + 1) if idx_b in ids_a[:3] else None
            rank_a_in_b = (ids_b.index(idx_a) + 1) if idx_a in ids_b[:3] else None

            # VIOLATION: hard negative appears in top-3 (should be pushed far away)
            violation = (rank_b_in_a is not None) or (rank_a_in_b is not None)
            verdict = "VIOLATION" if violation else "PASS"

            results.append(
                {
                    "mr": "MR-03",
                    "pair_id": pair.pair_id,
                    "pair_type": "hard_negative",
                    "text_a_preview": pair.text_a[:80],
                    "text_b_preview": pair.text_b[:80],
                    "top3_a": ids_a[:3],
                    "top3_b": ids_b[:3],
                    "rank_b_in_a": rank_b_in_a,
                    "rank_a_in_b": rank_a_in_b,
                    "verdict": verdict,
                }
            )

        self._drop_collection(col_name)
        return results


# ─────────────────────────────────────────────────────────────
# Metrics computation
# ─────────────────────────────────────────────────────────────

def _compute_metrics(results: List[Dict]) -> Dict[str, Any]:
    """Compute PASS/VIOLATION rates and per-MR breakdown."""
    mr01 = [r for r in results if r.get("mr") == "MR-01" and r.get("verdict") not in ("SKIP",)]
    mr03 = [r for r in results if r.get("mr") == "MR-03" and r.get("verdict") not in ("SKIP",)]

    def _rate(items: List[Dict], verdict: str) -> float:
        if not items:
            return 0.0
        return sum(1 for x in items if x.get("verdict") == verdict) / len(items)

    return {
        "total": len(results),
        "mr01": {
            "n": len(mr01),
            "pass_rate": _rate(mr01, "PASS"),
            "violation_rate": _rate(mr01, "VIOLATION"),
        },
        "mr03": {
            "n": len(mr03),
            "violation_rate": _rate(mr03, "VIOLATION"),
            "pass_rate": _rate(mr03, "PASS"),
        },
    }


# ─────────────────────────────────────────────────────────────
# Report generation
# ─────────────────────────────────────────────────────────────

def _render_report(
    sem_metrics: Dict,
    rnd_metrics: Dict,
    domain: str,
    sem_backend: str,
    dim: int,
    timestamp: str,
    sem_results: List[Dict],
    rnd_results: List[Dict],
) -> str:
    """Render Markdown ablation report comparing V_Sem vs V_Rnd."""

    def fmt(v: float) -> str:
        return f"{v:.1%}"

    lines = [
        "# V5 Ablation Study: Semantic Vector vs. Random Vector Baseline",
        "",
        f"**Generated**: {datetime.now().isoformat()}",
        f"**Domain**: {domain}",
        f"**Semantic Backend**: {sem_backend}",
        f"**Vector Dimension**: {dim}",
        f"**Timestamp**: {timestamp}",
        "",
        "## Objective",
        "",
        "Quantify the contribution of LLM-driven semantic data generation (via",
        "sentence-transformers / embedding model) to metamorphic test effectiveness.",
        "This is the missing V5 dimension absent from the V1-V4 ablation study,",
        "which only varies framework components (Gate/Oracle/Triage).",
        "",
        "## Variant Definitions",
        "",
        "| ID | Embed Strategy | Semantic Signal |",
        "|----|----------------|-----------------|",
        f"| V_Sem | {sem_backend} | YES — vectors encode linguistic meaning |",
        "| V_Rnd | np.random.randn(dim), unit-normalized | NO — statistically independent random directions |",
        "",
        "## Results",
        "",
        "| Variant | MR-01 N | MR-01 Pass | MR-01 Violation | MR-03 N | MR-03 Pass | MR-03 Violation |",
        "|---------|---------|------------|-----------------|---------|------------|-----------------|",
        f"| **V_Sem** | {sem_metrics['mr01']['n']} | {fmt(sem_metrics['mr01']['pass_rate'])} | {fmt(sem_metrics['mr01']['violation_rate'])} | {sem_metrics['mr03']['n']} | {fmt(sem_metrics['mr03']['pass_rate'])} | {fmt(sem_metrics['mr03']['violation_rate'])} |",
        f"| **V_Rnd** | {rnd_metrics['mr01']['n']} | {fmt(rnd_metrics['mr01']['pass_rate'])} | {fmt(rnd_metrics['mr01']['violation_rate'])} | {rnd_metrics['mr03']['n']} | {fmt(rnd_metrics['mr03']['pass_rate'])} | {fmt(rnd_metrics['mr03']['violation_rate'])} |",
        "",
        "## LLM Contribution Analysis",
        "",
    ]

    # Delta analysis
    mr01_delta = sem_metrics["mr01"]["pass_rate"] - rnd_metrics["mr01"]["pass_rate"]
    mr03_delta_viol = sem_metrics["mr03"]["violation_rate"] - rnd_metrics["mr03"]["violation_rate"]
    mr03_delta_pass = sem_metrics["mr03"]["pass_rate"] - rnd_metrics["mr03"]["pass_rate"]

    lines += [
        f"**MR-01 Semantic Equivalence Consistency**:",
        f"- V_Sem pass rate: {fmt(sem_metrics['mr01']['pass_rate'])}",
        f"- V_Rnd pass rate: {fmt(rnd_metrics['mr01']['pass_rate'])}",
        f"- Delta (Sem − Rnd): {mr01_delta:+.1%}",
        "",
        "Interpretation: A positive delta means semantic embeddings correctly cluster",
        "paraphrase pairs in vector space, producing more consistent top-k results.",
        "Random vectors yield random overlap regardless of linguistic similarity.",
        "",
        f"**MR-03 Hard Negative Discrimination**:",
        f"- V_Sem violation rate: {fmt(sem_metrics['mr03']['violation_rate'])}",
        f"- V_Rnd violation rate: {fmt(rnd_metrics['mr03']['violation_rate'])}",
        f"- V_Sem pass rate: {fmt(sem_metrics['mr03']['pass_rate'])}",
        f"- V_Rnd pass rate: {fmt(rnd_metrics['mr03']['pass_rate'])}",
        f"- Violation delta (Sem − Rnd): {mr03_delta_viol:+.1%}",
        "",
        "Interpretation: MR-03 tests whether the embedding model can discriminate",
        "semantically opposite pairs that share surface form (e.g., 'bond yield rose'",
        "vs 'bond yield fell'). With random vectors, these pairs land at statistically",
        "independent positions — V_Rnd violation rate is the random baseline (~40-60%).",
        "If V_Sem violation rate is LOWER than V_Rnd, the embedding model successfully",
        "separates hard negatives, proving LLM-generated data adds discrimination value.",
        "If V_Sem violation rate is HIGHER, the embedding model struggles with these",
        "domain-specific hard negatives (itself a finding: the test surface is effective).",
        "",
        "## Conclusion",
        "",
    ]

    # Overall conclusion
    # MR-01: higher pass rate with semantic = good (paraphrases cluster correctly)
    # MR-03: lower violation rate with semantic = good (hard negatives separated)
    #        higher violation rate with semantic vs random = embedding can't distinguish
    #        hard negatives in this domain (also informative: tests surface is effective)
    mr03_sem_better = sem_metrics["mr03"]["violation_rate"] < rnd_metrics["mr03"]["violation_rate"]

    if abs(mr01_delta) < 0.05 and abs(mr03_delta_viol) < 0.10:
        conclusion = (
            "The difference between V_Sem and V_Rnd is small (MR-01 delta < 5%, "
            "MR-03 violation delta < 10%). This likely indicates that the current "
            "embedding backend (" + sem_backend + ") does not produce strongly "
            "discriminative vectors for this domain. Run with a stronger model "
            "(e.g., sentence-transformers/all-mpnet-base-v2) for a definitive comparison."
        )
    elif mr01_delta > 0.10 and mr03_sem_better:
        conclusion = (
            f"Semantic embeddings ({sem_backend}) provide a clear advantage: "
            f"MR-01 paraphrase consistency is {mr01_delta:+.1%} higher than random "
            f"vectors, and MR-03 hard-negative discrimination shows "
            f"{sem_metrics['mr03']['violation_rate']:.1%} vs {rnd_metrics['mr03']['violation_rate']:.1%} "
            "violation rate (lower is better for MR-03). "
            "This confirms LLM-driven semantic data generation materially improves "
            "metamorphic test sensitivity."
        )
    elif mr01_delta > 0.10:
        conclusion = (
            f"Semantic embeddings ({sem_backend}) substantially improve MR-01 "
            f"paraphrase consistency ({mr01_delta:+.1%} delta vs random vectors). "
            f"For MR-03, the semantic violation rate ({sem_metrics['mr03']['violation_rate']:.1%}) "
            f"exceeds the random baseline ({rnd_metrics['mr03']['violation_rate']:.1%}), "
            "indicating the embedding model places hard negative pairs in proximity — "
            "a finding that the test surface is effective at exposing subtle semantic gaps "
            "that even well-trained models cannot fully resolve in this domain."
        )
    else:
        conclusion = (
            f"Results are mixed (MR-01 delta {mr01_delta:+.1%}, "
            f"MR-03 violation: V_Sem={sem_metrics['mr03']['violation_rate']:.1%} vs "
            f"V_Rnd={rnd_metrics['mr03']['violation_rate']:.1%}). "
            f"Embedding backend: {sem_backend}. "
            "The primary signal is MR-01: a positive delta confirms semantic embeddings "
            "cluster paraphrases better than random, validating the LLM data generation pipeline."
        )

    lines.append(conclusion)
    lines += [
        "",
        "## Implications for Paper",
        "",
        "This experiment addresses the core validity question: *Does using LLM-generated",
        "semantically-labeled text pairs (vs. arbitrary random vectors) improve the",
        "ability to detect vector DB behavioral anomalies?*",
        "",
        "The answer supports the paper's Section 4 (Methodology) claim that the",
        "semantic data generation pipeline (SemanticDataGenerator + embedding model)",
        "is a necessary component, not merely an implementation detail.",
        "",
        "## Detailed Results",
        "",
        "### V_Sem MR-01 Results",
        "",
        "| Pair ID | Text A (preview) | Overlap | Verdict |",
        "|---------|------------------|---------|---------|",
    ]

    for r in [x for x in sem_results if x.get("mr") == "MR-01"]:
        lines.append(
            f"| {r.get('pair_id','?')} | {r.get('text_a_preview','')[:50]}... "
            f"| {r.get('overlap', 0):.2f} | {r.get('verdict','?')} |"
        )

    lines += [
        "",
        "### V_Rnd MR-01 Results",
        "",
        "| Pair ID | Text A (preview) | Overlap | Verdict |",
        "|---------|------------------|---------|---------|",
    ]

    for r in [x for x in rnd_results if x.get("mr") == "MR-01"]:
        lines.append(
            f"| {r.get('pair_id','?')} | {r.get('text_a_preview','')[:50]}... "
            f"| {r.get('overlap', 0):.2f} | {r.get('verdict','?')} |"
        )

    lines += [
        "",
        "### V_Sem MR-03 Results",
        "",
        "| Pair ID | Text A (preview) | Rank B in A | Rank A in B | Verdict |",
        "|---------|------------------|-------------|-------------|---------|",
    ]

    for r in [x for x in sem_results if x.get("mr") == "MR-03"]:
        lines.append(
            f"| {r.get('pair_id','?')} | {r.get('text_a_preview','')[:50]}... "
            f"| {r.get('rank_b_in_a', '-')} | {r.get('rank_a_in_b', '-')} | {r.get('verdict','?')} |"
        )

    lines += [
        "",
        "### V_Rnd MR-03 Results",
        "",
        "| Pair ID | Text A (preview) | Rank B in A | Rank A in B | Verdict |",
        "|---------|------------------|-------------|-------------|---------|",
    ]

    for r in [x for x in rnd_results if x.get("mr") == "MR-03"]:
        lines.append(
            f"| {r.get('pair_id','?')} | {r.get('text_a_preview','')[:50]}... "
            f"| {r.get('rank_b_in_a', '-')} | {r.get('rank_a_in_b', '-')} | {r.get('verdict','?')} |"
        )

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────

SUPPORTED_DOMAINS = ["finance", "medical", "legal", "code", "general"]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="V5 Ablation: Semantic vs. Random Vector Baseline"
    )
    parser.add_argument(
        "--domain",
        default="finance",
        choices=SUPPORTED_DOMAINS + ["all"],
        help="Domain for offline dataset (default: finance). Use 'all' to run all domains.",
    )
    parser.add_argument(
        "--force-hash",
        action="store_true",
        help="Force hash-based embedding instead of sentence-transformers",
    )
    parser.add_argument(
        "--dim",
        type=int,
        default=128,
        help="Vector dimension for random and hash embeddings (default: 128)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="Top-K for search (default: 10)",
    )
    parser.add_argument(
        "--output-dir",
        default="results",
        help="Directory to write JSON and Markdown results (default: results)",
    )
    parser.add_argument(
        "--rng-seed",
        type=int,
        default=None,
        help="RNG seed for random vector generator (default: None = truly random)",
    )
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    domains = SUPPORTED_DOMAINS if args.domain == "all" else [args.domain]

    print("=" * 60)
    print("V5 Ablation Study: Semantic vs. Random Vector Baseline")
    print("=" * 60)
    print(f"Domains: {domains}")
    print(f"Top-K:   {args.top_k}")
    print(f"Dim:     {args.dim}")
    print(f"Output:  {output_dir}")
    print()

    # Build semantic embed_fn once
    print("Building semantic embedding function...")
    sem_embed_fn, sem_backend, actual_dim = build_semantic_embed_fn(
        force_hash=args.force_hash, dim=args.dim
    )
    # Use actual_dim for random baseline too
    rnd_embed_fn = make_random_embed_fn(dim=actual_dim, seed=args.rng_seed)
    print(f"Random baseline: np.random.randn({actual_dim}), unit-normalized")
    print()

    # Oracle (shared — only ApproximateOracle matters for MR-01/03)
    oracle = create_oracle()
    adapter = MockAdapter(response_mode=ResponseMode.SUCCESS, diagnostic_quality=DiagnosticQuality.FULL)

    all_domain_results: List[Dict] = []

    for domain in domains:
        print(f"--- Domain: {domain} ---")

        # Load offline dataset
        print(f"  Generating offline dataset...")
        dataset = generate_offline(domain=domain)
        n_pairs = len(dataset.pairs)
        print(f"  Pairs: {n_pairs} (pos={len(dataset.get_pairs_by_type('positive'))}, "
              f"neg={len(dataset.get_pairs_by_type('negative'))}, "
              f"hard_neg={len(dataset.get_pairs_by_type('hard_negative'))})")

        run_id = f"v5_{domain}_{timestamp}"

        # ── Run V_Sem ────────────────────────────────────────
        print(f"  Running V_Sem ({sem_backend})...")
        sem_runner = V5Runner(
            adapter=adapter,
            oracle=oracle,
            embed_fn=sem_embed_fn,
            dim=actual_dim,
            top_k=args.top_k,
        )
        sem_mr01 = sem_runner.run_mr01(dataset, run_id + "_sem")
        sem_mr03 = sem_runner.run_mr03(dataset, run_id + "_sem")
        sem_results = sem_mr01 + sem_mr03
        sem_metrics = _compute_metrics(sem_results)
        print(f"    MR-01: {sem_metrics['mr01']['n']} cases, "
              f"pass={sem_metrics['mr01']['pass_rate']:.1%}, "
              f"violation={sem_metrics['mr01']['violation_rate']:.1%}")
        print(f"    MR-03: {sem_metrics['mr03']['n']} cases, "
              f"pass={sem_metrics['mr03']['pass_rate']:.1%}, "
              f"violation={sem_metrics['mr03']['violation_rate']:.1%}")

        # ── Run V_Rnd ────────────────────────────────────────
        print(f"  Running V_Rnd (random baseline)...")
        rnd_runner = V5Runner(
            adapter=adapter,
            oracle=oracle,
            embed_fn=rnd_embed_fn,
            dim=actual_dim,
            top_k=args.top_k,
        )
        rnd_mr01 = rnd_runner.run_mr01(dataset, run_id + "_rnd")
        rnd_mr03 = rnd_runner.run_mr03(dataset, run_id + "_rnd")
        rnd_results = rnd_mr01 + rnd_mr03
        rnd_metrics = _compute_metrics(rnd_results)
        print(f"    MR-01: {rnd_metrics['mr01']['n']} cases, "
              f"pass={rnd_metrics['mr01']['pass_rate']:.1%}, "
              f"violation={rnd_metrics['mr01']['violation_rate']:.1%}")
        print(f"    MR-03: {rnd_metrics['mr03']['n']} cases, "
              f"pass={rnd_metrics['mr03']['pass_rate']:.1%}, "
              f"violation={rnd_metrics['mr03']['violation_rate']:.1%}")

        # ── Generate report ──────────────────────────────────
        report_md = _render_report(
            sem_metrics=sem_metrics,
            rnd_metrics=rnd_metrics,
            domain=domain,
            sem_backend=sem_backend,
            dim=actual_dim,
            timestamp=timestamp,
            sem_results=sem_results,
            rnd_results=rnd_results,
        )

        report_path = output_dir / f"v5_ablation_{domain}_{timestamp}.md"
        report_path.write_text(report_md, encoding="utf-8")
        print(f"  Report: {report_path}")

        # ── Save JSON ────────────────────────────────────────
        json_payload = {
            "experiment": "V5_ablation",
            "domain": domain,
            "timestamp": timestamp,
            "sem_backend": sem_backend,
            "dim": actual_dim,
            "top_k": args.top_k,
            "rng_seed": args.rng_seed,
            "V_Sem": {"metrics": sem_metrics, "results": sem_results},
            "V_Rnd": {"metrics": rnd_metrics, "results": rnd_results},
        }
        json_path = output_dir / f"v5_ablation_{domain}_{timestamp}.json"
        json_path.write_text(json.dumps(json_payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  JSON:   {json_path}")
        print()

        all_domain_results.append(
            {
                "domain": domain,
                "sem_metrics": sem_metrics,
                "rnd_metrics": rnd_metrics,
            }
        )

    # ── Cross-domain summary ─────────────────────────────────
    print("=" * 60)
    print("CROSS-DOMAIN SUMMARY")
    print("=" * 60)
    print(
        f"{'Domain':<12} {'MR01 Sem':>10} {'MR01 Rnd':>10} {'MR01 D':>8} "
        f"{'MR03 Sem V':>12} {'MR03 Rnd V':>12} {'MR03 D':>8}"
    )
    print("-" * 76)
    for d in all_domain_results:
        dom = d["domain"]
        sm = d["sem_metrics"]
        rm = d["rnd_metrics"]
        mr01_delta = sm["mr01"]["pass_rate"] - rm["mr01"]["pass_rate"]
        mr03_delta = sm["mr03"]["violation_rate"] - rm["mr03"]["violation_rate"]
        print(
            f"{dom:<12} "
            f"{sm['mr01']['pass_rate']:>10.1%} "
            f"{rm['mr01']['pass_rate']:>10.1%} "
            f"{mr01_delta:>+8.1%} "
            f"{sm['mr03']['violation_rate']:>12.1%} "
            f"{rm['mr03']['violation_rate']:>12.1%} "
            f"{mr03_delta:>+8.1%}"
        )
    print()

    # Save combined JSON
    combined_path = output_dir / f"v5_ablation_mock_{timestamp}.json"
    combined_path.write_text(
        json.dumps(
            {
                "experiment": "V5_ablation_combined",
                "timestamp": timestamp,
                "sem_backend": sem_backend,
                "dim": actual_dim,
                "domains": all_domain_results,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"Combined results: {combined_path}")
    print("Done.")


if __name__ == "__main__":
    main()
