"""R8: Data Drift / Index Quality Degradation Test.

Tests whether dynamic insertions cause index quality to degrade —
i.e., recall drops as the index drifts from the original distribution.

Protocol:
  Phase-0  Build a clean baseline corpus (N_BASE vectors from dist D0)
  Phase-1  Measure baseline recall@K on Q probe queries
  Phase-2  Insert a drift batch (N_DRIFT vectors from a *different* distribution D1)
  Phase-3  Measure post-drift recall@K on the SAME Q probe queries (no re-index)
  Phase-4  Rebuild index (if applicable) and measure recovery recall@K
  Phase-5  Report: recall curve + violation classification

Violation rule:
  If  recall(Phase-3) < recall(Phase-1) - TOLERANCE  → R8-DEGRADATION
  If  recall(Phase-4) < recall(Phase-1) - TOLERANCE  → R8-NO-RECOVERY  (severe)

The test runs on multiple adapters via --adapter flag (milvus / qdrant / weaviate / mock)
so results can be compared cross-database.

Usage:
    python scripts/run_r8_data_drift.py
    python scripts/run_r8_data_drift.py --adapter milvus --host localhost --port 19530
    python scripts/run_r8_data_drift.py --adapter qdrant --qdrant-url http://localhost:6333
    python scripts/run_r8_data_drift.py --adapter weaviate --weaviate-host localhost
    python scripts/run_r8_data_drift.py --adapter mock  # offline, no Docker needed
    python scripts/run_r8_data_drift.py --adapters milvus qdrant  # multi-adapter compare
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from adapters.mock import MockAdapter, ResponseMode

RESULTS_DIR = Path("results")


# ─────────────────────────────────────────────────────────────
# Vector generators
# ─────────────────────────────────────────────────────────────

def _uniform_vectors(n: int, dim: int, seed: int = 0) -> List[List[float]]:
    """Uniform random vectors in [-1, 1]^dim."""
    rng = random.Random(seed)
    return [[rng.uniform(-1, 1) for _ in range(dim)] for _ in range(n)]


def _gaussian_cluster(n: int, dim: int, center: List[float], std: float = 0.1, seed: int = 0) -> List[List[float]]:
    """Gaussian cluster around a center point."""
    import math
    rng = random.Random(seed)
    result = []
    for _ in range(n):
        vec = []
        for c in center:
            # Box-Muller transform
            u1 = rng.random()
            u2 = rng.random()
            z  = math.sqrt(-2 * math.log(max(u1, 1e-10))) * math.cos(2 * math.pi * u2)
            vec.append(c + std * z)
        result.append(vec)
    return result


def _norm(v: List[float]) -> float:
    return math.sqrt(sum(x * x for x in v))


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    dot   = sum(x * y for x, y in zip(a, b))
    na, nb = _norm(a), _norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _brute_force_topk(query: List[float], corpus: List[List[float]], k: int) -> List[int]:
    """Brute-force exact top-k by cosine similarity (for ground truth)."""
    sims  = [(_cosine_similarity(query, doc), i) for i, doc in enumerate(corpus)]
    sims.sort(key=lambda x: -x[0])
    return [i for _, i in sims[:k]]


def _recall_at_k(ground_truth: List[int], retrieved: List[int]) -> float:
    """Recall@K = |GT ∩ Retrieved| / |GT|."""
    if not ground_truth:
        return 1.0
    return len(set(ground_truth) & set(retrieved)) / len(ground_truth)


# ─────────────────────────────────────────────────────────────
# Adapter factory
# ─────────────────────────────────────────────────────────────

def _build_adapter(adapter_name: str, args) -> Tuple[Any, str, bool]:
    """Build adapter, returning (adapter, actual_name, is_fallback)."""
    if adapter_name == "mock":
        return MockAdapter(response_mode=ResponseMode.SUCCESS), "mock", False

    if adapter_name == "milvus":
        try:
            from adapters.milvus_adapter import MilvusAdapter
            a = MilvusAdapter({"host": args.host, "port": args.port})
            if a.health_check():
                return a, "milvus", False
            raise RuntimeError("health check failed")
        except Exception as e:
            print(f"    Milvus unavailable ({e}), falling back to mock.")
            return MockAdapter(response_mode=ResponseMode.SUCCESS), "mock", True

    if adapter_name == "qdrant":
        try:
            from adapters.qdrant_adapter import QdrantAdapter
            a = QdrantAdapter({"url": args.qdrant_url})
            if a.health_check():
                return a, "qdrant", False
            raise RuntimeError("health check failed")
        except Exception as e:
            print(f"    Qdrant unavailable ({e}), falling back to mock.")
            return MockAdapter(response_mode=ResponseMode.SUCCESS), "mock", True

    if adapter_name == "weaviate":
        try:
            from adapters.weaviate_adapter import WeaviateAdapter
            a = WeaviateAdapter({"host": args.weaviate_host, "port": args.weaviate_port})
            if a.health_check():
                return a, "weaviate", False
            raise RuntimeError("health check failed")
        except Exception as e:
            print(f"    Weaviate unavailable ({e}), falling back to mock.")
            return MockAdapter(response_mode=ResponseMode.SUCCESS), "mock", True

    if adapter_name == "seekdb":
        try:
            from adapters.seekdb_adapter import SeekDBAdapter
            cfg = {
                "host":     getattr(args, "seekdb_host", "localhost"),
                "port":     getattr(args, "seekdb_port", 2881),
                "user":     getattr(args, "seekdb_user", "root"),
                "password": getattr(args, "seekdb_password", ""),
                "database": getattr(args, "seekdb_db", "test"),
            }
            a = SeekDBAdapter(cfg)
            if a.health_check():
                return a, "seekdb", False
            raise RuntimeError("health check failed")
        except Exception as e:
            print(f"    SeekDB unavailable ({e}), falling back to mock.")
            return MockAdapter(response_mode=ResponseMode.SUCCESS), "mock", True

    if adapter_name == "pgvector":
        try:
            from adapters.pgvector_adapter import PgvectorAdapter
            cfg = {
                "container": getattr(args, "pgvector_container", "pgvector"),
                "database": getattr(args, "pgvector_db", "vectordb"),
                "user": "postgres",
                "password": "pgvector",
            }
            a = PgvectorAdapter(cfg)
            if a.health_check():
                return a, "pgvector", False
            raise RuntimeError("health check failed")
        except Exception as e:
            print(f"    Pgvector unavailable ({e}), falling back to mock.")
            return MockAdapter(response_mode=ResponseMode.SUCCESS), "mock", True

    return MockAdapter(response_mode=ResponseMode.SUCCESS), "mock", True


# ─────────────────────────────────────────────────────────────
# Single-adapter drift test
# ─────────────────────────────────────────────────────────────

def run_drift_test_on_adapter(
    adapter,
    adapter_name: str,
    n_base: int,
    n_drift: int,
    n_probes: int,
    dim: int,
    top_k: int,
    recall_tolerance: float,
    run_id: str,
) -> Dict[str, Any]:
    """Run the full R8 drift protocol on a single adapter.

    Returns a result dict with phases, recalls, and violation classification.
    """
    col_name = f"r8_drift_{adapter_name}_{run_id}"
    print(f"  Collection: {col_name}")

    # ── Phase-0: Build baseline corpus ──────────────────────
    print(f"  [Phase-0] Building baseline corpus ({n_base} vectors, dim={dim})...")
    base_vectors = _uniform_vectors(n_base, dim, seed=42)
    # Probe queries: K random queries from a Gaussian around the origin (well-covered region)
    probe_center = [0.0] * dim
    probe_queries = _gaussian_cluster(n_probes, dim, probe_center, std=0.3, seed=99)

    # Ground truth for probes: brute-force over base corpus
    print(f"  [Phase-0] Computing ground truth recall (brute-force top-{top_k})...")
    ground_truths: List[List[int]] = [
        _brute_force_topk(q, base_vectors, top_k) for q in probe_queries
    ]

    # Create collection and insert base corpus
    adapter.execute({"operation": "drop_collection", "params": {"collection_name": col_name}})
    r = adapter.execute({"operation": "create_collection", "params": {
        "collection_name": col_name, "dimension": dim,
    }})
    if r.get("status") != "success":
        return {"error": f"create_collection failed: {r.get('error')}", "adapter": adapter_name}

    # Insert in batches
    BATCH = 200
    for i in range(0, len(base_vectors), BATCH):
        adapter.execute({"operation": "insert", "params": {
            "collection_name": col_name,
            "vectors": base_vectors[i:i + BATCH],
            "ids": list(range(i, min(i + BATCH, n_base))),
        }})

    adapter.execute({"operation": "flush", "params": {"collection_name": col_name}})
    adapter.execute({"operation": "build_index", "params": {
        "collection_name": col_name, "index_type": "IVF_FLAT", "metric_type": "L2",
        "nlist": min(64, max(4, n_base // 10)),
    }})
    adapter.execute({"operation": "load", "params": {"collection_name": col_name}})

    # ── Phase-1: Baseline recall ─────────────────────────────
    print(f"  [Phase-1] Measuring baseline recall@{top_k} on {n_probes} probe queries...")
    phase1_recalls = []
    for qi, (q, gt) in enumerate(zip(probe_queries, ground_truths)):
        r = adapter.execute({"operation": "search", "params": {
            "collection_name": col_name, "vector": q, "top_k": top_k,
        }})
        retrieved = [x.get("id") for x in r.get("data", [])]
        phase1_recalls.append(_recall_at_k(gt, retrieved))
    recall_p1 = sum(phase1_recalls) / len(phase1_recalls) if phase1_recalls else 0.0
    print(f"    Baseline recall@{top_k} = {recall_p1:.3f}")

    # ── Phase-2: Insert drift batch ──────────────────────────
    # Drift vectors come from a very different distribution: Gaussian far from origin
    drift_center = [1.5] * dim
    print(f"  [Phase-2] Inserting drift batch ({n_drift} vectors from off-distribution cluster)...")
    drift_vectors = _gaussian_cluster(n_drift, dim, drift_center, std=0.2, seed=77)
    for i in range(0, len(drift_vectors), BATCH):
        adapter.execute({"operation": "insert", "params": {
            "collection_name": col_name,
            "vectors": drift_vectors[i:i + BATCH],
            "ids": list(range(n_base + i, n_base + min(i + BATCH, n_drift))),
        }})
    adapter.execute({"operation": "flush", "params": {"collection_name": col_name}})
    # Intentionally do NOT rebuild index here — simulating drift without reindex
    print(f"    Drift batch inserted ({n_drift} vectors). Index NOT rebuilt.")

    # ── Phase-3: Post-drift recall ───────────────────────────
    print(f"  [Phase-3] Measuring post-drift recall@{top_k} (no reindex)...")
    time.sleep(0.2)  # allow flush to settle
    phase3_recalls = []
    for q, gt in zip(probe_queries, ground_truths):
        r = adapter.execute({"operation": "search", "params": {
            "collection_name": col_name, "vector": q, "top_k": top_k,
        }})
        retrieved = [x.get("id") for x in r.get("data", [])]
        phase3_recalls.append(_recall_at_k(gt, retrieved))
    recall_p3 = sum(phase3_recalls) / len(phase3_recalls) if phase3_recalls else 0.0
    print(f"    Post-drift recall@{top_k} = {recall_p3:.3f}  (delta={recall_p3 - recall_p1:+.3f})")

    # ── Phase-4: Rebuild index, measure recovery ─────────────
    print(f"  [Phase-4] Rebuilding index and measuring recovery recall@{top_k}...")
    adapter.execute({"operation": "build_index", "params": {
        "collection_name": col_name, "index_type": "IVF_FLAT", "metric_type": "L2",
        "nlist": min(64, max(4, (n_base + n_drift) // 10)),
    }})
    adapter.execute({"operation": "load", "params": {"collection_name": col_name}})
    time.sleep(0.2)
    phase4_recalls = []
    for q, gt in zip(probe_queries, ground_truths):
        r = adapter.execute({"operation": "search", "params": {
            "collection_name": col_name, "vector": q, "top_k": top_k,
        }})
        retrieved = [x.get("id") for x in r.get("data", [])]
        phase4_recalls.append(_recall_at_k(gt, retrieved))
    recall_p4 = sum(phase4_recalls) / len(phase4_recalls) if phase4_recalls else 0.0
    print(f"    Recovery recall@{top_k} = {recall_p4:.3f}  (delta={recall_p4 - recall_p1:+.3f})")

    # ── Cleanup ──────────────────────────────────────────────
    adapter.execute({"operation": "drop_collection", "params": {"collection_name": col_name}})

    # ── Violation classification ─────────────────────────────
    degradation = recall_p1 - recall_p3
    recovery_gap = recall_p1 - recall_p4

    violations = []
    if degradation > recall_tolerance:
        violations.append({
            "type": "R8-DEGRADATION",
            "detail": f"Recall dropped {degradation:.3f} after drift insert (tolerance={recall_tolerance})",
            "severity": "HIGH" if degradation > 2 * recall_tolerance else "MEDIUM",
        })
    if recovery_gap > recall_tolerance:
        violations.append({
            "type": "R8-NO-RECOVERY",
            "detail": f"Recall still {recovery_gap:.3f} below baseline after reindex",
            "severity": "HIGH",
        })

    return {
        "adapter": adapter_name,
        "run_id": run_id,
        "config": {
            "n_base": n_base,
            "n_drift": n_drift,
            "n_probes": n_probes,
            "dim": dim,
            "top_k": top_k,
            "recall_tolerance": recall_tolerance,
        },
        "recalls": {
            "phase1_baseline":  round(recall_p1, 4),
            "phase3_post_drift": round(recall_p3, 4),
            "phase4_recovery":  round(recall_p4, 4),
            "drift_delta":      round(recall_p3 - recall_p1, 4),
            "recovery_delta":   round(recall_p4 - recall_p1, 4),
        },
        "violations": violations,
        "classification": "VIOLATION" if violations else "PASS",
    }


# ─────────────────────────────────────────────────────────────
# Cross-adapter report
# ─────────────────────────────────────────────────────────────

def _generate_r8_report(
    all_results: List[Dict[str, Any]],
    run_timestamp: str,
    output_dir: Path,
) -> Path:
    """Generate Markdown report for R8 data drift results."""
    report_path = output_dir / f"r8_drift_report_{run_timestamp}.md"

    lines = [
        "# R8 Data Drift / Index Quality Degradation Report",
        "",
        f"**Generated**: {datetime.now().isoformat()}",
        f"**Run Timestamp**: {run_timestamp}",
        "",
        "## Protocol",
        "",
        "Each adapter is tested through four phases:",
        "Phase-1 = baseline recall@K on clean corpus;",
        "Phase-2 = insert off-distribution drift batch (no reindex);",
        "Phase-3 = post-drift recall@K (degradation measured here);",
        "Phase-4 = rebuild index and measure recovery recall@K.",
        "",
        "## Cross-Adapter Comparison",
        "",
        "| Adapter | Baseline R@K | Post-Drift R@K | Recovery R@K | Drift Δ | Violations |",
        "|---------|-------------|---------------|-------------|---------|------------|",
    ]

    for res in all_results:
        if "error" in res:
            lines.append(f"| {res.get('adapter','?')} | ERROR | — | — | — | ERROR |")
            continue
        r  = res["recalls"]
        v  = len(res["violations"])
        lines.append(
            f"| {res['adapter']} "
            f"| {r['phase1_baseline']:.3f} "
            f"| {r['phase3_post_drift']:.3f} "
            f"| {r['phase4_recovery']:.3f} "
            f"| {r['drift_delta']:+.3f} "
            f"| {v} violations |"
        )

    lines += ["", "## Detailed Results", ""]

    for res in all_results:
        adapter = res.get("adapter", "?")
        lines.append(f"### {adapter}")
        lines.append("")
        if "error" in res:
            lines.append(f"> ERROR: {res['error']}")
            lines.append("")
            continue
        cfg = res.get("config", {})
        r   = res["recalls"]
        lines += [
            f"**Config**: n_base={cfg.get('n_base')}, n_drift={cfg.get('n_drift')}, "
            f"dim={cfg.get('dim')}, top_k={cfg.get('top_k')}, "
            f"tolerance={cfg.get('recall_tolerance')}",
            "",
            f"| Phase | Recall@{cfg.get('top_k',10)} |",
            "|-------|----------|",
            f"| Phase-1 Baseline   | {r['phase1_baseline']:.4f} |",
            f"| Phase-3 Post-Drift | {r['phase3_post_drift']:.4f} |",
            f"| Phase-4 Recovery   | {r['phase4_recovery']:.4f} |",
            "",
        ]
        if res["violations"]:
            lines.append(f"**Violations** ({len(res['violations'])}):")
            for v in res["violations"]:
                lines.append(f"- `{v['type']}` [{v['severity']}]: {v['detail']}")
            lines.append("")
        else:
            lines.append("**No violations** — index quality maintained through drift.")
            lines.append("")

    lines += [
        "## Interpretation",
        "",
        "A large negative Drift Δ (Phase-3 vs Phase-1) indicates that inserting",
        "off-distribution vectors without reindexing causes measurable recall degradation.",
        "The Recovery phase tests whether rebuilding the index restores recall;",
        "failure to recover (R8-NO-RECOVERY) is the more severe finding.",
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
    parser = argparse.ArgumentParser(description="R8 Data Drift / Index Quality Degradation Test")
    parser.add_argument("--adapters", nargs="+",
                        default=["milvus"],
                        choices=["mock", "milvus", "qdrant", "weaviate", "seekdb", "pgvector"],
                        help="Adapters to test (default: milvus)")
    parser.add_argument("--adapter", default=None,
                        help="Single adapter shorthand (overrides --adapters)")
    # Milvus
    parser.add_argument("--host", default="localhost", help="Milvus host")
    parser.add_argument("--port", type=int, default=19530, help="Milvus port")
    # Qdrant
    parser.add_argument("--qdrant-url", default="http://localhost:6333")
    # Weaviate
    parser.add_argument("--weaviate-host", default="localhost")
    parser.add_argument("--weaviate-port", type=int, default=8080)
    # SeekDB
    parser.add_argument("--seekdb-host", default="localhost")
    parser.add_argument("--seekdb-port", type=int, default=2881)
    parser.add_argument("--seekdb-user", default="root")
    parser.add_argument("--seekdb-password", default="")
    parser.add_argument("--seekdb-db", default="test")
    # Pgvector
    parser.add_argument("--pgvector-container", default="pgvector")
    parser.add_argument("--pgvector-db", default="vectordb")
    # Test config
    parser.add_argument("--n-base",      type=int,   default=500,   help="Baseline corpus size")
    parser.add_argument("--n-drift",     type=int,   default=200,   help="Drift batch size")
    parser.add_argument("--n-probes",    type=int,   default=20,    help="Number of probe queries")
    parser.add_argument("--dim",         type=int,   default=64,    help="Vector dimension")
    parser.add_argument("--top-k",       type=int,   default=10,    help="Top-K for recall")
    parser.add_argument("--tolerance",   type=float, default=0.05,  help="Recall degradation tolerance")
    parser.add_argument("--output-dir",  default="results")

    args  = parser.parse_args()
    adapters_to_test = [args.adapter] if args.adapter else args.adapters

    run_timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_dir    = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    print("=" * 65)
    print("  R8 DATA DRIFT / INDEX QUALITY DEGRADATION TEST")
    print(f"  Adapters  : {', '.join(adapters_to_test)}")
    print(f"  Config    : n_base={args.n_base}, n_drift={args.n_drift}, dim={args.dim}")
    print(f"  Timestamp : {run_timestamp}")
    print("=" * 65)
    print()

    all_results = []

    for adapter_name in adapters_to_test:
        print("-" * 55)
        print(f"  Adapter: {adapter_name.upper()}")
        print("-" * 55)
        adapter, actual_name, fallback = _build_adapter(adapter_name, args)
        if fallback:
            print(f"  WARNING: Using mock (real {adapter_name} unavailable).")

        result = run_drift_test_on_adapter(
            adapter       = adapter,
            adapter_name  = actual_name,
            n_base        = args.n_base,
            n_drift       = args.n_drift,
            n_probes      = args.n_probes,
            dim           = args.dim,
            top_k         = args.top_k,
            recall_tolerance = args.tolerance,
            run_id        = run_timestamp.replace('-', '_'),
        )
        all_results.append(result)

        try:
            adapter.close()
        except Exception:
            pass

        cls = result.get("classification", "UNKNOWN")
        v   = len(result.get("violations", []))
        print(f"\n  Result: {cls} ({v} violations)")
        print()

    # Save raw JSON
    raw_path = output_dir / f"r8_drift_raw_{run_timestamp}.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump({"run_timestamp": run_timestamp, "results": all_results}, f, indent=2)
    print(f"Raw results: {raw_path}")

    # Generate report
    report_path = _generate_r8_report(all_results, run_timestamp, output_dir)
    print(f"Report     : {report_path}")

    # Final summary
    print()
    print("=" * 65)
    print("  R8 SUMMARY")
    print("=" * 65)
    total_violations = sum(len(r.get("violations", [])) for r in all_results)
    for res in all_results:
        r   = res.get("recalls", {})
        cls = res.get("classification", "N/A")
        adp = res.get("adapter", "?")
        print(
            f"  {adp:<12}  {cls:<12}  "
            f"baseline={r.get('phase1_baseline', 0):.3f}  "
            f"post-drift={r.get('phase3_post_drift', 0):.3f}  "
            f"recovery={r.get('phase4_recovery', 0):.3f}"
        )
    print(f"\n  Total violations: {total_violations}")
    print(f"  Report: {report_path}")


if __name__ == "__main__":
    main()
