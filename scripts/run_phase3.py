"""Phase 3 run script - full mock flow with evidence output."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from casegen.generators.instantiator import load_templates, instantiate_all
from contracts.core.loader import get_default_contract
from contracts.db_profiles.loader import load_profile
from pipeline.preconditions import PreconditionEvaluator
from adapters.mock import MockAdapter, ResponseMode, DiagnosticQuality
from oracles.write_read_consistency import WriteReadConsistency
from oracles.filter_strictness import FilterStrictness
from pipeline.executor import Executor
from pipeline.triage import Triage
from evidence.writer import EvidenceWriter


def main():
    parser = argparse.ArgumentParser(description="Run Phase 3 mock flow with evidence")
    parser.add_argument("--output-dir", default="runs", help="Output directory for evidence")
    parser.add_argument("--diagnostic-quality", default="full",
                        choices=["full", "partial", "none"],
                        help="Mock adapter diagnostic quality")
    parser.add_argument("--run-id", default=None,
                        help="Run ID (default: auto-generated)")
    args = parser.parse_args()

    # Generate run ID
    if args.run_id is None:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        args.run_id = f"phase3-{timestamp}"

    print(f"=== Phase 3 Mock Flow ===")
    print(f"Run ID: {args.run_id}")
    print(f"Output: {args.output_dir}/{args.run_id}")
    print()

    # Load templates and generate cases
    print("Loading templates...")
    templates = load_templates("casegen/templates/basic_templates.yaml")
    print(f"Loaded {len(templates)} templates")

    print("Instantiating cases...")
    cases = instantiate_all(templates, {"collection": "test", "k": 10})
    print(f"Generated {len(cases)} cases")
    print()

    # Load contract and profile
    print("Loading contract and profile...")
    contract = get_default_contract()
    profile = load_profile("contracts/db_profiles/milvus_profile.yaml")
    print(f"Contract: {len(contract.operations)} operations")
    print(f"Profile: {len(profile.supported_operations)} supported operations")
    print()

    # Set up runtime context
    runtime_context = {
        "collections": ["test"],
        "indexed_collections": ["test"],
        "connected": True,
        "target_collection": "test"
    }
    print(f"Runtime context: {runtime_context}")
    print()

    # Create components
    print("Creating components...")
    precond = PreconditionEvaluator(contract, profile, runtime_context)
    adapter = MockAdapter(ResponseMode.SUCCESS, DiagnosticQuality(args.diagnostic_quality.upper()))
    oracles = [WriteReadConsistency(), FilterStrictness()]
    executor = Executor(adapter, precond, oracles)
    triage = Triage()
    writer = EvidenceWriter()
    print(f"PreconditionEvaluator: {type(precond).__name__}")
    print(f"Adapter: {type(adapter).__name__}")
    print(f"Oracles: {[type(o).__name__ for o in oracles]}")
    print()

    # Execute cases
    print("Executing cases...")
    results = executor.execute_batch(cases, run_id=args.run_id)
    print(f"Executed {len(results)} cases")

    # Count outcomes
    from schemas.common import ObservedOutcome
    success_count = sum(1 for r in results if r.observed_outcome == ObservedOutcome.SUCCESS)
    failure_count = sum(1 for r in results if r.observed_outcome == ObservedOutcome.FAILURE)
    print(f"  Success: {success_count}")
    print(f"  Failure: {failure_count}")
    print()

    # Classify bugs
    print("Classifying bugs...")
    triage_results = [triage.classify(case, result) for case, result in zip(cases, results)]
    bug_count = sum(1 for t in triage_results if t is not None)
    print(f"Found {bug_count} bugs")
    print()

    # Write evidence
    print("Writing evidence...")
    run_dir = writer.create_run_dir(args.run_id, base_path=args.output_dir)
    run_metadata = {
        "run_id": args.run_id,
        "timestamp": datetime.now().isoformat(),
        "phase": "3",
        "case_count": len(cases),
        "bug_count": bug_count,
        "success_count": success_count,
        "failure_count": failure_count,
        "runtime_context": runtime_context
    }
    writer.write_all(run_dir, run_metadata, cases, results, triage_results)
    print(f"Evidence written to {run_dir}")
    print()

    # Summary
    print("=== Summary ===")
    print(f"Total cases: {len(cases)}")
    print(f"Bugs found: {bug_count}")
    print(f"Evidence: {run_dir}")
    print()
    print("Done!")


if __name__ == "__main__":
    main()
