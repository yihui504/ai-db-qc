#!/usr/bin/env python3
"""Diff two test runs using RESULTS_INDEX.json for file lookup.

REQUIREMENT: Must read RESULTS_INDEX.json first to locate result files.
No glob pattern matching allowed - explicit run_id lookup only.
"""

import argparse
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict


def load_results_index() -> Dict[str, Dict[str, Any]]:
    """Load RESULTS_INDEX.json as lookup table.

    Returns:
        Dict mapping run_id to index entry
    """
    index_path = Path("results/RESULTS_INDEX.json")
    if not index_path.exists():
        print(f"Error: RESULTS_INDEX.json not found at {index_path}")
        print("Run: python scripts/index_results.py")
        return {}

    data = json.loads(index_path.read_text())

    # Build lookup table: run_id -> entry
    lookup = {}
    for entry in data.get("entries", []):
        run_id = entry.get("run_id")
        if run_id:
            lookup[run_id] = entry

    return lookup


def locate_result_file(run_id: str, index: Dict[str, Dict[str, Any]]) -> Optional[Path]:
    """Locate result file by run_id using index.

    Args:
        run_id: Run ID to look up
        index: Index lookup table from load_results_index()

    Returns:
        Path to result file or None if not found
    """
    entry = index.get(run_id)
    if not entry:
        return None

    result_file = entry.get("result_file")
    if not result_file:
        return None

    path = Path(result_file)
    if not path.exists():
        print(f"Error: Result file exists in index but not on disk: {result_file}")
        return None

    return path


def load_result(run_id: str, index: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Load result data by run_id.

    Args:
        run_id: Run ID to load
        index: Index lookup table

    Returns:
        Result data dict or None if not found
    """
    result_path = locate_result_file(run_id, index)
    if not result_path:
        print(f"Error: Run ID not found in index: {run_id}")
        return None

    return json.loads(result_path.read_text())


def diff_results(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
    """Compare two result runs.

    Args:
        before: Earlier result data
        after: Later result data

    Returns:
        Diff dict with delta information
    """
    before_results = before.get("results", [])
    after_results = after.get("results", [])

    # Build lookup by case_id
    before_by_case: Dict[str, Dict] = {r.get("case_id"): r for r in before_results}
    after_by_case: Dict[str, Dict] = {r.get("case_id"): r for r in after_results}

    # All unique cases
    all_cases = set(before_by_case.keys()) | set(after_by_case.keys())

    delta = {
        "before_run_id": before.get("run_id"),
        "after_run_id": after.get("run_id"),
        "before_timestamp": before.get("timestamp"),
        "after_timestamp": after.get("timestamp"),
        "before_campaign": before.get("campaign"),
        "after_campaign": after.get("campaign"),
        "summary_delta": {},
        "case_deltas": []
    }

    # Summary delta
    before_summary = before.get("summary", {})
    after_summary = after.get("summary", {})

    delta["summary_delta"] = {
        "total_cases_change": after_summary.get("total", 0) - before_summary.get("total", 0),
        "before_classifications": before_summary.get("by_classification", {}),
        "after_classifications": after_summary.get("by_classification", {})
    }

    # Per-case deltas
    for case_id in sorted(all_cases):
        before_case = before_by_case.get(case_id)
        after_case = after_by_case.get(case_id)

        if before_case and after_case:
            # Both exist - check for classification change
            before_class = before_case.get("oracle", {}).get("classification")
            after_class = after_case.get("oracle", {}).get("classification")

            if before_class != after_class:
                delta["case_deltas"].append({
                    "case_id": case_id,
                    "change_type": "classification_changed",
                    "before_classification": before_class,
                    "after_classification": after_class,
                    "before_contract_id": before_case.get("contract_id"),
                    "after_contract_id": after_case.get("contract_id")
                })
        elif before_case and not after_case:
            # Case removed
            delta["case_deltas"].append({
                "case_id": case_id,
                "change_type": "removed",
                "before_classification": before_case.get("oracle", {}).get("classification"),
                "after_classification": None,
                "before_contract_id": before_case.get("contract_id"),
                "after_contract_id": None
            })
        else:
            # Case added
            delta["case_deltas"].append({
                "case_id": case_id,
                "change_type": "added",
                "before_classification": None,
                "after_classification": after_case.get("oracle", {}).get("classification"),
                "before_contract_id": None,
                "after_contract_id": after_case.get("contract_id")
            })

    return delta


def main():
    parser = argparse.ArgumentParser(description="Diff two test runs")
    parser.add_argument("before_run_id", help="Earlier run ID (e.g., r5d-p0-20260310-140345)")
    parser.add_argument("after_run_id", help="Later run ID (e.g., r5d-p05-20260310-141439)")
    parser.add_argument("--output", "-o", help="Output diff JSON path")
    args = parser.parse_args()

    # Load index
    index = load_results_index()
    if not index:
        return 1

    # Verify both runs exist in index
    if args.before_run_id not in index:
        print(f"Error: Before run ID not found in index: {args.before_run_id}")
        return 1

    if args.after_run_id not in index:
        print(f"Error: After run ID not found in index: {args.after_run_id}")
        return 1

    # Load results
    before_result = load_result(args.before_run_id, index)
    after_result = load_result(args.after_run_id, index)

    if not before_result or not after_result:
        return 1

    # Compute diff
    delta = diff_results(before_result, after_result)

    # Output
    output_path = Path(args.output) if args.output else None
    if output_path:
        output_path.write_text(json.dumps(delta, indent=2))
        print(f"Diff written to: {output_path}")
    else:
        print(json.dumps(delta, indent=2))

    # Print summary
    print(f"\nDiff: {args.before_run_id} -> {args.after_run_id}")
    print(f"Before: {delta.get('before_campaign')} @ {delta.get('before_timestamp')}")
    print(f"After: {delta.get('after_campaign')} @ {delta.get('after_timestamp')}")

    summary = delta.get("summary_delta", {})
    print(f"\nSummary delta:")
    print(f"  Total cases change: {summary.get('total_cases_change', 0)}")

    print(f"\nCase deltas: {len(delta.get('case_deltas', []))}")
    for d in delta.get("case_deltas", []):
        print(f"  [{d.get('change_type')}] {d.get('case_id')}: "
              f"{d.get('before_classification')} -> {d.get('after_classification')}")

    return 0


if __name__ == "__main__":
    exit(main())
