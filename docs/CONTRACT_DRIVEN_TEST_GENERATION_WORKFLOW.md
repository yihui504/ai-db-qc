# Contract-Driven Test Generation Workflow

**Document Version**: 1.0
**Date**: 2026-03-09
**Scope**: End-to-End Workflow from Contract Extraction to Regression Packaging

---

## Executive Summary

This document describes the complete contract-driven test generation workflow. The workflow transforms raw information sources (documentation, APIs, observed behavior) into validated test cases, executes them, judges correctness, and produces regression packs. The workflow is iterative, with feedback loops at each stage.

---

## Workflow Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           CONTRACT-DRIVEN TEST GENERATION WORKFLOW              │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  INPUT                   PROCESS                 OUTPUT                         │
│  ──────                  ────────                ───────                        │
│                                                                                 │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐                │
│  │              │      │  1. Contract │      │              │                │
│  │  Source      │  →   │     Extract  │  →   │  Candidate   │                │
│  │  Material    │      │              │      │  Contracts   │                │
│  └──────────────┘      └──────────────┘      └──────────────┘                │
│                                                                                 │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐                │
│  │  Candidate   │      │  2. Contract │      │              │                │
│  │  Contracts   │  →   │    Normalize │  →   │  Formal      │                │
│  │              │      │              │      │  Contracts   │                │
│  └──────────────┘      └──────────────┘      └──────────────┘                │
│                                                                                 │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐                │
│  │  Formal      │      │  3. Test Case│      │              │                │
│  │  Contracts   │  →   │   Generate   │  →   │  Test Suite  │                │
│  │              │      │              │      │              │                │
│  └──────────────┘      └──────────────┘      └──────────────┘                │
│                                                                                 │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐                │
│  │  Test Suite  │      │  4. Test     │      │              │                │
│  │              │  →   │    Execute   │  →   │  Raw Results │                │
│  │              │      │              │      │              │                │
│  └──────────────┘      └──────────────┘      └──────────────┘                │
│                                                                                 │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐                │
│  │  Raw Results │      │  5. Correct- │      │              │                │
│  │              │  →   │     ness     │  →   │  Classified  │                │
│  │              │      │    Judge     │      │  Findings    │                │
│  └──────────────┘      └──────────────┘      └──────────────┘                │
│                                                                                 │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐                │
│  │  Classified  │      │  6. Bug /    │      │              │                │
│  │  Findings    │  →   │  Non-Bug     │  →   │  Triage      │                │
│  │              │      │   Classify   │      │  Report      │                │
│  └──────────────┘      └──────────────┘      └──────────────┘                │
│                                                                                 │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐                │
│  │  Triage      │      │  7. Reconfir- │      │              │                │
│  │  Report      │  →   │   mation &   │  →   │  Regression   │                │
│  │              │      │   Regression  │      │  Pack        │                │
│  └──────────────┘      └──────────────┘      └──────────────┘                │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Stage 1: Contract Extraction

**Purpose**: Identify candidate contracts from source materials.

### Input Sources

| Source Type | Examples | Contract Yield |
|-------------|----------|----------------|
| **Documentation** | API docs, user guides, tutorials | Operation-level, result contracts |
| **API Specifications** | Type signatures, parameter lists | Operation-level contracts |
| **Standards** | SQL specifications, industry standards | Universal contracts |
| **Academic Literature** | Research papers, theorems | Universal contracts |
| **Observed Behavior** | Test execution, production data | Empirical contracts |

### Extraction Methods

#### Manual Curation

**Process**:
1. Read documentation
2. Identify behavioral statements
3. Extract implicit contracts
4. Formalize as contract specification

**Example**:
```
Documentation: "Once a collection is dropped, all operations on it will fail."
Extracted Contract (UC-002):
  - Statement: "Dropped collections must reject all subsequent operations"
  - Type: Universal
  - Violation: Operation succeeds on dropped collection
```

#### API Analysis

**Process**:
1. Parse API signatures
2. Identify parameter types and constraints
3. Extract type contracts
4. Infer validation requirements

**Example**:
```
API: create_collection(name: str, dimension: int)
Extracted Contracts:
  - OP-001: dimension must be positive integer
  - OP-002: name must be non-empty string
```

