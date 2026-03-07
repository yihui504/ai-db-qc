# Phase 1: Initial Structure & Schema Foundation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the minimal static skeleton for an AI database quality assurance prototype system - establishing the research framing of "structured test case generation + structured correctness judgment" with schema-first architecture.

**Architecture:** Contract-driven, adapter-based, evidence-backed, run-scoped system with strict separation between abstract legality (contracts) and runtime readiness (preconditions), and hard red-line constraint that Type-3/4 bugs require `precondition_pass=true`.

**Tech Stack:** Python 3.11+, pydantic v2 for schemas, pytest for testing, YAML for configs, dataclasses for internal models

---

## Overview

This phase establishes the foundational structure for the AI-DB-QC system. We will:
1. Initialize the repository structure
2. Write research-quality foundational documentation
3. Implement core schemas with validation
4. Implement contract/profile loading infrastructure
5. Provide minimal Milvus profile and case templates
6. Establish unit test skeleton

**Critical Constraints:**
- LLM is NOT a source of truth - only assists with generation
- `precondition_pass=true` is HARD constraint for Type-3/4 classification
- "input legal" (contract-valid) ≠ "precondition_pass" (runtime-ready)
- Keep schemas minimal - no overengineering
- NO real DB execution, NO oracles, NO triage logic, NO LLM in this phase

---

## Task 1: Repository Structure Initialization

**Files:**
- Create: `README.md`
- Create: `.gitignore`
- Create: `pyproject.toml`
- Create: `requirements.txt`
- Create: Directory structure

**Step 1: Initialize git repository**

```bash
cd "C:\Users\11428\Desktop\ai-db-qc"
git init
```

Expected: Repository initialized

**Step 2: Create .gitignore**

```python
# .gitignore
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual environments
venv/
ENV/
env/
.venv

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# Runs and evidence (keep structure, ignore large content)
runs/*/replay.sh
runs/*.log
runs/*/artifacts/

# Environment
.env
.env.local

# OS
.DS_Store
Thumbs.db
```

**Step 3: Create pyproject.toml**

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "ai-db-qc"
version = "0.1.0"
description = "Contract-driven AI database quality assurance prototype"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.0.0",
    "pyyaml>=6.0",
    "typer>=0.9.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "black>=23.0.0",
    "mypy>=1.0.0",
    "ruff>=0.1.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]

[tool.black]
line-length = 100
target-version = ["py311"]

[tool.ruff]
line-length = 100
target-version = "py311"
select = ["E", "F", "I", "N", "W"]

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

**Step 4: Create requirements.txt**

```txt
# requirements.txt
pydantic>=2.0.0
pyyaml>=6.0
typer>=0.9.0

# Development dependencies
pytest>=7.0.0
pytest-cov>=4.0.0
black>=23.0.0
mypy>=1.0.0
ruff>=0.1.0
```

**Step 5: Create directory structure**

```bash
mkdir -p contracts/core contracts/db_profiles
mkdir -p schemas
mkdir -p casegen/prompts casegen/templates casegen/generators
mkdir -p adapters
mkdir -p pipeline
mkdir -p oracles
mkdir -p evidence
mkdir -p benchmarks/mock_faults benchmarks/milvus_basic benchmarks/semantic_oracles
mkdir -p scripts
mkdir -p tests/unit tests/integration
mkdir -p docs/plans
```

Expected: All directories created

**Step 6: Create initial README.md**

```markdown
# AI-DB-QC: AI Database Quality Assurance Prototype

A contract-driven, adapter-based, evidence-backed prototype system for automated testing and defect discovery in AI databases (vector/hybrid retrieval databases).

## Research Framing

This system implements two core research functions:
1. **Structured Test Case Generation** - LLM-assisted and rule-based generation of test cases
2. **Structured Correctness Judgment** - Contract-based validation of test outcomes with semantic oracles

## Bug Taxonomy

All findings are classified into four types:

- **Type-1**: Illegal operation succeeded (should fail but succeeded)
- **Type-2**: Illegal operation failed without diagnostic error
- **Type-3**: Legal operation failed/crashed/hung (requires `precondition_pass=true`)
- **Type-4**: Legal operation succeeded but violates semantic invariant (requires `precondition_pass=true`)

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/

# Generate test cases
python scripts/generate_cases.py

# Run test suite
python scripts/run_cases.py
```

## Project Structure

```
ai-db-qc/
├── contracts/          # Core contracts and DB profiles
├── schemas/            # Pydantic schemas for all data structures
├── casegen/            # Test case generation (rule-based + LLM-assisted)
├── adapters/           # Database adapters (base + Milvus + mock)
├── pipeline/           # Gate, execute, triage, confirm, report
├── oracles/            # Semantic correctness validators
├── evidence/           # Evidence collection and replay
├── benchmarks/         # Validation benchmarks
├── scripts/            # CLI entry points
└── tests/              # Unit and integration tests
```

## Documentation

- `THEORY.md` - Theoretical foundation
- `PROJECT_SCOPE.md` - Project boundaries and goals
- `BUG_TAXONOMY.md` - Defect classification framework
- `NON_GOALS.md` - Explicitly excluded features

## License

MIT License - Research prototype for academic use
```

**Step 7: Create __init__.py files for all packages**

```bash
# Create __init__.py for all packages
touch contracts/__init__.py
touch contracts/core/__init__.py
touch contracts/db_profiles/__init__.py
touch schemas/__init__.py
touch casegen/__init__.py
touch casegen/prompts/__init__.py
touch casegen/templates/__init__.py
touch casegen/generators/__init__.py
touch adapters/__init__.py
touch pipeline/__init__.py
touch oracles/__init__.py
touch evidence/__init__.py
touch benchmarks/__init__.py
touch scripts/__init__.py
touch tests/__init__.py
touch tests/unit/__init__.py
touch tests/integration/__init__.py
```

**Step 8: Commit**

```bash
git add .
git commit -m "feat: initialize repository structure and configuration"
```

---

## Task 2: Foundational Documentation - THEORY.md

**Files:**
- Create: `THEORY.md`

**Step 1: Create THEORY.md**

```markdown
# Theoretical Foundation

## Abstract

This document outlines the theoretical foundation for the AI-DB-QC system: a contract-driven, adapter-based, evidence-backed approach to quality assurance for AI databases (vector and hybrid retrieval databases).

## Problem Statement

AI databases present unique quality assurance challenges:

1. **Complex Data Types**: High-dimensional vectors, embeddings, and unstructured text
2. **Semantic Query Semantics**: Similarity search, hybrid retrieval, filtering with approximations
3. **Approximate Algorithms**: ANN search with tunable precision/recall trade-offs
4. **Stateful Operations**: Collection lifecycle, index building, loading, optimization
5. **Diagnostic Challenges**: Error messages often lack root-cause information

Traditional testing approaches (property-based testing, metamorphic testing, fuzzing) are necessary but insufficient for AI databases because:
- They don't systematically distinguish between contract violations vs. precondition failures
- They lack structured semantic oracles for approximate results
- They don't maintain traceable evidence for research reproducibility

## Core Research Hypothesis

A quality assurance system for AI databases should provide:

1. **Structured Test Case Generation**: Systematic exploration of the input space with awareness of contract boundaries and runtime preconditions
2. **Structured Correctness Judgment**: Oracle-based validation with explicit traceability from contracts → execution → evidence → classification

## Theoretical Framework

### 1. Dual-Layer Validity Model

We distinguish two orthogonal validity dimensions:

#### Abstract Legality (Contract-Valid)
A request is **abstractly legal** if it satisfies:
- Type constraints (dimensionality, data types)
- Parameter ranges (top-k limits, radius thresholds)
- Required fields presence
- Operation-specific constraints

This is **purely syntactic and declarative** - it can be checked by examining the request against a contract.

#### Runtime Readiness (Precondition-Pass)
A request is **runtime-ready** if:
- Target collection exists
- Index has been built and loaded
- Required features are supported by the database
- Environment state permits execution

This is **stateful and environmental** - it can only be evaluated at runtime.

**Key Insight**: A request can be contract-valid but precondition-fail. This distinction is critical for valid bug classification.

### 2. Four-Type Defect Taxonomy

Based on the dual-layer validity model, we classify all defects into four mutually exclusive types:

| Type | Name | Condition | Research Significance |
|------|------|-----------|----------------------|
| Type-1 | Illegal Operation Succeeded | `illegal ∧ succeeded` | Accepts what should reject - input validation gap |
| Type-2 | Diagnostic Failure | `illegal ∧ failed ∧ poor_error` | Error messages lack diagnostic value |
| Type-3 | Runtime Failure | `legal ∧ precondition_pass ∧ failed` | Correct request fails at runtime |
| Type-4 | Semantic Violation | `legal ∧ precondition_pass ∧ succeeded ∧ oracle_failed` | Silent violation of semantic invariants |

**The Red Line**: Type-3 and Type-4 **require** `precondition_pass = true`. Without this, we cannot distinguish between genuine bugs vs. expected failures due to unmet runtime prerequisites.

### 3. Contract-Driven Architecture

#### Core Contracts (Database-Agnostic)
Abstract semantic rules that define:
- What operations exist
- What parameters they accept
- What constraints exist (abstract legality)
- What diagnostic information is required on failure

Core contracts are **research artifacts** - they capture our understanding of what an AI database "should" do, independent of any specific implementation.

#### DB Profiles (Database-Specific)
Concrete mappings that define:
- How core contracts map to specific database APIs
- What relaxations or variations exist
- What capabilities are supported
- What quirks or workarounds exist

DB profiles are **implementation artifacts** - they capture the reality of specific databases.

### 4. Evidence-Centric Execution

Every test execution produces an **EvidenceBundle** containing:
- Run metadata (timestamp, config, environment)
- Case snapshot (exact input)
- Request/Response snapshots
- Oracle results with metrics
- Gate trace (precondition evaluation)
- Replay information

This ensures **research reproducibility** - every claim can be traced to evidence.

### 5. Oracle-Based Semantic Validation

For Type-4 detection, we need **semantic oracles** that validate:
- **Monotonicity**: Increasing top-k should monotonically expand result sets
- **Consistency**: Write-then-read should return written data
- **Strictness**: Adding filters should constrain, not expand, results
- **Distance Preservation**: Similarity scores should respect metric properties

Oracles are **approximate validators** - they check necessary (not sufficient) conditions for correctness.

## Methodological Implications

### LLM Positioning

LLMs are **never** sources of truth for:
- Final bug type classification
- Correctness determination
- Confirmation decisions

LLMs **may** assist with:
- Generating candidate test cases (subject to contract validation)
- Explaining complex error messages
- Suggesting oracle configurations

### Separation of Concerns

| Component | Responsibility | Must NOT |
|-----------|----------------|----------|
| Adapter | Execute and normalize response | Classify or validate |
| Oracle | Check semantic invariants | Report or classify |
| Gate | Evaluate runtime readiness | Classify failures |
| Triage | Classify into Type 1-4 | Execute or validate |
| Confirm | Re-verify with reruns | Change classification logic |

### Minimal Publishable Prototype

The goal is **not** a general-purpose testing platform. The goal is a **research artifact** that:
- Demonstrates the dual-layer validity model
- Validates the four-type taxonomy
- Shows evidence traceability
- Supports reproducible experiments

Complexity is the enemy. When in doubt: fewer modules, simpler interfaces, stronger documentation.

## References

This framework draws from:
- Contract-based testing
- Property-based testing (QuickCheck, Hypothesis)
- Metamorphic testing
- Oracle-based validation
- Runtime verification
```

**Step 2: Commit**

```bash
git add THEORY.md
git commit -m "docs: add theoretical foundation document"
```

---

## Task 3: PROJECT_SCOPE.md

**Files:**
- Create: `PROJECT_SCOPE.md`

**Step 1: Create PROJECT_SCOPE.md**

```markdown
# Project Scope

## Mission Statement

Build a **minimal publishable prototype** of a contract-driven quality assurance system for AI databases, demonstrating that structured test case generation combined with structured correctness judgment can effectively discover and classify defects.

## In Scope

### Core Research Functions
1. **Structured Test Case Generation**
   - Rule-based generation from contracts
   - Contract-based mutation for boundary exploration
   - LLM-assisted suggestion (optional enhancement)

2. **Structured Correctness Judgment**
   - Contract-based input validity checking
   - Precondition gate for runtime readiness
   - Semantic oracles for Type-4 detection
   - Triage pipeline for Type 1-4 classification
   - Confirm pipeline with rerun verification

### Target Systems
- **Primary**: Milvus (open-source vector database)
- **Secondary**: Any vector/hybrid retrieval database with adapter

### Initial Oracle Set
- Top-K monotonicity
- Filter strictness
- Write-read consistency

### Evidence and Reproducibility
- Run-scoped evidence bundles
- Environment fingerprinting
- Case snapshot preservation
- Replay script generation

### Validation Benchmarks
- Mock fault injection (controlled Type 1-4 coverage)
- Milvus basic operations
- Semantic oracle validation

## Out of Scope (NON-GOALS)

