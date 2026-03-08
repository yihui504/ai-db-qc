# CLI and Product Workflow Description (Refined)

**Date**: 2026-03-08
**Purpose**: Implementation-ready reference for CLI structure and workflow wrappers

---

## CLI Command Structure

### Entry Point: `ai_db_qa/__main__.py`

```python
"""
AI Database QA Tool - Minimum Viable CLI

Three primary user workflows:
1. validate - Single-database validation
2. compare  - Cross-database differential comparison
3. export   - Result export to reports
"""

import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(
        description="AI Database QA Tool - Test databases, judge correctness, generate reports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Quick Start:
  # Validate a database
  python -m ai_db_qa validate --campaign campaigns/milvus_validation.yaml

  # Compare databases
  python -m ai_db_qa compare --campaign campaigns/differential_comparison.yaml

  # Export reports
  python -m ai_db_qa export --input results/milvus_val/ --type issue-report

Documentation: https://github.com/your-repo/ai-db-qa
        """
    )

    subparsers = parser.add_subparsers(
        dest='command',
        help='Available commands',
        required=True
    )

    # Command: validate
    _add_validate_parser(subparsers)

    # Command: compare
    _add_compare_parser(subparsers)

    # Command: export
    _add_export_parser(subparsers)

    args = parser.parse_args()

    # Dispatch to workflow
    if args.command == 'validate':
        from .workflows.validate import run_validation
        run_validation(args)
    elif args.command == 'compare':
        from .workflows.compare import run_comparison
        run_comparison(args)
    elif args.command == 'export':
        from .workflows.export import run_export
        run_export(args)

def _add_validate_parser(subparsers):
    """Add validate subcommand parser."""
    parser = subparsers.add_parser(
        'validate',
        help='Validate a single database against test cases',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using campaign file (recommended)
  python -m ai_db_qa validate --campaign campaigns/milvus_validation.yaml

  # Using direct parameters
  python -m ai_db_qa validate --db milvus --pack packs/basic_ops.json

  # With custom output
  python -m ai_db_qa validate --db milvus --pack packs/basic_ops.json --output results/my_run
        """
    )

    # Input: campaign OR (db + pack)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        '--campaign',
        type=Path,
        help='Campaign YAML file (recommended: includes db, pack, contract, outputs)'
    )
    input_group.add_argument(
        '--db',
        choices=['milvus', 'seekdb'],
        help='Database type (requires --pack)'
    )

    parser.add_argument(
        '--pack',
        type=Path,
        help='Case pack JSON file (required with --db)'
    )
    parser.add_argument(
        '--contract',
        type=Path,
        help='Contract/profile YAML (optional, uses default if not specified)'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('results'),
        help='Output directory (default: results)'
    )

def _add_compare_parser(subparsers):
    """Add compare subcommand parser."""
    parser = subparsers.add_parser(
        'compare',
        help='Compare two databases using the same test cases',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using campaign file (recommended)
  python -m ai_db_qa compare --campaign campaigns/differential_comparison.yaml

  # Using direct parameters
  python -m ai_db_qa compare --databases milvus,seekdb --pack packs/differential.json --tag v4

  # With custom output
  python -m ai_db_qa compare --databases milvus,seekdb --pack packs/diff.json --output results/my_comparison
        """
    )

    # Input: campaign OR (databases + pack)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        '--campaign',
        type=Path,
        help='Campaign YAML file (recommended: includes databases, pack, outputs)'
    )
    input_group.add_argument(
        '--databases',
        help='Comma-separated database names (e.g., milvus,seekdb)'
    )

    parser.add_argument(
        '--pack',
        type=Path,
        help='Shared case pack JSON file (required with --databases)'
    )
    parser.add_argument(
        '--tag',
        help='Run identifier for the comparison (e.g., v4, experimental)'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('results'),
        help='Output directory (default: results)'
    )

def _add_export_parser(subparsers):
    """Add export subcommand parser."""
    parser = subparsers.add_parser(
        'export',
        help='Export test results to formatted reports',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Export issue report from single-DB validation
  python -m ai_db_qa export --input results/milvus_val/ --type issue-report --output bugs.md

  # Export paper cases from differential comparison
  python -m ai_db_qa export --input results/differential_v4/ --type paper-cases --output cases.md

  # Export summary from multiple runs
  python -m ai_db_qa export --input results/v3-p1/,results/v3-p2/ --type summary --output summary.md
        """
    )

    parser.add_argument(
        '--input',
        type=Path,
        required=True,
        help='Input results directory (single-DB, differential, or comma-separated for aggregated)'
    )
    parser.add_argument(
        '--type',
        required=True,
        choices=['issue-report', 'paper-cases', 'summary'],
        help='Type of report to generate'
    )
    parser.add_argument(
        '--output',
        type=Path,
        required=True,
        help='Output file path'
    )

if __name__ == '__main__':
    main()
```

