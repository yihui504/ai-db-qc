# AI-DB-QC: Contract-Driven Vector Database QA Framework

A **contract-driven, adapter-based, evidence-backed** system for automated testing and semantic defect discovery in AI databases (vector and hybrid retrieval databases).

---

## What is AI-DB-QC?

AI-DB-QC is a research framework that automates the discovery of semantic bugs, API violations, and correctness issues in vector databases like Milvus, Qdrant, and Weaviate. It uses **formal contracts** to define expected behavior and **semantic oracles** to classify test results.

### Key Innovation: Contract-Driven Testing

Instead of writing manual tests, you define **contracts** - formal specifications of correct behavior. The framework automatically generates test cases, executes them against real databases, and classifies results as:

- **PASS**: Contract satisfied
- **VIOLATION**: Bug discovered
- **ALLOWED_DIFFERENCE**: Architectural variance (not a bug)
- **OBSERVATION**: Needs investigation

### Why Vector Databases?

Vector databases power RAG (Retrieval Augmented Generation), semantic search, and recommendation systems. They have unique testing challenges:

- **Approximate algorithms**: ANN trades accuracy for speed
- **Complex semantics**: Vector similarity, metric types, hybrid queries
- **Vendor fragmentation**: Different APIs and behaviors
- **Rapidly evolving**: New features, insufficient testing

**AI-DB-QC addresses these gaps** with systematic, automated, evidence-backed testing.

---

## Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/your-org/ai-db-qc.git
cd ai-db-qc

# Install dependencies
pip install -e .

# Verify installation
python -c "from core.oracle_engine import OracleEngine; print('OK')"
```

### Define a Contract

```json
// contracts/ann/ann-001-top-k-cardinality.json
{
  "contract_id": "ANN-001",
  "name": "Top-K Cardinality Correctness",
  "statement": "Search with top_k parameter must return at most K results",
  "type": "universal",
  "scope": {
    "databases": ["all"],
    "operations": ["search"]
  },
  "violation_criteria": {
    "condition": "length(search_results) > top_k",
    "severity": "high"
  }
}
```

### Generate Tests

```python
from core.contract_test_generator import ContractTestGenerator

generator = ContractTestGenerator()
tests = generator.generate_by_family("ann")
generator.save_tests(tests, "ann_tests")

# Output: generated_tests/ann_tests_TIMESTAMP.json
```

### Execute Tests

```python
from adapters.milvus_adapter import MilvusAdapter
from core.oracle_engine import OracleEngine

# Initialize adapter
adapter = MilvusAdapter({"host": "localhost", "port": 19530})

# Execute tests
results = []
for test in tests:
    result = execute_test_sequence(test, adapter)
    results.append(result)

# Evaluate with oracle
oracle = OracleEngine()
for test, result in zip(tests, results):
    oracle_result = oracle.evaluate(test.contract_id, result)
    print(f"{test.test_id}: {oracle_result.classification.value}")
```

---

## Current Status

### Completed Milestones

| Milestone | Focus | Tests | Bugs Found | Status |
|-----------|-------|-------|------------|--------|
| **R1** | Parameter Boundary Testing | 50 | 3 | ✅ Complete |
| **R2** | API Validation / Usability | 40 | 2 | ✅ Complete |
| **R3** | Sequence & State Testing | 30 | 1 | ✅ Complete |
| **R4** | Differential Semantic Testing | 100+ | 4* | ✅ Complete |
| **R5A** | ANN Contract Testing | 10 | 0 | ✅ Complete |
| **R5C** | Hybrid Query Contract Testing | 14 | 0 | ✅ Complete |

*Most R4 findings were ALLOWED_DIFFERENCE (architectural variance)

**Total**: 244 tests executed, 10 contract violations discovered

### Current Focus: R5B (Index Contracts)

**Status**: Design complete, implementation pending

**Scope**: 6 tests (revised from 16 after pre-implementation audit)

**Key Improvement**: Refined IDX-001 oracle separates hard contract checks from ANN approximation tolerance

**Documentation**:
- [R5B Design](docs/R5B_INDEX_PILOT_REVISED.md)
- [Pre-Implementation Audit](docs/R5B_PREIMPLEMENTATION_AUDIT.md)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          AI-DB-QC Framework                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐         │
│  │   Contract   │────▶│    Test      │────▶│  Execution   │         │
│  │   Registry   │     │   Generator  │     │   Pipeline   │         │
│  └──────────────┘     └──────────────┘     └───────┬──────┘         │
│         │                      │                     │                │
│         ▼                      ▼                     ▼                │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐       │
│  │   Contract   │     │   Generated   │────▶│    Adapter    │       │
│  │    Files     │     │    Tests      │     │    Layer      │       │
│  └──────────────┘     └──────────────┘     └───────┬──────┘       │
│                                                     │                │
│                                                     ▼                │
│                                              ┌──────────────┐       │
│                                              │   Database    │       │
│                                              │   (Milvus)    │       │
│                                              └──────────────┘       │
│                                                     │                │
│                                                     ▼                │
│                                              ┌──────────────┐       │
│                                              │   Oracle     │       │
│                                              │   Engine     │       │
│                                              └───────┬──────┘       │
│                                                      │              │
│                                                      ▼              │
│                                              ┌──────────────┐       │
│                                              │ Classification│       │
│                                              │ PASS/VIOL.   │       │
│                                              └──────────────┘       │
└─────────────────────────────────────────────────────────────────────────┘
```

