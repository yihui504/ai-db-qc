"""HYB Contract Tests for Qdrant: Payload Filter Edge Cases.

This script tests HYB-001/002/003 contracts on Qdrant with focus on:
1. Range filters (>, <, >=, <=)
2. DATETIME filters (boundary values, invalid formats)
3. Complex filter combinations

Based on historical bug analysis from GitHub issues:
- Qdrant #7462: DATETIME payload accepts invalid RFC3339 timestamps
- Qdrant payload filter inconsistencies

Run: python scripts/run_qdrant_hyb_contract.py
"""

import json
import sys
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Dict, List

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from adapters.qdrant_adapter import QdrantAdapter


def generate_test_vectors(dim: int = 64, n: int = 100) -> List[List[float]]:
    """Generate random test vectors."""
    np.random.seed(42)
    return np.random.rand(n, dim).astype(np.float32).tolist()


def test_hyb_001_range_filter(adapter: QdrantAdapter, collection: str) -> Dict[str, Any]:
    """HYB-001: Filter Pre-Application - Range filters."""
    results = {
        "test": "HYB-001 Range Filter",
        "violations": [],
        "passed": [],
    }

    # Test 1: Greater than (gt)
    filter_gt = {"score": {"gt": 50}}
    result = adapter.execute({
        "operation": "filtered_search",
        "params": {"collection_name": collection, "vector": [0.1] * 64, "top_k": 100, "filter": filter_gt}
    })
    if result["status"] == "success":
        returned_ids = [r["id"] for r in result["data"]]
        for r in result["data"]:
            if r["payload"].get("score", 0) <= 50:
                results["violations"].append({
                    "filter": "score > 50",
                    "returned_id": r["id"],
                    "actual_score": r["payload"].get("score"),
                    "issue": "Filter not applied - returned entity with score <= 50"
                })
        results["passed"].append(f"gt filter: {len(returned_ids)} results")

    # Test 2: Less than (lt)
    filter_lt = {"score": {"lt": 50}}
    result = adapter.execute({
        "operation": "filtered_search",
        "params": {"collection_name": collection, "vector": [0.1] * 64, "top_k": 100, "filter": filter_lt}
    })
    if result["status"] == "success":
        for r in result["data"]:
            if r["payload"].get("score", 100) >= 50:
                results["violations"].append({
                    "filter": "score < 50",
                    "returned_id": r["id"],
                    "actual_score": r["payload"].get("score"),
                    "issue": "Filter not applied - returned entity with score >= 50"
                })
        results["passed"].append(f"lt filter: {len(result['data'])} results")

    # Test 3: Range combination (gte + lte)
    filter_range = {"score": {"gte": 30, "lte": 70}}
    result = adapter.execute({
        "operation": "filtered_search",
        "params": {"collection_name": collection, "vector": [0.1] * 64, "top_k": 100, "filter": filter_range}
    })
    if result["status"] == "success":
        for r in result["data"]:
            score = r["payload"].get("score", 0)
            if score < 30 or score > 70:
                results["violations"].append({
                    "filter": "30 <= score <= 70",
                    "returned_id": r["id"],
                    "actual_score": score,
                    "issue": "Range filter not applied"
                })
        results["passed"].append(f"range filter: {len(result['data'])} results")

    return results


def test_hyb_002_filter_consistency(adapter: QdrantAdapter, collection: str) -> Dict[str, Any]:
    """HYB-002: Filter-Result Consistency."""
    results = {
        "test": "HYB-002 Filter Consistency",
        "violations": [],
        "passed": [],
    }

    # Test: Category filter
    filter_cat = {"category": "A"}
    result = adapter.execute({
        "operation": "filtered_search",
        "params": {"collection_name": collection, "vector": [0.1] * 64, "top_k": 100, "filter": filter_cat}
    })
    if result["status"] == "success":
        for r in result["data"]:
            if r["payload"].get("category") != "A":
                results["violations"].append({
                    "filter": "category == 'A'",
                    "returned_id": r["id"],
                    "actual_category": r["payload"].get("category"),
                    "issue": "Filter consistency violation"
                })
        results["passed"].append(f"category filter: {len(result['data'])} results")

    # Test: IN filter
    filter_in = {"status": ["active", "pending"]}
    result = adapter.execute({
        "operation": "filtered_search",
        "params": {"collection_name": collection, "vector": [0.1] * 64, "top_k": 100, "filter": filter_in}
    })
    if result["status"] == "success":
        for r in result["data"]:
            if r["payload"].get("status") not in ["active", "pending"]:
                results["violations"].append({
                    "filter": "status in [active, pending]",
                    "returned_id": r["id"],
                    "actual_status": r["payload"].get("status"),
                    "issue": "IN filter consistency violation"
                })
        results["passed"].append(f"IN filter: {len(result['data'])} results")

    return results