---

## Workflow Wrappers

### 1. Validate Workflow: `ai_db_qa/workflows/validate.py`

```python
"""
Single-database validation workflow.

Wraps existing pipeline components:
- adapters/milvus_adapter.py, adapters/seekdb_adapter.py
- pipeline/executor.py
- pipeline/preconditions.py
- oracles/
- pipeline/triage.py
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from adapters.milvus_adapter import MilvusAdapter
from adapters.seekdb_adapter import SeekDBAdapter
from pipeline.executor import Executor
from pipeline.preconditions import PreconditionEvaluator
from pipeline.triage import Triage
from oracles.filter_strictness import FilterStrictness
from oracles.write_read_consistency import WriteReadConsistency
from oracles.monotonicity import Monotonicity
from contracts.core.loader import get_default_contract
from contracts.db_profiles.loader import load_profile


def run_validation(args):
    """Execute single-database validation workflow."""
    print(f"🔍 Starting validation workflow...")

    # Load configuration
    if args.campaign:
        config = _load_campaign_config(args.campaign)
        db_config = config['databases'][0]
        pack_path = Path(config['case_pack'])
        contract_path = Path(config.get('contract', {}).get('profile'))
        outputs = config.get('outputs', [])
    else:
        # Direct parameters
        db_config = {'type': args.db}
        pack_path = args.pack
        contract_path = args.contract
        outputs = [{'type': 'issue-report', 'format': 'markdown'}]

    # Load contract and profile
    print(f"📋 Loading contract and profile...")
    contract = get_default_contract()
    if contract_path and contract_path.exists():
        profile = load_profile(contract_path)
    else:
        profile = load_profile(f"contracts/db_profiles/{db_config['type']}_profile.yaml")

    # Load adapter
    print(f"🔌 Connecting to {db_config['type']}...")
    if db_config['type'] == 'milvus':
        adapter = MilvusAdapter({
            'host': db_config.get('host', 'localhost'),
            'port': db_config.get('port', 19530),
            'alias': 'default'
        })
    else:  # seekdb
        adapter = SeekDBAdapter({
            'api_endpoint': f"{db_config.get('host', '127.0.0.1')}:{db_config.get('port', 2881)}"
        })

    # Get runtime snapshot
    snapshot = adapter.get_runtime_snapshot()

    # Create executor
    runtime_context = {
        "collections": snapshot.get("collections", []),
        "indexed_collections": snapshot.get("indexed_collections", []),
        "loaded_collections": snapshot.get("loaded_collections", []),
        "connected": snapshot.get("connected", True),
        "supported_features": ["hybrid_search", "filtering", "multi_model"]
    }

    precond = PreconditionEvaluator(contract, profile, runtime_context)
    precond.load_runtime_snapshot(snapshot)

    oracles = [WriteReadConsistency(validate_ids=True), FilterStrictness(), Monotonicity()]
    executor = Executor(adapter, precond, oracles)
    triage = Triage()

    # Load and run cases
    print(f"📦 Loading case pack from {pack_path}...")
    with open(pack_path, 'r') as f:
        cases_data = json.load(f)

    # Convert to TestCase objects
    from schemas.common import TestCase
    cases = [TestCase(**c) for c in cases_data]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_base = Path(args.output) / f"{db_config['type']}_validation_{timestamp}"
    output_base.mkdir(parents=True, exist_ok=True)

    print(f"🚀 Running {len(cases)} test cases...")
    results = []
    for i, case in enumerate(cases, 1):
        print(f"  [{i}/{len(cases)}] {case.case_id}...", end=' ')
        result = executor.execute_case(case, f"validation_{timestamp}")

        # Triage
        triage_result = triage.classify(case, result, naive=False)
        result.triage_result = triage_result

        results.append(result)
        print(f"{result.observed_outcome}")

    # Save detailed results
    results_file = output_base / "execution_results.jsonl"
    with open(results_file, "w") as f:
        for result in results:
            f.write(json.dumps(result.__dict__, default=str) + "\n")
    print(f"💾 Saved results to {results_file}")

    # Generate requested outputs
    for output_spec in outputs:
        _generate_output(results, output_spec, output_base, db_config['type'])

    print(f"\n✅ Validation complete!")
    print(f"📁 Results: {output_base}")


def _load_campaign_config(campaign_path):
    """Load campaign YAML configuration."""
    import yaml
    with open(campaign_path, 'r') as f:
        return yaml.safe_load(f)


def _generate_output(results, output_spec, output_dir, db_name):
    """Generate requested output type."""
    from .export import generate_issue_report, generate_summary_report

    if output_spec['type'] == 'issue-report':
        report = generate_issue_report(results, f"{db_name} Validation")
        output_file = output_dir / "BUG_REPORT.md"
        output_file.write_text(report)
        print(f"📄 Bug report: {output_file}")

    elif output_spec['type'] == 'summary':
        summary = generate_summary_report(results)
        output_file = output_dir / "summary.json"
        output_file.write_text(summary)
        print(f"📊 Summary: {output_file}")
```

