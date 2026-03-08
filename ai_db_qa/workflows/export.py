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
    """Export paper cases - read from validate output artifacts."""
    print(f"[Export] Generating paper cases...")

    # Load data from validate artifacts (uses metadata.json, triage_results.json)
    cases_by_type = {}
    for p in input_paths:
        try:
            # Load metadata
            metadata_path = p / "metadata.json"
            triage_path = p / "triage_results.json"
            results_path = p / "execution_results.jsonl"
            cases_path = p / "cases.jsonl"

            if not all([metadata_path.exists(), results_path.exists(), cases_path.exists()]):
                print(f"[Export] Skipped: {p} (missing required artifacts)")
                continue

            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            with open(cases_path, 'r') as f:
                cases = [json.loads(line) for line in f]

            # Load triage results if available
            bugs = []
            if triage_path.exists():
                with open(triage_path, 'r') as f:
                    bugs = json.load(f)

            print(f"[Export] Loaded: {p} ({len(bugs)} bugs found)")

            # Group by bug type for representative cases
            for bug in bugs:
                bug_type = bug.get('final_type', 'unknown')
                if bug_type not in cases_by_type:
                    cases_by_type[bug_type] = []
                cases_by_type[bug_type].append({
                    'metadata': metadata,
                    'bug': bug,
                    'case': next((c for c in cases if c.get('case_id') == bug.get('case_id')), None)
                })

        except FileNotFoundError as e:
            print(f"[Export] Skipped: {p} ({e})")
        except (json.JSONDecodeError, KeyError) as e:
            print(f"[Export] Skipped: {p} (invalid data: {e})")

    if not cases_by_type:
        print("[Export] No bugs found - paper cases require bug findings")
        # Generate empty report
        output_file.write_text("# Paper Cases\n\nNo bug candidates found in the provided runs.\n")
        print(f"[Export] Paper cases: {output_file} (0 cases)")
        return

    # Generate markdown
    lines = ["# Paper Cases\n\n"]
    lines.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    lines.append(f"**Total Bug Types**: {len(cases_by_type)}\n\n")

    for bug_type, cases_list in cases_by_type.items():
        lines.append(f"## {bug_type.upper()}\n\n")
        for case_data in cases_list[:1]:  # One representative per type
            bug = case_data['bug']
            case = case_data['case']
            lines.append(f"### Case: {bug.get('case_id', 'unknown')}\n\n")
            lines.append(f"**Rationale**: {bug.get('rationale', 'N/A')}\n\n")
            if case:
                lines.append(f"**Operation**: {case.get('operation', 'unknown')}\n")
                lines.append(f"**Params**: {json.dumps(case.get('params', {}), indent=2)}\n\n")
            lines.append("---\n\n")

    output_file.write_text(''.join(lines))
    print(f"[Export] Paper cases: {output_file} ({len(cases_by_type)} types)")


def _export_summary(input_paths: List[Path], output_file: Path):
    """Export summary - read summary.json directly from validate outputs."""
    print(f"[Export] Generating summary...")

    summaries = []
    for p in input_paths:
        try:
            # Try summary.json first (created by validate workflow)
            summary_path = p / "summary.json"
            if summary_path.exists():
                with open(summary_path, 'r') as f:
                    summary = json.load(f)
                    summaries.append(summary)
                    print(f"[Export] Loaded summary: {p}")
            else:
                # Fallback to analysis script (expects run_metadata.json)
                summary = summarize_single_run(p)
                summaries.append(summary)
                print(f"[Export] Summarized: {p}")
        except FileNotFoundError as e:
            print(f"[Export] Skipped: {p} ({e})")
        except (json.JSONDecodeError, KeyError) as e:
            print(f"[Export] Skipped: {p} (invalid data: {e})")

    if not summaries:
        print("[Export] No valid runs found")
        return

    # Generate markdown from summaries
    lines = ["# Test Summary\n\n"]
    for summary in summaries:
        run_id = summary.get("run_id", "unknown")
        db_type = summary.get("db_type", "unknown")
        lines.append(f"## {run_id}\n\n")
        lines.append(f"- **Database**: {db_type}\n")
        lines.append(f"- **Total Cases**: {summary.get('total_cases', 0)}\n")
        lines.append(f"- **Total Bugs**: {summary.get('total_bugs', 0)}\n")

        bug_counts = summary.get('bug_candidate_counts_by_type', {})
        if bug_counts:
            lines.append(f"- **Bugs by Type**:\n")
            for bug_type, count in bug_counts.items():
                lines.append(f"  - {bug_type}: {count}\n")

        lines.append(f"- **Precondition Filtered**: {summary.get('precondition_filtered_count', 0)}\n")
        lines.append(f"- **Non-Bugs**: {summary.get('non_bug_count', 0)}\n\n")

    output_file.write_text(''.join(lines))
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
