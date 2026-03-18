"""R6 Consistency Contract Cross-Database Testing.

This script runs R6 consistency contract tests across multiple databases
(Milvus, Qdrant, Weaviate, pgvector) to identify behavioral differences
in consistency, visibility, and timing semantics.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.run_phase5_3_eval import create_adapter_with_fallback, VariantFlags
from oracles.differential import R6ConsistencyOracle, DifferenceCategory
from pipeline.executor import Executor
from pipeline.preconditions import PreconditionEvaluator
from contracts.core.loader import get_default_contract
from contracts.db_profiles.loader import load_profile
from schemas.common import ObservedOutcome


# R6 Consistency Test Cases
R6_TEST_CASES = [
    {
        "case_id": "R6-001",
        "name": "Insert Return vs Storage Visibility",
        "description": "insert() returns immediately, but storage_count visibility may require flush",
        "sequence": [
            {"operation": "create_collection", "params": {"collection_name": "r6_001_test", "dimension": 128}},
            {"operation": "insert", "params": {"collection_name": "r6_001_test", "vectors": [[0.1]*128]}, "record": "insert_count"},
            {"operation": "count", "params": {"collection_name": "r6_001_test"}, "record": "immediate_count"},
            {"operation": "flush", "params": {"collection_name": "r6_001_test"}},
            {"operation": "count", "params": {"collection_name": "r6_001_test"}, "record": "post_flush_count"}
        ],
        "analysis": "compare_counts"
    },
    {
        "case_id": "R6-002",
        "name": "Storage-Visible vs Search-Visible Relationship",
        "description": "flush enables storage-visible count; search-visible requires index/load",
        "sequence": [
            {"operation": "create_collection", "params": {"collection_name": "r6_002_test", "dimension": 128}},
            {"operation": "insert", "params": {"collection_name": "r6_002_test", "vectors": [[0.1]*128, [0.2]*128]}},
            {"operation": "flush", "params": {"collection_name": "r6_002_test"}},
            {"operation": "count", "params": {"collection_name": "r6_002_test"}, "record": "storage_count"},
            {"operation": "build_index", "params": {"collection_name": "r6_002_test", "index_type": "HNSW"}},
            {"operation": "load_index", "params": {"collection_name": "r6_002_test"}},
            {"operation": "search", "params": {"collection_name": "r6_002_test", "vector": [0.1]*128, "top_k": 10}, "record": "search_results"}
        ],
        "analysis": "visibility_relationship"
    },
    {
        "case_id": "R6-003",
        "name": "Load/Release/Reload Gate on Search Visibility",
        "description": "search requires loaded collection; unload/release blocks search; reload restores",
        "sequence": [
            {"operation": "create_collection", "params": {"collection_name": "r6_003_test", "dimension": 128}},
            {"operation": "insert", "params": {"collection_name": "r6_003_test", "vectors": [[0.1]*128]}},
            {"operation": "build_index", "params": {"collection_name": "r6_003_test", "index_type": "HNSW"}},
            {"operation": "load_index", "params": {"collection_name": "r6_003_test"}},
            {"operation": "search", "params": {"collection_name": "r6_003_test", "vector": [0.1]*128, "top_k": 10}, "expected": "success", "record": "baseline_search"},
            {"operation": "release", "params": {"collection_name": "r6_003_test"}},
            {"operation": "search", "params": {"collection_name": "r6_003_test", "vector": [0.1]*128, "top_k": 10}, "expected": "failure", "record": "post_release_search"},
            {"operation": "load_index", "params": {"collection_name": "r6_003_test"}},
            {"operation": "search", "params": {"collection_name": "r6_003_test", "vector": [0.1]*128, "top_k": 10}, "expected": "success", "record": "post_reload_search"}
        ],
        "analysis": "load_gate"
    },
    {
        "case_id": "R6-004",
        "name": "Insert-Search Timing Window",
        "description": "Observe insert-search visibility within tested wait window",
        "sequence": [
            {"operation": "create_collection", "params": {"collection_name": "r6_004_test", "dimension": 128}},
            {"operation": "build_index", "params": {"collection_name": "r6_004_test", "index_type": "HNSW"}},
            {"operation": "load_index", "params": {"collection_name": "r6_004_test"}},
            {"operation": "insert", "params": {"collection_name": "r6_004_test", "vectors": [[0.1]*128]}},
            {"operation": "search", "params": {"collection_name": "r6_004_test", "vector": [0.1]*128, "top_k": 10}, "record": "immediate_search"},
            {"operation": "wait", "params": {"seconds": 1}},
            {"operation": "search", "params": {"collection_name": "r6_004_test", "vector": [0.1]*128, "top_k": 10}, "record": "delayed_search"},
            {"operation": "flush", "params": {"collection_name": "r6_004_test"}},
            {"operation": "search", "params": {"collection_name": "r6_004_test", "vector": [0.1]*128, "top_k": 10}, "record": "flushed_search"}
        ],
        "analysis": "timing_visibility"
    },
    {
        "case_id": "R6-005",
        "name": "Release Preserves Storage Data",
        "description": "release() preserves storage_count; reload restores search visibility",
        "sequence": [
            {"operation": "create_collection", "params": {"collection_name": "r6_005_test", "dimension": 128}},
            {"operation": "insert", "params": {"collection_name": "r6_005_test", "vectors": [[0.1]*128, [0.2]*128]}},
            {"operation": "flush", "params": {"collection_name": "r6_005_test"}},
            {"operation": "count", "params": {"collection_name": "r6_005_test"}, "record": "pre_release_count"},
            {"operation": "build_index", "params": {"collection_name": "r6_005_test", "index_type": "HNSW"}},
            {"operation": "load_index", "params": {"collection_name": "r6_005_test"}},
            {"operation": "search", "params": {"collection_name": "r6_005_test", "vector": [0.1]*128, "top_k": 10}, "record": "pre_release_search"},
            {"operation": "release", "params": {"collection_name": "r6_005_test"}},
            {"operation": "count", "params": {"collection_name": "r6_005_test"}, "record": "post_release_count"},
            {"operation": "load_index", "params": {"collection_name": "r6_005_test"}},
            {"operation": "search", "params": {"collection_name": "r6_005_test", "vector": [0.1]*128, "top_k": 10}, "record": "post_reload_search"}
        ],
        "analysis": "release_preservation"
    },
    {
        "case_id": "R6-006",
        "name": "Repeated Flush Stability",
        "description": "Repeated flush should not introduce contradictory visibility regressions",
        "sequence": [
            {"operation": "create_collection", "params": {"collection_name": "r6_006_test", "dimension": 128}},
            {"operation": "insert", "params": {"collection_name": "r6_006_test", "vectors": [[0.1]*128]}},
            {"operation": "flush", "params": {"collection_name": "r6_006_test"}},
            {"operation": "count", "params": {"collection_name": "r6_006_test"}, "record": "count_after_first_flush"},
            {"operation": "insert", "params": {"collection_name": "r6_006_test", "vectors": [[0.2]*128]}},
            {"operation": "flush", "params": {"collection_name": "r6_006_test"}},
            {"operation": "count", "params": {"collection_name": "r6_006_test"}, "record": "count_after_second_flush"}
        ],
        "analysis": "flush_stability"
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


def execute_r6_sequence(
    db_name: str,
    sequence: List[Dict[str, Any]],
    require_real: bool = False,
    **adapter_kwargs
) -> Dict[str, Any]:
    """Execute R6 test sequence on a single database.
    
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
        expected = step.get("expected", "success")
        record_key = step.get("record")
        
        # Handle wait operation
        if operation == "wait":
            time.sleep(params.get("seconds", 1))
            step_results.append({
                "step": i + 1,
                "operation": operation,
                "params": params,
                "success": True
            })
            continue
        
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
                elif operation == "insert":
                    recorded_observations[record_key] = response.get("inserted_count", 1)
            
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
        "recorded_observations": recorded_observations,
        "total_steps": len(step_results),
        "success_count": sum(1 for s in step_results if s["success"]),
        "failure_count": sum(1 for s in step_results if not s["success"])
    }


