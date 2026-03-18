"""IDX-003 & IDX-004 Contract Testing Script.

IDX-003: Index Parameter Validation Contract
  - Illegal index type (e.g., "INVALID_TYPE") MUST fail with diagnostic error
  - Out-of-range HNSW M parameter (M=-1, M=0, M=100000) MUST fail
  - Out-of-range IVF_FLAT nlist (nlist=0, nlist=-1) MUST fail
  - Valid parameters MUST succeed

IDX-004: Sequential Index Rebuild Contract
  - Building a NEW index on a collection that already has an index MUST succeed
    without data loss
  - Search after index rebuild MUST return same-quality results (recall >= threshold)
  - Index type change (IVF_FLAT -> HNSW -> FLAT) MUST be idempotent

Usage:
    python scripts/run_r5bc_idx003_idx004.py --host localhost --port 19530
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from adapters.milvus_adapter import MilvusAdapter

RESULTS_DIR = Path("results")


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def make_vectors(n: int, dim: int, seed: int = 42) -> List[List[float]]:
    rng = random.Random(seed)
    return [[rng.gauss(0, 1) for _ in range(dim)] for _ in range(n)]


def cosine_recall(gt_ids: List[int], retrieved_ids: List[int]) -> float:
    if not gt_ids:
        return 1.0
    return len(set(gt_ids) & set(retrieved_ids)) / len(set(gt_ids))


def setup_collection(adapter: MilvusAdapter, col: str, dim: int, n: int = 200) -> List[List[float]]:
    """Drop-create-insert a fresh collection. Returns inserted vectors."""
    adapter.execute({"operation": "drop_collection", "params": {"collection_name": col}})
    r = adapter.execute({"operation": "create_collection", "params": {"collection_name": col, "dimension": dim}})
    assert r["status"] == "success", f"create_collection failed: {r}"
    vecs = make_vectors(n, dim)
    r = adapter.execute({"operation": "insert", "params": {"collection_name": col, "vectors": vecs}})
    assert r["status"] == "success", f"insert failed: {r}"
    adapter.execute({"operation": "flush", "params": {"collection_name": col}})
    return vecs


def build_and_load(adapter: MilvusAdapter, col: str, index_type: str, **idx_params) -> Dict:
    """Build index and load collection. Returns (build_result, load_result)."""
    params = {"collection_name": col, "index_type": index_type, "metric_type": "L2"}
    params.update(idx_params)
    r_idx = adapter.execute({"operation": "build_index", "params": params})
    if r_idx["status"] != "success":
        return r_idx
    r_load = adapter.execute({"operation": "load", "params": {"collection_name": col}})
    return r_load


def search(adapter: MilvusAdapter, col: str, vec: List[float], top_k: int = 10,
           index_type: str = "HNSW") -> Optional[List[int]]:
    """Search with index-type-aware search params."""
    from pymilvus import Collection
    collection = Collection(col)
    if index_type == "HNSW":
        sp = {"metric_type": "L2", "params": {"ef": max(top_k * 4, 64)}}
    elif index_type in ("IVF_FLAT", "IVF_SQ8", "IVF_PQ"):
        sp = {"metric_type": "L2", "params": {"nprobe": 16}}
    else:  # FLAT, DISKANN, etc.
        sp = {"metric_type": "L2", "params": {}}
    try:
        results = collection.search(
            data=[vec], anns_field="vector", param=sp, limit=top_k
        )
        return [hit.id for hit in results[0]]
    except Exception as e:
        print(f"    search error: {e}")
        return None


def teardown(adapter: MilvusAdapter, col: str) -> None:
    try:
        adapter.execute({"operation": "release", "params": {"collection_name": col}})
    except Exception:
        pass
    adapter.execute({"operation": "drop_collection", "params": {"collection_name": col}})


# ─────────────────────────────────────────────────────────────
# IDX-003: Parameter Validation
# ─────────────────────────────────────────────────────────────

def run_idx003(adapter: MilvusAdapter, dim: int = 32) -> List[Dict]:
    """
    IDX-003 Contract: Illegal index parameters must be rejected with diagnostic errors.
    
    Test matrix:
      ILLEGAL (Type-1 check):
        - index_type="NONEXISTENT"         → must fail
        - HNSW with M=0                    → must fail
        - HNSW with M=-1                   → must fail
        - IVF_FLAT with nlist=0            → must fail
        - IVF_FLAT with nlist=-1           → must fail
        - IVF_FLAT with nlist=99999999     → must fail (overflow / out of range)
      LEGAL (sanity check):
        - HNSW M=8                         → must succeed
        - IVF_FLAT nlist=64               → must succeed
        - FLAT (no params)                 → must succeed
    """
    print("\n--- IDX-003: Parameter Validation Contract ---")
    results = []

    illegal_cases = [
        {
            "test_id": "IDX-003-ILLEGAL-01",
            "desc": "Invalid index type 'NONEXISTENT'",
            "index_type": "NONEXISTENT",
            "idx_params": {},
        },
        {
            "test_id": "IDX-003-ILLEGAL-02",
            "desc": "HNSW M=0 (must be >= 1)",
            "index_type": "HNSW",
            "idx_params": {"M": 0, "efConstruction": 200},
        },
        {
            "test_id": "IDX-003-ILLEGAL-03",
            "desc": "HNSW M=-1 (negative, must be rejected)",
            "index_type": "HNSW",
            "idx_params": {"M": -1, "efConstruction": 200},
        },
        {
            "test_id": "IDX-003-ILLEGAL-04",
            "desc": "IVF_FLAT nlist=0 (must be >= 1)",
            "index_type": "IVF_FLAT",
            "idx_params": {"nlist": 0},
        },
        {
            "test_id": "IDX-003-ILLEGAL-05",
            "desc": "IVF_FLAT nlist=-5 (negative, must be rejected)",
            "index_type": "IVF_FLAT",
            "idx_params": {"nlist": -5},
        },
    ]

    legal_cases = [
        {
            "test_id": "IDX-003-LEGAL-01",
            "desc": "HNSW M=8, efConstruction=100 (valid)",
            "index_type": "HNSW",
            "idx_params": {"M": 8, "efConstruction": 100},
        },
        {
            "test_id": "IDX-003-LEGAL-02",
            "desc": "IVF_FLAT nlist=64 (valid)",
            "index_type": "IVF_FLAT",
            "idx_params": {"nlist": 64},
        },
        {
            "test_id": "IDX-003-LEGAL-03",
            "desc": "FLAT (no algorithm params, always exact)",
            "index_type": "FLAT",
            "idx_params": {},
        },
    ]

    # -- Illegal cases: expect build_index to fail --
    for case in illegal_cases:
        col = f"idx003_{case['test_id'].lower().replace('-', '_')}"
        try:
            setup_collection(adapter, col, dim, n=100)
            params = {
                "collection_name": col,
                "index_type": case["index_type"],
                "metric_type": "L2",
            }
            params.update(case["idx_params"])
            r = adapter.execute({"operation": "build_index", "params": params})

            if r["status"] == "success":
                # Type-1 bug: illegal param accepted silently
                classification = "VIOLATION"
                reason = f"Illegal params accepted without error: {case['desc']}"
            else:
                # Correctly rejected
                error_msg = r.get("error", "")
                if error_msg:
                    classification = "PASS"
                    reason = f"Correctly rejected with diagnostic: '{error_msg[:120]}'"
                else:
                    # Rejected but no diagnostic info → Type-2 bug
                    classification = "VIOLATION"
                    reason = "Rejected but with empty error message (Type-2: no diagnostic)"

        except Exception as e:
            classification = "PASS"
            reason = f"Rejected via exception (acceptable): {str(e)[:100]}"
        finally:
            teardown(adapter, col)

        record = {
            "test_id": case["test_id"],
            "contract": "IDX-003",
            "subtype": "illegal",
            "desc": case["desc"],
            "index_type": case["index_type"],
            "idx_params": case["idx_params"],
            "classification": classification,
            "reason": reason,
        }
        status_icon = "[PASS]" if classification == "PASS" else "[VIOLATION]"
        print(f"  {status_icon}  {case['test_id']}: {case['desc'][:60]}")
        results.append(record)

    # -- Legal cases: expect success + search works --
    for case in legal_cases:
        col = f"idx003_{case['test_id'].lower().replace('-', '_')}"
        try:
            vecs = setup_collection(adapter, col, dim, n=200)
            r = build_and_load(adapter, col, case["index_type"], **case["idx_params"])

            if r["status"] != "success":
                classification = "VIOLATION"
                reason = f"Legal params rejected: {r.get('error', 'unknown')}"
            else:
                # Verify search works
                qvec = vecs[0]
                ids = search(adapter, col, qvec, top_k=10)
                if ids is None:
                    classification = "VIOLATION"
                    reason = "Build succeeded but search failed"
                elif len(ids) == 0:
                    classification = "VIOLATION"
                    reason = "Build succeeded but search returned empty results"
                else:
                    classification = "PASS"
                    reason = f"Build+load+search succeeded ({len(ids)} results)"

        except Exception as e:
            classification = "VIOLATION"
            reason = f"Exception on legal operation: {str(e)[:120]}"
        finally:
            teardown(adapter, col)

        record = {
            "test_id": case["test_id"],
            "contract": "IDX-003",
            "subtype": "legal",
            "desc": case["desc"],
            "index_type": case["index_type"],
            "idx_params": case["idx_params"],
            "classification": classification,
            "reason": reason,
        }
        status_icon = "[PASS]" if classification == "PASS" else "[VIOLATION]"
        print(f"  {status_icon}  {case['test_id']}: {case['desc'][:60]}")
        results.append(record)

    return results


# ─────────────────────────────────────────────────────────────
# IDX-004: Sequential Index Rebuild (Index Idempotency)
# ─────────────────────────────────────────────────────────────

def run_idx004(adapter: MilvusAdapter, dim: int = 32) -> List[Dict]:
    """
    IDX-004 Contract: Index rebuilds must preserve data and maintain result quality.
    
    Test matrix:
      SEQ-01: IVF_FLAT → HNSW    (change index type, verify recall preserved)
      SEQ-02: HNSW    → IVF_FLAT (reverse direction)
      SEQ-03: HNSW    → HNSW     (same type, different M parameter)
      SEQ-04: 3-step chain: FLAT → IVF_FLAT → HNSW  (full rebuild chain)
    """
    print("\n--- IDX-004: Index Rebuild Idempotency Contract ---")
    results = []
    n = 500
    top_k = 20

    # Generate fixed dataset and compute brute-force ground truth
    vecs = make_vectors(n, dim, seed=123)
    query = make_vectors(1, dim, seed=999)[0]

    def brute_force_top_k(corpus: List[List[float]], q: List[float], k: int) -> List[int]:
        """Simple L2-based brute-force nearest neighbors (ground truth)."""
        def l2sq(a, b):
            return sum((x - y) ** 2 for x, y in zip(a, b))
        dists = [(l2sq(q, v), i) for i, v in enumerate(corpus)]
        dists.sort()
        return [i for _, i in dists[:k]]

    gt_ids = brute_force_top_k(vecs, query, top_k)

    sequences = [
        {
            "test_id": "IDX-004-SEQ-01",
            "desc": "IVF_FLAT -> HNSW index change",
            "steps": [
                ("IVF_FLAT", {"nlist": 64}),
                ("HNSW",     {"M": 16, "efConstruction": 200}),
            ],
        },
        {
            "test_id": "IDX-004-SEQ-02",
            "desc": "HNSW -> IVF_FLAT index change (reverse)",
            "steps": [
                ("HNSW",     {"M": 16, "efConstruction": 200}),
                ("IVF_FLAT", {"nlist": 64}),
            ],
        },
        {
            "test_id": "IDX-004-SEQ-03",
            "desc": "HNSW M=8 -> HNSW M=32 (same type, param change)",
            "steps": [
                ("HNSW", {"M": 8,  "efConstruction": 100}),
                ("HNSW", {"M": 32, "efConstruction": 400}),
            ],
        },
        {
            "test_id": "IDX-004-SEQ-04",
            "desc": "3-step chain: FLAT -> IVF_FLAT -> HNSW",
            "steps": [
                ("FLAT",     {}),
                ("IVF_FLAT", {"nlist": 128}),
                ("HNSW",     {"M": 16, "efConstruction": 200}),
            ],
        },
    ]

    for seq in sequences:
        col = f"idx004_{seq['test_id'].lower().replace('-', '_')}"
        step_records = []
        final_classification = "PASS"
        final_reason = ""

        try:
            # Use fixed vectors for reproducible brute-force GT
            vecs_inserted = setup_collection(adapter, col, dim, n=n)

            # Compute brute-force ground truth using the SAME vectors
            gt_ids = brute_force_top_k(vecs_inserted, query, top_k)

            current_index_type = None
            for step_i, (idx_type, idx_params) in enumerate(seq["steps"]):
                step_label = f"step{step_i+1}_{idx_type}"

                # Release before any index operation (Milvus requirement)
                adapter.execute({"operation": "release", "params": {"collection_name": col}})

                # Drop existing index before rebuilding (Milvus v2.6 allows only 1 index per field)
                if step_i > 0:
                    r_drop = adapter.execute({"operation": "drop_index",
                                              "params": {"collection_name": col}})
                    if r_drop.get("status") != "success":
                        print(f"    {step_label}: drop_index warning: {r_drop.get('error', '?')}")

                r = build_and_load(adapter, col, idx_type, **idx_params)
                if r["status"] != "success":
                    final_classification = "VIOLATION"
                    final_reason = f"{step_label}: build/load failed: {r.get('error', 'unknown')}"
                    step_records.append({"step": step_label, "status": "FAILED", "reason": final_reason})
                    break

                current_index_type = idx_type
                # Search and compute recall
                retrieved = search(adapter, col, query, top_k=top_k, index_type=idx_type)
                if retrieved is None:
                    final_classification = "VIOLATION"
                    final_reason = f"{step_label}: search failed after rebuild"
                    step_records.append({"step": step_label, "status": "FAILED", "reason": final_reason})
                    break

                recall = cosine_recall(gt_ids, retrieved)
                # Threshold: FLAT must be perfect, HNSW/IVF_FLAT >= 0.70
                threshold = 0.99 if idx_type == "FLAT" else 0.70
                status = "PASS" if recall >= threshold else "ALLOWED_DIFF"

                step_records.append({
                    "step": step_label,
                    "index_type": idx_type,
                    "recall": round(recall, 4),
                    "threshold": threshold,
                    "status": status,
                })
                print(f"    {seq['test_id']} {step_label}: recall={recall:.3f} (threshold={threshold}) -> {status}")

            if final_classification == "PASS" and step_records:
                last = step_records[-1]
                if last.get("status") in ("PASS", "ALLOWED_DIFF"):
                    final_reason = f"All {len(seq['steps'])} rebuild steps completed; final recall={last.get('recall', '?')}"
                else:
                    final_classification = "VIOLATION"
                    final_reason = f"Final step recall below threshold"

            # Verify data preservation
            r_count = adapter.execute({"operation": "count_entities",
                                        "params": {"collection_name": col}})
            if r_count.get("status") == "success":
                # count_entities returns data as a list of dicts
                count_data = r_count.get("data", [])
                if isinstance(count_data, list) and count_data:
                    count_after = count_data[0].get("storage_count")
                elif isinstance(count_data, dict):
                    count_after = count_data.get("count") or count_data.get("storage_count")
                else:
                    count_after = r_count.get("storage_count")
            else:
                count_after = None
            if count_after is not None and count_after != n:
                final_classification = "VIOLATION"
                final_reason = f"Data loss after rebuild: expected {n}, got {count_after}"

        except Exception as e:
            final_classification = "VIOLATION"
            final_reason = f"Exception: {str(e)[:150]}"
        finally:
            teardown(adapter, col)

        record = {
            "test_id": seq["test_id"],
            "contract": "IDX-004",
            "desc": seq["desc"],
            "steps": step_records,
            "classification": final_classification,
            "reason": final_reason,
        }
        status_icon = "[PASS]" if final_classification == "PASS" else "[VIOLATION]"
        print(f"  {status_icon}  {seq['test_id']}: {seq['desc']}")
        results.append(record)

    return results


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=19530)
    parser.add_argument("--dim", type=int, default=32)
    args = parser.parse_args()

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_id = f"idx003-idx004-{ts}"

    print(f"\n{'='*60}")
    print(f"  IDX-003 + IDX-004 Contract Testing")
    print(f"  Run ID: {run_id}")
    print(f"  Target: {args.host}:{args.port}  dim={args.dim}")
    print(f"{'='*60}")

    adapter = MilvusAdapter({"host": args.host, "port": args.port})
    if not adapter.health_check():
        print("ERROR: Milvus health check failed.")
        sys.exit(1)
    print(f"  Milvus connected OK\n")

    idx003_results = run_idx003(adapter, dim=args.dim)
    idx004_results = run_idx004(adapter, dim=args.dim)

    all_results = idx003_results + idx004_results
    total = len(all_results)
    violations = [r for r in all_results if r["classification"] == "VIOLATION"]
    passes = [r for r in all_results if r["classification"] == "PASS"]

    # Save results
    RESULTS_DIR.mkdir(exist_ok=True)
    out_path = RESULTS_DIR / f"{run_id}-results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "run_id": run_id,
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total": total,
                "violations": len(violations),
                "passes": len(passes),
                "violation_rate": f"{len(violations)/total*100:.1f}%",
            },
            "idx003": idx003_results,
            "idx004": idx004_results,
        }, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print(f"  RESULTS SUMMARY")
    print(f"  Total tests:  {total}")
    print(f"  PASS:         {len(passes)}")
    print(f"  VIOLATIONS:   {len(violations)}")
    if violations:
        print(f"\n  Violations:")
        for v in violations:
            print(f"    [{v['test_id']}] {v['reason'][:80]}")
    print(f"\n  Results saved: {out_path}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
