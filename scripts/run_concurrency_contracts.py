#!/usr/bin/env python3
"""
Concurrency Contract Tests for ai-db-qc
========================================
Tests three concurrency contracts:

  CONC-001  Write Isolation    -- concurrent writers must not corrupt each other's data
  CONC-002  Batch Atomicity    -- batch inserts are atomic (no partial-visibility)
  CONC-003  Read-After-Write   -- inserted vector is immediately retrievable by ANN search

Usage:
    python scripts/run_concurrency_contracts.py --db milvus
    python scripts/run_concurrency_contracts.py --db qdrant
    python scripts/run_concurrency_contracts.py --db weaviate
    python scripts/run_concurrency_contracts.py --db pgvector
    python scripts/run_concurrency_contracts.py --db all
"""

import argparse
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

# ---------------------------------------------------------------------------
# Path setup so we can import adapters from the project root
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Triage helper
# ---------------------------------------------------------------------------

TRIAGE_LEVELS = ["PASS", "MARGINAL", "AMBIGUOUS", "SUSPICIOUS", "LIKELY_BUG", "BUG"]


def triage(condition: bool, label: str, details: str = "") -> str:
    """Return a triage verdict string."""
    verdict = "PASS" if condition else "LIKELY_BUG"
    icon = "✓" if condition else "✗"
    suffix = f"  [{details}]" if details else ""
    print(f"  {icon} {label}: {verdict}{suffix}")
    return verdict


# ---------------------------------------------------------------------------
# Adapter factory
# ---------------------------------------------------------------------------

def get_adapter(db_name: str) -> Any:
    """Instantiate and return the adapter for *db_name*."""
    db_name = db_name.lower()
    if db_name == "milvus":
        from adapters.milvus_adapter import MilvusAdapter
        return MilvusAdapter()
    elif db_name == "qdrant":
        from adapters.qdrant_adapter import QdrantAdapter
        return QdrantAdapter()
    elif db_name == "weaviate":
        from adapters.weaviate_adapter import WeaviateAdapter
        return WeaviateAdapter()
    elif db_name in ("pgvector", "pg"):
        from adapters.pgvector_adapter import PgvectorAdapter
        return PgvectorAdapter()
    else:
        raise ValueError(f"Unknown database: {db_name!r}. "
                         "Choose from: milvus, qdrant, weaviate, pgvector")


def _is_milvus(adapter: Any) -> bool:
    return type(adapter).__name__ == "MilvusAdapter"


def _flush(adapter: Any, col: str) -> None:
    """Issue a flush if the adapter supports it (required for Milvus)."""
    try:
        adapter.execute({"operation": "flush", "params": {"collection_name": col}})
        time.sleep(1.0)   # give Milvus time to compact
    except Exception:
        pass


def _count(adapter: Any, col: str) -> int:
    """Return the storage entity count for *col*."""
    res = adapter.execute({"operation": "count_entities",
                           "params": {"collection_name": col}})
    # try different result keys used by different adapters
    if res.get("status") == "success":
        for key in ("storage_count", "count", "entity_count"):
            val = res.get(key) or (res.get("data", [{}])[0].get(key) if res.get("data") else None)
            if val is not None:
                return int(val)
    return 0


def _setup_collection(adapter: Any, col: str, dim: int) -> None:
    """Drop-and-recreate collection."""
    adapter.execute({"operation": "drop_collection",
                     "params": {"collection_name": col}})
    adapter.execute({"operation": "create_collection",
                     "params": {"collection_name": col, "dim": dim,
                                "metric_type": "L2", "enable_dynamic_field": True}})


def _random_vectors(n: int, dim: int) -> List[List[float]]:
    """Return *n* random unit vectors of dimension *dim*."""
    vecs = np.random.randn(n, dim).astype(np.float32)
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    vecs = vecs / np.maximum(norms, 1e-9)
    return vecs.tolist()


# ---------------------------------------------------------------------------
# CONC-001: Write Isolation Contract
# ---------------------------------------------------------------------------

