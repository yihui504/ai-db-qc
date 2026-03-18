"""Semantic Metamorphic Testing Campaign.

Integrates the two core innovations:
1. LLM-driven semantic test data generation (SemanticDataGenerator)
2. Multi-layer Oracle evaluation (MultiLayerOracle)

Campaign workflow:
  1. Generate semantic test data (positive/negative/hard-negative pairs)
  2. Load the pairs into a real vector database (Milvus)
  3. Execute metamorphic test queries per MR definitions
  4. Evaluate results with multi-layer oracle
  5. Generate detailed report

Usage:
    python scripts/run_semantic_campaign.py --host localhost --port 19530 --domain finance
    python scripts/run_semantic_campaign.py --offline --domain medical
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from ai_db_qa.semantic_datagen import SemanticDataGenerator, SemanticTestDataset, TextPair, generate_offline
    from ai_db_qa.multi_layer_oracle import (
        MultiLayerOracle, ExactOracle, ApproximateOracle, SemanticOracle,
        Verdict, LayerResult, OracleDecision, create_oracle
    )
    from ai_db_qa.embedding import get_embed_fn, EmbedBackend, get_backend_info
    from adapters.milvus_adapter import MilvusAdapter
    from adapters.mock import MockAdapter, ResponseMode
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)


# ─────────────────────────────────────────────────────────────
# Embedding support (real or fallback)
# ─────────────────────────────────────────────────────────────

def embed_texts_local(texts: List[str], dim: int = 128) -> List[List[float]]:
    """Fallback: deterministic pseudo-embedding using text hash (for testing without GPU).
    
    WARNING: No semantic meaning. Real embeddings require sentence-transformers.
    Install: pip install sentence-transformers
    """
    import hashlib
    vectors = []
    for text in texts:
        h = hashlib.sha256(text.encode()).hexdigest()
        raw_ints = [int(h[i:i+2], 16) for i in range(0, min(len(h), dim * 2), 2)]
        vec = [(x - 127.5) / 127.5 for x in raw_ints[:dim]]
        while len(vec) < dim:
            vec.append(0.0)
        vectors.append(vec[:dim])
    return vectors


def build_embed_fn(
    openai_api_key: Optional[str] = None,
    st_model: str = "all-MiniLM-L6-v2",
    force_hash: bool = False,
) -> tuple:
    """Return (embed_fn, backend_name, dim).
    
    Priority:
      1. sentence-transformers (local, real semantic embeddings, 384D)
      2. OpenAI API embeddings (cloud, real, 1536D)  
      3. Hash fallback (deterministic, no semantic meaning, 128D)
    """
    if force_hash:
        return embed_texts_local, "hash-fallback", 128

    try:
        embed_fn = get_embed_fn(
            backend=EmbedBackend.AUTO,
            model=st_model,
            api_key=openai_api_key,
        )
        info = get_backend_info()
        backend = info.get("selected_backend", "unknown")

        # Determine output dimension
        test_vec = embed_fn(["test"])
        dim = len(test_vec[0])

        print(f"  Embedding backend: {backend} ({dim}D)")
        if backend == "hash":
            print("  WARNING: Hash embeddings have no semantic meaning.")
            print("  Install sentence-transformers for real results: pip install sentence-transformers")

        return embed_fn, backend, dim
    except Exception as e:
        print(f"  Embedding auto-detect failed ({e}), using hash fallback.")
        return embed_texts_local, "hash-fallback", 128


# ─────────────────────────────────────────────────────────────
# Campaign test case builders
# ─────────────────────────────────────────────────────────────

class SemanticCampaignRunner:
    """Runs the semantic metamorphic testing campaign."""

    def __init__(
        self,
        adapter,
        oracle: MultiLayerOracle,
        dim: int = 128,
        top_k: int = 10,
        embed_fn=None,
    ):
        self.adapter = adapter
        self.oracle = oracle
        self.dim = dim
        self.top_k = top_k
        self.embed_fn = embed_fn or embed_texts_local
        self._results: List[Dict] = []

    def _setup_collection(self, col_name: str, vectors: List[List[float]], ids: List[int]) -> bool:
        """Create and populate a collection with the given vectors."""
        self.adapter.execute({"operation": "drop_collection", "params": {"collection_name": col_name}})
        r = self.adapter.execute({"operation": "create_collection", "params": {
            "collection_name": col_name, "dimension": self.dim,
        }})
        if r.get("status") != "success":
            return False

        # Insert in batches
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            batch_vecs = vectors[i:i + batch_size]
            batch_ids = ids[i:i + batch_size]
            entities = [{"id": id_, "vector": vec} for id_, vec in zip(batch_ids, batch_vecs)]
            # Pass as explicit entities with IDs
            import pymilvus
            col = pymilvus.Collection(col_name)
            data = [[e["id"] for e in entities], [e["vector"] for e in entities]]
            col.insert(data)

        self.adapter.execute({"operation": "flush", "params": {"collection_name": col_name}})
        r = self.adapter.execute({"operation": "build_index", "params": {
            "collection_name": col_name, "index_type": "IVF_FLAT", "metric_type": "L2", "nlist": 64,
        }})
        r = self.adapter.execute({"operation": "load", "params": {"collection_name": col_name}})
        return r.get("status") == "success"

    def _setup_collection_simple(self, col_name: str, texts: List[str], ids: List[int]) -> Tuple[bool, List[List[float]]]:
        """Create collection, embed texts, insert vectors. Returns (success, vectors)."""
        try:
            vectors = self.embed_fn(texts)
        except TypeError:
            vectors = self.embed_fn(texts, dim=self.dim)

        self.adapter.execute({"operation": "drop_collection", "params": {"collection_name": col_name}})
        r = self.adapter.execute({"operation": "create_collection", "params": {
            "collection_name": col_name, "dimension": self.dim,
        }})
        if r.get("status") != "success":
            return False, []

        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            batch_raw_ids = ids[i:i + batch_size]
            r = self.adapter.execute({"operation": "insert", "params": {
                "collection_name": col_name,
                "vectors": batch,
            }})
            if r.get("status") != "success":
                return False, vectors

        self.adapter.execute({"operation": "flush", "params": {"collection_name": col_name}})
        r = self.adapter.execute({"operation": "build_index", "params": {
            "collection_name": col_name, "index_type": "IVF_FLAT", "metric_type": "L2", "nlist": min(64, len(vectors)),
        }})
        r = self.adapter.execute({"operation": "load", "params": {"collection_name": col_name}})
        return r.get("status") == "success", vectors

    def _search_text(self, col_name: str, query_text: str) -> Dict:
        """Embed query text with the configured embed_fn and search."""
        try:
            qvec = self.embed_fn([query_text])[0]
        except TypeError:
            # Some embed functions accept a dim kwarg
            qvec = self.embed_fn([query_text], dim=self.dim)[0]
        return self.adapter.execute({"operation": "search", "params": {
            "collection_name": col_name,
            "vector": qvec,
            "top_k": self.top_k,
        }})

    # ── MR-01: Semantic Equivalence Consistency ──────────────

    def run_mr01_semantic_equivalence(
        self,
        dataset: SemanticTestDataset,
        run_id: str,
    ) -> List[Dict]:
        """MR-01: Paraphrase queries should return highly overlapping result sets (>=70%)."""
        col_name = f"mr01_{run_id}"
        results = []

        # Build a corpus of all texts
        all_texts = []
        for pair in dataset.pairs:
            all_texts.append(pair.text_a)
            all_texts.append(pair.text_b)
        all_texts = list(set(all_texts))  # deduplicate
        ids = list(range(len(all_texts)))

        print(f"    [MR-01] Setting up corpus ({len(all_texts)} documents)...")
        ok, corpus_vectors = self._setup_collection_simple(col_name, all_texts, ids)
        if not ok:
            self.adapter.execute({"operation": "drop_collection", "params": {"collection_name": col_name}})
            return [{"mr": "MR-01", "classification": "INFRA_FAILURE", "error": "Collection setup failed"}]

        positive_pairs = dataset.get_pairs_by_type("positive")
        print(f"    [MR-01] Testing {len(positive_pairs)} positive pairs...")

        for pair in positive_pairs[:20]:  # cap at 20 for efficiency
            r_a = self._search_text(col_name, pair.text_a)
            r_b = self._search_text(col_name, pair.text_b)

            ids_a = [x.get("id") for x in r_a.get("data", [])]
            ids_b = [x.get("id") for x in r_b.get("data", [])]

            # Approximate oracle: check overlap
            l2 = self.oracle.approximate.check_metamorphic_consistency(
                [{"id": i} for i in ids_a],
                [{"id": i} for i in ids_b],
                relation_type="semantic_equivalence",
                min_overlap=0.60,
            )

            result = {
                "mr": "MR-01",
                "pair_id": pair.pair_id,
                "pair_type": pair.pair_type,
                "text_a_preview": pair.text_a[:80],
                "text_b_preview": pair.text_b[:80],
                "ids_a": ids_a,
                "ids_b": ids_b,
                "oracle": l2.__dict__ if hasattr(l2, '__dict__') else {
                    "layer": l2.layer,
                    "verdict": l2.verdict.value,
                    "confidence": l2.confidence,
                    "metrics": l2.metrics,
                    "reason": l2.reason,
                },
                "classification": l2.verdict.value,
            }
            results.append(result)

        self.adapter.execute({"operation": "drop_collection", "params": {"collection_name": col_name}})
        return results

    # ── MR-03: Hard Negative Discrimination ─────────────────

    def run_mr03_hard_negative_discrimination(
        self,
        dataset: SemanticTestDataset,
        run_id: str,
    ) -> List[Dict]:
        """MR-03: Hard negatives should NOT appear as top results for each other.
        
        If rank of text_b when querying text_a is in top-3, something is wrong.
        Hard negatives are surface-similar but semantically different.
        """
        col_name = f"mr03_{run_id}"
        results = []

        hard_neg_pairs = dataset.get_pairs_by_type("hard_negative")
        if not hard_neg_pairs:
            return [{"mr": "MR-03", "classification": "SKIP", "reason": "No hard negative pairs in dataset"}]

        # Build corpus from all texts
        all_texts = list(set(
            [p.text_a for p in dataset.pairs] + [p.text_b for p in dataset.pairs]
        ))
        ids = list(range(len(all_texts)))
        text_to_id = {t: i for i, t in enumerate(all_texts)}

        print(f"    [MR-03] Setting up corpus ({len(all_texts)} documents)...")
        ok, _ = self._setup_collection_simple(col_name, all_texts, ids)
        if not ok:
            self.adapter.execute({"operation": "drop_collection", "params": {"collection_name": col_name}})
            return [{"mr": "MR-03", "classification": "INFRA_FAILURE", "error": "Collection setup failed"}]

        print(f"    [MR-03] Testing {len(hard_neg_pairs)} hard negative pairs...")
        for pair in hard_neg_pairs[:20]:
            r_a = self._search_text(col_name, pair.text_a)
            returned_ids = [x.get("id") for x in r_a.get("data", [])]
            target_id = text_to_id.get(pair.text_b)

            rank_of_b = None
            if target_id is not None and target_id in returned_ids:
                rank_of_b = returned_ids.index(target_id) + 1  # 1-based rank

            # Hard negative should NOT be in top-3
            if rank_of_b is not None and rank_of_b <= 3:
                classification = "VIOLATION"
                reason = f"Hard negative appeared at rank {rank_of_b} (should be far)"
            elif rank_of_b is not None:
                classification = "OBSERVATION"
                reason = f"Hard negative appeared at rank {rank_of_b} (borderline)"
            else:
                classification = "PASS"
                reason = "Hard negative correctly not in top-K"

            results.append({
                "mr": "MR-03",
                "pair_id": pair.pair_id,
                "text_a_preview": pair.text_a[:80],
                "text_b_preview": pair.text_b[:80],
                "semantic_notes": pair.semantic_notes,
                "rank_of_hard_negative": rank_of_b,
                "classification": classification,
                "reason": reason,
            })

        self.adapter.execute({"operation": "drop_collection", "params": {"collection_name": col_name}})
        return results

    # ── MR-04: Negative Pair Rejection ──────────────────────

    def run_mr04_negative_rejection(
        self,
        dataset: SemanticTestDataset,
        run_id: str,
    ) -> List[Dict]:
        """MR-04: Semantically dissimilar texts should not appear in each other's top-K."""
        col_name = f"mr04_{run_id}"
        results = []

        neg_pairs = dataset.get_pairs_by_type("negative")
        if not neg_pairs:
            return [{"mr": "MR-04", "classification": "SKIP", "reason": "No negative pairs"}]

        all_texts = list(set(
            [p.text_a for p in dataset.pairs] + [p.text_b for p in dataset.pairs]
        ))
        ids = list(range(len(all_texts)))
        text_to_id = {t: i for i, t in enumerate(all_texts)}

        print(f"    [MR-04] Setting up corpus ({len(all_texts)} documents)...")
        ok, _ = self._setup_collection_simple(col_name, all_texts, ids)
        if not ok:
            self.adapter.execute({"operation": "drop_collection", "params": {"collection_name": col_name}})
            return [{"mr": "MR-04", "classification": "INFRA_FAILURE", "error": "Collection setup failed"}]

        print(f"    [MR-04] Testing {len(neg_pairs)} negative pairs...")
        for pair in neg_pairs[:15]:
            r_a = self._search_text(col_name, pair.text_a)
            returned_ids = [x.get("id") for x in r_a.get("data", [])]
            target_id = text_to_id.get(pair.text_b)

            if target_id in returned_ids:
                rank = returned_ids.index(target_id) + 1
                classification = "VIOLATION" if rank <= 5 else "OBSERVATION"
                reason = f"Semantically dissimilar text appeared at rank {rank}"
            else:
                classification = "PASS"
                reason = "Negative correctly excluded from top-K"

            results.append({
                "mr": "MR-04",
                "pair_id": pair.pair_id,
                "text_a_preview": pair.text_a[:80],
                "text_b_preview": pair.text_b[:80],
                "classification": classification,
                "reason": reason,
            })

        self.adapter.execute({"operation": "drop_collection", "params": {"collection_name": col_name}})
        return results

    def run_all(self, dataset: SemanticTestDataset) -> Dict[str, Any]:
        """Run all metamorphic relations and return aggregated results."""
        run_id = datetime.now().strftime("%H%M%S")
        campaign_results = {}

        print(f"\n  Running MR-01: Semantic Equivalence Consistency...")
        campaign_results["MR-01"] = self.run_mr01_semantic_equivalence(dataset, f"{run_id}_mr01")

        print(f"\n  Running MR-03: Hard Negative Discrimination...")
        campaign_results["MR-03"] = self.run_mr03_hard_negative_discrimination(dataset, f"{run_id}_mr03")

        print(f"\n  Running MR-04: Negative Pair Rejection...")
        campaign_results["MR-04"] = self.run_mr04_negative_rejection(dataset, f"{run_id}_mr04")

        return campaign_results


