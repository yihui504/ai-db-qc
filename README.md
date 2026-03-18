# AI-DB-QC: Contract-Driven Vector Database QA Framework

A **contract-driven, adapter-based, evidence-backed** system for automated testing and semantic defect discovery in vector databases.

---

## Overview

AI-DB-QC automates the discovery of semantic bugs, API violations, and correctness issues across multiple vector databases. Rather than writing manual tests, users define **formal contracts** that specify expected behavior. The framework generates test cases from those contracts, executes them against real databases, and classifies results using a multi-layer oracle system.

The framework has been validated against four major vector databases at their latest versions, discovering **22 bugs** across boundary conditions, schema operations, and stress testing -- with **8 confirmed issues** backed by complete documentation-behavior-analysis evidence chains.

### Supported Databases

| Database | Version Tested | Adapter | Status |
|----------|---------------|---------|--------|
| **Milvus** | v2.6.12 | `milvus_adapter.py` | Full support |
| **Qdrant** | v1.17.0 | `qdrant_adapter.py` | Full support |
| **Weaviate** | v1.36.5 | `weaviate_adapter.py` | Full support |
| **Pgvector** | v0.8.2 (pg17) | `pgvector_adapter.py` | Full support |
| **SeekDB** | - | `seekdb_adapter.py` | Experimental |
| **Mock** | - | `mock.py` | In-memory reference |

---

## Quick Start

### Prerequisites

- Python 3.11+
- Docker (for running databases)
- Git

### Installation

```bash
git clone https://github.com/yihui504/ai-db-qc.git
cd ai-db-qc
pip install -e .
```

### Launch Databases

```bash
docker compose up -d
```

This starts Milvus, Qdrant, Weaviate, and PostgreSQL (with pgvector) as defined in `docker-compose.yml`.

### Run a Test Campaign

```bash
# Run boundary condition tests
python scripts/run_boundary_tests.py

# Run stress tests
python scripts/run_stress_tests.py

# Run schema evolution tests
python scripts/run_schema_evolution.py

# Run the full bug mining pipeline
python scripts/run_bug_mining.py
```

### Verify Installation

```bash
python -c "from core.oracle_engine import OracleEngine; print('OK')"
python -c "from adapters.milvus_adapter import MilvusAdapter; print('OK')"
```

---

## Architecture

```
Contracts (JSON/YAML)
    |
    v
Test Generator (casegen/)
    |
    v
Generated Tests (generated_tests/)
    |
    v
Adapter Layer (adapters/)  --->  Database Instances
    |
    v
Multi-Layer Oracle (oracles/)
    |
    v
Classification: PASS | VIOLATION | ALLOWED_DIFFERENCE | OBSERVATION
```

### Core Components

| Component | Location | Description |
|-----------|----------|-------------|
| **Contract Registry** | `core/contract_registry.py` | Loads and indexes contract definitions |
| **Test Generator** | `core/contract_test_generator.py` | Creates test cases from contracts |
| **Case Generators** | `casegen/` | Fuzzing, boundary, and discovery generators |
| **Adapter Layer** | `adapters/` | Abstracts database-specific operations |
| **Oracle Engine** | `core/oracle_engine.py` | Primary evaluation engine |
| **Multi-Layer Oracles** | `oracles/` | Differential, metamorphic, recall, monotonicity, trivalent, filter strictness, write-read consistency, sequence assertion |
| **Schemas** | `schemas/` | Pydantic data models for tests and results |
| **Pipeline** | `pipeline/` | Execution orchestration |

---

## Contract Library

Contracts are organized into families covering different testing dimensions:

| Family | Directory | Contracts | Focus |
|--------|-----------|-----------|-------|
| **ANN** | `contracts/ann/` | 5 | Search correctness: top-k cardinality, distance metrics, NN inclusion |
| **Index** | `contracts/index/` | 4 | Index behavior: semantic neutrality, data preservation |
| **Hybrid** | `contracts/hybrid/` | 3 | Filter + vector search interaction |
| **Schema** | `contracts/schema/` | 15 | Schema evolution, boundary conditions, stress testing |
| **Concurrency** | `contracts/conc/` | - | Concurrent operation contracts |
| **Constraints** | `contracts/cons/` | - | Constraint validation contracts |

### Contract Format

```json
{
  "contract_id": "BND-001",
  "name": "Dimension Boundaries",
  "type": "universal",
  "statement": "Vector dimensions must be validated against documented limits",
  "scope": {
    "databases": ["all"],
    "operations": ["create_collection", "insert"]
  },
  "violation_criteria": {
    "condition": "invalid_dimension_accepted",
    "severity": "high"
  },
  "oracle": {
    "check": "dimension_within_valid_range"
  }
}
```

---

## Bug Discovery Results

### Latest Campaign: AGGRESSIVE_BUG_MINING_2025_001

Tested against the latest versions of all four databases using 8 contracts and 48 test cases across schema evolution, boundary conditions, and stress testing.

**Summary**: 22 bugs discovered, 8 filed as confirmed issues with complete evidence chains.

| Severity | Count | Details |
|----------|-------|---------|
| **Critical** | 1 | Qdrant 502 crash under load (ISSUE-002) |
| **High** | 3 | Weaviate/Pgvector dimension & top-k issues (ISSUE-005, 007, 008) |
| **Medium** | 4 | Metric validation, naming, top-k issues (ISSUE-001, 003, 004, 006) |