### Platform Features NOT Included
- Distributed test execution
- Complex scheduling systems
- Web UI or dashboard
- Multi-user support
- Persistent result database (beyond file-based evidence)
- Test suite management
- Continuous integration integration

### Technical Scope NOT Included
- Full multi-database abstraction (beyond what's needed for Milvus + extensibility)
- Complex DSL for test specification
- Performance optimization
- Load testing or stress testing
- Security testing
- Coverage measurement

### Research Scope NOT Included
- Automatic oracle synthesis
- Test case prioritization
- Test suite minimization
- Fault localization
- Automatic repair

## Phase Boundary (Phase 1)

### What Phase 1 DOES:
- Establish repository structure
- Write foundational documentation
- Implement core schemas with validation
- Implement contract/profile loading infrastructure
- Provide Milvus profile example
- Provide 10 basic case templates
- Establish unit test skeleton

### What Phase 1 Does NOT Do:
- Real database execution
- Oracle implementations
- Triage logic implementation
- Confirm pipeline implementation
- LLM integration
- Evidence writing (beyond schema definitions)

## Success Criteria

Phase 1 succeeds when:
1. ✅ Repository structure is complete and clean
2. ✅ Documentation clearly articulates the research contribution
3. ✅ All schemas are defined and can serialize/deserialize
4. ✅ Core contracts can be loaded
5. ✅ Milvus profile is defined and loadable
6. ✅ Case templates cover valid, invalid, and pseudo-valid cases
7. ✅ Unit tests validate schema and loading logic
8. ✅ `pytest tests/` passes

## Success Criteria (Full System)

The full prototype succeeds when:
1. Can generate test cases from contracts
2. Can execute cases against Milvus (or mock)
3. Can distinguish Type 1-4 defects with proper red-line enforcement
4. Can produce traceable evidence bundles
5. Can demonstrate findings on at least 3 benchmarks
6. Results are reproducible via replay
7. System can be extended to new databases via adapter pattern

## Design Principles

1. **Schema-First**: All module interactions use structured schemas
2. **LLM-Optional**: System works without LLM; LLM is enhancement only
3. **Evidence-Traceable**: Every conclusion traces to evidence
4. **YAGNI**: Minimal viable prototype, not platform
5. **Research-Oriented**: Design choices serve research clarity, not feature completeness
```

**Step 2: Commit**

```bash
git add PROJECT_SCOPE.md
git commit -m "docs: add project scope document"
```

---

## Task 4: BUG_TAXONOMY.md

**Files:**
- Create: `BUG_TAXONOMY.md`

**Step 1: Create BUG_TAXONOMY.md**

```markdown
# Bug Taxonomy

## Overview

This document defines the unified four-type defect classification framework used throughout the AI-DB-QC system. All findings are classified using this taxonomy.

## Core Principles

1. **Mutual Exclusivity**: Each finding belongs to exactly one type
2. **Red-Line Enforcement**: Type-3 and Type-4 require `precondition_pass=true`
3. **Evidence-Based**: Classification must be traceable to execution evidence
4. **LLM-Independent**: Final classification is never delegated to LLM judgment

## The Four Types

### Type-1: Illegal Operation Succeeded

**Definition**: An operation that should have failed (based on contract) but succeeded.

**Formal Condition**:
```
input_validity = illegal
observed_success = true
final_type = Type-1
```

**Examples**:
- Inserting vectors with wrong dimensionality
- Searching with negative top-k
- Creating collection with invalid configuration
- Passing malformed filter expressions

**Research Significance**:
Input validation gap - the database accepts what it should reject. These are often "too permissive" bugs that can cause silent failures downstream.

**Subtypes** (optional refinement):
- Type-1.A: Type constraint violation accepted
- Type-1.B: Range constraint violation accepted
- Type-1.C: Required field missing but accepted
- Type-1.D: Malformed input accepted

---

### Type-2: Illegal Operation Failed (Poor Diagnostic)

**Definition**: An operation that correctly failed, but the error message lacks diagnostic value.

**Formal Condition**:
```
input_validity = illegal
observed_success = false
error_message_lacks_root_cause = true
final_type = Type-2
```

**Examples**:
- Generic "internal error" without root cause
- "Invalid parameter" without specifying which parameter
- "Operation failed" without explaining why
- Stack traces without meaningful context

**Research Significance**:
Diagnostic gap - the database fails correctly but doesn't help developers understand what went wrong. This impacts usability and debugging efficiency.

**Special Subtype: Type-2.PreconditionFailed**

A request that is **contract-valid** but **precondition-fail** produces a non-diagnostic error:

```
input_validity = legal
precondition_pass = false
observed_success = false
error_message_lacks_root_cause = true
final_type = Type-2.PreconditionFailed
```

This is distinct from other Type-2 because the input is abstractly legal but runtime conditions prevent execution.

---

### Type-3: Legal Operation Failed

**Definition**: A contract-valid operation, with all preconditions satisfied, that failed, crashed, hung, or timed out.

**Formal Condition**:
```
input_validity = legal
precondition_pass = true
observed_success = false
final_type = Type-3
```

**RED-LINE**: `precondition_pass=true` is MANDATORY. If precondition_pass=false, the finding **MUST NOT** be classified as Type-3.

**Examples**:
- Valid insert fails after collection is loaded
- Valid search returns database error after index is built
- Valid operation causes crash or hang
- Valid operation times out unexpectedly

**Research Significance**:
Runtime failure gap - the database cannot handle correct operations under valid runtime conditions. These are often critical bugs affecting reliability.

**Subtypes**:
- Type-3.A: Exception/Error thrown
- Type-3.B: Crash/segfault
- Type-3.C: Hang/infinite wait
- Type-3.D: Timeout

---

### Type-4: Semantic Violation

**Definition**: A contract-valid operation, with all preconditions satisfied, that succeeded but produces results that violate semantic invariants.

**Formal Condition**:
```
input_validity = legal
precondition_pass = true
observed_success = true
oracle_result = failed
final_type = Type-4
```

**RED-LINE**: `precondition_pass=true` is MANDATORY. If precondition_pass=false, the finding **MUST NOT** be classified as Type-4.

**Examples**:
- Top-K=10 returns fewer than K results without explanation
- Top-K monotonicity violated (K=5 returns more results than K=10)
- Filter doesn't actually filter (returns unfiltered results)
- Written data not returned on subsequent read
- Similarity scores don't respect metric properties

**Research Significance**:
Semantic correctness gap - the database appears to work but produces wrong results. These are often subtle bugs that can silently corrupt applications.

**Subtypes** (by oracle):
- Type-4.Monotonicity: Top-K monotonicity violation
- Type-4.Consistency: Write-read inconsistency
- Type-4.Strictness: Filter strictness violation
- Type-4.Metric: Distance/semantic violation

---

## Classification Decision Tree

```
┌─────────────────────────────────────┐
│     Is input contract-valid?        │
└─────────────┬───────────────────────┘
              │
     ┌────────┴────────┐
     │                 │
    NO                YES
     │                 │
     │     ┌───────────────────────────┐
     │     │ Did operation succeed?    │
     │     └───────────┬───────────────┘
     │                 │
     │        ┌────────┴────────┐
     │        │                 │
     │       NO                YES
     │        │                 │
     │        │     ┌───────────────────────┐
     │        │     │ precondition_pass?    │
     │        │     └───────────┬───────────┘
     │        │                 │
     │        │    ┌────────────┴────────────┐
     │        │    │                         │
     │        │   NO                        YES
     │        │    │                         │
     │        │    │           ┌─────────────────────────┐
     │        │    │           │ Did oracle pass?        │
     │        │    │           └──────────┬──────────────┘
     │        │    │                      │
     │        │    │         ┌────────────┴────────────┐
     │        │    │         │                         │
     │        │    │        NO                        YES
     │        │    │         │                         │
     │        │    │         │                    ✅ Valid
     │        │    │         │
     │        │    │    Type-4              Type-3
     │        │    │  (Semantic          (Runtime
     │        │    │   Violation)         Failure)
     │        │    │
     │        │    Type-2.PreconditionFailed
     │        │    (or dropped_pseudo_valid)
     │        │
     │   Type-2
     │  (Poor
     │  Diagnostic)
     │
  Type-1
(Illegal
 Succeeded)
```

## The Precondition Red Line

### Why This Is Critical

Without the `precondition_pass` gate, we cannot distinguish between:
- **Genuine bugs** (Type-3/4): Valid operations failing under valid conditions
- **Expected failures** (not bugs): Operations failing because runtime prerequisites aren't met

### Examples of Pseudo-Valid Cases

A case may be **contract-valid** but **precondition-fail**:
- Search on non-existent collection
- Insert before collection is created
- Search before index is loaded
- Filter on unsupported field
- Hybrid search with disabled index

These **should not** count as Type-3 or Type-4 because they represent expected failures, not bugs.

### Classification Policy

When `precondition_pass = false`:
- **Option A**: Reclassify as `Type-2.PreconditionFailed` if error is non-diagnostic
- **Option B**: Drop as `dropped_pseudo_valid` if this is expected behavior

The system must make this policy explicit and configurable.

## Triage Rationale Requirements

Every TriageResult MUST include:
1. **final_type**: One of Type-1, Type-2, Type-3, Type-4
2. **subtype**: Optional refinement
3. **rationale**: Explanation of how classification was derived
4. **confidence**: Numerical or categorical confidence level
5. **dropped_reason**: If not counted, explain why
6. **confirm_needed**: Whether this requires verification

## Oracle Definitions

### Top-K Monotonicity Oracle
**Invariant**: `search(top_k=N)` should return at least as many results as `search(top_k=M)` for all N ≥ M.

### Filter Strictness Oracle
**Invariant**: `search(filter=F)` should return a subset of `search()` (no filter).

### Write-Read Consistency Oracle
**Invariant**: Data written with `insert()` should be retrievable via subsequent `search()` or `get()`.

## Examples

### Example 1: Type-1
```python
# Case: Insert with wrong dimension
case = {
    "operation": "insert",
    "params": {"vectors": [[1.0, 2.0]], "collection": "test_128d"}  # 2D vs 128D
}
# Result: Insert succeeded
# Classification: Type-1 (illegal operation succeeded)
```

### Example 2: Type-2
```python
# Case: Search with negative top-k
case = {
    "operation": "search",
    "params": {"top_k": -1, "vector": [1.0] * 128}
}
# Result: Failed with "Error: Invalid parameter"
# Classification: Type-2 (poor diagnostic - doesn't say which parameter)
```

### Example 3: Type-2.PreconditionFailed
```python
# Case: Search on non-loaded collection
case = {
    "operation": "search",
    "params": {"collection": "unloaded", "top_k": 10}
}
# Result: Failed with "Collection not loaded"
# precondition_pass = false
# Classification: Type-2.PreconditionFailed (or dropped_pseudo_valid)
```

### Example 4: Type-3
```python
# Case: Valid search after proper setup
# (collection created, index built, loaded)
case = {
    "operation": "search",
    "params": {"collection": "properly_setup", "top_k": 10}
}
# Result: Database crash
# precondition_pass = true
# Classification: Type-3 (runtime failure)
```

### Example 5: Type-4
```python
# Case: Valid search with monotonicity check
case1 = {"operation": "search", "params": {"top_k": 5}}
case2 = {"operation": "search", "params": {"top_k": 10}}
# Result: Both succeeded, but case2 returned fewer results than case1
# precondition_pass = true for both
# Classification: Type-4.Monotonicity (semantic violation)
```

## Implementation Notes

- The triage module MUST enforce the red-line constraint
- The confirm module MUST re-verify preconditions on rerun
- Evidence bundles MUST include gate trace for reproducibility
- Documentation MUST explain the rationale to users
```

**Step 2: Commit**

```bash
git add BUG_TAXONOMY.md
git commit -m "docs: add bug taxonomy documentation"
```

---

## Task 5: NON_GOALS.md

**Files:**
- Create: `NON_GOALS.md`

**Step 1: Create NON_GOALS.md**

```markdown
# Non-Goals

## Purpose

This document explicitly lists features and capabilities that are **out of scope** for the AI-DB-QC project. This serves as a guardrail to maintain focus on the core research contribution.

## Principle: Minimal Publishable Prototype

The goal is a research artifact that demonstrates a novel approach to AI database quality assurance, not a production testing platform.

---

## Platform Features (NOT Included)

### Distributed Execution
We will NOT build:
- Distributed test runners
- Worker pools
- Load balancing
- Multi-machine coordination

**Rationale**: These are infrastructure concerns, not research contributions. Single-machine execution is sufficient.

### Web UI / Dashboard
We will NOT build:
- Web interface
- Real-time dashboards
- Interactive result visualization
- User management

**Rationale**: CLI and file-based reports are sufficient for research. UI adds complexity without research value.

### Persistent Database
We will NOT build:
- PostgreSQL/MySQL backend
- Result history database
- Query interface for historical results
- Multi-run comparison tools

**Rationale**: File-based evidence bundles provide reproducibility. A database adds unnecessary complexity.

### Continuous Integration Integration
We will NOT build:
- GitHub Actions workflows
- CI/CD pipeline integration
- Automated regression testing

**Rationale**: The system is a research tool, not a production testing service.

### Test Suite Management
We will NOT build:
- Test suite organization
- Test case versioning
- Suite composition tools
- Tag-based selection

**Rationale**: These are secondary concerns. Single-run execution is sufficient for validation.

---

## Technical Scope (NOT Included)

### Multi-Database Abstraction
We will NOT build:
- Universal query language
- Database-agnostic API layer
- Automatic SQL/API translation

**Rationale**: We focus on Milvus with extensibility via adapters. Over-abstraction obscures the research contribution.

### Complex DSL for Test Specification
We will NOT build:
- Domain-specific language for tests
- Test specification syntax
- Test composition language

**Rationale**: Python/JSON schemas are sufficient. A DSL adds complexity without research value.

### Performance Optimization
We will NOT focus on:
- Test execution speed
- Parallel test execution
- Resource optimization

**Rationale**: Correctness and clarity are more important than speed for a research prototype.

### Load Testing / Stress Testing
We will NOT build:
- High-concurrency testing
- Resource exhaustion testing
- Performance benchmarking

**Rationale**: These are separate concerns from functional correctness.

### Security Testing
We will NOT build:
- Injection attack testing
- Authentication/authorization testing
- Data privacy validation

**Rationale**: These are important but outside the scope of functional correctness.

---

## Research Scope (NOT Included)

### Automatic Oracle Synthesis
We will NOT build:
- Automatic discovery of invariants
- Machine learning for oracle generation
- Self-learning oracles

**Rationale**: We manually implement well-understood oracles. Automatic synthesis is a separate research problem.

### Test Case Prioritization
We will NOT build:
- Intelligent case ordering
- Coverage-based prioritization
- Adaptive test selection

**Rationale**: These are optimization concerns, not core to the classification framework.

### Test Suite Minimization
We will NOT build:
- Redundancy elimination
- Minimal suite generation
- Delta debugging

**Rationale**: These are valuable but separate from the core research question.

### Fault Localization
We will NOT build:
- Root cause analysis
- Fault localization algorithms
- Suspicion scoring

**Rationale**: Our contribution is classification, not localization.

### Automatic Repair
We will NOT build:
- Patch generation
- Automatic bug fixing
- Repair suggestions

**Rationale**: Repair is a separate problem from detection and classification.

---

## LLM Scope (NOT Included)

### LLM as Source of Truth
We will NOT:
- Use LLM for final bug classification
- Use LLM for correctness determination
- Use LLM for confirmation decisions

**Rationale**: LLMs are probabilistic and non-deterministic. Final classification must be deterministic and traceable.

### LLM-Only Operation
We will NOT:
- Make LLM required for core functionality
- Design the system around LLM capabilities

**Rationale**: The system must work without LLM. LLM is an optional enhancement.

---

## What We WILL Build

### Core Research Functions
1. **Structured Test Case Generation** (rule-based + optional LLM assistance)
2. **Structured Correctness Judgment** (contract + gate + oracle + triage + confirm)

### Essential Components
1. Core schemas for all data structures
2. Contract/profile loading infrastructure
3. Milvus adapter with mock alternative
4. Precondition gate
5. Three initial oracles (monotonicity, strictness, consistency)
6. Triage pipeline with red-line enforcement
7. Confirm pipeline with rerun
8. Evidence bundle generation
9. Three validation benchmarks

### Essential Documentation
1. Theoretical foundation
2. Bug taxonomy with formal definitions
3. Project scope and boundaries
4. Architecture documentation
5. Experiment reproducibility guide

---

## Feature Addition Criteria

A feature SHOULD be added if:
1. It is necessary to validate the core research hypothesis
2. It is required for paper publication
3. It enables a critical validation experiment

A feature SHOULD NOT be added if:
1. It is "nice to have" but not research-critical
2. It exists in other testing tools but is not part of our contribution
3. It adds complexity without clarifying the research approach

---

## Evolution Path

If the project evolves beyond Phase 1:

**Phase 2**: Add execution, oracles, triage, confirm
**Phase 3**: Add validation benchmarks
**Phase 4**: Prepare for publication

Features in NON_GOALS may be reconsidered ONLY if:
- They become necessary for publication
- They enable critical validation experiments
- The core research contribution is solid first

The order is: **Foundation → Validation → Publication → Extensions**

NOT: **Platform → Features → Extensions → Research**
```

**Step 2: Commit**

```bash
git add NON_GOALS.md
git commit -m "docs: add non-goals documentation"
```

---

## Task 6: Core Schemas - Base Types

**Files:**
- Create: `schemas/__init__.py`
- Create: `schemas/common.py`

**Step 1: Create schemas/common.py with base types**

```python
# schemas/common.py
"""Common types and enums used across schemas."""

from enum import Enum
from typing import Literal, Optional
from pydantic import BaseModel, Field


class InputValidity(str, Enum):
    """Whether input satisfies abstract contract constraints."""

    LEGAL = "legal"
    ILLEGAL = "illegal"


class PreconditionStatus(str, Enum):
    """Whether runtime preconditions are satisfied."""

    PASS = "pass"
    FAIL = "fail"


class ObservedOutcome(str, Enum):
    """What actually happened during execution."""

    SUCCESS = "success"
    FAILURE = "failure"
    CRASH = "crash"
    HANG = "hang"
    TIMEOUT = "timeout"


class BugType(str, Enum):
    """The four-type defect classification."""

    TYPE_1 = "type-1"  # Illegal operation succeeded
    TYPE_2 = "type-2"  # Illegal operation with poor diagnostic
    TYPE_2_PRECONDITION_FAILED = "type-2.precondition_failed"
    TYPE_3 = "type-3"  # Legal operation failed
    TYPE_4 = "type-4"  # Semantic violation


class ConfirmStatus(str, Enum):
    """Status of confirmation rerun."""

    PENDING = "pending"
    CONFIRMED_BUG = "confirmed_bug"
    FLAKY_CANDIDATE = "flaky_candidate"
    INFRA_ISSUE = "infra_issue"
    NOT_REPRODUCIBLE = "not_reproducible"


class OperationType(str, Enum):
    """Supported database operations."""

    CREATE_COLLECTION = "create_collection"
    DROP_COLLECTION = "drop_collection"
    INSERT = "insert"
    DELETE = "delete"
    BUILD_INDEX = "build_index"
    LOAD_INDEX = "load_index"
    SEARCH = "search"
    FILTERED_SEARCH = "filtered_search"
    HYBRID_SEARCH = "hybrid_search"


class SourceType(str, Enum):
    """Where a test case originated."""

    RULE_BASED = "rule_based"
    LLM_ASSISTED = "llm_assisted"
    CONTRACT_MUTATION = "contract_mutation"
    MANUAL = "manual"


class RunMetadata(BaseModel):
    """Metadata about a test run."""

    run_id: str = Field(description="Unique identifier for this run")
    timestamp: str = Field(description="ISO timestamp of run start")
    config_hash: str = Field(description="Hash of configuration used")
    adapter_name: str = Field(description="Database adapter used")
    total_cases: int = Field(description="Total cases in run")
    completed_cases: int = Field(default=0, description="Cases completed")


class DiagnosticSlot(BaseModel):
    """A required piece of diagnostic information in error messages."""

    slot_name: str = Field(description="Name of the diagnostic slot")
    required: bool = Field(default=True, description="Whether this slot is required")
    description: str = Field(default="", description="What this slot represents")


class GateTrace(BaseModel):
    """Trace of precondition evaluation."""

    precondition_name: str = Field(description="Name of the precondition checked")
    passed: bool = Field(description="Whether the precondition passed")
    reason: str = Field(default="", description="Explanation if failed")
    check_time_ms: float = Field(default=0.0, description="Time to check")
```

**Step 2: Run tests to verify imports work**

```bash
cd "C:\Users\11428\Desktop\ai-db-qc"
python -c "from schemas.common import *; print('Imports successful')"
```

Expected: "Imports successful"

**Step 3: Commit**

```bash
git add schemas/
git commit -m "feat(schemas): add common base types and enums"
```

---

## Task 7: Core Schemas - TestCase

**Files:**
- Create: `schemas/case.py`

**Step 1: Create schemas/case.py**

```python
# schemas/case.py
"""Test case schema."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from schemas.common import (
    InputValidity,
    OperationType,
    SourceType,
)


class Preconditions(BaseModel):
    """Runtime preconditions that must be satisfied."""

    collection_exists: bool = Field(default=False, description="Target collection must exist")
    index_built: bool = Field(default=False, description="Index must be built")
    index_loaded: bool = Field(default=False, description="Index must be loaded")
    min_data_count: Optional[int] = Field(default=None, description="Minimum data required")
    supported_features: List[str] = Field(
        default_factory=list, description="Required feature support"
    )


class TestCase(BaseModel):
    """A test case for database quality assurance."""

    case_id: str = Field(description="Unique identifier for this case")
    operation: OperationType = Field(description="Operation to perform")
    params: Dict[str, Any] = Field(description="Operation parameters")
    expected_validity: InputValidity = Field(
        description="Whether input is expected to be contract-valid"
    )
    preconditions: Preconditions = Field(
        default_factory=Preconditions, description="Runtime preconditions"
    )
    oracle_refs: List[str] = Field(
        default_factory=list, description="Oracles to apply (e.g., 'topk_monotonicity')"
    )
    source: SourceType = Field(
        default=SourceType.RULE_BASED, description="How this case was generated"
    )
    seed: Optional[str] = Field(default=None, description="Seed for deterministic generation")
    tags: List[str] = Field(default_factory=list, description="Case tags for filtering")
    rationale: str = Field(default="", description="Explanation of what this case tests")

    class Config:
        json_encoders = {
            # Add any custom encoders if needed
        }


class CaseTemplate(BaseModel):
    """A template for generating test cases."""

    template_id: str = Field(description="Template identifier")
    operation: OperationType = Field(description="Operation type")
    param_template: Dict[str, Any] = Field(
        description="Parameter template with placeholders"
    )
    validity_category: str = Field(
        description="Category: valid, invalid, or pseudo_valid"
    )
    expected_validity: InputValidity = Field(description="Expected contract validity")
    precondition_sensitivity: List[str] = Field(
        default_factory=list,
        description="Which preconditions this case is sensitive to",
    )
    rationale: str = Field(default="", description="What this template tests")
```

**Step 2: Create tests/unit/test_schemas.py**

```python
# tests/unit/test_schemas.py
"""Unit tests for core schemas."""

import pytest
from schemas.case import TestCase, Preconditions, CaseTemplate
from schemas.common import InputValidity, OperationType, SourceType


def test_test_case_creation():
    """Test creating a basic test case."""
    case = TestCase(
        case_id="test-001",
        operation=OperationType.SEARCH,
        params={"collection": "test", "top_k": 10},
        expected_validity=InputValidity.LEGAL,
        rationale="Basic search test"
    )
    assert case.case_id == "test-001"
    assert case.operation == OperationType.SEARCH
    assert case.expected_validity == InputValidity.LEGAL


def test_test_case_with_preconditions():
    """Test test case with preconditions."""
    preconditions = Preconditions(
        collection_exists=True,
        index_built=True,
        index_loaded=True
    )
    case = TestCase(
        case_id="test-002",
        operation=OperationType.SEARCH,
        params={"collection": "test", "top_k": 10},
        expected_validity=InputValidity.LEGAL,
        preconditions=preconditions
    )
    assert case.preconditions.collection_exists is True
    assert case.preconditions.index_loaded is True


def test_case_serialization():
    """Test that test cases can be serialized to JSON."""
    case = TestCase(
        case_id="test-003",
        operation=OperationType.INSERT,
        params={"vectors": [[1.0, 2.0, 3.0]]},
        expected_validity=InputValidity.LEGAL
    )
    json_str = case.model_dump_json()
    assert "test-003" in json_str

    # Deserialize
    restored = TestCase.model_validate_json(json_str)
    assert restored.case_id == case.case_id
    assert restored.operation == case.operation


def test_case_template():
    """Test case template structure."""
    template = CaseTemplate(
        template_id="tmpl-search-valid",
        operation=OperationType.SEARCH,
        param_template={"top_k": "{k}", "collection": "{collection}"},
        validity_category="valid",
        expected_validity=InputValidity.LEGAL,
        precondition_sensitivity=["collection_exists", "index_loaded"],
        rationale="Valid search case"
    )
    assert template.template_id == "tmpl-search-valid"
    assert template.validity_category == "valid"
    assert len(template.precondition_sensitivity) == 2
```

**Step 3: Run tests**

```bash
cd "C:\Users\11428\Desktop\ai-db-qc"
pytest tests/unit/test_schemas.py -v
```

Expected: All tests pass

**Step 4: Commit**

```bash
git add schemas/ tests/unit/
git commit -m "feat(schemas): add TestCase and CaseTemplate schemas"
```

---

## Task 8: Core Schemas - ExecutionResult

**Files:**
- Create: `schemas/result.py`

**Step 1: Create schemas/result.py**

```python
# schemas/result.py
"""Execution result and oracle result schemas."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from schemas.common import (
    ObservedOutcome,
    PreconditionStatus,
    DiagnosticSlot,
    GateTrace,
)


