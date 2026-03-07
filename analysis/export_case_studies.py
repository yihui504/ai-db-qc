"""Case study exporter module for extracting representative bug examples.

This module provides functions to load run data, find representative cases
for each bug type, and export them in markdown and JSON formats.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    """Load a JSONL file and return list of dictionaries.

    Args:
        path: Path to the JSONL file

    Returns:
        List of dictionaries parsed from each line

    Raises:
        FileNotFoundError: If the file doesn't exist
        json.JSONDecodeError: If any line is not valid JSON
    """
    results = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                results.append(json.loads(line))
    return results


def load_run_data(run_dir: str | Path) -> Dict[str, Any]:
    """Load cases, results, and triage from a run directory.

    Args:
        run_dir: Path to the run directory

    Returns:
        Dictionary containing:
        - metadata: run_metadata.json content
        - cases: list of test cases from cases.jsonl
        - results: list of execution results from execution_results.jsonl
        - triage: list of triage results from triage_report.json
        - run_id: extracted run_id

    Raises:
        FileNotFoundError: If required files are missing
    """
    run_dir = Path(run_dir)

    # Load all artifacts
    metadata_path = run_dir / "run_metadata.json"
    cases_path = run_dir / "cases.jsonl"
    results_path = run_dir / "execution_results.jsonl"
    triage_path = run_dir / "triage_report.json"

    if not metadata_path.exists():
        raise FileNotFoundError(f"run_metadata.json not found in {run_dir}")
    if not cases_path.exists():
        raise FileNotFoundError(f"cases.jsonl not found in {run_dir}")
    if not results_path.exists():
        raise FileNotFoundError(f"execution_results.jsonl not found in {run_dir}")
    if not triage_path.exists():
        raise FileNotFoundError(f"triage_report.json not found in {run_dir}")

    with open(metadata_path, "r") as f:
        metadata = json.load(f)

    cases = _load_jsonl(cases_path)
    results = _load_jsonl(results_path)

    with open(triage_path, "r") as f:
        triage = json.load(f)

    run_id = metadata.get("run_id", Path(run_dir).name)

    return {
        "metadata": metadata,
        "cases": cases,
        "results": results,
        "triage": triage,
        "run_id": run_id
    }


def find_representative_cases(runs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Find one representative case per bug type across all runs.

    Args:
        runs: List of run data dictionaries from load_run_data()

    Returns:
        List of representative case study dictionaries, one for each:
        - Type-1
        - Type-2
        - Type-2.PreconditionFailed
        - Type-3
        - Type-4
        - Non-bug (cases not in triage)

    Each case study includes:
        run_id, case_id, operation, expected_validity, precondition_pass,
        observed_outcome, bug_type, evidence_files, interpretation
    """
    # Bug types to find
    bug_types_to_find = [
        "type-1",
        "type-2",
        "type-2.precondition_failed",
        "type-3",
        "type-4"
    ]

    # Store representative cases by bug type
    representatives: Dict[str, Dict[str, Any]] = {}
    non_bugs: List[Dict[str, Any]] = []

    # Track all case_ids that were triaged as bugs
    triaged_case_ids: set[str] = set()

    # First pass: find representatives for each bug type
    for run in runs:
        run_id = run["run_id"]
        cases = run["cases"]
        results = run["results"]
        triage = run["triage"]

        # Create lookup dictionaries
        case_by_id: Dict[str, Dict[str, Any]] = {c["case_id"]: c for c in cases}
        result_by_id: Dict[str, Dict[str, Any]] = {r["case_id"]: r for r in results}

        # Track triaged cases
        for triage_entry in triage:
            case_id = triage_entry.get("case_id")
            if case_id:
                triaged_case_ids.add(case_id)

            bug_type = triage_entry.get("final_type", "")
            if bug_type not in bug_types_to_find:
                continue

            # Skip if we already found a representative for this type
            if bug_type in representatives:
                continue

            # Get case and result data
            case = case_by_id.get(case_id, {})
            result = result_by_id.get(case_id, {})

            # Extract precondition_pass from gate_trace if available
            precondition_pass = result.get("precondition_pass")
            if precondition_pass is None:
                # Check gate_trace for precondition status
                gate_trace = result.get("gate_trace", [])
                if gate_trace:
                    # Precondition failed if any gate check failed
                    precondition_pass = all(
                        trace.get("passed", True) for trace in gate_trace
                    )
                else:
                    precondition_pass = True  # No gates = passed

            # Build interpretation string
            interpretation = _build_interpretation(
                triage_entry, case, result
            )

            representatives[bug_type] = {
                "run_id": run_id,
                "case_id": case_id,
                "operation": case.get("operation", "unknown"),
                "expected_validity": case.get("expected_validity", "unknown"),
                "precondition_pass": precondition_pass,
                "observed_outcome": result.get("observed_outcome", "unknown"),
                "bug_type": bug_type,
                "evidence_files": f"{run_id}/",
                "interpretation": interpretation
            }

        # Stop if we found all bug types
        if len(representatives) >= len(bug_types_to_find):
            break

    # Second pass: find a non-bug case
    for run in runs:
        run_id = run["run_id"]
        cases = run["cases"]
        results = run["results"]

        case_by_id: Dict[str, Dict[str, Any]] = {c["case_id"]: c for c in cases}
        result_by_id: Dict[str, Dict[str, Any]] = {r["case_id"]: r for r in results}

        for case in cases:
            case_id = case.get("case_id")
            if not case_id:
                continue

            # Skip if this case was triaged as a bug
            if case_id in triaged_case_ids:
                continue

            result = result_by_id.get(case_id, {})

            # Extract precondition_pass
            precondition_pass = result.get("precondition_pass", True)
            if precondition_pass is None:
                gate_trace = result.get("gate_trace", [])
                if gate_trace:
                    precondition_pass = all(
                        trace.get("passed", True) for trace in gate_trace
                    )
                else:
                    precondition_pass = True

            # Found a non-bug case
            non_bugs.append({
                "run_id": run_id,
                "case_id": case_id,
                "operation": case.get("operation", "unknown"),
                "expected_validity": case.get("expected_validity", "unknown"),
                "precondition_pass": precondition_pass,
                "observed_outcome": result.get("observed_outcome", "unknown"),
                "bug_type": "non-bug",
                "evidence_files": f"{run_id}/",
                "interpretation": "Correct behavior - no bug detected"
            })

            # Only need one non-bug
            if len(non_bugs) >= 1:
                break

        if len(non_bugs) >= 1:
            break

    # Build final list in order
    case_studies: List[Dict[str, Any]] = []

    # Add bug types in order
    for bug_type in bug_types_to_find:
        if bug_type in representatives:
            case_studies.append(representatives[bug_type])

    # Add non-bug if found
    if non_bugs:
        case_studies.append(non_bugs[0])

    return case_studies