### Key Findings

**Qdrant** exhibited the most severe issues, including a critical 502 Bad Gateway crash at just 1000 RPS (ISSUE-002), along with missing metric validation (ISSUE-004) and lenient collection naming rules (ISSUE-003).

**Weaviate** and **Pgvector** both accepted clearly invalid dimensions (0, -1, 100000) without rejection (ISSUE-005, ISSUE-007), and both produced internal errors rather than graceful error messages when given top_k=0 (ISSUE-006, ISSUE-008).

**Milvus** showed the fewest issues -- only one confirmed bug (ISSUE-001) for accepting unsupported metric types. Its strict validation on dimensions and top_k was generally correct per documentation.

See `results/issues/` for detailed evidence-chain reports on each confirmed issue.

### Bug Classification

| Type | Description | Severity |
|------|-------------|----------|
| **TYPE-1** | Invalid input accepted (no rejection) | HIGH |
| **TYPE-2** | Valid input rejected (poor diagnostics) | MEDIUM |
| **TYPE-3** | Valid input causes crash / internal error | HIGH |
| **TYPE-4** | Operation succeeds but violates semantic invariant | MEDIUM |

---

## Evidence Chain Methodology

Each confirmed bug follows a three-part evidence chain:

1. **Documentation Evidence** -- Official documentation quotes and URLs establishing the expected behavior
2. **Actual Behavior** -- Raw test results from automated execution showing the observed behavior
3. **Analysis** -- Impact assessment, root cause analysis, and recommended fix

Bugs where documentation evidence is ambiguous or confirms the behavior is expected are **not** filed as issues. This rigorous filtering ensures that every filed issue is backed by a genuine documentation-behavior contradiction.

---

## Project Structure

```
ai-db-qc/
├── adapters/                # Database adapters (Milvus, Qdrant, Weaviate, Pgvector, SeekDB, Mock)
├── ai_db_qa/               # Semantic data generation, embedding, multi-layer oracle
├── archive/                 # Historical artifacts (v1 issues, old reports)
├── campaigns/               # Campaign configurations (YAML)
├── capabilities/            # Capability descriptions (JSON)
├── casegen/                 # Test case generators
│   ├── fuzzing/             # Fuzzing strategies
│   ├── generators/          # Discovery and hybrid generators
│   └── templates/           # Contract templates (YAML)
├── configs/                 # Database connection configs
├── contracts/               # Contract definitions
│   ├── ann/                 # ANN correctness contracts
│   ├── conc/                # Concurrency contracts
│   ├── cons/                # Constraint contracts
│   ├── core/                # Core contract definitions
│   ├── db_profiles/         # Per-database profiles
│   ├── hybrid/              # Hybrid query contracts
│   ├── index/               # Index behavior contracts
│   └── schema/              # Schema, boundary, stress contracts
├── core/                    # Framework core (registry, generator, oracle engine)
├── docs/                    # Documentation, design docs, reports, paper materials
├── evidence/                # Bug evidence collection utilities
├── generated_tests/         # Generated test case files (JSON)
├── oracles/                 # Multi-layer oracle system
├── pipeline/                # Execution pipeline
├── results/                 # Test results, bug mining reports, filed issues
│   ├── issues/              # Evidence-chain issue files
│   ├── boundary_*/          # Boundary test results
│   ├── stress_*/            # Stress test results
│   └── schema_evolution_*/  # Schema evolution results
├── schemas/                 # Pydantic schemas for tests and results
├── scripts/                 # Execution and analysis scripts
├── tests/                   # Unit and integration tests
├── docker-compose.yml       # Database deployment configuration
├── pyproject.toml           # Python project configuration
└── requirements.txt         # Python dependencies
```

---

## Development

### Run Tests

```bash
# Unit tests
pytest tests/ -v

# Specific test modules
pytest tests/test_fuzzing_strategies.py -v
```

### Run a Smoke Test

```bash
python run_smoke.py
```

### Database Health Checks

```bash
python scripts/_health_check.py
```

---

## Documentation

Key documents are organized under `docs/`:

- [Project Scope & Theory](docs/PROJECT_SCOPE.md) | [Theory](docs/THEORY.md)
- [Framework Architecture](docs/FRAMEWORK_ARCHITECTURE.md) | [Contract Model](docs/CONTRACT_MODEL.md)
- [Oracle Methodology](docs/oracle_methodology.md) | [Bug Taxonomy](docs/BUG_TAXONOMY.md)
- [Concurrency Contract Design](docs/CONCURRENCY_CONTRACT_DESIGN.md)
- [Bug Mining Execution Report](results/BUG_MINING_REPORT_v2.md) | [Issues Summary](results/issues/ISSUES_SUMMARY.md)
- [Historical Bugs Analysis](docs/historical_bugs_analysis.md) | [Defect Analysis](docs/defect_analysis_report.md)

---

## Citation

If you use this framework in your research, please cite:

```bibtex
@software{ai_db_qc_2026,
  title = {AI-DB-QC: Contract-Driven Vector Database QA Framework},
  author = {AI-DB-QC Framework Team},
  year = {2026},
  url = {https://github.com/yihui504/ai-db-qc}
}
```

---

## License

MIT License - Research prototype for academic and industrial use.
