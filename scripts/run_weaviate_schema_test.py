"""Weaviate SCH Contract Tests.

Run: python scripts/run_weaviate_schema_test.py
"""
import sys
import json
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Any, Dict

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_sch_001_data_preservation(adapter, collection: str) -> Dict[str, Any]:
    """SCH-001: Schema Evolution Data Preservation.
    
    Insert vectors with different schema fields, verify all are searchable.
    """
    results = {
        "test": "SCH-001 Data Preservation",
        "contract": "SCH-001",
        "violations": [],
        "passed": [],
    }

    # Phase 1: Insert without dynamic field
    adapter.execute({
        "operation": "drop_collection",
        "params": {"collection_name": collection}
    })
    adapter.execute({
        "operation": "create_collection",
        "params": {"collection_name": collection, "dimension": 64}
    })

    vectors_v1 = [[0.1] * 64 for _ in range(50)]
    adapter.execute({
        "operation": "insert",
        "params": {
            "collection_name": collection,
            "vectors": vectors_v1,
            "ids": list(range(50)),
            "payloads": [{"source": "v1"}] * 50
        }
    })

    # Phase 2: Add new field and insert more vectors
    # Weaviate doesn't support dynamic fields like Milvus, but we can add new properties
    vectors_v2 = [[0.2] * 64 for _ in range(50)]
    adapter.execute({
        "operation": "insert",
        "params": {
            "collection_name": collection,
            "vectors": vectors_v2,
            "ids": list(range(50, 100)),
            "payloads": [{"source": "v2", "category": "new"}] * 50
        }
    })

    # Search without filter - should return all 100
    search_result = adapter.execute({
        "operation": "search",
        "params": {"collection_name": collection, "vector": [0.1] * 64, "top_k": 100}
    })

    returned_count = len(search_result.get('data', []))
    results["passed"].append(f"Total searchable: {returned_count}/100")

    if returned_count < 100:
        results["violations"].append({
            "contract": "SCH-001",
            "expected": "100 entities searchable",
            "actual": f"{returned_count} entities",
            "issue": "Schema evolution data preservation violation"
        })

    return results


def test_sch_002_filter_compatibility(adapter, collection: str) -> Dict[str, Any]:
    """SCH-002: Query Compatibility Across Schema Updates.
    
    After schema extension, filter queries should work correctly.
    Note: Weaviate handles properties differently than Milvus.
    """
    results = {
        "test": "SCH-002 Filter Compatibility",
        "contract": "SCH-002",
        "violations": [],
        "passed": [],
    }

    # Setup: Create collection with initial data
    adapter.execute({
        "operation": "drop_collection",
        "params": {"collection_name": collection}
    })
    adapter.execute({
        "operation": "create_collection",
        "params": {"collection_name": collection, "dimension": 64}
    })

    # Insert initial batch without category field
    vectors_initial = [[0.1] * 64 for _ in range(50)]
    adapter.execute({
        "operation": "insert",
        "params": {
            "collection_name": collection,
            "vectors": vectors_initial,
            "ids": list(range(50)),
            "payloads": [{"status": "active"}] * 50
        }
    })

    # Insert new batch WITH category field
    vectors_new = [[0.2] * 64 for _ in range(50)]
    adapter.execute({
        "operation": "insert",
        "params": {
            "collection_name": collection,
            "vectors": vectors_new,
            "ids": list(range(50, 100)),
            "payloads": [{"status": "active", "category": "premium"}] * 50
        }
    })

    # Filter by category == 'premium' - should return exactly 50
    filter_result = adapter.execute({
        "operation": "filtered_search",
        "params": {
            "collection_name": collection,
            "vector": [0.1] * 64,
            "filter": {"category": "premium"},
            "top_k": 100
        }
    })

    filtered_count = len(filter_result.get('data', []))
    results["passed"].append(f"Filter category==premium: {filtered_count}/50 expected")

    # Weaviate may return 0 for non-existent property (expected behavior)
    # or may return false positives. Check if exactly 50.
    if filtered_count != 50:
        results["violations"].append({
            "contract": "SCH-002",
            "expected": "50 entities with category==premium",
            "actual": f"{filtered_count} entities",
            "issue": "Filter compatibility across schema updates"
        })

    return results


def test_sch_003_index_rebuild(adapter, collection: str) -> Dict[str, Any]:
    """SCH-003: Index Rebuild After Schema Change.
    
    Verify recall is preserved after index rebuild.
    """
    results = {
        "test": "SCH-003 Index Rebuild",
        "contract": "SCH-003",
        "violations": [],
        "passed": [],
    }

    # Setup
    adapter.execute({
        "operation": "drop_collection",
        "params": {"collection_name": collection}
    })
    adapter.execute({
        "operation": "create_collection",
        "params": {"collection_name": collection, "dimension": 64}
    })

    # Insert test data
    np.random.seed(42)
    vectors = np.random.rand(100, 64).tolist()
    adapter.execute({
        "operation": "insert",
        "params": {
            "collection_name": collection,
            "vectors": vectors,
            "ids": list(range(100)),
            "payloads": [{"idx": i} for i in range(100)]
        }
    })

    # Query vector (similar to first vector)
    query_vec = vectors[0]

    # Search before index
    result_before = adapter.execute({
        "operation": "search",
        "params": {"collection_name": collection, "vector": query_vec, "top_k": 10}
    })
    ids_before = set(r['id'] for r in result_before.get('data', []))

    # Trigger index rebuild (Weaviate: trigger compaction)
    # Note: Weaviate auto-compacts, but we can force it
    adapter.execute({
        "operation": "flush",
        "params": {"collection_name": collection}
    })

    # Search after index rebuild
    result_after = adapter.execute({
        "operation": "search",
        "params": {"collection_name": collection, "vector": query_vec, "top_k": 10}
    })
    ids_after = set(r['id'] for r in result_after.get('data', []))

    # Calculate recall
    intersection = len(ids_before & ids_after)
    recall = intersection / 10.0 if len(ids_before) > 0 else 0
    results["passed"].append(f"Recall before/after: {recall:.3f}")

    if recall < 0.9:
        results["violations"].append({
            "contract": "SCH-003",
            "expected": "recall >= 0.9",
            "actual": f"recall = {recall:.3f}",
            "issue": "Index rebuild recall degradation"
        })

    return results


