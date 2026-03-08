# Productization Plan: Workflow-First Approach

**Date**: 2026-03-07
**Approach**: Define workflow before CLI, tasks before commands

---

## Step 1: Minimum Product Workflow

### Primary User Persona

**User**: Database quality engineer or researcher who needs to:
- Validate AI database behavior
- Compare databases objectively
- Generate evidence-backed bug reports
- Produce publication-ready comparisons

**User Capabilities**:
- Can run Python scripts
- Can connect to databases
- Can edit YAML configuration files
- Can interpret test results

---

### Scenario 1: Single-Database Validation

**User Goal**: "I want to validate a database implementation against expected behavior"

**User Input**:
1. Database connection info (host, port, credentials)
2. Test case pack (YAML or JSON)
3. Contract/profile (defines expected behavior)

**Workflow**:
```
┌────────────────────────────────────────────────────────────┐
│ 1. User provides:                                          │
│    - Database: milvus (localhost:19530)                   │
│    - Cases: templates/basic_operations.yaml                │
│    - Contract: contracts/db_profiles/milvus_profile.yaml    │
└────────────────────────────────────────────────────────────┘
                         ↓
┌────────────────────────────────────────────────────────────┐
│ 2. System executes:                                       │
│    - Connect to database                                    │
│    - Load test cases from template                           │
│    - Run each case with oracles                             │
│    - Collect evidence (gate_trace, oracle_results)          │
│    - Triage outcomes (bug vs non-bug)                       │
└────────────────────────────────────────────────────────────┘
                         ↓
┌────────────────────────────────────────────────────────────┐
│ 3. User receives:                                          │
│    - Bug report: Issue-ready candidates with evidence       │
│    - Summary: Pass/fail statistics, noise metrics            │
│    - Detailed results: JSONL with full evidence             │
└────────────────────────────────────────────────────────────┘
```

**Concrete Example**:
```bash
# User creates simple config
cat > config.yaml << EOF
database:
  type: milvus
  host: localhost
  port: 19530

cases:
  template: casegen/templates/basic_operations.yaml

contract:
  profile: contracts/db_profiles/milvus_profile.yaml
  output:
    bugs: reports/milvus_bugs.md
    summary: reports/milvus_summary.json
EOF

# Single command to execute
python -m pipeline.run_campaign config.yaml
```

**User Outputs**:
1. **Bug Report** (`reports/milvus_bugs.md`): Issue-ready candidates
2. **Summary** (`reports/milvus_summary.json`): Statistics
3. **Detailed Results** (`results/milvus_run.jsonl`): Raw evidence

---

### Scenario 2: Cross-Database Differential Comparison

**User Goal**: "I want to compare how two databases behave on the same tests"

**User Input**:
1. Two database connections
2. Shared test case pack
3. Comparison criteria

**Workflow**:
```
┌────────────────────────────────────────────────────────────┐
│ 1. User provides:                                          │
│    - Database 1: milvus (localhost:19530)                  │
│    - Database 2: seekdb (127.0.0.1:2881)                  │
│    - Cases: templates/differential_shared.yaml              │
│    - Output: differential comparison report                 │
└────────────────────────────────────────────────────────────┘
                         ↓
┌────────────────────────────────────────────────────────────┐
│ 2. System executes:                                       │
│    - Connect to both databases                              │
│    - Run SAME cases on both                                │
│    - Compare outcomes per case                             │
│    - Label differences (milvus_stricter, seekdb_stricter)    │
│    - Aggregate into comparison table                        │
└────────────────────────────────────────────────────────────┘
                         ↓
┌────────────────────────────────────────────────────────────┐
│ 3. User receives:                                          │
│    - Comparison table: Which database is stricter?          │
│    - Differential cases: Detailed analysis                  │
│    - Labels: Per-case behavior classification               │
└────────────────────────────────────────────────────────────┘
```

**Concrete Example**:
```bash
# User creates comparison config
cat > comparison_config.yaml << EOF
databases:
  milvus:
    type: milvus
    host: localhost
    port: 19530
  seekdb:
    type: seekdb
    host: 127.0.0.1
    port: 2881

cases:
  template: casegen/templates/differential_shared.yaml

output:
  comparison: reports/comparison.md
  details: reports/differential_details.json
EOF

# Single command to compare
python -m pipeline.differential_comparison comparison_config.yaml
```

