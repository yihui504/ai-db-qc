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

    # SETUP PHASE: Create test collection for dependent operations
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

    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_id = f"differential-{args.run_tag}-{timestamp}"

    print("="*60)
    print("  Milvus-vs-seekdb Differential Campaign")
    print("="*60)
    print(f"Run ID: {run_id}")
    print()

    # Load shared case pack
    print("Loading shared case pack...")
    templates = load_templates("casegen/templates/differential_shared_pack.yaml")
    print(f"Loaded {len(templates)} templates")

    # Instantiate
    cases = instantiate_all(templates, {
        "collection": "diff_test",
        "query_vector": [0.1] * 128,
        "vectors": [[0.1] * 128, [0.2] * 128],
        "k": 10,
        "wrong_dim_vectors": [[0.1] * 64],
        "empty_collection": "diff_empty"
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
    print(f"Next: python scripts/analyze_differential_results.py {output_dir}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
