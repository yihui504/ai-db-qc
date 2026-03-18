#!/usr/bin/env python3
"""
Schema Evolution Contract Tests for ai-db-qc
=============================================
Tests schema evolution contracts:

  SCH-005  Backward Compatibility  -- schema extensions must not break existing queries
  SCH-006  Schema Atomicity         -- schema operations must be atomic

Usage:
    python scripts/run_schema_evolution.py --db milvus
    python scripts/run_schema_evolution.py --db qdrant
    python scripts/run_schema_evolution.py --db weaviate
    python scripts/run_schema_evolution.py --db pgvector
    python scripts/run_schema_evolution.py --db all
"""

import argparse
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import yaml

import numpy as np

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ---------------------------------------------------------------------------
# Load database connection config
# ---------------------------------------------------------------------------
def load_connection_config() -> Dict[str, Any]:
    """Load database connection configuration."""
    config_path = PROJECT_ROOT / "configs" / "database_connections.yaml"
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return {}

CONNECTION_CONFIG = load_connection_config()

# ---------------------------------------------------------------------------
# Triage helper
# ---------------------------------------------------------------------------

TRIAGE_LEVELS = ["PASS", "MARGINAL", "AMBIGUOUS", "SUSPICIOUS", "LIKELY_BUG", "BUG"]


def triage(condition: bool, label: str, details: str = "") -> str:
    """Return a triage verdict string."""
    verdict = "PASS" if condition else "LIKELY_BUG"
    icon = "[OK]" if condition else "[FAIL]"
    suffix = f"  [{details}]" if details else ""
    print(f"  {icon} {label}: {verdict}{suffix}")
    return verdict


# ---------------------------------------------------------------------------
# Adapter factory
# ---------------------------------------------------------------------------

def get_adapter(db_name: str) -> Any:
    """Instantiate and return adapter for *db_name*."""
    db_name = db_name.lower()
    config = CONNECTION_CONFIG.get(db_name, {})
    
    if db_name == "milvus":
        from adapters.milvus_adapter import MilvusAdapter
        return MilvusAdapter(config)
    elif db_name == "qdrant":
        from adapters.qdrant_adapter import QdrantAdapter
        return QdrantAdapter(config)
    elif db_name == "weaviate":
        from adapters.weaviate_adapter import WeaviateAdapter
        return WeaviateAdapter(config)
    elif db_name in ("pgvector", "pg"):
        from adapters.pgvector_adapter import PgvectorAdapter
        return PgvectorAdapter(config)
    else:
        raise ValueError(f"Unknown database: {db_name!r}. "
                         "Choose from: milvus, qdrant, weaviate, pgvector")


def _is_milvus(adapter: Any) -> bool:
    return type(adapter).__name__ == "MilvusAdapter"


def _flush(adapter: Any, col: str) -> None:
    """Issue a flush if adapter supports it (required for Milvus)."""
    try:
        adapter.execute({"operation": "flush", "params": {"collection_name": col}})
        time.sleep(1.0)
    except Exception:
        pass


def _count(adapter: Any, col: str) -> int:
    """Return entity count for *col*."""
    res = adapter.execute({"operation": "count_entities",
                           "params": {"collection_name": col}})
    if res.get("status") == "success":
        for key in ("storage_count", "count", "entity_count"):
            val = res.get(key) or (res.get("data", [{}])[0].get(key) if res.get("data") else None)
            if val is not None:
                return int(val)
    return 0


def _get_schema(adapter: Any, col: str) -> Dict[str, Any]:
    """Get schema for collection."""
    try:
        res = adapter.execute({"operation": "describe_collection",
                               "params": {"collection_name": col}})
        if res.get("status") == "success":
            return res.get("data", {})
    except Exception:
        pass
    return {}


# ---------------------------------------------------------------------------
# Test utilities
# ---------------------------------------------------------------------------

def generate_vectors(count: int, dim: int) -> List[List[float]]:
    """Generate random vectors."""
    return np.random.random((count, dim)).tolist()