**User Outputs**:
1. **Comparison Report** (`reports/comparison.md`): Aggregate table + key findings
2. **Differential Details** (`reports/differential_details.json`): Per-case breakdown
3. **Summary**: Which database is stricter, genuine differences found

---

### Scenario 3: Issue/Paper-Oriented Export

**User Goal**: "I want to generate publication-ready issue reports or paper case studies from my results"

**User Input**:
1. Previous run results
2. Export format (issue-report, paper-cases, or summary)
3. Output target

**Workflow**:
```
┌────────────────────────────────────────────────────────────┐
│ 1. User provides:                                          │
│    - Results directory (from previous run)                 │
│    - Export type: issue-report | paper-cases | summary       │
│    - Template or style preferences                        │
└────────────────────────────────────────────────────────────┘
                         ↓
┌────────────────────────────────────────────────────────────┐
│ 2. System processes:                                     │
│    - Load results (execution_results.jsonl)                │
│    - Filter by export criteria:                             │
│      * Issue-report: Type-1, Type-2, Type-2.PF bugs          │
│      * Paper-cases: Genuine differences only              │
│      * Summary: Statistics and metadata                     │
│    - Format into template:                                 │
│      * Issue: Title, severity, reproduction, evidence       │
│      * Paper: Background, comparison, trade-offs            │
│      * Summary: Tables, counts, metrics                     │
└────────────────────────────────────────────────────────────┘
                         ↓
┌────────────────────────────────────────────────────────────┐
│ 3. User receives:                                          │
│    - Formatted report (Markdown)                            │
│    - Ready for submission (issues) or publication (papers)    │
└────────────────────────────────────────────────────────────┘
```

**Concrete Example**:
```bash
# Export issue reports from v3 results
python -m pipeline.export \
  --input runs/differential-v3-phase1-fixed/ \
  --type issue-report \
  --output docs/issues/v3_issues.md

# Export paper cases
python -m pipeline.export \
  --input runs/differential-v3-phase1-fixed/,runs/differential-v3-phase2-/ \
  --type paper-cases \
  --output docs/paper_cases/v3_comparison.md

# Export summary
python -m pipeline.export \
  --input runs/ \
  --type summary \
  --output docs/v3_summary.md
```

**User Outputs**:
1. **Issue Report**: Formatted bug reports with reproduction steps
2. **Paper Cases**: Academic-style case descriptions
3. **Summary**: Statistical overview, tables, metrics

---

### Workflow Summary

| Scenario | Input | Output | Value |
|----------|-------|--------|-------|
| **Single-DB Validation** | Connection + cases + contract | Bug report + summary | Find bugs in implementation |
| **Cross-DB Comparison** | 2 connections + shared cases | Comparison report | Understand database differences |
| **Result Export** | Results + export type | Formatted report | Publication-ready output |

**Key Insight**: These workflows are **already implemented** in the current system. The task is **exposure**, not new development.

---

## Step 2: Minimal CLI Design

### Design Principle: Wrap Existing Workflows

**Current State**: Workflows exist but require reading source code
**Goal**: Make workflows discoverable and executable

### Minimal CLI Structure