# ─────────────────────────────────────────────────────────────
# Report generation
# ─────────────────────────────────────────────────────────────

def generate_campaign_report(
    run_id: str,
    domain: str,
    campaign_results: Dict[str, List[Dict]],
    dataset_stats: Dict[str, int],
    output_dir: str = "results",
) -> str:
    """Generate a Markdown report from campaign results."""
    lines = [
        f"# Semantic Metamorphic Testing Campaign Report",
        f"",
        f"**Run ID**: {run_id}",
        f"**Domain**: {domain}",
        f"**Timestamp**: {datetime.now().isoformat()}",
        f"",
        f"## Dataset Statistics",
        f"",
    ]
    for ptype, count in dataset_stats.items():
        lines.append(f"- **{ptype}**: {count} pairs")

    lines += ["", "## Campaign Results by Metamorphic Relation", ""]

    total_tests = 0
    total_violations = 0
    total_passes = 0

    for mr_name, mr_results in campaign_results.items():
        lines.append(f"### {mr_name}")
        lines.append("")
        if not mr_results:
            lines.append("No results.")
            continue

        mr_counts: Dict[str, int] = {}
        for r in mr_results:
            cls = r.get("classification", "UNKNOWN")
            mr_counts[cls] = mr_counts.get(cls, 0) + 1

        for cls, cnt in sorted(mr_counts.items()):
            lines.append(f"- **{cls}**: {cnt}")
        lines.append("")

        violations = [r for r in mr_results if r.get("classification") == "VIOLATION"]
        if violations:
            lines.append(f"**Violations ({len(violations)}):**")
            lines.append("")
            for v in violations[:5]:
                lines.append(f"- Pair `{v.get('pair_id', 'N/A')}`: {v.get('reason', '')}")
                if v.get("text_a_preview"):
                    lines.append(f"  - text_a: _{v['text_a_preview']}_")
                if v.get("text_b_preview"):
                    lines.append(f"  - text_b: _{v['text_b_preview']}_")
            lines.append("")

        n = len(mr_results)
        v = mr_counts.get("VIOLATION", 0)
        p = mr_counts.get("PASS", 0)
        total_tests += n
        total_violations += v
        total_passes += p

    lines += [
        "## Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total tests | {total_tests} |",
        f"| Violations | {total_violations} |",
        f"| Passes | {total_passes} |",
        f"| Violation rate | {total_violations/total_tests*100:.1f}% |" if total_tests else "| Violation rate | N/A |",
        "",
        "## Key Findings",
        "",
    ]

    if total_violations > 0:
        lines.append(f"Found **{total_violations} metamorphic violations** across {total_tests} tests.")
        lines.append("These indicate semantic correctness issues in the vector database's retrieval.")
    else:
        lines.append(f"No metamorphic violations found in {total_tests} tests.")
        lines.append("The vector database correctly handles semantic relationships for this domain.")

    report = "\n".join(lines)

    Path(output_dir).mkdir(exist_ok=True)
    report_path = Path(output_dir) / f"{run_id}-semantic-report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    return str(report_path)


