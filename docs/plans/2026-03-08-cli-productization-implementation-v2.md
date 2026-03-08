# CLI Productization Implementation Plan (Milestone 1)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a usable CLI wrapper for the existing AI Database QA framework with working single-database validation and export workflows.

**Architecture:** Minimal wrapper approach - thin CLI layer that imports and wraps existing components. No architectural changes. Wrap existing analysis logic rather than rewriting.

**Tech Stack:** Python 3.8+, argparse (CLI), yaml (config), json (data), pathlib (paths), existing project components

**Design Reference:** `docs/plans/2026-03-08-cli-productization-design.md`

**Milestone 1 Scope:**
- a) Usable CLI wrapper
- b) Working single-database workflow
- c) Working export workflow
- d) Compare workflow (after above are stable)

---

## Artifact Contracts (Explicit)

### execution_results.jsonl

**Content:** ONE line per executed test case. Each line is a JSON object with:

```json
{
  "case_id": "create_collection_valid",
  "run_id": "milvus_validation_20260308_120000",
  "adapter_name": "MilvusAdapter",
  "request": {"operation": "create_collection", "params": {...}},
  "response": {"status": "success", "data": [...]},
  "observed_outcome": "success",
  "error_message": null,
  "latency_ms": 45.2,
  "precondition_pass": true,
  "gate_trace": [
    {"precondition_name": "operation_exists", "check_type": "legality", "passed": true, "reason": ""}
  ],
  "oracle_results": [],
  "triage_result": null  // Included if triage was run, may be null (non-bug) or object (bug)
}
```

**Key points:**
- EVERY executed case gets a line (bugs and non-bugs)
- `triage_result` field is present for ALL cases
- `triage_result = null` means NOT a bug
- `triage_result = {...}` means IS a bug

### triage_results.json

**Content:** JSON ARRAY containing ONLY bug candidates (triage_result objects where triage classified as bug).

```json
[
  {
    "case_id": "invalid_dimension_negative",
    "run_id": "milvus_validation_20260308_120000",
    "final_type": "type-3",
    "input_validity": "legal",
    "observed_outcome": "failure",
    "precondition_pass": true,
    "rationale": "Legal input failed (precondition satisfied)"
  }
]
```

**Key points:**
- Contains ONLY bugs (triage_result != null AND not type-2.precondition_failed)
- Type-2.precondition_failed is EXCLUDED (expected behavior, not a bug)
- Export reads this file for issue-report generation

**Taxonomy-aware filtering:**
```python
# Bug types to INCLUDE in triage_results.json:
bug_types = {"type-1", "type-2", "type-3", "type-4"}
# EXCLUDE: "type-2.precondition_failed"
```

### Export Input Contracts

| Export Type | Reads From | Output |
|-------------|------------|--------|
| `issue-report` | `execution_results.jsonl` | Markdown bug report |
| `paper-cases` | `triage_results.json` + run data | Markdown case studies |
| `summary` | `summary.json` or computed from results | JSON or Markdown stats |

**Key points:**
- `issue-report` parses `execution_results.jsonl`, filters where `triage_result != null`
- `paper-cases` loads full run data using existing `analysis/export_case_studies.py`
- `summary` uses existing `analysis/summarize_runs.py`

---

## Block 1: Package Skeleton + CLI Parsers

**Goal:** Create package structure, entry point, and argument parsers. Test basic CLI structure.

**Files:**
- Create: `ai_db_qa/__init__.py`
- Create: `ai_db_qa/__main__.py`
- Create: `ai_db_qa/cli_parsers.py`
- Create: `ai_db_qa/workflows/__init__.py`

**Step 1: Create package structure**

```python
# ai_db_qa/__init__.py
"""AI Database QA Tool - Minimal CLI wrapper for database testing."""

__version__ = "0.1.0"
```

```python
# ai_db_qa/workflows/__init__.py
"""Workflow modules for AI Database QA Tool."""
```

**Step 2: Create main entry point**

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
  ai-db-qa generate --campaign campaigns/generate_milvus.yaml
  ai-db-qa validate --campaign campaigns/milvus_validation.yaml
  ai-db-qa export --input results/run/ --type issue-report

