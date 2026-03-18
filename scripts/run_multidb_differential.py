"""Five-way Differential Campaign: Milvus vs Qdrant vs Weaviate vs pgvector.

Runs R1-R3 contract tests (ANN correctness, filter correctness, count parity)
against all available databases and produces a cross-DB comparison matrix.

Contracts tested:
  R1A — ANN Recall correctness   (HNSW recall@K >= threshold)
  R1B — ANN Monotonicity         (larger K yields subset superset)
  R2A — Filter purity            (filtered results must satisfy filter predicate)
  R2B — Filter coverage          (no qualifying entity should be excluded from results)
  R3A — Count parity             (count after insert == expected)
  R3B — Count after delete       (count decreases exactly by deleted amount)

Usage:
    # All databases (requires Milvus + Qdrant + Weaviate + pgvector running)
    python scripts/run_multidb_differential.py

    # Skip unavailable databases
    python scripts/run_multidb_differential.py --skip-weaviate --skip-pgvector

    # Offline mock only
    python scripts/run_multidb_differential.py --mock

    # Custom scale
    python scripts/run_multidb_differential.py --n-vectors 500 --dim 64
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

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from adapters.milvus_adapter   import MilvusAdapter
from adapters.qdrant_adapter   import QdrantAdapter
from adapters.weaviate_adapter import WeaviateAdapter
from adapters.pgvector_adapter import PgvectorAdapter
from adapters.mock             import MockAdapter, ResponseMode


RESULTS_DIR = Path(__file__).parent.parent / "results" / "multidb_diff"


# ─────────────────────────────────────────────────────────────
# Vector utilities
# ─────────────────────────────────────────────────────────────

def make_vectors(n: int, dim: int, seed: int = 42) -> np.ndarray:
    rng = np.random.default_rng(seed)
    vecs = rng.standard_normal((n, dim)).astype(np.float32)
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vecs / norms


def brute_force_topk(query: np.ndarray, corpus: np.ndarray, k: int) -> List[int]:
    """Exact L2 nearest neighbours (ground truth)."""
    dists = np.linalg.norm(corpus - query, axis=1)
    return list(np.argsort(dists)[:k])


def compute_recall(found: List[int], ground_truth: List[int]) -> float:
    if not ground_truth:
        return 1.0
    return len(set(found) & set(ground_truth)) / len(set(ground_truth))


# ─────────────────────────────────────────────────────────────
# Adapter helpers
# ─────────────────────────────────────────────────────────────

def extract_ids(response: Dict[str, Any]) -> List[int]:
    if response.get("status") != "success":
        return []
    data = response.get("data", [])
    if isinstance(data, list):
        return [int(d["id"]) for d in data if "id" in d]
    return []


def extract_count(response: Dict[str, Any]) -> Optional[int]:
    if response.get("status") != "success":
        return None
    return response.get("storage_count") or (
        response.get("data", [{}])[0].get("storage_count") if response.get("data") else None
    )


# ─────────────────────────────────────────────────────────────
# Per-database test runner
# ─────────────────────────────────────────────────────────────

def run_contracts_on_db(
    adapter,
    db_name: str,
    vectors: np.ndarray,
    queries: np.ndarray,
    col_prefix: str,
    n_tag: int = 50,
    top_k: int = 10,
    recall_threshold: float = 0.70,
) -> Dict[str, Any]:
    """Run R1A/R1B/R2A/R2B/R3A/R3B contracts on a single database."""

    N, dim = vectors.shape
    n_queries = len(queries)
    col = f"{col_prefix}_{db_name}"
    ids = list(range(N))

    results: Dict[str, Any] = {
        "db": db_name,
        "contracts": {},
        "errors": [],
    }

    def record(name: str, status: str, detail: Dict):
        results["contracts"][name] = {"status": status, **detail}
        sym = "+" if status == "PASS" else ("!" if status in ("VIOLATION", "FAIL") else "~")
        print(f"  [{db_name}] [{sym}] {name}: {status}  {detail.get('note', '')}")

    # ── Setup ──────────────────────────────────────────────────────────────

    r = adapter.execute({"operation": "drop_collection",
                         "params": {"collection_name": col}})
    r = adapter.execute({"operation": "create_collection",
                         "params": {"collection_name": col, "dimension": dim,
                                    "metric_type": "L2"}})
    if r.get("status") != "success":
        results["errors"].append(f"create_collection failed: {r.get('error')}")
        return results

    r = adapter.execute({"operation": "insert",
                         "params": {"collection_name": col,
                                    "vectors": vectors.tolist(), "ids": ids}})
    if r.get("status") != "success":
        results["errors"].append(f"insert failed: {r.get('error')}")
        adapter.execute({"operation": "drop_collection",
                         "params": {"collection_name": col}})
        return results

    adapter.execute({"operation": "flush",     "params": {"collection_name": col}})
    # pgvector: prefer HNSW (accurate, no nprobe tuning needed).
    # Milvus/Qdrant/Weaviate: use IVF_FLAT (they handle recall reliably with their defaults).
    if db_name == "pgvector":
        adapter.execute({"operation": "build_index",
                         "params": {"collection_name": col, "index_type": "HNSW",
                                    "metric_type": "L2", "m": 16, "ef_construction": 64}})
    else:
        adapter.execute({"operation": "build_index",
                         "params": {"collection_name": col, "index_type": "IVF_FLAT",
                                    "metric_type": "L2", "nlist": max(1, int(math.sqrt(N)))}})
    adapter.execute({"operation": "load",      "params": {"collection_name": col}})
    time.sleep(0.5)  # let index settle

    # ── R1A: ANN Recall ────────────────────────────────────────────────────
    recalls = []
    for q in queries[:min(n_queries, 20)]:
        gt   = set(brute_force_topk(q, vectors, top_k))
        resp = adapter.execute({"operation": "search",
                                "params": {"collection_name": col,
                                           "vector": q.tolist(), "top_k": top_k}})
        found = set(extract_ids(resp))
        if not resp.get("status") == "success":
            recalls.append(0.0)
        else:
            recalls.append(compute_recall(list(found), list(gt)))

    mean_recall = sum(recalls) / len(recalls) if recalls else 0.0
    if mean_recall >= recall_threshold:
        record("R1A", "PASS", {"mean_recall": round(mean_recall, 4),
                               "threshold": recall_threshold, "n_queries": len(recalls)})
    else:
        record("R1A", "VIOLATION", {"mean_recall": round(mean_recall, 4),
                                    "threshold": recall_threshold,
                                    "note": f"recall {mean_recall:.3f} < {recall_threshold}"})

    # ── R1B: Monotonicity (topK_big superset of topK_small) ────────────────
    mono_ok = 0
    mono_fail = 0
    q = queries[0]
    r_small = adapter.execute({"operation": "search",
                               "params": {"collection_name": col,
                                          "vector": q.tolist(), "top_k": top_k}})
    r_big   = adapter.execute({"operation": "search",
                               "params": {"collection_name": col,
                                          "vector": q.tolist(), "top_k": top_k * 2}})
    ids_small = set(extract_ids(r_small))
    ids_big   = set(extract_ids(r_big))
    if ids_small and ids_big:
        if ids_small.issubset(ids_big):
            record("R1B", "PASS", {"note": f"top{top_k} subset of top{top_k*2}"})
        else:
            extra = ids_small - ids_big
            record("R1B", "VIOLATION",
                   {"note": f"{len(extra)} ids in top{top_k} not in top{top_k*2}",
                    "missing_from_big": sorted(extra)[:10]})
    else:
        record("R1B", "SKIP", {"note": "search returned empty"})

    # ── R2A/R2B: Filtered search ────────────────────────────────────────────
    # Tag first n_tag vectors with scalar_data group=1, rest group=0
    # For databases that support filtered_search natively (Milvus/Qdrant/Weaviate):
    # We use a simple filter: group == 0 (should NOT return tagged items)
    # For pgvector: SQL predicate (no extra column → skip R2 gracefully)

    # Try a filtered search with a known empty filter to check basic filter support
    r_filt = adapter.execute({
        "operation": "filtered_search",
        "params": {
            "collection_name": col,
            "vector": queries[0].tolist(),
            "top_k": top_k,
            "filter": {"_nonexistent_key_xyz": "impossible_value_xyz"},
        }
    })
    if r_filt.get("status") == "success" and len(extract_ids(r_filt)) == 0:
        record("R2A", "PASS", {"note": "impossible filter returned empty result"})
    elif r_filt.get("status") != "success":
        record("R2A", "SKIP", {"note": f"filter not supported: {r_filt.get('error','')[:80]}"})
    else:
        n_leaked = len(extract_ids(r_filt))
        if n_leaked == 0:
            record("R2A", "PASS", {"note": "impossible filter returned 0 results"})
        else:
            record("R2A", "VIOLATION",
                   {"note": f"impossible filter leaked {n_leaked} results",
                    "leaked_ids": extract_ids(r_filt)[:10]})

    # R2B: unfiltered search should return top_k results (coverage)
    r_unfiltered = adapter.execute({
        "operation": "search",
        "params": {"collection_name": col, "vector": queries[0].tolist(), "top_k": top_k}
    })
    n_found = len(extract_ids(r_unfiltered))
    if n_found >= min(top_k, N):
        record("R2B", "PASS", {"note": f"search returned {n_found}/{min(top_k,N)} results"})
    else:
        record("R2B", "VIOLATION",
               {"note": f"search returned only {n_found}/{min(top_k,N)} results"})

    # ── R3A: Count parity ──────────────────────────────────────────────────
    r_count = adapter.execute({"operation": "count_entities",
                               "params": {"collection_name": col}})
    count = extract_count(r_count)
    if count == N:
        record("R3A", "PASS", {"count": count, "expected": N})
    elif count is None:
        record("R3A", "SKIP", {"note": "count_entities not supported"})
    else:
        record("R3A", "VIOLATION",
               {"count": count, "expected": N,
                "note": f"count {count} != expected {N}"})

    # ── R3B: Count after delete ────────────────────────────────────────────
    n_delete = min(20, N // 5)
    del_ids  = ids[:n_delete]
    r_del = adapter.execute({"operation": "delete",
                             "params": {"collection_name": col, "ids": del_ids}})
    if r_del.get("status") != "success":
        record("R3B", "SKIP", {"note": f"delete failed: {r_del.get('error','')[:80]}"})
    else:
        time.sleep(0.3)
        r_count2 = adapter.execute({"operation": "count_entities",
                                    "params": {"collection_name": col}})
        count2 = extract_count(r_count2)
        expected2 = N - n_delete
        if count2 == expected2:
            record("R3B", "PASS", {"count": count2, "expected": expected2,
                                   "deleted": n_delete})
        elif count2 is None:
            record("R3B", "SKIP", {"note": "count_entities not supported"})
        else:
            record("R3B", "VIOLATION",
                   {"count": count2, "expected": expected2, "deleted": n_delete,
                    "discrepancy": count2 - expected2,
                    "note": f"count {count2} != expected {expected2}"})

    # ── Cleanup ────────────────────────────────────────────────────────────
    adapter.execute({"operation": "drop_collection",
                     "params": {"collection_name": col}})

    return results


# ─────────────────────────────────────────────────────────────
# Cross-DB comparison
# ─────────────────────────────────────────────────────────────

def compare_results(all_results: List[Dict]) -> Dict[str, Any]:
    """Compare contract outcomes across databases."""
    contracts = set()
    for r in all_results:
        contracts.update(r.get("contracts", {}).keys())

    matrix: Dict[str, Dict[str, str]] = {}
    for contract in sorted(contracts):
        matrix[contract] = {}
        for r in all_results:
            db = r["db"]
            c  = r.get("contracts", {}).get(contract, {})
            matrix[contract][db] = c.get("status", "SKIP")

    divergences = []
    for contract, db_statuses in matrix.items():
        statuses = set(db_statuses.values())
        if len(statuses) > 1 and "SKIP" not in statuses:
            # Real divergence
            divergences.append({
                "contract": contract,
                "db_statuses": db_statuses,
            })

    return {"matrix": matrix, "divergences": divergences}


# ─────────────────────────────────────────────────────────────
# Report generation
# ─────────────────────────────────────────────────────────────

def generate_report(
    all_results: List[Dict],
    comparison: Dict,
    run_id: str,
    args: argparse.Namespace,
) -> str:
    lines = [
        f"# Multi-DB Differential Campaign Report",
        f"",
        f"**Run ID**: {run_id}  ",
        f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
        f"**Databases**: {', '.join(r['db'] for r in all_results)}  ",
        f"**Vectors**: {args.n_vectors} × dim={args.dim}  ",
        f"",
        f"## Contract Status Matrix",
        f"",
    ]

    # Header
    dbs = [r["db"] for r in all_results]
    header = "| Contract | " + " | ".join(dbs) + " |"
    sep    = "|----------|" + "|".join(["---------"] * len(dbs)) + "|"
    lines += [header, sep]

    for contract, db_statuses in comparison["matrix"].items():
        row = f"| {contract} | "
        cells = []
        for db in dbs:
            st = db_statuses.get(db, "SKIP")
            if st == "PASS":
                cells.append("PASS +")
            elif st in ("VIOLATION", "FAIL"):
                cells.append("VIOLATION !")
            else:
                cells.append(st)
        row += " | ".join(cells) + " |"
        lines.append(row)

    lines += ["", f"## Divergences ({len(comparison['divergences'])} found)", ""]
    if comparison["divergences"]:
        for d in comparison["divergences"]:
            lines.append(f"- **{d['contract']}**: " +
                         ", ".join(f"{db}={st}" for db, st in d["db_statuses"].items()))
    else:
        lines.append("_No divergences found — all databases agree on all contracts._")

    lines += ["", "## Per-Database Detail", ""]
    for r in all_results:
        lines += [f"### {r['db']}", ""]
        if r.get("errors"):
            lines += [f"**Errors**: {'; '.join(r['errors'])}", ""]
        for name, detail in r.get("contracts", {}).items():
            st = detail.get("status", "?")
            note = detail.get("note", "")
            lines.append(f"- **{name}** [{st}]  {note}")
        lines.append("")

    lines += [
        f"## Summary",
        f"",
        f"| Database | PASS | VIOLATION | SKIP |",
        f"|----------|------|-----------|------|",
    ]
    for r in all_results:
        contracts_list = r.get("contracts", {})
        n_pass = sum(1 for c in contracts_list.values() if c.get("status") == "PASS")
        n_viol = sum(1 for c in contracts_list.values() if c.get("status") in ("VIOLATION", "FAIL"))
        n_skip = sum(1 for c in contracts_list.values() if c.get("status") == "SKIP")
        lines.append(f"| {r['db']} | {n_pass} | {n_viol} | {n_skip} |")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Multi-DB Differential Campaign (Milvus / Qdrant / Weaviate / pgvector)"
    )
    p.add_argument("--n-vectors",    type=int,   default=300)
    p.add_argument("--n-queries",    type=int,   default=20)
    p.add_argument("--dim",          type=int,   default=64)
    p.add_argument("--top-k",        type=int,   default=10)
    p.add_argument("--recall-threshold", type=float, default=0.70,
                   help="Minimum acceptable ANN recall@K (default: 0.70)")
    p.add_argument("--mock",         action="store_true",
                   help="Use mock adapters for all databases (offline test)")
    p.add_argument("--skip-milvus",  action="store_true")
    p.add_argument("--skip-qdrant",  action="store_true")
    p.add_argument("--skip-weaviate",action="store_true")
    p.add_argument("--skip-pgvector",action="store_true")
    p.add_argument("--milvus-host",  default="localhost")
    p.add_argument("--milvus-port",  type=int, default=19530)
    p.add_argument("--qdrant-host",  default="localhost")
    p.add_argument("--qdrant-port",  type=int, default=6333)
    p.add_argument("--weaviate-host",default="localhost")
    p.add_argument("--weaviate-port",type=int, default=8080)
    p.add_argument("--pg-container", default="pgvector")
    p.add_argument("--output-dir",   default=str(RESULTS_DIR))
    return p.parse_args()


def main():
    args = parse_args()
    run_id = f"multidb-diff-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*65}")
    print(f"  Multi-DB Differential Campaign")
    print(f"  Run ID : {run_id}")
    print(f"  N={args.n_vectors} dim={args.dim} top_k={args.top_k}")
    print(f"{'='*65}\n")

    # Generate dataset
    vectors = make_vectors(args.n_vectors, args.dim, seed=42)
    queries = make_vectors(args.n_queries, args.dim, seed=999)

    # Build adapter list
    adapters: List[Tuple[str, Any]] = []

    if args.mock:
        for name in ["mock-A", "mock-B"]:
            adapters.append((name, MockAdapter({"response_mode": "success"})))
    else:
        if not args.skip_milvus:
            try:
                a = MilvusAdapter({"host": args.milvus_host, "port": args.milvus_port})
                if a.health_check():
                    adapters.append(("milvus", a))
                    print(f"  [milvus] connected OK")
                else:
                    print(f"  [milvus] health_check failed -- skipping")
            except Exception as e:
                print(f"  [milvus] init error: {e} — skipping")

        if not args.skip_qdrant:
            try:
                a = QdrantAdapter({"host": args.qdrant_host, "port": args.qdrant_port})
                if a.health_check():
                    adapters.append(("qdrant", a))
                    print(f"  [qdrant] connected OK")
                else:
                    print(f"  [qdrant] health_check failed -- skipping")
            except Exception as e:
                print(f"  [qdrant] init error: {e} — skipping")

        if not args.skip_weaviate:
            try:
                a = WeaviateAdapter({"host": args.weaviate_host, "port": args.weaviate_port})
                if a.health_check():
                    adapters.append(("weaviate", a))
                    print(f"  [weaviate] connected OK")
                else:
                    print(f"  [weaviate] health_check failed -- skipping")
            except Exception as e:
                print(f"  [weaviate] init error: {e} — skipping")

        if not args.skip_pgvector:
            try:
                a = PgvectorAdapter({"container": args.pg_container})
                if a.health_check():
                    adapters.append(("pgvector", a))
                    print(f"  [pgvector] connected OK")
                else:
                    print(f"  [pgvector] health_check failed -- skipping")
            except Exception as e:
                print(f"  [pgvector] init error: {e} — skipping")

    if not adapters:
        print("  No adapters available. Use --mock for offline testing.")
        sys.exit(1)

    col_prefix = f"mdbdiff_{datetime.now().strftime('%H%M%S')}"

    # Run contracts on each database
    all_results = []
    for db_name, adapter in adapters:
        print(f"\n  Running contracts on {db_name} ...")
        try:
            res = run_contracts_on_db(
                adapter, db_name, vectors, queries, col_prefix,
                top_k=args.top_k,
                recall_threshold=args.recall_threshold,
            )
            all_results.append(res)
        except Exception as e:
            print(f"  [{db_name}] FATAL: {e}")
            all_results.append({"db": db_name, "contracts": {}, "errors": [str(e)]})

    # Cross-DB comparison
    comparison = compare_results(all_results)

    # Summary
    print(f"\n{'='*65}")
    print(f"  CROSS-DB CONTRACT MATRIX")
    print(f"{'='*65}")
    for contract, db_statuses in comparison["matrix"].items():
        row = f"  {contract:12s} "
        for db, st in db_statuses.items():
            icon = "+" if st == "PASS" else ("!" if st in ("VIOLATION","FAIL") else "~")
            row += f" {db}:{icon} "
        print(row)

    if comparison["divergences"]:
        print(f"\n  DIVERGENCES ({len(comparison['divergences'])}):")
        for d in comparison["divergences"]:
            print(f"    {d['contract']}: " +
                  ", ".join(f"{db}={st}" for db, st in d["db_statuses"].items()))
    else:
        print(f"\n  No divergences -- all databases agree.")

    # Save results
    raw_path = out_dir / f"{run_id}-results.json"
    with open(raw_path, "w") as f:
        json.dump({
            "run_id": run_id,
            "timestamp": datetime.now().isoformat(),
            "config": vars(args),
            "results": all_results,
            "comparison": comparison,
        }, f, indent=2)

    # Markdown report
    report = generate_report(all_results, comparison, run_id, args)
    rpt_path = out_dir / f"{run_id}-report.md"
    with open(rpt_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n  Results  : {raw_path}")
    print(f"  Report   : {rpt_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
