# CLI Productization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a usable CLI product that exposes the existing AI Database QA research framework through four commands: generate, validate, compare, and export.

**Architecture:** Minimal wrapper approach - thin CLI layer (~940 lines) that imports and wraps existing components. No architectural changes to the research framework. Uses standard library argparse for CLI, proper package installation for imports, and YAML/JSON for configuration.

**Tech Stack:** Python 3.8+, argparse (CLI), yaml (config), json (data), pathlib (paths), existing project components (adapters, pipeline, oracles, schemas)

**Design Reference:** `docs/plans/2026-03-08-cli-productization-design.md`

---

## Prerequisites

**Before starting implementation:**

1. Ensure project is in editable install mode:
```bash
cd C:\Users\11428\Desktop\ai-db-qc
pip install -e .
```

2. Verify existing imports work:
```bash
python -c "from adapters.milvus_adapter import MilvusAdapter; print('OK')"
```

3. Read the design document:
```bash
cat docs/plans/2026-03-08-cli-productization-design.md
```

---

## Task 1: Create Package Structure

**Files:**
- Create: `ai_db_qa/__init__.py`
- Create: `ai_db_qa/__main__.py` (skeleton)
- Create: `ai_db_qa/cli_parsers.py` (skeleton)
- Create: `ai_db_qa/workflows/__init__.py`

**Step 1: Create package init file**

```python
# ai_db_qa/__init__.py
"""AI Database QA Tool - Minimal CLI wrapper for database testing."""

__version__ = "0.1.0"
__author__ = "AI-DB-QC Team"
```

**Step 2: Create workflows init file**

```python
# ai_db_qa/workflows/__init__.py
"""Workflow modules for AI Database QA Tool."""
```

**Step 3: Create main entry point skeleton**

```python
# ai_db_qa/__main__.py
"""AI Database QA Tool - Minimum Viable CLI

Four primary workflows:
1. generate - Create case packs from templates/campaigns
2. validate - Single-database validation
3. compare  - Cross-database differential comparison
4. export   - Result export to reports
"""

import argparse


def main():
    parser = argparse.ArgumentParser(
        description="AI Database QA Tool - Test databases, judge correctness, generate reports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Quick Start:
  python -m ai_db_qa generate --campaign campaigns/generate_milvus.yaml
  python -m ai_db_qa validate --campaign campaigns/milvus_validation.yaml
  python -m ai_db_qa compare --campaign campaigns/differential_comparison.yaml
  python -m ai_db_qa export --input results/run/ --type issue-report

Documentation: https://github.com/your-repo/ai-db-qa
        """
    )

    subparsers = parser.add_subparsers(dest='command', required=True)

    # Each workflow adds its own subparser
    from .cli_parsers import (
        add_generate_parser, add_validate_parser,
        add_compare_parser, add_export_parser
    )

    add_generate_parser(subparsers)
    add_validate_parser(subparsers)
    add_compare_parser(subparsers)
    add_export_parser(subparsers)

    args = parser.parse_args()

    # Thin dispatch - no product logic
    if args.command == 'generate':
        from .workflows.generate import run_generate
        run_generate(args)
    elif args.command == 'validate':
        from .workflows.validate import run_validate
        run_validate(args)
    elif args.command == 'compare':
        from .workflows.compare import run_compare
        run_compare(args)
    elif args.command == 'export':
        from .workflows.export import run_export
        run_export(args)


if __name__ == '__main__':
    main()
```

**Step 4: Create CLI parsers skeleton**

```python
# ai_db_qa/cli_parsers.py
"""CLI argument parsers for each workflow."""

from pathlib import Path
import argparse


def add_generate_parser(subparsers):
    """Add generate subcommand parser."""
    parser = subparsers.add_parser(
        'generate',
        help='Generate case packs from templates or campaigns'
    )
    # Input: campaign OR (template + substitutions)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        '--campaign',
        type=Path,
        help='Campaign YAML file with template and substitutions'
    )
    input_group.add_argument(
        '--template',
        type=Path,
        help='Template YAML file (requires --substitutions)'
    )
    parser.add_argument(
        '--substitutions',
        type=str,
        help='Substitutions as key=value,key2=value2 (required with --template)'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('packs/generated_pack.json'),
        help='Output case pack JSON file'
    )


def add_validate_parser(subparsers):
    """Add validate subcommand parser."""
    parser = subparsers.add_parser(
        'validate',
        help='Validate a single database against test cases'
    )
    # Input: campaign OR (db + pack)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        '--campaign',
        type=Path,
        help='Campaign YAML file (recommended)'
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
        help='Contract/profile YAML (optional)'
    )
    parser.add_argument(
        '--host',
        type=str,
        help='Database host (overrides campaign)'
    )
    parser.add_argument(
        '--port',
        type=int,
        help='Database port (overrides campaign)'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('results'),
        help='Output directory'
    )


def add_compare_parser(subparsers):
    """Add compare subcommand parser."""
    parser = subparsers.add_parser(
        'compare',
        help='Compare two databases using the same test cases'
    )
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        '--campaign',
        type=Path,
        help='Campaign YAML file (recommended)'
    )
    input_group.add_argument(
        '--databases',
        type=str,
        help='Comma-separated database names (e.g., milvus,seekdb)'
    )
    parser.add_argument(
        '--pack',
        type=Path,
        help='Shared case pack JSON file (required with --databases)'
    )
    parser.add_argument(
        '--tag',
        type=str,
        help='Run identifier for the comparison'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('results'),
        help='Output directory'
    )


def add_export_parser(subparsers):
    """Add export subcommand parser."""
    parser = subparsers.add_parser(
        'export',
        help='Export test results to formatted reports'
    )
    parser.add_argument(
        '--input',
        type=str,
        required=True,
        help='Input results directory (comma-separated for aggregated)'
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
```

**Step 5: Test basic CLI structure**

```bash
cd C:\Users\11428\Desktop\ai-db-qc
python -m ai_db_qa --help
```

Expected: Help output showing four commands (generate, validate, compare, export)

**Step 6: Commit**

