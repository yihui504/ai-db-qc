"""R4 Lifecycle Contract Cross-Database Testing.

This script runs R4 lifecycle contract tests across multiple databases
(Milvus, Qdrant, Weaviate, pgvector) to identify behavioral differences
in sequence semantics, state management, and API consistency.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.run_phase5_3_eval import create_adapter_with_fallback, VariantFlags
from oracles.differential import R4LifecycleOracle, DifferenceCategory
from pipeline.executor import Executor
from pipeline.preconditions import PreconditionEvaluator
from pipeline.triage import Triage
from contracts.core.loader import get_default_contract
from contracts.db_profiles.loader import load_profile
from evidence.writer import EvidenceWriter
from schemas.common import ObservedOutcome, OperationType


# R4 Test Cases - 8 Semantic Properties
R4_TEST_CASES = [
    {
        "case_id": "R4-001",
        "name": "Post-Drop Rejection",
        "description": "Collections, once dropped, must no longer exist and must reject all subsequent operations",
        "sequence": [
            {"operation": "create_collection", "params": {"collection_name": "r4_001_test", "dimension": 128}},
            {"operation": "insert", "params": {"collection_name": "r4_001_test", "vectors": [[0.1]*128]}},
            {"operation": "drop_collection", "params": {"collection_name": "r4_001_test"}},
            {"operation": "search", "params": {"collection_name": "r4_001_test", "vector": [0.1]*128, "top_k": 10}, "expected": "failure"}
        ]
    },
    {
        "case_id": "R4-002",
        "name": "Deleted Entity Visibility",
        "description": "Entities that have been explicitly deleted must not appear in subsequent search results",
        "sequence": [
            {"operation": "create_collection", "params": {"collection_name": "r4_002_test", "dimension": 128}},
            {"operation": "insert", "params": {"collection_name": "r4_002_test", "vectors": [[0.1]*128, [0.2]*128], "ids": ["id_1", "id_2"]}},
            {"operation": "load", "params": {"collection_name": "r4_002_test"}},
            {"operation": "delete", "params": {"collection_name": "r4_002_test", "ids": ["id_1"]}},
            {"operation": "search", "params": {"collection_name": "r4_002_test", "vector": [0.1]*128, "top_k": 10}, "check": "id_1_not_in_results"}
        ]
    },
    {
        "case_id": "R4-003",
        "name": "Delete Idempotency",
        "description": "Deleting the same entity multiple times should not cause errors",
        "sequence": [
            {"operation": "create_collection", "params": {"collection_name": "r4_003_test", "dimension": 128}},
            {"operation": "insert", "params": {"collection_name": "r4_003_test", "vectors": [[0.1]*128], "ids": ["id_1"]}},
            {"operation": "delete", "params": {"collection_name": "r4_003_test", "ids": ["id_1"]}},
            {"operation": "delete", "params": {"collection_name": "r4_003_test", "ids": ["id_1"]}, "expected": "success_or_noop"}
        ]
    },
    {
        "case_id": "R4-004",
        "name": "Index-Independent Search",
        "description": "Search should work regardless of index state (with different performance)",
        "sequence": [
            {"operation": "create_collection", "params": {"collection_name": "r4_004_test", "dimension": 128}},
            {"operation": "insert", "params": {"collection_name": "r4_004_test", "vectors": [[0.1]*128, [0.2]*128]}},
            {"operation": "load", "params": {"collection_name": "r4_004_test"}},
            {"operation": "search", "params": {"collection_name": "r4_004_test", "vector": [0.1]*128, "top_k": 10}, "expected": "success"}
        ]
    },
    {
        "case_id": "R4-005",
        "name": "Load-State Enforcement",
        "description": "Search requires loaded collection; unload/release blocks search",
        "sequence": [
            {"operation": "create_collection", "params": {"collection_name": "r4_005_test", "dimension": 128}},
            {"operation": "insert", "params": {"collection_name": "r4_005_test", "vectors": [[0.1]*128]}},
            {"operation": "build_index", "params": {"collection_name": "r4_005_test", "index_type": "HNSW"}},
            {"operation": "load_index", "params": {"collection_name": "r4_005_test"}},
            {"operation": "search", "params": {"collection_name": "r4_005_test", "vector": [0.1]*128, "top_k": 10}, "expected": "success"},
            {"operation": "release", "params": {"collection_name": "r4_005_test"}},
            {"operation": "search", "params": {"collection_name": "r4_005_test", "vector": [0.1]*128, "top_k": 10}, "expected": "failure"}
        ]
    },
    {
        "case_id": "R4-006",
        "name": "Empty Collection Handling",
        "description": "Operations on empty collections should be handled gracefully",
        "sequence": [
            {"operation": "create_collection", "params": {"collection_name": "r4_006_test", "dimension": 128}},
            {"operation": "build_index", "params": {"collection_name": "r4_006_test", "index_type": "HNSW"}},
            {"operation": "load", "params": {"collection_name": "r4_006_test"}},
            {"operation": "search", "params": {"collection_name": "r4_006_test", "vector": [0.1]*128, "top_k": 10}, "expected": "success_or_empty"},
            {"operation": "count", "params": {"collection_name": "r4_006_test"}, "expected": "zero"}
        ]
    },
    {
        "case_id": "R4-007",
        "name": "Non-Existent Delete Tolerance",
        "description": "Deleting non-existent entities should not cause errors",
        "sequence": [
            {"operation": "create_collection", "params": {"collection_name": "r4_007_test", "dimension": 128}},
            {"operation": "delete", "params": {"collection_name": "r4_007_test", "ids": ["non_existent_id"]}, "expected": "success_or_noop"}
        ]
    },
    {
        "case_id": "R4-008",
        "name": "Collection Creation Idempotency",
        "description": "Creating a collection that already exists should be handled consistently",
        "sequence": [
            {"operation": "create_collection", "params": {"collection_name": "r4_008_test", "dimension": 128}},
            {"operation": "create_collection", "params": {"collection_name": "r4_008_test", "dimension": 128}, "expected": "idempotent_behavior"}
        ]
    }
]


# Database configurations
DB_CONFIGS = {
    "mock": {
        "profile": "contracts/db_profiles/milvus_profile.yaml",
        "adapter": "mock",
        "mock": True
    },
    "milvus": {
        "profile": "contracts/db_profiles/milvus_profile.yaml",
        "adapter": "milvus",
        "default_host": "localhost",
        "default_port": 19530
    },
    "qdrant": {
        "profile": "contracts/db_profiles/qdrant_profile.yaml",
        "adapter": "qdrant",
        "default_url": "http://localhost:6333"
    },
    "weaviate": {
        "profile": "contracts/db_profiles/weaviate_profile.yaml",
        "adapter": "weaviate",
        "default_host": "localhost",
        "default_port": 8080
    },
    "pgvector": {
        "profile": "contracts/db_profiles/pgvector_profile.yaml",
        "adapter": "pgvector",
        "default_container": "pgvector",
        "default_db": "vectordb"
    }
}


def execute_sequence_on_database(
    db_name: str,
    sequence: List[Dict[str, Any]],
    require_real: bool = False,
    **adapter_kwargs
) -> Dict[str, Any]:
    """Execute a test sequence on a single database.
    
    Args:
        db_name: Database name
        sequence: Test sequence steps
        require_real: Require real database connection
        **adapter_kwargs: Adapter connection parameters
        
    Returns:
        Execution results and observations
    """
    db_config = DB_CONFIGS.get(db_name)
    if not db_config:
        return {"error": f"Unknown database: {db_name}"}
    
    # Create adapter
    adapter, adapter_flags, adapter_info = create_adapter_with_fallback(
        db_config["adapter"],
        adapter_kwargs.get("host", db_config.get("default_host", "localhost")),
        adapter_kwargs.get("port", db_config.get("default_port", 19530)),
        require_real=require_real,
        qdrant_url=adapter_kwargs.get("qdrant_url", db_config.get("default_url", "http://localhost:6333")),
        weaviate_host=adapter_kwargs.get("weaviate_host", db_config.get("default_host", "localhost")),
        weaviate_port=adapter_kwargs.get("weaviate_port", db_config.get("default_port", 8080)),
        pgvector_container=adapter_kwargs.get("pgvector_container", db_config.get("default_container", "pgvector")),
        pgvector_db=adapter_kwargs.get("pgvector_db", db_config.get("default_db", "vectordb")),
    )
    
    if adapter_info.get("adapter_fallback"):
        return {
            "error": f"Adapter fallback for {db_name}",
            "fallback_reason": adapter_info.get("fallback_reason")
        }
    
    # Load contract and profile
    try:
        contract = get_default_contract()
        profile = load_profile(db_config["profile"])
    except Exception as e:
        return {"error": f"Failed to load contract/profile: {e}"}
    
    # Set up runtime context
    runtime_context = {
        "collections": [],
        "indexed_collections": [],
        "loaded_collections": [],
        "connected": True,
        "supported_features": ["IVF_FLAT", "HNSW"]
    }
    
    precond = PreconditionEvaluator(contract, profile, runtime_context)
    executor = Executor(adapter, precond, oracles=[])
    
    # Execute sequence
    step_results = []
    for i, step in enumerate(sequence):
        operation = step["operation"]
        params = step.get("params", {})
        expected = step.get("expected", "success")
        
        try:
            # Execute operation
            request = {"operation": operation, "params": params}
            response = adapter.execute(request)
            
            success = response.get("status") == "success"
            error = response.get("error") if not success else None
            
            step_result = {
                "step": i + 1,
                "operation": operation,
                "params": params,
                "expected": expected,
                "success": success,
                "error": error,
                "response": response
            }
            
            # Update runtime context based on operation
            if success:
                if operation == "create_collection":
                    runtime_context["collections"].append(params.get("collection_name"))
                elif operation == "drop_collection":
                    coll = params.get("collection_name")
                    if coll in runtime_context["collections"]:
                        runtime_context["collections"].remove(coll)
                    if coll in runtime_context["indexed_collections"]:
                        runtime_context["indexed_collections"].remove(coll)
                    if coll in runtime_context["loaded_collections"]:
                        runtime_context["loaded_collections"].remove(coll)
                elif operation == "build_index":
                    runtime_context["indexed_collections"].append(params.get("collection_name"))
                elif operation == "load_index":
                    runtime_context["loaded_collections"].append(params.get("collection_name"))
                elif operation == "release":
                    coll = params.get("collection_name")
                    if coll in runtime_context["loaded_collections"]:
                        runtime_context["loaded_collections"].remove(coll)
            
        except Exception as e:
            step_result = {
                "step": i + 1,
                "operation": operation,
                "params": params,
                "expected": expected,
                "success": False,
                "error": str(e),
                "response": {}
            }
        
        step_results.append(step_result)
    
    # Cleanup
    try:
        adapter.close()
    except Exception:
        pass
    
    return {
        "database": db_name,
        "steps": step_results,
        "total_steps": len(step_results),
        "success_count": sum(1 for s in step_results if s["success"]),
        "failure_count": sum(1 for s in step_results if not s["success"])
    }


def run_r4_cross_db(
    databases: List[str],
    test_cases: Optional[List[str]] = None,
    run_tag: str = "r4-cross-db",
    output_dir: str = "runs/r4_cross_db",
    require_real: bool = False,
    **adapter_kwargs
) -> Dict[str, Any]:
    """Run R4 lifecycle contract tests across multiple databases.
    
    Args:
        databases: List of databases to test
        test_cases: Optional list of specific test case IDs to run
        run_tag: Run identifier
        output_dir: Output directory
        require_real: Require real database connections
        **adapter_kwargs: Adapter connection parameters
        
    Returns:
        Aggregated results from all tests
    """
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_id = f"r4-cross-db-{run_tag}-{timestamp}"
    
    # Filter test cases if specified
    cases_to_run = R4_TEST_CASES
    if test_cases:
        cases_to_run = [c for c in R4_TEST_CASES if c["case_id"] in test_cases]
    
    results = {
        "run_id": run_id,
        "timestamp": timestamp,
        "databases": databases,
        "test_cases": [],
        "summary": {}
    }
    
    print(f"\n{'='*70}")
    print(f"R4 Cross-Database Lifecycle Testing")
    print(f"Run ID: {run_id}")
    print(f"Databases: {', '.join(databases)}")
    print(f"Test Cases: {len(cases_to_run)}")
    print(f"{'='*70}\n")
    
    for test_case in cases_to_run:
        case_id = test_case["case_id"]
        case_name = test_case["name"]
        
        print(f"\n[Testing] {case_id}: {case_name}")
        print(f"  Description: {test_case['description']}")
        
        case_result = {
            "case_id": case_id,
            "name": case_name,
            "description": test_case["description"],
            "database_results": []
        }
        
        # Execute on each database
        for db_name in databases:
            print(f"  - Executing on {db_name}...")
            
            db_result = execute_sequence_on_database(
                db_name=db_name,
                sequence=test_case["sequence"],
                require_real=require_real,
                **adapter_kwargs
            )
            
            case_result["database_results"].append(db_result)
            
            if "error" in db_result:
                print(f"    ERROR: {db_result['error']}")
            else:
                print(f"    Success: {db_result['success_count']}/{db_result['total_steps']}")
        
        # Compare results across databases
        successful_results = [r for r in case_result["database_results"] if "error" not in r]
        
        if len(successful_results) >= 2:
            # Compare behaviors
            comparison = compare_behaviors(successful_results)
            case_result["comparison"] = comparison
            print(f"  Comparison: {comparison.get('category', 'N/A')}")
        
        results["test_cases"].append(case_result)
    
    # Generate summary
    total_cases = len(results["test_cases"])
    cases_with_differences = sum(
        1 for c in results["test_cases"]
        if c.get("comparison", {}).get("category") != "consistent"
    )
    
    results["summary"] = {
        "total_cases": total_cases,
        "cases_with_differences": cases_with_differences,
        "databases_tested": len(databases),
        "consistent_cases": total_cases - cases_with_differences
    }
    
    # Write results
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    report_file = output_path / f"{run_id}_report.json"
    with open(report_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    # Print summary
    print(f"\n{'='*70}")
    print("R4 Cross-Database Testing Summary")
    print(f"{'='*70}")
    print(f"Total test cases: {total_cases}")
    print(f"Consistent across databases: {results['summary']['consistent_cases']}")
    print(f"Cases with differences: {cases_with_differences}")
    print(f"Report saved: {report_file}")
    
    return results


def compare_behaviors(database_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compare behaviors across databases.
    
    Args:
        database_results: Results from each database
        
    Returns:
        Comparison analysis
    """
    if len(database_results) < 2:
        return {"category": "insufficient_data", "reason": "Need at least 2 databases"}
    
    # Compare step-by-step
    step_count = database_results[0]["total_steps"]
    differences = []
    
    for step_idx in range(step_count):
        step_outcomes = {}
        for db_result in database_results:
            db_name = db_result["database"]
            if step_idx < len(db_result["steps"]):
                step = db_result["steps"][step_idx]
                step_outcomes[db_name] = step["success"]
        
        # Check if all databases agree on this step
        outcomes = list(step_outcomes.values())
        if not all(o == outcomes[0] for o in outcomes):
            differences.append({
                "step": step_idx + 1,
                "outcomes": step_outcomes
            })
    
    if not differences:
        return {
            "category": "consistent",
            "description": "All databases behave consistently across all steps"
        }
    
    # Classify differences
    # For now, mark as allowed difference (needs more sophisticated analysis)
    return {
        "category": "allowed_difference",
        "description": "Databases show behavioral differences in some steps",
        "differences": differences,
        "note": "Differences may be due to architectural variations"
    }


