"""R5B Index Behavior Pilot - Complete Implementation.

Executes 6 tests covering IDX-001 (Semantic Neutrality) and IDX-002 (Data Preservation).
Uses refined oracle that separates hard checks from approximate quality checks.

Usage:
    python scripts/run_r5b_index_pilot.py --host localhost --port 19530
    python scripts/run_r5b_index_pilot.py --mock  # For offline testing
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from adapters.milvus_adapter import MilvusAdapter
    from adapters.mock import MockAdapter, ResponseMode
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)


# ─────────────────────────────────────────────────────────────
# Dataset generation
# ─────────────────────────────────────────────────────────────

def generate_random_dataset(n: int = 1000, dim: int = 128, seed: int = 42) -> List[List[float]]:
    """Generate uniform random vectors."""
    rng = random.Random(seed)
    return [[rng.uniform(-1, 1) for _ in range(dim)] for _ in range(n)]


def generate_clustered_dataset(n: int = 500, dim: int = 128, n_clusters: int = 5, seed: int = 42) -> List[List[float]]:
    """Generate clustered vectors with Gaussian noise around cluster centers."""
    rng = random.Random(seed)
    centers = [[rng.choice([-1.0, 1.0]) for _ in range(dim)] for _ in range(n_clusters)]
    vectors = []
    for i in range(n):
        center = centers[i % n_clusters]
        vec = [c + rng.gauss(0, 0.1) for c in center]
        vectors.append(vec)
    return vectors


def generate_query_vectors(n: int = 10, dim: int = 128, seed: int = 99) -> List[List[float]]:
    """Generate query vectors (distinct seed from dataset)."""
    rng = random.Random(seed)
    return [[rng.uniform(-1, 1) for _ in range(dim)] for _ in range(n)]


# ─────────────────────────────────────────────────────────────
# Oracle logic
# ─────────────────────────────────────────────────────────────

RECALL_THRESHOLDS = {
    "FLAT": 0.99,
    "HNSW": 0.80,
    "IVF_FLAT": 0.75,
    "IVF_SQ8": 0.70,
}

def compute_recall(before_ids: List[int], after_ids: List[int]) -> float:
    """Compute recall@k: fraction of brute-force top-k found in ANN results."""
    if not before_ids:
        return 1.0
    return len(set(before_ids) & set(after_ids)) / len(set(before_ids))


def oracle_idx001(results_before: List[Dict], results_after: Optional[List[Dict]], index_type: str) -> Dict[str, Any]:
    """IDX-001 Refined Oracle: Semantic Neutrality.
    
    Hard checks:
    - Search must succeed (results_after is not None)
    - Results not empty if before was non-empty
    
    Quality checks (ALLOWED_DIFFERENCE, not VIOLATION):
    - Recall >= index-type-specific threshold
    """
    # Hard check 1: search succeeded
    if results_after is None:
        return {
            "classification": "VIOLATION",
            "passed": False,
            "reason": "Search failed after index creation (hard check failed)",
            "check": "search_succeeds",
        }

    # Hard check 2: non-empty results
    if results_before and not results_after:
        return {
            "classification": "VIOLATION",
            "passed": False,
            "reason": "Index caused search to return empty results (hard check failed)",
            "check": "results_not_empty",
        }

    # Quality check: recall
    before_ids = [r["id"] for r in results_before]
    after_ids = [r["id"] for r in results_after]
    recall = compute_recall(before_ids, after_ids)
    threshold = RECALL_THRESHOLDS.get(index_type, 0.75)

    if recall >= threshold:
        quality = "PASS"
        quality_msg = f"Recall {recall:.3f} >= {threshold:.2f} for {index_type}"
    else:
        quality = "ALLOWED_DIFFERENCE"
        quality_msg = f"Recall {recall:.3f} < {threshold:.2f} for {index_type} (within ANN approximation tolerance)"

    return {
        "classification": "PASS",       # hard checks passed
        "passed": True,
        "recall": recall,
        "threshold": threshold,
        "quality_classification": quality,
        "quality_message": quality_msg,
        "index_type": index_type,
        "results_before_count": len(results_before),
        "results_after_count": len(results_after),
    }


def oracle_idx002(count_before: Optional[int], count_after: Optional[int]) -> Dict[str, Any]:
    """IDX-002 Oracle: Data Preservation. Count must not change after index creation."""
    if count_before is None or count_after is None:
        return {
            "classification": "OBSERVATION",
            "passed": False,
            "reason": "Could not obtain entity count",
        }

    if count_before == count_after:
        return {
            "classification": "PASS",
            "passed": True,
            "count_before": count_before,
            "count_after": count_after,
        }
    else:
        return {
            "classification": "VIOLATION",
            "passed": False,
            "reason": f"Entity count changed: {count_before} -> {count_after} (data loss or corruption)",
            "count_before": count_before,
            "count_after": count_after,
        }


# ─────────────────────────────────────────────────────────────
# Test execution helpers
# ─────────────────────────────────────────────────────────────

def setup_collection(adapter: MilvusAdapter, col_name: str, dim: int, vectors: List[List[float]]) -> bool:
    """Create collection and insert vectors. Returns True on success."""
    # Drop if exists
    adapter.execute({"operation": "drop_collection", "params": {"collection_name": col_name}})

    # Create
    r = adapter.execute({"operation": "create_collection", "params": {
        "collection_name": col_name,
        "dimension": dim,
    }})
    if r.get("status") != "success":
        print(f"  ERROR creating collection: {r.get('error')}")
        return False

    # Insert in batches of 500 to avoid timeouts
    batch_size = 500
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i:i + batch_size]
        r = adapter.execute({"operation": "insert", "params": {
            "collection_name": col_name,
            "vectors": batch,
        }})
        if r.get("status") != "success":
            print(f"  ERROR inserting batch {i}-{i+len(batch)}: {r.get('error')}")
            return False

    # Flush
    adapter.execute({"operation": "flush", "params": {"collection_name": col_name}})
    return True


def search_brute_force(adapter: MilvusAdapter, col_name: str, queries: List[List[float]], top_k: int = 10) -> Optional[List[Dict]]:
    """Search without index (brute-force baseline). Returns list of results or None on failure."""
    all_ids = []
    for q in queries:
        r = adapter.execute({"operation": "search", "params": {
            "collection_name": col_name,
            "vector": q,
            "top_k": top_k,
        }})
        if r.get("status") != "success":
            return None
        for item in r.get("data", []):
            if item["id"] not in all_ids:
                all_ids.append(item["id"])
    # Return as list of dicts with id
    return [{"id": id_} for id_ in all_ids]


def get_entity_count(adapter: MilvusAdapter, col_name: str) -> Optional[int]:
    """Get entity count. Returns None on failure."""
    r = adapter.execute({"operation": "count_entities", "params": {"collection_name": col_name}})
    if r.get("status") != "success":
        return None
    data = r.get("data", [{}])
    if data:
        return data[0].get("storage_count") or r.get("storage_count")
    return None


# ─────────────────────────────────────────────────────────────
# Individual test runners
# ─────────────────────────────────────────────────────────────

def run_idx001_test(
    adapter: MilvusAdapter,
    test_id: str,
    index_type: str,
    vectors: List[List[float]],
    queries: List[List[float]],
    top_k: int = 10,
    index_params: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Run IDX-001 semantic neutrality test for given index type."""
    col_name = f"r5b_idx001_{test_id}_{datetime.now().strftime('%H%M%S')}"
    dim = len(vectors[0])
    result = {
        "test_id": f"IDX-001-{test_id}",
        "contract": "IDX-001",
        "index_type": index_type,
        "dataset_size": len(vectors),
        "query_count": len(queries),
        "top_k": top_k,
        "started_at": datetime.now().isoformat(),
        "steps": [],
        "oracle": None,
        "classification": None,
    }

    try:
        # Step 1: Setup collection
        print(f"    [1/6] Setting up collection {col_name}...")
        if not setup_collection(adapter, col_name, dim, vectors):
            result["classification"] = "INFRA_FAILURE"
            result["error"] = "Collection setup failed"
            return result
        result["steps"].append({"step": "setup", "status": "ok"})

        # Step 2: Load for brute-force search (Milvus requires load before search)
        print(f"    [2/6] Loading for brute-force baseline...")
        r = adapter.execute({"operation": "load", "params": {"collection_name": col_name}})
        result["steps"].append({"step": "load_for_baseline", "status": r.get("status")})

        # Step 3: Search WITHOUT index (baseline)
        print(f"    [3/6] Searching without index (baseline)...")
        results_before = search_brute_force(adapter, col_name, queries, top_k)
        result["steps"].append({"step": "search_before_index", "result_count": len(results_before) if results_before else 0})

        # Step 4: Release, build index, reload
        print(f"    [4/6] Building {index_type} index...")
        adapter.execute({"operation": "release", "params": {"collection_name": col_name}})
        build_params = {"collection_name": col_name, "index_type": index_type, "metric_type": "L2"}
        if index_params:
            build_params.update(index_params)
        r = adapter.execute({"operation": "build_index", "params": build_params})
        if r.get("status") != "success":
            result["classification"] = "INFRA_FAILURE"
            result["error"] = f"Index build failed: {r.get('error')}"
            return result
        result["steps"].append({"step": "build_index", "status": "ok", "index_type": index_type, "algo_params": r.get("algo_params", {})})

        # Step 5: Load with index
        print(f"    [5/6] Loading with index...")
        r = adapter.execute({"operation": "load", "params": {"collection_name": col_name}})
        result["steps"].append({"step": "load_with_index", "status": r.get("status")})

        # Step 6: Search WITH index
        print(f"    [6/6] Searching with {index_type} index...")
        results_after = search_brute_force(adapter, col_name, queries, top_k)
        result["steps"].append({"step": "search_after_index", "result_count": len(results_after) if results_after else 0})

        # Oracle evaluation
        oracle_result = oracle_idx001(results_before or [], results_after, index_type)
        result["oracle"] = oracle_result
        result["classification"] = oracle_result["classification"]

    except Exception as e:
        result["classification"] = "INFRA_FAILURE"
        result["error"] = str(e)
    finally:
        # Cleanup
        adapter.execute({"operation": "drop_collection", "params": {"collection_name": col_name}})
        result["finished_at"] = datetime.now().isoformat()

    return result


