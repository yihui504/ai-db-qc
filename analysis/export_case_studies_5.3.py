"""Export comprehensive case studies for Phase 5.3.

This module exports representative case studies for all bug types
found in the evaluation runs, plus synthetic examples for missing types.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def _build_interpretation(bug_type: str, rationale: str) -> str:
    """Build a conservative, taxonomy-consistent interpretation."""
    interpretations = {
        "type-1": f"Illegal input accepted: {rationale}",
        "type-2": f"Illegal input rejected, lacks diagnostic: {rationale}",
        "type-2.precondition_failed": f"Expected failure (precondition not met): {rationale}",
        "type-3": f"Legal input failed: {rationale}",
        "type-4": f"Semantic oracle violation: {rationale}",
        "non-bug": "Expected behavior - operation succeeded as designed"
    }
    return interpretations.get(bug_type, rationale)


def load_run_data(run_dir: Path) -> Dict[str, Any]:
    """Load all data from a run directory."""
    with open(run_dir / "cases.jsonl", "r") as f:
        cases = {json.loads(line)["case_id"]: json.loads(line) for line in f}

    with open(run_dir / "execution_results.jsonl", "r") as f:
        results = {json.loads(line)["case_id"]: json.loads(line) for line in f}

    with open(run_dir / "triage_report.json", "r") as f:
        triage = {t["case_id"]: t for t in json.load(f)}

    return {"cases": cases, "results": results, "triage": triage}


def find_representative_cases(base_dir: Path) -> List[Dict[str, Any]]:
    """Find representative cases for each bug type."""
    base_dir = Path(base_dir)
    case_studies = []
    seen_types = set()

    # Priority order for finding examples
    run_dirs = [
        "phase5-baseline_real-20260307-183035",  # Real Milvus
        "phase5-baseline_mock-20260307-183121",  # Mock
    ]

    for run_dir_name in run_dirs:
        run_dir = base_dir / run_dir_name
        if not run_dir.exists():
            continue

        run_data = load_run_data(run_dir)

        # Find one example per bug type
        for case_id, triage_entry in run_data["triage"].items():
            bug_type = triage_entry.get("final_type")
            if bug_type and bug_type not in seen_types:
                case = run_data["cases"][case_id]
                result = run_data["results"][case_id]

                case_study = {
                    "case_id": case_id,
                    "run_id": run_dir_name,
                    "bug_type": bug_type,
                    "operation": case["operation"],
                    "params": case["params"],
                    "expected_validity": case["expected_validity"],
                    "precondition_pass": triage_entry["precondition_pass"],
                    "observed_outcome": triage_entry["observed_outcome"],
                    "error_message": result.get("error_message", ""),
                    "interpretation": _build_interpretation(bug_type, triage_entry.get("rationale", "")),
                }
                case_studies.append(case_study)
                seen_types.add(bug_type)

    # Add non-bug examples (cases not in triage)
    for run_dir_name in run_dirs:
        run_dir = base_dir / run_dir_name
        if not run_dir.exists():
            continue

        run_data = load_run_data(run_dir)

        for case_id, case in run_data["cases"].items():
            if case_id not in run_data["triage"] and "non-bug" not in seen_types:
                result = run_data["results"].get(case_id, {})
                case_study = {
                    "case_id": case_id,
                    "run_id": run_dir_name,
                    "bug_type": "non-bug",
                    "operation": case["operation"],
                    "params": case["params"],
                    "expected_validity": case["expected_validity"],
                    "precondition_pass": result.get("precondition_pass", True),
                    "observed_outcome": result.get("observed_outcome", "success"),
                    "error_message": result.get("error_message", ""),
                    "interpretation": "Expected behavior - operation succeeded as designed",
                }
                case_studies.append(case_study)
                seen_types.add("non-bug")
                break

    return case_studies


def add_synthetic_examples(case_studies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Add synthetic examples for missing bug types."""
    seen_types = {cs["bug_type"] for cs in case_studies}

    # Type-4: Semantic violation (not found in actual runs)
    if "type-4" not in seen_types:
        case_studies.append({
            "case_id": "synthetic-type4-001",
            "run_id": "synthetic",
            "bug_type": "type-4",
            "operation": "search",
            "params": {"collection_name": "test_collection", "query_vector": "[0.1, 0.2, 0.3]", "top_k": 10},
            "expected_validity": "legal",
            "precondition_pass": True,
            "observed_outcome": "success",
            "error_message": "",
            "interpretation": "Semantic oracle violation: Top-K=10 returned only 5 results without explanation",
            "note": "SYNTHETIC EXAMPLE - Type-4 requires oracle-visible violations not present in current test set"
        })

    return case_studies