def _build_interpretation(
    triage_entry: Dict[str, Any],
    case: Dict[str, Any],
    result: Dict[str, Any]
) -> str:
    """Build a short interpretation description for a case.

    Args:
        triage_entry: Triage result dictionary
        case: Test case dictionary
        result: Execution result dictionary

    Returns:
        Short description string
    """
    bug_type = triage_entry.get("final_type", "unknown")
    rationale = triage_entry.get("rationale", "")

    if bug_type == "type-1":
        return f"Illegal input accepted: {rationale}"
    elif bug_type == "type-2":
        return f"Illegal input rejected, lacks diagnostic: {rationale}"
    elif bug_type == "type-2.precondition_failed":
        return f"Expected failure (precondition not met): {rationale}"
    elif bug_type == "type-3":
        return f"Legal input failed: {rationale}"
    elif bug_type == "type-4":
        return f"Semantic oracle violation: {rationale}"
    else:
        return rationale or "See triage report for details"


def write_case_studies_markdown(cases: List[Dict[str, Any]], output_path: str | Path) -> None:
    """Write case studies to markdown format.

    Args:
        cases: List of case study dictionaries from find_representative_cases()
        output_path: Path to output markdown file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append("# Representative Case Studies\n")
    lines.append("This document contains representative examples for each bug type ")
    lines.append("identified during testing.\n")

    for i, case in enumerate(cases, 1):
        bug_type = case.get("bug_type", "unknown")
        lines.append(f"## Case Study {i}: {bug_type}\n")

        lines.append(f"**Run ID:** `{case.get('run_id', 'unknown')}`  \n")
        lines.append(f"**Case ID:** `{case.get('case_id', 'unknown')}`  \n")
        lines.append(f"**Operation:** `{case.get('operation', 'unknown')}`  \n")
        lines.append(f"**Expected Validity:** `{case.get('expected_validity', 'unknown')}`  \n")
        lines.append(f"**Precondition Pass:** `{case.get('precondition_pass', True)}`  \n")
        lines.append(f"**Observed Outcome:** `{case.get('observed_outcome', 'unknown')}`  \n")
        lines.append(f"**Bug Type:** `{bug_type}`  \n")
        lines.append(f"**Evidence Files:** `{case.get('evidence_files', '')}`  \n")
        lines.append("\n")
        lines.append(f"**Interpretation:** {case.get('interpretation', 'No interpretation available.')}")
        lines.append("\n")
        lines.append("---\n")

    with open(output_path, "w") as f:
        f.write("\n".join(lines))


def write_case_studies_json(cases: List[Dict[str, Any]], output_path: str | Path) -> None:
    """Write case studies to JSON format.

    Args:
        cases: List of case study dictionaries from find_representative_cases()
        output_path: Path to output JSON file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(cases, f, indent=2)


