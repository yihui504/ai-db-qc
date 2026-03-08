# Productization Plan: Workflow-First Approach (Refined)

**Date**: 2026-03-08
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

### Artifact Model: Templates vs Case Packs vs Campaigns

Before defining workflows, clarify the product's input artifacts:

#### Raw Template Files

**Definition**: YAML files defining test case patterns with parameter placeholders

**Location**: `casegen/templates/`

**Example**:
```yaml
# casegen/templates/invalid_metric_type.yaml
- case_id: invalid_metric_type_L2
  operation: create_index
  param_template:
    metric_type: "{{metric_type}}"
  rationale: "Test invalid metric type rejection"
```

**Purpose**: Author-level, editable, intended for extension

**Not ideal for**: Direct end-user consumption (requires understanding template syntax)

---

#### Case Packs

**Definition**: Pre-instantiated JSON collections of test cases, ready to execute

**Generation**:
```bash
# From template to case pack
python -m ai_db_qa generate \
  --template casegen/templates/basic_ops.yaml \
  --output packs/basic_ops_pack.json
```

**Format**: JSON array of fully-specified test cases
```json
[
  {
    "case_id": "invalid_metric_type_L2",
    "operation": "create_index",
    "params": {"metric_type": "L2", "dimension": 128},
    "rationale": "Test invalid metric type rejection"
  }
]
```

**Purpose**: End-user consumable, reusable, version-controlled

**Benefits**:
- No template syntax required
- Explicit parameters (no surprises)
- Can be audited before execution
- Can be shared between teams

---

#### Campaigns

**Definition**: Case pack + execution configuration + comparison criteria

**Components**:
1. **Case pack**: What to test
2. **Target databases**: Where to test
3. **Oracle configuration**: How to judge correctness
4. **Export templates**: What outputs to produce

**Example**:
```yaml
# campaigns/milvus_validation.yaml
name: "Milvus v2.4 Validation"
case_pack: packs/basic_ops_pack.json
databases:
  - type: milvus
    host: localhost
    port: 19530
oracles:
  - write_read_consistency
  - filter_strictness
  - monotonicity
outputs:
  - type: issue-report
    format: markdown
  - type: summary
    format: json
```

**Purpose**: Complete, reproducible testing scenario

**Benefits**:
- Self-documenting (all context in one file)
- Reproducible (same configuration = same results)
- Shareable (can be versioned and peer-reviewed)

---

### Scenario 1: Single-Database Validation

**User Goal**: "I want to validate a database implementation against expected behavior"

**User Input**:
1. Database connection info (host, port, credentials)
2. Case pack or campaign YAML
3. Contract/profile (defines expected behavior)

**Workflow**:
```
┌────────────────────────────────────────────────────────────┐
│ 1. User provides:                                          │
│    - Database: milvus (localhost:19530)                   │
│    - Case pack: packs/basic_ops_pack.json                  │
│      OR Campaign: campaigns/milvus_validation.yaml          │
│    - Contract: contracts/db_profiles/milvus_profile.yaml    │
└────────────────────────────────────────────────────────────┘
                         ↓
┌────────────────────────────────────────────────────────────┐
│ 2. System executes:                                       │
│    - Connect to database                                    │
│    - Load test cases from pack                              │
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
# Simple: Case pack directly
python -m ai_db_qa validate \
  --db milvus \
  --pack packs/basic_ops_pack.json \
  --output results/milvus_validation

# OR: Campaign file (recommended)
python -m ai_db_qa validate \
  --campaign campaigns/milvus_validation.yaml \
  --output results/milvus_validation
```

**User Outputs**:
1. **Bug Report** (`BUG_REPORT.md`): Issue-ready candidates
2. **Summary** (`summary.json`): Statistics
3. **Detailed Results** (`execution_results.jsonl`): Raw evidence

---

### Scenario 2: Cross-Database Differential Comparison

**User Goal**: "I want to compare how two databases behave on the same tests"

**User Input**:
1. Two database connections
2. Shared case pack
3. Comparison criteria