---

### 2. Compare Workflow: `ai_db_qa/workflows/compare.py`

```python
"""
Cross-database differential comparison workflow.

Wraps existing scripts:
- scripts/run_differential_campaign.py
- scripts/analyze_differential_results.py
"""

import json
import sys
import yaml
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from adapters.milvus_adapter import MilvusAdapter
from adapters.seekdb_adapter import SeekDBAdapter
from scripts.run_differential_campaign import run_differential_campaign
from scripts.analyze_differential_results import analyze_and_report


def run_comparison(args):
    """Execute cross-database comparison workflow."""
    print(f"🔬 Starting differential comparison workflow...")

    # Load configuration
    if args.campaign:
        config = _load_campaign_config(args.campaign)
        databases = config['databases']
        pack_path = Path(config['case_pack'])
        tag = config.get('tag', 'comparison')
    else:
        # Direct parameters
        db_names = args.databases.split(',')
        databases = [
            {'type': db.strip()}
            for db in db_names
        ]
        pack_path = args.pack
        tag = args.tag or 'comparison'

    # Create output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_base = Path(args.output) / f"differential_{tag}_{timestamp}"
    output_base.mkdir(parents=True, exist_ok=True)

    print(f"📦 Loading case pack from {pack_path}...")
    with open(pack_path, 'r') as f:
        cases_data = json.load(f)

    # Initialize adapters
    adapters = []
    for db_config in databases:
        print(f"🔌 Connecting to {db_config['type']}...")
        if db_config['type'] == 'milvus':
            adapter = MilvusAdapter({
                'host': db_config.get('host', 'localhost'),
                'port': db_config.get('port', 19530),
                'alias': db_config['type']
            })
        else:  # seekdb
            adapter = SeekDBAdapter({
                'api_endpoint': f"{db_config.get('host', '127.0.0.1')}:{db_config.get('port', 2881)}",
                'alias': db_config['type']
            })
        adapters.append(adapter)

    # Run differential campaign
    print(f"🚀 Running differential campaign with {len(cases_data)} cases...")
    results_by_db = run_differential_campaign(
        adapters,
        cases_data,
        str(output_base),
        tag
    )

    # Analyze and generate report
    print(f"📊 Analyzing differential results...")
    report_path = analyze_and_report(results_by_db, output_base)

    print(f"\n✅ Comparison complete!")
    print(f"📁 Results: {output_base}")
    print(f"📄 Report: {report_path}")


def _load_campaign_config(campaign_path):
    """Load campaign YAML configuration."""
    with open(campaign_path, 'r') as f:
        return yaml.safe_load(f)
```