```bash
git add ai_db_qa/
git commit -m "feat(cli): create package structure and CLI skeleton

- Add ai_db_qa package with __init__.py
- Add __main__.py with thin dispatch layer
- Add cli_parsers.py with argument parsers for all workflows
- Add workflows package structure

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 2: Implement Generate Workflow

**Files:**
- Create: `ai_db_qa/workflows/generate.py`
- Test: Manual testing with existing template

**Step 1: Write the generate workflow**

```python
# ai_db_qa/workflows/generate.py
"""Generate case packs from templates/campaigns."""

from pathlib import Path
import json
import yaml

from casegen.generators.instantiator import load_templates, instantiate_all


def run_generate(args):
    """Execute generate workflow."""
    if args.campaign:
        config = _load_campaign_config(args.campaign)
        template_path = Path(config['template'])
        substitutions = _parse_substitutions_from_dict(config.get('substitutions', {}))
        output_path = Path(config.get('output', args.output))
    else:
        template_path = args.template
        substitutions = _parse_substitutions_string(args.substitutions)
        output_path = args.output

    print(f"📦 Loading templates from {template_path}...")
    templates = load_templates(template_path)
    print(f"   Found {len(templates)} templates")

    print(f"🔨 Instantiating {len(templates)} cases...")
    cases = instantiate_all(templates, substitutions)

    # Serialize to JSON (uses existing TestCase schema)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        case_data = [
            {
                "case_id": c.case_id,
                "operation": c.operation.value,
                "params": c.params,
                "expected_validity": c.expected_validity.value,
                "required_preconditions": c.required_preconditions,
                "oracle_refs": c.oracle_refs,
                "rationale": c.rationale
            }
            for c in cases
        ]
        pack_meta = {
            "pack_meta": {
                "name": f"Generated Case Pack",
                "version": "1.0",
                "description": f"Generated from {template_path.name}",
                "author": "ai-db-qa",
                "created": str(Path.cwd().stat().st_mtime)
            },
            "cases": case_data
        }
        json.dump(pack_meta, f, indent=2)

    print(f"✅ Generated {len(cases)} cases → {output_path}")


def _load_campaign_config(path: Path) -> dict:
    """Load campaign configuration for generate."""
    with open(path, 'r') as f:
        return yaml.safe_load(f)


def _parse_substitutions_from_dict(subst_dict: dict) -> dict:
    """Convert campaign substitutions to instantiator format."""
    result = {}
    for key, value in subst_dict.items():
        if isinstance(value, dict):
            # Handle generation specs (for future enhancement)
            if 'fill' in value and 'repeat' in value:
                result[key] = [value['fill']] * value['repeat']
            elif 'json' in key:
                # JSON-encoded string
                result[key.replace('_json', '')] = json.loads(value)
            else:
                result[key] = value
        else:
            result[key] = value
    return result


def _parse_substitutions_string(subst_str: str) -> dict:
    """Parse key=value substitutions from command line."""
    substitutions = {}
    for pair in subst_str.split(','):
        key, value = pair.split('=')
        # Try to parse as JSON for complex values
        try:
            substitutions[key] = json.loads(value)
        except json.JSONDecodeError:
            substitutions[key] = value
    return substitutions
```

**Step 2: Test generate with existing template**

```bash
cd C:\Users\11428\Desktop\ai-db-qc
python -m ai_db_qa generate \
  --template casegen/templates/differential_v3_phase1.yaml \
  --substitutions "collection=test_collection,dimension=128,k=10" \
  --output packs/test_pack.json
```

Expected: Output showing templates loaded and cases generated

**Step 3: Verify generated pack format**

```bash
cat packs/test_pack.json | head -20
```

Expected: Valid JSON with `pack_meta` and `cases` array

**Step 4: Commit**

```bash
git add ai_db_qa/workflows/generate.py
git commit -m "feat(cli): implement generate workflow

- Add run_generate() function
- Support campaign file or template+substitutions input
- Handle JSON-encoded substitutions for complex values
- Output uses existing TestCase schema
- Create pack metadata in output JSON

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 3: Implement Validate Workflow - Part 1 (Config & Setup)

**Files:**
- Create: `ai_db_qa/workflows/validate.py` (first version)
- Test: Manual testing with mock adapter

**Step 1: Write validate workflow with configuration loading**

