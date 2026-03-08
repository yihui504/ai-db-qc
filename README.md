# AI-DB-QC: AI Database Quality Assurance Tool

A contract-driven, adapter-based, evidence-backed system for automated testing and defect discovery in AI databases (vector/hybrid retrieval databases).

## Quick Start

```bash
# Install
pip install -e .

# Generate test case pack from templates
ai-db-qa generate --campaign campaigns/generate_example.yaml

# Validate a database (requires running database)
ai-db-qa validate --campaign campaigns/validate_example.yaml
# Output: [Validate] Validation complete! Results: results/milvus_validation_YYYYMMDD_HHMMSS

# Export bug report
ai-db-qa export --input results/milvus_validation_YYYYMMDD_HHMMSS --type issue-report --output bugs.md

# Compare two databases
ai-db-qa compare --campaign campaigns/compare_example.yaml
```

## CLI Commands

### `ai-db-qa generate` - Create test case packs

Generate test case packs from template files.

```bash
# Using campaign file (recommended)
ai-db-qa generate --campaign campaigns/generate_example.yaml

# Using direct parameters
ai-db-qa generate --template casegen/templates/differential_v3_phase1.yaml --substitutions "collection=test,dimension=128" --output packs/test_pack.json
```

**Output**: JSON file containing instantiated test cases with metadata.

### `ai-db-qa validate` - Test a single database

Run test cases against a database and generate detailed results.

```bash
# Using campaign file (recommended)
ai-db-qa validate --campaign campaigns/validate_example.yaml

# Using direct parameters
ai-db-qa validate --db milvus --pack packs/example_pack.json --host localhost --port 19530
```

**Output Artifacts**:
- `execution_results.jsonl` - All test case results (bugs + non-bugs)
- `triage_results.json` - Only bug candidates (excludes type-2.precondition_failed)
- `summary.json` - Statistics and counts
- `metadata.json` - Run metadata
- `cases.jsonl` - Original test cases

### `ai-db-qa export` - Generate reports

Export results in various formats.

```bash
# Issue report (for bug filing)
ai-db-qa export --input results/milvus_validation_YYYYMMDD_HHMMSS --type issue-report --output bugs.md

# Paper case studies (academic format)
ai-db-qa export --input results/milvus_validation_YYYYMMDD_HHMMSS --type paper-cases --output cases.md

# Summary statistics
ai-db-qa export --input results/milvus_validation_YYYYMMDD_HHMMSS --type summary --output summary.md
```

### `ai-db-qa compare` - Compare two databases

Differential testing between two databases.

```bash
# Using campaign file (recommended)
ai-db-qa compare --campaign campaigns/compare_example.yaml

# Using direct parameters
ai-db-qa compare --databases milvus,seekdb --pack packs/example_pack.json --tag comparison_v1
```

**Output Artifacts**:
- Per-database subdirectories with all validate artifacts
- `differential_details.json` - Cross-database differences
- `differential_report.md` - Human-readable comparison report
- `comparison_metadata.json` - Comparison run metadata

## Output Artifacts Reference

### Validate Workflow Artifacts
| File | Description |
|------|-------------|
| `execution_results.jsonl` | All executed cases with triage results |
| `triage_results.json` | Only bug candidates (taxonomy-aware filtering) |
| `summary.json` | Statistics: total cases, bugs by type, precondition-filtered, non-bugs |
| `metadata.json` | Run metadata: tool version, workflow type, db type, timestamp |
| `cases.jsonl` | Original test cases for reference |

### Compare Workflow Artifacts
| File | Description |
|------|-------------|
| `differential_details.json` | Genuine differences with stricter_db tracking |
| `differential_report.md` | Human-readable comparison report |
| `comparison_metadata.json` | Comparison run metadata |

## Bug Taxonomy

All findings are classified into four top-level types:

- **Type-1**: Illegal operation succeeded (should fail but succeeded) - HIGH severity
- **Type-2**: Illegal operation failed without diagnostic error - MEDIUM severity
  - **Type-2.precondition_failed** (subtype): Expected behavior, NOT a bug - excluded from bug reports
- **Type-3**: Legal operation failed/crashed/hung - HIGH severity
- **Type-4**: Legal operation succeeded but violates semantic invariant - MEDIUM severity

**Critical**: Type-3 and Type-4 require `precondition_pass=true` (red-line constraint).

## Research Background

This system implements two core research functions:

1. **Structured Test Case Generation** - Systematic exploration of input space via templates
2. **Structured Correctness Judgment** - Contract-based validation with semantic oracles

See `docs/plans/2026-03-08-cli-productization-design.md` for detailed design documentation.

## Project Structure

```
ai-db-qc/
├── ai_db_qa/           # CLI wrapper package
│   ├── __main__.py     # Entry point
│   ├── cli_parsers.py  # Argument parsers
│   └── workflows/      # Workflow implementations
├── adapters/           # Database adapters (milvus, seekdb, mock)
├── campaigns/          # Example campaign configurations
├── contracts/          # Core contracts and DB profiles
├── schemas/            # Pydantic schemas
├── casegen/            # Test case templates
├── oracles/            # Semantic oracles
├── pipeline/           # Execution, preconditions, triage
├── analysis/           # Result analysis and export
├── docs/               # Design documentation
├── packs/              # Generated test case packs
└── results/            # Test execution results
```

## Development

```bash
# Run tests
pytest tests/unit/ -v

# Verify imports
python -c "from schemas import TestCase, BugType; from contracts.core.loader import get_default_contract; print('OK')"
```

## Documentation

- `THEORY.md` - Theoretical foundation and dual-layer validity model
- `PROJECT_SCOPE.md` - Project boundaries and success criteria
- `BUG_TAXONOMY.md` - Four-type defect classification with red-line constraint

## License

MIT License - Research prototype for academic use
