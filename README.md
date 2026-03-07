# AI-DB-QC: AI Database Quality Assurance Prototype

A contract-driven, adapter-based, evidence-backed prototype system for automated testing and defect discovery in AI databases (vector/hybrid retrieval databases).

## Research Framing

This system implements two core research functions:

1. **Structured Test Case Generation** - Systematic exploration of input space
2. **Structured Correctness Judgment** - Contract-based validation with semantic oracles

## Bug Taxonomy

All findings are classified into four top-level types:

- **Type-1**: Illegal operation succeeded (should fail but succeeded)
- **Type-2**: Illegal operation failed without diagnostic error
  - **Type-2.PreconditionFailed** (subtype): Contract-valid but precondition-fail with poor diagnostic
- **Type-3**: Legal operation failed/crashed/hung
- **Type-4**: Legal operation succeeded but violates semantic invariant

**Critical**: Type-3 and Type-4 require `precondition_pass=true` (red-line constraint).

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/unit/ -v

# Verify setup
python -c "from schemas import TestCase, BugType; from contracts.core.loader import get_default_contract; print('OK')"
```

## Project Structure

```
ai-db-qc/
├── contracts/          # Core contracts (agnostic) and DB profiles (specific)
├── schemas/            # Pydantic schemas for all data structures
├── casegen/            # Test case templates and generation
├── tests/              # Unit tests
├── docs/               # Plans and documentation
├── THEORY.md           # Theoretical foundation
├── PROJECT_SCOPE.md    # Scope boundaries
├── BUG_TAXONOMY.md     # Defect classification framework
└── README.md           # This file
```

## Documentation

- `THEORY.md` - Theoretical foundation and dual-layer validity model
- `PROJECT_SCOPE.md` - Project boundaries and success criteria
- `BUG_TAXONOMY.md` - Four-type defect classification with red-line constraint

## License

MIT License - Research prototype for academic use
