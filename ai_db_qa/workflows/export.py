"""Result export workflow - wraps existing analysis scripts."""

from pathlib import Path
from datetime import datetime
import json
import sys
from typing import List

# Add parent directory to path to import from analysis module
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from analysis.summarize_runs import load_execution_results, summarize_single_run, write_summary_markdown
from analysis.export_case_studies import load_run_data, find_representative_cases, write_case_studies_markdown
from schemas.common import BugType


def run_export(args):
    """Execute export workflow."""
    input_paths = [Path(p.strip()) for p in args.input.split(',')]
    output_file = Path(args.output)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    if args.type == 'issue-report':
        _export_issue_report(input_paths, output_file)
    elif args.type == 'paper-cases':
        _export_paper_cases(input_paths, output_file)
    elif args.type == 'summary':
        _export_summary(input_paths, output_file)


def _export_issue_report(input_paths: List[Path], output_file: Path):
    """Export issue report - wraps existing logic with taxonomy-aware filtering."""
    print(f"[Export] Generating issue report...")

    # Load from execution_results.jsonl (following contract)
    all_results = []
    for p in input_paths:
        results_file = p / "execution_results.jsonl"
        if results_file.exists():
            with open(results_file, 'r') as f:
                for line in f:
                    if line.strip():
                        all_results.append(json.loads(line))
        else:
            print(f"[Export] Warning: {results_file} not found, skipping")

    # Filter: taxonomy-aware (triage_result != null AND not type-2.precondition_failed)
    bug_types_to_include = {"type-1", "type-2", "type-3", "type-4"}
    bugs = [
        r for r in all_results
        if r.get('triage_result') is not None
        and r['triage_result'].get('final_type') in bug_types_to_include
    ]
    print(f"[Export] Found {len(bugs)} bugs (excluding type-2.precondition_failed)")

    # Sort by severity
    bugs.sort(key=lambda r: _get_severity(r.get('triage_result', {}).get('final_type', '')))

    # Generate markdown
    lines = [
        f"# Bug Report\n\n**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n**Bugs**: {len(bugs)}\n\n---\n"
    ]
    for i, bug in enumerate(bugs, 1):
        t = bug['triage_result']
        lines.append(f"## Issue #{i}: {bug['case_id']}\n")
        lines.append(f"**Type**: {t['final_type']}\n")
        lines.append(f"**Severity**: {_get_severity(t['final_type'])}\n")
        lines.append(f"**Rationale**: {t['rationale']}\n\n")
        if bug.get('gate_trace'):
            lines.append("**Preconditions**:\n")
            for g in bug['gate_trace']:
                lines.append(f"- {'✓' if g.get('passed') else '✗'} {g.get('precondition_name', 'unknown')}\n")
            lines.append("\n")
        lines.append("---\n\n")

    output_file.write_text(''.join(lines))
    print(f"[Export] Issue report: {output_file}")


def _export_paper_cases(input_paths: List[Path], output_file: Path):
    """Export paper cases - reuse existing export_case_studies.py."""
    print(f"[Export] Generating paper cases...")

    runs = []
    for p in input_paths:
        try:
            runs.append(load_run_data(p))
            print(f"[Export] Loaded: {p}")
        except FileNotFoundError as e:
            print(f"[Export] Skipped: {p} ({e})")
        except (json.JSONDecodeError, KeyError) as e:
            print(f"[Export] Skipped: {p} (invalid data: {e})")

    if not runs:
        print("[Export] No valid runs found")
        return

    cases = find_representative_cases(runs)
    write_case_studies_markdown(cases, output_file)
    print(f"[Export] Paper cases: {output_file} ({len(cases)} cases)")


def _export_summary(input_paths: List[Path], output_file: Path):
    """Export summary - reuse existing summarize_runs.py."""
    print(f"[Export] Generating summary...")

    summaries = []
    for p in input_paths:
        try:
            summaries.append(summarize_single_run(p))
            print(f"[Export] Summarized: {p}")
        except FileNotFoundError as e:
            print(f"[Export] Skipped: {p} ({e})")
        except (json.JSONDecodeError, KeyError) as e:
            print(f"[Export] Skipped: {p} (invalid data: {e})")

    if not summaries:
        print("[Export] No valid runs found")
        return

    write_summary_markdown(summaries, output_file)
    print(f"[Export] Summary: {output_file} ({len(summaries)} runs)")


def _get_severity(bug_type: str) -> str:
    """Get severity level for a bug type.

    Type-1 and Type-3 are HIGH (incorrect behavior)
    Type-2 and Type-4 are MEDIUM (missing diagnostics/semantic issues)
    """
    severity_map = {
        BugType.TYPE_1.value: "HIGH",
        BugType.TYPE_3.value: "HIGH",
        BugType.TYPE_2.value: "MEDIUM",
        BugType.TYPE_4.value: "MEDIUM",
    }
    return severity_map.get(bug_type, "UNKNOWN")
