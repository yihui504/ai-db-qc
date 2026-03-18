#!/usr/bin/env python3
"""
Boundary Condition Contract Tests for ai-db-qc
==============================================
Tests boundary condition contracts:

  BND-001  Dimension Boundaries     -- vector dimension validation
  BND-002  Top-K Boundaries          -- top_k parameter validation
  BND-003  Metric Type Validation    -- metric_type parameter validation
  BND-004  Collection Name Boundaries -- collection_name validation

Usage:
    python scripts/run_boundary_tests.py --db milvus
    python scripts/run_boundary_tests.py --db qdrant
    python scripts/run_boundary_tests.py --db weaviate
    python scripts/run_boundary_tests.py --db pgvector
    python scripts/run_boundary_tests.py --db all
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


def _has_good_diagnostics(error_msg: str) -> bool:
    """Check if error message has good diagnostics."""
    if not error_msg:
        return False
    # Good: mentions specific parameter, value, or issue
    good_keywords = ["dimension", "top_k", "metric", "collection", "invalid", "required", "must"]
    return any(kw in error_msg.lower() for kw in good_keywords)


# ---------------------------------------------------------------------------
# Test utilities
# ---------------------------------------------------------------------------

def generate_vector(dim: int) -> List[float]:
    """Generate random vector."""
    return np.random.random(dim).tolist()


def generate_vectors(count: int, dim: int) -> List[List[float]]:
    """Generate random vectors."""
    return np.random.random((count, dim)).tolist()


# ---------------------------------------------------------------------------
# BND-001: Dimension Boundaries
# ---------------------------------------------------------------------------

def test_bnd001_dimension_boundaries(adapter: Any, db_name: str) -> Dict[str, Any]:
    """Test BND-001: Dimension Boundaries."""
    print(f"\n{'='*60}")
    print(f"BND-001: Dimension Boundaries - {db_name}")
    print(f"{'='*60}")

    results = {
        "contract_id": "BND-001",
        "database": db_name,
        "test_cases": []
    }

    test_cases = [
        {"name": "Minimum dimension (1)", "dimension": 1, "expected": "accepted"},
        {"name": "Zero dimension", "dimension": 0, "expected": "rejected"},
        {"name": "Negative dimension", "dimension": -1, "expected": "rejected"},
        {"name": "Standard dimension (128)", "dimension": 128, "expected": "accepted"},
        {"name": "Large dimension (4096)", "dimension": 4096, "expected": "accepted"},
        {"name": "Excessive dimension (100000)", "dimension": 100000, "expected": "rejected"},
    ]

    for tc in test_cases:
        print(f"\n[Test] {tc['name']}")
        test_result = {"name": tc["name"], "checks": []}

        col = f"bnd001_dim_{abs(tc['dimension'])}"

        try:
            create_res = adapter.execute({
                "operation": "create_collection",
                "params": {
                    "collection_name": col,
                    "dimension": tc["dimension"],
                    "metric_type": "L2"
                }
            })

            success = create_res.get("status") == "success"
            expected_accepted = tc["expected"] == "accepted"

            if expected_accepted:
                # Should accept
                test_result["checks"].append({
                    "name": f"Accepted (expected)",
                    "status": success
                })
                test_result["verdict"] = "PASS" if success else "TYPE-2 (valid rejected)"
            else:
                # Should reject
                test_result["checks"].append({
                    "name": f"Rejected (expected)",
                    "status": not success
                })
                error_msg = create_res.get("message", "")
                good_diagnostics = _has_good_diagnostics(error_msg)
                test_result["checks"].append({
                    "name": "Good error diagnostics",
                    "status": good_diagnostics,
                    "message": error_msg
                })
                if not success:
                    test_result["verdict"] = "PASS" if good_diagnostics else "TYPE-2 (poor diagnostics)"
                else:
                    test_result["verdict"] = "TYPE-1 (invalid accepted)"

            results["test_cases"].append(test_result)

        except Exception as e:
            test_result["checks"].append({
                "name": "Exception during test",
                "status": False,
                "error": str(e)
            })
            test_result["verdict"] = "ERROR"
            results["test_cases"].append(test_result)

        finally:
            # Cleanup
            try:
                adapter.execute({"operation": "drop_collection",
                               "params": {"collection_name": col}})
            except Exception:
                pass

    # Test vector dimension mismatch
    print(f"\n[Test] Vector dimension mismatch")
    test_result = {"name": "Vector dimension mismatch", "checks": []}
    col = "bnd001_mismatch"

    try:
        # Create collection with dimension 128
        create_res = adapter.execute({
            "operation": "create_collection",
            "params": {
                "collection_name": col,
                "dimension": 128,
                "metric_type": "L2"
            }
        })
        assert create_res.get("status") == "success"

        # Try to insert vector with wrong dimension
        wrong_vec = generate_vector(256)  # 256 instead of 128
        insert_res = adapter.execute({
            "operation": "insert",
            "params": {
                "collection_name": col,
                "vectors": [wrong_vec],
                "ids": [0]
            }
        })

        rejected = insert_res.get("status") != "success"
        test_result["checks"].append({
            "name": "Wrong dimension vector rejected",
            "status": rejected
        })
        error_msg = insert_res.get("message", "")
        good_diagnostics = _has_good_diagnostics(error_msg)
        test_result["checks"].append({
            "name": "Good error diagnostics",
            "status": good_diagnostics,
            "message": error_msg
        })

        if rejected:
            test_result["verdict"] = "PASS" if good_diagnostics else "TYPE-2 (poor diagnostics)"
        else:
            test_result["verdict"] = "TYPE-1 (invalid accepted)"

        results["test_cases"].append(test_result)

    except Exception as e:
        test_result["checks"].append({
            "name": "Exception during test",
            "status": False,
            "error": str(e)
        })
        test_result["verdict"] = "ERROR"
        results["test_cases"].append(test_result)

    finally:
        try:
            adapter.execute({"operation": "drop_collection",
                           "params": {"collection_name": col}})
        except Exception:
            pass

    # Overall verdict
    all_pass = all(tc["verdict"] == "PASS" for tc in results["test_cases"])
    results["overall_verdict"] = "PASS" if all_pass else "BUG"

    return results


# ---------------------------------------------------------------------------
# BND-002: Top-K Boundaries
# ---------------------------------------------------------------------------

def test_bnd002_topk_boundaries(adapter: Any, db_name: str) -> Dict[str, Any]:
    """Test BND-002: Top-K Boundaries."""
    print(f"\n{'='*60}")
    print(f"BND-002: Top-K Boundaries - {db_name}")
    print(f"{'='*60}")

    results = {
        "contract_id": "BND-002",
        "database": db_name,
        "test_cases": []
    }

    col = "bnd002_test"

    try:
        # Setup
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
        vectors = generate_vectors(100, 128)
        insert_res = adapter.execute({
            "operation": "insert",
            "params": {
                "collection_name": col,
                "vectors": vectors,
                "ids": list(range(100))
            }
        })

        # Build and load index
        adapter.execute({"operation": "build_index",
                        "params": {"collection_name": col, "index_type": "IVF_FLAT"}})
        adapter.execute({"operation": "load",
                        "params": {"collection_name": col}})

        query_vec = generate_vector(128)

        test_cases = [
            {"name": "Top-K = 0", "top_k": 0, "expected": "empty or rejected"},
            {"name": "Top-K = 1", "top_k": 1, "expected": "1 result"},
            {"name": "Top-K = 10", "top_k": 10, "expected": "10 results"},
            {"name": "Top-K = 100 (equal to collection size)", "top_k": 100, "expected": "100 results"},
            {"name": "Top-K = 200 (greater than collection)", "top_k": 200, "expected": "100 results"},
            {"name": "Negative top-K", "top_k": -1, "expected": "rejected"},
        ]

        for tc in test_cases:
            print(f"\n[Test] {tc['name']}")
            test_result = {"name": tc["name"], "checks": []}

            try:
                search_res = adapter.execute({
                    "operation": "search",
                    "params": {
                        "collection_name": col,
                        "vector": query_vec,
                        "top_k": tc["top_k"]
                    }
                })

                success = search_res.get("status") == "success"

                if tc["expected"] == "rejected":
                    test_result["checks"].append({
                        "name": "Rejected (expected)",
                        "status": not success
                    })
                    error_msg = search_res.get("message", "")
                    good_diagnostics = _has_good_diagnostics(error_msg)
                    test_result["checks"].append({
                        "name": "Good error diagnostics",
                        "status": good_diagnostics
                    })
                    if not success:
                        test_result["verdict"] = "PASS" if good_diagnostics else "TYPE-2"
                    else:
                        test_result["verdict"] = "TYPE-1"
                else:
                    test_result["checks"].append({
                        "name": "Search succeeded",
                        "status": success
                    })
                    if success:
                        result_count = len(search_res.get("data", []))
                        expected_count = int(tc["expected"].split()[0])
                        test_result["checks"].append({
                            "name": f"Returned {result_count} results (expected ~{expected_count})",
                            "status": result_count <= tc["top_k"]
                        })
                        # Oracle: result count <= top_k
                        count_valid = result_count <= tc["top_k"]
                        test_result["checks"].append({
                            "name": f"Result count ({result_count}) <= top_k ({tc['top_k']})",
                            "status": count_valid
                        })
                        test_result["verdict"] = "PASS" if count_valid else "TYPE-4 (count > top_k)"
                    else:
                        test_result["verdict"] = "TYPE-3 (crash)"

                results["test_cases"].append(test_result)

            except Exception as e:
                test_result["checks"].append({
                    "name": "Exception during test",
                    "status": False,
                    "error": str(e)
                })
                test_result["verdict"] = "TYPE-3"
                results["test_cases"].append(test_result)

        # Overall verdict
        all_pass = all(tc["verdict"] == "PASS" for tc in results["test_cases"])
        results["overall_verdict"] = "PASS" if all_pass else "BUG"

    except Exception as e:
        print(f"\n  [ERROR] Exception during BND-002: {e}")
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
# BND-003: Metric Type Validation
# ---------------------------------------------------------------------------

def test_bnd003_metric_validation(adapter: Any, db_name: str) -> Dict[str, Any]:
    """Test BND-003: Metric Type Validation."""
    print(f"\n{'='*60}")
    print(f"BND-003: Metric Type Validation - {db_name}")
    print(f"{'='*60}")

    results = {
        "contract_id": "BND-003",
        "database": db_name,
        "test_cases": []
    }

    test_cases = [
        {"name": "L2 metric", "metric": "L2", "expected": "accepted"},
        {"name": "IP metric", "metric": "IP", "expected": "accepted"},
        {"name": "COSINE metric", "metric": "COSINE", "expected": "accepted"},
        {"name": "Lowercase 'l2'", "metric": "l2", "expected": "consistent"},
        {"name": "Lowercase 'ip'", "metric": "ip", "expected": "consistent"},
        {"name": "Lowercase 'cosine'", "metric": "cosine", "expected": "consistent"},
        {"name": "Unsupported metric 'MANHATTAN'", "metric": "MANHATTAN", "expected": "rejected"},
        {"name": "Empty metric", "metric": "", "expected": "rejected"},
    ]

    for tc in test_cases:
        print(f"\n[Test] {tc['name']}")
        test_result = {"name": tc["name"], "checks": []}
        col = f"bnd003_{tc['metric'].lower().replace('_', '')}"

        try:
            create_res = adapter.execute({
                "operation": "create_collection",
                "params": {
                    "collection_name": col,
                    "dimension": 128,
                    "metric_type": tc["metric"] if tc["metric"] else None
                }
            })

            success = create_res.get("status") == "success"

            if tc["expected"] == "accepted":
                test_result["checks"].append({
                    "name": "Accepted (expected)",
                    "status": success
                })
                test_result["verdict"] = "PASS" if success else "TYPE-2"
            elif tc["expected"] == "consistent":
                test_result["checks"].append({
                    "name": f"Handled consistently (result: {'accepted' if success else 'rejected'})",
                    "status": True
                })
                test_result["verdict"] = "PASS"  # Consistency is what matters
            else:
                # Should reject
                test_result["checks"].append({
                    "name": "Rejected (expected)",
                    "status": not success
                })
                error_msg = create_res.get("message", "")
                good_diagnostics = _has_good_diagnostics(error_msg)
                test_result["checks"].append({
                    "name": "Good error diagnostics",
                    "status": good_diagnostics,
                    "message": error_msg
                })
                if not success:
                    test_result["verdict"] = "PASS" if good_diagnostics else "TYPE-2"
                else:
                    test_result["verdict"] = "TYPE-1"

            results["test_cases"].append(test_result)

        except Exception as e:
            test_result["checks"].append({
                "name": "Exception during test",
                "status": False,
                "error": str(e)
            })
            test_result["verdict"] = "ERROR"
            results["test_cases"].append(test_result)

        finally:
            # Cleanup
            try:
                adapter.execute({"operation": "drop_collection",
                               "params": {"collection_name": col}})
            except Exception:
                pass

    # Overall verdict
    all_pass = all(tc["verdict"] == "PASS" for tc in results["test_cases"])
    results["overall_verdict"] = "PASS" if all_pass else "BUG"

    return results


# ---------------------------------------------------------------------------
# BND-004: Collection Name Boundaries
# ---------------------------------------------------------------------------

def test_bnd004_name_boundaries(adapter: Any, db_name: str) -> Dict[str, Any]:
    """Test BND-004: Collection Name Boundaries."""
    print(f"\n{'='*60}")
    print(f"BND-004: Collection Name Boundaries - {db_name}")
    print(f"{'='*60}")

    results = {
        "contract_id": "BND-004",
        "database": db_name,
        "test_cases": []
    }

    test_cases = [
        {"name": "Valid name 'test_collection'", "name": "test_collection", "expected": "accepted"},
        {"name": "Name with underscores 'my_test_col'", "name": "my_test_col", "expected": "accepted"},
        {"name": "Empty name", "name": "", "expected": "rejected"},
        {"name": "Name with spaces 'my collection'", "name": "my collection", "expected": "rejected"},
        {"name": "Name with special chars 'test/name'", "name": "test/name", "expected": "rejected"},
        {"name": "Name starting with number '123collection'", "name": "123collection", "expected": "varies"},
        {"name": "Reserved name 'system'", "name": "system", "expected": "rejected_or_warned"},
    ]

    for tc in test_cases:
        print(f"\n[Test] {tc['name']}")
        test_result = {"name": tc["name"], "checks": []}

        try:
            create_res = adapter.execute({
                "operation": "create_collection",
                "params": {
                    "collection_name": tc["name"],
                    "dimension": 128,
                    "metric_type": "L2"
                }
            })

            success = create_res.get("status") == "success"

            if tc["expected"] == "accepted":
                test_result["checks"].append({
                    "name": "Accepted (expected)",
                    "status": success
                })
                test_result["verdict"] = "PASS" if success else "TYPE-2"
                # Cleanup if created
                if success:
                    try:
                        adapter.execute({"operation": "drop_collection",
                                       "params": {"collection_name": tc["name"]}})
                    except Exception:
                        pass
            elif tc["expected"] == "varies":
                test_result["checks"].append({
                    "name": f"Handled as {'accepted' if success else 'rejected'}",
                    "status": True
                })
                test_result["verdict"] = "PASS"
                if success:
                    try:
                        adapter.execute({"operation": "drop_collection",
                                       "params": {"collection_name": tc["name"]}})
                    except Exception:
                        pass
            else:
                # Should reject
                test_result["checks"].append({
                    "name": "Rejected (expected)",
                    "status": not success
                })
                error_msg = create_res.get("message", "")
                good_diagnostics = _has_good_diagnostics(error_msg)
                test_result["checks"].append({
                    "name": "Good error diagnostics",
                    "status": good_diagnostics,
                    "message": error_msg
                })
                if not success:
                    test_result["verdict"] = "PASS" if good_diagnostics else "TYPE-2"
                else:
                    test_result["verdict"] = "TYPE-1"
                    # Cleanup
                    try:
                        adapter.execute({"operation": "drop_collection",
                                       "params": {"collection_name": tc["name"]}})
                    except Exception:
                        pass

            results["test_cases"].append(test_result)

        except Exception as e:
            test_result["checks"].append({
                "name": "Exception during test",
                "status": False,
                "error": str(e)
            })
            test_result["verdict"] = "ERROR"
            results["test_cases"].append(test_result)

    # Test duplicate name
    print(f"\n[Test] Duplicate collection name")
    test_result = {"name": "Duplicate collection name", "checks": []}
    col = "bnd004_duplicate"

    try:
        # Create first collection
        create1_res = adapter.execute({
            "operation": "create_collection",
            "params": {
                "collection_name": col,
                "dimension": 128,
                "metric_type": "L2"
            }
        })
        assert create1_res.get("status") == "success"

        # Try to create duplicate
        create2_res = adapter.execute({
            "operation": "create_collection",
            "params": {
                "collection_name": col,
                "dimension": 128,
                "metric_type": "L2"
            }
        })

        rejected = create2_res.get("status") != "success"
        test_result["checks"].append({
            "name": "Duplicate name rejected",
            "status": rejected
        })
        error_msg = create2_res.get("message", "")
        good_diagnostics = _has_good_diagnostics(error_msg)
        test_result["checks"].append({
            "name": "Good error diagnostics",
            "status": good_diagnostics,
            "message": error_msg
        })

        if rejected:
            test_result["verdict"] = "PASS" if good_diagnostics else "TYPE-2"
        else:
            test_result["verdict"] = "TYPE-1"

        results["test_cases"].append(test_result)

    except Exception as e:
        test_result["checks"].append({
            "name": "Exception during test",
            "status": False,
            "error": str(e)
        })
        test_result["verdict"] = "ERROR"
        results["test_cases"].append(test_result)

    finally:
        # Cleanup
        try:
            adapter.execute({"operation": "drop_collection",
                           "params": {"collection_name": col}})
        except Exception:
            pass

    # Overall verdict
    all_pass = all(tc["verdict"] == "PASS" for tc in results["test_cases"])
    results["overall_verdict"] = "PASS" if all_pass else "BUG"

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Run boundary condition contract tests")
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

            # Run BND-001
            bnd001_results = test_bnd001_dimension_boundaries(adapter, db)
            all_results.append(bnd001_results)

            # Run BND-002
            bnd002_results = test_bnd002_topk_boundaries(adapter, db)
            all_results.append(bnd002_results)

            # Run BND-003
            bnd003_results = test_bnd003_metric_validation(adapter, db)
            all_results.append(bnd003_results)

            # Run BND-004
            bnd004_results = test_bnd004_name_boundaries(adapter, db)
            all_results.append(bnd004_results)

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