```python
# ai_db_qa/workflows/validate.py
"""Single-database validation workflow."""

from pathlib import Path
from datetime import datetime
import json
import yaml

from adapters.milvus_adapter import MilvusAdapter
from adapters.seekdb_adapter import SeekDBAdapter
from pipeline.executor import Executor
from pipeline.preconditions import PreconditionEvaluator
from pipeline.triage import Triage
from oracles.write_read_consistency import WriteReadConsistency
from oracles.filter_strictness import FilterStrictness
from oracles.monotonicity import Monotonicity
from contracts.core.loader import get_default_contract
from contracts.db_profiles.loader import load_profile
from schemas.case import TestCase


def run_validate(args):
    """Execute validation workflow."""
    # Load configuration
    config = _load_validation_config(args)

    # Load adapter
    print(f"🔌 Connecting to {config['db_type']}...")
    adapter = _create_adapter(config['db_type'], config['db_config'])
    snapshot = adapter.get_runtime_snapshot()
    print(f"   Connected: {snapshot.get('connected', False)}")

    # Load contract and profile
    contract = get_default_contract()
    profile_path = config.get('profile_path')
    if profile_path and profile_path.exists():
        profile = load_profile(profile_path)
    else:
        profile = load_profile(f"contracts/db_profiles/{config['db_type']}_profile.yaml")

    # Setup executor
    runtime_context = {
        "collections": snapshot.get("collections", []),
        "indexed_collections": snapshot.get("indexed_collections", []),
        "loaded_collections": snapshot.get("loaded_collections", []),
        "connected": snapshot.get("connected", True),
        "supported_features": ["hybrid_search", "filtering", "multi_model"]
    }

    precond = PreconditionEvaluator(contract, profile, runtime_context)
    precond.load_runtime_snapshot(snapshot)

    oracles = [
        WriteReadConsistency(validate_ids=True),
        FilterStrictness(),
        Monotonicity()
    ]
    executor = Executor(adapter, precond, oracles)
    triage = Triage()

    # Load cases
    print(f"📦 Loading case pack from {config['pack_path']}...")
    with open(config['pack_path'], 'r') as f:
        pack_data = json.load(f)
    cases = [TestCase(**c) for c in pack_data['cases']]
    print(f"   Loaded {len(cases)} cases")

    # Create output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_base = Path(config.get('output_dir', 'results')) / f"{config['db_type']}_validation_{timestamp}"
    output_base.mkdir(parents=True, exist_ok=True)

    # Execute cases
    print(f"🚀 Running {len(cases)} test cases...")
    results = []
    for i, case in enumerate(cases, 1):
        print(f"  [{i}/{len(cases)}] {case.case_id}...", end=' ')
        result = executor.execute_case(case, f"validation_{timestamp}")

        triage_result = triage.classify(case, result, naive=False)
        result.triage_result = triage_result
        results.append(result)
        print(f"{result.observed_outcome.value}")

    # Save results
    _save_results(results, cases, output_base, config['db_type'], timestamp, adapter)

    print(f"\n✅ Validation complete!")
    print(f"📁 Results: {output_base}")


def _load_validation_config(args) -> dict:
    """Load validation configuration from campaign or direct params."""
    if args.campaign:
        with open(args.campaign, 'r') as f:
            campaign = yaml.safe_load(f)

        db_entry = campaign['databases'][0]

        return {
            'db_type': db_entry['type'],
            'db_config': {
                'host': db_entry.get('host', 'localhost'),
                'port': db_entry.get('port', _default_port(db_entry['type'])),
                'alias': db_entry.get('alias', 'default')
            },
            'pack_path': Path(campaign['case_pack']),
            'profile_path': Path(campaign.get('contract', {}).get('profile')) if campaign.get('contract') else None,
            'output_dir': Path(args.output) if args.output else Path('results')
        }
    else:
        return {
            'db_type': args.db,
            'db_config': {
                'host': args.host if args.host else 'localhost',
                'port': args.port if args.port else _default_port(args.db),
                'alias': 'default'
            },
            'pack_path': args.pack,
            'profile_path': args.contract,
            'output_dir': args.output
        }


def _default_port(db_type: str) -> int:
    """Get default port for database type."""
    return 19530 if db_type == 'milvus' else 2881


def _create_adapter(db_type: str, db_config: dict):
    """Create database adapter.

    Args:
        db_type: Database type ('milvus' or 'seekdb')
        db_config: Connection config dict (host, port, alias)

    Returns:
        Adapter instance (MilvusAdapter or SeekDBAdapter)
    """
    # Merge type into config for adapter constructors
    config = {**db_config, 'type': db_type}

    if db_type == 'milvus':
        return MilvusAdapter(config)
    elif db_type == 'seekdb':
        return SeekDBAdapter(config)
    else:
        raise ValueError(f"Unknown database type: {db_type}")


def _save_results(results, cases, output_dir: Path, db_type: str, timestamp: str, adapter):
    """Save all required output artifacts."""
    from collections import Counter

    # 1. Save execution results (all cases)
    results_file = output_dir / "execution_results.jsonl"
    with open(results_file, "w") as f:
        for result in results:
            result_dict = result.__dict__ if hasattr(result, '__dict__') else result
            # Convert triage_result to dict if present
            if hasattr(result, 'triage_result') and result.triage_result:
                result_dict = result_dict.copy()
                result_dict['triage_result'] = result.triage_result.__dict__ if hasattr(result.triage_result, '__dict__') else result.triage_result
            f.write(json.dumps(result_dict, default=str) + "\n")
    print(f"💾 execution_results.jsonl: {len(results)} cases")

    # 2. Save triage results (bugs only - filter out None)
    triage_results = [
        result.triage_result.__dict__
        for result in results
        if result.triage_result is not None
    ]
    triage_file = output_dir / "triage_results.json"
    with open(triage_file, "w") as f:
        json.dump(triage_results, f, indent=2)
    print(f"💾 triage_results.json: {len(triage_results)} bugs")

    # 3. Save original cases (for reference)
    cases_file = output_dir / "cases.jsonl"
    with open(cases_file, "w") as f:
        for case in cases:
            case_dict = case.__dict__ if hasattr(case, '__dict__') else case
            f.write(json.dumps(case_dict, default=str) + "\n")
    print(f"💾 cases.jsonl: {len(cases)} cases")

    # 4. Save summary statistics
    bug_type_counts = Counter(t.get('final_type', 'unknown') for t in triage_results)
    outcome_counts = Counter(r.observed_outcome.value for r in results)
    precondition_filtered = sum(1 for r in results if not r.precondition_pass)

    summary = {
        "run_id": f"{db_type}_validation_{timestamp}",
        "run_tag": "validation",
        "db_type": db_type,
        "timestamp": timestamp,
        "total_cases": len(cases),
        "total_executed": len(results),
        "total_bugs": len(triage_results),
        "bug_candidate_counts_by_type": dict(bug_type_counts),
        "precondition_filtered_count": precondition_filtered,
        "non_bug_count": len(cases) - len(triage_results),
        "outcome_counts": dict(outcome_counts)
    }
    summary_file = output_dir / "summary.json"
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"💾 summary.json: {len(triage_results)} bugs found")

    # 5. Save metadata
    metadata = {
        "tool_version": "0.1.0",
        "workflow_type": "validate",
        "db_type": db_type,
        "adapter_used": type(adapter).__name__,
        "config_source": "cli_args",  # TODO: track actual source
        "timestamp": timestamp,
        "run_tag": "validation",
        "run_id": f"{db_type}_validation_{timestamp}",
        "total_cases": len(cases),
        "total_bugs": len(triage_results)
    }
    metadata_file = output_dir / "metadata.json"
    with open(metadata_file, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"💾 metadata.json")
```

**Step 2: Test basic import**

```bash
cd C:\Users\11428\Desktop\ai-db-qc
python -c "from ai_db_qa.workflows.validate import run_validate; print('Import OK')"
```

Expected: "Import OK"

**Step 3: Commit**

