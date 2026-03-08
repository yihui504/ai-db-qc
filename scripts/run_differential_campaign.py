"""Run differential campaign on Milvus and seekdb.

Executes the same 30 shared cases on both databases.

Usage:
    python scripts/run_differential_campaign.py --run-tag <tag>
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from adapters.seekdb_adapter import SeekDBAdapter
    from adapters.milvus_adapter import MilvusAdapter
    from casegen.generators.instantiator import load_templates, instantiate_all
    from contracts.core.loader import get_default_contract
    from contracts.db_profiles.loader import load_profile
    from pipeline.preconditions import PreconditionEvaluator
    from pipeline.executor import Executor
    from pipeline.triage import Triage
    from schemas.common import ObservedOutcome
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)


def cleanup_test_collections(adapter, adapter_name: str, prefix: str):
    """Drop all test collections matching the run prefix."""
    try:
        snapshot = adapter.get_runtime_snapshot()
        dropped = 0
        for coll in snapshot.get("collections", []):
            if coll.startswith(prefix.replace("main", "")):
                result = adapter.execute({
                    "operation": "drop_collection",
                    "params": {"collection_name": coll}
                })
                if result.get("status") == "success":
                    dropped += 1
        print(f"  [{adapter_name}] Cleaned up {dropped} test collections")
    except Exception as e:
        print(f"  [{adapter_name}] Cleanup warning: {e}")


def run_campaign_on_db(adapter, adapter_name: str, cases: List, run_id: str) -> Dict:
    """Run campaign on a single database."""
    print(f"\n{'='*60}")
    print(f"  Running on {adapter_name}")
    print(f"{'='*60}\n")

    # Load contract and profile
    contract = get_default_contract()
    if adapter_name == "seekdb":
        profile = load_profile("contracts/db_profiles/seekdb_profile.yaml")
    else:
        profile = load_profile("contracts/db_profiles/milvus_profile.yaml")

    # Get runtime snapshot
    snapshot = adapter.get_runtime_snapshot()

    # Runtime context
    runtime_context = {
        "collections": snapshot.get("collections", []),
        "indexed_collections": snapshot.get("indexed_collections", []),
        "loaded_collections": snapshot.get("loaded_collections", []),
        "connected": snapshot.get("connected", True),
        "supported_features": ["hybrid_search", "filtering", "multi_model"]
    }

    # Create executor
    precond = PreconditionEvaluator(contract, profile, runtime_context)
    precond.load_runtime_snapshot(snapshot)

    from oracles.filter_strictness import FilterStrictness
    from oracles.write_read_consistency import WriteReadConsistency
    from oracles.monotonicity import Monotonicity

    oracles = [
        WriteReadConsistency(validate_ids=True),
        FilterStrictness(),
        Monotonicity()
    ]

    executor = Executor(adapter, precond, oracles)
    triage = Triage()

    # PHASE 2 MULTI-COLLECTION SETUP: Create precondition test collections
    print(f"  [{adapter_name}] PHASE2 SETUP: Creating precondition test collections...")

    # Collection 1: no_index_test (has data, no index)
    result = adapter.execute({
        "operation": "create_collection",
        "params": {"collection_name": "no_index_test", "dimension": 128, "metric_type": "L2"}
    })
    if result.get("status") == "success":
        adapter.execute({
            "operation": "insert",
            "params": {"collection_name": "no_index_test", "vectors": [[0.1] * 128, [0.2] * 128]}
        })
        print(f"  [{adapter_name}] PHASE2 SETUP: no_index_test created (with data, no index)")

    # Collection 2: empty_no_index_test (no data, no index)
    result = adapter.execute({
        "operation": "create_collection",
        "params": {"collection_name": "empty_no_index_test", "dimension": 128, "metric_type": "L2"}
    })
    if result.get("status") == "success":
        print(f"  [{adapter_name}] PHASE2 SETUP: empty_no_index_test created (empty, no index)")

    # Collection 3: indexed_not_loaded_test (has data, has index, NOT loaded for Milvus)
    result = adapter.execute({
        "operation": "create_collection",
        "params": {"collection_name": "indexed_not_loaded_test", "dimension": 128, "metric_type": "L2"}
    })
    if result.get("status") == "success":
        adapter.execute({
            "operation": "insert",
            "params": {"collection_name": "indexed_not_loaded_test", "vectors": [[0.1] * 128, [0.2] * 128]}
        })
        adapter.execute({
            "operation": "build_index",
            "params": {"collection_name": "indexed_not_loaded_test", "index_type": "IVF_FLAT", "metric_type": "L2"}
        })
        # Intentionally NOT loading this collection
        print(f"  [{adapter_name}] PHASE2 SETUP: indexed_not_loaded_test created (indexed, not loaded)")

    # Collection 4: vector_only_test (same as no_index_test for basic vector search)
    result = adapter.execute({
        "operation": "create_collection",
        "params": {"collection_name": "vector_only_test", "dimension": 128, "metric_type": "L2"}
    })
    if result.get("status") == "success":
        adapter.execute({
            "operation": "insert",
            "params": {"collection_name": "vector_only_test", "vectors": [[0.1] * 128, [0.2] * 128]}
        })
        print(f"  [{adapter_name}] PHASE2 SETUP: vector_only_test created (vector-only)")

    # STANDARD SETUP PHASE: Create test collection for dependent operations
    print(f"  [{adapter_name}] SETUP: Creating test collection...")
    setup_request = {
        "operation": "create_collection",
        "params": {
            "collection_name": "diff_test",
            "dimension": 128,
            "metric_type": "L2"
        }
    }
    setup_result = adapter.execute(setup_request)
    if setup_result.get("status") == "success":
        print(f"  [{adapter_name}] SETUP: Test collection created")
    else:
        print(f"  [{adapter_name}] SETUP WARNING: {setup_result.get('error', 'Unknown error')}")

    # SETUP PHASE: Insert test data
    print(f"  [{adapter_name}] SETUP: Inserting test data...")
    insert_request = {
        "operation": "insert",
        "params": {
            "collection_name": "diff_test",
            "vectors": [[0.1] * 128, [0.2] * 128, [0.3] * 128]
        }
    }
    insert_result = adapter.execute(insert_request)
    if insert_result.get("status") == "success":
        print(f"  [{adapter_name}] SETUP: Test data inserted")
    else:
        print(f"  [{adapter_name}] SETUP WARNING: Insert failed - {insert_result.get('error', 'Unknown error')[:80]}")

    # SETUP PHASE: Build index (required for search operations)
    print(f"  [{adapter_name}] SETUP: Building index...")
    index_request = {
        "operation": "build_index",
        "params": {
            "collection_name": "diff_test",
            "index_type": "IVF_FLAT",
            "metric_type": "L2"
        }
    }
    index_result = adapter.execute(index_request)
    if index_result.get("status") == "success":
        print(f"  [{adapter_name}] SETUP: Index built")
    else:
        print(f"  [{adapter_name}] SETUP WARNING: Index build failed - {index_result.get('error', 'Unknown error')[:80]}")

    # SETUP PHASE: Load collection/index (required for Milvus search)
    print(f"  [{adapter_name}] SETUP: Loading collection...")
    load_request = {
        "operation": "load",
        "params": {
            "collection_name": "diff_test"
        }
    }
    load_result = adapter.execute(load_request)
    if load_result.get("status") == "success":
        print(f"  [{adapter_name}] SETUP: Collection loaded")
    else:
        print(f"  [{adapter_name}] SETUP WARNING: Load failed - {load_result.get('error', 'Unknown error')[:80]}")

    # Execute cases
    results = []
    for case in cases:
        print(f"  [{adapter_name}] {case.case_id} ({case.operation})")
        try:
            result = executor.execute_case(case, run_id)
            results.append(result)
        except Exception as e:
            print(f"  [{adapter_name}] ERROR: {e}")
            from schemas.case import ExecutionResult
            result = ExecutionResult(
                case_id=case.case_id,
                run_id=run_id,
                status="error",
                observed_outcome=ObservedOutcome.FAILURE,
                error=str(e)
            )
            results.append(result)

    # Triage
    triage_results = []
    for case in cases:
        result = next((r for r in results if r.case_id == case.case_id), None)
        if result:
            triage_result = triage.classify(case, result, naive=False)
            triage_results.append(triage_result)

    success_count = sum(1 for r in results if r.observed_outcome == ObservedOutcome.SUCCESS)
    failure_count = sum(1 for r in results if r.observed_outcome == ObservedOutcome.FAILURE)

    print(f"\n[{adapter_name}] Results: {success_count} success, {failure_count} failure")
    print(f"[{adapter_name}] Bugs triaged: {sum(1 for t in triage_results if t is not None)}")

    return {
        "adapter_name": adapter_name,
        "results": results,
        "triage_results": triage_results,
        "snapshot": snapshot,
        "success_count": success_count,
        "failure_count": failure_count
    }


def main():
    parser = argparse.ArgumentParser(description="Run differential campaign")
    parser.add_argument("--run-tag", required=True, help="Run tag")
    parser.add_argument("--seekdb-endpoint", default=os.getenv("SEEKDB_API_ENDPOINT", "127.0.0.1:2881"))
    parser.add_argument("--seekdb-api-key", default=os.getenv("SEEKDB_API_KEY", ""))
    parser.add_argument("--milvus-endpoint", default=os.getenv("MILVUS_API_ENDPOINT", "http://localhost:19530"))
    parser.add_argument("--skip-milvus", action="store_true")
    parser.add_argument("--skip-seekdb", action="store_true")
    parser.add_argument("--output-dir", default="runs")
    parser.add_argument("--templates", default="casegen/templates/differential_shared_pack.yaml", help="Template file to use")

    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_id = f"differential-{args.run_tag}-{timestamp}"

    print("="*60)
    print("  Milvus-vs-seekdb Differential Campaign")
    print("="*60)
    print(f"Run ID: {run_id}")
    print()

    # Load shared case pack
    print(f"Loading templates from {args.templates}...")
    templates = load_templates(args.templates)
    print(f"Loaded {len(templates)} templates")

    # Use unique collection names to avoid collisions (underscores only for Milvus compatibility)
    collection_prefix = f"diff_{timestamp}_"

    # Instantiate
    cases = instantiate_all(templates, {
        "collection": f"{collection_prefix}main",
        "query_vector": [0.1] * 128,
        "vectors": [[0.1] * 128, [0.2] * 128],
        "k": 10,
        "wrong_dim_vectors": [[0.1] * 64],
        "empty_collection": f"{collection_prefix}empty"
    })
    print(f"Instantiated {len(cases)} cases\n")

    campaign_results = {}

    # Run on seekdb
    if not args.skip_seekdb:
        try:
            seekdb_adapter = SeekDBAdapter(
                api_endpoint=args.seekdb_endpoint,
                api_key=args.seekdb_api_key,
                collection="diff_test"
            )
            if seekdb_adapter.health_check():
                campaign_results["seekdb"] = run_campaign_on_db(
                    seekdb_adapter, "seekdb", cases, run_id
                )
            else:
                print("ERROR: seekdb health check failed")
        except Exception as e:
            print(f"ERROR: seekdb campaign failed: {e}")

    # Run on Milvus
    if not args.skip_milvus:
        try:
            # Parse Milvus endpoint (expected format: http://host:port or host:port)
            endpoint = args.milvus_endpoint
            if "://" in endpoint:
                endpoint = endpoint.split("://")[-1]
            if ":" in endpoint:
                host, port = endpoint.split(":")
                port = int(port)
            else:
                host = endpoint
                port = 19530

            # Milvus adapter expects connection_config dict
            milvus_adapter = MilvusAdapter({
                "host": host,
                "port": port,
                "alias": "default"
            })
            if milvus_adapter.health_check():
                campaign_results["milvus"] = run_campaign_on_db(
                    milvus_adapter, "milvus", cases, run_id
                )
            else:
                print("ERROR: Milvus health check failed")
        except Exception as e:
            print(f"ERROR: Milvus campaign failed: {e}")

    if not campaign_results:
        print("\nERROR: No campaigns completed successfully")
        return 1

    # Save results
    output_dir = Path(args.output_dir) / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    for db_name, data in campaign_results.items():
        db_dir = output_dir / db_name
        db_dir.mkdir(exist_ok=True)

        # Save results
        with open(db_dir / "execution_results.jsonl", "w") as f:
            for result in data["results"]:
                result_dict = result.__dict__ if hasattr(result, '__dict__') else result
                f.write(json.dumps(result_dict, default=str) + "\n")

        # Save triage
        triage_list = []
        for t in data["triage_results"]:
            if t is not None:
                triage_list.append(t.__dict__ if hasattr(t, '__dict__') else t)
            else:
                triage_list.append(None)

        with open(db_dir / "triage_results.json", "w") as f:
            json.dump(triage_list, f, indent=2)

        # Save metadata
        with open(db_dir / "metadata.json", "w") as f:
            json.dump({
                "adapter_name": data["adapter_name"],
                "success_count": data["success_count"],
                "failure_count": data["failure_count"],
                "snapshot": data["snapshot"]
            }, f, indent=2)

    print(f"\nResults saved to {output_dir}")

    # Cleanup phase - clean up test collections
    print("\n" + "="*60)
    print("  Cleanup Phase")
    print("="*60)
    collection_prefix = f"diff_{timestamp}_"

    # Recreate adapters for cleanup
    if not args.skip_seekdb and "seekdb" in campaign_results:
        try:
            cleanup_adapter = SeekDBAdapter(
                api_endpoint=args.seekdb_endpoint,
                api_key=args.seekdb_api_key,
                collection="diff_test"
            )
            cleanup_test_collections(cleanup_adapter, "seekdb", collection_prefix)
        except Exception as e:
            print(f"  seekdb cleanup skipped: {e}")

    if not args.skip_milvus and "milvus" in campaign_results:
        try:
            # Parse Milvus endpoint again
            endpoint = args.milvus_endpoint
            if "://" in endpoint:
                endpoint = endpoint.split("://")[-1]
            if ":" in endpoint:
                host, port = endpoint.split(":")
                port = int(port)
            else:
                host = endpoint
                port = 19530

            cleanup_adapter = MilvusAdapter({
                "host": host,
                "port": port,
                "alias": "default"
            })
            cleanup_test_collections(cleanup_adapter, "milvus", collection_prefix)
        except Exception as e:
            print(f"  milvus cleanup skipped: {e}")

    print(f"\nNext: python scripts/analyze_differential_results.py {output_dir}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