def analyze_r6_results(
    case_id: str,
    analysis_type: str,
    database_results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Analyze R6 test results across databases.
    
    Args:
        case_id: Test case ID
        analysis_type: Type of analysis to perform
        database_results: Results from each database
        
    Returns:
        Analysis results
    """
    if analysis_type == "compare_counts":
        # Compare count observations across databases
        observations = {}
        for db_result in database_results:
            db_name = db_result["database"]
            obs = db_result.get("recorded_observations", {})
            observations[db_name] = {
                "immediate_count": obs.get("immediate_count"),
                "post_flush_count": obs.get("post_flush_count")
            }
        
        # Check if all databases show same pattern
        patterns = set()
        for db_name, obs in observations.items():
            imm = obs.get("immediate_count")
            post = obs.get("post_flush_count")
            if imm is not None and post is not None:
                if imm == post:
                    patterns.add("immediate_visible")
                else:
                    patterns.add("flush_required")
        
        return {
            "analysis_type": analysis_type,
            "observations": observations,
            "behavior_patterns": list(patterns),
            "consistent": len(patterns) <= 1
        }
    
    elif analysis_type == "load_gate":
        # Analyze load/release/reload behavior
        gate_behaviors = {}
        for db_result in database_results:
            db_name = db_result["database"]
            steps = db_result.get("steps", [])
            
            # Find search steps
            search_steps = [s for s in steps if s["operation"] == "search"]
            if len(search_steps) >= 3:
                gate_behaviors[db_name] = {
                    "baseline": search_steps[0].get("success"),
                    "post_release": search_steps[1].get("success"),
                    "post_reload": search_steps[2].get("success")
                }
        
        return {
            "analysis_type": analysis_type,
            "gate_behaviors": gate_behaviors,
            "note": "All databases should enforce load gate (baseline=True, post_release=False, post_reload=True)"
        }
    
    elif analysis_type == "timing_visibility":
        # Analyze timing behavior
        timing_patterns = {}
        for db_result in database_results:
            db_name = db_result["database"]
            obs = db_result.get("recorded_observations", {})
            timing_patterns[db_name] = {
                "immediate": obs.get("immediate_search", {}).get("count", 0),
                "delayed": obs.get("delayed_search", {}).get("count", 0),
                "flushed": obs.get("flushed_search", {}).get("count", 0)
            }
        
        return {
            "analysis_type": analysis_type,
            "timing_patterns": timing_patterns,
            "note": "Visibility timing may vary by database implementation"
        }
    
    elif analysis_type == "release_preservation":
        # Analyze data preservation across release/reload
        preservation_results = {}
        for db_result in database_results:
            db_name = db_result["database"]
            obs = db_result.get("recorded_observations", {})
            
            pre_count = obs.get("pre_release_count")
            post_count = obs.get("post_release_count")
            
            preservation_results[db_name] = {
                "count_preserved": pre_count == post_count if pre_count is not None and post_count is not None else None,
                "pre_release_count": pre_count,
                "post_release_count": post_count
            }
        
        return {
            "analysis_type": analysis_type,
            "preservation_results": preservation_results,
            "note": "Data should be preserved across release (count unchanged)"
        }
    
    else:
        return {
            "analysis_type": analysis_type,
            "note": "Analysis not yet implemented for this type"
        }


def run_r6_cross_db(
    databases: List[str],
    test_cases: Optional[List[str]] = None,
    run_tag: str = "r6-cross-db",
    output_dir: str = "runs/r6_cross_db",
    require_real: bool = False,
    **adapter_kwargs
) -> Dict[str, Any]:
    """Run R6 consistency contract tests across multiple databases.
    
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
    run_id = f"r6-cross-db-{run_tag}-{timestamp}"
    
    # Filter test cases
    cases_to_run = R6_TEST_CASES
    if test_cases:
        cases_to_run = [c for c in R6_TEST_CASES if c["case_id"] in test_cases]
    
    results = {
        "run_id": run_id,
        "timestamp": timestamp,
        "databases": databases,
        "test_cases": [],
        "summary": {}
    }
    
    print(f"\n{'='*70}")
    print(f"R6 Cross-Database Consistency Testing")
    print(f"Run ID: {run_id}")
    print(f"Databases: {', '.join(databases)}")
    print(f"Test Cases: {len(cases_to_run)}")
    print(f"{'='*70}\n")
    
    for test_case in cases_to_run:
        case_id = test_case["case_id"]
        case_name = test_case["name"]
        analysis_type = test_case.get("analysis", "basic")
        
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
            
            db_result = execute_r6_sequence(
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
                if db_result.get("recorded_observations"):
                    print(f"    Observations: {list(db_result['recorded_observations'].keys())}")
        
        # Analyze results
        successful_results = [r for r in case_result["database_results"] if "error" not in r]
        if len(successful_results) >= 2:
            analysis = analyze_r6_results(case_id, analysis_type, successful_results)
            case_result["analysis"] = analysis
            print(f"  Analysis: {analysis.get('analysis_type')}")
            if analysis.get('consistent'):
                print(f"  Result: CONSISTENT across databases")
            else:
                print(f"  Result: VARIATION detected")
        
        results["test_cases"].append(case_result)
    
    # Generate summary
    total_cases = len(results["test_cases"])
    consistent_cases = sum(
        1 for c in results["test_cases"]
        if c.get("analysis", {}).get("consistent", False)
    )
    
    results["summary"] = {
        "total_cases": total_cases,
        "consistent_cases": consistent_cases,
        "variation_cases": total_cases - consistent_cases,
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
    print("R6 Cross-Database Testing Summary")
    print(f"{'='*70}")
    print(f"Total test cases: {total_cases}")
    print(f"Consistent across databases: {consistent_cases}")
    print(f"Cases with variation: {total_cases - consistent_cases}")
    print(f"Report saved: {report_file}")
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Run R6 consistency contract tests across multiple databases"
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
        default="r6-cross-db",
        help="Run identifier tag"
    )
    parser.add_argument(
        "--output-dir",
        default="runs/r6_cross_db",
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
    
    run_r6_cross_db(
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
