# CLI Productization Design Document

**Date**: 2026-03-08
**Author**: AI-DB-QC Team
**Status**: Approved for Implementation
**Milestone**: First Productization - Usable Validation Tool

---

## Overview

This document describes the design for exposing the existing AI Database QA research framework as a usable CLI product. The approach is **minimal wrapper** - no architectural changes, just exposure and integration of existing components.

### Design Approach: Option 1 - Minimal CLI Wrapper

- Create thin wrappers around existing components
- Reuse existing scripts (instantiator, differential_campaign, analysis) via imports
- ~600 lines of new code, zero architectural changes
- Standard library `argparse` (no new dependencies)
- Use existing `schemas.case.TestCase` for case pack format

### Key Principles

1. **Expose, don't rebuild** - Product is the same system, exposed better
2. **Thin dispatch layer** - `__main__.py` only parses and routes
3. **Config-driven primary** - Campaign files are primary input, CLI flags are overrides
4. **Proper imports** - No `sys.path.insert()` manipulation
5. **Artifact consistency** - Clear output contracts for all workflows

---

## Package Structure

```
ai_db_qa/
├── __init__.py              # Package init, version info (~5 lines)
├── __main__.py              # CLI entry point, thin dispatch (~80 lines)
├── cli_parsers.py           # Argument parser definitions (~150 lines)
└── workflows/
    ├── __init__.py          # Package init (~5 lines)
    ├── generate.py          # Template → case pack wrapper (~100 lines)
    ├── validate.py          # Single-DB validation wrapper (~200 lines)
    ├── compare.py           # Differential comparison wrapper (~200 lines)
    └── export.py            # Result export wrapper (~200 lines)
```

**Total**: ~940 lines of new code (increased from initial estimate due to explicit artifact saving)

---

## Workflow 1: Generate (`generate`)

### Purpose
Create case packs from templates or campaigns. Case packs are pre-instantiated JSON files ready for execution.

### Input Priority
1. **Campaign file** (recommended) - includes template reference + substitutions
2. **Template + substitutions** (lower-level) - direct use

### Campaign Format (YAML-safe)

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
  query_vector_json: "[0.1, 0.1, 0.1, ..., 0.1]"  # 128 values
  vectors_json: "[[0.1, 0.1, ...], [0.2, 0.2, ...]]"  # 2 vectors of 128 dims

  # Alternative: generation specs (future enhancement)
  # vector_spec:
  #   type: "fill"
  #   value: 0.1
  #   count: 128