def test_datetime_filter(adapter: QdrantAdapter, collection: str) -> Dict[str, Any]:
    """Test DATETIME filtering - boundary values."""
    results = {
        "test": "DATETIME Filter Edge Cases",
        "violations": [],
        "passed": [],
    }

    # Test: Future dates (year > 2500)
    filter_future = {"event_date": {"gte": "2500-01-01T00:00:00Z"}}
    result = adapter.execute({
        "operation": "filtered_search",
        "params": {"collection_name": collection, "vector": [0.1] * 64, "top_k": 100, "filter": filter_future}
    })
    if result["status"] == "success":
        for r in result["data"]:
            date_val = r["payload"].get("event_date", "")
            if date_val and date_val < "2500-01-01":
                results["violations"].append({
                    "filter": "event_date >= 2500-01-01",
                    "returned_id": r["id"],
                    "actual_date": date_val,
                    "issue": "DATETIME filter returned pre-2500 date"
                })
        results["passed"].append(f"future date filter: {len(result['data'])} results")

    # Test: Invalid DATETIME format handling
    invalid_dates = [
        "2025-01-01 00:00:00+00:00",  # Space instead of T
    ]

    for inv_date in invalid_dates:
        try:
            adapter.execute({
                "operation": "insert",
                "params": {
                    "collection_name": collection,
                    "vectors": [[0.1] * 64],
                    "ids": [9999],
                    "scalar_data": [{"invalid_date": inv_date}]
                }
            })
            filter_inv = {"invalid_date": inv_date}
            result = adapter.execute({
                "operation": "filtered_search",
                "params": {"collection_name": collection, "vector": [0.1] * 64, "top_k": 10, "filter": filter_inv}
            })
            results["passed"].append(f"invalid date '{inv_date}': inserted, filter result: {len(result.get('data', []))}")
        except Exception as e:
            results["passed"].append(f"invalid date '{inv_date}': rejected with {type(e).__name__}")

    return results


def test_null_filter(adapter: QdrantAdapter, collection: str) -> Dict[str, Any]:
    """Test null/empty value filtering."""
    results = {
        "test": "Null Filter Handling",
        "violations": [],
        "passed": [],
    }

    # Insert point with null field
    adapter.execute({
        "operation": "insert",
        "params": {
            "collection_name": collection,
            "vectors": [[0.1] * 64],
            "ids": [8888],
            "scalar_data": [{"optional_field": None}]
        }
    })

    # Filter for null field
    filter_null = {"optional_field": None}
    result = adapter.execute({
        "operation": "filtered_search",
        "params": {"collection_name": collection, "vector": [0.1] * 64, "top_k": 10, "filter": filter_null}
    })
    if result["status"] == "success":
        results["passed"].append(f"null filter: {len(result['data'])} results")

    return results


def main():
    """Run HYB contract tests on Qdrant."""
    print("=" * 60)
    print("Qdrant HYB Contract Tests")
    print("=" * 60)

    # Initialize adapter
    adapter = QdrantAdapter({"url": "http://localhost:6333"})
    
    # Health check
    if not adapter.health_check():
        print("ERROR: Qdrant is not accessible at http://localhost:6333")
        return

    # Create test collection
    collection = "hyb_test_collection"
    adapter.execute({"operation": "drop_collection", "params": {"collection_name": collection}})
    adapter.execute({
        "operation": "create_collection",
        "params": {"collection_name": collection, "dimension": 64}
    })
    print(f"\nCreated collection: {collection}")

    # Insert test data
    print("Inserting test data...")
    n = 100
    vectors = generate_test_vectors(dim=64, n=n)

    scalar_data = []
    for i in range(n):
        scalar_data.append({
            "id": i,
            "score": i,
            "category": "A" if i < 50 else "B",
            "status": "active" if i % 2 == 0 else "pending",
            "event_date": f"202{i % 5}-01-{(i % 28) + 1:02d}T00:00:00Z",
            "value": float(i * 10),
        })

    adapter.execute({
        "operation": "insert",
        "params": {
            "collection_name": collection,
            "vectors": vectors,
            "ids": list(range(n)),
            "scalar_data": scalar_data
        }
    })
    print(f"Inserted {n} vectors with diverse payload")

    # Run tests
    all_results = []

    # Test 1: Range filters
    print("\n[1/4] Testing HYB-001 Range Filters...")
    r1 = test_hyb_001_range_filter(adapter, collection)
    all_results.append(r1)
    print(f"  Violations: {len(r1['violations'])}")

    # Test 2: Filter consistency
    print("\n[2/4] Testing HYB-002 Filter Consistency...")
    r2 = test_hyb_002_filter_consistency(adapter, collection)
    all_results.append(r2)
    print(f"  Violations: {len(r2['violations'])}")

    # Test 3: DATETIME edge cases
    print("\n[3/4] Testing DATETIME Edge Cases...")
    r3 = test_datetime_filter(adapter, collection)
    all_results.append(r3)
    print(f"  Violations: {len(r3['violations'])}")

    # Test 4: Null handling
    print("\n[4/4] Testing Null Filter Handling...")
    r4 = test_null_filter(adapter, collection)
    all_results.append(r4)
    print(f"  Violations: {len(r4['violations'])}")

    # Summary
    total_violations = sum(len(r["violations"]) for r in all_results)
    print("\n" + "=" * 60)
    print(f"TOTAL VIOLATIONS: {total_violations}")
    print("=" * 60)

    # Save results
    output_path = project_root / "results" / f"qdrant_hyb_contract_{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, "w") as f:
        json.dump({
            "results": all_results,
            "summary": {
                "total_violations": total_violations,
                "tests_run": len(all_results),
            }
        }, f, indent=2, default=str)

    print(f"\nResults saved to: {output_path}")

    # Cleanup
    adapter.execute({"operation": "drop_collection", "params": {"collection_name": collection}})
    print("Test collection cleaned up.")

    return total_violations


if __name__ == "__main__":
    sys.exit(main())
