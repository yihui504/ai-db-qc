# AI-DB-QC Project Overview

**Project**: AI Database Quality Assurance Framework
**Status**: Active Development (Milestone: R1-R5C Complete)
**Date**: 2026-03-10

---

## What is AI-DB-QC?

AI-DB-QC is a **contract-driven testing framework** for AI databases, specifically vector and hybrid retrieval databases. It automates the discovery of semantic bugs, API violations, and correctness issues in databases like Milvus, Qdrant, and Weaviate.

The project addresses a critical gap: **AI databases lack comprehensive testing tools**. Traditional database testing focuses on ACID properties and SQL correctness, but vector databases introduce new semantic dimensions (approximate nearest neighbor search, vector similarity, hybrid filtering) that require new testing approaches.

---

## The Problem: Why AI Databases Need Better Testing

### Unique Challenges of Vector Databases

1. **Approximate Algorithms**: ANN (Approximate Nearest Neighbor) indexes trade accuracy for speed, making correctness judgment difficult
2. **Semantic Invariants**: "Similar vectors should return similar results" is hard to test automatically
3. **Complex State**: Index types, metric types, collection states create large input spaces
4. **Vendor Fragmentation**: Different databases have different APIs, parameters, and behaviors

### Current Testing Gaps

- Manual testing is slow and incomplete
- Existing tools focus on performance, not correctness
- No systematic way to define and verify semantic contracts
- Bug discovery is often incidental, not systematic

---

## What is "Contract-Driven Testing"?

### Core Concept

A **contract** is a formal specification of expected database behavior:

```json
{
  "contract_id": "ANN-001",
  "name": "Top-K Cardinality Correctness",
  "statement": "Search with top_k parameter must return at most K results",
  "preconditions": ["collection_exists", "top_k >= 0"],
  "postconditions": ["length(results) <= top_k"],
  "violation_criteria": {
    "condition": "length(search_results) > top_k",
    "severity": "high"
  }
}
```

### How It Works

```
Contract Definition → Test Generation → Database Execution → Oracle Evaluation → Classification
       (JSON)              (Python)            (Adapter)           (Engine)         (PASS/VIOLATION)
```

1. **Define Contract**: Specify what correct behavior looks like
2. **Generate Tests**: Automatically create test cases from contract
3. **Execute Tests**: Run tests against real database
4. **Evaluate Results**: Oracle checks if results satisfy contract
5. **Classify**: PASS (correct), VIOLATION (bug), ALLOWED_DIFFERENCE (architectural variance)

### Why Contract-Driven?

| Aspect | Traditional Testing | Contract-Driven Testing |
|--------|---------------------|-------------------------|
| **Test Creation** | Manual, ad-hoc | Automated from specifications |
| **Correctness Judgment** | Human inspection | Formal oracle evaluation |
| **Coverage** | Incomplete | Systematic exploration of input space |
| **Reproducibility** | Low | High (deterministic) |
| **Scalability** | Limited | High (contracts are reusable) |

---

## Target Databases

### Primary Target: Vector Databases

Vector databases store and search high-dimensional vectors (embeddings) for similarity search:

- **Milvus**: Open-source, PostgreSQL-like architecture
- **Qdrant**: Rust-based, focus on performance
- **Weaviate**: GraphQL-based, knowledge graph integration

### Why Vector Databases?

1. **Growing Importance**: Powering RAG (Retrieval Augmented Generation), semantic search, recommendation systems
2. **Complex Semantics**: ANN approximation, metric types (L2, IP, COSINE), hybrid queries
3. **Rapidly Evolving**: New features, insufficient testing practices
4. **Production Critical**: Errors affect AI application correctness

### Secondary Target: Hybrid Retrieval

Databases that combine vector search with structured filters (e.g., "find similar vectors WHERE color='red'")

---

## Framework Architecture

### High-Level Components