---

### 3. Export Workflow: `ai_db_qa/workflows/export.py`

```python
"""
Result export workflow.

Generates formatted reports from test results.
"""

import json
import sys
from pathlib import Path
from typing import List
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))


def run_export(args):
    """Execute export workflow."""
    print(f"📝 Starting export workflow...")

    input_paths = [Path(p.strip()) for p in args.input.split(',')]
    output_file = Path(args.output)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Load results
    print(f"📂 Loading results from {len(input_paths)} source(s)...")
    all_results = []
    for input_path in input_paths:
        results = load_results(input_path)
        all_results.extend(results)
        print(f"  - {input_path}: {len(results)} results")

    print(f"📊 Total results: {len(all_results)}")

    # Generate report
    if args.type == 'issue-report':
        report = generate_issue_report(all_results, "Exported Bug Report")
        output_file.write_text(report)
        print(f"📄 Issue report: {output_file}")

    elif args.type == 'paper-cases':
        report = generate_paper_cases(all_results)
        output_file.write_text(report)
        print(f"📄 Paper cases: {output_file}")

    elif args.type == 'summary':
        report = generate_summary_report(all_results)
        output_file.write_text(report)
        print(f"📄 Summary: {output_file}")

    print(f"\n✅ Export complete!")


def load_results(results_dir: Path) -> List:
    """Load results from directory."""
    results_file = results_dir / "execution_results.jsonl"
    if not results_file.exists():
        print(f"⚠️  No execution_results.jsonl found in {results_dir}")
        return []

    results = []
    with open(results_file, 'r') as f:
        for line in f:
            if line.strip():
                results.append(json.loads(line))
    return results


def generate_issue_report(results: List, title: str) -> str:
    """Generate issue-ready bug report."""
    bugs = [r for r in results if is_bug_candidate(r)]

    report = f"""# {title}

**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Total Cases**: {len(results)}
**Bug Candidates**: {len(bugs)}

---

"""

    for i, bug in enumerate(bugs, 1):
        report += f"## Issue #{i}: {bug.get('case_id', 'Unknown')}\n\n"

        if bug.get('triage_result'):
            triage = bug['triage_result']
            report += f"**Type**: {triage.get('bug_type', 'Unknown')}\n"
            report += f"**Severity**: {triage.get('severity', 'Unknown')}\n"
            report += f"**Classification**: {triage.get('classification', 'Unknown')}\n\n"

        report += "### Reproduction\n\n"
        report += "```python\n"
        report += format_reproduction(bug)
        report += "\n```\n\n"

        report += "### Evidence\n\n"
        report += format_evidence(bug)
        report += "\n---\n\n"

    return report


def generate_paper_cases(results: List) -> str:
    """Generate paper-worthy case studies."""
    # Identify genuine differences (differential results only)
    diffs = identify_genuine_differences(results)

    report = f"""# Paper Cases: Behavioral Differences

**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Genuine Differences Found**: {len(diffs)}

---

"""

    for i, diff in enumerate(diffs, 1):
        report += f"## Case {i}: {diff.get('title', 'Unnamed')}\n\n"
        report += f"**Case ID**: {diff.get('case_id', 'Unknown')}\n"
        report += f"**Difference Type**: {diff.get('diff_type', 'Unknown')}\n\n"

        report += "### Description\n\n"
        report += diff.get('description', 'No description available')
        report += "\n\n"

        report += "### Reproduction\n\n"
        report += "```python\n"
        report += diff.get('reproduction', '# No reproduction steps')
        report += "\n```\n\n"

        report += "### Analysis\n\n"
        report += diff.get('analysis', 'No analysis available')
        report += "\n---\n\n"

    return report