def main() -> None:
    """CLI entry point for case study export."""
    parser = argparse.ArgumentParser(
        description="Export representative case studies from evaluation runs"
    )
    parser.add_argument(
        "--runs-dir",
        type=str,
        default="runs",
        help="Base directory containing run directories (default: runs)"
    )
    parser.add_argument(
        "--run-tags",
        type=str,
        nargs="*",
        default=None,
        help="Optional list of run tags to filter (default: all runs)"
    )
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Output directory path (will write case_studies.md and case_studies.json)"
    )

    args = parser.parse_args()

    # Find and load run directories
    base_dir = Path(args.runs_dir)
    if not base_dir.exists():
        raise FileNotFoundError(f"Runs directory not found: {args.runs_dir}")

    run_dirs = [d for d in base_dir.iterdir() if d.is_dir()]

    # Load run data
    runs = []
    for run_dir in run_dirs:
        try:
            # Load metadata to check run_tag if filtering
            metadata_path = run_dir / "run_metadata.json"
            if args.run_tags is not None and metadata_path.exists():
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)
                run_tag = metadata.get("run_tag", "")
                if run_tag not in args.run_tags:
                    continue

            # Load full run data
            run_data = load_run_data(run_dir)
            runs.append(run_data)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            # Skip runs with missing or corrupted files
            print(f"Warning: Skipping {run_dir} due to error: {e}")
            continue

    if not runs:
        print("No valid runs found matching criteria")
        return

    # Find representative cases
    case_studies = find_representative_cases(runs)

    if not case_studies:
        print("No case studies found")
        return

    # Write outputs
    output_dir = Path(args.output)
    md_path = output_dir / "case_studies.md"
    json_path = output_dir / "case_studies.json"

    write_case_studies_markdown(case_studies, md_path)
    write_case_studies_json(case_studies, json_path)

    print(f"Exported {len(case_studies)} case studies")
    print(f"  Markdown: {md_path}")
    print(f"  JSON: {json_path}")


if __name__ == "__main__":
    main()