```bash
git add ai_db_qa/workflows/validate.py
git commit -m "feat(cli): implement validate workflow - config and execution

- Add run_validate() function
- Support campaign file or direct parameters input
- Implement _load_validation_config() with priority handling
- Implement _create_adapter() with explicit interface
- Implement _save_results() with 5 output artifacts
- Add metadata.json and summary.json with required fields

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 4: Implement Export Workflow - Part 1 (Structure)

**Files:**
- Create: `ai_db_qa/workflows/export.py` (first version)

**Step 1: Write export workflow structure**

```python
# ai_db_qa/workflows/export.py
"""Result export workflow."""

from pathlib import Path
from datetime import datetime
import json

from schemas.common import BugType

# Import reusable functions from analysis scripts
from analysis.export_case_studies import (
    load_run_data, find_representative_cases,
    write_case_studies_markdown
)
from analysis.summarize_runs import (
    load_execution_results, summarize_single_run,
    write_summary_json, write_summary_markdown
)


def run_export(args):
    """Execute export workflow."""
    input_paths = [Path(p.strip()) for p in args.input.split(',')]
    output_file = Path(args.output)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Route to export type
    if args.type == 'issue-report':
        _export_issue_report(input_paths, output_file)
    elif args.type == 'paper-cases':
        _export_paper_cases(input_paths, output_file)
    elif args.type == 'summary':
        _export_summary(input_paths, output_file)


def _export_issue_report(input_paths: list[Path], output_file: Path):
    """Export issue report from single-DB or differential results."""
    print(f"📝 Generating issue report from {len(input_paths)} source(s)...")

    # Load results from all input paths
    all_results = []
    for input_path in input_paths:
        try:
            results = load_execution_results(input_path)
            all_results.extend(results)
            print(f"   {input_path}: {len(results)} results")
        except FileNotFoundError:
            print(f"   Warning: {input_path} not found, skipping")

    # Filter bug candidates using taxonomy-aware filtering
    bugs = [r for r in all_results if _is_bug_candidate(r)]
    print(f"   Found {len(bugs)} bug candidates")

    # Sort by severity then bug type
    bugs.sort(key=lambda r: (
        _get_bug_severity(r.get('triage_result', {})),
        r.get('triage_result', {}).get('final_type', '')
    ))

    # Generate markdown report
    report = _format_issue_report(bugs, datetime.now())
    output_file.write_text(report)
    print(f"📄 Issue report: {output_file}")


def _export_paper_cases(input_paths: list[Path], output_file: Path):
    """Export paper cases from differential results."""
    print(f"📝 Generating paper cases from {len(input_paths)} source(s)...")

    # Load run data for case study export
    runs = []
    for input_path in input_paths:
        try:
            run_data = load_run_data(input_path)
            runs.append(run_data)
            print(f"   {input_path}: loaded")
        except FileNotFoundError:
            print(f"   Warning: {input_path} not found, skipping")

    if not runs:
        print("⚠️  No valid runs found for paper cases")
        return

    # Find representative cases
    case_studies = find_representative_cases(runs)
    print(f"   Found {len(case_studies)} representative cases")

    # Write markdown
    write_case_studies_markdown(case_studies, output_file)
    print(f"📄 Paper cases: {output_file}")


def _export_summary(input_paths: list[Path], output_file: Path):
    """Export summary statistics."""
    print(f"📝 Generating summary from {len(input_paths)} source(s)...")

    summaries = []
    for input_path in input_paths:
        try:
            summary = summarize_single_run(input_path)
            summaries.append(summary)
            print(f"   {input_path}: {summary.get('total_cases', 0)} cases")
        except FileNotFoundError:
            print(f"   Warning: {input_path} not found, skipping")

    # Write format based on output extension
    if output_file.suffix == '.json':
        write_summary_json(summaries, output_file)
    else:
        write_summary_markdown(summaries, output_file)
    print(f"📄 Summary: {output_file}")


# Helper functions

def _is_bug_candidate(result: dict) -> bool:
    """Check if result represents a bug candidate.

    Uses taxonomy-aware filtering:
    - Type-1: Illegal input accepted (BUG)
    - Type-2: Illegal input rejected with poor diagnostics (BUG)
    - Type-2.precondition_failed: Expected failure (NOT a bug - exclude)
    - Type-3: Legal input failed (BUG)
    - Type-4: Semantic oracle violation (BUG)
    - None/missing: Not a bug
    """
    triage = result.get('triage_result')
    if triage is None:
        return False

    bug_type = triage.get('final_type', '')

    # Explicit bug types (excluding precondition_failed)
    bug_types = {
        BugType.TYPE_1.value,          # "type-1"
        BugType.TYPE_2.value,          # "type-2"
        BugType.TYPE_3.value,          # "type-3"
        BugType.TYPE_4.value,          # "type-4"
    }

    # Exclude type-2.precondition_failed (expected behavior, not a bug)
    return bug_type in bug_types


def _get_bug_severity(triage: dict) -> str:
    """Get bug severity from triage result.

    Severity mapping:
    - Type-1: HIGH (illegal input accepted - security/correctness risk)
    - Type-2: MEDIUM (poor diagnostics - UX issue)
    - Type-3: HIGH (legal input failed - correctness issue)
    - Type-4: MEDIUM (semantic violation - correctness issue)
    """
    bug_type = triage.get('final_type', '')

    severity_map = {
        BugType.TYPE_1.value: "HIGH",
        BugType.TYPE_2.value: "MEDIUM",
        BugType.TYPE_3.value: "HIGH",
        BugType.TYPE_4.value: "MEDIUM",
    }

    return severity_map.get(bug_type, "UNKNOWN")


def _format_issue_report(bugs: list, generated: datetime) -> str:
    """Format issue report as markdown."""
    lines = [
        f"# Bug Report\n",
        f"**Generated**: {generated.strftime('%Y-%m-%d %H:%M:%S')}\n",
        f"**Total Bugs**: {len(bugs)}\n",
        "---\n"
    ]

    for i, bug in enumerate(bugs, 1):
        case_id = bug.get('case_id', 'unknown')
        triage = bug.get('triage_result', {})
        bug_type = triage.get('final_type', 'unknown')
        severity = _get_bug_severity(triage)

        lines.append(f"## Issue #{i}: {case_id}\n")
        lines.append(f"**Type**: {bug_type}\n")
        lines.append(f"**Severity**: {severity}\n")
        lines.append(f"**Rationale**: {triage.get('rationale', 'No rationale')}\n\n")

        # Add evidence
        lines.append("### Evidence\n\n")
        if bug.get('gate_trace'):
            lines.append("**Precondition Checks**:\n")
            for check in bug['gate_trace']:
                status = "✓" if check.get('passed') else "✗"
                lines.append(f"- {status} {check.get('precondition_name', check.get('check_name', 'unknown'))}\n")
            lines.append("\n")

        if bug.get('oracle_results'):
            lines.append("**Oracle Results**:\n")
            for oracle_name, oracle_result in bug['oracle_results'].items():
                passed = oracle_result.get('passed', False)
                status = "✓" if passed else "✗"
                lines.append(f"- {status} {oracle_name}\n")
            lines.append("\n")

        lines.append("---\n\n")

    return "\n".join(lines)