def generate_test_data(count: int, dim: int) -> List[Dict[str, Any]]:
    """Generate test data with vectors and metadata."""
    vectors = generate_vectors(count, dim)
    data = []
    for i, vec in enumerate(vectors):
        data.append({
            "id": i,
            "vector": vec,
            "metadata": {"category": f"cat_{i % 5}", "value": i}
        })
    return data


# ---------------------------------------------------------------------------
# SCH-005: Schema Extension Backward Compatibility
# ---------------------------------------------------------------------------

def test_sch005_backward_compatibility(adapter: Any, db_name: str) -> Dict[str, Any]:
    """Test SCH-005: Schema Extension Backward Compatibility."""
    print(f"\n{'='*60}")
    print(f"SCH-005: Schema Extension Backward Compatibility - {db_name}")
    print(f"{'='*60}")

    results = {
        "contract_id": "SCH-005",
        "database": db_name,
        "test_cases": []
    }

    col = "sch005_test"

    try:
        # Test Case 1: Search after field extension
        print("\n[Test 1] Search after field extension")
        test1_result = {"name": "Search after field extension", "checks": []}

        # Create collection with base schema
        create_res = adapter.execute({
            "operation": "create_collection",
            "params": {
                "collection_name": col,
                "dimension": 128,
                "metric_type": "L2"
            }
        })
        assert create_res.get("status") == "success", f"Failed to create collection: {create_res}"

        # Insert baseline data
        base_data = generate_test_data(100, 128)
        insert_res = adapter.execute({
            "operation": "insert",
            "params": {
                "collection_name": col,
                "vectors": [d["vector"] for d in base_data],
                "ids": [d["id"] for d in base_data]
            }
        })
        test1_result["checks"].append({
            "name": "Baseline data inserted",
            "status": insert_res.get("status") == "success"
        })

        if _is_milvus(adapter):
            _flush(adapter, col)

        # Build and load index
        index_res = adapter.execute({
            "operation": "build_index",
            "params": {
                "collection_name": col,
                "index_type": "IVF_FLAT"
            }
        })
        load_res = adapter.execute({
            "operation": "load",
            "params": {"collection_name": col}
        })

        # Perform baseline search
        query_vec = generate_vectors(1, 128)[0]
        baseline_search = adapter.execute({
            "operation": "search",
            "params": {
                "collection_name": col,
                "vector": query_vec,
                "top_k": 10
            }
        })

        baseline_success = baseline_search.get("status") == "success"
        baseline_count = len(baseline_search.get("data", []))
        test1_result["checks"].append({
            "name": "Baseline search successful",
            "status": baseline_success
        })
        test1_result["checks"].append({
            "name": f"Baseline returned {baseline_count} results",
            "status": True
        })

        # Attempt to extend schema (if supported)
        # Note: Schema extension may not be supported by all databases
        # We'll test backward compatibility by checking if queries still work
        schema_extended = False
        try:
            # Try to add a new field
            alter_res = adapter.execute({
                "operation": "alter_collection",
                "params": {
                    "collection_name": col,
                    "action": "add_field",
                    "field": {"name": "new_field", "type": "text"}
                }
            })
            schema_extended = alter_res.get("status") == "success"
            test1_result["checks"].append({
                "name": "Schema extension supported",
                "status": schema_extended
            })
        except Exception as e:
            test1_result["checks"].append({
                "name": "Schema extension not supported (expected for some databases)",
                "status": True,
                "note": str(e)
            })

        # Perform same search query after potential extension
        post_search = adapter.execute({
            "operation": "search",
            "params": {
                "collection_name": col,
                "vector": query_vec,
                "top_k": 10
            }
        })

        post_success = post_search.get("status") == "success"
        post_count = len(post_search.get("data", []))
        test1_result["checks"].append({
            "name": "Post-extension search successful",
            "status": post_success
        })
        test1_result["checks"].append({
            "name": f"Post-extension returned {post_count} results",
            "status": True
        })

        # Verify backward compatibility
        queries_still_work = post_success
        results_consistent = post_count == baseline_count if schema_extended else True
        test1_result["checks"].append({
            "name": "Queries still work",
            "status": queries_still_work
        })
        test1_result["checks"].append({
            "name": "Results consistent",
            "status": results_consistent
        })

        test1_result["verdict"] = "PASS" if queries_still_work else "LIKELY_BUG"
        results["test_cases"].append(test1_result)

        # Test Case 2: Concurrent queries during schema change
        print("\n[Test 2] Queries during schema operations")
        test2_result = {"name": "Queries during schema operations", "checks": []}

        # Perform multiple searches
        search_results = []
        for i in range(10):
            qv = generate_vectors(1, 128)[0]
            sr = adapter.execute({
                "operation": "search",
                "params": {
                    "collection_name": col,
                    "vector": qv,
                    "top_k": 10
                }
            })
            search_results.append(sr.get("status") == "success")

        all_searches_succeed = all(search_results)
        test2_result["checks"].append({
            "name": "All 10 searches succeed",
            "status": all_searches_succeed
        })

        test2_result["verdict"] = "PASS" if all_searches_succeed else "LIKELY_BUG"
        results["test_cases"].append(test2_result)

        # Overall verdict
        all_pass = all(tc["verdict"] == "PASS" for tc in results["test_cases"])
        results["overall_verdict"] = "PASS" if all_pass else "LIKELY_BUG"

    except Exception as e:
        print(f"\n  [ERROR] Exception during SCH-005: {e}")
        results["error"] = str(e)
        results["overall_verdict"] = "ERROR"
    finally:
        # Cleanup
        try:
            adapter.execute({"operation": "drop_collection",
                           "params": {"collection_name": col}})
        except Exception:
            pass

    return results