def generate_summary_report(results: List) -> str:
    """Generate summary statistics."""
    total = len(results)
    bugs = sum(1 for r in results if is_bug_candidate(r))
    diffs = sum(1 for r in results if is_genuine_diff(r))

    outcome_counts = {}
    for r in results:
        outcome = r.get('observed_outcome', 'unknown')
        outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1

    report = f"""# Validation Summary

**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Total Cases**: {total}

## Overview

| Metric | Count | Percentage |
|--------|-------|------------|
| Total cases | {total} | 100% |
| Bug candidates | {bugs} | {bugs/total*100:.1f}% if total > 0 else 0}% |
| Genuine differences | {diffs} | {diffs/total*100:.1f}% if total > 0 else 0}% |

## Outcome Breakdown

| Outcome | Count | Percentage |
|---------|-------|------------|
"""

    for outcome, count in sorted(outcome_counts.items()):
        pct = count/total*100 if total > 0 else 0
        report += f"| {outcome} | {count} | {pct:.1f}% |\n"

    return report


# Helper functions

def is_bug_candidate(result) -> bool:
    """Check if result represents a bug candidate."""
    if not result.get('triage_result'):
        return False
    triage = result['triage_result']
    classification = triage.get('classification', 'unknown')
    return classification in ['bug', 'likely_bug']


def is_genuine_diff(result) -> bool:
    """Check if result represents a genuine difference."""
    return result.get('is_genuine_difference', False)


def identify_genuine_differences(results: List) -> List:
    """Identify genuine behavioral differences."""
    # This would integrate with analyze_differential_results.py logic
    return [r for r in results if r.get('is_genuine_difference', False)]


def format_reproduction(result) -> str:
    """Format reproduction steps."""
    request = result.get('request', {})
    operation = request.get('operation', 'unknown')
    params = request.get('params', {})

    lines = [
        f"# Operation: {operation}",
        f"params = {params}",
        f"# Execute with your database adapter"
    ]
    return '\n'.join(lines)


def format_evidence(result) -> str:
    """Format evidence from result."""
    evidence = []

    if result.get('gate_trace'):
        evidence.append("**Precondition Checks**:\n")
        for check in result['gate_trace']:
            status = "✓" if check.get('passed') else "✗"
            evidence.append(f"- {status} {check.get('check_name', 'unknown')}")
        evidence.append("")

    if result.get('oracle_results'):
        evidence.append("**Oracle Results**:\n")
        for oracle_name, oracle_result in result['oracle_results'].items():
            passed = oracle_result.get('passed', False)
            status = "✓" if passed else "✗"
            evidence.append(f"- {status} {oracle_name}: {oracle_result.get('message', '')}")
        evidence.append("")

    return '\n'.join(evidence) if evidence else "No evidence available."
```

---

## Summary: Implementation Readiness

### Files to Create

| File | Purpose | Lines of Code |
|------|---------|---------------|
| `ai_db_qa/__init__.py` | Package init | ~5 |
| `ai_db_qa/__main__.py` | CLI entry point | ~150 |
| `ai_db_qa/workflows/__init__.py` | Package | ~5 |
| `ai_db_qa/workflows/validate.py` | Validate workflow | ~150 |
| `ai_db_qa/workflows/compare.py` | Compare workflow | ~100 |
| `ai_db_qa/workflows/export.py` | Export workflow | ~200 |

### Dependencies

All dependencies are **existing components**:
- `adapters/milvus_adapter.py`
- `adapters/seekdb_adapter.py`
- `pipeline/executor.py`
- `pipeline/preconditions.py`
- `pipeline/triage.py`
- `oracles/`
- `scripts/run_differential_campaign.py`
- `scripts/analyze_differential_results.py`

### Testing Strategy

1. **Unit tests**: Mock adapters, test workflow logic
2. **Integration tests**: Use v3 case packs, verify outputs
3. **End-to-end tests**: Run against real databases (Milvus, seekdb)

### Next Steps

1. Create package structure
2. Implement CLI entry point
3. Implement workflow wrappers
4. Convert v3 templates to case packs
5. Test with existing v3 results