def run_conc001_isolation(
    adapter: Any,
    n_vectors: int = 50,
    n_threads: int = 3,
    dim: int = 32,
) -> str:
    """CONC-001 – Concurrent writers must not corrupt each other's data.

    Spawns *n_threads* writer threads, each inserting *n_vectors* distinct vectors.
    After all writers complete (+ optional flush), asserts:
        count_entities == n_threads * n_vectors
    """
    col = "conc001_isolation_test"
    expected = n_threads * n_vectors
    print(f"\n[CONC-001] Write Isolation  ({n_threads} writers × {n_vectors} vectors each)")
    _setup_collection(adapter, col, dim)

    errors: List[str] = []
    lock = threading.Lock()

    def writer_thread(thread_id: int) -> None:
        offset = thread_id * n_vectors
        ids = list(range(offset, offset + n_vectors))
        vecs = _random_vectors(n_vectors, dim)
        scalar = [{"writer_id": thread_id}] * n_vectors
        res = adapter.execute({
            "operation": "insert",
            "params": {
                "collection_name": col,
                "vectors": vecs,
                "ids": ids,
                "scalar_data": scalar,
            }
        })
        if res.get("status") != "success":
            with lock:
                errors.append(f"Thread {thread_id} insert failed: {res.get('error')}")

    threads = [threading.Thread(target=writer_thread, args=(i,)) for i in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    if errors:
        print(f"  ✗ Insert errors: {errors}")
        return "LIKELY_BUG"

    if _is_milvus(adapter):
        print("  (Milvus: flushing before count)")
        _flush(adapter, col)

    actual = _count(adapter, col)
    verdict = triage(
        actual == expected,
        f"count after concurrent insert",
        f"expected={expected}, actual={actual}",
    )
    # Cleanup
    adapter.execute({"operation": "drop_collection", "params": {"collection_name": col}})
    return verdict


# ---------------------------------------------------------------------------
# CONC-002: Batch Atomicity Contract
# ---------------------------------------------------------------------------

def run_conc002_atomicity(
    adapter: Any,
    batch_size: int = 200,
    dim: int = 32,
    n_readers: int = 4,
    read_interval: float = 0.005,
) -> str:
    """CONC-002 – A batch insert is atomic: only 0 or batch_size should be observed.

    Spawns *n_readers* threads that continuously poll count_entities while a
    single writer performs a large batch insert.  Any intermediate count value
    0 < c < batch_size indicates partial visibility → LIKELY_BUG.
    """
    col = "conc002_atomicity_test"
    print(f"\n[CONC-002] Batch Atomicity  (batch_size={batch_size}, readers={n_readers})")
    _setup_collection(adapter, col, dim)

    observed_counts: List[int] = []
    lock = threading.Lock()
    stop_reading = threading.Event()

    def reader_thread() -> None:
        while not stop_reading.is_set():
            c = _count(adapter, col)
            with lock:
                observed_counts.append(c)
            time.sleep(read_interval)

    # Start readers
    readers = [threading.Thread(target=reader_thread, daemon=True) for _ in range(n_readers)]
    for r in readers:
        r.start()

    # Writer inserts one large batch
    vecs = _random_vectors(batch_size, dim)
    ids = list(range(batch_size))
    adapter.execute({
        "operation": "insert",
        "params": {"collection_name": col, "vectors": vecs, "ids": ids},
    })

    # Allow readers to observe the post-insert state
    time.sleep(0.2)
    stop_reading.set()
    for r in readers:
        r.join(timeout=2.0)

    if _is_milvus(adapter):
        _flush(adapter, col)

    # Check for partial visibility
    partial = [c for c in observed_counts if 0 < c < batch_size]
    verdict = triage(
        len(partial) == 0,
        "no partial-batch visibility",
        f"partial counts observed: {sorted(set(partial))[:5]}" if partial else "clean",
    )
    adapter.execute({"operation": "drop_collection", "params": {"collection_name": col}})
    return verdict


# ---------------------------------------------------------------------------
# CONC-003: Read-After-Write Contract
# ---------------------------------------------------------------------------

def run_conc003_read_after_write(
    adapter: Any,
    n_trials: int = 10,
    dim: int = 32,
    dist_epsilon: float = 1e-5,
) -> str:
    """CONC-003 – After inserting a vector (+ flush on Milvus), an ANN search with
    the same query vector must return that vector as the top-1 result with distance ≈ 0.

    Repeats *n_trials* times; any failure is a LIKELY_BUG.
    """
    col = "conc003_raw_test"
    print(f"\n[CONC-003] Read-After-Write  (trials={n_trials})")
    _setup_collection(adapter, col, dim)

    failures = 0
    for trial in range(n_trials):
        vec = _random_vectors(1, dim)[0]
        vec_id = 1000 + trial

        # Insert
        adapter.execute({
            "operation": "insert",
            "params": {
                "collection_name": col,
                "vectors": [vec],
                "ids": [vec_id],
            }
        })

        if _is_milvus(adapter):
            _flush(adapter, col)

        # ANN search with the exact same vector
        res = adapter.execute({
            "operation": "search",
            "params": {
                "collection_name": col,
                "vector": vec,
                "top_k": 1,
                "metric_type": "L2",
            }
        })

        data = res.get("data", [])
        if not data:
            failures += 1
            print(f"  Trial {trial+1}: no results returned")
            continue

        top_hit = data[0]
        returned_id = top_hit.get("id")
        distance = float(top_hit.get("distance", top_hit.get("score", 999)))

        ok = (returned_id == vec_id) and (distance < dist_epsilon)
        if not ok:
            failures += 1
            print(f"  Trial {trial+1}: id={returned_id} (expected {vec_id}), "
                  f"dist={distance:.2e} (expected < {dist_epsilon:.1e})")

    verdict = triage(
        failures == 0,
        f"read-after-write ({n_trials} trials)",
        f"{failures}/{n_trials} failures",
    )
    adapter.execute({"operation": "drop_collection", "params": {"collection_name": col}})
    return verdict


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run concurrency contract tests (CONC-001/002/003) against a vector DB."
    )
    parser.add_argument(
        "--db",
        default="milvus",
        help="Database to test: milvus | qdrant | weaviate | pgvector | all",
    )
    parser.add_argument("--dim", type=int, default=32, help="Vector dimension (default 32)")
    parser.add_argument("--n-vectors", type=int, default=50,
                        help="Vectors per writer thread for CONC-001 (default 50)")
    parser.add_argument("--n-threads", type=int, default=3,
                        help="Writer threads for CONC-001 (default 3)")
    parser.add_argument("--batch-size", type=int, default=200,
                        help="Batch size for CONC-002 (default 200)")
    parser.add_argument("--n-trials", type=int, default=10,
                        help="Trials for CONC-003 (default 10)")
    args = parser.parse_args()

    targets = (
        ["milvus", "qdrant", "weaviate", "pgvector"] if args.db == "all" else [args.db]
    )

    overall: Dict[str, Dict[str, str]] = {}

    for db in targets:
        print(f"\n{'='*60}")
        print(f"  Database: {db.upper()}")
        print(f"{'='*60}")
        try:
            adapter = get_adapter(db)
        except Exception as exc:
            print(f"  ERROR: Could not instantiate adapter for {db}: {exc}")
            overall[db] = {"CONC-001": "ERROR", "CONC-002": "ERROR", "CONC-003": "ERROR"}
            continue

        results: Dict[str, str] = {}
        try:
            results["CONC-001"] = run_conc001_isolation(
                adapter, n_vectors=args.n_vectors, n_threads=args.n_threads, dim=args.dim
            )
        except Exception as exc:
            print(f"  CONC-001 crashed: {exc}")
            results["CONC-001"] = "ERROR"

        try:
            results["CONC-002"] = run_conc002_atomicity(
                adapter, batch_size=args.batch_size, dim=args.dim
            )
        except Exception as exc:
            print(f"  CONC-002 crashed: {exc}")
            results["CONC-002"] = "ERROR"

        try:
            results["CONC-003"] = run_conc003_read_after_write(
                adapter, n_trials=args.n_trials, dim=args.dim
            )
        except Exception as exc:
            print(f"  CONC-003 crashed: {exc}")
            results["CONC-003"] = "ERROR"

        overall[db] = results

    print(f"\n{'='*60}")
    print("  SUMMARY")
    print(f"{'='*60}")
    header = f"{'DB':<12} {'CONC-001':<12} {'CONC-002':<12} {'CONC-003':<12}"
    print(header)
    print("-" * len(header))
    for db, res in overall.items():
        row = (f"{db:<12} "
               f"{res.get('CONC-001','N/A'):<12} "
               f"{res.get('CONC-002','N/A'):<12} "
               f"{res.get('CONC-003','N/A'):<12}")
        print(row)
    print()


if __name__ == "__main__":
    main()