```

**Step 2: Test import**

```bash
cd C:\Users\11428\Desktop\ai-db-qc
python -c "from ai_db_qa.workflows.export import run_export; print('Import OK')"
```

Expected: "Import OK"

**Step 3: Commit**

```bash
git add ai_db_qa/workflows/export.py
git commit -m "feat(cli): implement export workflow structure

- Add run_export() function with type routing
- Implement _export_issue_report() with taxonomy-aware filtering
- Implement _export_paper_cases() using existing analysis functions
- Implement _export_summary() with JSON/Markdown support
- Add _is_bug_candidate() with explicit bug type filtering
- Add _get_bug_severity() with severity mapping
- Add _format_issue_report() for markdown output

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 5: Update pyproject.toml for Package Installation

**Files:**
- Modify: `pyproject.toml`

**Step 1: Update pyproject.toml**

Check if `pyproject.toml` exists and has proper configuration:

```bash
cd C:\Users\11428\Desktop\ai-db-qc
cat pyproject.toml
```

If missing or incomplete, update it:

```toml
[project]
name = "ai-db-qa"
version = "0.1.0"
description = "AI Database QA Tool - Test databases, judge correctness, generate reports"
readme = "README.md"
requires-python = ">=3.8"
dependencies = [
    "pymilvus>=2.3.0",
    "pyyaml>=6.0",
    "pydantic>=2.0.0",
]

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project.scripts]
ai-db-qa = "ai_db_qa.__main__:main"
```

**Step 2: Reinstall package in editable mode**

```bash
cd C:\Users\11428\Desktop\ai-db-qc
pip install -e .
```

Expected: Successfully installed ai-db-qa

**Step 3: Verify CLI works**

```bash
ai-db-qa --help
```

Expected: Help output showing four commands

**Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "chore: update pyproject.toml for package installation

- Add project metadata and dependencies
- Add [project.scripts] entry point for ai-db-qa CLI
- Enable editable install: pip install -e .

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 6: Create Example Campaign Files

**Files:**
- Create: `campaigns/generate_milvus_validation.yaml`
- Create: `campaigns/milvus_validation.yaml`
- Create: `campaigns/differential_comparison.yaml`

**Step 1: Create generate campaign**

```yaml
# campaigns/generate_milvus_validation.yaml
name: "Milvus Validation Case Pack"
template: casegen/templates/differential_v3_phase1.yaml
substitutions:
  # Scalar values
  collection: "test_collection"
  dimension: 128
  k: 10

  # Vector values - use JSON-encoded strings for complex data
  # In practice, users would generate these with scripts or tools
  query_vector_json: "[0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1]"

output: packs/milvus_validation_pack.json
```

**Step 2: Create validate campaign**

```yaml
# campaigns/milvus_validation.yaml
name: "Milvus Basic Validation"
version: "1.0"
description: "Validate Milvus against core test cases"

# Database configuration
databases:
  - type: milvus
    host: localhost
    port: 19530
    alias: default

# Test cases (pre-instantiated pack)
case_pack: packs/milvus_validation_pack.json

# Expected behavior
contract:
  profile: contracts/db_profiles/milvus_profile.yaml

# Correctness judgment
oracles:
  - name: write_read_consistency
    config:
      validate_ids: true
  - name: filter_strictness
    config: {}
  - name: monotonicity
    config: {}

# Execution options
execution:
  parallel: false
  timeout_seconds: 30
  continue_on_failure: true

# Output specifications
outputs:
  - type: issue-report
    format: markdown
    file: BUG_REPORT.md
  - type: summary
    format: json
    file: summary.json
```

**Step 3: Create compare campaign**

```yaml
# campaigns/differential_comparison.yaml
name: "Milvus vs SeekDB Comparison"
version: "1.0"
description: "Compare behavior on shared test cases"
tag: "v4"

# Databases to compare
databases:
  - type: milvus
    host: localhost
    port: 19530
    alias: milvus

  - type: seekdb
    host: 127.0.0.1
    port: 2881
    alias: seekdb

# Shared test cases
case_pack: packs/milvus_validation_pack.json

# Expected behavior
contract:
  profile: contracts/db_profiles/generic_profile.yaml

# Correctness judgment
oracles:
  - name: write_read_consistency
    config:
      validate_ids: true
  - name: filter_strictness
    config: {}
  - name: monotonicity
    config: {}

# Execution options
execution:
  mode: differential
  parallel: true
  timeout_seconds: 30
  continue_on_failure: true

# Output specifications
outputs:
  - type: differential
    format: markdown
    file: differential_report.md
  - type: issue-report
    format: markdown
    file: BUG_REPORT.md
```

**Step 4: Create campaigns directory**

```bash
cd C:\Users\11428\Desktop\ai-db-qc
mkdir -p campaigns packs
```

**Step 5: Commit**

```bash
git add campaigns/
git commit -m "docs(cli): add example campaign files

- Add generate_milvus_validation.yaml for case pack generation
- Add milvus_validation.yaml for single-DB validation
- Add differential_comparison.yaml for cross-database comparison
- Create campaigns/ and packs/ directories

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 7: Implement Compare Workflow

**Files:**
- Create: `ai_db_qa/workflows/compare.py`

**Step 1: Extract reusable function from run_differential_campaign.py**

First, let's check the existing script structure:

```bash
cd C:\Users\11428\Desktop\ai-db-qc
head -50 scripts/run_differential_campaign.py
```

**Step 2: Write compare workflow**

```python
# ai_db_qa/workflows/compare.py
"""Cross-database differential comparison workflow."""