output: packs/milvus_validation_pack.json
```

**Note**: Campaign substitutions use JSON-encoded strings for complex values to ensure YAML compatibility. Python expressions like `[0.1] * 128` are NOT valid YAML.

### Output Format

```json
// packs/milvus_validation_pack.json
{
  "pack_meta": {
    "name": "Milvus Validation Case Pack",
    "version": "1.0",
    "description": "Core vector database operations",
    "author": "ai-db-qa",
    "created": "2026-03-08"
  },
  "cases": [
    {
      "case_id": "create_collection_valid",
      "operation": "create_collection",
      "params": {
        "collection_name": "test_collection",
        "dimension": 128,
        "metric_type": "L2"
      },
      "expected_validity": "legal",
      "required_preconditions": [],
      "oracle_refs": [],
      "rationale": "Valid collection creation should succeed"
    }
    // ... more cases
  ]
}
```

### Key Implementation Details

- Reuses `casegen.generators.instantiator.load_templates()` and `instantiate_all()`
- Converts `substitutions` dict to handle JSON-encoded strings
- Output uses existing `TestCase` schema with `expected_validity` field
- No new schema introduction

---

## Workflow 2: Validate (`validate`)

### Purpose
Single-database validation with evidence-backed triage and comprehensive artifact generation.

### Input Priority
1. **Campaign file** (recommended) - complete configuration
2. **Case pack + database type** - with optional CLI overrides (host, port, output)

### Minimum Output Artifacts

```
results/<db_type>_validation_<timestamp>/
├── execution_results.jsonl    # Per-case execution results (all cases)
├── triage_results.json         # Triage classification (bugs only)
├── cases.jsonl                 # Original test cases (for reference)
├── summary.json                # Summary statistics (see schema below)
└── metadata.json               # Run metadata (see schema below)
```

### Output Artifact Schemas

#### metadata.json - Convention 1

```json
{
  "tool_version": "0.1.0",
  "workflow_type": "validate",
  "db_type": "milvus",
  "adapter_used": "MilvusAdapter",
  "config_source": "campaigns/milvus_validation.yaml",
  "timestamp": "20260308_120000",
  "run_tag": "validation",
  "run_id": "milvus_validation_20260308_120000",
  "total_cases": 18,
  "total_bugs": 3
}
```

**Required fields for metadata.json:**
- `tool_version`: CLI tool version
- `workflow_type`: "validate", "compare", "generate", or "export"
- `db_type`: "milvus" or "seekdb" (for validate/compare)
- `adapter_used`: Adapter class name used
- `config_source`: Path to campaign file or "cli_args"
- `timestamp`: Run timestamp
- `run_tag`: User-provided or default run identifier
- Additional fields as needed per workflow

#### summary.json - Convention 2

```json
{
  "run_id": "milvus_validation_20260308_120000",
  "run_tag": "validation",
  "db_type": "milvus",
  "timestamp": "20260308_120000",

  // Minimum required field set
  "total_cases": 18,
  "bug_candidate_counts_by_type": {
    "type-1": 0,
    "type-2": 1,
    "type-3": 1,
    "type-4": 1
  },
  "precondition_filtered_count": 2,
  "non_bug_count": 13,
  "total_bugs": 3,

  // Additional derived metrics
  "outcome_counts": {
    "success": 15,
    "failure": 3
  },
  "oracle_eval_count": 18,
  "oracle_fail_count": 1
}
```

**Minimum required fields for summary.json:**
- `total_cases`: Total number of test cases
- `bug_candidate_counts_by_type`: Counts for each bug type (type-1 through type-4)
- `precondition_filtered_count`: Cases filtered by preconditions
- `non_bug_count`: Cases not classified as bugs
- `run_id` or `run_tag`: Run identifier

### Adapter Creation Interface

**Function signature:**
```python
def _create_adapter(db_type: str, db_config: dict) -> AdapterBase:
    """Create database adapter.

    Args:
        db_type: Database type ('milvus' or 'seekdb')
        db_config: Connection config dict with keys:
                   - host: str (default: 'localhost')
                   - port: int (default: 19530 for milvus, 2881 for seekdb)
                   - alias: str (default: 'default')

    Returns:
        Adapter instance (MilvusAdapter or SeekDBAdapter)
    """