### Core Components

- **Contract Registry**: Loads and indexes contract definitions
- **Test Generator**: Creates test cases from contracts
- **Adapter Layer**: Abstracts database-specific operations
- **Execution Pipeline**: Orchestrates test execution
- **Oracle Engine**: Evaluates results against contracts

### Supported Databases

| Database | Status | Operations |
|----------|--------|------------|
| **Milvus** | ✅ Full | create, insert, build_index, search, filtered_search, drop |
| **Mock** | ✅ Full | All operations (in-memory) |
| **SeekDB** | ⚠️ Experimental | Basic operations |
| **Qdrant** | ❌ Planned | - |

---

## Contract Library

### 16 Contracts Across 4 Families

| Family | Contracts | Focus |
|--------|-----------|-------|
| **ANN** | 5 | Search correctness (top-k, distance, metrics, NN inclusion) |
| **Index** | 4 | Index behavior (semantic neutrality, data preservation) |
| **Hybrid** | 3 | Filter + vector search interaction |
| **Schema** | 4 | Schema evolution and metadata accuracy |

### Contract Format

```json
{
  "contract_id": "ANN-001",
  "name": "Top-K Cardinality Correctness",
  "family": "ANN",
  "type": "universal",
  "statement": "Search with top_k must return at most K results",
  "preconditions": ["collection_exists", "top_k >= 0"],
  "postconditions": ["length(results) <= top_k"],
  "violation_criteria": {
    "condition": "length(search_results) > top_k",
    "severity": "high"
  },
  "test_generation": {
    "strategy": "boundary",
    "parameters": {"top_k": [0, 1, 10, 100]}
  },
  "oracle": {
    "check": "count(results) <= top_k"
  }
}
```

---

## Bug Classification

Findings are classified into four types:

| Type | Description | Severity |
|------|-------------|----------|
| **Type-1** | Illegal operation succeeded | HIGH |
| **Type-2** | Illegal operation failed without diagnostic error | MEDIUM |
| **Type-3** | Legal operation failed/crashed | HIGH |
| **Type-4** | Legal operation succeeded but violates semantic invariant | MEDIUM |

### Example Bugs Found

1. **issue_001**: Invalid metric_type "INVALID" accepted (Type-1)
2. **issue_002**: Invalid index_type accepted (Type-1)
3. **issue_003**: Invalid top_k returns unclear error (Type-2)
4. **issue_004**: Silent parameter ignoring (Type-2)

See [docs/issues/](docs/issues/) for full details.

---

## Documentation

### Core Documents

- **[PROJECT_OVERVIEW](docs/PROJECT_OVERVIEW.md)**: Project introduction and goals
- **[PROJECT_PROGRESS_SUMMARY](docs/PROJECT_PROGRESS_SUMMARY.md)**: Campaign history and results
- **[FRAMEWORK_ARCHITECTURE](docs/FRAMEWORK_ARCHITECTURE.md)**: Technical architecture
- **[CURRENT_CHALLENGES](docs/CURRENT_CHALLENGES.md)**: Known limitations
- **[NEXT_ROADMAP](docs/NEXT_ROADMAP.md)**: Future direction

### Design Documents

- **[CONTRACT_MODEL](docs/CONTRACT_MODEL.md)**: Contract specification format
- **[CONTRACT_DRIVEN_FRAMEWORK_DESIGN](docs/CONTRACT_DRIVEN_FRAMEWORK_DESIGN.md)**: Framework design
- **[BUG_TAXONOMY](docs/BUG_TAXONOMY.md)**: Classification system

### Campaign Reports

- **[R5A_ANN_PILOT_REPORT](docs/R5A_ANN_PILOT_REPORT.md)**: ANN contract testing results
- **[R5C_HYBRID_PILOT_REPORT](docs/R5C_HYBRID_PILOT_REPORT.md)**: Hybrid query testing results
- **[R4_FULL_REPORT](docs/R4_FULL_REPORT.md)**: Differential testing results

---

## Project Structure