#### Behavioral Observation

**Process**:
1. Execute tests
2. Observe behavior patterns
3. Identify invariants
4. Formalize as empirical contracts

**Example**:
```
Observation: Repeated delete on same ID always succeeds
Extracted Contract (SS-003):
  - Statement: "Delete operations are idempotent"
  - Type: Sequence/State
  - Violation: Inconsistent behavior on repeated delete
```

### Output: Candidate Contracts

```json
{
  "candidate_contracts": [
    {
      "id": "CC-001",
      "source": "documentation",
      "statement": "Dropped collections reject all operations",
      "confidence": "high",
      "type_candidate": "universal"
    }
  ]
}
```

---

## Stage 2: Contract Normalization

**Purpose**: Transform candidate contracts into formal, machine-readable specifications.

### Normalization Steps

#### 1. Classification

Classify contract by type:
- Universal vs. Database-Specific
- Operation-Level vs. Sequence vs. Result

#### 2. Formalization

Express contract in formal language:
```json
{
  "contract_id": "UC-002",
  "type": "universal",
  "statement": "Dropped collections must reject all subsequent operations",
  "preconditions": ["collection_dropped"],
  "postconditions": ["operation_fails"],
  "violation_criteria": {
    "condition": "operation_succeeds AND collection_dropped",
    "severity": "critical"
  }
}
```

#### 3. Validation

Validate contract:
- Is it testable?
- Is violation detectable?
- Is scope clear?

#### 4. Cross-Reference

Link related contracts:
```json
{
  "related_contracts": ["UC-001", "SS-001"]
}
```

### Output: Formal Contracts

```json
{
  "formal_contracts": [
    {
      "contract_id": "UC-002",
      "type": "universal",
      "statement": "...",
      "preconditions": [...],
      "postconditions": [...],
      "violation_criteria": {...},
      "test_generation_rules": {...},
      "oracle": {...}
    }
  ]
}
```

---

## Stage 3: Test Case Generation

**Purpose**: Generate test cases from formal contracts.

### Generation Strategies

#### Legal Case Generation

**Purpose**: Validate compliant behavior.

**Process**:
```
For each contract:
  1. Satisfy all preconditions
  2. Execute operation
  3. Verify postconditions
  4. Generate test case
```

**Example**:
```
Contract: UC-002 (Post-Drop Rejection)
Legal Case:
  1. Create collection
  2. Insert data
  3. Search (baseline)
  4. Drop collection
  5. Search → EXPECTED: Error
```

#### Illegal Case Generation

**Purpose**: Validate violation detection.

**Process**:
```
For each contract:
  1. Satisfy preconditions
  2. Violate constraint
  3. Execute operation
  4. Verify error/exception
  5. Generate test case
```

**Example**:
```
Contract: OP-001 (Dimension Validation)
Illegal Case:
  1. Create collection with dimension = 0
  2. EXPECTED: Error "dimension must be positive"
```

#### Boundary Case Generation

**Purpose**: Test edge conditions.

**Process**:
```
For each parameter constraint:
  1. Identify min/max values
  2. Generate test at min
  3. Generate test at max
  4. Generate test just outside bounds
```

**Example**:
```
Contract: OP-001 (Dimension in [1, 32768])
Boundary Cases:
  - dimension = 1 (min valid)
  - dimension = 32768 (max valid)
  - dimension = 0 (invalid, below min)
  - dimension = 32769 (invalid, above max)
```

#### State-Dependent Generation

**Purpose**: Test sequences and state transitions.

**Process**:
```
For state contracts:
  1. Define state machine
  2. Identify valid transitions
  3. Generate sequences for each transition
  4. Generate sequences for invalid transitions
```

**Example**:
```
Contract: SS-001 (Collection Prerequisite)
State Cases:
  - Valid: create → insert → search
  - Invalid: insert (no collection created)
  - Invalid: create → drop → search
```

### Output: Test Suite

```json
{
  "test_suite": {
    "suite_id": "TS-001",
    "contracts": ["UC-002", "OP-001", "SS-001"],
    "test_cases": [
      {
        "test_id": "TC-001",
        "contract_id": "UC-002",
        "strategy": "legal",
        "description": "Post-drop rejection",
        "steps": [...],
        "expected_outcome": "error",
        "oracle": {...}
      }
    ]
  }
}
```

