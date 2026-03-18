"""Extended Semantic Domain Coverage Campaign.

Tests MR-01 / MR-03 / MR-04 metamorphic relations across four domains:
  - finance  (existing baseline)
  - medical  (existing baseline)
  - legal    (NEW: contract/liability/verdict discrimination)
  - code     (NEW: API semantics, thread-safety, sync vs async)

For each domain this script:
  1. Generates the semantic test dataset (offline templates, no LLM needed)
  2. Connects to the target vector database
  3. Runs MR-01 (equivalence), MR-03 (hard-negative discrimination), MR-04 (rejection)
  4. Saves raw results + per-domain summary
  5. Produces a cross-domain comparison report

Usage:
    # all four domains, Milvus
    python scripts/run_semantic_extended.py

    # offline mode (mock adapter, no Docker needed)
    python scripts/run_semantic_extended.py --offline

    # specific domains only
    python scripts/run_semantic_extended.py --domains finance medical legal

    # with Qdrant
    python scripts/run_semantic_extended.py --adapter qdrant --qdrant-url http://localhost:6333
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from ai_db_qa.semantic_datagen import SemanticDataGenerator, SemanticTestDataset
    from ai_db_qa.multi_layer_oracle import MultiLayerOracle, create_oracle
    from ai_db_qa.embedding import get_embed_fn, EmbedBackend, get_backend_info
    from adapters.mock import MockAdapter, ResponseMode
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

RESULTS_DIR = Path("results")

ALL_DOMAINS = ["finance", "medical", "legal", "code"]


# ─────────────────────────────────────────────────────────────
# Embedding helpers
# ─────────────────────────────────────────────────────────────

def _embed_texts_hash(texts: List[str], dim: int = 384) -> List[List[float]]:
    """Deterministic hash-based embeddings fallback (no semantic meaning)."""
    import hashlib
    vectors = []
    for text in texts:
        h = hashlib.sha256(text.encode()).hexdigest()
        raw = [int(h[i:i+2], 16) for i in range(0, min(len(h), dim * 2), 2)]
        vec = [(x - 127.5) / 127.5 for x in raw[:dim]]
        while len(vec) < dim:
            vec.append(0.0)
        vectors.append(vec[:dim])
    return vectors


def _build_embed_fn(openai_key: Optional[str] = None, st_model: str = "all-MiniLM-L6-v2", force_hash: bool = False):
    """Return (embed_fn, backend_name, dim)."""
    if force_hash:
        return _embed_texts_hash, "hash-fallback", 384
    try:
        embed_fn = get_embed_fn(backend=EmbedBackend.AUTO, model=st_model, api_key=openai_key)
        info = get_backend_info()
        backend = info.get("selected_backend", "unknown")
        test_vec = embed_fn(["test"])
        dim = len(test_vec[0])
        print(f"  Embedding: {backend} ({dim}D)")
        if backend == "hash":
            print("  WARNING: Hash embeddings carry no semantic meaning.")
        return embed_fn, backend, dim
    except Exception as e:
        print(f"  Embedding auto-detect failed ({e}), using hash fallback.")
        return _embed_texts_hash, "hash-fallback", 384


# ─────────────────────────────────────────────────────────────
# Adapter factory
# ─────────────────────────────────────────────────────────────

def _build_adapter(args):
    """Build the requested adapter, falling back to mock on error."""
    if args.offline or args.adapter == "mock":
        print("  Using MockAdapter (offline mode)")
        return MockAdapter(response_mode=ResponseMode.SUCCESS), "mock", False

    if args.adapter == "milvus":
        try:
            from adapters.milvus_adapter import MilvusAdapter
            adapter = MilvusAdapter({"host": args.host, "port": args.port})
            if adapter.health_check():
                print(f"  Connected to Milvus at {args.host}:{args.port}")
                return adapter, "milvus", False
            raise RuntimeError("health_check failed")
        except Exception as e:
            print(f"  Milvus unavailable ({e}), falling back to mock.")
            return MockAdapter(response_mode=ResponseMode.SUCCESS), "mock", True

    if args.adapter == "qdrant":
        try:
            from adapters.qdrant_adapter import QdrantAdapter
            adapter = QdrantAdapter({"url": args.qdrant_url})
            if adapter.health_check():
                print(f"  Connected to Qdrant at {args.qdrant_url}")
                return adapter, "qdrant", False
            raise RuntimeError("health_check failed")
        except Exception as e:
            print(f"  Qdrant unavailable ({e}), falling back to mock.")
            return MockAdapter(response_mode=ResponseMode.SUCCESS), "mock", True

    if args.adapter == "weaviate":
        try:
            from adapters.weaviate_adapter import WeaviateAdapter
            adapter = WeaviateAdapter({"host": args.weaviate_host, "port": args.weaviate_port})
            if adapter.health_check():
                print(f"  Connected to Weaviate at {args.weaviate_host}:{args.weaviate_port}")
                return adapter, "weaviate", False
            raise RuntimeError("health_check failed")
        except Exception as e:
            print(f"  Weaviate unavailable ({e}), falling back to mock.")
            return MockAdapter(response_mode=ResponseMode.SUCCESS), "mock", True

    if args.adapter == "pgvector":
        try:
            from adapters.pgvector_adapter import PgvectorAdapter
            adapter = PgvectorAdapter({
                "container": args.pgvector_container,
                "database": args.pgvector_db,
                "user": "postgres",
                "password": "pgvector",
            })
            if adapter.health_check():
                print(f"  Connected to Pgvector at {args.pgvector_container}/{args.pgvector_db}")
                return adapter, "pgvector", False
            raise RuntimeError("health_check failed")
        except Exception as e:
            print(f"  Pgvector unavailable ({e}), falling back to mock.")
            return MockAdapter(response_mode=ResponseMode.SUCCESS), "mock", True

    # Fallback
    print(f"  Unknown adapter '{args.adapter}', using mock.")
    return MockAdapter(response_mode=ResponseMode.SUCCESS), "mock", True


# ─────────────────────────────────────────────────────────────
# Core test runners (inline, not calling SemanticCampaignRunner
# to avoid pymilvus dependency in import path)
# ─────────────────────────────────────────────────────────────

class DomainCampaignRunner:
    """Runs MR-01 / MR-03 / MR-04 on a given adapter + dataset."""

    def __init__(self, adapter, oracle: MultiLayerOracle, embed_fn, dim: int, top_k: int = 10):
        self.adapter = adapter
        self.oracle = oracle
        self.embed_fn = embed_fn
        self.dim = dim
        self.top_k = top_k

    def _embed(self, texts: List[str]) -> List[List[float]]:
        try:
            return self.embed_fn(texts)
        except TypeError:
            return self.embed_fn(texts, dim=self.dim)

    def _setup(self, col: str, texts: List[str]) -> bool:
        vecs = self._embed(texts)
        self.adapter.execute({"operation": "drop_collection", "params": {"collection_name": col}})
        r = self.adapter.execute({"operation": "create_collection", "params": {
            "collection_name": col, "dimension": len(vecs[0]) if vecs else self.dim,
        }})
        if r.get("status") != "success":
            return False
        for i in range(0, len(vecs), 100):
            self.adapter.execute({"operation": "insert", "params": {
                "collection_name": col, "vectors": vecs[i:i+100],
            }})
        self.adapter.execute({"operation": "flush", "params": {"collection_name": col}})
        self.adapter.execute({"operation": "build_index", "params": {
            "collection_name": col, "index_type": "IVF_FLAT", "metric_type": "L2",
            "nlist": min(64, max(1, len(vecs))),
        }})
        self.adapter.execute({"operation": "load", "params": {"collection_name": col}})
        return True

    def _search(self, col: str, text: str) -> List[Any]:
        qvec = self._embed([text])[0]
        r = self.adapter.execute({"operation": "search", "params": {
            "collection_name": col, "vector": qvec, "top_k": self.top_k,
        }})
        return r.get("data", [])

    def run(self, dataset: SemanticTestDataset, run_id: str) -> Dict[str, Any]:
        all_texts = list(set(
            [p.text_a for p in dataset.pairs] + [p.text_b for p in dataset.pairs]
        ))
        text_to_idx = {t: i for i, t in enumerate(all_texts)}
        col = f"sem_ext_{run_id}"

        ok = self._setup(col, all_texts)
        if not ok:
            self.adapter.execute({"operation": "drop_collection", "params": {"collection_name": col}})
            return {"error": "collection setup failed"}

        # MR-01: positive pairs → overlap check
        mr01 = []
        for pair in dataset.get_pairs_by_type("positive")[:20]:
            ids_a = [x.get("id") for x in self._search(col, pair.text_a)]
            ids_b = [x.get("id") for x in self._search(col, pair.text_b)]
            if ids_a and ids_b:
                overlap = len(set(ids_a) & set(ids_b)) / max(len(set(ids_a) | set(ids_b)), 1)
            else:
                overlap = 0.0
            cls = "PASS" if overlap >= 0.50 else "VIOLATION"
            mr01.append({"pair_id": pair.pair_id, "overlap": overlap, "classification": cls,
                          "text_a": pair.text_a[:60], "text_b": pair.text_b[:60]})

        # MR-03: hard negatives → should NOT be in top-3
        mr03 = []
        for pair in dataset.get_pairs_by_type("hard_negative")[:20]:
            results = self._search(col, pair.text_a)
            returned_ids = [x.get("id") for x in results]
            target_idx = text_to_idx.get(pair.text_b)
            rank = None
            if target_idx is not None and target_idx in returned_ids:
                rank = returned_ids.index(target_idx) + 1
            if rank and rank <= 3:
                cls = "VIOLATION"
            elif rank:
                cls = "OBSERVATION"
            else:
                cls = "PASS"
            mr03.append({"pair_id": pair.pair_id, "rank": rank, "classification": cls,
                          "notes": pair.semantic_notes[:80],
                          "text_a": pair.text_a[:60], "text_b": pair.text_b[:60]})

        # MR-04: negatives → should NOT appear in top-5
        mr04 = []
        for pair in dataset.get_pairs_by_type("negative")[:15]:
            results = self._search(col, pair.text_a)
            returned_ids = [x.get("id") for x in results]
            target_idx = text_to_idx.get(pair.text_b)
            if target_idx in returned_ids:
                rank = returned_ids.index(target_idx) + 1
                cls = "VIOLATION" if rank <= 5 else "OBSERVATION"
            else:
                cls = "PASS"
                rank = None
            mr04.append({"pair_id": pair.pair_id, "rank": rank, "classification": cls,
                          "text_a": pair.text_a[:60], "text_b": pair.text_b[:60]})

        self.adapter.execute({"operation": "drop_collection", "params": {"collection_name": col}})

        def _summary(records):
            counts: Dict[str, int] = {}
            for rec in records:
                c = rec.get("classification", "UNKNOWN")
                counts[c] = counts.get(c, 0) + 1
            return counts

        return {
            "MR-01": {"records": mr01, "summary": _summary(mr01)},
            "MR-03": {"records": mr03, "summary": _summary(mr03)},
            "MR-04": {"records": mr04, "summary": _summary(mr04)},
        }


# ─────────────────────────────────────────────────────────────
# Cross-domain report
# ─────────────────────────────────────────────────────────────

def _cross_domain_report(
    domain_results: Dict[str, Dict],
    adapter_name: str,
    embed_backend: str,
    run_timestamp: str,
    output_dir: Path,
) -> Path:
    """Generate a cross-domain comparison Markdown report."""
    report_path = output_dir / f"semantic_extended_report_{run_timestamp}.md"

    lines = [
        "# Extended Semantic Domain Coverage Report",
        "",
        f"**Generated**: {datetime.now().isoformat()}",
        f"**Adapter**: {adapter_name}",
        f"**Embedding**: {embed_backend}",
        f"**Domains**: {', '.join(domain_results.keys())}",
        "",
        "## Cross-Domain Summary",
        "",
        "| Domain | MR-01 Violations | MR-03 Violations | MR-04 Violations | Total Tests |",
        "|--------|-----------------|-----------------|-----------------|-------------|",
    ]

    for domain, res in domain_results.items():
        if "error" in res:
            lines.append(f"| {domain} | ERROR | ERROR | ERROR | — |")
            continue
        mr01_v = res.get("MR-01", {}).get("summary", {}).get("VIOLATION", 0)
        mr03_v = res.get("MR-03", {}).get("summary", {}).get("VIOLATION", 0)
        mr04_v = res.get("MR-04", {}).get("summary", {}).get("VIOLATION", 0)
        total = (
            len(res.get("MR-01", {}).get("records", [])) +
            len(res.get("MR-03", {}).get("records", [])) +
            len(res.get("MR-04", {}).get("records", []))
        )
        lines.append(f"| {domain} | {mr01_v} | {mr03_v} | {mr04_v} | {total} |")

    lines += ["", "## Domain Detail", ""]

    for domain, res in domain_results.items():
        lines.append(f"### {domain.capitalize()}")
        lines.append("")
        if "error" in res:
            lines.append(f"> ERROR: {res['error']}")
            lines.append("")
            continue

        for mr_name in ["MR-01", "MR-03", "MR-04"]:
            mr_data = res.get(mr_name, {})
            summary = mr_data.get("summary", {})
            records = mr_data.get("records", [])
            lines.append(f"**{mr_name}**: {dict(summary)} ({len(records)} tests)")
            violations = [r for r in records if r.get("classification") == "VIOLATION"]
            if violations:
                for v in violations[:3]:
                    lines.append(f"  - `{v.get('pair_id')}` | {v.get('text_a','')[:50]} ← → {v.get('text_b','')[:50]}")
                    if mr_name == "MR-03":
                        lines.append(f"    rank={v.get('rank')} notes={v.get('notes','')[:60]}")
            lines.append("")

    lines += [
        "## Key Observations",
        "",
        "The extended domain tests above quantify whether the vector database's semantic",
        "retrieval degrades in specialized legal and code domains compared to the baseline",
        "finance/medical domains. MR-03 hard-negative violations in the `code` domain",
        "are especially significant: opposite-meaning API semantics (sync/async, stable/unstable)",
        "should be clearly separated by any competent embedding model.",
        "",
    ]

    content = "\n".join(lines)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(content)
    return report_path


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Extended semantic domain coverage campaign")
    parser.add_argument("--adapter", default="milvus", choices=["mock", "milvus", "qdrant", "weaviate", "pgvector"])
    parser.add_argument("--host", default="localhost", help="Milvus host")
    parser.add_argument("--port", type=int, default=19530, help="Milvus port")
    parser.add_argument("--qdrant-url", default="http://localhost:6333", help="Qdrant URL")
    parser.add_argument("--weaviate-host", default="localhost", help="Weaviate host")
    parser.add_argument("--weaviate-port", type=int, default=8080, help="Weaviate port")
    parser.add_argument("--pgvector-container", default="pgvector", help="Pgvector container name")
    parser.add_argument("--pgvector-db", default="vectordb", help="Pgvector database name")
    parser.add_argument("--offline", action="store_true", help="Force mock adapter")
    parser.add_argument("--domains", nargs="+", default=ALL_DOMAINS,
                        choices=ALL_DOMAINS, help="Domains to test")
    parser.add_argument("--n-positives", type=int, default=10)
    parser.add_argument("--n-negatives", type=int, default=5)
    parser.add_argument("--n-hard-negatives", type=int, default=10)
    parser.add_argument("--output-dir", default="results")
    parser.add_argument("--force-hash-embed", action="store_true")
    parser.add_argument("--openai-api-key", default=None)
    parser.add_argument("--st-model", default="all-MiniLM-L6-v2")
    args = parser.parse_args()

    run_timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    print("=" * 65)
    print("  EXTENDED SEMANTIC DOMAIN COVERAGE CAMPAIGN")
    print(f"  Domains    : {', '.join(args.domains)}")
    print(f"  Timestamp  : {run_timestamp}")
    print("=" * 65)
    print()

    # Build adapter
    print("[Setup] Building adapter...")
    adapter, adapter_name, fallback = _build_adapter(args)
    if fallback:
        print("  WARNING: Using mock fallback — results won't reflect real DB behavior.")
    print()

    # Build embedding
    print("[Setup] Resolving embedding backend...")
    embed_fn, embed_backend, embed_dim = _build_embed_fn(
        openai_key=args.openai_api_key,
        st_model=args.st_model,
        force_hash=args.force_hash_embed,
    )
    print()

    # Oracle
    oracle = create_oracle(llm_api_key=None)

    # Run per domain
    domain_results: Dict[str, Dict] = {}

    for domain in args.domains:
        print("-" * 55)
        print(f"  Domain: {domain.upper()}")
        print("-" * 55)

        # Generate dataset
        gen = SemanticDataGenerator()
        dataset = gen.generate(
            domain=domain,
            n_positives=args.n_positives,
            n_negatives=args.n_negatives,
            n_hard_negatives=args.n_hard_negatives,
            n_boundary=3,
        )
        ds_path = output_dir / f"sem_ext_{domain}_{run_timestamp}.json"
        dataset.save(str(ds_path))
        print(f"  Dataset: {ds_path.name} stats={dataset.stats()}")

        # Run campaign
        runner = DomainCampaignRunner(
            adapter=adapter,
            oracle=oracle,
            embed_fn=embed_fn,
            dim=embed_dim,
            top_k=10,
        )
        run_id = f"{domain}_{run_timestamp.replace('-', '_')}"
        print(f"  Running MR-01 / MR-03 / MR-04...")
        results = runner.run(dataset, run_id)
        domain_results[domain] = results

        # Print quick summary
        for mr_name in ["MR-01", "MR-03", "MR-04"]:
            s = results.get(mr_name, {}).get("summary", {})
            n = len(results.get(mr_name, {}).get("records", []))
            violations = s.get("VIOLATION", 0)
            print(f"    {mr_name}: {n} tests, {violations} violations — {dict(s)}")
        print()

    # Save raw JSON
    raw_path = output_dir / f"sem_ext_raw_{run_timestamp}.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump({
            "run_timestamp": run_timestamp,
            "adapter": adapter_name,
            "embed_backend": embed_backend,
            "domains": args.domains,
            "results": domain_results,
        }, f, indent=2, ensure_ascii=False)
    print(f"Raw results: {raw_path}")

    # Generate cross-domain report
    report_path = _cross_domain_report(
        domain_results, adapter_name, embed_backend, run_timestamp, output_dir
    )
    print(f"Report     : {report_path}")

    # Close adapter
    try:
        adapter.close()
    except Exception:
        pass

    # Final summary
    print()
    print("=" * 65)
    print("  CAMPAIGN COMPLETE")
    print("=" * 65)
    total_v = sum(
        res.get(mr, {}).get("summary", {}).get("VIOLATION", 0)
        for res in domain_results.values()
        for mr in ["MR-01", "MR-03", "MR-04"]
        if "error" not in res
    )
    print(f"  Total MR violations across all domains: {total_v}")
    print(f"  Report: {report_path}")


if __name__ == "__main__":
    main()