from pathlib import Path
from datetime import datetime
import json
import yaml

from adapters.milvus_adapter import MilvusAdapter
from adapters.seekdb_adapter import SeekDBAdapter
from pipeline.executor import Executor
from pipeline.preconditions import PreconditionEvaluator
from pipeline.triage import Triage
from oracles.write_read_consistency import WriteReadConsistency
from oracles.filter_strictness import FilterStrictness
from oracles.monotonicity import Monotonicity
from contracts.core.loader import get_default_contract
from contracts.db_profiles.loader import load_profile
from schemas.case import TestCase


def run_compare(args):
    """Execute comparison workflow."""
    # Load configuration
    config = _load_comparison_config(args)

    # Create output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    tag = config.get('tag', 'comparison')
    output_base = Path(config.get('output_dir', 'results')) / f"differential_{tag}_{timestamp}"
    output_base.mkdir(parents=True, exist_ok=True)

    # Load cases
    print(f"📦 Loading case pack from {config['pack_path']}...")
    with open(config['pack_path'], 'r') as f:
        pack_data = json.load(f)
    cases = [TestCase(**c) for c in pack_data['cases']]
    print(f"   Loaded {len(cases)} cases")

    # Run on each database
    results_by_db = {}
    adapters_used = []
    for db_config in config['databases']:
        db_type = db_config['type']
        db_output_dir = output_base / db_type
        db_output_dir.mkdir(exist_ok=True)

        print(f"\n{'='*60}")
        print(f"  Running on {db_type}")
        print(f"{'='*60}\n")

        # Run validation on this database
        adapter, results = _run_single_db_validation(
            db_config, cases, db_output_dir, f"{tag}_{timestamp}"
        )
        results_by_db[db_type] = results
        adapters_used.append(type(adapter).__name__)

    # Analyze differential results
    print(f"\n📊 Analyzing differential results...")
    differential_details = _analyze_differential(results_by_db, cases)

    # Save differential artifacts
    _save_differential_artifacts(
        differential_details, output_base, tag, timestamp,
        config, adapters_used
    )

    print(f"\n✅ Comparison complete!")
    print(f"📁 Results: {output_base}")


def _load_comparison_config(args) -> dict:
    """Load comparison configuration from campaign or direct params."""
    if args.campaign:
        with open(args.campaign, 'r') as f:
            campaign = yaml.safe_load(f)

        return {
            'databases': campaign['databases'],
            'pack_path': Path(campaign['case_pack']),
            'tag': campaign.get('tag'),
            'output_dir': Path(args.output) if args.output else Path('results')
        }
    else:
        db_names = args.databases.split(',')
        databases = []
        for db_name in db_names:
            db_type = db_name.strip()
            databases.append({
                'type': db_type,
                'host': 'localhost',
                'port': 19530 if db_type == 'milvus' else 2881,
                'alias': db_type
            })

        return {
            'databases': databases,
            'pack_path': args.pack,
            'tag': args.tag or 'comparison',
            'output_dir': args.output
        }


def _run_single_db_validation(db_config, cases, output_dir, run_id):
    """Run validation on a single database.

    Returns: (adapter, results) tuple
    """
    from ai_db_qa.workflows.validate import _create_adapter
    from collections import Counter

    # Load adapter
    db_type = db_config['type']
    adapter = _create_adapter(db_type, db_config)
    snapshot = adapter.get_runtime_snapshot()
    print(f"   Connected: {snapshot.get('connected', False)}")

    # Load contract and profile
    contract = get_default_contract()
    profile_path = f"contracts/db_profiles/{db_type}_profile.yaml"
    profile = load_profile(profile_path)

    # Setup executor
    runtime_context = {
        "collections": snapshot.get("collections", []),
        "indexed_collections": snapshot.get("indexed_collections", []),
        "loaded_collections": snapshot.get("loaded_collections", []),
        "connected": snapshot.get("connected", True),
        "supported_features": ["hybrid_search", "filtering", "multi_model"]
    }

    precond = PreconditionEvaluator(contract, profile, runtime_context)
    precond.load_runtime_snapshot(snapshot)

    oracles = [
        WriteReadConsistency(validate_ids=True),
        FilterStrictness(),
        Monotonicity()
    ]
    executor = Executor(adapter, precond, oracles)
    triage = Triage()

    # Execute cases
    print(f"🚀 Running {len(cases)} test cases...")
    results = []
    for i, case in enumerate(cases, 1):
        print(f"  [{i}/{len(cases)}] {case.case_id}...", end=' ')
        result = executor.execute_case(case, run_id)
        triage_result = triage.classify(case, result, naive=False)
        result.triage_result = triage_result
        results.append(result)
        print(f"{result.observed_outcome.value}")

    # Save per-database artifacts (reuse validate logic)
    from ai_db_qa.workflows.validate import _save_results
    _save_results(results, cases, output_dir, db_type, run_id.replace(f"{run_id.split('_')[0]}_", ''), adapter)

    return adapter, results


