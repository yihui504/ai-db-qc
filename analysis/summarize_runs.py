"""Run summarization module for processing evidence artifacts.

This module provides functions to load, summarize, and report on test runs
by aggregating metrics from execution results and triage reports.
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


def load_run_metadata(run_dir: Path) -> Dict[str, Any]:
    """Load run_metadata.json from a run directory.

    Args:
        run_dir: Path to the run directory

    Returns:
        Dictionary containing run metadata

    Raises:
        FileNotFoundError: If run_metadata.json doesn't exist
        json.JSONDecodeError: If the file is not valid JSON
    """
    metadata_path = run_dir / "run_metadata.json"
    with open(metadata_path, "r") as f:
        return json.load(f)


def _get_triage_mode(run_tag: str) -> str:
    """Determine triage mode from run tag.

    Args:
        run_tag: Run tag string

    Returns:
        "diagnostic" or "naive"
    """
    if "naive" in run_tag.lower():
        return "naive"
    return "diagnostic"


def _normalize_variant_flags(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize variant_flags to expected field names.

    Args:
        metadata: Raw run_metadata dictionary

    Returns:
        Dictionary with normalized fields: gate_enabled, oracle_enabled, triage_mode, milvus_available
    """
    variant_flags = metadata.get("variant_flags", {})
    adapter = metadata.get("adapter", "unknown")

    return {
        "gate_enabled": not variant_flags.get("no_gate", False),
        "oracle_enabled": not variant_flags.get("no_oracle", False),
        "triage_mode": "naive" if variant_flags.get("naive_triage", False) else "diagnostic",
        "milvus_available": adapter == "milvus" and not metadata.get("adapter_fallback", False)
    }


def load_execution_results(run_dir: Path) -> List[Dict[str, Any]]:
    """Load execution_results.jsonl from a run directory.

    Args:
        run_dir: Path to the run directory

    Returns:
        List of execution result dictionaries

    Raises:
        FileNotFoundError: If execution_results.jsonl doesn't exist
    """
    results_path = run_dir / "execution_results.jsonl"
    return _load_jsonl(results_path)


def load_triage_report(run_dir: Path) -> List[Dict[str, Any]]:
    """Load triage_report.json from a run directory.

    Args:
        run_dir: Path to the run directory

    Returns:
        List of triage result dictionaries (bugs only)

    Raises:
        FileNotFoundError: If triage_report.json doesn't exist
    """
    triage_path = run_dir / "triage_report.json"
    with open(triage_path, "r") as f:
        return json.load(f)


def load_cases(run_dir: Path) -> List[Dict[str, Any]]:
    """Load cases.jsonl from a run directory.

    Args:
        run_dir: Path to the run directory

    Returns:
        List of test case dictionaries

    Raises:
        FileNotFoundError: If cases.jsonl doesn't exist
    """
    cases_path = run_dir / "cases.jsonl"
    return _load_jsonl(cases_path)