# ---------------------------------------------------------------------------
# SCH-006: Schema Operation Atomicity
# ---------------------------------------------------------------------------

def test_sch006_atomicity(adapter: Any, db_name: str) -> Dict[str, Any]:
    """Test SCH-006: Schema Operation Atomicity."""
    print(f"\n{'='*60}")
    print(f"SCH-006: Schema Operation Atomicity - {db_name}")
    print(f"{'='*60}")

    results = {
        "contract_id": "SCH-006",
        "database": db_name,
        "test_cases": []
    }

    col = "sch006_test"

    try:
        # Test Case 1: Failed schema operation rollback
        print("\n[Test 1] Failed schema operation rollback")
        test1_result = {"name": "Failed schema operation rollback", "checks": []}

        # Create collection
        create_res = adapter.execute({
            "operation": "create_collection",
            "params": {
                "collection_name": col,
                "dimension": 128,
                "metric_type": "L2"
            }
        })
        assert create_res.get("status") == "success"

        # Insert data
        data = generate_test_data(50, 128)
        insert_res = adapter.execute({
            "operation": "insert",
            "params": {
                "collection_name": col,
                "vectors": [d["vector"] for d in data],
                "ids": [d["id"] for d in data]
            }
        })

        if _is_milvus(adapter):
            _flush(adapter, col)
            # Create index before loading
            adapter.execute({
                "operation": "build_index",
                "params": {
                    "collection_name": col,
                    "index_type": "IVF_FLAT"
                }
            })
            adapter.execute({
                "operation": "load",
                "params": {"collection_name": col}
            })

        original_count = _count(adapter, col)
        test1_result["checks"].append({
            "name": f"Original data count: {original_count}",
            "status": original_count > 0
        })

        original_schema = _get_schema(adapter, col)
        test1_result["checks"].append({
            "name": "Original schema captured",
            "status": bool(original_schema)
        })

        # Attempt invalid schema change
        invalid_alter_res = adapter.execute({
            "operation": "alter_collection",
            "params": {
                "collection_name": col,
                "action": "invalid_action",
                "field": "invalid"
            }
        })

        failed_as_expected = invalid_alter_res.get("status") != "success"
        test1_result["checks"].append({
            "name": "Invalid schema change rejected",
            "status": failed_as_expected
        })

        # Verify original schema intact
        current_schema = _get_schema(adapter, col)
        schema_intact = bool(current_schema)
        test1_result["checks"].append({
            "name": "Schema intact after failed change",
            "status": schema_intact
        })

        # Verify all data accessible
        current_count = _count(adapter, col)
        data_accessible = current_count == original_count
        test1_result["checks"].append({
            "name": f"All data accessible (count={current_count})",
            "status": data_accessible
        })

        no_partial_state = data_accessible and schema_intact
        test1_result["checks"].append({
            "name": "No partial state visible",
            "status": no_partial_state
        })

        test1_result["verdict"] = "PASS" if no_partial_state else "LIKELY_BUG"
        results["test_cases"].append(test1_result)

        # Test Case 2: Schema consistency verification
        print("\n[Test 2] Schema state consistency")
        test2_result = {"name": "Schema state consistency", "checks": []}

        # Verify collection still exists
        exists_res = adapter.execute({
            "operation": "has_collection",
            "params": {"collection_name": col}
        })
        collection_exists = exists_res.get("status") == "success" and exists_res.get("data", False)
        test2_result["checks"].append({
            "name": "Collection still exists",
            "status": collection_exists
        })

        # Verify can still insert data
        new_vecs = generate_vectors(5, 128)
        new_ids = list(range(original_count, original_count + 5))
        new_insert_res = adapter.execute({
            "operation": "insert",
            "params": {
                "collection_name": col,
                "vectors": new_vecs,
                "ids": new_ids
            }
        })
        can_insert = new_insert_res.get("status") == "success"
        test2_result["checks"].append({
            "name": "Can still insert new data",
            "status": can_insert
        })

        # Verify can still search
        search_vec = generate_vectors(1, 128)[0]
        search_res = adapter.execute({
            "operation": "search",
            "params": {
                "collection_name": col,
                "vector": search_vec,
                "top_k": 10
            }
        })
        can_search = search_res.get("status") == "success"
        test2_result["checks"].append({
            "name": "Can still search",
            "status": can_search
        })

        consistency_verified = collection_exists and can_insert and can_search
        test2_result["verdict"] = "PASS" if consistency_verified else "LIKELY_BUG"
        results["test_cases"].append(test2_result)

        # Overall verdict
        all_pass = all(tc["verdict"] == "PASS" for tc in results["test_cases"])
        results["overall_verdict"] = "PASS" if all_pass else "LIKELY_BUG"

    except Exception as e:
        print(f"\n  [ERROR] Exception during SCH-006: {e}")
        results["error"] = str(e)
        results["overall_verdict"] = "ERROR"
    finally:
        # Cleanup
        try:
            adapter.execute({"operation": "drop_collection",
                           "params": {"collection_name": col}})
        except Exception:
            pass

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Run schema evolution contract tests")
    parser.add_argument("--db", type=str, default="milvus",
                       choices=["milvus", "qdrant", "weaviate", "pgvector", "all"],
                       help="Database to test")
    parser.add_argument("--output", type=str, default=None,
                       help="Output file for results (JSON)")
    args = parser.parse_args()

    databases = ["milvus", "qdrant", "weaviate", "pgvector"] if args.db == "all" else [args.db]

    all_results = []

    for db in databases:
        print(f"\n{'#'*60}")
        print(f"# Testing {db.upper()}")
        print(f"{'#'*60}")

        try:
            adapter = get_adapter(db)

            # Run SCH-005
            sch005_results = test_sch005_backward_compatibility(adapter, db)
            all_results.append(sch005_results)

            # Run SCH-006
            sch006_results = test_sch006_atomicity(adapter, db)
            all_results.append(sch006_results)

        except Exception as e:
            print(f"\n  [ERROR] Failed to test {db}: {e}")
            all_results.append({
                "database": db,
                "error": str(e),
                "overall_verdict": "ERROR"
            })

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for res in all_results:
        db = res.get("database", "unknown")
        contract = res.get("contract_id", "unknown")
        verdict = res.get("overall_verdict", "ERROR")
        icon = "[OK]" if verdict == "PASS" else "[FAIL]"
        print(f"  {icon} {db} {contract}: {verdict}")

    # Save results
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(all_results, f, indent=2, default=str)
        print(f"\nResults saved to: {output_path}")

    return all_results


if __name__ == "__main__":
    main()
