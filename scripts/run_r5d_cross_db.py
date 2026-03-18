"""R5D Schema Evolution Contract Cross-Database Testing.

This script runs R5D schema evolution contract tests across multiple databases
to validate schema semantics, data preservation, and query compatibility.
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
from contracts.core.loader import get_default_contract
from contracts.db_profiles.loader import load_profile
from pipeline.preconditions import PreconditionEvaluator
from pipeline.executor import Executor


# R5D Schema Evolution Test Cases
R5D_TEST_CASES = [
    {
        "case_id": "R5D-001",
        "name": "Metadata Accuracy",
        "description": "Collection metadata must accurately reflect actual schema",
        "sequence": [
            {"operation": "create_collection", "params": {"collection_name": "r5d_001_v1", "dimension": 128}},
            {"operation": "describe_collection", "params": {"collection_name": "r5d_001_v1"}, "record": "v1_metadata"},
            {"operation": "insert", "params": {"collection_name": "r5d_001_v1", "vectors": [[0.1]*128]}},
            {"operation": "describe_collection", "params": {"collection_name": "r5d_001_v1"}, "record": "v1_metadata_with_data"}
        ],
        "validation": "metadata_accuracy"
    },
    {
        "case_id": "R5D-002",
        "name": "Data Preservation After Schema Extension",
        "description": "Creating collection_v2 with extended schema must not affect data in collection_v1",
        "sequence": [
            {"operation": "create_collection", "params": {"collection_name": "r5d_002_v1", "dimension": 128}},
            {"operation": "insert", "params": {"collection_name": "r5d_002_v1", "vectors": [[0.1]*128, [0.2]*128]}},
            {"operation": "count", "params": {"collection_name": "r5d_002_v1"}, "record": "v1_count_before"},
            {"operation": "create_collection", "params": {"collection_name": "r5d_002_v2", "dimension": 128}},
            {"operation": "insert", "params": {"collection_name": "r5d_002_v2", "vectors": [[0.3]*128]}},
            {"operation": "count", "params": {"collection_name": "r5d_002_v1"}, "record": "v1_count_after"},
            {"operation": "count", "params": {"collection_name": "r5d_002_v2"}, "record": "v2_count"}
        ],
        "validation": "data_preservation"
    },
    {
        "case_id": "R5D-003",
        "name": "Backward Query Compatibility",
        "description": "Queries on collection_v1 must continue working after collection_v2 creation",
        "sequence": [
            {"operation": "create_collection", "params": {"collection_name": "r5d_003_v1", "dimension": 128}},
            {"operation": "insert", "params": {"collection_name": "r5d_003_v1", "vectors": [[0.1]*128, [0.2]*128]}},
            {"operation": "build_index", "params": {"collection_name": "r5d_003_v1", "index_type": "HNSW"}},
            {"operation": "load_index", "params": {"collection_name": "r5d_003_v1"}},
            {"operation": "search", "params": {"collection_name": "r5d_003_v1", "vector": [0.1]*128, "top_k": 10}, "record": "v1_search_before"},
            {"operation": "create_collection", "params": {"collection_name": "r5d_003_v2", "dimension": 128}},
            {"operation": "search", "params": {"collection_name": "r5d_003_v1", "vector": [0.1]*128, "top_k": 10}, "record": "v1_search_after"}
        ],
        "validation": "query_compatibility"
    },
    {
        "case_id": "R5D-004",
        "name": "Metadata Reflection After Change",
        "description": "After creating collection_v2, collection_v1 metadata must remain accurate",
        "sequence": [
            {"operation": "create_collection", "params": {"collection_name": "r5d_004_v1", "dimension": 128}},
            {"operation": "describe_collection", "params": {"collection_name": "r5d_004_v1"}, "record": "v1_metadata_initial"},
            {"operation": "create_collection", "params": {"collection_name": "r5d_004_v2", "dimension": 256}},
            {"operation": "describe_collection", "params": {"collection_name": "r5d_004_v1"}, "record": "v1_metadata_final"}
        ],
        "validation": "metadata_stability"
    },
    {
        "case_id": "R5D-005",
        "name": "Cross-Collection Isolation",
        "description": "Operations on one collection should not affect another collection",
        "sequence": [
            {"operation": "create_collection", "params": {"collection_name": "r5d_005_a", "dimension": 128}},
            {"operation": "create_collection", "params": {"collection_name": "r5d_005_b", "dimension": 128}},
            {"operation": "insert", "params": {"collection_name": "r5d_005_a", "vectors": [[0.1]*128]}},
            {"operation": "count", "params": {"collection_name": "r5d_005_a"}, "record": "count_a"},
            {"operation": "count", "params": {"collection_name": "r5d_005_b"}, "record": "count_b"},
            {"operation": "insert", "params": {"collection_name": "r5d_005_b", "vectors": [[0.2]*128]}},
            {"operation": "count", "params": {"collection_name": "r5d_005_a"}, "record": "count_a_after"},
            {"operation": "count", "params": {"collection_name": "r5d_005_b"}, "record": "count_b_after"}
        ],
        "validation": "cross_collection_isolation"
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


def execute_r5d_sequence(
    db_name: str,
    sequence: List[Dict[str, Any]],
    require_real: bool = False,
    **adapter_kwargs
) -> Dict[str, Any]:
    """Execute R5D test sequence on a single database.
    
    Args:
        db_name: Database name
        sequence: Test sequence steps
        require_real: Require real database connection
        **adapter_kwargs: Adapter connection parameters
        
    Returns:
        Execution results with recorded observations
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
    recorded_observations = {}
    
    for i, step in enumerate(sequence):
        operation = step["operation"]
        params = step.get("params", {})
        record_key = step.get("record")
        
        # Handle describe_collection - may not be supported by all adapters
        if operation == "describe_collection":
            try:
                # Try to get collection info
                request = {"operation": "describe_collection", "params": params}
                response = adapter.execute(request)
                
                success = response.get("status") == "success"
                
                step_result = {
                    "step": i + 1,
                    "operation": operation,
                    "params": params,
                    "success": success,
                    "response": response
                }
                
                if record_key and success:
                    recorded_observations[record_key] = {
                        "dimension": response.get("dimension"),
                        "fields": response.get("fields", []),
                        "entity_count": response.get("entity_count", 0)
                    }
                    
            except Exception as e:
                # describe_collection may not be supported
                step_result = {
                    "step": i + 1,
                    "operation": operation,
                    "params": params,
                    "success": False,
                    "error": str(e),
                    "note": "describe_collection may not be supported by this adapter"
                }
                
                if record_key:
                    recorded_observations[record_key] = {"error": "not_supported"}
        
        else:
            # Standard operation execution
            try:
                request = {"operation": operation, "params": params}
                response = adapter.execute(request)
                
                success = response.get("status") == "success"
                error = response.get("error") if not success else None
                
                step_result = {
                    "step": i + 1,
                    "operation": operation,
                    "params": params,
                    "success": success,
                    "error": error,
                    "response": response
                }
                
                # Record observation if specified
                if record_key and success:
                    if operation == "count":
                        recorded_observations[record_key] = response.get("count", 0)
                    elif operation == "search":
                        data = response.get("data", [])
                        recorded_observations[record_key] = {
                            "count": len(data),
                            "ids": [item.get("id") for item in data if isinstance(item, dict)]
                        }
                
                # Update runtime context
                if success:
                    if operation == "create_collection":
                        runtime_context["collections"].append(params.get("collection_name"))
                    elif operation == "drop_collection":
                        coll = params.get("collection_name")
                        for lst in [runtime_context["collections"], runtime_context["indexed_collections"], runtime_context["loaded_collections"]]:
                            if coll in lst:
                                lst.remove(coll)
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
        "recorded_observations": recorded_observations,
        "total_steps": len(step_results),
        "success_count": sum(1 for s in step_results if s["success"]),
        "failure_count": sum(1 for s in step_results if not s["success"])
    }