def summarize_single_run(run_dir: Path) -> Dict[str, Any]:
    """Summarize a single run directory.

    Loads all evidence artifacts and computes summary metrics including:
    - Raw counts (total cases, executions, bugs by type)
    - Derived metrics (pass rates, type shares)

    Args:
        run_dir: Path to the run directory

    Returns:
        Dictionary containing all summary metrics

    Raises:
        FileNotFoundError: If required files are missing
    """
    # Load all artifacts
    metadata = load_run_metadata(run_dir)
    execution_results = load_execution_results(run_dir)
    triage_results = load_triage_report(run_dir)
    cases = load_cases(run_dir)

    # Extract metadata fields
    run_id = metadata.get("run_id", Path(run_dir).name)
    run_tag = metadata.get("run_tag", "")
    adapter = metadata.get("adapter", "unknown")

    # Normalize variant_flags to expected field names
    normalized = _normalize_variant_flags(metadata)
    gate_enabled = normalized["gate_enabled"]
    oracle_enabled = normalized["oracle_enabled"]
    triage_mode = normalized["triage_mode"]
    milvus_available = normalized["milvus_available"]

    # Initialize counters
    total_cases = len(cases)
    total_executed = len(execution_results)

    # Count by input validity
    illegal_cases = 0
    legal_cases = 0
    for case in cases:
        # cases.jsonl uses "expected_validity", triage uses "input_validity"
        validity = case.get("expected_validity", case.get("input_validity", "legal"))
        if validity == "illegal":
            illegal_cases += 1
        else:
            legal_cases += 1

    # Count precondition outcomes
    precondition_pass_count = sum(1 for r in execution_results if r.get("precondition_pass", False))
    precondition_fail_count = total_executed - precondition_pass_count

    # Count observed outcomes
    observed_success_count = sum(1 for r in execution_results if r.get("observed_outcome") == "success")
    observed_failure_count = sum(1 for r in execution_results if r.get("observed_outcome") == "failure")

    # Count oracle results
    oracle_eval_count = 0
    oracle_fail_count = 0
    for result in execution_results:
        oracle_results = result.get("oracle_results", [])
        if oracle_results:
            oracle_eval_count += 1
            # Count if any oracle failed
            if any(not orcl.get("passed", True) for orcl in oracle_results):
                oracle_fail_count += 1

    # Count triage results by bug type
    type1_count = 0
    type2_count = 0
    type2_precondition_failed_count = 0
    type3_count = 0
    type4_count = 0
    non_bug_count = 0

    for triage in triage_results:
        bug_type = triage.get("final_type", "")
        if bug_type == "type-1":
            type1_count += 1
        elif bug_type == "type-2":
            type2_count += 1
        elif bug_type == "type-2.precondition_failed":
            type2_precondition_failed_count += 1
        elif bug_type == "type-3":
            type3_count += 1
        elif bug_type == "type-4":
            type4_count += 1

    # Calculate non_bugs (total cases - bugs)
    total_bugs = len(triage_results)
    non_bug_count = total_cases - total_bugs

    # Derived metrics
    # Count failures from illegal input cases only
    # Create a mapping of case_id to input_validity
    case_validity = {}
    for case in cases:
        case_id = case.get("case_id")
        if case_id:
            # cases.jsonl uses "expected_validity", triage uses "input_validity"
            validity = case.get("expected_validity", case.get("input_validity", "legal"))
            case_validity[case_id] = validity

    illegal_failures = sum(
        1 for r in execution_results
        if (r.get("observed_outcome") == "failure" and
            case_validity.get(r.get("case_id")) == "illegal")
    )

    # Calculate derived metrics with safety checks
    precondition_pass_rate = (
        precondition_pass_count / total_cases if total_cases > 0 else 0.0
    )

    type2_share_among_illegal_failures = (
        type2_count / illegal_failures if illegal_failures > 0 else 0.0
    )

    type4_share_among_oracle_evaluable = (
        type4_count / oracle_eval_count if oracle_eval_count > 0 else 0.0
    )

    non_bug_share = (
        non_bug_count / total_cases if total_cases > 0 else 0.0
    )

    gate_filtered_share = (
        precondition_fail_count / total_cases if total_cases > 0 else 0.0
    )

    # Build summary dictionary
    summary = {
        # Run identification
        "run_id": run_id,
        "run_tag": run_tag,
        "adapter": adapter,
        "gate_enabled": gate_enabled,
        "oracle_enabled": oracle_enabled,
        "triage_mode": triage_mode,
        "milvus_available": milvus_available,

        # Raw counts
        "total_cases": total_cases,
        "total_executed": total_executed,
        "illegal_cases": illegal_cases,
        "legal_cases": legal_cases,
        "precondition_pass_count": precondition_pass_count,
        "precondition_fail_count": precondition_fail_count,
        "observed_success_count": observed_success_count,
        "observed_failure_count": observed_failure_count,
        "type1_count": type1_count,
        "type2_count": type2_count,
        "type2_precondition_failed_count": type2_precondition_failed_count,
        "type3_count": type3_count,
        "type4_count": type4_count,
        "non_bug_count": non_bug_count,
        "oracle_fail_count": oracle_fail_count,
        "oracle_eval_count": oracle_eval_count,

        # Derived metrics
        "precondition_pass_rate": precondition_pass_rate,
        "type2_share_among_illegal_failures": type2_share_among_illegal_failures,
        "type4_share_among_oracle_evaluable": type4_share_among_oracle_evaluable,
        "non_bug_share": non_bug_share,
        "gate_filtered_share": gate_filtered_share,
    }

    return summary


def summarize_all_runs(
    base_dir: Path,
    run_tags: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """Summarize multiple runs.

    Args:
        base_dir: Base directory containing run directories
        run_tags: Optional list of run tags to filter. If None, summarize all runs.

    Returns:
        List of summary dictionaries, one per run

    Raises:
        FileNotFoundError: If base_dir doesn't exist
    """
    base_path = Path(base_dir)
    if not base_path.exists():
        raise FileNotFoundError(f"Base directory not found: {base_dir}")

    summaries = []

    # Find all run directories
    run_dirs = [d for d in base_path.iterdir() if d.is_dir()]

    for run_dir in run_dirs:
        try:
            # Skip if run_tags filter is specified and tag doesn't match
            if run_tags is not None:
                metadata_path = run_dir / "run_metadata.json"
                if not metadata_path.exists():
                    continue
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)
                run_tag = metadata.get("run_tag", "")
                if run_tag not in run_tags:
                    continue

            summary = summarize_single_run(run_dir)
            summaries.append(summary)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            # Skip runs with missing or corrupted files
            print(f"Warning: Skipping {run_dir} due to error: {e}")
            continue

    return summaries