Documentation: docs/plans/2026-03-08-cli-productization-design.md
        """
    )

    subparsers = parser.add_subparsers(dest='command', required=True)

    from .cli_parsers import (
        add_generate_parser, add_validate_parser,
        add_compare_parser, add_export_parser
    )

    add_generate_parser(subparsers)
    add_validate_parser(subparsers)
    add_compare_parser(subparsers)
    add_export_parser(subparsers)

    args = parser.parse_args()

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

**Step 3: Create CLI parsers**

```python
# ai_db_qa/cli_parsers.py
"""CLI argument parsers for each workflow."""

from pathlib import Path


def add_generate_parser(subparsers):
    """Add generate subcommand parser."""
    parser = subparsers.add_parser('generate', help='Generate case packs from templates/campaigns')
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--campaign', type=Path, help='Campaign YAML file')
    input_group.add_argument('--template', type=Path, help='Template YAML file')
    parser.add_argument('--substitutions', type=str, help='Substitutions as key=value,key2=value2')
    parser.add_argument('--output', type=Path, default=Path('packs/generated_pack.json'))


def add_validate_parser(subparsers):
    """Add validate subcommand parser."""
    parser = subparsers.add_parser('validate', help='Validate a single database')
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--campaign', type=Path, help='Campaign YAML file')
    input_group.add_argument('--db', choices=['milvus', 'seekdb'], help='Database type')
    parser.add_argument('--pack', type=Path, help='Case pack JSON file')
    parser.add_argument('--contract', type=Path, help='Contract/profile YAML')
    parser.add_argument('--host', type=str, help='Database host (overrides campaign)')
    parser.add_argument('--port', type=int, help='Database port (overrides campaign)')
    parser.add_argument('--output', type=Path, default=Path('results'), help='Output directory')


def add_compare_parser(subparsers):
    """Add compare subcommand parser."""
    parser = subparsers.add_parser('compare', help='Compare two databases')
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--campaign', type=Path, help='Campaign YAML file')
    input_group.add_argument('--databases', type=str, help='Comma-separated: milvus,seekdb')
    parser.add_argument('--pack', type=Path, help='Shared case pack JSON')
    parser.add_argument('--tag', type=str, help='Run identifier')
    parser.add_argument('--output', type=Path, default=Path('results'), help='Output directory')


def add_export_parser(subparsers):
    """Add export subcommand parser."""
    parser = subparsers.add_parser('export', help='Export results to reports')
    parser.add_argument('--input', type=str, required=True, help='Results directory')
    parser.add_argument('--type', required=True, choices=['issue-report', 'paper-cases', 'summary'])
    parser.add_argument('--output', type=Path, required=True, help='Output file')
```

**Step 4: Update pyproject.toml**

```toml
[project]
name = "ai-db-qa"
version = "0.1.0"
description = "AI Database QA Tool"
requires-python = ">=3.8"
dependencies = ["pymilvus>=2.3.0", "pyyaml>=6.0", "pydantic>=2.0.0"]

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project.scripts]
ai-db-qa = "ai_db_qa.__main__:main"
```

**Step 5: Install and test**

```bash
cd C:\Users\11428\Desktop\ai-db-qc
pip install -e .
ai-db-qa --help
```

Expected: Help showing 4 commands

**Step 6: Commit**

```bash
git add ai_db_qa/ pyproject.toml
git commit -m "feat(cli): create package skeleton and CLI structure

- Add ai_db_qa package with entry point
- Add cli_parsers.py for all 4 commands
- Update pyproject.toml for editable install
- Test: ai-db-qa --help works

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Block 2: Generate Workflow

**Goal:** Implement case pack generation from templates. Support campaign files and direct template input.

**Files:**
- Create: `ai_db_qa/workflows/generate.py`
- Create: `campaigns/generate_example.yaml`

**Generate Substitutions Contract:**

**Recommended: Campaign file** (supports structured, complex substitutions)
- Use YAML-native types (scalars, lists)
- For complex vectors: use compact representations or helper scripts
- Example: `dimension: 128`, `k: 10`, `collection: test`

**Minimal: Direct `--substitutions` flag** (simple key=value pairs only)
- Supports: scalar values (strings, numbers)
- Limitations: No lists, no nested structures, no complex types
- Example: `--substitutions "collection=test,dimension=128,k=10"`
- For vectors: Use campaign file instead

**Step 1: Implement generate workflow**

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
        config = _load_yaml(args.campaign)
        template_path = Path(config['template'])
        substitutions = config.get('substitutions', {})
        output_path = Path(config.get('output', args.output))
    else:
        template_path = args.template
        substitutions = _parse_substitutions(args.substitutions or '')
        output_path = args.output

    print(f"📦 Loading templates from {template_path}...")
    templates = load_templates(template_path)
    print(f"   Found {len(templates)} templates")

    print(f"🔨 Instantiating cases...")
    cases = instantiate_all(templates, substitutions)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        # Use centralized serialization helper (avoids hand-maintaining field list)
        case_data = [_serialize_case(c) for c in cases]
        pack_meta = {
            "pack_meta": {
                "name": "Generated Case Pack",
                "version": "1.0",
                "description": f"From {template_path.name}",
                "author": "ai-db-qa",
            },
            "cases": case_data
        }
        json.dump(pack_meta, f, indent=2)

    print(f"✅ Generated {len(cases)} cases → {output_path}")


def _load_yaml(path: Path) -> dict:
    with open(path, 'r') as f:
        return yaml.safe_load(f)


def _parse_substitutions(subst_str: str) -> dict:
    if not subst_str:
        return {}
    result = {}
    for pair in subst_str.split(','):
        if '=' in pair:
            key, value = pair.split('=', 1)
            result[key] = value
    return result


def _serialize_case(case) -> dict:
    """Centralized serialization helper for TestCase objects.

    Aligned with existing schemas.case.TestCase schema.
    If schema changes, update this single function.
    """
    return {
        "case_id": case.case_id,
        "operation": case.operation.value,
        "params": case.params,
        "expected_validity": case.expected_validity.value,
        "required_preconditions": case.required_preconditions,
        "oracle_refs": case.oracle_refs,
        "rationale": case.rationale
    }
```

**Step 2: Create example campaign (compact)**

```yaml
# campaigns/generate_example.yaml
name: "Example Case Pack"
template: casegen/templates/differential_v3_phase1.yaml
substitutions:
  collection: test_collection
  dimension: 128
  k: 10
output: packs/example_pack.json
```

**Step 3: Test generate**

```bash
cd C:\Users\11428\Desktop\ai-db-qc
mkdir -p campaigns packs
# (Copy the example campaign above)
ai-db-qa generate --campaign campaigns/generate_example.yaml
```

Expected: Success message

**Step 4: Commit**

```bash
git add ai_db_qa/workflows/generate.py campaigns/
git commit -m "feat(cli): implement generate workflow with centralized serialization

- Add run_generate() wrapping existing instantiator
- Support campaign file (recommended) and direct template input
- Add _serialize_case() helper (avoids hand-maintaining field list)
- Create example campaign with compact substitutions
- Output uses existing TestCase schema

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Block 3: Validate Workflow

**Goal:** Implement single-database validation with full artifact generation. Wrap existing pipeline components.

**Files:**
- Create: `ai_db_qa/workflows/validate.py`
- Create: `campaigns/validate_example.yaml`

**Step 1: Implement validate workflow**

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
    config = _load_validate_config(args)

    print(f"🔌 Connecting to {config['db_type']}...")
    adapter = _create_adapter(config['db_type'], config['db_config'])
    snapshot = adapter.get_runtime_snapshot()

    contract = get_default_contract()
    profile = load_profile(
        config.get('profile_path') or
        f"contracts/db_profiles/{config['db_type']}_profile.yaml"
    )

    # Derive runtime context from snapshot (no hardcoded feature list)
    runtime_context = {
        "collections": snapshot.get("collections", []),
        "indexed_collections": snapshot.get("indexed_collections", []),
        "loaded_collections": snapshot.get("loaded_collections", []),
        "connected": snapshot.get("connected", True),
        # Derive from profile/adapter if available, otherwise empty set
        "supported_features": snapshot.get("supported_features", profile.get("supported_features", []))
    }

    precond = PreconditionEvaluator(contract, profile, runtime_context)
    precond.load_runtime_snapshot(snapshot)

    oracles = [WriteReadConsistency(validate_ids=True), FilterStrictness(), Monotonicity()]
    executor = Executor(adapter, precond, oracles)
    triage = Triage()

    print(f"📦 Loading cases from {config['pack_path']}...")
    with open(config['pack_path'], 'r') as f:
        pack_data = json.load(f)
    cases = [TestCase(**c) for c in pack_data['cases']]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_base = Path(config.get('output_dir', 'results')) / f"{config['db_type']}_validation_{timestamp}"
    output_base.mkdir(parents=True, exist_ok=True)

    print(f"🚀 Running {len(cases)} cases...")
    results = []
    for i, case in enumerate(cases, 1):
        print(f"  [{i}/{len(cases)}] {case.case_id}...", end=' ')
        result = executor.execute_case(case, f"validation_{timestamp}")
        triage_result = triage.classify(case, result, naive=False)
        result.triage_result = triage_result
        results.append(result)
        print(f"{result.observed_outcome.value}")

    config_source = str(args.campaign) if args.campaign else "cli_args"
    _save_results(results, cases, output_base, config['db_type'], timestamp, adapter, config_source)

    print(f"\n✅ Validation complete! Results: {output_base}")


def _load_validate_config(args) -> dict:
    if args.campaign:
        with open(args.campaign, 'r') as f:
            campaign = yaml.safe_load(f)
        db = campaign['databases'][0]
        return {
            'db_type': db['type'],
            'db_config': {
                'host': args.host or db.get('host', 'localhost'),
                'port': args.port or db.get('port', 19530 if db['type'] == 'milvus' else 2881),
                'alias': db.get('alias', 'default')
            },
            'pack_path': Path(campaign['case_pack']),
            'profile_path': Path(campaign.get('contract', {}).get('profile')) if campaign.get('contract') else None,
            'output_dir': args.output
        }
    else:
        return {
            'db_type': args.db,
            'db_config': {'host': args.host or 'localhost', 'port': args.port or 19530, 'alias': 'default'},
            'pack_path': args.pack,
            'profile_path': args.contract,
            'output_dir': args.output
        }


def _create_adapter(db_type: str, db_config: dict):
    config = {**db_config, 'type': db_type}
    if db_type == 'milvus':
        return MilvusAdapter(config)
    return SeekDBAdapter(config)


def _save_results(results, cases, output_dir: Path, db_type: str, timestamp: str, adapter, config_source: str):
    """Save all output artifacts following explicit contracts."""

    # 1. execution_results.jsonl - ALL cases, triage_result included (may be null)
    with open(output_dir / "execution_results.jsonl", "w") as f:
        for result in results:
            d = result.__dict__.copy()
            d['triage_result'] = result.triage_result.__dict__ if result.triage_result else None
            f.write(json.dumps(d, default=str) + "\n")

    # 2. triage_results.json - ONLY bugs (taxonomy-aware filtering)
    # Exclude type-2.precondition_failed (expected behavior, not a bug)
    bug_types_to_include = {"type-1", "type-2", "type-3", "type-4"}
    bugs = [
        r.triage_result.__dict__
        for r in results
        if r.triage_result is not None
        and r.triage_result.final_type.value in bug_types_to_include
    ]
    with open(output_dir / "triage_results.json", "w") as f:
        json.dump(bugs, f, indent=2)

    # 3. cases.jsonl - original cases
    with open(output_dir / "cases.jsonl", "w") as f:
        for case in cases:
            f.write(json.dumps(case.__dict__, default=str) + "\n")

    # 4. summary.json - with minimum required fields and correct accounting
    bug_counts = {}
    for b in bugs:
        bt = b.get('final_type', 'unknown')
        bug_counts[bt] = bug_counts.get(bt, 0) + 1

    precondition_filtered = sum(1 for r in results if not r.precondition_pass)
    total_bugs = len(bugs)
    ran_successfully = sum(1 for r in results if r.precondition_pass)

    # Tightened accounting: non_bugs are explicitly defined
    # non_bugs = executed cases (precondition_pass=true) with no bug-classifying triage result
    # A triage_result that is None, or is type-2.precondition_failed, means "not a bug"
    non_bugs = sum(
        1 for r in results
        if r.precondition_pass and (
            r.triage_result is None or
            r.triage_result.final_type.value == "type-2.precondition_failed"
        )
    )

    summary = {
        "run_id": f"{db_type}_validation_{timestamp}",
        "run_tag": "validation",
        "db_type": db_type,
        "timestamp": timestamp,
        "total_cases": len(cases),
        "total_executed": ran_successfully + precondition_filtered,
        "bug_candidate_counts_by_type": bug_counts,
        "total_bugs": total_bugs,
        "precondition_filtered_count": precondition_filtered,
        "non_bug_count": non_bugs
    }
    with open(output_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    # 5. metadata.json - with required convention 1 fields
    metadata = {
        "tool_version": "0.1.0",
        "workflow_type": "validate",
        "db_type": db_type,
        "adapter_used": type(adapter).__name__,
        "config_source": config_source,
        "timestamp": timestamp,
        "run_tag": "validation"
    }
    with open(output_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"💾 Saved: execution_results.jsonl ({len(results)}), triage_results.json ({len(bugs)} bugs)")


# Export for use by compare workflow
__all__ = ['run_validate', '_create_adapter', '_save_results']
```

**Step 2: Create example validate campaign**

```yaml
# campaigns/validate_example.yaml
name: "Example Validation"
databases:
  - type: milvus
    host: localhost
    port: 19530
case_pack: packs/example_pack.json
contract:
  profile: contracts/db_profiles/milvus_profile.yaml
```

**Step 3: Test validate (requires running database)**

```bash
cd C:\Users\11428\Desktop\ai-db-qc
ai-db-qa validate --campaign campaigns/validate_example.yaml
```

**Step 4: Verify artifacts**

```bash
cd C:\Users\11428\Desktop\ai-db-qc
ls results/milvus_validation_*/
cat results/milvus_validation_*/metadata.json
cat results/milvus_validation_*/summary.json
```

**Step 5: Commit**

```bash
git add ai_db_qa/workflows/validate.py campaigns/validate_example.yaml
git commit -m "feat(cli): implement validate workflow with taxonomy-aware artifact saving

- Add run_validate() wrapping existing pipeline
- Support campaign and direct parameter input
- Save 5 artifacts: execution_results.jsonl, triage_results.json, cases.jsonl, summary.json, metadata.json
- triage_results.json: ONLY bugs, excludes type-2.precondition_failed (taxonomy-aware)
- summary.json: Distinguishes bugs, precondition-filtered, non-bugs (explicit non-bug definition)
- config_source passed explicitly to _save_results() (no args scope issues)
- Derive supported_features from profile/snapshot (no hardcoded list)
- Export _create_adapter and _save_results for compare reuse

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Block 4: Export Workflow

**Goal:** Implement export using existing analysis scripts. No new analysis logic.

**Files:**
- Create: `ai_db_qa/workflows/export.py`

**Step 1: Implement export workflow**

```python
# ai_db_qa/workflows/export.py
"""Result export workflow - wraps existing analysis scripts."""

from pathlib import Path
from datetime import datetime
import json

# Reuse existing analysis functions
from analysis.summarize_runs import load_execution_results, summarize_single_run, write_summary_markdown
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


def _export_issue_report(input_paths: list[Path], output_file: Path):
    """Export issue report - wraps existing logic with taxonomy-aware filtering."""
    print(f"📝 Generating issue report...")

    # Load from execution_results.jsonl (following contract)
    all_results = []
    for p in input_paths:
        results_file = p / "execution_results.jsonl"
        if results_file.exists():
            with open(results_file, 'r') as f:
                for line in f:
                    if line.strip():
                        all_results.append(json.loads(line))

    # Filter: taxonomy-aware (triage_result != null AND not type-2.precondition_failed)
    bug_types_to_include = {"type-1", "type-2", "type-3", "type-4"}
    bugs = [
        r for r in all_results
        if r.get('triage_result') is not None
        and r['triage_result'].get('final_type') in bug_types_to_include
    ]
    print(f"   Found {len(bugs)} bugs (excluding type-2.precondition_failed)")

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
    print(f"📄 Issue report: {output_file}")


def _export_paper_cases(input_paths: list[Path], output_file: Path):
    """Export paper cases - reuse existing export_case_studies.py."""
    print(f"📝 Generating paper cases...")

    from analysis.export_case_studies import load_run_data, find_representative_cases, write_case_studies_markdown

    runs = []
    for p in input_paths:
        try:
            runs.append(load_run_data(p))
            print(f"   Loaded: {p}")
        except FileNotFoundError:
            print(f"   Skipped: {p} (not found)")

    if not runs:
        print("⚠️  No valid runs")
        return

    cases = find_representative_cases(runs)
    write_case_studies_markdown(cases, output_file)
    print(f"📄 Paper cases: {output_file} ({len(cases)} cases)")


def _export_summary(input_paths: list[Path], output_file: Path):
    """Export summary - reuse existing summarize_runs.py."""
    print(f"📝 Generating summary...")

    summaries = []
    for p in input_paths:
        try:
            summaries.append(summarize_single_run(p))
        except FileNotFoundError:
            pass

    write_summary_markdown(summaries, output_file)
    print(f"📄 Summary: {output_file} ({len(summaries)} runs)")


def _get_severity(bug_type: str) -> str:
    return {
        BugType.TYPE_1.value: "HIGH",
        BugType.TYPE_3.value: "HIGH",
        BugType.TYPE_2.value: "MEDIUM",
        BugType.TYPE_4.value: "MEDIUM",
    }.get(bug_type, "UNKNOWN")
```

**Step 2: Test export**

```bash
cd C:\Users\11428\Desktop\ai-db-qc
# After validate has created results, use the printed output directory
ai-db-qa export --input results/milvus_validation_20260308_120000 --type issue-report --output bugs.md
cat bugs.md
```

**Step 3: Commit**

```bash
git add ai_db_qa/workflows/export.py
git commit -m "feat(cli): implement export workflow with taxonomy-aware filtering

- Add run_export() with type routing
- Wrap existing analysis scripts (summarize_runs, export_case_studies)
- Implement issue-report generation from execution_results.jsonl
- Filter bugs: triage_result != null AND type not in {type-2.precondition_failed}
- Reuse paper-cases and summary from existing code
- Sort bugs by severity (HIGH before MEDIUM)

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Block 5: Compare Workflow (After Validate + Export Stable)

**Goal:** Implement differential comparison after core workflows are stable. Reuse validate logic per database.

**Files:**
- Create: `ai_db_qa/workflows/compare.py`
- Create: `campaigns/compare_example.yaml`

**Step 1: Implement compare workflow**

```python
# ai_db_qa/workflows/compare.py
"""Cross-database differential comparison - wraps existing logic."""

from pathlib import Path
from datetime import datetime
import json
import yaml

from schemas.case import TestCase
from ai_db_qa.workflows.validate import _create_adapter, _save_results


def run_compare(args):
    """Execute comparison workflow."""
    config = _load_compare_config(args)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    tag = config.get('tag', 'comparison')
    output_base = Path(config.get('output_dir', 'results')) / f"differential_{tag}_{timestamp}"
    output_base.mkdir(parents=True, exist_ok=True)

    # Load cases
    with open(config['pack_path'], 'r') as f:
        pack_data = json.load(f)
    cases = [TestCase(**c) for c in pack_data['cases']]

    # Run on each database (reuse validate logic)
    results_by_db = {}
    adapters_used = []
    for db_config in config['databases']:
        db_type = db_config['type']
        db_output = output_base / db_type
        db_output.mkdir(exist_ok=True)

        print(f"\n{'='*60}\n  Running on {db_type}\n{'='*60}")
        adapter, results = _run_db_validation(db_config, cases, db_output, f"{tag}_{timestamp}")
        results_by_db[db_type] = results
        adapters_used.append(type(adapter).__name__)

    # Analyze differential
    print(f"\n📊 Analyzing differential...")
    diff_details = _analyze_differential(results_by_db, cases)

    # Save differential artifacts
    _save_differential_artifacts(diff_details, output_base, tag, timestamp, config, adapters_used)

    print(f"\n✅ Comparison complete! Results: {output_base}")


def _load_compare_config(args) -> dict:
    if args.campaign:
        with open(args.campaign, 'r') as f:
            c = yaml.safe_load(f)
        return {
            'databases': c['databases'],
            'pack_path': Path(c['case_pack']),
            'tag': c.get('tag'),
            'output_dir': args.output,
            '_campaign_path': str(args.campaign)  # Store for metadata
        }
    # Direct params parsing...
    dbs = args.databases.split(',')
    return {
        'databases': [{'type': d.strip(), 'host': 'localhost', 'port': 19530 if d.strip() == 'milvus' else 2881, 'alias': d.strip()} for d in dbs],
        'pack_path': args.pack,
        'tag': args.tag,
        'output_dir': args.output,
        '_campaign_path': 'cli_args'
    }


def _run_db_validation(db_config, cases, output_dir, run_id):
    """Run validation on single DB - reuses validate workflow logic."""
    from contracts.core.loader import get_default_contract
    from contracts.db_profiles.loader import load_profile
    from pipeline.executor import Executor
    from pipeline.preconditions import PreconditionEvaluator
    from pipeline.triage import Triage
    from oracles.write_read_consistency import WriteReadConsistency
    from oracles.filter_strictness import FilterStrictness
    from oracles.monotonicity import Monotonicity

    adapter = _create_adapter(db_config['type'], db_config)
    snapshot = adapter.get_runtime_snapshot()

    contract = get_default_contract()
    profile = load_profile(f"contracts/db_profiles/{db_config['type']}_profile.yaml")

    precond = PreconditionEvaluator(contract, profile, {
        "collections": snapshot.get("collections", []),
        "indexed_collections": snapshot.get("indexed_collections", []),
        "loaded_collections": snapshot.get("loaded_collections", []),
        "connected": snapshot.get("connected", True),
        "supported_features": ["hybrid_search", "filtering", "multi_model"]
    })
    precond.load_runtime_snapshot(snapshot)

    oracles = [WriteReadConsistency(validate_ids=True), FilterStrictness(), Monotonicity()]
    executor = Executor(adapter, precond, oracles)
    triage = Triage()

    results = []
    for case in cases:
        result = executor.execute_case(case, run_id)
        result.triage_result = triage.classify(case, result, naive=False)
        results.append(result)

    config_source = "compare_workflow"  # compare workflow context
    _save_results(results, cases, output_dir, db_config['type'], run_id, adapter, config_source)
    return adapter, results


def _analyze_differential(results_by_db: dict, cases) -> dict:
    """Analyze differences - reuses existing differential-label logic.

    MILESTONE-1 NOTE: This imports from scripts/analyze_differential_results.py.
    This is temporary technical debt. Future milestone should extract
    reusable differential functions into a neutral module (e.g., analysis/differential.py).
    """
    db_names = list(results_by_db.keys())
    if len(db_names) != 2:
        return {'total_cases': len(cases), 'genuine_difference_count': 0, 'stricter_db': 'none', 'genuine_differences': []}

    # Import existing differential analysis logic (MILESTONE-1 TEMPORARY)
    from scripts.analyze_differential_results import (
        compare_outcomes, label_differences, identify_stricter_database
    )

    r1 = {r.case_id: r for r in results_by_db[db_names[0]]}
    r2 = {r.case_id: r for r in results_by_db[db_names[1]]}

    # Use existing comparison logic
    diffs = []
    milvus_strict_count = 0
    seekdb_strict_count = 0

    for case in cases:
        res1, res2 = r1.get(case.case_id), r2.get(case.case_id)
        if not res1 or not res2:
            continue

        # Reuse existing label_differences logic
        label = label_differences(res1, res2, case)
        if label != 'no_difference':
            diffs.append({
                'case_id': case.case_id,
                'difference_type': label,
                f'{db_names[0]}_outcome': res1.observed_outcome.value,
                f'{db_names[1]}_outcome': res2.observed_outcome.value,
                'interpretation': _interpret_label(label, db_names)
            })

            # Track stricter database
            if label == f'{db_names[0]}_stricter':
                if db_names[0] == 'milvus':
                    milvus_strict_count += 1
                else:
                    seekdb_strict_count += 1
            elif label == f'{db_names[1]}_stricter':
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
        'genuine_difference_count': len(diffs),
        'stricter_db': stricter_db,
        'genuine_differences': diffs,
        'milvus_strict_count': milvus_strict_count,
        'seekdb_strict_count': seekdb_strict_count
    }


def _interpret_label(label: str, db_names: list) -> str:
    """Convert difference label to human-readable interpretation."""
    if label == f'{db_names[0]}_stricter':
        return f"{db_names[0].capitalize()} rejects, {db_names[1].capitalize()} accepts (stricter)"
    elif label == f'{db_names[1]}_stricter':
        return f"{db_names[1].capitalize()} rejects, {db_names[0].capitalize()} accepts (stricter)"
    elif 'oracle' in label.lower():
        return f"Different oracle results"
    return label.replace('_', ' ').title()


def _save_differential_artifacts(details: dict, output_dir: Path, tag: str, timestamp: str, config: dict, adapters: list):
    """Save differential artifacts."""
    with open(output_dir / "differential_details.json", "w") as f:
        json.dump(details, f, indent=2, default=str)

    # Generate report
    lines = [
        f"# Differential Comparison\n\n**Tag**: {tag}\n**Timestamp**: {timestamp}\n\n",
        f"## Summary\n- Total: {details['total_cases']}\n- Differences: {details['genuine_difference_count']}\n\n"
    ]
    for d in details['genuine_differences']:
        lines.append(f"### {d['case_id']}\n**Type**: {d['difference_type']}\n**Interpretation**: {d['interpretation']}\n\n")
    (output_dir / "differential_report.md").write_text(''.join(lines))

    metadata = {
        "tool_version": "0.1.0",
        "workflow_type": "compare",
        "databases": config['databases'],
        "adapter_used": adapters,
        "config_source": str(config.get('_campaign_path', 'cli_args')),
        "timestamp": timestamp,
        "run_tag": tag
    }
    with open(output_dir / "comparison_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"💾 Saved differential artifacts")
```

**Step 2: Create example compare campaign**

```yaml
# campaigns/compare_example.yaml
name: "Example Comparison"
tag: "test"
databases:
  - type: milvus
    host: localhost
    port: 19530
  - type: seekdb
    host: localhost
    port: 2881
case_pack: packs/example_pack.json
```

**Step 3: Commit**

```bash
git add ai_db_qa/workflows/compare.py campaigns/compare_example.yaml
git commit -m "feat(cli): implement compare workflow with strengthened differential analysis

- Add run_compare() for cross-database comparison
- Reuse validate logic per database via _run_db_validation
- Import existing differential-label logic from scripts/analyze_differential_results.py
- Use label_differences() for proper classification (not just observed_outcome)
- Track stricter_db with milvus_strict_count/seekdb_strict_count
- Save 3 differential artifacts: details.json, report.md, metadata.json

TECHNICAL DEBT (milestone-1): Importing from scripts/ is temporary.
Future milestone should extract reusable differential functions to
analysis/differential.py for better modularity.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Final: Documentation and README

**Step 1: Create README**

```markdown
# AI Database QA Tool - CLI

## Installation

```bash
pip install -e .
```

## Quick Start

```bash
# Generate case pack
ai-db-qa generate --campaign campaigns/generate_example.yaml

# Validate database (prints output directory)
ai-db-qa validate --campaign campaigns/validate_example.yaml
# Output: ✅ Validation complete! Results: results/milvus_validation_20260308_120000

# Export bugs (use the printed directory path)
ai-db-qa export --input results/milvus_validation_20260308_120000 --type issue-report --output bugs.md

# Compare databases
ai-db-qa compare --campaign campaigns/compare_example.yaml
```

## Output Artifacts

### Validate
- `execution_results.jsonl` - All cases (bugs + non-bugs)
- `triage_results.json` - Only bugs (excludes type-2.precondition_failed)
- `summary.json` - Statistics (bugs, precondition-filtered, non-bugs)
- `metadata.json` - Run info
- `cases.jsonl` - Original cases

### Compare
- Per-database artifacts (same as validate)
- `differential_details.json`
- `differential_report.md`
- `comparison_metadata.json`
```

**Step 2: Final commit**

```bash
git add README.md
git commit -m "docs(cli): add README and complete milestone 1

Milestone 1 complete:
- CLI wrapper with 4 commands
- Single-database validation working
- Export working
- Compare workflow implemented
- Explicit artifact contracts documented

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Testing Checklist

- [ ] `pip install -e .` works
- [ ] `ai-db-qa --help` shows 4 commands
- [ ] Generate creates valid pack JSON with _serialize_case() helper
- [ ] Validate runs and creates 5 artifacts
- [ ] execution_results.jsonl has triage_result for ALL cases (null or object)
- [ ] triage_results.json has ONLY bugs (excludes type-2.precondition_failed)
- [ ] summary.json has explicit non-bug definition (executed, no bug triage)
- [ ] supported_features derived from profile/snapshot (not hardcoded)
- [ ] Export reads correct input files
- [ ] Compare uses existing differential-label logic (not just outcome comparison)
- [ ] Compare documents scripts/ import as technical debt
- [ ] No sys.path.insert in workflows

---

## Exit Criteria

Milestone 1 complete when:
- ✅ Single-DB validation workflow end-to-end
- ✅ Export generates issue reports
- ✅ All artifact contracts followed
- ✅ README documents usage
- ✅ No breaking changes to existing code

---

**Plan ready for execution. 4 implementation blocks. Lean, focused, wraps existing logic.**