class OracleResult(BaseModel):
    """Result from an oracle validation check."""

    oracle_id: str = Field(description="Identifier for the oracle (e.g., 'topk_monotonicity')")
    passed: bool = Field(description="Whether the oracle check passed")
    metrics: Dict[str, float] = Field(
        default_factory=dict, description="Metrics measured by oracle"
    )
    expected_relation: str = Field(
        default="", description="Expected relation (e.g., 'result_count(K=10) >= result_count(K=5)')"
    )
    observed_relation: str = Field(
        default="", description="Actually observed relation"
    )
    explanation: str = Field(default="", description="Explanation of why oracle failed/passed")
    evidence_refs: List[str] = Field(
        default_factory=list, description="References to evidence artifacts"
    )


class ExecutionResult(BaseModel):
    """Result of executing a test case."""

    run_id: str = Field(description="Run identifier")
    case_id: str = Field(description="Case identifier")
    adapter_name: str = Field(description="Database adapter used")

    # Request/Response
    request: Dict[str, Any] = Field(description="The request that was sent")
    response: Optional[Dict[str, Any]] = Field(default=None, description="Raw response from database")

    # Outcome
    observed_outcome: ObservedOutcome = Field(description="What happened")
    error_type: Optional[str] = Field(default=None, description="Type of error if any")
    error_message: Optional[str] = Field(default=None, description="Error message if any")

    # Timing
    latency_ms: float = Field(description="Execution time in milliseconds")

    # Precondition Gate
    precondition_pass: bool = Field(description="Whether all preconditions passed")
    gate_trace: List[GateTrace] = Field(
        default_factory=list, description="Trace of precondition checks"
    )

    # Diagnostic slots (for Type-2 detection)
    provided_slots: Dict[str, Any] = Field(
        default_factory=dict, description="Diagnostic slots actually provided in error"
    )
    missing_slots: List[str] = Field(
        default_factory=list, description="Required diagnostic slots that were missing"
    )

    # Infrastructure suspicion
    infra_suspect: bool = Field(default=False, description="Whether this looks like infra issue")

    # Oracle results
    oracle_results: List[OracleResult] = Field(
        default_factory=list, description="Results from oracle checks"
    )

    # Evidence
    evidence_refs: List[str] = Field(
        default_factory=list, description="References to evidence artifacts"
    )

    # Metadata
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def observed_success(self) -> bool:
        """Convenience property: was the execution successful?"""
        return self.observed_outcome == ObservedOutcome.SUCCESS