```
┌─────────────────────────────────────────────────────────────────┐
│                        AI-DB-QC Framework                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌───────────────┐     ┌─────────────────┐     ┌─────────────┐ │
│  │   Contract    │────▶│   Test          │────▶│   Adapter   │ │
│  │   Registry    │     │   Generator     │     │   Layer     │ │
│  └───────────────┘     └─────────────────┘     └─────────────┘ │
│           │                      │                     │         │
│           ▼                      ▼                     ▼         │
│  ┌───────────────┐     ┌─────────────────┐     ┌─────────────┐ │
│  │   Contract    │     │   Execution     │────▶│   Database  │ │
│  │   Files       │     │   Pipeline      │     │   (Milvus)  │ │
│  └───────────────┘     └─────────────────┘     └─────────────┘ │
│                                                         │         │
│                                                         ▼         │
│                                                  ┌─────────────┐ │
│                                                  │   Oracle    │ │
│                                                  │   Engine    │ │
│                                                  └─────────────┘ │
│                                                         │         │
│                                                         ▼         │
│                                                  ┌─────────────┐ │
│                                                  │ Classification││
│                                                  │ (PASS/VIOL.) │ │
│                                                  └─────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Component Descriptions

#### 1. Contract Registry
- Loads contract definitions from JSON files
- Validates contract schema and dependencies
- Provides contract lookup and statistics

**File**: `contracts/core/loader.py`

#### 2. Contract Test Generator
- Generates test cases from contract definitions
- Expands parameter ranges (boundary, legal, illegal cases)
- Attaches oracle definitions to tests

**File**: `core/contract_test_generator.py`

#### 3. Adapter Layer
- Abstracts database-specific operations
- Supports: Milvus, Mock, SeekDB (experimental)
- Executes: create_collection, insert, build_index, search, etc.

**Files**: `adapters/milvus_adapter.py`, `adapters/mock.py`

#### 4. Execution Pipeline
- Executes test sequences against database
- Collects results and metadata
- Handles cleanup and error recovery

**Files**: `pipeline/execute.py`, `pipeline/preconditions.py`

#### 5. Oracle Engine
- Evaluates results against contract oracles
- Classifies outcomes: PASS, VIOLATION, ALLOWED_DIFFERENCE, OBSERVATION
- Provides reasoning and evidence

**File**: `core/oracle_engine.py`

---

## Current Capabilities

### Contract Library (16 Contracts)

| Family | Contracts | Focus |
|--------|-----------|-------|
| **ANN** | 5 | Search correctness (top-k, distance, metrics) |
| **Index** | 4 | Index behavior (semantic neutrality, data preservation) |
| **Hybrid** | 3 | Filter + vector search interaction |
| **Schema** | 4 | Schema evolution and metadata accuracy |

### Database Support

| Database | Status | Operations Supported |
|----------|--------|---------------------|
| **Milvus** | ✅ Full | create_collection, insert, build_index, search, filtered_search |
| **Mock** | ✅ Full | All operations (in-memory) |
| **SeekDB** | ⚠️ Experimental | Basic operations only |
| **Qdrant** | ❌ Planned | Not yet implemented |

### Bug Classification

Four-type taxonomy for contract violations:

| Type | Description | Severity |
|------|-------------|----------|
| **Type-1** | Illegal operation succeeded | HIGH |
| **Type-2** | Illegal operation failed without diagnostic error | MEDIUM |
| **Type-3** | Legal operation failed/crashed | HIGH |
| **Type-4** | Legal operation succeeded but violates semantic invariant | MEDIUM |

---

## Project Status

### Completed Milestones (R1-R5C)

| Milestone | Focus | Tests | Bugs Found | Status |
|-----------|-------|-------|------------|--------|
| **R1** | Parameter Boundary Testing | 50 | 3 | ✅ Complete |
| **R2** | API Validation / Usability | 40 | 2 | ✅ Complete |
| **R3** | Sequence & State Testing | 30 | 1 | ✅ Complete |
| **R4** | Differential Semantic Testing | 100+ | 4 | ✅ Complete |
| **R5A** | ANN Contract Testing | 10 | 0 | ✅ Complete |
| **R5C** | Hybrid Query Contract Testing | 14 | 0 | ✅ Complete |

**Total**: 244 tests executed, 10 contract violations discovered

### Current Focus: R5B (Index Contracts)

Next milestone focusing on index behavior contracts with refined oracle design to address ANN approximation tolerance.

---

## Key Findings So Far

### 1. Milvus Core Operations Are Robust

- ANN search: No contract violations (R5A)
- Hybrid queries: No contract violations (R5C)
- Conclusion: Well-tested core functionality

### 2. Parameter Validation Has Gaps

- Invalid metric types accepted (Type-1 bug)
- Invalid index types accepted (Type-1 bug)
- Poor error messages for invalid parameters (Type-2 bug)

### 3. Differential Testing Reveals Implementation Differences

- Cross-database behavior varies significantly
- "Allowed differences" are common (not bugs)
- Need for database-specific contracts

### 4. Contract-Driven Approach Works

- Test generation automation is effective
- Oracle evaluation is sound for well-defined contracts
- Framework successfully classifies PASS vs VIOLATION

### 5. Bug Discovery is Challenging

- Low bug yield on mature databases (Milvus)
- ANN approximation tolerance complicates oracles
- Need for more sophisticated contracts

---

## Usage Example

### Define a Contract

```json
// contracts/ann/ann-001-top-k-cardinality.json
{
  "contract_id": "ANN-001",
  "name": "Top-K Cardinality Correctness",
  "statement": "Search with top_k must return at most K results",
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
```

### Execute Tests

```python
from adapters.milvus_adapter import MilvusAdapter
from pipeline.execute import execute_test_sequence

adapter = MilvusAdapter({"host": "localhost", "port": 19530})

for test in tests:
    result = execute_test_sequence(test, adapter)
    # result contains execution data
```

### Evaluate Results

```python
from core.oracle_engine import OracleEngine

engine = OracleEngine()

for test, result in zip(tests, results):
    oracle_result = engine.evaluate(test.contract_id, result)
    print(f"{test.test_id}: {oracle_result.classification.value}")
    # Output: ann-001_boundary_001: PASS
```

---

## Documentation Structure

```
docs/
├── PROJECT_OVERVIEW.md           # This file
├── PROJECT_PROGRESS_SUMMARY.md   # Campaign history and results
├── FRAMEWORK_ARCHITECTURE.md     # Technical architecture details
├── CURRENT_CHALLENGES.md          # Known limitations and challenges
├── NEXT_ROADMAP.md               # Future plans and direction
├── CONTRACT_MODEL.md             # Contract specification format
├── CONTRACT_DRIVEN_FRAMEWORK_DESIGN.md  # Framework design
├── BUG_TAXONOMY.md               # Bug classification system
├── R*_FINAL_SUMMARY.md           # Per-milestone reports
└── issues/                       # Discovered bug reports
```

---

## Contributing

The project is in active development. Key areas for contribution:

1. **Database Adapters**: Add support for Qdrant, Weaviate, Pinecone
2. **Contract Library**: Expand coverage (concurrency, transactions)
3. **Oracle Engine**: Improve semantic oracles for complex contracts
4. **Test Generation**: Enhance strategies (combinatorial, property-based)

---

## License

MIT License - Research prototype for academic and industrial use

---

**Last Updated**: 2026-03-10
**Milestone**: R1-R5C Complete, R5B (Index Contracts) In Design