---

## Stage 4: Test Execution

**Purpose**: Execute test suite and capture raw results.

### Execution Process

#### 1. Environment Setup

```
For each database in scope:
  1. Start database (if needed)
  2. Verify connectivity
  3. Initialize adapter
  4. Capture environment snapshot
```

#### 2. Test Execution

```
For each test case:
  1. Execute steps sequentially
  2. Capture result at each step
  3. Capture state (if applicable)
  4. Handle exceptions
  5. Store raw results
```

#### 3. Result Capture

```json
{
  "execution_result": {
    "test_id": "TC-001",
    "database": "milvus",
    "timestamp": "2026-03-09T22:00:00Z",
    "steps": [
      {
        "step": 1,
        "operation": "create_collection",
        "status": "success",
        "data": {...},
        "error": null
      },
      {
        "step": 5,
        "operation": "search",
        "status": "error",
        "data": {},
        "error": "collection not exist"
      }
    ]
  }
}
```

### Output: Raw Results

```json
{
  "raw_results": {
    "suite_id": "TS-001",
    "database": "milvus",
    "results": [...],
    "summary": {
      "total": 10,
      "passed": 8,
      "failed": 2,
      "errors": 0
    }
  }
}
```

---

## Stage 5: Correctness Judgment

**Purpose**: Apply oracle to classify behavior as compliant or violating.

### Oracle Application

#### 1. Extract Test Step Result

```python
# Get the critical test step
test_step = 5  # Post-drop search
result = execution_result["steps"][test_step - 1]
```

#### 2. Apply Oracle Rules

```python
# Check violation criteria
if contract.violation_criteria.matches(result):
    classification = "CONTRACT_VIOLATION"
else:
    classification = "CONTRACT_COMPLIANT"
```

#### 3. Consider Context

```python
# Check for architectural differences
if is_database_specific(contract):
    if is_implementation_difference(result):
        classification = "ALLOWED_DIFFERENCE"
```

### Classification Categories

| Category | Oracle Logic | Example |
|----------|--------------|---------|
| **CONTRACT_COMPLIANT** | All postconditions satisfied | Post-drop search fails correctly |
| **CONTRACT_VIOLATION** | Postcondition violated | Post-drop search succeeds (BUG) |
| **ALLOWED_DIFFERENCE** | Database-specific variation | Milvus requires load, Qdrant doesn't |
| **UNDEFINED** | No clear contract | Empty collection search behavior |

### Output: Classified Findings

```json
{
  "classified_finding": {
    "test_id": "TC-001",
    "contract_id": "UC-002",
    "classification": "CONTRACT_COMPLIANT",
    "confidence": "high",
    "evidence": {
      "expected": "error",
      "observed": "error",
      "error_message": "collection not exist"
    },
    "reasoning": "Database correctly fails search on dropped collection"
  }
}
```

---

## Stage 6: Bug / Non-Bug Classification

**Purpose**: Categorize findings and assess severity.

### Classification Framework

#### Primary Classification

```
Is this a contract violation?
├─ YES → Is it a universal contract?
│   ├─ YES → BUG (Critical)
│   └─ NO → Is it within the specific database's contract?
│       ├─ YES → BUG (for that database)
│       └─ NO → ALLOWED DIFFERENCE (architectural)
└─ NO → Is behavior defined?
    ├─ YES → CONTRACT_COMPLIANT (PASS)
    └─ NO → OBSERVATION (undefined)
```

#### Severity Assessment

| Factor | Levels | Weight |
|--------|--------|--------|
| **Contract Type** | Universal > Specific | High |
| **Impact** | Data loss > Crash > Incorrect > Annoyance | High |
| **Scope** | Widespread > Isolated | Medium |
| **Reproducibility** | Always > Sometimes | Medium |

### Triage Categories