```

**Usage:**
```python
config = _load_validation_config(args)
adapter = _create_adapter(config['db_type'], config['db_config'])
```

---

## Workflow 3: Compare (`compare`)

### Purpose
Cross-database differential comparison with comprehensive differential analysis.

### Input Priority
1. **Campaign file** (recommended) - includes both databases + shared case pack
2. **Databases + case pack** - with optional tag

### Minimum Output Artifacts

```
results/differential_<tag>_<timestamp>/
├── milvus/
│   ├── execution_results.jsonl
│   ├── triage_results.json
│   ├── cases.jsonl
│   ├── summary.json
│   └── metadata.json
├── seekdb/
│   ├── execution_results.jsonl
│   ├── triage_results.json
│   ├── cases.jsonl
│   ├── summary.json
│   └── metadata.json
├── differential_details.json      # Cross-database comparison data
├── differential_report.md         # Human-readable comparison report
└── comparison_metadata.json       # Comparison run metadata
```

### Differential Artifacts

#### comparison_metadata.json

```json
{
  "tool_version": "0.1.0",
  "workflow_type": "compare",
  "databases": [
    {"type": "milvus", "host": "localhost", "port": 19530},
    {"type": "seekdb", "host": "127.0.0.1", "port": 2881}
  ],
  "adapter_used": ["MilvusAdapter", "SeekDBAdapter"],
  "config_source": "campaigns/differential_comparison.yaml",
  "timestamp": "20260308_120000",
  "run_tag": "v4",
  "comparison_id": "differential_v4_20260308_120000",
  "total_cases": 18,
  "genuine_differences": 3,
  "stricter_db": "milvus"
}
```

#### differential_details.json

```json
{
  "comparison_id": "differential_v4_20260308_120000",
  "databases": ["milvus", "seekdb"],
  "total_cases": 18,
  "genuine_difference_count": 3,
  "stricter_db": "milvus",
  "genuine_differences": [
    {
      "case_id": "invalid_dimension_negative",
      "difference_type": "milvus_rejects_seekdb_accepts",
      "milvus_outcome": "failure",
      "seekdb_outcome": "success",
      "interpretation": "Milvus rejects negative dimension, SeekDB accepts it"
    }
    // ... more differences
  ],
  "per_case_analysis": {
    // Detailed per-case comparison
  }
}
```

### Key Implementation Details

- Imports from `scripts.run_differential_campaign` for reusable functions
- Creates output subdirectories per database
- Calls `_run_single_db_validation()` for each database (reuses validate logic)
- Calls `_analyze_differential()` to compute cross-database differences
- Saves 3 differential artifacts plus per-database artifacts

---

## Workflow 4: Export (`export`)

### Purpose
Generate formatted reports from test results. Supports three export types.

### Export Types

| Type | Input Source | Output Format | Purpose |
|------|-------------|---------------|---------|
| `issue-report` | Single-DB or differential results | Markdown | Bug candidates for issue filing |
| `paper-cases` | Differential or aggregated results | Markdown | Academic case study format |
| `summary` | Any run type | JSON or Markdown | Statistical overview |

### Bug Candidate Detection - Taxonomy-Aware Filtering

```python
from schemas.common import BugType

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
```

### Severity Mapping

| Bug Type | Severity | Rationale |
|----------|----------|-----------|
| Type-1 | HIGH | Illegal input accepted - security/correctness risk |
| Type-2 | MEDIUM | Poor diagnostics - UX issue |
| Type-3 | HIGH | Legal input failed - correctness issue |
| Type-4 | MEDIUM | Semantic violation - correctness issue |

### Implementation Strategy

- Reuses existing analysis script functions via imports:
  - `analysis.export_case_studies`: `load_run_data()`, `find_representative_cases()`
  - `analysis.summarize_runs`: `load_execution_results()`, `summarize_single_run()`
- Export types separated into distinct functions
- Minimal new code, primarily routing and formatting

---

## Import Strategy

### No `sys.path.insert()` in Product Code

**Problem**: `sys.path.insert()` is not acceptable in milestone-1 product code.

**Solution**: Use proper package installation.

#### Option A: Editable Install (Recommended)

```bash
# User installs once from project root
pip install -e .

# Then CLI works with proper imports
python -m ai_db_qa validate --campaign campaigns/milvus_validation.yaml
```

#### Option B: PYTHONPATH

```bash
# User sets PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
python -m ai_db_qa validate --campaign campaigns/milvus_validation.yaml
```

### Project Configuration

Ensure `pyproject.toml` has proper configuration:

```toml
[project]
name = "ai-db-qa"
version = "0.1.0"
description = "AI Database QA Tool"
requires-python = ">=3.8"

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project.scripts]
ai-db-qa = "ai_db_qa.__main__:main"
```

### Workflow Imports

```python
# Direct imports - assumes project is installed or PYTHONPATH is set
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
from schemas.common import BugType
```

---

## CLI Interface

### Entry Point (`__main__.py`)

**Purpose**: Thin dispatch layer only - parse arguments and route to workflows.

```python
"""AI Database QA Tool - Minimum Viable CLI"""

import argparse