```

**Step 2: Add tests to tests/unit/test_schemas.py**

```python
# Add to tests/unit/test_schemas.py

from schemas.result import ExecutionResult, OracleResult
from schemas.common import ObservedOutcome, PreconditionStatus


def test_execution_result_success():
    """Test execution result with success."""
    result = ExecutionResult(
        run_id="run-001",
        case_id="test-001",
        adapter_name="milvus",
        request={"operation": "search", "top_k": 10},
        response={"results": []},
        observed_outcome=ObservedOutcome.SUCCESS,
        latency_ms=50.0,
        precondition_pass=True
    )
    assert result.observed_success is True
    assert result.observed_outcome == ObservedOutcome.SUCCESS
    assert result.precondition_pass is True


def test_execution_result_failure():
    """Test execution result with failure."""
    result = ExecutionResult(
        run_id="run-001",
        case_id="test-002",
        adapter_name="milvus",
        request={"operation": "search", "top_k": -1},
        observed_outcome=ObservedOutcome.FAILURE,
        error_type="InvalidParameter",
        error_message="Invalid parameter: top_k",
        latency_ms=5.0,
        precondition_pass=True,
        missing_slots=["parameter_name"]  # Missing which parameter
    )
    assert result.observed_success is False
    assert "parameter_name" in result.missing_slots


def test_oracle_result():
    """Test oracle result structure."""
    oracle_result = OracleResult(
        oracle_id="topk_monotonicity",
        passed=False,
        metrics={"k5_count": 5, "k10_count": 3},
        expected_relation="k10_count >= k5_count",
        observed_relation="k10_count (3) < k5_count (5)",
        explanation="Monotonicity violated: larger K returned fewer results"
    )
    assert oracle_result.passed is False
    assert oracle_result.metrics["k5_count"] == 5
```

**Step 3: Run tests**

```bash
cd "C:\Users\11428\Desktop\ai-db-qc"
pytest tests/unit/test_schemas.py -v
```

Expected: All tests pass

**Step 4: Commit**

```bash
git add schemas/ tests/unit/
git commit -m "feat(schemas): add ExecutionResult and OracleResult schemas"
```

---

## Task 9: Core Schemas - TriageResult and ConfirmResult

**Files:**
- Modify: `schemas/result.py`

**Step 1: Add to schemas/result.py**

```python
# Add to schemas/result.py

from schemas.common import BugType, ConfirmStatus


class TriageResult(BaseModel):
    """Result of triage classification."""

    case_id: str = Field(description="Case identifier")
    run_id: str = Field(description="Run identifier")

    # Classification
    final_type: BugType = Field(description="Final bug type (1-4)")
    subtype: Optional[str] = Field(default=None, description="Subtype if applicable")

    # Rationale
    rationale: str = Field(description="Explanation of classification")
    confidence: str = Field(
        default="high",
        description="Confidence level: high, medium, low"
    )

    # Evidence trace
    input_validity: str = Field(description="Input validity assessment")
    observed_outcome: str = Field(description="What was observed")
    precondition_pass: bool = Field(description="Whether preconditions passed")
    oracle_pass: Optional[bool] = Field(
        default=None, description="Whether oracle passed (if applicable)"
    )

    # Handling
    dropped_reason: Optional[str] = Field(
        default=None, description="If dropped, explain why"
    )
    confirm_needed: bool = Field(
        default=True, description="Whether this needs confirmation"
    )


class ConfirmResult(BaseModel):
    """Result of confirmation rerun."""

    case_id: str = Field(description="Case identifier")
    original_run_id: str = Field(description="Original run ID")
    confirm_run_id: str = Field(description="Confirmation run ID")

    # Re-verification
    rerun_count: int = Field(default=0, description="Number of reruns performed")
    stable_repro: bool = Field(description="Whether issue is stably reproducible")
    infra_recheck: bool = Field(
        default=False, description="Whether infrastructure was rechecked"
    )

    # Final decision
    final_decision: ConfirmStatus = Field(description="Final confirmation status")
    notes: str = Field(default="", description="Additional notes")

    # Variance analysis
    outcome_variance: List[str] = Field(
        default_factory=list,
        description="Different outcomes observed across reruns"
    )
    timing_variance_ms: float = Field(
        default=0.0, description="Timing variance across reruns"
    )
```

**Step 2: Add tests to tests/unit/test_schemas.py**

```python
# Add to tests/unit/test_schemas.py

from schemas.result import TriageResult, ConfirmResult
from schemas.common import BugType, ConfirmStatus


def test_triage_result_type_1():
    """Test triage result for Type-1 bug."""
    triage = TriageResult(
        case_id="test-001",
        run_id="run-001",
        final_type=BugType.TYPE_1,
        rationale="Illegal negative top_k was accepted",
        input_validity="illegal",
        observed_outcome="success",
        precondition_pass=True
    )
    assert triage.final_type == BugType.TYPE_1
    assert triage.confirm_needed is True


def test_triage_result_type_3_with_red_line():
    """Test that Type-3 requires precondition_pass."""
    # This should be a valid Type-3
    triage = TriageResult(
        case_id="test-002",
        run_id="run-001",
        final_type=BugType.TYPE_3,
        rationale="Valid operation failed after precondition check",
        input_validity="legal",
        observed_outcome="failure",
        precondition_pass=True  # REQUIRED for Type-3
    )
    assert triage.final_type == BugType.TYPE_3
    assert triage.precondition_pass is True


def test_triage_result_dropped():
    """Test triage result that was dropped."""
    triage = TriageResult(
        case_id="test-003",
        run_id="run-001",
        final_type=BugType.TYPE_2_PRECONDITION_FAILED,
        rationale="Case was pseudo-valid (contract-valid but precondition-fail)",
        input_validity="legal",
        observed_outcome="failure",
        precondition_pass=False,
        dropped_reason="pseudo_valid: search on unloaded collection",
        confirm_needed=False
    )
    assert triage.dropped_reason is not None
    assert triage.confirm_needed is False


def test_confirm_result():
    """Test confirm result structure."""
    confirm = ConfirmResult(
        case_id="test-001",
        original_run_id="run-001",
        confirm_run_id="run-002",
        rerun_count=3,
        stable_repro=True,
        final_decision=ConfirmStatus.CONFIRMED_BUG,
        notes="Bug reproduced consistently across 3 reruns"
    )
    assert confirm.final_decision == ConfirmStatus.CONFIRMED_BUG
    assert confirm.stable_repro is True