def _analyze_differential(results_by_db: dict, cases) -> dict:
    """Analyze differential results between databases.

    Returns differential details with:
    - genuine_differences: Cases where outcomes differ
    - stricter_db: Which database is stricter overall
    - per_case_analysis: Detailed comparison per case
    """
    db_names = list(results_by_db.keys())
    if len(db_names) < 2:
        raise ValueError("Need at least 2 databases for comparison")

    # Compare outcomes
    db1_results = {r.case_id: r for r in results_by_db[db_names[0]]}
    db2_results = {r.case_id: r for r in results_by_db[db_names[1]]}

    genuine_differences = []
    milvus_strict_count = 0
    seekdb_strict_count = 0

    for case in cases:
        r1 = db1_results.get(case.case_id)
        r2 = db2_results.get(case.case_id)

        if not r1 or not r2:
            continue

        # Check if outcomes differ (one succeeds, one fails)
        if r1.observed_outcome.value != r2.observed_outcome.value:
            if r1.observed_outcome.value == 'failure' and r2.observed_outcome.value == 'success':
                genuine_differences.append({
                    'case_id': case.case_id,
                    'difference_type': f"{db_names[0]}_rejects_{db_names[1]}_accepts",
                    f'{db_names[0]}_outcome': r1.observed_outcome.value,
                    f'{db_names[1]}_outcome': r2.observed_outcome.value,
                    'interpretation': f"{db_names[0].capitalize()} rejects, {db_names[1].capitalize()} accepts"
                })
                if db_names[0] == 'milvus':
                    milvus_strict_count += 1
                else:
                    seekdb_strict_count += 1
            elif r2.observed_outcome.value == 'failure' and r1.observed_outcome.value == 'success':
                genuine_differences.append({
                    'case_id': case.case_id,
                    'difference_type': f"{db_names[1]}_rejects_{db_names[0]}_accepts",
                    f'{db_names[0]}_outcome': r1.observed_outcome.value,
                    f'{db_names[1]}_outcome': r2.observed_outcome.value,
                    'interpretation': f"{db_names[1].capitalize()} rejects, {db_names[0].capitalize()} accepts"
                })
                if db_names[1] == 'milvus':
                    milvus_strict_count += 1
                else:
                    seekdb_strict_count += 1

    # Determine stricter database
    if milvus_strict_count > seekdb_strict_count:
        stricter_db = 'milvus'
    elif seekdb_strict_count > milvus_strict_count:
        stricter_db = 'seekdb'
    else:
        stricter_db = 'none'

    return {
        'total_cases': len(cases),
        'genuine_difference_count': len(genuine_differences),
        'stricter_db': stricter_db,
        'genuine_differences': genuine_differences,
        'milvus_strict_count': milvus_strict_count,
        'seekdb_strict_count': seekdb_strict_count
    }


def _save_differential_artifacts(differential_details: dict, output_dir: Path,
                                 tag: str, timestamp: str, config: dict, adapters_used: list):
    """Save differential comparison artifacts."""

    # 1. Save differential_details.json
    details_file = output_dir / "differential_details.json"
    with open(details_file, "w") as f:
        json.dump(differential_details, f, indent=2, default=str)
    print(f"💾 differential_details.json")

    # 2. Save differential_report.md
    report = _format_differential_report(differential_details, tag, timestamp, config)
    report_file = output_dir / "differential_report.md"
    report_file.write_text(report)
    print(f"💾 differential_report.md")

    # 3. Save comparison_metadata.json
    metadata = {
        "tool_version": "0.1.0",
        "workflow_type": "compare",
        "databases": config['databases'],
        "adapter_used": adapters_used,
        "config_source": "cli_args",  # TODO: track actual source
        "timestamp": timestamp,
        "run_tag": tag,
        "comparison_id": f"differential_{tag}_{timestamp}",
        "total_cases": differential_details.get('total_cases', 0),
        "genuine_differences": differential_details.get('genuine_difference_count', 0),
        "stricter_db": differential_details.get('stricter_db', 'none')
    }
    metadata_file = output_dir / "comparison_metadata.json"
    with open(metadata_file, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"💾 comparison_metadata.json")


def _format_differential_report(details: dict, tag: str, timestamp: str, config: dict) -> str:
    """Format differential comparison report as markdown."""
    db_names = [db['type'] for db in config['databases']]

    lines = [
        f"# Differential Comparison Report\n",
        f"**Tag**: {tag}\n",
        f"**Timestamp**: {timestamp}\n",
        f"**Databases**: {', '.join(db_names)}\n",
        "---\n\n",

        f"## Summary\n",
        f"- **Total Cases**: {details.get('total_cases', 0)}\n",
        f"- **Genuine Differences**: {details.get('genuine_difference_count', 0)}\n",
        f"- **Stricter Database**: {details.get('stricter_db', 'N/A')}\n",
        "\n---\n\n",

        f"## Genuine Differences\n",
    ]

    for diff in details.get('genuine_differences', []):
        case_id = diff.get('case_id', 'unknown')
        diff_type = diff.get('difference_type', 'unknown')

        lines.append(f"### {case_id}\n")
        lines.append(f"**Difference Type**: {diff_type}\n")
        lines.append(f"**Interpretation**: {diff.get('interpretation', 'N/A')}\n\n")

    return "\n".join(lines)
```

**Step 3: Commit**

```bash
git add ai_db_qa/workflows/compare.py
git commit -m "feat(cli): implement compare workflow

- Add run_compare() function
- Implement _load_comparison_config() with campaign/direct params
- Implement _run_single_db_validation() reusing validate logic
- Implement _analyze_differential() for cross-database comparison
- Implement _save_differential_artifacts() with 3 output files
- Add comparison_metadata.json following convention 1
- Import _create_adapter and _save_results from validate workflow

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 8: Update Validate Workflow to Import Shared Functions

**Files:**
- Modify: `ai_db_qa/workflows/validate.py`

**Step 1: Update validate.py to expose shared functions**

Add at the top of validate.py to ensure functions can be imported:

```python
# Add these exports at the bottom of validate.py
__all__ = ['run_validate', '_create_adapter', '_save_results', '_default_port']
```

**Step 2: Test imports work**

```bash
cd C:\Users\11428\Desktop\ai-db-qc
python -c "from ai_db_qa.workflows.validate import _create_adapter, _save_results; print('Import OK')"
```

Expected: "Import OK"

**Step 3: Commit**

```bash
git add ai_db_qa/workflows/validate.py
git commit -m "refactor(cli): export shared functions from validate workflow

- Add __all__ to export _create_adapter, _save_results, _default_port
- Allow compare workflow to import shared functions

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 9: Integration Testing

**Files:**
- Test: Manual integration testing

**Step 1: Test generate command**

```bash
cd C:\Users\11428\Desktop\ai-db-qc

# Test with template directly
ai-db-qa generate \
  --template casegen/templates/differential_v3_phase1.yaml \
  --substitutions "collection=test,dimension=128,k=10" \
  --output packs/integration_test_pack.json
