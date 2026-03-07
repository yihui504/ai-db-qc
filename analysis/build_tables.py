"""Table builder module for generating comparison tables from run summaries.

This module provides functions to load summarized run data and generate
comparison tables for different experimental configurations.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def load_summaries(summary_path: str | Path) -> List[Dict[str, Any]]:
    """Load phase5_summary.json file.

    Args:
        summary_path: Path to the phase5_summary.json file

    Returns:
        List of summary dictionaries, one per run configuration

    Raises:
        FileNotFoundError: If the summary file doesn't exist
        json.JSONDecodeError: If the file is not valid JSON
    """
    summary_path = Path(summary_path)
    with open(summary_path, "r") as f:
        return json.load(f)


def table1_main_comparison(summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate main configuration comparison table.

    Rows: All 6 run configurations
    Columns: Run, Total, Precond Pass, Failures, T1, T2, T2.PF, T3, T4, Non-bug, Oracle Fail

    Args:
        summaries: List of summary dictionaries from load_summaries()

    Returns:
        Dictionary with:
        - headers: List of column headers
        - rows: List of row data (one per configuration)
    """
    headers = [
        "Run",
        "Total",
        "Precond Pass",
        "Failures",
        "T1",
        "T2",
        "T2.PF",
        "T3",
        "T4",
        "Non-bug",
        "Oracle Fail"
    ]

    rows = []
    for summary in summaries:
        run_tag = summary.get("run_tag", summary.get("run_id", "unknown"))
        row = [
            run_tag,
            summary.get("total_cases", 0),
            summary.get("precondition_pass_count", 0),
            summary.get("observed_failure_count", 0),
            summary.get("type1_count", 0),
            summary.get("type2_count", 0),
            summary.get("type2_precondition_failed_count", 0),
            summary.get("type3_count", 0),
            summary.get("type4_count", 0),
            summary.get("non_bug_count", 0),
            summary.get("oracle_fail_count", 0)
        ]
        rows.append(row)

    return {
        "headers": headers,
        "rows": rows
    }