```python
# ai_db_qa/__main__.py

"""
AI Database QA Tool - Minimum Viable CLI

Primary workflows:
1. Single-database validation
2. Cross-database differential comparison
3. Result export (issue-report, paper-cases, summary)
"""

import sys
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(
        description="AI Database QA Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single database validation
  python -m ai_db_qa validate --db milvus --templates templates/ops.yaml

  # Cross-database comparison
  python -m ai_db_qa compare --databases milvus,seekdb --templates templates/shared.yaml

  # Export results
  python -m ai_db_qa export --results runs/v3-phase1/ --type issue-report
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Command 1: validate (single-database validation)
    validate_parser = subparsers.add_parser('validate', help='Validate single database')
    validate_parser.add_argument('--db', required=True, choices=['milvus', 'seekdb'])
    validate_parser.add_argument('--templates', required=True, help='Template YAML file')
    validate_parser.add_argument('--output', default='results', help='Output directory')

    # Command 2: compare (cross-database differential)
    compare_parser = subparsers.add_parser('compare', help='Compare databases')
    compare_parser.add_argument('--databases', required=True, help='Comma-separated database names')
    compare_parser.add_argument('--templates', required=True, help='Shared template YAML')
    compare_parser.add_argument('--output', default='results', help='Output directory')
    compare_parser.add_argument('--tag', required=True, help='Run identifier')

    # Command 3: export (result export)
    export_parser = subparsers.add_parser('export', help='Export results to reports')
    export_parser.add_argument('--results', required=True, help='Results directory')
    export_parser.add_argument('--type', required=True, choices=['issue-report', 'paper-cases', 'summary'])
    export_parser.add_argument('--output', required=True, help='Output file')

    args = parser.parse_args()

    if args.command == 'validate':
        from .workflows.validate import run_validation
        run_validation(args)
    elif args.command == 'compare':
        from .workflows.compare import run_comparison
        run_comparison(args)
    elif args.command == 'export':
        from .workflows.export import run_export
        run_export(args)

if __name__ == '__main__':
    main()
```

### Workflow Wrappers

**File**: `ai_db_qa/workflows/validate.py`

```python
"""Single-database validation workflow."""

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.executor import Executor
from pipeline.preconditions import PreconditionEvaluator
from contracts.core.loader import get_default_contract
from contracts.db_profiles.loader import load_profile
from adapters.milvus_adapter import MilvusAdapter
from adapters.seekdb_adapter import SeekDBAdapter
from casegen.generators.instantiator import load_templates, instantiate_all
import json
from datetime import datetime

def run_validation(args):
    """Run validation workflow."""
    print(f"Validating {args.db} with {args.templates}")

    # Load contract and profile
    contract = get_default_contract()
    profile = load_profile(f"contracts/db_profiles/{args.db}_profile.yaml")

    # Load adapter
    if args.db == 'milvus':
        adapter = MilvusAdapter({'host': 'localhost', 'port': 19530, 'alias': 'default'})
    else:
        adapter = SeekDBAdapter({'api_endpoint': '127.0.0.1:2881'})

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

    from oracles.filter_strictness import FilterStrictness
    from oracles.write_read_consistency import WriteReadConsistency
    from oracles.monotonicity import Monotonicity

    oracles = [WriteReadConsistency(validate_ids=True), FilterStrictness(), Monotonicity()]
    executor = Executor(adapter, precond, oracles)
    triage = Triage()

    # Load and run cases
    templates = load_templates(args.templates)
    cases = instantiate_all(templates, {})

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(args.output) / f"{args.db}_validation_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for case in cases:
        result = executor.execute_case(case, f"validation_{timestamp}")
        results.append(result)
        print(f"  {case.case_id}: {result.observed_outcome}")

    # Save results
    with open(output_dir / "execution_results.jsonl", "w") as f:
        for result in results:
            f.write(json.dumps(result.__dict__, default=str) + "\n")

    # Export bug report
    from .export import generate_bug_report
    bug_report = generate_bug_report(results, f"{args.db} Validation")
    with open(output_dir / "BUG_REPORT.md", "w") as f:
        f.write(bug_report)

    print(f"\nResults: {output_dir}")
    print(f"Bug report: {output_dir / 'BUG_REPORT.md'}")
```

### Three Commands, Three Workflows

| Command | Workflow | Primary User Task |
|---------|----------|-------------------|
| `validate` | Single-DB validation | "Test my database" |
| `compare` | Cross-DB differential | "Compare databases" |
| `export` | Result export | "Generate reports" |

---

## Step 3: Reporting/Export Packaging

### Export System Design

**File**: `ai_db_qa/workflows/export.py`