**Workflow**:
```
┌────────────────────────────────────────────────────────────┐
│ 1. User provides:                                          │
│    - Database 1: milvus (localhost:19530)                  │
│    - Database 2: seekdb (127.0.0.1:2881)                  │
│    - Case pack: packs/differential_pack.json                │
│      OR Campaign: campaigns/differential_comparison.yaml     │
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
# Simple: Case pack directly
python -m ai_db_qa compare \
  --databases milvus,seekdb \
  --pack packs/differential_pack.json \
  --output results/differential_v4

# OR: Campaign file (recommended)
python -m ai_db_qa compare \
  --campaign campaigns/differential_comparison.yaml \
  --output results/differential_v4
```

**User Outputs**:
1. **Comparison Report** (`differential_report.md`): Aggregate table + key findings
2. **Differential Details** (`differential_details.json`): Per-case breakdown
3. **Summary**: Which database is stricter, genuine differences found

---

### Scenario 3: Result Export

**User Goal**: "I want to generate publication-ready issue reports or paper case studies from my results"

**User Input**: Previous run results directory

**Export Input Model** (refined):

```
┌─────────────────────────────────────────────────────────────┐
│                     EXPORT INPUT SOURCES                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Single-DB Run Outputs                                      │
│  ├─ execution_results.jsonl (per-case results)             │
│  ├─ summary.json (statistics)                               │
│  └─ BUG_REPORT.md (auto-generated bugs)                    │
│                                                              │
│  Differential Comparison Outputs                            │
│  ├─ milvus/execution_results.jsonl                          │
│  ├─ seekdb/execution_results.jsonl                          │
│  ├─ differential_details.json (comparison data)            │
│  └─ differential_report.md (comparison summary)             │
│                                                              │
│  Aggregated Artifacts                                       │
│  ├─ Multiple runs merged (e.g., v3-phase1 + v3-phase2)     │
│  ├─ Cross-campaign analysis                                 │
│  └─ Historical comparison                                   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Export Types by Input Source**:

| Export Type | Valid Input Sources | Output Format |
|-------------|---------------------|---------------|
| **issue-report** | Single-DB run, Differential run | Markdown bug reports |
| **paper-cases** | Differential run, Aggregated artifacts | Academic case studies |
| **summary** | Any run type | Statistics overview |

**Concrete Examples**:

```bash
# Export issue report from single-DB validation
python -m ai_db_qa export \
  --input results/milvus_validation/ \
  --type issue-report \
  --output reports/milvus_bugs.md

# Export paper cases from differential comparison
python -m ai_db_qa export \
  --input results/differential_v4/ \
  --type paper-cases \
  --output papers/v4_comparison.md

# Export summary from aggregated runs
python -m ai_db_qa export \
  --input results/v3-phase1/,results/v3-phase2/ \
  --type summary \
  --output reports/v3_aggregated_summary.md
```

**User Outputs**:
1. **Issue Report**: Formatted bug reports with reproduction steps
2. **Paper Cases**: Academic-style case descriptions
3. **Summary**: Statistical overview, tables, metrics

---

### Workflow Summary

| Scenario | Input | Output | Value |
|----------|-------|--------|-------|
| **Single-DB Validation** | Connection + case pack/campaign | Bug report + summary | Find bugs in implementation |
| **Cross-DB Comparison** | 2 connections + shared pack/campaign | Comparison report | Understand database differences |
| **Result Export** | Results directory (single/diff/aggregated) | Formatted report | Publication-ready output |

**Key Insight**: These workflows are **already implemented** in the current system. The task is **exposure**, not new development.

---

## Step 2: Minimal Configuration Model

### Configuration Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│                     CONFIGURATION LAYERS                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Connection Config (database connectivity)               │
│     ├─ type: milvus | seekdb                                │
│     ├─ host, port, credentials                              │
│     └─ Connection pool settings                             │
│                                                              │
│  2. Contract/Profile Config (expected behavior)             │
│     ├─ Database profile (which capabilities expected)       │
│     ├─ Contract (operation legality rules)                  │
│     └─ Parameter constraints                                │
│                                                              │
│  3. Oracle Config (correctness judgment)                    │
│     ├─ Which oracles to enable                              │
│     ├─ Oracle-specific settings                              │
│     └─ Severity thresholds                                  │
│                                                              │
│  4. Campaign Config (execution scenario)                    │
│     ├─ Case pack reference                                  │
│     ├─ Target databases                                     │
│     ├─ Execution options (parallel, timeout)                │
│     └─ Output specifications                                │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Minimal Config: Single-Database Validation

```yaml
# campaigns/milvus_validation.yaml
name: "Milvus Basic Validation"

