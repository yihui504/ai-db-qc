"""Phase 5 evaluation runner - supports experiment variants via command-line flags."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


try:
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
    from schemas.common import OperationType, ObservedOutcome
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure all dependencies are installed")
    sys.exit(1)


class VariantFlags:
    """Container for experiment variant flags."""

    def __init__(
        self,
        no_gate: bool = False,
        no_oracle: bool = False,
        naive_triage: bool = False,
        adapter_fallback: bool = False,
        adapter_fallback_reason: str = ""
    ):
        self.no_gate = no_gate
        self.no_oracle = no_oracle
        self.naive_triage = naive_triage
        self.adapter_fallback = adapter_fallback
        self.adapter_fallback_reason = adapter_fallback_reason

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for metadata storage."""
        return {
            "no_gate": self.no_gate,
            "no_oracle": self.no_oracle,
            "naive_triage": self.naive_triage,
            "adapter_fallback": self.adapter_fallback,
            "adapter_fallback_reason": self.adapter_fallback_reason
        }


def execute_filtered_pair(
    executor: Executor,
    unfiltered_case: TestCase,
    filtered_case: TestCase,
    run_id: str
) -> tuple[Any, Any, Dict[str, Any]]:
    """Execute unfiltered -> filtered pair for FilterStrictness.

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


def create_adapter_with_fallback(
    adapter_choice: str,
    host: str,
    port: int,
    require_real: bool = False
) -> tuple[Any, VariantFlags, Dict[str, str]]:
    """Create adapter with Milvus fallback to mock.

    Args:
        adapter_choice: "mock" or "milvus"
        host: Milvus host
        port: Milvus port
        require_real: If True, fail instead of falling back to mock

    Returns:
        Tuple of (adapter, variant_flags, adapter_info)
        adapter_info contains: adapter_requested, adapter_actual, adapter_fallback, fallback_reason
    """
    variant_flags = VariantFlags()
    adapter_requested = adapter_choice

    if adapter_choice == "mock":
        # Explicit mock choice - no fallback
        return (
            MockAdapter(ResponseMode.SUCCESS),
            variant_flags,
            {
                "adapter_requested": adapter_requested,
                "adapter_actual": "mock",
                "adapter_fallback": False,
                "fallback_reason": None
            }
        )

    # Try Milvus adapter
    try:
        print(f"Connecting to Milvus at {host}:{port}...")
        connection_config = {
            "host": host,
            "port": port,
            "alias": "default"
        }
        adapter = MilvusAdapter(connection_config)

        # Test connection with health check
        if adapter.health_check():
            print(f"Successfully connected to Milvus")
            return (
                adapter,
                variant_flags,
                {
                    "adapter_requested": adapter_requested,
                    "adapter_actual": "milvus",
                    "adapter_fallback": False,
                    "fallback_reason": None
                }
            )
        else:
            raise Exception("Milvus health check failed")

    except Exception as e:
        # Handle connection failure
        error_msg = str(e)
        print(f"ERROR: Milvus connection failed: {error_msg}")

        if require_real:
            print("--require-real flag is set; failing instead of falling back to mock")
            print(f"ERROR: Cannot proceed without real Milvus connection")
            raise SystemExit(1) from e

        # Fallback to mock adapter
        print("WARNING: Falling back to mock adapter (data will NOT reflect real Milvus behavior)")
        variant_flags.adapter_fallback = True
        variant_flags.adapter_fallback_reason = error_msg
        return (
            MockAdapter(ResponseMode.SUCCESS),
            variant_flags,
            {
                "adapter_requested": adapter_requested,
                "adapter_actual": "mock",
                "adapter_fallback": True,
                "fallback_reason": error_msg
            }
        )


def create_oracles(variant_flags: VariantFlags) -> List[Any]:
    """Create oracle list based on variant flags.

    Args:
        variant_flags: Experiment variant flags

    Returns:
        List of oracle instances (empty if --no-oracle)
    """
    if variant_flags.no_oracle:
        print("Oracle execution disabled (--no-oracle)")
        return []

    return [WriteReadConsistency(validate_ids=True), FilterStrictness()]


def classify_with_naive_support(
    triage: Triage,
    case: TestCase,
    result: ExecutionResult,
    variant_flags: VariantFlags
) -> Any:
    """Classify with optional naive triage support.

    Args:
        triage: Triage instance
        case: Test case
        result: Execution result
        variant_flags: Experiment variant flags

    Returns:
        Triage result or None
    """
    naive_mode = variant_flags.naive_triage
    return triage.classify(case, result, naive=naive_mode)


def apply_gate_filter(
    results: List[ExecutionResult],
    cases: List[TestCase],
    variant_flags: VariantFlags
) -> List[ExecutionResult]:
    """Apply gate filtering based on variant flags.

    When --no-gate is set, Type-3/4 bugs are NOT filtered by precondition_pass.
    This means all results are included regardless of precondition status.

    Args:
        results: List of execution results
        cases: List of test cases
        variant_flags: Experiment variant flags

    Returns:
        Filtered list of results
    """
    if variant_flags.no_gate:
        # Gate filtering disabled - return all results
        return results

    # Standard gate filtering - only include results where precondition passed
    # This filters out Type-3/4 bugs that failed preconditions
    return [r for r in results if r.precondition_pass]


def main():
    parser = argparse.ArgumentParser(
        description="Run Phase 5 evaluation with experiment variants"
    )
    parser.add_argument(
        "--adapter",
        default="milvus",
        choices=["mock", "milvus"],
        help="Adapter to use (default: milvus)"
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="Milvus host (default: localhost)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=19530,
        help="Milvus port (default: 19530)"
    )
    parser.add_argument(
        "--no-gate",
        action="store_true",
        help="Disable gate filtering for Type-3/4 bugs"
    )
    parser.add_argument(
        "--no-oracle",
        action="store_true",
        help="Disable oracle execution (no Type-4 bugs)"
    )
    parser.add_argument(
        "--naive-triage",
        action="store_true",
        help="Use naive Type-2 classification"
    )
    parser.add_argument(
        "--run-tag",
        required=True,
        help="Required run tag (e.g., baseline_real_runA)"
    )
    parser.add_argument(
        "--output-dir",
        default="runs",
        help="Output directory (default: runs)"
    )
    parser.add_argument(
        "--require-real",
        action="store_true",
        help="Require real Milvus connection; fail instead of falling back to mock"
    )

    args = parser.parse_args()

    # Create variant flags
    variant_flags = VariantFlags(
        no_gate=args.no_gate,
        no_oracle=args.no_oracle,
        naive_triage=args.naive_triage
    )

    # Generate run ID from tag
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_id = f"phase5-{args.run_tag}-{timestamp}"

    print(f"=== Phase 5 Evaluation Runner ===")
    print(f"Run ID: {run_id}")
    print(f"Run Tag: {args.run_tag}")
    print(f"Output: {args.output_dir}/{run_id}")
    print()

    # Display variant configuration
    print("Variant Configuration:")
    print(f"  Adapter: {args.adapter}")
    print(f"  Gate Filtering: {'DISABLED' if variant_flags.no_gate else 'ENABLED'}")
    print(f"  Oracle Execution: {'DISABLED' if variant_flags.no_oracle else 'ENABLED'}")
    print(f"  Naive Triage: {'ENABLED' if variant_flags.naive_triage else 'DISABLED'}")
    print()

    # Load contract and profile
    print("Loading contract and profile...")
    contract = get_default_contract()
    profile = load_profile("contracts/db_profiles/milvus_profile.yaml")
    print(f"Contract: {len(contract.operations)} operations")
    print(f"Profile: {len(profile.supported_operations)} supported operations")
    print()

    # Create adapter with fallback
    adapter, adapter_flags, adapter_info = create_adapter_with_fallback(
        args.adapter, args.host, args.port, args.require_real
    )

    # Merge adapter fallback flags
    variant_flags.adapter_fallback = adapter_flags.adapter_fallback
    variant_flags.adapter_fallback_reason = adapter_flags.adapter_fallback_reason

    # Capture fingerprint if using Milvus
    fingerprint = None
    if args.adapter == "milvus" and not variant_flags.adapter_fallback:
        try:
            connection_config = {
                "host": args.host,
                "port": args.port,
                "alias": "default"
            }
            fingerprint = capture_environment(connection_config, adapter)
            print(f"Connected to Milvus {fingerprint.milvus_version}")
            print(f"pymilvus version: {fingerprint.pymilvus_version}")
        except Exception as e:
            print(f"WARNING: Could not capture fingerprint: {e}")
    else:
        print("Using mock adapter")
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
    oracles = create_oracles(variant_flags)
    executor = Executor(adapter, precond, oracles)

    # Store variant flags in executor for potential use
    executor.variant_flags = variant_flags.to_dict()

    triage = Triage()
    writer = EvidenceWriter()

    # Load and prepare cases
    print("Loading test cases...")
    # Use test template for now (real_milvus_cases.yaml has YAML syntax issues)
    templates = load_templates("casegen/templates/test_phase5.yaml")
    cases = instantiate_all(templates, {"collection": "test_collection"})
    print(f"Loaded {len(cases)} cases")
    print()

    # If Milvus, load runtime snapshot
    runtime_snapshots = []
    if args.adapter == "milvus" and not variant_flags.adapter_fallback:
        try:
            snapshot = adapter.get_runtime_snapshot()
            snapshot_id = f"snapshot-{datetime.now().strftime('%H%M%S')}"
            snapshot["snapshot_id"] = snapshot_id
            snapshot["timestamp"] = datetime.now().isoformat()
            runtime_snapshots.append(snapshot)
            precond.load_runtime_snapshot(snapshot)
            print(f"Runtime snapshot: {len(snapshot['collections'])} collections")
        except Exception as e:
            print(f"WARNING: Could not load runtime snapshot: {e}")
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
                print(f"  Executing pair: {case_id} -> {pair_id}")

                # Check which is unfiltered
                if "unfiltered" in case_id.lower():
                    unfiltered_case, filtered_case = case, pair_case
                else:
                    unfiltered_case, filtered_case = pair_case, case

                unfiltered_result, filtered_result, context = execute_filtered_pair(
                    executor, unfiltered_case, filtered_case, run_id
                )

                pair_results[case_id] = unfiltered_result
                pair_results[pair_id] = filtered_result
                results.append(unfiltered_result)
                results.append(filtered_result)

    # Execute unpaired cases
    for case in unpaired_cases:
        if case.case_id not in pair_results:
            print(f"  Executing: {case.case_id} ({case.operation})")
            result = executor.execute_case(case, run_id)
            results.append(result)

    print(f"Executed {len(results)} cases")

    # Count outcomes
    success_count = sum(1 for r in results if r.observed_outcome == ObservedOutcome.SUCCESS)
    failure_count = sum(1 for r in results if r.observed_outcome == ObservedOutcome.FAILURE)
    print(f"  Success: {success_count}")
    print(f"  Failure: {failure_count}")
    print()

    # Apply gate filtering based on variant flags
    filtered_results = apply_gate_filter(results, cases, variant_flags)

    if variant_flags.no_gate:
        print("Gate filtering DISABLED - all results included")
    else:
        print(f"Gate filtering applied: {len(filtered_results)}/{len(results)} results passed preconditions")
    print()

    # Classify bugs
    print("Classifying bugs...")
    triage_results = []
    for case in cases:
        # Find matching result by case_id
        result = next((r for r in results if r.case_id == case.case_id), None)
        if result:
            triage_result = classify_with_naive_support(
                triage, case, result, variant_flags
            )
            triage_results.append(triage_result)

    bug_count = sum(1 for t in triage_results if t is not None)
    print(f"Found {bug_count} bugs")
    print()

    # Write evidence
    print("Writing evidence...")
    run_dir = writer.create_run_dir(run_id, base_path=args.output_dir)
    run_metadata = {
        "run_id": run_id,
        "run_tag": args.run_tag,
        "timestamp": datetime.now().isoformat(),
        "phase": "5",
        "adapter": args.adapter,
        "adapter_requested": adapter_info["adapter_requested"],
        "adapter_actual": adapter_info["adapter_actual"],
        "adapter_fallback": adapter_info["adapter_fallback"],
        "fallback_reason": adapter_info["fallback_reason"],
        "variant_flags": variant_flags.to_dict(),
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
        runtime_snapshots if (args.adapter == "milvus" and not variant_flags.adapter_fallback) else None
    )
    print(f"Evidence written to {run_dir}")
    print()

    # Summary
    print("=== Summary ===")
    print(f"Run Tag: {args.run_tag}")
    print(f"Adapter: {args.adapter}")
    if variant_flags.adapter_fallback:
        print(f"ADAPTER FALLBACK: {variant_flags.adapter_fallback_reason}")
    print(f"Total cases: {len(cases)}")
    print(f"Bugs found: {bug_count}")
    print(f"Gate filtering: {'OFF' if variant_flags.no_gate else 'ON'}")
    print(f"Oracle execution: {'OFF' if variant_flags.no_oracle else 'ON'}")
    print(f"Naive triage: {'ON' if variant_flags.naive_triage else 'OFF'}")
    print(f"Evidence: {run_dir}")
    print()

    # Cleanup
    if args.adapter == "milvus" and not variant_flags.adapter_fallback:
        try:
            adapter.close()
            print("Milvus connection closed")
        except Exception:
            pass

    print("Done!")


if __name__ == "__main__":
    main()