def main():
    parser = argparse.ArgumentParser(
        description="AI Database QA Tool - Test databases, judge correctness, generate reports"
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

### Command Examples

```bash
# Generate case pack from campaign
python -m ai_db_qa generate --campaign campaigns/generate_milvus.yaml

# Generate from template (lower-level)
python -m ai_db_qa generate \
  --template casegen/templates/differential_v3_phase1.yaml \
  --substitutions "collection=test,dimension=128" \
  --output packs/test_pack.json

# Validate database using campaign
python -m ai_db_qa validate --campaign campaigns/milvus_validation.yaml

# Validate with CLI overrides
python -m ai_db_qa validate \
  --db milvus \
  --pack packs/basic_ops.json \
  --host localhost \
  --port 19530 \
  --output results/my_run

# Compare databases
python -m ai_db_qa compare --campaign campaigns/differential_comparison.yaml

# Export issue report
python -m ai_db_qa export \
  --input results/milvus_validation_20260308_120000/ \
  --type issue-report \
  --output bugs.md

# Export summary
python -m ai_db_qa export \
  --input results/milvus_val/,results/seekdb_val/ \
  --type summary \
  --output summary.md
```

---

## Success Criteria

### Milestone: "Usable Validation Tool"

**Objective**: User can complete end-to-end validation workflow and generate issue-ready or paper-ready outputs within 1 hour.

**Deliverables**:
1. ✅ Four CLI commands (generate, validate, compare, export)
2. ✅ Working example using existing v3 templates
3. ✅ Documentation (README, quick start)
4. ✅ All output artifacts clearly defined

**Success Criteria**:
- ✅ User can run full workflow without reading source code
- ✅ Generated reports are issue-ready or paper-ready
- ✅ Total time: <1 hour for end-to-end workflow (install → results)
- ✅ No breaking changes to existing components

**Exit Condition**: CLI produces same outputs as existing scripts when tested against v3 results.

---

## Dependencies

All dependencies are **existing components** - no new packages required:

### Existing Imports
- `adapters/milvus_adapter.py`, `adapters/seekdb_adapter.py`
- `pipeline/executor.py`, `pipeline/preconditions.py`, `pipeline/triage.py`
- `oracles/write_read_consistency.py`, `oracles/filter_strictness.py`, `oracles/monotonicity.py`
- `contracts/core/loader.py`, `contracts/db_profiles/loader.py`
- `schemas/case.py`, `schemas/common.py`
- `casegen/generators/instantiator.py`
- `analysis/export_case_studies.py`, `analysis/summarize_runs.py`
- `scripts/run_differential_campaign.py`

### Standard Library Only
- `argparse` - CLI parsing
- `pathlib` - File paths
- `json`, `yaml` - Data formats
- `datetime` - Timestamps
- `typing` - Type hints

---

## Implementation Estimate

**Core CLI package**: ~940 lines of code
- Entry point: ~80 lines
- CLI parsers: ~150 lines
- Generate workflow: ~100 lines
- Validate workflow: ~200 lines
- Compare workflow: ~200 lines
- Export workflow: ~200 lines

**Timeline**: 3-5 days
- Day 1: Package structure + CLI entry point + parsers
- Day 2: Generate + Validate workflows
- Day 3: Compare workflow
- Day 4: Export workflow
- Day 5: Testing and documentation

**Minimal extraction from existing scripts**:
- `run_differential_campaign.py`: Extract `run_differential_from_config()` function

---

## Explicit Conventions Summary

### Convention 1: metadata.json Fields

**Required for all workflows:**
- `tool_version`: CLI tool version
- `workflow_type`: "generate", "validate", "compare", or "export"
- `db_type` or `databases`: Database type(s) involved
- `adapter_used` or `adapters_used`: Adapter class name(s)
- `config_source`: Campaign file path or "cli_args"
- `timestamp`: Run timestamp
- `run_tag`: User-provided or default run identifier

**Workflow-specific:**
- `run_id`: Unique run identifier
- `total_cases`, `total_bugs`: For validate/compare
- `comparison_id`, `genuine_differences`, `stricter_db`: For compare

### Convention 2: summary.json Fields

**Minimum required field set:**
- `total_cases`: Total number of test cases
- `bug_candidate_counts_by_type`: Object with counts for each bug type
- `precondition_filtered_count`: Cases filtered by preconditions
- `non_bug_count`: Cases not classified as bugs
- `run_id` or `run_tag`: Run identifier

**Additional recommended fields:**
- `outcome_counts`: Counts by observed outcome
- `oracle_eval_count`, `oracle_fail_count`: Oracle statistics
- `db_type`, `timestamp`: Context information

---

## Next Steps

1. ✅ Design document approved
2. ⏸️ Create implementation plan (using writing-plans skill)
3. ⏸️ Implement package structure
4. ⏸️ Implement workflows
5. ⏸️ Create example campaigns
6. ⏸️ Test with existing v3 results
7. ⏸️ Write user documentation

---

**Document Status**: Final - Ready for implementation planning phase