```
ai-db-qc/
├── contracts/              # Contract definitions (JSON)
│   ├── ann/               # ANN contracts (5)
│   ├── index/             # Index contracts (4)
│   ├── hybrid/            # Hybrid contracts (3)
│   └── schema/            # Schema contracts (4)
│
├── core/                  # Framework core
│   ├── contract_registry.py
│   ├── contract_test_generator.py
│   └── oracle_engine.py
│
├── adapters/              # Database adapters
│   ├── milvus_adapter.py
│   ├── mock.py
│   └── base.py
│
├── pipeline/              # Execution pipeline
│   ├── execute.py
│   └── preconditions.py
│
├── schemas/               # Pydantic schemas
│   └── *.py
│
├── scripts/               # Execution scripts
│   ├── run_ann_pilot.py
│   └── run_hybrid_pilot.py
│
├── docs/                  # Documentation
│   └── *.md
│
├── generated_tests/       # Generated test cases
└── results/               # Test execution results
```

---

## Usage Examples

### Example 1: Test ANN Correctness

```python
from core.contract_registry import get_registry
from core.contract_test_generator import ContractTestGenerator
from adapters.milvus_adapter import MilvusAdapter
from core.oracle_engine import OracleEngine

# Load contracts
registry = get_registry()
registry.load_all()

# Generate ANN tests
generator = ContractTestGenerator()
ann_tests = generator.generate_by_family("ann")

# Execute on Milvus
adapter = MilvusAdapter({"host": "localhost", "port": 19530})
oracle = OracleEngine()

for test in ann_tests:
    result = execute_test_sequence(test, adapter)
    oracle_result = oracle.evaluate(test.contract_id, result)
    print(f"{test.test_id}: {oracle_result.classification.value}")
```

### Example 2: Define Custom Contract

```python
# Create contract file: contracts/custom/cust-001.json
{
  "contract_id": "CUST-001",
  "name": "Custom Index Behavior",
  "family": "INDEX",
  "type": "database_specific",
  "statement": "Index creation must not affect data count",
  "violation_criteria": {
    "condition": "count_before != count_after",
    "severity": "critical"
  }
}

# Generate and test
generator = ContractTestGenerator()
tests = generator.generate_by_contract("CUST-001")
# ... execute as above
```

---

## Development

### Run Tests

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# Oracle tests
pytest tests/test_oracle.py -v
```

### Verify Installation

```bash
python -c "from core.oracle_engine import OracleEngine; print('OK')"
python -c "from adapters.milvus_adapter import MilvusAdapter; print('OK')"
python -c "from core.contract_registry import get_registry; print('OK')"
```

---

## Contributing

We welcome contributions in these areas:

1. **Database Adapters**: Add support for Qdrant, Weaviate, Pinecone
2. **Contract Library**: Expand coverage (concurrency, transactions)
3. **Oracle Engine**: Improve semantic oracles
4. **Test Generation**: Property-based testing, combinatorial strategies

See [docs/NEXT_ROADMAP.md](docs/NEXT_ROADMAP.md) for detailed plans.

---

## Key Findings

### Milvus Quality Assessment

After 244 tests across 6 campaigns:

- **Core Operations**: Robust and correct
- **ANN Search**: No contract violations (R5A)
- **Hybrid Queries**: No contract violations (R5C)
- **Parameter Validation**: Some gaps (invalid metric_type accepted)

**Conclusion**: Milvus is a mature, well-tested database for core operations.

### Framework Validation

The contract-driven approach is **validated and effective**:

- ✅ Automated test generation works
- ✅ Oracle evaluation is sound
- ✅ End-to-end execution is reliable
- ⚠️ Bug-yield is low on mature databases

---

## Current Challenges

1. **Low Bug-Yield**: Milvus core operations are well-tested
2. **ANN Approximation**: Distinguishing bugs from allowed differences
3. **Adapter Limitations**: Hardcoded parameters, missing operations
4. **Oracle Complexity**: Sophisticated contracts need complex oracles

See [docs/CURRENT_CHALLENGES.md](docs/CURRENT_CHALLENGES.md) for detailed analysis.

---

## Next Steps

### Short-Term (R5B)

Complete index behavior contract testing with refined oracle design.

### Medium-Term

Expand to multiple databases (Qdrant, Weaviate) for higher bug-yield.

### Long-Term

Evolve into general AI database QA framework supporting vector, graph, and time-series databases.

See [docs/NEXT_ROADMAP.md](docs/NEXT_ROADMAP.md) for complete roadmap.

---

## Citation

If you use this framework in your research, please cite:

```bibtex
@software{ai_db_qc_2026,
  title = {AI-DB-QC: Contract-Driven Vector Database QA Framework},
  author = {AI-DB-QC Framework Team},
  year = {2026},
  url = {https://github.com/your-org/ai-db-qc}
}
```

---

## License

MIT License - Research prototype for academic and industrial use

---

## Acknowledgments

- **Milvus**: Open-source vector database (primary testing target)
- **Qdrant**: Rust-based vector database (planned support)
- **Anthropic**: Claude AI for assistance in framework development

---

**Project Status**: Active Development (Milestone: R1-R5C Complete)
**Last Updated**: 2026-03-10
**Next Milestone**: R5B (Index Behavior Contracts)
**Contact**: See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines
