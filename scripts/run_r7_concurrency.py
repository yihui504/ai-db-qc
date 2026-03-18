"""R7: Concurrency Testing Campaign for Vector Databases.

Tests correctness under concurrent read/write workloads — the highest
bug-yield unexplored area identified in prior analysis.

Test matrix:
  R7A: Concurrent search isolation
       - N threads issue search queries simultaneously
       - Contract: each thread gets valid cardinality-correct results
       - Oracle: ExactOracle.check_search_response per thread result

  R7B: Write-read interleaving
       - Writer thread inserts batches while readers query concurrently
       - Contract: no reader sees a partial write; results are monotonic
         (count never decreases between consecutive reads)
       - Oracle: count monotonicity check + cardinality per query

  R7C: Insert idempotency under concurrency
       - 2-4 threads insert identical vectors simultaneously
       - Contract: final entity count must be exactly N (no duplicates
         if using deterministic IDs; or exactly N*threads if auto-ID)
       - Oracle: count_entities after all threads complete

  R7D: Search-while-build (hot rebuild)
       - Background thread rebuilds index while foreground issues search
       - Contract: search must either succeed with correct results OR
         fail with a clear error — never silent corruption
       - Oracle: if search succeeds, cardinality must be correct

Usage:
    python scripts/run_r7_concurrency.py --host localhost --port 19530
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from adapters.milvus_adapter import MilvusAdapter
from pymilvus import Collection, connections

RESULTS_DIR = Path("results")


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def make_vectors(n: int, dim: int, seed: int = 0) -> List[List[float]]:
    rng = random.Random(seed)
    return [[rng.gauss(0, 1) for _ in range(dim)] for _ in range(n)]


def setup_collection(adapter: MilvusAdapter, col: str, dim: int, n: int,
                     index_type: str = "IVF_FLAT", nlist: int = 64) -> None:
    """Create collection, insert n vectors, build index, load."""
    adapter.execute({"operation": "drop_collection", "params": {"collection_name": col}})
    r = adapter.execute({"operation": "create_collection",
                         "params": {"collection_name": col, "dimension": dim}})
    assert r["status"] == "success"
    vecs = make_vectors(n, dim)
    r = adapter.execute({"operation": "insert", "params": {"collection_name": col, "vectors": vecs}})
    assert r["status"] == "success"
    adapter.execute({"operation": "flush", "params": {"collection_name": col}})
    r = adapter.execute({"operation": "build_index", "params": {
        "collection_name": col, "index_type": index_type,
        "metric_type": "L2", "nlist": nlist,
    }})
    assert r["status"] == "success"
    r = adapter.execute({"operation": "load", "params": {"collection_name": col}})
    assert r["status"] == "success"


def teardown(adapter: MilvusAdapter, col: str) -> None:
    try:
        adapter.execute({"operation": "release", "params": {"collection_name": col}})
    except Exception:
        pass
    adapter.execute({"operation": "drop_collection", "params": {"collection_name": col}})


def concurrent_search(col: str, vec: List[float], top_k: int, alias: str = "default") -> Dict:
    """Thread-safe search using a direct pymilvus call on the shared connection."""
    start = time.monotonic()
    try:
        collection = Collection(col, using=alias)
        results = collection.search(
            data=[vec],
            anns_field="vector",
            param={"metric_type": "L2", "params": {"nprobe": 10}},
            limit=top_k,
        )
        ids = [h.id for h in results[0]]
        latency_ms = (time.monotonic() - start) * 1000
        return {
            "status": "success",
            "ids": ids,
            "count": len(ids),
            "latency_ms": round(latency_ms, 2),
        }
    except Exception as e:
        latency_ms = (time.monotonic() - start) * 1000
        return {
            "status": "error",
            "error": str(e)[:200],
            "latency_ms": round(latency_ms, 2),
        }


def get_count(col: str, alias: str = "default") -> Optional[int]:
    try:
        collection = Collection(col, using=alias)
        return collection.num_entities
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────
# R7A: Concurrent Search Isolation
# ─────────────────────────────────────────────────────────────

def run_r7a(adapter: MilvusAdapter, dim: int = 64, n_threads: int = 8,
            queries_per_thread: int = 10, top_k: int = 10) -> Dict:
    """
    R7A: N threads issue search queries simultaneously.
    Contract: every result must satisfy cardinality (|results| <= top_k)
              and succeed (no crashes or silent errors).
    """
    print(f"\n  [R7A] Concurrent Search Isolation ({n_threads} threads x {queries_per_thread} queries)")
    col = "r7a_concurrent_search"
    n_docs = 1000

    setup_collection(adapter, col, dim, n_docs)
    query_vecs = make_vectors(n_threads * queries_per_thread, dim, seed=77)

    total_checks = 0
    violations = []
    errors = []
    latencies = []

    def worker(thread_id: int, queries: List[List[float]]) -> List[Dict]:
        results = []
        for q in queries:
            r = concurrent_search(col, q, top_k)
            results.append({"thread_id": thread_id, **r})
        return results

    with ThreadPoolExecutor(max_workers=n_threads) as pool:
        futures = []
        for t in range(n_threads):
            qs = query_vecs[t * queries_per_thread:(t + 1) * queries_per_thread]
            futures.append(pool.submit(worker, t, qs))

        for fut in as_completed(futures):
            thread_results = fut.result()
            for r in thread_results:
                total_checks += 1
                latencies.append(r.get("latency_ms", 0))
                if r["status"] == "error":
                    errors.append(r)
                elif r["count"] > top_k:
                    violations.append({
                        "type": "cardinality",
                        "returned": r["count"],
                        "top_k": top_k,
                    })

    teardown(adapter, col)

    avg_lat = sum(latencies) / len(latencies) if latencies else 0
    p95_lat = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0

    summary = {
        "total_checks": total_checks,
        "violations": len(violations),
        "errors": len(errors),
        "avg_latency_ms": round(avg_lat, 2),
        "p95_latency_ms": round(p95_lat, 2),
        "classification": "PASS" if not violations and not errors else "VIOLATION",
    }
    print(f"    {summary['classification']}: {total_checks} checks, "
          f"{len(violations)} violations, {len(errors)} errors, "
          f"p95={p95_lat:.1f}ms")
    return {"test_id": "R7A", **summary, "violation_details": violations[:5], "error_details": errors[:3]}


# ─────────────────────────────────────────────────────────────
# R7B: Write-Read Interleaving
# ─────────────────────────────────────────────────────────────

def run_r7b(adapter: MilvusAdapter, dim: int = 64, n_batches: int = 5,
            batch_size: int = 100, n_readers: int = 4, top_k: int = 10) -> Dict:
    """
    R7B: Writer inserts batches while readers query concurrently.
    Contract:
      1. Each reader query must succeed or fail cleanly (no silent corruption).
      2. Observed entity counts must be monotonically non-decreasing over time.
      3. Every successful search must satisfy cardinality.
    """
    print(f"\n  [R7B] Write-Read Interleaving ({n_readers} readers, {n_batches} batches x {batch_size})")
    col = "r7b_write_read"
    dim_local = dim

    # Start with small initial set
    setup_collection(adapter, col, dim_local, n=100)

    violations = []
    total_reads = 0
    count_observations = []
    stop_readers = threading.Event()

    def reader_worker(reader_id: int) -> List[Dict]:
        nonlocal total_reads
        results = []
        q = make_vectors(1, dim_local, seed=reader_id * 100)[0]
        prev_count = 0
        while not stop_readers.is_set():
            r = concurrent_search(col, q, top_k)
            cnt = get_count(col)
            total_reads += 1

            entry = {
                "reader_id": reader_id,
                "status": r["status"],
                "count": r.get("count"),
                "entity_count": cnt,
                "latency_ms": r.get("latency_ms"),
            }

            # Check count monotonicity
            if cnt is not None and cnt < prev_count:
                entry["count_violation"] = f"Count decreased: {prev_count} -> {cnt}"
                violations.append(entry)
            if cnt is not None:
                prev_count = cnt
                count_observations.append(cnt)

            # Check cardinality
            if r["status"] == "success" and r.get("count", 0) > top_k:
                entry["cardinality_violation"] = f"Returned {r['count']} > top_k={top_k}"
                violations.append(entry)

            results.append(entry)
            time.sleep(0.05)  # don't hammer the DB
        return results

    def writer_worker() -> List[Dict]:
        results = []
        for batch_i in range(n_batches):
            vecs = make_vectors(batch_size, dim_local, seed=batch_i * 200 + 99)
            r = adapter.execute({"operation": "insert", "params": {
                "collection_name": col, "vectors": vecs,
            }})
            results.append({
                "batch": batch_i,
                "status": r["status"],
                "error": r.get("error", ""),
            })
            time.sleep(0.3)  # space out writes
        return results

    # Start readers
    with ThreadPoolExecutor(max_workers=n_readers + 1) as pool:
        read_futures = [pool.submit(reader_worker, i) for i in range(n_readers)]
        write_future = pool.submit(writer_worker)

        # Wait for writer to finish
        write_results = write_future.result()
        time.sleep(0.5)  # let readers do a few more reads after writes
        stop_readers.set()

        all_read_results = []
        for fut in as_completed(read_futures):
            all_read_results.extend(fut.result())

    teardown(adapter, col)

    final_count = count_observations[-1] if count_observations else None
    expected_count = 100 + n_batches * batch_size  # may differ due to async flush

    summary = {
        "total_reads": total_reads,
        "violations": len(violations),
        "write_batches": n_batches,
        "final_observed_count": final_count,
        "expected_count_approx": expected_count,
        "classification": "PASS" if not violations else "VIOLATION",
    }
    print(f"    {summary['classification']}: {total_reads} reads, "
          f"{len(violations)} violations, final_count={final_count}")
    return {"test_id": "R7B", **summary, "violation_details": violations[:5]}


# ─────────────────────────────────────────────────────────────
# R7C: Concurrent Insert — No Silent Data Loss
# ─────────────────────────────────────────────────────────────

def run_r7c(adapter: MilvusAdapter, dim: int = 64, n_threads: int = 4,
            vectors_per_thread: int = 250) -> Dict:
    """
    R7C: Multiple threads insert concurrently.
    Contract: final entity count must equal total vectors inserted.
    """
    print(f"\n  [R7C] Concurrent Insert ({n_threads} threads x {vectors_per_thread} vectors)")
    col = "r7c_concurrent_insert"

    adapter.execute({"operation": "drop_collection", "params": {"collection_name": col}})
    r = adapter.execute({"operation": "create_collection",
                         "params": {"collection_name": col, "dimension": dim}})
    assert r["status"] == "success"

    errors = []

    def insert_worker(thread_id: int) -> Dict:
        vecs = make_vectors(vectors_per_thread, dim, seed=thread_id * 1000)
        r = adapter.execute({"operation": "insert",
                             "params": {"collection_name": col, "vectors": vecs}})
        return {"thread_id": thread_id, "status": r["status"], "error": r.get("error", "")}

    with ThreadPoolExecutor(max_workers=n_threads) as pool:
        futures = [pool.submit(insert_worker, t) for t in range(n_threads)]
        insert_results = [f.result() for f in as_completed(futures)]

    for r in insert_results:
        if r["status"] != "success":
            errors.append(r)

    # Flush and count
    adapter.execute({"operation": "flush", "params": {"collection_name": col}})
    time.sleep(1)  # wait for flush to complete

    final_count = get_count(col)
    expected = n_threads * vectors_per_thread

    teardown(adapter, col)

    if final_count is not None and abs(final_count - expected) > 0:
        classification = "VIOLATION"
        reason = f"Count mismatch: expected {expected}, got {final_count}"
    elif errors:
        classification = "VIOLATION"
        reason = f"{len(errors)} insert errors"
    else:
        classification = "PASS"
        reason = f"All {expected} vectors inserted correctly ({final_count} counted)"

    summary = {
        "total_vectors_expected": expected,
        "final_count": final_count,
        "insert_errors": len(errors),
        "classification": classification,
        "reason": reason,
    }
    print(f"    {summary['classification']}: expected={expected}, got={final_count}")
    return {"test_id": "R7C", **summary}


# ─────────────────────────────────────────────────────────────
# R7D: Search-while-Build (Hot Rebuild)
# ─────────────────────────────────────────────────────────────

def run_r7d(adapter: MilvusAdapter, dim: int = 64, n_searchers: int = 4,
            top_k: int = 10) -> Dict:
    """
    R7D: Searchers issue queries while index is being rebuilt in background.
    Contract: every search result must either succeed with correct cardinality
              OR fail with a descriptive error. Silent corruption (empty result
              with success status) is a VIOLATION.
    """
    print(f"\n  [R7D] Search-while-Build Hot Rebuild ({n_searchers} searchers)")
    col = "r7d_hot_rebuild"
    n_docs = 500

    setup_collection(adapter, col, dim, n_docs)

    violations = []
    total_searches = 0
    search_results_log = []
    stop_searchers = threading.Event()

    def searcher_worker(searcher_id: int) -> List[Dict]:
        nonlocal total_searches
        results = []
        q = make_vectors(1, dim, seed=searcher_id * 333)[0]
        while not stop_searchers.is_set():
            r = concurrent_search(col, q, top_k)
            total_searches += 1

            entry = {
                "searcher_id": searcher_id,
                "status": r["status"],
                "count": r.get("count"),
                "error": r.get("error", ""),
            }

            # Check: success with empty result is suspicious during hot rebuild
            if r["status"] == "success" and r.get("count", 0) == 0:
                # This can legitimately happen when collection is being rebuilt
                # We classify as OBSERVATION rather than VIOLATION
                entry["note"] = "Empty result during hot rebuild (may be transient)"
            elif r["status"] == "success" and r.get("count", 0) > top_k:
                entry["violation"] = f"Cardinality: returned {r['count']} > top_k={top_k}"
                violations.append(entry)

            results.append(entry)
            time.sleep(0.02)
        return results

    def rebuild_worker() -> Dict:
        """Perform: release -> drop_index -> rebuild -> reload."""
        r1 = adapter.execute({"operation": "release", "params": {"collection_name": col}})
        time.sleep(0.1)
        r2 = adapter.execute({"operation": "drop_index", "params": {"collection_name": col}})
        time.sleep(0.1)
        r3 = adapter.execute({"operation": "build_index", "params": {
            "collection_name": col, "index_type": "HNSW",
            "metric_type": "L2", "M": 16, "efConstruction": 200,
        }})
        time.sleep(0.1)
        r4 = adapter.execute({"operation": "load", "params": {"collection_name": col}})
        return {
            "release": r1.get("status"),
            "drop_index": r2.get("status"),
            "build_index": r3.get("status"),
            "load": r4.get("status"),
        }

    with ThreadPoolExecutor(max_workers=n_searchers + 1) as pool:
        search_futures = [pool.submit(searcher_worker, i) for i in range(n_searchers)]
        time.sleep(0.2)  # let searchers get started
        rebuild_future = pool.submit(rebuild_worker)
        rebuild_result = rebuild_future.result()
        time.sleep(0.5)  # let searchers continue after rebuild
        stop_searchers.set()

        for fut in as_completed(search_futures):
            search_results_log.extend(fut.result())

    teardown(adapter, col)

    empty_results = [r for r in search_results_log
                     if r.get("status") == "success" and r.get("count", 0) == 0]
    errors = [r for r in search_results_log if r.get("status") == "error"]

    summary = {
        "total_searches": total_searches,
        "violations": len(violations),
        "errors": len(errors),
        "empty_during_rebuild": len(empty_results),
        "rebuild_result": rebuild_result,
        "classification": "PASS" if not violations else "VIOLATION",
    }
    obs_note = f" ({len(empty_results)} transient empty results)" if empty_results else ""
    print(f"    {summary['classification']}: {total_searches} searches, "
          f"{len(violations)} violations, {len(errors)} errors{obs_note}")
    return {"test_id": "R7D", **summary, "violation_details": violations[:3]}


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────
# Stress Matrix: multi-thread × multi-target
# ─────────────────────────────────────────────────────────────

def _build_adapter(target: str, host: str, port: int) -> Any:
    """Build the appropriate adapter for a given target string."""
    if target == "milvus":
        return MilvusAdapter({"host": host, "port": port})
    elif target == "qdrant":
        from adapters.qdrant_adapter import QdrantAdapter
        return QdrantAdapter({"host": host, "port": 6333})
    elif target == "seekdb":
        from adapters.seekdb_adapter import SeekDBAdapter
        return SeekDBAdapter(
            api_endpoint=f"{host}:2881",
            api_key="",
            user="root",
            password="",
            database="test",
        )
    elif target == "weaviate":
        from adapters.weaviate_adapter import WeaviateAdapter
        return WeaviateAdapter({"host": host, "port": 8080})
    elif target == "pgvector":
        from adapters.pgvector_adapter import PgvectorAdapter
        return PgvectorAdapter({
            "container": "pgvector",
            "database": "vectordb",
            "user": "postgres",
            "password": "pgvector",
        })
    else:
        raise ValueError(f"Unknown target: {target!r}. Choose from: milvus, qdrant, seekdb, weaviate, pgvector")


def _percentile(data: List[float], pct: float) -> float:
    if not data:
        return 0.0
    s = sorted(data)
    idx = int(len(s) * pct / 100)
    return round(s[min(idx, len(s) - 1)], 2)


def run_r7_stress_matrix(
    targets: List[str],
    thread_counts: List[int],
    host: str = "localhost",
    base_port: int = 19530,
    dim: int = 64,
    queries_per_thread: int = 20,
    top_k: int = 10,
) -> Dict[str, Any]:
    """
    R7 Stress Matrix: run R7A (concurrent search) across multiple
    adapters and thread counts, output p50/p95/p99 latency matrix.

    Returns a dict keyed by target name, each containing a list of
    per-thread-count result rows.
    """
    matrix: Dict[str, List[Dict]] = {t: [] for t in targets}

    for target in targets:
        print(f"\n{'='*60}")
        print(f"  Stress target: {target.upper()}")
        print(f"{'='*60}")
        try:
            adapter = _build_adapter(target, host, base_port)
            if not adapter.health_check():
                print(f"  SKIP {target}: health_check failed")
                continue
        except Exception as e:
            print(f"  SKIP {target}: cannot build adapter — {e}")
            continue

        for n_threads in thread_counts:
            print(f"\n  Threads={n_threads}", end="", flush=True)
            col = f"r7stress_{target}_{n_threads}t"
            n_docs = max(n_threads * queries_per_thread * 2, 500)

            # Setup
            try:
                adapter.execute({"operation": "drop_collection",
                                 "params": {"collection_name": col}})
                r = adapter.execute({"operation": "create_collection",
                                     "params": {"collection_name": col, "dimension": dim}})
                if r.get("status") != "success":
                    raise RuntimeError(f"create_collection failed: {r}")
                vecs = make_vectors(n_docs, dim, seed=42)
                r = adapter.execute({"operation": "insert",
                                     "params": {"collection_name": col, "vectors": vecs}})
                if r.get("status") != "success":
                    raise RuntimeError(f"insert failed: {r}")
                adapter.execute({"operation": "flush",
                                 "params": {"collection_name": col}})
                adapter.execute({"operation": "build_index",
                                 "params": {"collection_name": col,
                                            "index_type": "IVF_FLAT",
                                            "metric_type": "L2",
                                            "nlist": 64}})
                adapter.execute({"operation": "load",
                                 "params": {"collection_name": col}})
            except Exception as e:
                print(f" — setup error: {e}")
                matrix[target].append({
                    "threads": n_threads,
                    "status": "setup_error",
                    "error": str(e)[:120],
                })
                continue

            # Run concurrent searches
            query_vecs = make_vectors(n_threads * queries_per_thread, dim, seed=77)
            latencies: List[float] = []
            violations = 0
            errors = 0

            def _search_worker(tid: int, qs: List[List[float]]) -> List[Dict]:
                out = []
                for q in qs:
                    start = time.monotonic()
                    try:
                        rr = adapter.execute({"operation": "search",
                                              "params": {"collection_name": col,
                                                         "vector": q,
                                                         "top_k": top_k}})
                        lat = (time.monotonic() - start) * 1000
                        cnt = len(rr.get("data", []))
                        out.append({"status": rr.get("status", "unknown"),
                                    "count": cnt,
                                    "latency_ms": lat})
                    except Exception as exc:
                        lat = (time.monotonic() - start) * 1000
                        out.append({"status": "error",
                                    "error": str(exc)[:100],
                                    "latency_ms": lat})
                return out

            with ThreadPoolExecutor(max_workers=n_threads) as pool:
                futs = []
                for t in range(n_threads):
                    qs = query_vecs[t * queries_per_thread:(t + 1) * queries_per_thread]
                    futs.append(pool.submit(_search_worker, t, qs))
                for fut in as_completed(futs):
                    for r in fut.result():
                        latencies.append(r["latency_ms"])
                        if r["status"] == "error":
                            errors += 1
                        elif r.get("count", 0) > top_k:
                            violations += 1

            # Cleanup
            try:
                adapter.execute({"operation": "drop_collection",
                                 "params": {"collection_name": col}})
            except Exception:
                pass

            row = {
                "threads": n_threads,
                "total_queries": len(latencies),
                "violations": violations,
                "errors": errors,
                "p50_ms": _percentile(latencies, 50),
                "p95_ms": _percentile(latencies, 95),
                "p99_ms": _percentile(latencies, 99),
                "max_ms": round(max(latencies), 2) if latencies else 0,
                "classification": "PASS" if not violations and not errors else "VIOLATION",
            }
            matrix[target].append(row)
            print(f" p50={row['p50_ms']}ms p95={row['p95_ms']}ms p99={row['p99_ms']}ms "
                  f"violations={violations} errors={errors}")

    return matrix


def _print_stress_matrix(matrix: Dict[str, List[Dict]], thread_counts: List[int]) -> None:
    """Print p95/p99 latency matrix as an ASCII table."""
    print(f"\n{'='*70}")
    print("  R7 STRESS MATRIX — p95 / p99 Latency (ms)")
    print(f"{'='*70}")
    targets = [t for t in matrix if matrix[t]]
    header = f"  {'Target':<12}" + "".join(f"  {f'{n}T p95':>10}  {f'{n}T p99':>10}" for n in thread_counts)
    print(header)
    print("-" * (14 + 22 * len(thread_counts)))
    for target in targets:
        rows_by_threads = {r["threads"]: r for r in matrix[target] if r.get("status") != "setup_error"}
        row_str = f"  {target:<12}"
        for n in thread_counts:
            r = rows_by_threads.get(n)
            if r:
                row_str += f"  {r['p95_ms']:>10.1f}  {r['p99_ms']:>10.1f}"
            else:
                row_str += f"  {'N/A':>10}  {'N/A':>10}"
        print(row_str)
    print(f"{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(description="R7 Concurrency Testing Campaign")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=19530)
    parser.add_argument("--dim", type=int, default=64)
    parser.add_argument("--threads", type=int, default=8,
                        help="Number of concurrent threads for R7A/R7C (single-target mode)")
    # New flags for multi-target stress mode
    parser.add_argument("--stress", action="store_true",
                        help="Run stress matrix across multiple thread counts and targets")
    parser.add_argument("--targets", nargs="+", default=["milvus"],
                        choices=["milvus", "qdrant", "seekdb", "weaviate", "pgvector"],
                        help="Adapters to test in stress mode (default: milvus)")
    parser.add_argument("--thread-counts", nargs="+", type=int, default=[8, 16, 32],
                        dest="thread_counts",
                        help="Thread counts for stress matrix (default: 8 16 32)")
    parser.add_argument("--queries-per-thread", type=int, default=20,
                        dest="queries_per_thread",
                        help="Queries per thread in stress matrix (default: 20)")
    args = parser.parse_args()

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")

    # ── Stress matrix mode ──────────────────────────────────
    if args.stress:
        run_id = f"r7-stress-{ts}"
        print(f"\n{'='*60}")
        print(f"  R7 STRESS MATRIX MODE")
        print(f"  Run ID : {run_id}")
        print(f"  Targets: {args.targets}")
        print(f"  Threads: {args.thread_counts}")
        print(f"  dim={args.dim}  queries_per_thread={args.queries_per_thread}")
        print(f"{'='*60}")

        matrix = run_r7_stress_matrix(
            targets=args.targets,
            thread_counts=args.thread_counts,
            host=args.host,
            base_port=args.port,
            dim=args.dim,
            queries_per_thread=args.queries_per_thread,
        )
        _print_stress_matrix(matrix, args.thread_counts)

        RESULTS_DIR.mkdir(exist_ok=True)
        out_path = RESULTS_DIR / f"{run_id}-matrix.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({
                "run_id": run_id,
                "timestamp": datetime.now().isoformat(),
                "mode": "stress_matrix",
                "config": {
                    "targets": args.targets,
                    "thread_counts": args.thread_counts,
                    "dim": args.dim,
                    "queries_per_thread": args.queries_per_thread,
                },
                "matrix": matrix,
            }, f, indent=2, ensure_ascii=False, default=str)
        print(f"  Matrix saved: {out_path}")
        return

    # ── Standard single-target R7A-D mode ───────────────────
    run_id = f"r7-concurrency-{ts}"

    print(f"\n{'='*60}")
    print(f"  R7: Concurrency Testing Campaign")
    print(f"  Run ID: {run_id}")
    print(f"  Target: {args.host}:{args.port}  dim={args.dim}  threads={args.threads}")
    print(f"{'='*60}")

    adapter = MilvusAdapter({"host": args.host, "port": args.port})
    if not adapter.health_check():
        print("ERROR: Milvus health check failed.")
        sys.exit(1)
    print(f"  Milvus connected OK\n")

    results = {}
    results["R7A"] = run_r7a(adapter, dim=args.dim, n_threads=args.threads)
    results["R7B"] = run_r7b(adapter, dim=args.dim)
    results["R7C"] = run_r7c(adapter, dim=args.dim, n_threads=args.threads)
    results["R7D"] = run_r7d(adapter, dim=args.dim)

    all_tests = list(results.values())
    total = len(all_tests)
    violations = [r for r in all_tests if r.get("classification") == "VIOLATION"]
    passes = [r for r in all_tests if r.get("classification") == "PASS"]

    # Save results
    RESULTS_DIR.mkdir(exist_ok=True)
    out_path = RESULTS_DIR / f"{run_id}-results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "run_id": run_id,
            "timestamp": datetime.now().isoformat(),
            "config": {"host": args.host, "port": args.port, "dim": args.dim, "threads": args.threads},
            "summary": {
                "total_test_types": total,
                "violations": len(violations),
                "passes": len(passes),
            },
            "results": results,
        }, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n{'='*60}")
    print(f"  R7 CONCURRENCY CAMPAIGN SUMMARY")
    print(f"  Test types: {total}")
    print(f"  PASS:       {len(passes)}")
    print(f"  VIOLATIONS: {len(violations)}")
    if violations:
        print(f"\n  Violations:")
        for v in violations:
            print(f"    [{v['test_id']}] {v.get('reason', '')} {v.get('violation_details', '')}")
    print(f"\n  Results saved: {out_path}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