def table2_gate_effect(summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate gate effect comparison table.

    Compares: baseline_real_runA vs no_gate_real
    Focus: precondition_fail_count, type3_count, type4_count, type2_precondition_failed_count, non_bug_count

    Args:
        summaries: List of summary dictionaries from load_summaries()

    Returns:
        Dictionary with:
        - title: Table title
        - comparison: Description of what is being compared
        - metrics: Dict mapping run tags to their metric values
    """
    # Find the relevant summaries
    baseline = None
    no_gate = None

    for summary in summaries:
        run_tag = summary.get("run_tag", "")
        if run_tag in ("baseline_real_runA", "baseline_real"):
            baseline = summary
        elif run_tag == "no_gate_real":
            no_gate = summary

    if baseline is None or no_gate is None:
        raise ValueError(f"Missing required run configurations. Found tags: {[s.get('run_tag') for s in summaries]}")

    baseline_tag = baseline.get("run_tag", "baseline")
    metrics = {
        baseline_tag: {
            "precondition_fail_count": baseline.get("precondition_fail_count", 0),
            "type3_count": baseline.get("type3_count", 0),
            "type4_count": baseline.get("type4_count", 0),
            "type2_precondition_failed_count": baseline.get("type2_precondition_failed_count", 0),
            "non_bug_count": baseline.get("non_bug_count", 0)
        },
        "no_gate_real": {
            "precondition_fail_count": no_gate.get("precondition_fail_count", 0),
            "type3_count": no_gate.get("type3_count", 0),
            "type4_count": no_gate.get("type4_count", 0),
            "type2_precondition_failed_count": no_gate.get("type2_precondition_failed_count", 0),
            "non_bug_count": no_gate.get("non_bug_count", 0)
        }
    }

    return {
        "title": "Gate Effect Comparison",
        "comparison": f"{baseline.get('run_tag', 'baseline')} vs no_gate_real",
        "metrics": metrics
    }


def table3_oracle_effect(summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate oracle effect comparison table.

    Compares: baseline_real_runA vs no_oracle_real
    Focus: oracle_eval_count, oracle_fail_count, type4_count, non_bug_count

    Args:
        summaries: List of summary dictionaries from load_summaries()

    Returns:
        Dictionary with:
        - title: Table title
        - comparison: Description of what is being compared
        - metrics: Dict mapping run tags to their metric values
    """
    # Find the relevant summaries
    baseline = None
    no_oracle = None

    for summary in summaries:
        run_tag = summary.get("run_tag", "")
        if run_tag in ("baseline_real_runA", "baseline_real"):
            baseline = summary
        elif run_tag == "no_oracle_real":
            no_oracle = summary

    if baseline is None or no_oracle is None:
        raise ValueError(f"Missing required run configurations. Found tags: {[s.get('run_tag') for s in summaries]}")

    baseline_tag = baseline.get("run_tag", "baseline")
    metrics = {
        baseline_tag: {
            "oracle_eval_count": baseline.get("oracle_eval_count", 0),
            "oracle_fail_count": baseline.get("oracle_fail_count", 0),
            "type4_count": baseline.get("type4_count", 0),
            "non_bug_count": baseline.get("non_bug_count", 0)
        },
        "no_oracle_real": {
            "oracle_eval_count": no_oracle.get("oracle_eval_count", 0),
            "oracle_fail_count": no_oracle.get("oracle_fail_count", 0),
            "type4_count": no_oracle.get("type4_count", 0),
            "non_bug_count": no_oracle.get("non_bug_count", 0)
        }
    }

    return {
        "title": "Oracle Effect Comparison",
        "comparison": f"{baseline.get('run_tag', 'baseline')} vs no_oracle_real",
        "metrics": metrics
    }


def table4_triage_effect(summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate triage effect comparison table.

    Compares: baseline_real_runA vs naive_triage_real
    Focus: illegal_cases, observed_failure_count, type2_count, non_bug_count, type2_share_among_illegal_failures

    Args:
        summaries: List of summary dictionaries from load_summaries()

    Returns:
        Dictionary with:
        - title: Table title
        - comparison: Description of what is being compared
        - metrics: Dict mapping run tags to their metric values
    """
    # Find the relevant summaries
    baseline = None
    naive_triage = None

    for summary in summaries:
        run_tag = summary.get("run_tag", "")
        if run_tag in ("baseline_real_runA", "baseline_real"):
            baseline = summary
        elif run_tag == "naive_triage_real":
            naive_triage = summary

    if baseline is None or naive_triage is None:
        raise ValueError(f"Missing required run configurations. Found tags: {[s.get('run_tag') for s in summaries]}")

    baseline_tag = baseline.get("run_tag", "baseline")
    metrics = {
        baseline_tag: {
            "illegal_cases": baseline.get("illegal_cases", 0),
            "observed_failure_count": baseline.get("observed_failure_count", 0),
            "type2_count": baseline.get("type2_count", 0),
            "non_bug_count": baseline.get("non_bug_count", 0),
            "type2_share_among_illegal_failures": baseline.get("type2_share_among_illegal_failures", 0.0)
        },
        "naive_triage_real": {
            "illegal_cases": naive_triage.get("illegal_cases", 0),
            "observed_failure_count": naive_triage.get("observed_failure_count", 0),
            "type2_count": naive_triage.get("type2_count", 0),
            "non_bug_count": naive_triage.get("non_bug_count", 0),
            "type2_share_among_illegal_failures": naive_triage.get("type2_share_among_illegal_failures", 0.0)
        }
    }

    return {
        "title": "Triage Effect Comparison",
        "comparison": f"{baseline.get('run_tag', 'baseline')} vs naive_triage_real",
        "metrics": metrics
    }


def table5_mock_vs_real(summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate mock vs real comparison table.

    Compares: baseline_mock vs baseline_real_runA
    Focus: total_cases, precondition_pass_count, observed_failure_count, type1-5 counts

    Args:
        summaries: List of summary dictionaries from load_summaries()

    Returns:
        Dictionary with:
        - title: Table title
        - comparison: Description of what is being compared
        - metrics: Dict mapping run tags to their metric values
    """
    # Find the relevant summaries
    mock = None
    real = None

    for summary in summaries:
        run_tag = summary.get("run_tag", "")
        if run_tag == "baseline_mock":
            mock = summary
        elif run_tag in ("baseline_real_runA", "baseline_real"):
            real = summary

    if mock is None or real is None:
        raise ValueError(f"Missing required run configurations. Found tags: {[s.get('run_tag') for s in summaries]}")

    real_tag = real.get("run_tag", "baseline_real")
    metrics = {
        "baseline_mock": {
            "total_cases": mock.get("total_cases", 0),
            "precondition_pass_count": mock.get("precondition_pass_count", 0),
            "observed_failure_count": mock.get("observed_failure_count", 0),
            "type1_count": mock.get("type1_count", 0),
            "type2_count": mock.get("type2_count", 0),
            "type2_precondition_failed_count": mock.get("type2_precondition_failed_count", 0),
            "type3_count": mock.get("type3_count", 0),
            "type4_count": mock.get("type4_count", 0),
            "non_bug_count": mock.get("non_bug_count", 0)
        },
        real_tag: {
            "total_cases": real.get("total_cases", 0),
            "precondition_pass_count": real.get("precondition_pass_count", 0),
            "observed_failure_count": real.get("observed_failure_count", 0),
            "type1_count": real.get("type1_count", 0),
            "type2_count": real.get("type2_count", 0),
            "type2_precondition_failed_count": real.get("type2_precondition_failed_count", 0),
            "type3_count": real.get("type3_count", 0),
            "type4_count": real.get("type4_count", 0),
            "non_bug_count": real.get("non_bug_count", 0)
        }
    }

    return {
        "title": "Mock vs Real Comparison",
        "comparison": f"baseline_mock vs {real_tag}",
        "metrics": metrics
    }


def write_all_tables_markdown(tables: Dict[str, Any], output_path: str | Path) -> None:
    """Write all tables to a single markdown file.

    Args:
        tables: Dictionary with table data (keys: table1, table2, etc.)
        output_path: Path to output markdown file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append("# Comparison Tables\n")

    # Table 1: Main Comparison
    if "table1" in tables:
        table1 = tables["table1"]
        lines.append("## Table 1: Main Configuration Comparison\n")
        lines.append("| " + " | ".join(table1["headers"]) + " |")
        lines.append("|" + "|".join(["---"] * len(table1["headers"])) + "|")
        for row in table1["rows"]:
            lines.append("| " + " | ".join(str(v) for v in row) + " |")
        lines.append("")

    # Tables 2-5: Effect comparisons
    for table_num in range(2, 6):
        table_key = f"table{table_num}"
        if table_key not in tables:
            continue

        table = tables[table_key]
        lines.append(f"## Table {table_num}: {table['title']}")
        lines.append(f"**Comparison:** {table['comparison']}\n")

        metrics = table["metrics"]
        if metrics:
            # Get all metric names from the first configuration
            first_config = next(iter(metrics.values()))
            metric_names = list(first_config.keys())

            # Create header
            lines.append("| Metric | " + " | ".join(metrics.keys()) + " |")
            lines.append("|" + "|".join(["---"] * (len(metrics) + 1)) + "|")

            # Add rows for each metric
            for metric_name in metric_names:
                row = [metric_name]
                for config_name in metrics.keys():
                    value = metrics[config_name].get(metric_name, 0)
                    # Format as percentage if it's a share/rate
                    if "share" in metric_name or "rate" in metric_name:
                        row.append(f"{value:.2%}")
                    else:
                        row.append(str(value))
                lines.append("| " + " | ".join(row) + " |")
        lines.append("")

    with open(output_path, "w") as f:
        f.write("\n".join(lines))


def write_table_csvs(tables: Dict[str, Any], output_dir: str | Path) -> None:
    """Write each table to separate CSV files.

    Args:
        tables: Dictionary with table data (keys: table1, table2, etc.)
        output_dir: Directory to write CSV files to
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Table 1: Main Comparison
    if "table1" in tables:
        table1 = tables["table1"]
        csv_path = output_dir / "table1_main_comparison.csv"
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(table1["headers"])
            writer.writerows(table1["rows"])

    # Tables 2-5: Effect comparisons
    for table_num in range(2, 6):
        table_key = f"table{table_num}"
        if table_key not in tables:
            continue

        table = tables[table_key]
        csv_path = output_dir / f"table{table_num}_{table['title'].lower().replace(' ', '_')}.csv"

        metrics = table["metrics"]
        if metrics:
            with open(csv_path, "w", newline="") as f:
                writer = csv.writer(f)

                # Get all metric names from the first configuration
                first_config = next(iter(metrics.values()))
                metric_names = list(first_config.keys())

                # Write header
                writer.writerow(["Metric"] + list(metrics.keys()))

                # Write rows for each metric
                for metric_name in metric_names:
                    row = [metric_name]
                    for config_name in metrics.keys():
                        value = metrics[config_name].get(metric_name, 0)
                        # Format as percentage if it's a share/rate
                        if "share" in metric_name or "rate" in metric_name:
                            row.append(f"{value:.2%}")
                        else:
                            row.append(str(value))
                    writer.writerow(row)


def main() -> None:
    """CLI entry point for table generation."""
    parser = argparse.ArgumentParser(
        description="Generate comparison tables from run summaries"
    )
    parser.add_argument(
        "--summary",
        type=str,
        required=True,
        help="Path to phase5_summary.json file"
    )
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Output path for markdown file"
    )
    parser.add_argument(
        "--csv-dir",
        type=str,
        default=None,
        help="Optional directory to write CSV files (default: no CSV output)"
    )

    args = parser.parse_args()

    # Load summaries
    summaries = load_summaries(args.summary)

    # Generate all tables
    tables = {
        "table1": table1_main_comparison(summaries),
        "table2": table2_gate_effect(summaries),
        "table3": table3_oracle_effect(summaries),
        "table4": table4_triage_effect(summaries),
        "table5": table5_mock_vs_real(summaries)
    }

    # Write markdown output
    write_all_tables_markdown(tables, args.output)
    print(f"Comparison tables written to {args.output}")

    # Write CSV files if requested
    if args.csv_dir:
        write_table_csvs(tables, args.csv_dir)
        print(f"CSV files written to {args.csv_dir}")


if __name__ == "__main__":
    main()
