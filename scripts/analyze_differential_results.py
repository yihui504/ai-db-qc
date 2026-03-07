"""Analyze differential campaign results and produce comparison report.

Usage:
    python scripts/analyze_differential_results.py <run_directory>
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List


# Comparison labels
DIFF_LABELS = {
    "same_behavior": "Both databases behaved identically",
    "seekdb_stricter": "seekdb rejected input that Milvus accepted",
    "milvus_stricter": "Milvus rejected input that seekdb accepted",
    "seekdb_poorer_diagnostic": "Both rejected but seekdb had worse error message",
    "milvus_poorer_diagnostic": "Both rejected but Milvus had worse error message",
    "seekdb_precond_sensitive": "seekdb failed due to precondition, Milvus didn't",
    "milvus_precond_sensitive": "Milvus failed due to precondition, seekdb didn't",
    "outcome_difference": "Different outcomes (other categories)",
}


class DifferentialAnalyzer:
    """Analyze and compare results from two databases."""

    def __init__(self, run_dir: Path):
        self.run_dir = Path(run_dir)
        self.milvus_results = self._load_results(self.run_dir / "milvus")
        self.seekdb_results = self._load_results(self.run_dir / "seekdb")

    def _load_results(self, db_dir: Path) -> Dict[str, Dict]:
        """Load execution results from database directory."""
        results = {}
        results_file = db_dir / "execution_results.jsonl"

        if not results_file.exists():
            return results

        with open(results_file, "r") as f:
            for line in f:
                data = json.loads(line)
                case_id = data.get("case_id")
                if case_id:
                    results[case_id] = data

        return results

    def compare_case(self, case_id: str) -> Dict:
        """Compare a single case across both databases."""
        milvus_result = self.milvus_results.get(case_id, {})
        seekdb_result = self.seekdb_results.get(case_id, {})

        if not milvus_result or not seekdb_result:
            return None

        comparison = {
            "case_id": case_id,
            "milvus_outcome": milvus_result.get("observed_outcome", "unknown"),
            "seekdb_outcome": seekdb_result.get("observed_outcome", "unknown"),
            "milvus_error": milvus_result.get("error", ""),
            "seekdb_error": seekdb_result.get("error", ""),
            "milvus_status": milvus_result.get("status", ""),
            "seekdb_status": seekdb_result.get("status", ""),
        }

        comparison["label"] = self._assign_label(comparison)
        comparison["label_description"] = DIFF_LABELS.get(comparison["label"], "Unknown")

        return comparison

    def _assign_label(self, comparison: Dict) -> str:
        """Assign differential comparison label."""
        milvus_outcome = comparison["milvus_outcome"]
        seekdb_outcome = comparison["seekdb_outcome"]
        milvus_error = comparison.get("milvus_error", "")
        seekdb_error = comparison.get("seekdb_error", "")

        # Both succeeded
        if milvus_outcome == "success" and seekdb_outcome == "success":
            return "same_behavior"

        # Both failed
        if milvus_outcome == "failure" and seekdb_outcome == "failure":
            # Check precondition differences
            if "not exist" in milvus_error.lower() and "not exist" not in seekdb_error.lower():
                return "milvus_precond_sensitive"
            if "not exist" in seekdb_error.lower() and "not exist" not in milvus_error.lower():
                return "seekdb_precond_sensitive"

            # Check diagnostic quality
            milvus_specific = self._is_specific_error(milvus_error)
            seekdb_specific = self._is_specific_error(seekdb_error)

            if milvus_specific and not seekdb_specific:
                return "seekdb_poorer_diagnostic"
            if seekdb_specific and not milvus_specific:
                return "milvus_poorer_diagnostic"

            return "same_behavior"

        # One succeeded, one failed
        if milvus_outcome == "success" and seekdb_outcome == "failure":
            return "seekdb_stricter"
        if milvus_outcome == "failure" and seekdb_outcome == "success":
            return "milvus_stricter"

        return "outcome_difference"

    def _is_specific_error(self, error: str) -> bool:
        """Check if error message is specific."""
        if not error:
            return False

        specific_keywords = [
            "dimension", "top_k", "metric", "collection",
            "must be", "required", "invalid", "expected"
        ]

        error_lower = error.lower()
        return any(kw in error_lower for kw in specific_keywords)

    def generate_report(self) -> Dict:
        """Generate complete differential report."""
        all_case_ids = set(self.milvus_results.keys()) | set(self.seekdb_results.keys())

        comparisons = []
        differential_cases = []

        for case_id in sorted(all_case_ids):
            comparison = self.compare_case(case_id)
            if comparison:
                comparisons.append(comparison)
                if comparison["label"] != "same_behavior":
                    differential_cases.append(comparison)

        # Aggregate statistics
        label_counts = {}
        for comp in comparisons:
            label = comp["label"]
            label_counts[label] = label_counts.get(label, 0) + 1

        return {
            "comparisons": comparisons,
            "differential_cases": differential_cases,
            "total_cases": len(comparisons),
            "differential_count": len(differential_cases),
            "label_counts": label_counts,
            "generated_at": datetime.now().isoformat()
        }


def main():
    parser = argparse.ArgumentParser(description="Analyze differential results")
    parser.add_argument("run_dir", help="Differential campaign run directory")
    parser.add_argument("--output", help="Output file (default: <run_dir>/differential_report.json)")

    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    if not run_dir.exists():
        print(f"ERROR: Run directory not found: {run_dir}")
        return 1

    print("="*60)
    print("  Differential Analysis")
    print("="*60)
    print(f"Run directory: {run_dir}")
    print()

    # Analyze
    analyzer = DifferentialAnalyzer(run_dir)
    report = analyzer.generate_report()

    # Print summary
    print(f"Total cases compared: {report['total_cases']}")
    print(f"Differential cases: {report['differential_count']}")
    print()
    print("Label breakdown:")
    for label, count in sorted(report["label_counts"].items()):
        desc = DIFF_LABELS.get(label, label)
        print(f"  {count:2d} {label}: {desc}")

    # Save JSON report
    output_file = Path(args.output) if args.output else run_dir / "differential_report.json"
    with open(output_file, "w") as f:
        json.dump(report, f, indent=2)

    print()
    print(f"JSON report: {output_file}")

    # Generate Markdown report
    markdown_file = run_dir / "differential_report.md"
    _generate_markdown_report(report, markdown_file)
    print(f"Markdown report: {markdown_file}")

    return 0


def _generate_markdown_report(report: Dict, output_file: Path):
    """Generate human-readable markdown report."""

    lines = [
        "# Milvus-vs-seekdb Differential Report",
        "",
        f"**Generated**: {report['generated_at']}",
        f"**Total Cases**: {report['total_cases']}",
        f"**Differential Cases**: {report['differential_count']}",
        "",
        "## Aggregate Comparison Table",
        "",
        "| Label | Count | Description |",
        "|-------|-------|-------------|"
    ]

    for label, count in sorted(report["label_counts"].items()):
        desc = DIFF_LABELS.get(label, label)
        lines.append(f"| {label} | {count} | {desc} |")

    lines.extend([
        "",
        "## Differential Case List",
        "",
        "Cases with different behavior between Milvus and seekdb:",
        "",
        "| Case ID | Label | Milvus | seekdb | Milvus Error | seekdb Error |",
        "|---------|-------|--------|--------|--------------|--------------|"
    ])

    for case in report["differential_cases"]:
        me = case['milvus_error'][:40] + "..." if len(case['milvus_error']) > 40 else case['milvus_error']
        se = case['seekdb_error'][:40] + "..." if len(case['seekdb_error']) > 40 else case['seekdb_error']
        lines.append(
            f"| {case['case_id']} | {case['label']} | {case['milvus_outcome']} | "
            f"{case['seekdb_outcome']} | {me} | {se} |"
        )

    lines.extend([
        "",
        "## All Cases Comparison",
        "",
        "| Case ID | Label | Milvus | seekdb |",
        "|---------|-------|--------|--------|"
    ])

    for case in report["comparisons"]:
        milvus_symbol = "[OK]" if case["milvus_outcome"] == "success" else "[FAIL]"
        seekdb_symbol = "[OK]" if case["seekdb_outcome"] == "success" else "[FAIL]"
        lines.append(
            f"| {case['case_id']} | {case['label']} | {milvus_symbol} | {seekdb_symbol} |"
        )

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    sys.exit(main())