```python
"""Result export workflow."""

import json
import argparse
from pathlib import Path
from typing import List, Dict, Any

def run_export(args):
    """Export results to formatted reports."""
    results_dir = Path(args.results)
    output_file = Path(args.output)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Load all results
    results = load_results(results_dir)

    if args.type == 'issue-report':
        report = generate_issue_report(results)
        output_file.write_text(report)
        print(f"Issue report: {output_file}")

    elif args.type == 'paper-cases':
        report = generate_paper_cases(results)
        output_file.write_text(report)
        print(f"Paper cases: {output_file}")

    elif args.type == 'summary':
        report = generate_summary_report(results)
        output_file.write_text(report)
        print(f"Summary: {output_file}")

def generate_issue_report(results: List) -> str:
    """Generate issue-ready bug report."""
    # Filter for bug candidates
    bugs = [r for r in results if is_bug_candidate(r)]

    report = f"# Bug Report: {len(bugs)} Issue-Ready Candidates\n\n"

    for i, bug in enumerate(bugs, 1):
        report += f"## Issue #{i}: {bug.case_id}\n\n"
        report += f"**Type**: {bug.triage_result.bug_type}\n"
        report += f"**Severity**: {bug.triage_result.severity}\n\n"
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
    # Filter for genuine differences
    diffs = identify_genuine_differences(results)

    report = f"# Paper Cases: {len(diffs)} Behavioral Differences\n\n"

    for i, diff in enumerate(diffs, 1):
        report += f"## Case {i}: {diff.title}\n\n"
        report += f"**Type**: {diff.type}\n"
        report += f"**Databases**: {diff.databases}\n\n"
        report += "### Description\n\n"
        report += diff.description
        report += "\n\n### Reproduction\n\n"
        report += diff.reproduction
        report += "\n\n### Analysis\n\n"
        report += diff.analysis
        report += "\n---\n\n"

    return report

def generate_summary_report(results: List) -> str:
    """Generate summary statistics."""
    total = len(results)
    bugs = sum(1 for r in results if is_bug(r))
    diffs = sum(1 for r in results if is_genuine_diff(r))

    return f"""# Validation Summary

**Total Cases**: {total}
**Bug Candidates**: {bugs}
**Genuine Differences**: {diffs}

### Statistics
| Metric | Count | Percentage |
|--------|-------|------------|
| Total cases | {total} | 100% |
| Bugs | {bugs} | {bugs/total*100:.1f}% |
| Differences | {diffs} | {diffs/total*100:.1f}% |
"""
```

### Export Templates

| Export Type | Input | Output | Use Case |
|-------------|-------|--------|----------|
| **issue-report** | Results JSONL | Markdown bug report | File to maintainers |
| **paper-cases** | Results JSONL | Academic case studies | Write paper |
| **summary** | Results dir | Statistics overview | Quick review |

---

## Step 4: Continued Mining as Product Usage

### Shift: Campaigns as Product Features

**Before**: "Run campaign → analyze methodology → write paper"
**After**: "Run campaign → generate reports → improve templates"

### Campaign v4: Product-Driven Template Expansion

**Focus**: Improve case-family coverage and campaign usefulness

**Assessment Before v4**:
- Current templates: 18 cases
- Coverage: Basic operations, some boundaries
- Gaps: delete operations, batch operations, advanced filtering

**v4 Objectives**:

1. **Improve Coverage**: Add missing operation families
   - Delete operations (not covered)
   - Update operations (not covered)
   - Batch insert/search (not covered)

2. **High-Yield Packs**: Create reusable focused packs
   - `validation_pack.yaml`: Contract validation tests
   - `boundary_pack.yaml`: Parameter boundary tests
   - `diagnostic_pack.yaml`: Error message quality tests

3. **Regression Tests**: Add tests for v3 findings
   - Dimension limit regression (seekdb 16000 limit)
   - Index validation regression
   - State management tests

**Success Metrics**:
- Templates cover all major operation families
- Reusable packs work on both databases
- New bugs discovered → New regression tests added

### Example: Template Expansion by Family

**Current (v3)**: 18 templates
```
Capability boundaries: 6 templates
Precondition sensitivity: 4 templates
Differential shared: 6 templates
Valid operations: 2 templates
```

**v4 Target**: Improve family coverage
```
Capability boundaries: +8 templates (add more limits)
Precondition sensitivity: +6 templates (add more states)
Delete operations: +5 templates (new family)
Update operations: +5 templates (new family)
Batch operations: +6 templates (new family)

Total: ~48 templates
```

**Focus**: Coverage and usefulness, not count

