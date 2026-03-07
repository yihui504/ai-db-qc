"""Phase 4 run script - real Milvus validation with evidence output."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from casegen.generators.instantiator import load_templates, instantiate_all
from contracts.core.loader import get_default_contract
from contracts.db_profiles.loader import load_profile
from pipeline.preconditions import PreconditionEvaluator
from adapters.mock import MockAdapter, ResponseMode
from adapters.milvus_adapter import MilvusAdapter
from oracles.write_read_consistency import WriteReadConsistency
from oracles.filter_strictness import FilterStrictness
from pipeline.executor import Executor
from pipeline.triage import Triage
from evidence.writer import EvidenceWriter
from evidence.fingerprint import capture_environment
from schemas.case import TestCase
from schemas.common import OperationType


def execute_filtered_pair(
    executor: Executor,
    unfiltered_case: TestCase,
    filtered_case: TestCase,
    run_id: str
) -> tuple[Any, Any, Dict[str, Any]]:
    """Execute unfiltered → filtered pair for FilterStrictness.

    Lightweight helper - no PairExecutor class needed.
    Returns (unfiltered_result, filtered_result, context).
    """
    # Execute unfiltered first
    unfiltered_result = executor.execute_case(unfiltered_case, run_id)

    # Extract IDs from unfiltered result
    unfiltered_ids = [
        item.get("id")
        for item in unfiltered_result.response.get("data", [])
        if "id" in item
    ]

    # Build context with unfiltered IDs
    context = {
        "unfiltered_result_ids": unfiltered_ids,
        "mock_state": executor.mock_state,
        "write_history": executor.write_history
    }

    # Execute filtered
    filtered_result = executor.execute_case(filtered_case, run_id)

    return unfiltered_result, filtered_result, context


def main():
    parser = argparse.ArgumentParser(description="Run Phase 4 real Milvus validation")
    parser.add_argument("--adapter", default="mock", choices=["mock", "milvus"],
                        help="Adapter to use (mock or milvus)")
    parser.add_argument("--host", default="localhost", help="Milvus host")
    parser.add_argument("--port", type=int, default=19530, help="Milvus port")
    parser.add_argument("--output-dir", default="runs", help="Output directory for evidence")
    parser.add_argument("--run-id", default=None, help="Run ID (default: auto-generated)")
    args = parser.parse_args()

    # Generate run ID
    if args.run_id is None:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        args.run_id = f"phase4-{args.adapter}-{timestamp}"

    print(f"=== Phase 4 {'Real' if args.adapter == 'milvus' else 'Mock'} DB Flow ===")
    print(f"Run ID: {args.run_id}")
    print(f"Output: {args.output_dir}/{args.run_id}")
    print()

    # Load contract and profile
    print("Loading contract and profile...")
    contract = get_default_contract()
    profile = load_profile("contracts/db_profiles/milvus_profile.yaml")
    print(f"Contract: {len(contract.operations)} operations")
    print(f"Profile: {len(profile.supported_operations)} supported operations")
    print()

    # Create adapter
    if args.adapter == "milvus":
        print(f"Connecting to Milvus at {args.host}:{args.port}...")
        connection_config = {
            "host": args.host,
            "port": args.port,
            "alias": "default"
        }
        adapter = MilvusAdapter(connection_config)

        # Capture fingerprint
        fingerprint = capture_environment(connection_config, adapter)
        print(f"Connected to Milvus {fingerprint.milvus_version}")
        print(f"pymilvus version: {fingerprint.pymilvus_version}")
        print()
    else:
        print("Using mock adapter...")
        adapter = MockAdapter(ResponseMode.SUCCESS)
        fingerprint = None
        print()

    # Create executor with oracles
    runtime_context = {
        "collections": [],
        "indexed_collections": [],
        "loaded_collections": [],
        "connected": True,
        "target_collection": "test_collection",
        "supported_features": ["IVF_FLAT", "HNSW"]
    }

    precond = PreconditionEvaluator(contract, profile, runtime_context)
    oracles = [WriteReadConsistency(validate_ids=True), FilterStrictness()]
    executor = Executor(adapter, precond, oracles)
    triage = Triage()
    writer = EvidenceWriter()

    # Load and prepare cases
    print("Loading real Milvus cases...")
    templates = load_templates("casegen/templates/real_milvus_cases.yaml")
    cases = instantiate_all(templates, {"collection": "test_collection"})
    print(f"Loaded {len(cases)} cases")
    print()

    # If Milvus, load runtime snapshot
    runtime_snapshots = []
    if args.adapter == "milvus":
        snapshot = adapter.get_runtime_snapshot()
        snapshot_id = f"snapshot-{datetime.now().strftime('%H%M%S')}"
        snapshot["snapshot_id"] = snapshot_id
        snapshot["timestamp"] = datetime.now().isoformat()
        runtime_snapshots.append(snapshot)
        precond.load_runtime_snapshot(snapshot)
        print(f"Runtime snapshot: {len(snapshot['collections'])} collections")
        print()

    # Execute cases (handle pairs for FilterStrictness)
    print("Executing cases...")
    results = []

    # Group cases by pair relationships
    paired_cases = {}
    unpaired_cases = []

    for case in cases:
        pair_with = case.params.get("pair_with")
        if pair_with:
            paired_cases[case.case_id] = case
        else:
            unpaired_cases.append(case)

    # Execute paired cases
    pair_results = {}
    for case_id, case in list(paired_cases.items()):
        pair_id = case.params.get("pair_with")
        if pair_id and pair_id in paired_cases:
            pair_case = paired_cases[pair_id]

            # Only process if not already done
            if case_id not in pair_results:
                print(f"  Executing pair: {case_id} → {pair_id}")

                # Check which is unfiltered
                if "unfiltered" in case_id.lower():
                    unfiltered_case, filtered_case = case, pair_case
                else:
                    unfiltered_case, filtered_case = pair_case, case

                unfiltered_result, filtered_result, context = execute_filtered_pair(
                    executor, unfiltered_case, filtered_case, args.run_id
                )

                pair_results[case_id] = unfiltered_result
                pair_results[pair_id] = filtered_result
                results.append(unfiltered_result)
                results.append(filtered_result)

    # Execute unpaired cases
    for case in unpaired_cases:
        if case.case_id not in pair_results:
            print(f"  Executing: {case.case_id} ({case.operation})")
            result = executor.execute_case(case, args.run_id)
            results.append(result)

    print(f"Executed {len(results)} cases")

    # Count outcomes
    from schemas.common import ObservedOutcome
    success_count = sum(1 for r in results if r.observed_outcome == ObservedOutcome.SUCCESS)
    failure_count = sum(1 for r in results if r.observed_outcome == ObservedOutcome.FAILURE)
    print(f"  Success: {success_count}")
    print(f"  Failure: {failure_count}")
    print()

    # Classify bugs - use explicit case-to-result mapping
    print("Classifying bugs...")
    triage_results = []
    for case in cases:
        # Find matching result by case_id
        result = next((r for r in results if r.case_id == case.case_id), None)
        if result:
            triage_result = triage.classify(case, result)
            triage_results.append(triage_result)
    bug_count = sum(1 for t in triage_results if t is not None)
    print(f"Found {bug_count} bugs")
    print()

    # Write evidence
    print("Writing evidence...")
    run_dir = writer.create_run_dir(args.run_id, base_path=args.output_dir)
    run_metadata = {
        "run_id": args.run_id,
        "timestamp": datetime.now().isoformat(),
        "phase": "4",
        "adapter": args.adapter,
        "case_count": len(cases),
        "bug_count": bug_count,
        "success_count": success_count,
        "failure_count": failure_count,
        "runtime_context": runtime_context
    }

    if fingerprint:
        run_metadata["fingerprint"] = fingerprint.model_dump(mode="json")

    writer.write_all(
        run_dir,
        run_metadata,
        cases,
        results,
        triage_results,
        fingerprint,
        runtime_snapshots if args.adapter == "milvus" else None
    )
    print(f"Evidence written to {run_dir}")
    print()

    # Summary
    print("=== Summary ===")
    print(f"Adapter: {args.adapter}")
    print(f"Total cases: {len(cases)}")
    print(f"Bugs found: {bug_count}")
    print(f"Evidence: {run_dir}")
    print()

    # Cleanup
    if args.adapter == "milvus":
        adapter.close()
        print("Milvus connection closed")

    print("Done!")


if __name__ == "__main__":
    main()