| Category | Criteria | Action |
|----------|----------|--------|
| **CRITICAL BUG** | Universal contract violation, data impact | Immediate attention |
| **HIGH BUG** | Specific contract violation, high impact | Prioritize fix |
| **MEDIUM BUG** | Contract violation, medium impact | Schedule fix |
| **LOW BUG** | Minor contract violation | Backlog |
| **ALLOWED DIFFERENCE** | Architectural variation | Document only |
| **OBSERVATION** | Undefined behavior | Document only |

### Output: Triage Report

```json
{
  "triage_report": {
    "finding_id": "F-001",
    "classification": "BUG",
    "severity": "CRITICAL",
    "category": "CONTRACT_VIOLATION",
    "contract_id": "UC-002",
    "title": "Database allows search after collection drop",
    "description": "Post-drop search succeeds when it should fail",
    "impact": "Data integrity violation - deleted data may be accessible",
    "reproduction": "...",
    "evidence": [...],
    "recommended_action": "Immediate fix required"
  }
}
```

---

## Stage 7: Reconfirmation & Regression Packaging

**Purpose**: Validate findings and create regression test packs.

### Reconfirmation Process

#### 1. Independent Verification

```
For each BUG finding:
  1. Create minimal reproduction case
  2. Execute on fresh environment
  3. Verify violation still occurs
  4. Confirm not a test artifact
```

#### 2. Cross-Database Validation

```
For universal contract violations:
  1. Test on multiple databases
  2. Confirm violation is specific to one database
  3. Rule out framework issues
```

#### 3. Documentation Check

```
For each finding:
  1. Check documentation
  2. Confirm behavior is undocumented
  3. Classify as bug or documentation issue
```

### Regression Pack Creation

#### 1. Select Regression Cases

```
For each confirmed bug:
  1. Extract minimal reproduction
  2. Add to regression suite
  3. Document expected behavior
  4. Add to CI/CD pipeline
```

#### 2. Pack Structure

```json
{
  "regression_pack": {
    "pack_id": "RP-001",
    "version": "1.0",
    "date": "2026-03-09",
    "bugs_covered": ["F-001", "F-002", "F-003"],
    "test_cases": [
      {
        "test_id": "REG-001",
        "bug_id": "F-001",
        "description": "Post-drop rejection regression test",
        "steps": [...],
        "expected_outcome": "error",
        "oracle": {...}
      }
    ],
    "execution_instructions": {
      "databases": ["milvus"],
      "environment": "real",
      "frequency": "every commit"
    }
  }
}
```

### Output: Regression Pack

```
regression-packs/
├── RP-001_post_drop_rejection.json
├── RP-002_deleted_entity_visibility.json
├── RP-003_delete_idempotency.json
└── README.md
```

---

## Iterative Feedback Loops

### Contract Refinement Loop

```
Observed Behavior → Contract Extraction → Contract Validation
     ↑                                              ↓
     └────────────── Contract Refinement ←──────────┘
```

**Trigger**: New behavior patterns observed
**Action**: Update or create contracts
**Impact**: New test cases generated

### Oracle Refinement Loop

```
Correctness Judgment → Classification Review → Oracle Update
     ↑                                              ↓
     └─────────────── Misclassification ←───────────┘
```

**Trigger**: Consistent misclassifications
**Action**: Refine oracle rules
**Impact**: Re-classify historical findings

### Test Suite Evolution Loop

```
Test Execution → Bug Discovery → Regression Test → Suite Update
     ↑                                              ↓
     └───────────────── New Test Cases ←─────────────┘
```

**Trigger**: New bugs discovered
**Action**: Add regression tests
**Impact**: Growing regression suite

---

## Workflow Metadata

- **Document**: Contract-Driven Test Generation Workflow
- **Version**: 1.0
- **Date**: 2026-03-09
- **Stages**: 7 (Extract, Normalize, Generate, Execute, Judge, Classify, Package)
- **Input Sources**: 4 (Documentation, APIs, Standards, Observation)
- **Output Types**: 4 (Contracts, Test Suites, Findings, Regression Packs)

---

**END OF CONTRACT-DRIVEN TEST GENERATION WORKFLOW**

This workflow defines the complete process from contract discovery to regression packaging. For framework architecture and contract definitions, see:
- `docs/CONTRACT_DRIVEN_FRAMEWORK_DESIGN.md`
- `docs/CONTRACT_MODEL.md`