def validate_r5d_results(
    case_id: str,
    validation_type: str,
    database_results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Validate R5D test results across databases.
    
    Args:
        case_id: Test case ID
        validation_type: Type of validation to perform
        database_results: Results from each database
        
    Returns:
        Validation results
    """
    if validation_type == "data_preservation":
        # Validate that v1 data is preserved after v2 creation
        validations = {}
        for db_result in database_results:
            db_name = db_result["database"]
            obs = db_result.get("recorded_observations", {})
            
            v1_before = obs.get("v1_count_before")
            v1_after = obs.get("v1_count_after")
            v2_count = obs.get("v2_count")
            
            validations[db_name] = {
                "v1_preserved": v1_before == v1_after if v1_before is not None and v1_after is not None else None,
                "v1_count_before": v1_before,
                "v1_count_after": v1_after,
                "v2_count": v2_count
            }
        
        return {
            "validation_type": validation_type,
            "validations": validations,
            "note": "v1 data should be preserved (v1_count_before == v1_count_after)"
        }
    
    elif validation_type == "query_compatibility":
        # Validate query compatibility across schema versions
        compat_results = {}
        for db_result in database_results:
            db_name = db_result["database"]
            obs = db_result.get("recorded_observations", {})
            
            search_before = obs.get("v1_search_before", {})
            search_after = obs.get("v1_search_after", {})
            
            count_before = search_before.get("count", 0)
            count_after = search_after.get("count", 0)
            
            compat_results[db_name] = {
                "query_stable": count_before == count_after,
                "count_before": count_before,
                "count_after": count_after
            }
        
        return {
            "validation_type": validation_type,
            "compat_results": compat_results,
            "note": "Query results should be stable across v2 creation"
        }
    
    elif validation_type == "cross_collection_isolation":
        # Validate cross-collection isolation
        isolation_results = {}
        for db_result in database_results:
            db_name = db_result["database"]
            obs = db_result.get("recorded_observations", {})
            
            count_a = obs.get("count_a")
            count_b = obs.get("count_b")
            count_a_after = obs.get("count_a_after")
            count_b_after = obs.get("count_b_after")
            
            isolation_results[db_name] = {
                "a_isolated": count_a == count_a_after if count_a is not None and count_a_after is not None else None,
                "b_isolated": count_b == 0 and count_b_after == 1 if count_b is not None and count_b_after is not None else None,
                "count_a": count_a,
                "count_a_after": count_a_after,
                "count_b": count_b,
                "count_b_after": count_b_after
            }
        
        return {
            "validation_type": validation_type,
            "isolation_results": isolation_results,
            "note": "Collections should be isolated (operations on B don't affect A)"
        }
    
    elif validation_type == "metadata_stability":
        # Validate metadata stability
        stability_results = {}
        for db_result in database_results:
            db_name = db_result["database"]
            obs = db_result.get("recorded_observations", {})
            
            initial = obs.get("v1_metadata_initial", {})
            final = obs.get("v1_metadata_final", {})
            
            stability_results[db_name] = {
                "dimension_stable": initial.get("dimension") == final.get("dimension"),
                "initial_dimension": initial.get("dimension"),
                "final_dimension": final.get("dimension"),
                "note": "describe_collection may not be supported by all adapters"
            }
        
        return {
            "validation_type": validation_type,
            "stability_results": stability_results,
            "note": "v1 metadata should remain unchanged after v2 creation"
        }
    
    else:
        return {
            "validation_type": validation_type,
            "note": "Validation not yet implemented for this type"
        }


def run_r5d_cross_db(
    databases: List[str],
    test_cases: Optional[List[str]] = None,
    run_tag: str = "r5d-cross-db",
    output_dir: str = "runs/r5d_cross_db",
    require_real: bool = False,
    **adapter_kwargs
) -> Dict[str, Any]:
    """Run R5D schema evolution contract tests across multiple databases.
    
    Args:
        databases: List of databases to test
        test_cases: Optional list of specific test case IDs
        run_tag: Run identifier
        output_dir: Output directory
        require_real: Require real database connections
        **adapter_kwargs: Adapter connection parameters
        
    Returns:
        Aggregated results from all tests
    """
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_id = f"r5d-cross-db-{run_tag}-{timestamp}"
    
    # Filter test cases
    cases_to_run = R5D_TEST_CASES
    if test_cases:
        cases_to_run = [c for c in R5D_TEST_CASES if c["case_id"] in test_cases]
    
    results = {
        "run_id": run_id,
        "timestamp": timestamp,
        "databases": databases,
        "test_cases": [],
        "summary": {}
    }
    
    print(f"\n{'='*70}")
    print(f"R5D Cross-Database Schema Evolution Testing")
    print(f"Run ID: {run_id}")
    print(f"Databases: {', '.join(databases)}")
    print(f"Test Cases: {len(cases_to_run)}")
    print(f"{'='*70}\n")
    
    for test_case in cases_to_run:
        case_id = test_case["case_id"]
        case_name = test_case["name"]
        validation_type = test_case.get("validation", "basic")
        
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
            
            db_result = execute_r5d_sequence(
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
        
        # Validate results
        successful_results = [r for r in case_result["database_results"] if "error" not in r]
        if len(successful_results) >= 1:
            validation = validate_r5d_results(case_id, validation_type, successful_results)
            case_result["validation"] = validation
            print(f"  Validation: {validation.get('validation_type')}")
        
        results["test_cases"].append(case_result)
    
    # Generate summary
    total_cases = len(results["test_cases"])
    passed_validations = sum(
        1 for c in results["test_cases"]
        if c.get("validation", {}).get("validations") or 
           c.get("validation", {}).get("compat_results") or
           c.get("validation", {}).get("isolation_results")
    )
    
    results["summary"] = {
        "total_cases": total_cases,
        "validated_cases": passed_validations,
        "databases_tested": len(databases)
    }
    
    # Write results
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    report_file = output_path / f"{run_id}_report.json"
    with open(report_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    # Print summary
    print(f"\n{'='*70}")
    print("R5D Cross-Database Testing Summary")
    print(f"{'='*70}")
    print(f"Total test cases: {total_cases}")
    print(f"Validated cases: {passed_validations}")
    print(f"Databases tested: {len(databases)}")
    print(f"Report saved: {report_file}")
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Run R5D schema evolution contract tests across multiple databases"
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
        default="r5d-cross-db",
        help="Run identifier tag"
    )
    parser.add_argument(
        "--output-dir",
        default="runs/r5d_cross_db",
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
    
    run_r5d_cross_db(
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