def test_sch_004_metadata_accuracy(adapter, collection: str) -> Dict[str, Any]:
    """SCH-004: Metadata Accuracy.
    
    Verify count is accurate after mixed schema operations.
    """
    results = {
        "test": "SCH-004 Metadata Accuracy",
        "contract": "SCH-004",
        "violations": [],
        "passed": [],
    }

    # Setup
    adapter.execute({
        "operation": "drop_collection",
        "params": {"collection_name": collection}
    })
    adapter.execute({
        "operation": "create_collection",
        "params": {"collection_name": collection, "dimension": 64}
    })

    # Insert v1 data
    vectors_v1 = [[0.1] * 64 for _ in range(50)]
    adapter.execute({
        "operation": "insert",
        "params": {
            "collection_name": collection,
            "vectors": vectors_v1,
            "ids": list(range(50)),
            "payloads": [{"ver": 1}] * 50
        }
    })

    # Insert v2 data with extra field
    vectors_v2 = [[0.2] * 64 for _ in range(50)]
    adapter.execute({
        "operation": "insert",
        "params": {
            "collection_name": collection,
            "vectors": vectors_v2,
            "ids": list(range(50, 100)),
            "payloads": [{"ver": 2, "category": "test"}] * 50
        }
    })

    # Delete some entities
    adapter.execute({
        "operation": "delete",
        "params": {"collection_name": collection, "ids": list(range(10))}
    })

    # Count should be 90
    count_result = adapter.execute({
        "operation": "count_entities",
        "params": {"collection_name": collection}
    })
    actual_count = count_result.get('data', [{}])[0].get('storage_count', 0)
    
    expected_count = 90
    results["passed"].append(f"Count after delete: {actual_count}/{expected_count}")

    if actual_count != expected_count:
        results["violations"].append({
            "contract": "SCH-004",
            "expected": expected_count,
            "actual": actual_count,
            "issue": "Metadata count inaccuracy after delete"
        })

    return results


def run_weaviate_schema_tests(adapter_name: str, adapter) -> Dict[str, Any]:
    """Run all SCH contracts on Weaviate."""
    collection = f"sch_test_{datetime.now().strftime('%H%M%S')}"
    
    print(f"\n{'='*60}")
    print(f"Weaviate SCH Contract Tests")
    print(f"{'='*60}")

    all_results = []

    # SCH-001: Data Preservation
    print("\n[SCH-001] Data Preservation...")
    r1 = test_sch_001_data_preservation(adapter, collection)
    all_results.append(r1)
    print(f"  Violations: {len(r1['violations'])}")

    # SCH-002: Filter Compatibility
    print("\n[SCH-002] Filter Compatibility...")
    r2 = test_sch_002_filter_compatibility(adapter, collection)
    all_results.append(r2)
    print(f"  Violations: {len(r2['violations'])}")

    # SCH-003: Index Rebuild
    print("\n[SCH-003] Index Rebuild...")
    r3 = test_sch_003_index_rebuild(adapter, collection)
    all_results.append(r3)
    print(f"  Violations: {len(r3['violations'])}")

    # SCH-004: Metadata Accuracy
    print("\n[SCH-004] Metadata Accuracy...")
    r4 = test_sch_004_metadata_accuracy(adapter, collection)
    all_results.append(r4)
    print(f"  Violations: {len(r4['violations'])}")

    # Cleanup
    adapter.execute({"operation": "drop_collection", "params": {"collection_name": collection}})

    # Summary
    total_violations = sum(len(r["violations"]) for r in all_results)
    print(f"\n{'='*60}")
    print(f"Weaviate SCH TOTAL VIOLATIONS: {total_violations}")
    print(f"{'='*60}")

    return {
        "adapter": adapter_name,
        "results": all_results,
        "total_violations": total_violations
    }


if __name__ == "__main__":
    from adapters.weaviate_adapter import WeaviateAdapter

    adapter = WeaviateAdapter({"url": "http://localhost:8080"})
    
    if not adapter.health_check():
        print("Weaviate is not available!")
        sys.exit(1)

    result = run_weaviate_schema_tests("weaviate", adapter)

    # Save results
    output_path = project_root / "results" / f"weaviate_sch_tests_{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2, default=str)

    print(f"\nResults saved to: {output_path}")