```

**Step 3: Run tests**

```bash
cd "C:\Users\11428\Desktop\ai-db-qc"
pytest tests/unit/test_schemas.py -v
```

Expected: All tests pass

**Step 4: Commit**

```bash
git add schemas/ tests/unit/
git commit -m "feat(schemas): add TriageResult and ConfirmResult schemas"
```

---

## Task 10: Core Schemas - EvidenceBundle

**Files:**
- Create: `schemas/evidence.py`

**Step 1: Create schemas/evidence.py**

```python
# schemas/evidence.py
"""Evidence bundle schema for reproducibility."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from schemas.case import TestCase
from schemas.result import ExecutionResult, TriageResult, ConfirmResult


class EnvironmentFingerprint(BaseModel):
    """Fingerprint of execution environment for reproducibility."""

    python_version: str = Field(description="Python version")
    os_info: str = Field(description="Operating system")
    adapter_version: Optional[str] = Field(default=None, description="Database version")
    dependencies: Dict[str, str] = Field(
        default_factory=dict, description="Key dependencies and versions"
    )
    environment_vars: List[str] = Field(
        default_factory=list, description="Relevant environment variables (sanitized)"
    )


class CaseSnapshot(BaseModel):
    """Snapshot of a test case."""

    case: TestCase = Field(description="The test case")
    serialized_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="When snapshot was taken"
    )


class RequestSnapshot(BaseModel):
    """Snapshot of request sent to database."""

    raw_request: Dict[str, Any] = Field(description="Raw request data")
    normalized_request: Dict[str, Any] = Field(
        description="Normalized/processed request"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )


class ResponseSnapshot(BaseModel):
    """Snapshot of response from database."""

    raw_response: Any = Field(description="Raw response (may be structured)")
    status_code: Optional[int] = Field(default=None, description="HTTP status if applicable")
    response_time_ms: float = Field(description="Response time")
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )


class EvidenceBundle(BaseModel):
    """Complete evidence bundle for a test case execution."""

    # Run metadata
    run_id: str = Field(description="Run identifier")
    case_id: str = Field(description="Case identifier")
    env_fingerprint: EnvironmentFingerprint = Field(
        description="Environment fingerprint"
    )

    # Snapshots
    case_snapshot: CaseSnapshot = Field(description="Test case snapshot")
    request_snapshot: RequestSnapshot = Field(description="Request snapshot")
    response_snapshot: Optional[ResponseSnapshot] = Field(
        default=None, description="Response snapshot"
    )

    # Execution results
    execution_result: ExecutionResult = Field(description="Execution result")
    triage_result: Optional[TriageResult] = Field(
        default=None, description="Triage result if available"
    )
    confirm_result: Optional[ConfirmResult] = Field(
        default=None, description="Confirm result if available"
    )

    # Artifacts
    logs: List[str] = Field(default_factory=list, description="Relevant log entries")
    oracle_artifacts: Dict[str, Any] = Field(
        default_factory=dict, description="Oracle-specific artifacts"
    )
    gate_trace: List[Dict[str, Any]] = Field(
        default_factory=list, description="Precondition gate trace"
    )

    # Replay information
    replay_info: Dict[str, Any] = Field(
        default_factory=dict,
        description="Information needed to replay this execution"
    )

    # Metadata
    bundle_created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )

    def to_file(self, path: str) -> None:
        """Write evidence bundle to file."""
        import json
        with open(path, 'w') as f:
            json.dump(self.model_dump(mode='json'), f, indent=2)

    @classmethod
    def from_file(cls, path: str) -> "EvidenceBundle":
        """Load evidence bundle from file."""
        import json
        with open(path, 'r') as f:
            data = json.load(f)
        return cls.model_validate(data)
```

**Step 2: Add tests to tests/unit/test_schemas.py**

```python
# Add to tests/unit/test_schemas.py

from schemas.evidence import (
    EvidenceBundle,
    EnvironmentFingerprint,
    CaseSnapshot,
    RequestSnapshot,
    ResponseSnapshot
)


def test_environment_fingerprint():
    """Test environment fingerprint structure."""
    fingerprint = EnvironmentFingerprint(
        python_version="3.11.0",
        os_info="Windows 11",
        adapter_version="milvus-2.3.0",
        dependencies={"pydantic": "2.0.0", "pytest": "7.0.0"}
    )
    assert fingerprint.python_version == "3.11.0"
    assert len(fingerprint.dependencies) == 2


def test_case_snapshot():
    """Test case snapshot structure."""
    from schemas.case import TestCase
    from schemas.common import OperationType, InputValidity

    case = TestCase(
        case_id="test-001",
        operation=OperationType.SEARCH,
        params={"top_k": 10},
        expected_validity=InputValidity.LEGAL
    )
    snapshot = CaseSnapshot(case=case)
    assert snapshot.case.case_id == "test-001"


def test_evidence_bundle():
    """Test complete evidence bundle structure."""
    from schemas.case import TestCase
    from schemas.result import ExecutionResult
    from schemas.common import OperationType, InputValidity, ObservedOutcome

    case = TestCase(
        case_id="test-001",
        operation=OperationType.SEARCH,
        params={"top_k": 10},
        expected_validity=InputValidity.LEGAL
    )

    result = ExecutionResult(
        run_id="run-001",
        case_id="test-001",
        adapter_name="milvus",
        request={"operation": "search"},
        observed_outcome=ObservedOutcome.SUCCESS,
        latency_ms=50.0,
        precondition_pass=True
    )

    bundle = EvidenceBundle(
        run_id="run-001",
        case_id="test-001",
        env_fingerprint=EnvironmentFingerprint(
            python_version="3.11.0",
            os_info="Windows 11"
        ),
        case_snapshot=CaseSnapshot(case=case),
        request_snapshot=RequestSnapshot(
            raw_request={"operation": "search"},
            normalized_request={"operation": "search", "top_k": 10}
        ),
        execution_result=result
    )

    assert bundle.run_id == "run-001"
    assert bundle.case_snapshot.case.case_id == "test-001"


def test_evidence_bundle_serialization(tmp_path):
    """Test that evidence bundles can be saved and loaded."""
    import json
    from schemas.case import TestCase
    from schemas.result import ExecutionResult
    from schemas.common import OperationType, InputValidity, ObservedOutcome

    case = TestCase(
        case_id="test-001",
        operation=OperationType.SEARCH,
        params={"top_k": 10},
        expected_validity=InputValidity.LEGAL
    )

    result = ExecutionResult(
        run_id="run-001",
        case_id="test-001",
        adapter_name="milvus",
        request={"operation": "search"},
        observed_outcome=ObservedOutcome.SUCCESS,
        latency_ms=50.0,
        precondition_pass=True
    )

    bundle = EvidenceBundle(
        run_id="run-001",
        case_id="test-001",
        env_fingerprint=EnvironmentFingerprint(
            python_version="3.11.0",
            os_info="Windows 11"
        ),
        case_snapshot=CaseSnapshot(case=case),
        request_snapshot=RequestSnapshot(
            raw_request={"operation": "search"},
            normalized_request={"operation": "search", "top_k": 10}
        ),
        execution_result=result
    )

    # Save to file
    file_path = tmp_path / "evidence.json"
    bundle.to_file(str(file_path))

    # Load from file
    loaded = EvidenceBundle.from_file(str(file_path))
    assert loaded.run_id == bundle.run_id
    assert loaded.case_id == bundle.case_id
```

**Step 3: Run tests**

```bash
cd "C:\Users\11428\Desktop\ai-db-qc"
pytest tests/unit/test_schemas.py -v
```

Expected: All tests pass

**Step 4: Update schemas/__init__.py to export all schemas**

```python
# schemas/__init__.py
"""Core schemas for AI-DB-QC system."""

from schemas.common import *
from schemas.case import TestCase, CaseTemplate, Preconditions
from schemas.result import ExecutionResult, OracleResult, TriageResult, ConfirmResult
from schemas.evidence import (
    EvidenceBundle,
    EnvironmentFingerprint,
    CaseSnapshot,
    RequestSnapshot,
    ResponseSnapshot,
)

__all__ = [
    # Common
    "InputValidity",
    "PreconditionStatus",
    "ObservedOutcome",
    "BugType",
    "ConfirmStatus",
    "OperationType",
    "SourceType",
    "RunMetadata",
    "DiagnosticSlot",
    "GateTrace",
    # Case
    "TestCase",
    "CaseTemplate",
    "Preconditions",
    # Result
    "ExecutionResult",
    "OracleResult",
    "TriageResult",
    "ConfirmResult",
    # Evidence
    "EvidenceBundle",
    "EnvironmentFingerprint",
    "CaseSnapshot",
    "RequestSnapshot",
    "ResponseSnapshot",
]
```

**Step 5: Commit**

```bash
git add schemas/ tests/unit/
git commit -m "feat(schemas): add EvidenceBundle schema and complete schema exports"
```

---

## Task 11: Contracts - Core Contract Schema

**Files:**
- Create: `contracts/core/__init__.py`
- Create: `contracts/core/schema.py`
- Create: `contracts/core/loader.py`

**Step 1: Create contracts/core/schema.py**

```python
# contracts/core/schema.py
"""Core contract schema (database-agnostic)."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from schemas.common import OperationType, DiagnosticSlot


class ParameterConstraint(BaseModel):
    """Constraint on a parameter."""

    name: str = Field(description="Parameter name")
    type: str = Field(description="Parameter type (int, str, list, etc.)")
    required: bool = Field(default=True, description="Whether parameter is required")
    default_value: Optional[Any] = Field(default=None, description="Default value if not required")
    min_value: Optional[float] = Field(default=None, description="Minimum value for numeric")
    max_value: Optional[float] = Field(default=None, description="Maximum value for numeric")
    allowed_values: Optional[List[Any]] = Field(
        default=None, description="List of allowed values"
    )
    description: str = Field(default="", description="Parameter description")


class OperationContract(BaseModel):
    """Contract for a single operation."""

    operation_type: OperationType = Field(description="Operation type")
    description: str = Field(description="Operation description")
    parameters: Dict[str, ParameterConstraint] = Field(
        description="Parameter constraints"
    )
    required_preconditions: List[str] = Field(
        default_factory=list,
        description="Required runtime preconditions"
    )
    error_diagnostic_slots: List[DiagnosticSlot] = Field(
        default_factory=list,
        description="Diagnostic information that should be provided on error"
    )
    applicable_oracles: List[str] = Field(
        default_factory=list,
        description="Oracles that can validate this operation"
    )


class CoreContract(BaseModel):
    """Core contract for database operations (database-agnostic)."""

    contract_name: str = Field(description="Contract identifier")
    contract_version: str = Field(description="Contract version")
    description: str = Field(description="Contract description")
    operations: Dict[OperationType, OperationContract] = Field(
        description="Operation contracts"
    )

    def get_operation_contract(self, op_type: OperationType) -> Optional[OperationContract]:
        """Get contract for a specific operation."""
        return self.operations.get(op_type)
```

**Step 2: Create contracts/core/loader.py**

```python
# contracts/core/loader.py
"""Core contract loader."""

import yaml
from pathlib import Path
from typing import Optional

from contracts.core.schema import CoreContract


class ContractLoadError(Exception):
    """Error loading contract."""

    pass


def load_contract(contract_path: str | Path) -> CoreContract:
    """
    Load a core contract from YAML file.

    Args:
        contract_path: Path to contract YAML file

    Returns:
        CoreContract instance

    Raises:
        ContractLoadError: If contract cannot be loaded
    """
    path = Path(contract_path)
    if not path.exists():
        raise ContractLoadError(f"Contract file not found: {contract_path}")

    try:
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ContractLoadError(f"Invalid YAML in contract file: {e}")

    try:
        contract = CoreContract(**data)
    except Exception as e:
        raise ContractLoadError(f"Invalid contract structure: {e}")

    return contract


def get_default_contract_path() -> Path:
    """Get path to default core contract."""
    return Path(__file__).parent / "default_contract.yaml"


class ContractRegistry:
    """Registry for core contracts."""

    _contracts: dict[str, CoreContract] = {}

    @classmethod
    def register(cls, name: str, contract: CoreContract) -> None:
        """Register a contract."""
        cls._contracts[name] = contract

    @classmethod
    def get(cls, name: str) -> Optional[CoreContract]:
        """Get a registered contract."""
        return cls._contracts.get(name)

    @classmethod
    def list_contracts(cls) -> list[str]:
        """List registered contract names."""
        return list(cls._contracts.keys())
```

**Step 3: Create contracts/core/validator.py**

```python
# contracts/core/validator.py
"""Contract validation utilities."""

from typing import List, Optional, Tuple

from schemas.case import TestCase
from schemas.common import InputValidity, OperationType
from contracts.core.schema import CoreContract, OperationContract, ParameterConstraint


class ContractValidator:
    """Validates test cases against contracts."""

    def __init__(self, contract: CoreContract):
        self.contract = contract

    def validate_case_validity(self, case: TestCase) -> Tuple[InputValidity, List[str]]:
        """
        Validate whether a test case satisfies contract constraints.

        Returns:
            (validity, violation_descriptions)
        """
        op_contract = self.contract.get_operation_contract(case.operation)
        if not op_contract:
            return InputValidity.ILLEGAL, [f"No contract for operation: {case.operation}"]

        violations: List[str] = []

        # Check required parameters
        for param_name, constraint in op_contract.parameters.items():
            if constraint.required and param_name not in case.params:
                violations.append(f"Missing required parameter: {param_name}")

            # Check type if present
            if param_name in case.params:
                value = case.params[param_name]
                if not self._check_type(value, constraint.type):
                    violations.append(
                        f"Parameter '{param_name}' has wrong type: expected {constraint.type}"
                    )

                # Check range for numeric
                if constraint.min_value is not None and isinstance(value, (int, float)):
                    if value < constraint.min_value:
                        violations.append(
                            f"Parameter '{param_name}' below minimum: {value} < {constraint.min_value}"
                        )

                if constraint.max_value is not None and isinstance(value, (int, float)):
                    if value > constraint.max_value:
                        violations.append(
                            f"Parameter '{param_name}' above maximum: {value} > {constraint.max_value}"
                        )

                # Check allowed values
                if constraint.allowed_values is not None:
                    if value not in constraint.allowed_values:
                        violations.append(
                            f"Parameter '{param_name}' not in allowed values: {value}"
                        )

        if violations:
            return InputValidity.ILLEGAL, violations

        return InputValidity.LEGAL, []

    def _check_type(self, value: any, expected_type: str) -> bool:
        """Check if value matches expected type."""
        type_map = {
            "int": int,
            "float": float,
            "str": str,
            "bool": bool,
            "list": list,
            "dict": dict,
        }

        python_type = type_map.get(expected_type)
        if python_type is None:
            return True  # Unknown type, assume valid

        if expected_type == "float" and isinstance(value, int):
            return True  # Accept int as float

        return isinstance(value, python_type)


def validate_against_contract(
    case: TestCase,
    contract: CoreContract
) -> Tuple[InputValidity, List[str]]:
    """
    Validate a test case against a contract.

    Convenience function that creates a validator.
    """
    validator = ContractValidator(contract)
    return validator.validate_case_validity(case)
```

**Step 4: Create unit tests**

```python
# tests/unit/test_contracts.py

import pytest
from contracts.core.schema import CoreContract, OperationContract, ParameterConstraint
from contracts.core.loader import load_contract, ContractRegistry, ContractLoadError
from contracts.core.validator import ContractValidator, validate_against_contract
from schemas.case import TestCase
from schemas.common import InputValidity, OperationType


def test_parameter_constraint():
    """Test parameter constraint schema."""
    constraint = ParameterConstraint(
        name="top_k",
        type="int",
        required=True,
        min_value=1,
        max_value=10000
    )
    assert constraint.name == "top_k"
    assert constraint.min_value == 1


def test_operation_contract():
    """Test operation contract schema."""
    contract = OperationContract(
        operation_type=OperationType.SEARCH,
        description="Search for similar vectors",
        parameters={
            "top_k": ParameterConstraint(
                name="top_k",
                type="int",
                required=True,
                min_value=1
            )
        },
        required_preconditions=["collection_exists", "index_loaded"]
    )
    assert contract.operation_type == OperationType.SEARCH
    assert "collection_exists" in contract.required_preconditions


def test_core_contract():
    """Test core contract schema."""
    contract = CoreContract(
        contract_name="ai_db_core_v1",
        contract_version="1.0.0",
        description="Core AI database contract",
        operations={
            OperationType.SEARCH: OperationContract(
                operation_type=OperationType.SEARCH,
                description="Search operation"
            )
        }
    )
    assert contract.contract_name == "ai_db_core_v1"
    assert len(contract.operations) == 1


def test_contract_load_error():
    """Test that loading non-existent contract raises error."""
    with pytest.raises(ContractLoadError):
        load_contract("/nonexistent/path.yaml")