def write_case_studies_markdown(cases: List[Dict[str, Any]], output_path: str | Path) -> None:
    """Write case studies to markdown format."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append("# Representative Case Studies\n")
    lines.append("This document contains representative examples for each bug type ")
    lines.append("identified during Phase 5.3 evaluation.\n")

    # Sort by bug type for consistent ordering
    type_order = ["type-1", "type-2", "type-2.precondition_failed", "type-3", "type-4", "non-bug"]
    cases_dict = {c["bug_type"]: c for c in cases}

    for i, bug_type in enumerate(type_order, 1):
        if bug_type not in cases_dict:
            lines.append(f"## Case Study {i}: {bug_type}\n")
            lines.append(f"**Status:** NOT FOUND IN CURRENT TEST SET\n")
            lines.append(f"**Reason:** Test set limitations\n")
            lines.append("\n---\n")
            continue

        case = cases_dict[bug_type]

        lines.append(f"## Case Study {i}: {bug_type}\n")
        lines.append(f"**Case ID:** `{case['case_id']}`\n")
        lines.append(f"**Run ID:** `{case['run_id']}`\n")
        lines.append(f"**Operation:** `{case['operation']}`\n")
        lines.append(f"**Expected Validity:** `{case['expected_validity']}`\n")
        lines.append(f"**Precondition Pass:** `{case['precondition_pass']}`\n")
        lines.append(f"**Observed Outcome:** `{case['observed_outcome']}`\n")

        if case.get("note"):
            lines.append(f"**Note:** {case['note']}\n")

        lines.append("\n**Parameters:**\n")
        lines.append(f"```json\n{json.dumps(case['params'], indent=2)}\n```\n")

        if case.get("error_message"):
            lines.append(f"\n**Error Message:**\n```\n{case['error_message']}\n```\n")

        lines.append(f"\n**Interpretation:** {case.get('interpretation', case.get('rationale', 'See triage report'))}\n")
        lines.append("\n---\n")

    with open(output_path, "w") as f:
        f.write("\n".join(lines))


def write_case_studies_json(cases: List[Dict[str, Any]], output_path: str | Path) -> None:
    """Write case studies to JSON format."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(cases, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Export case studies for Phase 5.3")
    parser.add_argument(
        "--runs-dir",
        type=str,
        default="runs",
        help="Base directory containing run directories (default: runs)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="docs/case_studies_phase5.3.md",
        help="Output markdown file path (default: docs/case_studies_phase5.3.md)"
    )

    args = parser.parse_args()

    # Find representative cases
    case_studies = find_representative_cases(Path(args.runs_dir))

    # Add synthetic examples for missing types
    case_studies = add_synthetic_examples(case_studies)

    # Write outputs
    output_md = Path(args.output)
    write_case_studies_markdown(case_studies, output_md)
    write_case_studies_json(case_studies, output_md.with_suffix(".json"))

    print(f"Exported {len(case_studies)} case studies")
    print(f"  Markdown: {output_md}")
    print(f"  JSON: {output_md.with_suffix('.json')}")

    # Report coverage
    found_types = {cs["bug_type"] for cs in case_studies}
    print("\n=== Bug Type Coverage ===")
    for bt in ["type-1", "type-2", "type-2.precondition_failed", "type-3", "type-4", "non-bug"]:
        status = "✓" if bt in found_types else "✗"
        synthetic = " (synthetic)" if bt == "type-4" else ""
        print(f"{status} {bt}{synthetic}")


if __name__ == "__main__":
    main()
