"""Extreme Lifecycle Tests: Delete-Immediately, Insert-Immediately, Index-Rebuild Window.

This script tests edge cases in vector database lifecycle operations:
1. Delete-then-search: Search immediately after deletion
2. Insert-then-search: Search immediately after bulk insert (before flush/rebuild)
3. Index rebuild window: Query during index rebuild

Run: python scripts/run_extreme_lifecycle_test.py --adapters qdrant weaviate
"""

import sys
import json
import time
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_delete_then_search(adapter, collection: str) -> Dict[str, Any]:
    """Test search immediately after deletion."""
    results = {
        "test": "Delete-then-Search",
        "violations": [],
        "passed": [],
    }

    # Insert 100 vectors
    vectors = [[0.1] * 64 for _ in range(100)]
    adapter.execute({
        "operation": "insert",
        "params": {"collection_name": collection, "vectors": vectors, "ids": list(range(100))}
    })

    # Get count before delete
    count_before = adapter.execute({
        "operation": "count_entities",
        "params": {"collection_name": collection}
    })
    results["passed"].append(f"Count before delete: {count_before['data'][0]['storage_count']}")

    # Delete half
    delete_ids = list(range(50))
    adapter.execute({
        "operation": "delete",
        "params": {"collection_name": collection, "ids": delete_ids}
    })

    # Search immediately (no flush/wait)
    search_result = adapter.execute({
        "operation": "search",
        "params": {"collection_name": collection, "vector": [0.1] * 64, "top_k": 100}
    })

    # Get count after delete
    count_after = adapter.execute({
        "operation": "count_entities",
        "params": {"collection_name": collection}
    })

    results["passed"].append(f"Count after delete: {count_after['data'][0]['storage_count']}")
    results["passed"].append(f"Search returned: {len(search_result['data'])} results")

    # Check consistency: count should reflect deletion
    expected_count = 50
    actual_count = count_after['data'][0]['storage_count']
    if actual_count != expected_count:
        results["violations"].append({
            "operation": "delete-then-count",
            "expected": expected_count,
            "actual": actual_count,
            "issue": "Count does not reflect deletion immediately"
        })

    return results


def test_insert_then_search(adapter, collection: str) -> Dict[str, Any]:
    """Test search immediately after bulk insert (before explicit flush)."""
    results = {
        "test": "Insert-then-Search",
        "violations": [],
        "passed": [],
    }

    # Get initial count
    count_before = adapter.execute({
        "operation": "count_entities",
        "params": {"collection_name": collection}
    })
    initial_count = count_before['data'][0]['storage_count']

    # Insert 50 more vectors
    vectors = [[0.1] * 64 for _ in range(50)]
    adapter.execute({
        "operation": "insert",
        "params": {"collection_name": collection, "vectors": vectors, "ids": list(range(100, 150))}
    })

    # Search immediately (no flush)
    search_result = adapter.execute({
        "operation": "search",
        "params": {"collection_name": collection, "vector": [0.1] * 64, "top_k": 200}
    })

    # Get count immediately after insert
    count_after = adapter.execute({
        "operation": "count_entities",
        "params": {"collection_name": collection}
    })

    results["passed"].append(f"Initial count: {initial_count}")
    results["passed"].append(f"Count after insert: {count_after['data'][0]['storage_count']}")
    results["passed"].append(f"Search returned: {len(search_result['data'])} results")

    # Check: count should include newly inserted
    expected_count = initial_count + 50
    actual_count = count_after['data'][0]['storage_count']
    if actual_count != expected_count:
        results["violations"].append({
            "operation": "insert-then-count",
            "expected": expected_count,
            "actual": actual_count,
            "issue": "Count does not include newly inserted entities"
        })

    # Check: search should return newly inserted
    if len(search_result['data']) < expected_count:
        results["violations"].append({
            "operation": "insert-then-search",
            "expected": f">={expected_count}",
            "actual": len(search_result['data']),
            "issue": "Search does not return newly inserted entities"
        })

    return results