def write_summary_json(summaries: List[Dict[str, Any]], output_path: Path) -> None:
    """Write summaries to JSON file.

    Args:
        summaries: List of summary dictionaries
        output_path: Path to output JSON file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(summaries, f, indent=2)


def write_summary_markdown(summaries: List[Dict[str, Any]], output_path: Path) -> None:
    """Write summaries to Markdown file.

    Args:
        summaries: List of summary dictionaries
        output_path: Path to output Markdown file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append("# Run Summaries\n")

    for summary in summaries:
        run_id = summary.get("run_id", "unknown")
        run_tag = summary.get("run_tag", "")
        lines.append(f"## Run: {run_id}")
        if run_tag:
            lines.append(f"**Tag:** {run_tag}\n")

        lines.append("### Configuration")
        lines.append(f"- Adapter: {summary.get('adapter', 'unknown')}")
        lines.append(f"- Gate Enabled: {summary.get('gate_enabled', False)}")
        lines.append(f"- Oracle Enabled: {summary.get('oracle_enabled', False)}")
        lines.append(f"- Triage Mode: {summary.get('triage_mode', 'unknown')}")
        lines.append(f"- Milvus Available: {summary.get('milvus_available', False)}\n")

        lines.append("### Raw Counts")
        lines.append(f"- Total Cases: {summary.get('total_cases', 0)}")
        lines.append(f"- Total Executed: {summary.get('total_executed', 0)}")
        lines.append(f"- Illegal Cases: {summary.get('illegal_cases', 0)}")
        lines.append(f"- Legal Cases: {summary.get('legal_cases', 0)}")
        lines.append(f"- Precondition Pass: {summary.get('precondition_pass_count', 0)}")
        lines.append(f"- Precondition Fail: {summary.get('precondition_fail_count', 0)}")
        lines.append(f"- Observed Success: {summary.get('observed_success_count', 0)}")
        lines.append(f"- Observed Failure: {summary.get('observed_failure_count', 0)}\n")

        lines.append("### Bug Type Counts")
        lines.append(f"- Type 1: {summary.get('type1_count', 0)}")
        lines.append(f"- Type 2: {summary.get('type2_count', 0)}")
        lines.append(f"- Type 2 (Precondition Failed): {summary.get('type2_precondition_failed_count', 0)}")
        lines.append(f"- Type 3: {summary.get('type3_count', 0)}")
        lines.append(f"- Type 4: {summary.get('type4_count', 0)}")
        lines.append(f"- Non-Bug: {summary.get('non_bug_count', 0)}\n")

        lines.append("### Derived Metrics")
        lines.append(f"- Precondition Pass Rate: {summary.get('precondition_pass_rate', 0.0):.2%}")
        lines.append(f"- Type 2 Share (Illegal Failures): {summary.get('type2_share_among_illegal_failures', 0.0):.2%}")
        lines.append(f"- Type 4 Share (Oracle Evaluable): {summary.get('type4_share_among_oracle_evaluable', 0.0):.2%}")
        lines.append(f"- Non-Bug Share: {summary.get('non_bug_share', 0.0):.2%}")
        lines.append(f"- Gate Filtered Share: {summary.get('gate_filtered_share', 0.0):.2%}\n")

        lines.append("---\n")

    with open(output_path, "w") as f:
        f.write("\n".join(lines))


def main() -> None:
    """CLI entry point for run summarization."""
    parser = argparse.ArgumentParser(
        description="Summarize test runs from evidence artifacts"
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
        help="Output file path (extension determines format: .json or .md)"
    )

    args = parser.parse_args()

    # Summarize runs
    summaries = summarize_all_runs(Path(args.runs_dir), args.run_tags)

    # Write output based on extension
    output_path = Path(args.output)
    if output_path.suffix == ".json":
        write_summary_json(summaries, output_path)
    elif output_path.suffix == ".md":
        write_summary_markdown(summaries, output_path)
    else:
        raise ValueError(f"Unsupported output format: {output_path.suffix}")

    print(f"Summary written to {output_path}")


if __name__ == "__main__":
    main()