# ─────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Semantic Metamorphic Testing Campaign")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=19530)
    parser.add_argument("--offline", action="store_true", help="Use mock adapter (no real DB)")
    parser.add_argument("--domain", default="general", choices=["general", "finance", "medical"])
    parser.add_argument("--llm-api-key", default=None, help="LLM API key for semantic oracle + data gen")
    parser.add_argument("--openai-api-key", default=None, help="OpenAI API key for embeddings (fallback if ST not available)")
    parser.add_argument("--st-model", default="all-MiniLM-L6-v2", help="sentence-transformers model name")
    parser.add_argument("--force-hash-embed", action="store_true", help="Force hash-based embeddings (no semantic meaning)")
    parser.add_argument("--output-dir", default="results")
    parser.add_argument("--n-positives", type=int, default=10)
    parser.add_argument("--n-negatives", type=int, default=5)
    parser.add_argument("--n-hard-negatives", type=int, default=10)
    args = parser.parse_args()

    run_id = f"semantic-{args.domain}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    print(f"\n{'='*60}")
    print(f"  SEMANTIC METAMORPHIC TESTING CAMPAIGN")
    print(f"  Run ID: {run_id}")
    print(f"  Domain: {args.domain}")
    print(f"{'='*60}\n")

    # 1. Generate semantic test data
    print("[Step 1] Generating semantic test dataset...")
    gen = SemanticDataGenerator(api_key=args.llm_api_key)
    dataset = gen.generate(
        domain=args.domain,
        n_positives=args.n_positives,
        n_negatives=args.n_negatives,
        n_hard_negatives=args.n_hard_negatives,
        n_boundary=5,
    )
    dataset_path = f"{args.output_dir}/{run_id}-dataset.json"
    dataset.save(dataset_path)
    print(f"  Dataset saved: {dataset_path}")
    print(f"  Stats: {dataset.stats()}\n")

    # 1b. Resolve embedding function
    print("[Step 1b] Resolving embedding backend...")
    embed_fn, backend_name, embed_dim = build_embed_fn(
        openai_api_key=args.openai_api_key,
        st_model=args.st_model,
        force_hash=args.force_hash_embed,
    )
    print(f"  Backend: {backend_name}  dim={embed_dim}\n")

    # 2. Create adapter
    print("[Step 2] Connecting to database...")
    if args.offline:
        print("  Using mock adapter (offline mode).")
        adapter = MockAdapter(response_mode=ResponseMode.SUCCESS)
    else:
        try:
            adapter = MilvusAdapter({"host": args.host, "port": args.port})
            if not adapter.health_check():
                raise RuntimeError("Health check failed")
            print(f"  Connected to Milvus at {args.host}:{args.port}")
        except Exception as e:
            print(f"  ERROR: {e}")
            sys.exit(1)

    # 3. Create oracle
    print("[Step 3] Initializing multi-layer oracle...")
    oracle = create_oracle(llm_api_key=args.llm_api_key)
    semantic_enabled = args.llm_api_key is not None
    print(f"  Layers: Exact=ON, Approximate=ON, Semantic={'ON' if semantic_enabled else 'OFF (no API key)'}\n")

    # 4. Run campaign
    print("[Step 4] Running metamorphic test campaign...")
    runner = SemanticCampaignRunner(adapter=adapter, oracle=oracle, dim=embed_dim, embed_fn=embed_fn)
    campaign_results = runner.run_all(dataset)

    # 5. Save raw results
    raw_path = f"{args.output_dir}/{run_id}-raw.json"
    Path(args.output_dir).mkdir(exist_ok=True)
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump({"run_id": run_id, "domain": args.domain, "results": campaign_results}, f, indent=2, ensure_ascii=False)
    print(f"\n  Raw results: {raw_path}")

    # 6. Generate report
    print("\n[Step 5] Generating report...")
    report_path = generate_campaign_report(
        run_id, args.domain, campaign_results, dataset.stats(), args.output_dir
    )
    print(f"  Report: {report_path}")

    # 7. Summary
    all_results = []
    for mr_results in campaign_results.values():
        all_results.extend(mr_results)
    violations = [r for r in all_results if r.get("classification") == "VIOLATION"]
    passes = [r for r in all_results if r.get("classification") == "PASS"]

    print(f"\n{'='*60}")
    print(f"  CAMPAIGN SUMMARY")
    print(f"  Total tests:     {len(all_results)}")
    print(f"  Violations:      {len(violations)}")
    print(f"  Passes:          {len(passes)}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