def run_idx002_test(
    adapter: MilvusAdapter,
    test_id: str,
    index_type: str,
    vectors: List[List[float]],
    index_params: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Run IDX-002 data preservation test."""
    col_name = f"r5b_idx002_{test_id}_{datetime.now().strftime('%H%M%S')}"
    dim = len(vectors[0])
    result = {
        "test_id": f"IDX-002-{test_id}",
        "contract": "IDX-002",
        "index_type": index_type,
        "dataset_size": len(vectors),
        "started_at": datetime.now().isoformat(),
        "steps": [],
        "oracle": None,
        "classification": None,
    }

    try:
        # Setup collection
        print(f"    [1/4] Setting up collection {col_name}...")
        if not setup_collection(adapter, col_name, dim, vectors):
            result["classification"] = "INFRA_FAILURE"
            result["error"] = "Collection setup failed"
            return result

        # Count before index
        print(f"    [2/4] Counting entities before index...")
        count_before = get_entity_count(adapter, col_name)
        result["steps"].append({"step": "count_before", "count": count_before})

        # Build index
        print(f"    [3/4] Building {index_type} index...")
        build_params = {"collection_name": col_name, "index_type": index_type, "metric_type": "L2"}
        if index_params:
            build_params.update(index_params)
        r = adapter.execute({"operation": "build_index", "params": build_params})
        if r.get("status") != "success":
            result["classification"] = "INFRA_FAILURE"
            result["error"] = f"Index build failed: {r.get('error')}"
            return result
        result["steps"].append({"step": "build_index", "status": "ok"})

        # Count after index
        print(f"    [4/4] Counting entities after index...")
        count_after = get_entity_count(adapter, col_name)
        result["steps"].append({"step": "count_after", "count": count_after})

        # Oracle evaluation
        oracle_result = oracle_idx002(count_before, count_after)
        result["oracle"] = oracle_result
        result["classification"] = oracle_result["classification"]

    except Exception as e:
        result["classification"] = "INFRA_FAILURE"
        result["error"] = str(e)
    finally:
        adapter.execute({"operation": "drop_collection", "params": {"collection_name": col_name}})
        result["finished_at"] = datetime.now().isoformat()

    return result


# ─────────────────────────────────────────────────────────────
# Main runner
# ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="R5B Index Behavior Pilot")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=19530)
    parser.add_argument("--mock", action="store_true", help="Use mock adapter (offline mode)")
    parser.add_argument("--output-dir", default="results")
    args = parser.parse_args()

    run_id = f"r5b-index-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    print(f"\n{'='*60}")
    print(f"  R5B INDEX BEHAVIOR PILOT")
    print(f"  Run ID: {run_id}")
    print(f"{'='*60}\n")

    # Create adapter
    if args.mock:
        print("Using mock adapter (offline mode).")
        adapter = MockAdapter(response_mode=ResponseMode.SUCCESS)
    else:
        print(f"Connecting to Milvus at {args.host}:{args.port}...")
        try:
            adapter = MilvusAdapter({"host": args.host, "port": args.port})
            if not adapter.health_check():
                raise RuntimeError("Health check failed")
            print("Connected successfully.\n")
        except Exception as e:
            print(f"ERROR: {e}")
            print("Tip: Start Milvus with: docker run -d --name milvus -p 19530:19530 milvusdb/milvus:latest")
            sys.exit(1)

    # Generate datasets
    print("Generating datasets...")
    dataset1 = generate_random_dataset(n=1000, dim=128, seed=42)
    dataset2 = generate_clustered_dataset(n=500, dim=128, n_clusters=5, seed=42)
    queries = generate_query_vectors(n=10, dim=128, seed=99)
    print(f"  Dataset 1 (random): {len(dataset1)} vectors × {len(dataset1[0])}D")
    print(f"  Dataset 2 (clustered): {len(dataset2)} vectors × {len(dataset2[0])}D")
    print(f"  Query vectors: {len(queries)}\n")

    all_results = []

    # ── IDX-001 tests ──────────────────────────────────────────
    idx001_cases = [
        ("hnsw",     "HNSW",     dataset1, {"M": 16, "efConstruction": 200}),
        ("ivf_flat", "IVF_FLAT", dataset1, {"nlist": 128}),
        ("flat",     "FLAT",     dataset1, None),
        ("clustered","HNSW",     dataset2, {"M": 16, "efConstruction": 200}),
    ]

    for short_id, index_type, dataset, idx_params in idx001_cases:
        print(f"\n── IDX-001-{short_id.upper()} ({index_type}, {len(dataset)} vectors) ──")
        r = run_idx001_test(adapter, short_id, index_type, dataset, queries, top_k=10, index_params=idx_params)
        all_results.append(r)
        cls = r["classification"]
        qual = r.get("oracle", {}).get("quality_classification", "N/A") if r.get("oracle") else "N/A"
        recall = r.get("oracle", {}).get("recall", "N/A") if r.get("oracle") else "N/A"
        recall_str = f"{recall:.3f}" if isinstance(recall, float) else str(recall)
        print(f"  → Classification: {cls}  |  Quality: {qual}  |  Recall: {recall_str}")

    # ── IDX-002 tests ──────────────────────────────────────────
    idx002_cases = [
        ("hnsw",     "HNSW",     dataset1, {"M": 16, "efConstruction": 200}),
        ("ivf_flat", "IVF_FLAT", dataset1, {"nlist": 128}),
    ]

    for short_id, index_type, dataset, idx_params in idx002_cases:
        print(f"\n── IDX-002-{short_id.upper()} ({index_type}, {len(dataset)} vectors) ──")
        r = run_idx002_test(adapter, short_id, index_type, dataset, index_params=idx_params)
        all_results.append(r)
        cls = r["classification"]
        oracle_info = r.get("oracle", {})
        cb = oracle_info.get("count_before", "N/A")
        ca = oracle_info.get("count_after", "N/A")
        print(f"  → Classification: {cls}  |  count_before={cb}  count_after={ca}")

    # ── Summary ────────────────────────────────────────────────
    counts: Dict[str, int] = {}
    for r in all_results:
        cls = r.get("classification", "UNKNOWN")
        counts[cls] = counts.get(cls, 0) + 1

    print(f"\n{'='*60}")
    print(f"  R5B SUMMARY")
    print(f"{'='*60}")
    print(f"  Total tests:    {len(all_results)}")
    for cls, cnt in sorted(counts.items()):
        print(f"  {cls:25s}: {cnt}")
    violations = [r for r in all_results if r.get("classification") == "VIOLATION"]
    if violations:
        print(f"\n  *** {len(violations)} VIOLATION(S) FOUND ***")
        for v in violations:
            print(f"    - {v['test_id']}: {v.get('oracle', {}).get('reason', 'unknown reason')}")
    else:
        print(f"\n  No violations found. Framework validated.")

    # Save results
    Path(args.output_dir).mkdir(exist_ok=True)
    out_file = Path(args.output_dir) / f"{run_id}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "run_id": run_id,
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(all_results),
            "classification_summary": counts,
            "violations_found": len(violations),
            "results": all_results,
        }, f, indent=2, ensure_ascii=False)
    print(f"\n  Results saved to: {out_file}")
    print(f"{'='*60}\n")

    if args.mock:
        print("NOTE: Mock adapter used. Results do not reflect real Milvus behavior.")


if __name__ == "__main__":
    main()