---

## Current System → Real User Tasks

### Task 1: "Test Milvus for bugs"

**Current System Maps To**:
- `pipeline/executor.py` → Test execution
- `oracles/` → Correctness judgment
- `pipeline/triage.py` → Bug classification

**User Needs**:
- Single command: `python -m ai_db_qa validate --db milvus --templates templates/basic_ops.yaml`
- Output: Bug report with reproduction steps

### Task 2: "Compare Milvus and seekdb"

**Current System Maps To**:
- `scripts/run_differential_campaign.py` → Dual execution
- `scripts/analyze_differential_results.py` → Comparison analysis

**User Needs**:
- Single command: `python -m ai_db_qa compare --databases milvus,seekdb --templates templates/shared.yaml`
- Output: Comparison report with tables

### Task 3: "Generate publication report"

**Current System Maps To**:
- Existing results + manual formatting
- Issue report templates (created in v3)

**User Needs**:
- Single command: `python -m ai_db_qa export --results runs/v3/ --type paper-cases`
- Output: Publication-ready case studies

---

## First Productization Milestone

### Milestone: "Usable Bug-Finding Tool"

**Objective**: User can find and report real database bugs in 1 hour

**Deliverables**:

1. **Three CLI Commands** (wrapping existing workflows)
   - `ai_db_qa validate` - Test single database
   - `ai_db_qa compare` - Compare databases
   - `ai_db_qa export` - Generate reports

2. **Working Example** (using v3 templates)
   ```bash
   # Validate Milvus
   python -m ai_db_qa validate --db milvus --templates casegen/templates/differential_v3_phase1.yaml

   # Compare databases
   python -m ai_db_qa compare --databases milvus,seekdb --templates casegen/templates/differential_v3_phase1.yaml --tag v4

   # Export issues
   python -m ai_db_qa export --results runs/v4-phase1/ --type issue-report
   ```

3. **Documentation**
   - README.md with quick start
   - Three scenario examples (validate, compare, export)
   - Output format descriptions

4. **Template Expansion** (from v3 learnings)
   - Add regression tests for v3 findings
   - Add missing operation families (delete, update)
   - Create reusable packs (validation, boundary, diagnostic)

**Success Criteria**:
- ✅ User can run full workflow without reading source code
- ✅ Generated reports are issue-ready
- ✅ New templates discover v3 regressions
- ✅ Total time: <1 hour for end-to-end workflow

---

## Revised Roadmap

### Phase 1: Define Workflows (This Week)
- [x] Document 3 primary workflows (validate, compare, export)
- [x] Map to existing system components
- [x] Define user inputs and outputs

### Phase 2: Minimal CLI (Week 2)
- [ ] Create ai_db_qa package with 3 commands
- [ ] Wrap existing workflows in CLI
- [ ] Test with v3 templates
- [ ] Documentation

### Phase 3: Export System (Week 3)
- [ ] Implement export templates
- [ ] Generate issue reports from v3 results
- [ ] Generate paper cases from v3 results
- [ ] Test export quality

### Phase 4: Template Expansion (Weeks 4-6)
- [ ] Audit template coverage
- [ ] Add missing families (delete, update, batch)
- [ ] Create v3 regression tests
- [ ] Create reusable packs
- [ ] Run v4 campaign

---

## Summary

### Product-First Approach

1. **Define workflows first** (what users want to do)
2. **Minimal CLI second** (expose existing workflows)
3. **Export third** (packaging output for users)
4. **Template expansion fourth** (improve usefulness, not just count)

### Key Shifts

- **From**: "18 → 50+ templates" (count metric)
- **To**: "Improve case-family coverage and campaign usefulness" (quality metric)

- **From**: "Neat command list" (design-first)
- **To**: "Task-oriented workflows" (user-first)

- **From**: "More research" (expansion)
- **To**: "Product usage" (real bug mining)

### First Milestone

**Usable Bug-Finding Tool**: User can find real bugs in 1 hour using:
1. `ai_db_qa validate` (test database)
2. `ai_db_qa compare` (find differences)
3. `ai_db_qa export` (generate reports)

**Current System Status**: ✅ All components exist, need CLI wrapping and documentation