# Database connection
databases:
  - type: milvus
    host: localhost
    port: 19530

# What to test
case_pack: packs/basic_ops_pack.json

# Expected behavior
contract:
  profile: contracts/db_profiles/milvus_profile.yaml

# How to judge correctness
oracles:
  - write_read_consistency:
      validate_ids: true
  - filter_strictness: {}
  - monotonicity: {}

# Outputs
outputs:
  - type: issue-report
    format: markdown
    file: BUG_REPORT.md
  - type: summary
    format: json
    file: summary.json
```

### Minimal Config: Cross-Database Comparison

```yaml
# campaigns/differential_comparison.yaml
name: "Milvus vs SeekDB Comparison"

# Databases to compare
databases:
  - type: milvus
    host: localhost
    port: 19530
  - type: seekdb
    host: 127.0.0.1
    port: 2881

# What to test (same tests on both)
case_pack: packs/differential_pack.json

# Expected behavior (use generic contract or per-DB)
contract:
  profile: contracts/db_profiles/generic_profile.yaml

# How to judge
oracles:
  - write_read_consistency:
      validate_ids: true
  - filter_strictness: {}
  - monotonicity: {}

# Outputs (differential-specific)
outputs:
  - type: differential
    format: markdown
    file: differential_report.md
  - type: issue-report
    format: markdown
    file: BUG_REPORT.md