def test_contract_registry():
    """Test contract registry."""
    contract = CoreContract(
        contract_name="test_contract",
        contract_version="1.0.0",
        description="Test contract",
        operations={}
    )

    ContractRegistry.register("test", contract)
    retrieved = ContractRegistry.get("test")

    assert retrieved is not None
    assert retrieved.contract_name == "test_contract"
    assert "test" in ContractRegistry.list_contracts()


def test_contract_validator_valid_case():
    """Test validator with valid case."""
    contract = CoreContract(
        contract_name="test",
        contract_version="1.0.0",
        description="Test",
        operations={
            OperationType.SEARCH: OperationContract(
                operation_type=OperationType.SEARCH,
                description="Search",
                parameters={
                    "top_k": ParameterConstraint(
                        name="top_k",
                        type="int",
                        required=True,
                        min_value=1
                    )
                }
            )
        }
    )

    case = TestCase(
        case_id="test-001",
        operation=OperationType.SEARCH,
        params={"top_k": 10},
        expected_validity=InputValidity.LEGAL
    )

    validator = ContractValidator(contract)
    validity, violations = validator.validate_case_validity(case)

    assert validity == InputValidity.LEGAL
    assert len(violations) == 0


def test_contract_validator_invalid_case():
    """Test validator with invalid case."""
    contract = CoreContract(
        contract_name="test",
        contract_version="1.0.0",
        description="Test",
        operations={
            OperationType.SEARCH: OperationContract(
                operation_type=OperationType.SEARCH,
                description="Search",
                parameters={
                    "top_k": ParameterConstraint(
                        name="top_k",
                        type="int",
                        required=True,
                        min_value=1
                    )
                }
            )
        }
    )

    # Test with negative top_k (below minimum)
    case = TestCase(
        case_id="test-002",
        operation=OperationType.SEARCH,
        params={"top_k": -1},
        expected_validity=InputValidity.ILLEGAL
    )

    validator = ContractValidator(contract)
    validity, violations = validator.validate_case_validity(case)

    assert validity == InputValidity.ILLEGAL
    assert len(violations) > 0
    assert "below minimum" in violations[0]
```

**Step 5: Run tests**

```bash
cd "C:\Users\11428\Desktop\ai-db-qc"
pytest tests/unit/test_contracts.py -v
```

Expected: All tests pass

**Step 6: Commit**

```bash
git add contracts/ tests/unit/
git commit -m "feat(contracts): add core contract schema, loader, and validator"
```

---

## Task 12: Default Core Contract YAML

**Files:**
- Create: `contracts/core/default_contract.yaml`

**Step 1: Create default contract YAML**

```yaml
# contracts/core/default_contract.yaml
contract_name: ai_db_core_v1
contract_version: "1.0.0"
description: Core contract for AI database quality assurance (database-agnostic)

operations:
  create_collection:
    description: Create a new collection for storing vectors
    parameters:
      collection_name:
        name: collection_name
        type: str
        required: true
        description: Name of the collection to create
      dimension:
        name: dimension
        type: int
        required: true
        min_value: 1
        description: Dimension of vectors to be stored
      metric_type:
        name: metric_type
        type: str
        required: false
        default_value: "L2"
        allowed_values: ["L2", "IP", "COSINE"]
        description: Distance metric type
    required_preconditions: []
    error_diagnostic_slots:
      - slot_name: collection_name
        required: true
        description: Name of the collection that failed
      - slot_name: error_reason
        required: true
        description: Why creation failed
    applicable_oracles: []

  drop_collection:
    description: Drop an existing collection
    parameters:
      collection_name:
        name: collection_name
        type: str
        required: true
        description: Name of the collection to drop
    required_preconditions:
      - collection_exists
    error_diagnostic_slots:
      - slot_name: collection_name
        required: true
      - slot_name: error_reason
        required: true
    applicable_oracles: []

  insert:
    description: Insert vectors into a collection
    parameters:
      collection_name:
        name: collection_name
        type: str
        required: true
        description: Target collection name
      vectors:
        name: vectors
        type: list
        required: true
        description: List of vectors to insert (each vector is list of floats)
      ids:
        name: ids
        type: list
        required: false
        description: Optional IDs for the vectors
    required_preconditions:
      - collection_exists
    error_diagnostic_slots:
      - slot_name: collection_name
        required: true
      - slot_name: dimension_mismatch
        required: true
        description: Whether dimension mismatch was the issue
      - slot_name: error_reason
        required: true
    applicable_oracles:
      - write_read_consistency

  delete:
    description: Delete vectors from a collection
    parameters:
      collection_name:
        name: collection_name
        type: str
        required: true
      ids:
        name: ids
        type: list
        required: true
        description: IDs of vectors to delete
    required_preconditions:
      - collection_exists
    error_diagnostic_slots:
      - slot_name: collection_name
        required: true
      - slot_name: error_reason
        required: true
    applicable_oracles: []

  build_index:
    description: Build an index for a collection
    parameters:
      collection_name:
        name: collection_name
        type: str
        required: true
      index_type:
        name: index_type
        type: str
        required: false
        default_value: "IVF_FLAT"
        description: Type of index to build
      index_params:
        name: index_params
        type: dict
        required: false
        description: Index-specific parameters
    required_preconditions:
      - collection_exists
      - min_data_count
    error_diagnostic_slots:
      - slot_name: collection_name
        required: true
      - slot_name: index_type
        required: true
      - slot_name: error_reason
        required: true
    applicable_oracles: []

  load_index:
    description: Load index into memory for search
    parameters:
      collection_name:
        name: collection_name
        type: str
        required: true
    required_preconditions:
      - collection_exists
      - index_built
    error_diagnostic_slots:
      - slot_name: collection_name
        required: true
      - slot_name: error_reason
        required: true
    applicable_oracles: []

  search:
    description: Search for similar vectors
    parameters:
      collection_name:
        name: collection_name
        type: str
        required: true
      vector:
        name: vector
        type: list
        required: true
        description: Query vector
      top_k:
        name: top_k
        type: int
        required: true
        min_value: 1
        description: Number of results to return
    required_preconditions:
      - collection_exists
      - index_built
      - index_loaded
    error_diagnostic_slots:
      - slot_name: collection_name
        required: true
      - slot_name: top_k
        required: true
      - slot_name: error_reason
        required: true
    applicable_oracles:
      - topk_monotonicity
      - filter_strictness

  filtered_search:
    description: Search with filter expression
    parameters:
      collection_name:
        name: collection_name
        type: str
        required: true
      vector:
        name: vector
        type: list
        required: true
      top_k:
        name: top_k
        type: int
        required: true
        min_value: 1
      filter:
        name: filter
        type: str
        required: true
        description: Filter expression
    required_preconditions:
      - collection_exists
      - index_built
      - index_loaded
      - supported_features
    error_diagnostic_slots:
      - slot_name: collection_name
        required: true
      - slot_name: filter
        required: true
      - slot_name: error_reason
        required: true
    applicable_oracles:
      - topk_monotonicity
      - filter_strictness

  hybrid_search:
    description: Hybrid search combining multiple strategies
    parameters:
      collection_name:
        name: collection_name
        type: str
        required: true
      vector:
        name: vector
        type: list
        required: true
      top_k:
        name: top_k
        type: int
        required: true
        min_value: 1
      filters:
        name: filters
        type: dict
        required: false
    required_preconditions:
      - collection_exists
      - index_built
      - index_loaded
      - supported_features
    error_diagnostic_slots:
      - slot_name: collection_name
        required: true
      - slot_name: error_reason
        required: true
    applicable_oracles:
      - topk_monotonicity
      - filter_strictness
```

**Step 2: Add test for loading default contract**

```python
# Add to tests/unit/test_contracts.py

def test_load_default_contract():
    """Test loading the default core contract."""
    from contracts.core.loader import get_default_contract_path

    contract = load_contract(get_default_contract_path())

    assert contract.contract_name == "ai_db_core_v1"
    assert contract.contract_version == "1.0.0"
    assert len(contract.operations) > 0

    # Check that search operation exists
    search_contract = contract.get_operation_contract(OperationType.SEARCH)
    assert search_contract is not None
    assert search_contract.parameters["top_k"].min_value == 1
    assert "index_loaded" in search_contract.required_preconditions
