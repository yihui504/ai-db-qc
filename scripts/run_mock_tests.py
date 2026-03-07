"""Main script for mock testing."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from collections import Counter
from typing import Dict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from casegen.generators.instantiator import load_templates, instantiate_all
from adapters.mock import MockAdapter, ResponseMode, DiagnosticQuality
from pipeline.gate import GateStub, PreconditionMode
from pipeline.executor import Executor
from pipeline.triage import Triage
from schemas.result import OracleResult
from schemas.common import BugType


def main():
    parser = argparse.ArgumentParser(description="Run mock tests")
    parser.add_argument(
        "--response-mode",
        type=str,
        default="success",
        choices=["success", "failure", "crash", "hang", "timeout"],
        help="Mock adapter response mode"
    )
    parser.add_argument(
        "--gate-mode",
        type=str,
        default="all_pass",
        choices=["all_pass", "all_fail", "selective"],
        help="Gate precondition mode"
    )
    parser.add_argument(
        "--diagnostic-quality",
        type=str,
        default="full",
        choices=["full", "partial", "none"],
        help="Error message diagnostic quality"
    )
    parser.add_argument(
        "--simulate-type4",
        action="store_true",
        help="Simulate Type-4 by injecting mock oracle failure"
    )
    parser.add_argument(
        "--templates",
        type=str,
        default="casegen/templates/basic_templates.yaml",
        help="Path to templates file"
    )
    args = parser.parse_args()

    # Load templates
    print(f"Loading templates from {args.templates}...")
    templates = load_templates(args.templates)
    print(f"Loaded {len(templates)} templates")

    # Instantiate cases
    substitutions = {
        "collection": "test_collection",
        "k": 10,
        "query_vector": "[1.0] * 128",
        "vectors": "[[1.0] * 128]",
        "id": "001"
    }
    cases = instantiate_all(templates, substitutions)
    print(f"Generated {len(cases)} test cases")

    # Create mock adapter
    response_mode = ResponseMode(args.response_mode)
    diagnostic_quality = DiagnosticQuality(args.diagnostic_quality)

    mock_oracle = None
    if args.simulate_type4:
        mock_oracle = OracleResult(
            oracle_id="mock_oracle",
            passed=False,
            explanation="Simulated oracle failure for Type-4 testing"
        )
        print("Type-4 simulation enabled (mock oracle will fail)")

    adapter = MockAdapter(
        response_mode=response_mode,
        diagnostic_quality=diagnostic_quality,
        mock_oracle_result=mock_oracle
    )

    # Create gate
    gate_mode = PreconditionMode(args.gate_mode)
    gate = GateStub(mode=gate_mode)

    # Create executor
    executor = Executor(adapter, gate)

    # Execute
    print(f"\nExecuting with response_mode={args.response_mode}, gate_mode={args.gate_mode}...")
    results = executor.execute_batch(cases)

    # Triage
    print("Classifying results...")
    triage = Triage()
    triage_results = []
    type_counts: Counter = Counter()

    for case, result in zip(cases, results):
        t_result = triage.classify(case, result)
        triage_results.append(t_result)

        if t_result:
            type_counts[t_result.final_type] += 1
        else:
            type_counts["valid"] += 1

    # Print summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    for bug_type, count in sorted(type_counts.items()):
        print(f"  {bug_type}: {count}")
    print(f"  Total: {len(results)}")

    # Print details
    print("\nDETAILS")
    print("-" * 50)
    for i, (case, result, t_result) in enumerate(zip(cases, results, triage_results)):
        status = t_result.final_type if t_result else "valid"
        print(f"{i+1}. {case.case_id}: {status}")
        print(f"   Precondition pass: {result.precondition_pass}")
        print(f"   Observed: {result.observed_outcome}")


if __name__ == "__main__":
    main()