```

### Configuration Loading Strategy

**Priority** (highest to lowest):
1. CLI flags (`--db milvus --host remote.host`)
2. Campaign file (`campaigns/milvus_validation.yaml`)
3. Default profiles (`contracts/db_profiles/milvus_profile.yaml`)

**Rationale**: Allow quick overrides via CLI, but encourage campaign files for reproducibility

---

## Step 3: Minimal CLI Design

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
  # Single database validation (campaign file)
  python -m ai_db_qa validate --campaign campaigns/milvus_validation.yaml

  # Single database validation (direct pack)
  python -m ai_db_qa validate --db milvus --pack packs/basic_ops.json

  # Cross-database comparison (campaign file)
  python -m ai_db_qa compare --campaign campaigns/differential.yaml

  # Cross-database comparison (direct pack)
  python -m ai_db_qa compare --databases milvus,seekdb --pack packs/diff.json

  # Export results
  python -m ai_db_qa export --input results/milvus_val/ --type issue-report
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Command 1: validate (single-database validation)
    validate_parser = subparsers.add_parser('validate', help='Validate single database')
    validate_parser.add_argument('--campaign', help='Campaign YAML file (recommended)')
    validate_parser.add_argument('--db', choices=['milvus', 'seekdb'], help='Database type')
    validate_parser.add_argument('--pack', help='Case pack JSON file')
    validate_parser.add_argument('--contract', help='Contract/profile YAML')
    validate_parser.add_argument('--output', default='results', help='Output directory')

    # Command 2: compare (cross-database differential)
    compare_parser = subparsers.add_parser('compare', help='Compare databases')
    compare_parser.add_argument('--campaign', help='Campaign YAML file (recommended)')
    compare_parser.add_argument('--databases', help='Comma-separated database names')
    compare_parser.add_argument('--pack', help='Shared case pack JSON')
    compare_parser.add_argument('--tag', help='Run identifier for comparison')
    compare_parser.add_argument('--output', default='results', help='Output directory')

    # Command 3: export (result export)
    export_parser = subparsers.add_parser('export', help='Export results to reports')
    export_parser.add_argument('--input', required=True, help='Results directory (single/diff/aggregated)')
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

### Three Commands, Three Workflows

| Command | Workflow | Primary User Task | Input Priority |
|---------|----------|-------------------|----------------|
| `validate` | Single-DB validation | "Test my database" | 1. Campaign file, 2. Pack + DB |
| `compare` | Cross-DB differential | "Compare databases" | 1. Campaign file, 2. Pack + DBs |
| `export` | Result export | "Generate reports" | Results directory |

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
   - `validation_pack.json`: Contract validation tests
   - `boundary_pack.json`: Parameter boundary tests
   - `diagnostic_pack.json`: Error message quality tests

3. **Regression Tests**: Add tests for v3 findings
   - Dimension limit regression (seekdb 16000 limit)
   - Index validation regression
   - State management tests

**Success Metrics**:
- Templates cover all major operation families
- Reusable packs work on both databases
- New bugs discovered → New regression tests added
- **Improved coverage measured by operation families, not template count**

---

## First Productization Milestone

### Milestone: "Usable Validation Tool"

**Objective**: User can complete end-to-end validation workflow and generate issue-ready or paper-ready outputs within 1 hour

**Deliverables**:

1. **Three CLI Commands** (wrapping existing workflows)
   - `ai_db_qa validate` - Test single database
   - `ai_db_qa compare` - Compare databases
   - `ai_db_qa export` - Generate reports

2. **Working Example** (using v3 templates converted to packs)
   ```bash
   # Generate case pack from existing templates
   python -m ai_db_qa generate \
     --template casegen/templates/differential_v3_phase1.yaml \
     --output packs/v3_phase1_pack.json

   # Validate Milvus
   python -m ai_db_qa validate --db milvus --pack packs/v3_phase1_pack.json

   # Compare databases
   python -m ai_db_qa compare --databases milvus,seekdb --pack packs/v3_phase1_pack.json --tag v4

   # Export issues
   python -m ai_db_qa export --input results/v4-phase1/ --type issue-report
   ```

3. **Documentation**
   - README.md with quick start
   - Three scenario examples (validate, compare, export)
   - Output format descriptions
   - Campaign file templates

4. **Template Expansion** (from v3 learnings)
   - Convert existing templates to reusable case packs
   - Add regression tests for v3 findings
   - Add missing operation families (delete, update)
   - Create reusable packs (validation, boundary, diagnostic)

**Success Criteria**:
- ✅ User can run full workflow without reading source code
- ✅ Generated reports are issue-ready or paper-ready
- ✅ New templates/patches discover v3 regressions
- ✅ Total time: <1 hour for end-to-end workflow (install → results)

---

## Summary

### Product-First Approach

1. **Define workflows first** (what users want to do)
2. **Artifact model second** (templates vs packs vs campaigns)
3. **Configuration model third** (how to specify workflows)
4. **Minimal CLI fourth** (expose existing workflows)
5. **Export fifth** (packaging output for users)
6. **Template expansion sixth** (improve coverage by operation family)

### Key Shifts

- **From**: "18 → 50+ templates" (count metric)
- **To**: "Improve case-family coverage and campaign usefulness" (quality metric)

- **From**: Direct template usage (expert-level)
- **To**: Case pack and campaign files (user-level)

- **From**: "Find real bugs in 1 hour"
- **To**: "Complete end-to-end validation workflow and generate issue-ready or paper-ready outputs within 1 hour"

### Artifact Hierarchy

```
Raw Templates (author-level)
    ↓ [generate]
Case Packs (user-level, reusable)
    ↓ [combine with config]
Campaigns (self-documenting scenarios)
    ↓ [execute]
Results (evidence + reports)
    ↓ [export]
Publications (issues, papers, summaries)
```

### First Milestone

**Usable Validation Tool**: User can complete end-to-end workflow in 1 hour using:
1. `ai_db_qa validate` (test database)
2. `ai_db_qa compare` (find differences)
3. `ai_db_qa export` (generate reports)

**Current System Status**: ✅ All components exist, need CLI wrapping, artifact organization, and documentation