```

Expected: Success message with case count

**Step 2: Verify generated pack**

```bash
cat packs/integration_test_pack.json | python -m json.tool | head -30
```

Expected: Valid JSON with pack_meta and cases

**Step 3: Test validate command (with mock/real database)**

Note: This requires a running database. Skip if not available.

**Step 4: Test export command with sample data**

First, create sample results directory structure:

```bash
cd C:\Users\11428\Desktop\ai-db-qc
mkdir -p results/test_export
```

Create a sample execution_results.jsonl:

```bash
cat > results/test_export/execution_results.jsonl << 'EOF'
{"case_id": "test_case_1", "run_id": "test_20260308", "adapter_name": "MockAdapter", "request": {"operation": "test", "params": {}}, "response": {"status": "success"}, "observed_outcome": "success", "precondition_pass": true, "gate_trace": [], "oracle_results": [], "triage_result": null}
{"case_id": "test_case_2", "run_id": "test_20260308", "adapter_name": "MockAdapter", "request": {"operation": "test", "params": {}}, "response": {"status": "failure", "error": "Test error"}, "observed_outcome": "failure", "precondition_pass": true, "gate_trace": [], "oracle_results": [], "triage_result": {"final_type": "type-3", "rationale": "Test bug"}}
EOF
```

Test export:

```bash
ai-db-qa export \
  --input results/test_export/ \
  --type issue-report \
  --output results/test_export/bugs.md
```

Expected: Bug report generated

**Step 5: Verify export output**

```bash
cat results/test_export/bugs.md
```

Expected: Markdown bug report

**Step 6: Create documentation**

```bash
cd C:\Users\11428\Desktop\ai-db-qc

cat > README_CLI.md << 'EOF'
# AI Database QA Tool - CLI

## Quick Start

### Installation

```bash
pip install -e .
```

### Generate Case Pack

```bash
# From campaign file
ai-db-qa generate --campaign campaigns/generate_milvus_validation.yaml

# From template directly
ai-db-qa generate \
  --template casegen/templates/differential_v3_phase1.yaml \
  --substitutions "collection=test,dimension=128,k=10" \
  --output packs/test_pack.json
```

### Validate Database

```bash
# Using campaign file
ai-db-qa validate --campaign campaigns/milvus_validation.yaml

# Using direct parameters
ai-db-qa validate \
  --db milvus \
  --pack packs/milvus_validation_pack.json \
  --host localhost \
  --port 19530
```

### Compare Databases

```bash
ai-db-qa compare --campaign campaigns/differential_comparison.yaml
```

### Export Results

```bash
# Export issue report
ai-db-qa export \
  --input results/milvus_validation_20260308_120000/ \
  --type issue-report \
  --output bugs.md

# Export summary
ai-db-qa export \
  --input results/run1/,results/run2/ \
  --type summary \
  --output summary.md
```

## Output Artifacts

### Validate Output

```
results/<db_type>_validation_<timestamp>/
├── execution_results.jsonl
├── triage_results.json
├── cases.jsonl
├── summary.json
└── metadata.json
```

### Compare Output

```
results/differential_<tag>_<timestamp>/
├── milvus/
│   ├── execution_results.jsonl
│   ├── triage_results.json
│   ├── cases.jsonl
│   ├── summary.json
│   └── metadata.json
├── seekdb/
│   └── (same structure)
├── differential_details.json
├── differential_report.md
└── comparison_metadata.json
```

## Campaign File Format

See `campaigns/` directory for examples.
EOF
```

**Step 7: Commit documentation**

```bash
git add README_CLI.md
git commit -m "docs(cli): add CLI quick start documentation

- Add installation instructions
- Add usage examples for all four commands
- Document output artifact structures
- Reference example campaign files

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 10: Final Integration and Cleanup

**Files:**
- Various cleanup and verification

**Step 1: Run full help output**

```bash
cd C:\Users\11428\Desktop\ai-db-qc
ai-db-qa --help
ai-db-qa generate --help
ai-db-qa validate --help
ai-db-qa compare --help
ai-db-qa export --help
```

Expected: All help outputs display correctly

**Step 2: Verify package structure**

```bash
cd C:\Users\11428\Desktop\ai-db-qc
find ai_db_qa/ -type f -name "*.py"
```

Expected: List of all Python files in package

**Step 3: Check for TODOs and fix critical ones**

```bash
cd C:\Users\11428\Desktop\ai-db-qc
grep -r "TODO" ai_db_qa/
```

**Step 4: Final commit**

```bash
git add ai_db_qa/ campaigns/ README_CLI.md
git commit -m "feat(cli): complete CLI productization milestone 1

All four workflows implemented:
- generate: Template/campaign to case pack conversion
- validate: Single-database validation with 5 output artifacts
- compare: Cross-database differential comparison
- export: Result export with taxonomy-aware filtering

Package structure:
- ai_db_qa/__init__.py
- ai_db_qa/__main__.py (thin dispatch)
- ai_db_qa/cli_parsers.py (argument parsing)
- ai_db_qa/workflows/generate.py
- ai_db_qa/workflows/validate.py
- ai_db_qa/workflows/compare.py
- ai_db_qa/workflows/export.py

Key features:
- YAML-safe campaign format
- Proper package imports (no sys.path manipulation)
- Explicit adapter creation interface
- Comprehensive output artifacts (metadata.json, summary.json conventions)
- Taxonomy-aware bug candidate filtering

Documentation:
- README_CLI.md with quick start guide
- Example campaign files in campaigns/

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Testing Checklist

Before considering the implementation complete:

- [ ] Package installs successfully: `pip install -e .`
- [ ] CLI help works: `ai-db-qa --help`
- [ ] Generate creates valid case pack
- [ ] Generate handles JSON-encoded substitutions
- [ ] Validate loads configuration correctly
- [ ] Compare runs on both databases
- [ ] Export filters bugs correctly (excludes type-2.precondition_failed)
- [ ] Export generates markdown reports
- [ ] All output artifacts include required metadata fields
- [ ] All summary.json files include minimum required fields
- [ ] No sys.path.insert in workflow files
- [ ] Adapter creation uses explicit interface

---

## Success Criteria

**Milestone: "Usable Validation Tool"**

- ✅ Four CLI commands working (generate, validate, compare, export)
- ✅ User can run full workflow without reading source code
- ✅ Generated reports are issue-ready or paper-ready
- ✅ No breaking changes to existing components
- ✅ Package structure follows design document
- ✅ All conventions (metadata.json, summary.json) followed

---

**Implementation plan complete. Ready for execution phase.**