def main():
    parser = argparse.ArgumentParser(
        description="Run R4 lifecycle contract tests across multiple databases"
    )
    parser.add_argument(
        "--databases",
        default="milvus,qdrant,weaviate,pgvector",
        help="Comma-separated list of databases to test"
    )
    parser.add_argument(
        "--test-cases",
        help="Comma-separated list of test case IDs (default: all)"
    )
    parser.add_argument(
        "--run-tag",
        default="r4-cross-db",
        help="Run identifier tag"
    )
    parser.add_argument(
        "--output-dir",
        default="runs/r4_cross_db",
        help="Output directory"
    )
    parser.add_argument(
        "--require-real",
        action="store_true",
        help="Require real database connections"
    )
    parser.add_argument(
        "--qdrant-url",
        default="http://localhost:6333",
        help="Qdrant URL"
    )
    parser.add_argument(
        "--weaviate-host",
        default="localhost",
        help="Weaviate host"
    )
    parser.add_argument(
        "--weaviate-port",
        type=int,
        default=8080,
        help="Weaviate port"
    )
    parser.add_argument(
        "--pgvector-container",
        default="pgvector",
        help="pgvector Docker container name"
    )
    parser.add_argument(
        "--pgvector-db",
        default="vectordb",
        help="pgvector database name"
    )
    
    args = parser.parse_args()
    
    databases = [db.strip() for db in args.databases.split(",")]
    test_cases = None
    if args.test_cases:
        test_cases = [tc.strip() for tc in args.test_cases.split(",")]
    
    run_r4_cross_db(
        databases=databases,
        test_cases=test_cases,
        run_tag=args.run_tag,
        output_dir=args.output_dir,
        require_real=args.require_real,
        qdrant_url=args.qdrant_url,
        weaviate_host=args.weaviate_host,
        weaviate_port=args.weaviate_port,
        pgvector_container=args.pgvector_container,
        pgvector_db=args.pgvector_db
    )


if __name__ == "__main__":
    main()