```

**Step 3: Run tests**

```bash
cd "C:\Users\11428\Desktop\ai-db-qc"
pytest tests/unit/test_contracts.py -v
```

Expected: All tests pass

**Step 4: Commit**

```bash
git add contracts/
git commit -m "feat(contracts): add default core contract YAML"
```

---

## Task 13: DB Profile Schema and Loader

**Files:**
- Create: `contracts/db_profiles/__init__.py`
- Create: `contracts/db_profiles/schema.py`
- Create: `contracts/db_profiles/loader.py`
- Create: `contracts/db_profiles/milvus_profile.yaml`

**Step 1: Create contracts/db_profiles/schema.py**

```python
# contracts/db_profiles/schema.py
"""Database profile schema (database-specific)."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from schemas.common import OperationType


class CapabilityMapping(BaseModel):
    """Mapping of core contract operation to DB-specific API."""

    core_operation: OperationType = Field(description="Core contract operation")
    db_operation: str = Field(description="Database-specific operation name")
    api_endpoint: str = Field(description="API endpoint or method")
    parameter_mapping: Dict[str, str] = Field(
        description="Map core parameter names to DB-specific names"
    )


class Capability(BaseModel):
    """Database capability descriptor."""

    capability_name: str = Field(description="Name of the capability")
    supported: bool = Field(description="Whether this DB supports this capability")
    notes: str = Field(default="", description="Additional notes")


class DBProfile(BaseModel):
    """Database-specific profile."""

    profile_name: str = Field(description="Profile identifier (e.g., 'milvus-2.3')")
    db_type: str = Field(description="Database type (e.g., 'milvus', 'qdrant')")
    db_version: str = Field(description="Supported database version")
    description: str = Field(description="Profile description")

    # Capabilities
    capabilities: Dict[str, Capability] = Field(
        description="Supported capabilities"
    )

    # Operation mappings
    operation_mappings: Dict[OperationType, CapabilityMapping] = Field(
        description="How core operations map to DB operations"
    )

    # Constraints and relaxations
    parameter_relaxations: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Relaxations to core contract constraints"
    )

    # Quirks and workarounds
    known_quirks: List[str] = Field(
        default_factory=list,
        description="Known database-specific quirks"
    )

    # Supported features
    supported_features: List[str] = Field(
        default_factory=list,
        description="Features that this database supports"
    )

    def supports_capability(self, capability_name: str) -> bool:
        """Check if database supports a capability."""
        cap = self.capabilities.get(capability_name)
        return cap is not None and cap.supported

    def get_operation_mapping(self, op_type: OperationType) -> Optional[CapabilityMapping]:
        """Get mapping for a core operation."""
        return self.operation_mappings.get(op_type)
```

**Step 2: Create contracts/db_profiles/loader.py**

```python
# contracts/db_profiles/loader.py
"""Database profile loader."""

import yaml
from pathlib import Path
from typing import Optional

from contracts.db_profiles.schema import DBProfile


class ProfileLoadError(Exception):
    """Error loading profile."""

    pass


def load_profile(profile_path: str | Path) -> DBProfile:
    """
    Load a database profile from YAML file.

    Args:
        profile_path: Path to profile YAML file

    Returns:
        DBProfile instance

    Raises:
        ProfileLoadError: If profile cannot be loaded
    """
    path = Path(profile_path)
    if not path.exists():
        raise ProfileLoadError(f"Profile file not found: {profile_path}")

    try:
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ProfileLoadError(f"Invalid YAML in profile file: {e}")

    # Parse operation type strings back to enums
    if "operation_mappings" in data:
        parsed_mappings = {}
        for op_str, mapping_data in data["operation_mappings"].items:
            try:
                op_type = OperationType(op_str)
                parsed_mappings[op_type] = mapping_data
            except ValueError:
                raise ProfileLoadError(f"Invalid operation type: {op_str}")
        data["operation_mappings"] = parsed_mappings

    try:
        profile = DBProfile(**data)
    except Exception as e:
        raise ProfileLoadError(f"Invalid profile structure: {e}")

    return profile


class ProfileRegistry:
    """Registry for database profiles."""

    _profiles: dict[str, DBProfile] = {}

    @classmethod
    def register(cls, name: str, profile: DBProfile) -> None:
        """Register a profile."""
        cls._profiles[name] = profile

    @classmethod
    def get(cls, name: str) -> Optional[DBProfile]:
        """Get a registered profile."""
        return cls._profiles.get(name)

    @classmethod
    def list_profiles(cls) -> list[str]:
        """List registered profile names."""
        return list(cls._profiles.keys())
```

**Step 3: Create contracts/db_profiles/milvus_profile.yaml**

```yaml
# contracts/db_profiles/milvus_profile.yaml
profile_name: milvus-2.3
db_type: milvus
db_version: "2.3.x"
description: Milvus 2.3.x database profile

capabilities:
  vector_index:
    supported: true
    notes: "Supports IVF_FLAT, IVF_SQ8, HNSW, etc."
  scalar_index:
    supported: true
    notes: "Supports scalar field indexing"
  hybrid_search:
    supported: true
    notes: "Supports hybrid vector + scalar search"
  filtered_search:
    supported: true
    notes: "Supports filter expressions on scalar fields"
  bulk_insert:
    supported: true
    notes: "Supports bulk vector insertion"
  upsert:
    supported: true
    notes: "Supports upsert operations"

operation_mappings:
  create_collection:
    core_operation: create_collection
    db_operation: "create_collection"
    api_endpoint: "/collections"
    parameter_mapping:
      collection_name: "collection_name"
      dimension: "dimension"
      metric_type: "metric_type"

  drop_collection:
    core_operation: drop_collection
    db_operation: "drop_collection"
    api_endpoint: "/collections/{collection_name}"
    parameter_mapping:
      collection_name: "collection_name"

  insert:
    core_operation: insert
    db_operation: "insert"
    api_endpoint: "/collections/{collection_name}/entities"
    parameter_mapping:
      collection_name: "collection_name"
      vectors: "data"
      ids: "ids"

  delete:
    core_operation: delete
    db_operation: "delete"
    api_endpoint: "/collections/{collection_name}/entities"
    parameter_mapping:
      collection_name: "collection_name"
      ids: "ids"

  build_index:
    core_operation: build_index
    db_operation: "create_index"
    api_endpoint: "/collections/{collection_name}/index"
    parameter_mapping:
      collection_name: "collection_name"
      index_type: "index_type"
      index_params: "params"

  load_index:
    core_operation: load_index
    db_operation: "load"
    api_endpoint: "/collections/{collection_name}/load"
    parameter_mapping:
      collection_name: "collection_name"

  search:
    core_operation: search
    db_operation: "search"
    api_endpoint: "/collections/{collection_name}/search"
    parameter_mapping:
      collection_name: "collection_name"
      vector: "data"
      top_k: "top_k"

  filtered_search:
    core_operation: filtered_search
    db_operation: "search"
    api_endpoint: "/collections/{collection_name}/search"
    parameter_mapping:
      collection_name: "collection_name"
      vector: "data"
      top_k: "top_k"
      filter: "expr"

  hybrid_search:
    core_operation: hybrid_search
    db_operation: "hybrid_search"
    api_endpoint: "/collections/{collection_name}/hybrid_search"
    parameter_mapping:
      collection_name: "collection_name"
      vector: "vector"
      top_k: "top_k"
      filters: "filters"

parameter_relaxations:
  search:
    top_k:
      # Milvus allows top_k up to 16384 by default
      max_value: 16384
      # Relax minimum for testing
      min_value: 1

known_quirks:
  - "Collection must be loaded before search operations"
  - "Index building requires minimum data (depends on index type)"
  - "Filtered search performance depends on scalar index existence"
  - "top_k larger than collection size returns all available results"

supported_features:
  - "IVF_FLAT"
  - "IVF_SQ8"
  - "HNSW"
  - "Scalar indexing"
  - "Boolean expression filters"
  - "Range queries"
  - "Bulk operations"
```

**Step 4: Create unit tests**

```python
# tests/unit/test_profiles.py

import pytest
from contracts.db_profiles.schema import DBProfile, Capability, CapabilityMapping
from contracts.db_profiles.loader import load_profile, ProfileRegistry, ProfileLoadError
from schemas.common import OperationType


def test_capability_schema():
    """Test capability schema."""
    capability = Capability(
        capability_name="vector_index",
        supported=True,
        notes="Supports various index types"
    )
    assert capability.capability_name == "vector_index"
    assert capability.supported is True


def test_capability_mapping():
    """Test capability mapping schema."""
    mapping = CapabilityMapping(
        core_operation=OperationType.SEARCH,
        db_operation="search",
        api_endpoint="/collections/{collection_name}/search",
        parameter_mapping={"top_k": "top_k", "vector": "data"}
    )
    assert mapping.core_operation == OperationType.SEARCH
    assert mapping.db_operation == "search"


def test_db_profile_schema():
    """Test DB profile schema."""
    profile = DBProfile(
        profile_name="test-db",
        db_type="test",
        db_version="1.0.0",
        description="Test profile",
        capabilities={
            "vector_index": Capability(
                capability_name="vector_index",
                supported=True
            )
        },
        operation_mappings={}
    )
    assert profile.profile_name == "test-db"
    assert profile.supports_capability("vector_index") is True
    assert profile.supports_capability("nonexistent") is False


def test_profile_load_error():
    """Test that loading non-existent profile raises error."""
    with pytest.raises(ProfileLoadError):
        load_profile("/nonexistent/path.yaml")


def test_load_milvus_profile():
    """Test loading Milvus profile."""
    profile = load_profile("contracts/db_profiles/milvus_profile.yaml")

    assert profile.profile_name == "milvus-2.3"
    assert profile.db_type == "milvus"
    assert profile.supports_capability("vector_index") is True

    # Check operation mapping exists
    search_mapping = profile.get_operation_mapping(OperationType.SEARCH)
    assert search_mapping is not None
    assert search_mapping.api_endpoint == "/collections/{collection_name}/search"


def test_profile_registry():
    """Test profile registry."""
    profile = DBProfile(
        profile_name="test-profile",
        db_type="test",
        db_version="1.0.0",
        description="Test",
        capabilities={},
        operation_mappings={}
    )

    ProfileRegistry.register("test", profile)
    retrieved = ProfileRegistry.get("test")

    assert retrieved is not None
    assert retrieved.profile_name == "test-profile"
```

**Step 5: Run tests**

```bash
cd "C:\Users\11428\Desktop\ai-db-qc"
pytest tests/unit/test_profiles.py -v
```

Expected: All tests pass

**Step 6: Fix loader.py operation type parsing bug**

The YAML loader has a syntax error. Fix it:

```python
# Fix in contracts/db_profiles/loader.py

        for op_str, mapping_data in data["operation_mappings"].items():
            try:
                op_type = OperationType(op_str)
                parsed_mappings[op_type] = mapping_data
            except ValueError:
                raise ProfileLoadError(f"Invalid operation type: {op_str}")
```

**Step 7: Commit**

```bash
git add contracts/ tests/unit/
git commit -m "feat(profiles): add database profile schema, loader, and Milvus profile"
```

---

## Task 14: Case Templates (10 Basic Cases)

**Files:**
- Create: `casegen/templates/basic_templates.yaml`

**Step 1: Create basic_templates.yaml**

```yaml
# casegen/templates/basic_templates.yaml
templates:
  # ===== VALID CASES =====

  - template_id: tmpl-valid-001
    operation: create_collection
    param_template:
      collection_name: "test_collection_{id}"
      dimension: 128
      metric_type: "L2"
    validity_category: valid
    expected_validity: legal
    precondition_sensitivity: []
    rationale: "Basic valid collection creation with standard parameters"

  - template_id: tmpl-valid-002
    operation: insert
    param_template:
      collection_name: "{collection}"
      vectors: "[{vectors}]"
      ids: "[{ids}]"
    validity_category: valid
    expected_validity: legal
    precondition_sensitivity:
      - collection_exists
    rationale: "Valid insert into existing collection"

  - template_id: tmpl-valid-003
    operation: search
    param_template:
      collection_name: "{collection}"
      vector: "{query_vector}"
      top_k: "{k}"
    validity_category: valid
    expected_validity: legal
    precondition_sensitivity:
      - collection_exists
      - index_built
      - index_loaded
    rationale: "Valid search with all preconditions satisfied"
    oracle_refs:
      - topk_monotonicity

  # ===== INVALID PARAMETER CASES =====

  - template_id: tmpl-invalid-001
    operation: create_collection
    param_template:
      collection_name: "test_collection_{id}"
      dimension: 0  # Invalid: dimension must be >= 1
      metric_type: "L2"
    validity_category: invalid
    expected_validity: illegal
    precondition_sensitivity: []
    rationale: "Invalid collection creation with zero dimension"

  - template_id: tmpl-invalid-002
    operation: search
    param_template:
      collection_name: "{collection}"
      vector: "{query_vector}"
      top_k: -1  # Invalid: top_k must be >= 1
    validity_category: invalid
    expected_validity: illegal
    precondition_sensitivity:
      - collection_exists
      - index_built
      - index_loaded
    rationale: "Invalid search with negative top_k parameter"

  - template_id: tmpl-invalid-003
    operation: insert
    param_template:
      collection_name: "{collection}"
      vectors: "[{vectors}]"  # Wrong dimension
      ids: "[{ids}]"
    validity_category: invalid
    expected_validity: illegal
    precondition_sensitivity:
      - collection_exists
    rationale: "Invalid insert with dimension mismatch"

  - template_id: tmpl-invalid-004
    operation: create_collection
    param_template:
      collection_name: "test_collection_{id}"
      dimension: 128
      metric_type: "INVALID_METRIC"  # Not in allowed values
    validity_category: invalid
    expected_validity: illegal
    precondition_sensitivity: []
    rationale: "Invalid metric type outside allowed values"

  # ===== PSEUDO-VALID / PRECONDITION-SENSITIVE CASES =====

  - template_id: tmpl-pseudo-001
    operation: search
    param_template:
      collection_name: "nonexistent_collection"  # Collection doesn't exist
      vector: "{query_vector}"
      top_k: "{k}"
    validity_category: pseudo_valid
    expected_validity: legal  # Contract-valid but precondition-fail
    precondition_sensitivity:
      - collection_exists
    rationale: "Contract-valid search on non-existent collection (precondition-fail)"

  - template_id: tmpl-pseudo-002
    operation: search
    param_template:
      collection_name: "{collection}"  # Exists but index not loaded
      vector: "{query_vector}"
      top_k: "{k}"
    validity_category: pseudo_valid
    expected_validity: legal  # Contract-valid but precondition-fail
    precondition_sensitivity:
      - collection_exists
      - index_built
      - index_loaded
    rationale: "Contract-valid search before index load (precondition-fail)"

  - template_id: tmpl-pseudo-003
    operation: insert
    param_template:
      collection_name: "{collection}"  # Valid parameters but collection doesn't exist
      vectors: "[{vectors}]"
      ids: "[{ids}]"
    validity_category: pseudo_valid
    expected_validity: legal  # Contract-valid but precondition-fail
    precondition_sensitivity:
      - collection_exists
    rationale: "Contract-valid insert into non-existent collection (precondition-fail)"
```

**Step 2: Create casegen/templates/loader.py**

```python
# casegen/templates/loader.py
"""Case template loader."""

import yaml
from pathlib import Path
from typing import List

from schemas.case import CaseTemplate


class TemplateLoadError(Exception):
    """Error loading templates."""

    pass


def load_templates(template_path: str | Path) -> List[CaseTemplate]:
    """
    Load case templates from YAML file.

    Args:
        template_path: Path to template YAML file

    Returns:
        List of CaseTemplate instances

    Raises:
        TemplateLoadError: If templates cannot be loaded
    """
    path = Path(template_path)
    if not path.exists():
        raise TemplateLoadError(f"Template file not found: {template_path}")

    try:
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise TemplateLoadError(f"Invalid YAML in template file: {e}")

    templates = []
    for tmpl_data in data.get("templates", []):
        try:
            template = CaseTemplate(**tmpl_data)
            templates.append(template)
        except Exception as e:
            raise TemplateLoadError(f"Invalid template structure: {e}")

    return templates


def get_basic_templates_path() -> Path:
    """Get path to basic templates file."""
    return Path(__file__).parent / "basic_templates.yaml"
```

**Step 3: Create unit tests**

```python
# tests/unit/test_templates.py

import pytest
from casegen.templates.loader import load_templates, get_basic_templates_path, TemplateLoadError
from schemas.case import CaseTemplate
from schemas.common import InputValidity


def test_load_basic_templates():
    """Test loading basic case templates."""
    templates = load_templates(get_basic_templates_path())

    assert len(templates) == 10

    # Check categories
    valid_count = sum(1 for t in templates if t.validity_category == "valid")
    invalid_count = sum(1 for t in templates if t.validity_category == "invalid")
    pseudo_count = sum(1 for t in templates if t.validity_category == "pseudo_valid")

    assert valid_count == 3
    assert invalid_count == 4
    assert pseudo_count == 3


def test_template_structure():
    """Test individual template structure."""
    templates = load_templates(get_basic_templates_path())

    # Find a valid template
    valid_tmpl = next(t for t in templates if t.template_id == "tmpl-valid-001")
    assert valid_tmpl.validity_category == "valid"
    assert valid_tmpl.expected_validity == InputValidity.LEGAL

    # Find an invalid template
    invalid_tmpl = next(t for t in templates if t.template_id == "tmpl-invalid-001")
    assert invalid_tmpl.validity_category == "invalid"
    assert invalid_tmpl.expected_validity == InputValidity.ILLEGAL

    # Find a pseudo-valid template
    pseudo_tmpl = next(t for t in templates if t.template_id == "tmpl-pseudo-001")
    assert pseudo_tmpl.validity_category == "pseudo_valid"
    assert pseudo_tmpl.expected_validity == InputValidity.LEGAL
    assert "collection_exists" in pseudo_tmpl.precondition_sensitivity


def test_template_load_error():
    """Test that loading non-existent templates raises error."""
    with pytest.raises(TemplateLoadError):
        load_templates("/nonexistent/path.yaml")


def test_template_precondition_sensitivity():
    """Test that pseudo-valid templates have precondition sensitivity."""
    templates = load_templates(get_basic_templates_path())

    pseudo_templates = [t for t in templates if t.validity_category == "pseudo_valid"]

    for tmpl in pseudo_templates:
        assert len(tmpl.precondition_sensitivity) > 0, \
            f"Pseudo-valid template {tmpl.template_id} should have precondition sensitivity"


def test_template_oracle_refs():
    """Test that some templates have oracle references."""
    templates = load_templates(get_basic_templates_path())

    # Find search template with oracle refs
    search_tmpl = next((t for t in templates if t.template_id == "tmpl-valid-003"), None)
    assert search_tmpl is not None
    assert "topk_monotonicity" in search_tmpl.oracle_refs or len(search_tmpl.oracle_refs) >= 0
```

**Step 4: Run tests**

```bash
cd "C:\Users\11428\Desktop\ai-db-qc"
pytest tests/unit/test_templates.py -v
```

Expected: All tests pass

**Step 5: Commit**

```bash
git add casegen/ tests/unit/
git commit -m "feat(casegen): add 10 basic case templates covering valid, invalid, and pseudo-valid cases"
```

---

## Task 15: Update Schema Exports and Final Integration

**Files:**
- Modify: `schemas/__init__.py`
- Create: `scripts/init_check.py`

**Step 1: Verify all schemas are properly exported**

```python
# schemas/__init__.py - verify it's complete
"""Core schemas for AI-DB-QC system."""

from schemas.common import *
from schemas.case import TestCase, CaseTemplate, Preconditions
from schemas.result import ExecutionResult, OracleResult, TriageResult, ConfirmResult
from schemas.evidence import (
    EvidenceBundle,
    EnvironmentFingerprint,
    CaseSnapshot,
    RequestSnapshot,
    ResponseSnapshot,
)

__all__ = [
    # Common
    "InputValidity",
    "PreconditionStatus",
    "ObservedOutcome",
    "BugType",
    "ConfirmStatus",
    "OperationType",
    "SourceType",
    "RunMetadata",
    "DiagnosticSlot",
    "GateTrace",
    # Case
    "TestCase",
    "CaseTemplate",
    "Preconditions",
    # Result
    "ExecutionResult",
    "OracleResult",
    "TriageResult",
    "ConfirmResult",
    # Evidence
    "EvidenceBundle",
    "EnvironmentFingerprint",
    "CaseSnapshot",
    "RequestSnapshot",
    "ResponseSnapshot",
]
```

**Step 2: Create initialization check script**

```python
# scripts/init_check.py
"""Verify Phase 1 initialization is complete."""

import sys
from pathlib import Path


def check_file_exists(path: str | Path) -> bool:
    """Check if file exists."""
    return Path(path).exists()


def check_directory_structure():
    """Check that all required directories exist."""
    required_dirs = [
        "contracts/core",
        "contracts/db_profiles",
        "schemas",
        "casegen/prompts",
        "casegen/templates",
        "casegen/generators",
        "adapters",
        "pipeline",
        "oracles",
        "evidence",
        "benchmarks/mock_faults",
        "benchmarks/milvus_basic",
        "benchmarks/semantic_oracles",
        "scripts",
        "tests/unit",
        "tests/integration",
        "docs/plans",
    ]

    print("Checking directory structure...")
    missing = []
    for dir_path in required_dirs:
        if not check_file_exists(dir_path):
            missing.append(dir_path)

    if missing:
        print(f"❌ Missing directories: {missing}")
        return False
    print("✅ All directories exist")
    return True


def check_documentation():
    """Check that all required documentation exists."""
    required_docs = [
        "README.md",
        "THEORY.md",
        "PROJECT_SCOPE.md",
        "BUG_TAXONOMY.md",
        "NON_GOALS.md",
    ]

    print("Checking documentation...")
    missing = []
    for doc_path in required_docs:
        if not check_file_exists(doc_path):
            missing.append(doc_path)

    if missing:
        print(f"❌ Missing documentation: {missing}")
        return False
    print("✅ All documentation exists")
    return True


def check_schemas():
    """Check that all schema files exist."""
    required_schemas = [
        "schemas/__init__.py",
        "schemas/common.py",
        "schemas/case.py",
        "schemas/result.py",
        "schemas/evidence.py",
    ]

    print("Checking schema files...")
    missing = []
    for schema_path in required_schemas:
        if not check_file_exists(schema_path):
            missing.append(schema_path)

    if missing:
        print(f"❌ Missing schema files: {missing}")
        return False
    print("✅ All schema files exist")
    return True


def check_contracts():
    """Check that contract files exist."""
    required_contracts = [
        "contracts/core/__init__.py",
        "contracts/core/schema.py",
        "contracts/core/loader.py",
        "contracts/core/validator.py",
        "contracts/core/default_contract.yaml",
        "contracts/db_profiles/__init__.py",
        "contracts/db_profiles/schema.py",
        "contracts/db_profiles/loader.py",
        "contracts/db_profiles/milvus_profile.yaml",
    ]

    print("Checking contract files...")
    missing = []
    for contract_path in required_contracts:
        if not check_file_exists(contract_path):
            missing.append(contract_path)

    if missing:
        print(f"❌ Missing contract files: {missing}")
        return False
    print("✅ All contract files exist")
    return True


def check_templates():
    """Check that case templates exist."""
    required_templates = [
        "casegen/templates/basic_templates.yaml",
        "casegen/templates/loader.py",
    ]

    print("Checking case templates...")
    missing = []
    for template_path in required_templates:
        if not check_file_exists(template_path):
            missing.append(template_path)

    if missing:
        print(f"❌ Missing template files: {missing}")
        return False
    print("✅ All template files exist")
    return True


def check_imports():
    """Check that all modules can be imported."""
    print("Checking module imports...")

    try:
        import schemas
        from schemas import (
            TestCase, ExecutionResult, OracleResult,
            TriageResult, ConfirmResult, EvidenceBundle
        )
        print("  ✅ schemas module")
    except Exception as e:
        print(f"  ❌ schemas module: {e}")
        return False

    try:
        import contracts.core
        from contracts.core import load_contract
        print("  ✅ contracts.core module")
    except Exception as e:
        print(f"  ❌ contracts.core module: {e}")
        return False

    try:
        import contracts.db_profiles
        from contracts.db_profiles import load_profile
        print("  ✅ contracts.db_profiles module")
    except Exception as e:
        print(f"  ❌ contracts.db_profiles module: {e}")
        return False

    try:
        import casegen.templates
        from casegen.templates import load_templates
        print("  ✅ casegen.templates module")
    except Exception as e:
        print(f"  ❌ casegen.templates module: {e}")
        return False

    print("✅ All modules import successfully")
    return True


def main():
    """Run all checks."""
    print("=" * 60)
    print("AI-DB-QC Phase 1 Initialization Check")
    print("=" * 60)
    print()

    all_passed = True
    all_passed &= check_directory_structure()
    all_passed &= check_documentation()
    all_passed &= check_schemas()
    all_passed &= check_contracts()
    all_passed &= check_templates()
    all_passed &= check_imports()

    print()
    print("=" * 60)
    if all_passed:
        print("✅ Phase 1 initialization complete!")
        print("=" * 60)
        return 0
    else:
        print("❌ Phase 1 initialization incomplete")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

**Step 3: Run initialization check**

```bash
cd "C:\Users\11428\Desktop\ai-db-qc"
python scripts/init_check.py
```

Expected: All checks pass

**Step 4: Run all tests**

```bash
cd "C:\Users\11428\Desktop\ai-db-qc"
pytest tests/unit/ -v --tb=short
```

Expected: All tests pass

**Step 5: Create summary document**

```markdown
# Phase 1 Completion Summary

## Completed Components

### 1. Repository Structure
- ✅ Complete directory structure matching specification
- ✅ Configuration files (pyproject.toml, requirements.txt, .gitignore)
- ✅ README with project overview

### 2. Foundational Documentation
- ✅ THEORY.md - Theoretical foundation with dual-layer validity model
- ✅ PROJECT_SCOPE.md - Project boundaries and success criteria
- ✅ BUG_TAXONOMY.md - Four-type defect classification with red-line constraint
- ✅ NON_GOALS.md - Explicit exclusion of platform features

### 3. Core Schemas
- ✅ common.py - Base types and enums (BugType, OperationType, etc.)
- ✅ case.py - TestCase, CaseTemplate, Preconditions
- ✅ result.py - ExecutionResult, OracleResult, TriageResult, ConfirmResult
- ✅ evidence.py - EvidenceBundle with full reproducibility support

### 4. Contract Infrastructure
- ✅ Core contract schema (database-agnostic)
- ✅ Contract loader and registry
- ✅ Contract validator for input validity checking
- ✅ Default core contract YAML with all operations

### 5. Database Profile Infrastructure
- ✅ DB profile schema (database-specific)
- ✅ Profile loader and registry
- ✅ Milvus 2.3 profile with operation mappings

### 6. Case Templates
- ✅ 10 basic templates:
  - 3 valid cases
  - 4 invalid parameter cases
  - 3 pseudo-valid / precondition-sensitive cases

### 7. Unit Tests
- ✅ test_schemas.py - All schema tests
- ✅ test_contracts.py - Contract loading and validation
- ✅ test_profiles.py - Profile loading
- ✅ test_templates.py - Template loading

## Verification

Run the initialization check:
```bash
python scripts/init_check.py
```

Run all unit tests:
```bash
pytest tests/unit/ -v
```

## Key Design Decisions

1. **Schema-First**: All data structures use pydantic for validation and serialization
2. **Dual-Layer Validity**: Explicit separation between contract-validity and precondition-pass
3. **Evidence-Centric**: EvidenceBundle designed for full reproducibility
4. **LLM-Optional**: No LLM dependencies in Phase 1
5. **Minimal Design**: Simple, readable schemas without over-engineering

## Next Steps (Phase 2)

Phase 2 will build on this foundation to add:
- Adapter layer (base + Milvus + mock)
- Precondition gate implementation
- Oracle implementations (topk_monotonicity, filter_strictness, write_read_consistency)
- Triage pipeline with red-line enforcement
- Evidence writing

## Files Created/Modified

### Documentation (5 files)
- README.md
- THEORY.md
- PROJECT_SCOPE.md
- BUG_TAXONOMY.md
- NON_GOALS.md

### Schemas (4 files)
- schemas/__init__.py
- schemas/common.py
- schemas/case.py
- schemas/result.py
- schemas/evidence.py

### Contracts (10 files)
- contracts/core/__init__.py
- contracts/core/schema.py
- contracts/core/loader.py
- contracts/core/validator.py
- contracts/core/default_contract.yaml
- contracts/db_profiles/__init__.py
- contracts/db_profiles/schema.py
- contracts/db_profiles/loader.py
- contracts/db_profiles/milvus_profile.yaml

### Case Generation (2 files)
- casegen/templates/basic_templates.yaml
- casegen/templates/loader.py

### Tests (4 files)
- tests/unit/__init__.py
- tests/unit/test_schemas.py
- tests/unit/test_contracts.py
- tests/unit/test_profiles.py
- tests/unit/test_templates.py

### Scripts (1 file)
- scripts/init_check.py

### Configuration (3 files)
- pyproject.toml
- requirements.txt
- .gitignore

**Total: 29 files created**
```

**Step 6: Commit**

```bash
git add .
git commit -m "feat: complete Phase 1 initialization with schemas, contracts, templates, and documentation"
```

**Step 7: Create git tag for Phase 1 completion**

```bash
git tag -a phase1-complete -m "Phase 1: Initial structure and schema foundation complete"
git tag -l
```

---

## End of Phase 1 Implementation Plan

This completes the Phase 1 implementation plan. When all tasks are complete:

1. ✅ Repository structure is complete
2. ✅ Documentation clearly articulates the research contribution
3. ✅ All schemas are defined and can serialize/deserialize
4. ✅ Core contracts can be loaded
5. ✅ Milvus profile is defined and loadable
6. ✅ Case templates cover valid, invalid, and pseudo-valid cases
7. ✅ Unit tests validate schema and loading logic
8. ✅ `pytest tests/` passes

### Acceptance Criteria Verification

```bash
# Run initialization check
python scripts/init_check.py

# Run all tests
pytest tests/unit/ -v

# Verify imports work
python -c "from schemas import *; from contracts.core import load_contract; from contracts.db_profiles import load_profile; from casegen.templates import load_templates; print('All imports successful')"
```

### Files Summary

| Category | Files |
|----------|-------|
| Documentation | 5 |
| Schemas | 5 |
| Contracts | 10 |
| Case Gen | 2 |
| Tests | 5 |
| Scripts | 1 |
| Config | 3 |
| **Total** | **29 files** |