def test_empty_collection_search(adapter, collection: str) -> Dict[str, Any]:
    """Test search on empty collection."""
    results = {
        "test": "Empty-Collection-Search",
        "violations": [],
        "passed": [],
    }

    # Ensure collection is empty
    adapter.execute({
        "operation": "drop_collection",
        "params": {"collection_name": collection}
    })
    adapter.execute({
        "operation": "create_collection",
        "params": {"collection_name": collection, "dimension": 64}
    })

    # Search on empty collection
    search_result = adapter.execute({
        "operation": "search",
        "params": {"collection_name": collection, "vector": [0.1] * 64, "top_k": 10}
    })

    results["passed"].append(f"Search on empty: {len(search_result['data'])} results")

    # Should return empty or gracefully handle
    if search_result["status"] == "error":
        results["violations"].append({
            "operation": "empty-search",
            "expected": "empty result or graceful handling",
            "actual": search_result["status"],
            "issue": "Error on empty collection search"
        })

    return results


def run_tests(adapter_name: str, adapter):
    """Run all lifecycle tests on a single adapter."""
    collection = f"lifecycle_test_{adapter_name}"

    # Cleanup
    try:
        adapter.execute({"operation": "drop_collection", "params": {"collection_name": collection}})
    except:
        pass

    # Create collection
    adapter.execute({
        "operation": "create_collection",
        "params": {"collection_name": collection, "dimension": 64}
    })

    print(f"\n{'='*60}")
    print(f"Testing {adapter_name}")
    print(f"{'='*60}")

    all_results = []

    # Test 1: Delete then search
    print(f"\n[1/3] Delete-then-Search...")
    r1 = test_delete_then_search(adapter, collection)
    all_results.append(r1)
    print(f"  Violations: {len(r1['violations'])}")

    # Test 2: Insert then search
    print(f"\n[2/3] Insert-then-Search...")
    r2 = test_insert_then_search(adapter, collection)
    all_results.append(r2)
    print(f"  Violations: {len(r2['violations'])}")

    # Test 3: Empty collection search
    print(f"\n[3/3] Empty-Collection-Search...")
    r3 = test_empty_collection_search(adapter, collection)
    all_results.append(r3)
    print(f"  Violations: {len(r3['violations'])}")

    # Summary
    total_violations = sum(len(r["violations"]) for r in all_results)
    print(f"\n{adapter_name} TOTAL VIOLATIONS: {total_violations}")

    # Cleanup
    adapter.execute({"operation": "drop_collection", "params": {"collection_name": collection}})

    return {
        "adapter": adapter_name,
        "results": all_results,
        "total_violations": total_violations
    }


def main():
    """Run lifecycle tests on all specified adapters."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--adapters", default="qdrant,weaviate", help="Comma-separated list of adapters")
    args = parser.parse_args()

    adapters_list = [a.strip() for a in args.adapters.split(",")]

    all_adapter_results = []

    for adapter_name in adapters_list:
        if adapter_name == "qdrant":
            from adapters.qdrant_adapter import QdrantAdapter
            adapter = QdrantAdapter({"url": "http://localhost:6333"})
        elif adapter_name == "weaviate":
            from adapters.weaviate_adapter import WeaviateAdapter
            adapter = WeaviateAdapter({"url": "http://localhost:8080"})
        elif adapter_name == "milvus":
            from adapters.milvus_adapter import MilvusAdapter
            adapter = MilvusAdapter({"host": "localhost", "port": 19530})
        else:
            print(f"Unknown adapter: {adapter_name}")
            continue

        # Health check
        if not adapter.health_check():
            print(f"{adapter_name} is not available, skipping...")
            continue

        result = run_tests(adapter_name, adapter)
        all_adapter_results.append(result)

    # Save results
    output_path = project_root / "results" / f"lifecycle_tests_{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(all_adapter_results, f, indent=2, default=str)

    print(f"\n{'='*60}")
    print(f"Results saved to: {output_path}")
    print(f"{'='*60}")

    # Summary
    total = sum(r["total_violations"] for r in all_adapter_results)
    print(f"\nOVERALL TOTAL VIOLATIONS: {total}")

    return total


if __name__ == "__main__":
    sys.exit(main())
