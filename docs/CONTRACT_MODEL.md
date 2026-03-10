# Contract Model

**Document Version**: 1.0
**Date**: 2026-03-09
**Scope**: Formal Definition of Contracts for AI-DB-QC Framework

---

## Executive Summary

This document defines what "contract" means in the AI-DB-QC framework. A contract is a formal specification of expected behavior that can be used to generate test cases and judge correctness. The framework recognizes five types of contracts, each with different scope, information content, and testing applications.

---

## Contract Definition

### What is a Contract?

A **contract** is a formal or informal specification of expected behavior that:

1. **Specifies constraints** on inputs, operations, or outputs
2. **Supports test generation** by defining legal and illegal scenarios
3. **Enables correctness judgment** by providing oracle criteria
4. **Has clear scope** (universal, database-specific, operation-level, etc.)

### Contract Components

Every contract in the framework contains:

| Component | Description | Example |
|-----------|-------------|---------|
| **Scope** | What the contract applies to | "All vector databases" |
| **Preconditions** | Required state before operation | "Collection must exist" |
| **Postconditions** | Required state after operation | "Entity must be inserted" |
| **Invariants** | Properties that must always hold | "Deleted entities never appear in search" |
| **Violation Criteria** | How to detect violations | "Search results contain deleted ID" |
| **Test Generation Rules** | How to generate tests | "Legal: search existing collection" |

---

## Five Contract Types

### 1. Strong Universal Contracts

**Definition**: Semantic invariants that should hold across ALL vector databases.

**Characteristics**:
- Derived from first principles of data management
- Independent of implementation details
- Violations indicate genuine bugs
- Form the basis for differential testing

**Examples**:

| Contract ID | Contract | Violation Condition |
|-------------|----------|---------------------|
| **UC-001** | Deleted entities must not appear in search results | Search returns deleted ID |
| **UC-002** | Dropped collections must reject all operations | Operation succeeds on dropped collection |
| **UC-003** | Idempotent operations must have consistent behavior | Same operation sometimes succeeds, sometimes fails |
| **UC-004** | Non-existent entities must be handled gracefully | Crash or undefined behavior |
| **UC-005** | Data must persist across operations | Inserted data disappears |

**Information Content**:
```json
{
  "contract_id": "UC-001",
  "name": "Deleted Entity Visibility",
  "type": "universal",
  "scope": "all_vector_databases",
  "statement": "Deleted entities must not appear in subsequent search results",
  "rationale": "Users expect delete operations to permanently remove data",
  "preconditions": ["Entity exists", "Entity has been deleted"],
  "postconditions": ["Entity not in search results"],
  "invariants": ["Delete is permanent"],
  "violation_criteria": {
    "condition": "deleted_entity_id IN search_result_ids",
    "severity": "critical"
  },
  "test_generation": {
    "legal_cases": [
      "Insert entity, delete it, search → entity not found"
    ],
    "illegal_cases": [
      "Insert entity, delete it, search → entity found (VIOLATION)"
    ]
  },
  "oracle": {
    "check": "NOT found(deleted_id, search_results)",
    "violation_classification": "BUG"
  }
}
```

**Test Generation**:
- **Legal Cases**: Normal operations following the contract
- **Illegal Cases**: Operations that would violate the contract (used for validation)
- **Cross-Database**: Execute on multiple databases, classify differences as bugs

**Correctness Judgment**:
- Any database violating a universal contract has a BUG
- No architectural exceptions allowed
- Clear binary classification: COMPLIANT or VIOLATION

---

### 2. Database-Specific Contracts

**Definition**: Implementation-specific guarantees that apply only to particular databases.

**Characteristics**:
- Derived from database documentation or observed behavior
- May differ across databases (these are ALLOWED DIFFERENCES)
- Violations indicate bugs within that specific database
- Important for portability understanding

**Examples**:

| Contract ID | Database | Contract | Violation Condition |
|-------------|----------|----------|---------------------|
| **MS-001** | Milvus | Collection must be loaded before search | Search succeeds without load |
| **MS-002** | Milvus | Index must be created before load | Load succeeds without index |
| **QD-001** | Qdrant | Collections with same name cannot be created | Duplicate creation succeeds |
| **QD-002** | Qdrant | Search returns empty results for empty collection | Search fails on empty collection |

**Information Content**:
```json
{
  "contract_id": "MS-001",
  "name": "Milvus Load Requirement",
  "type": "database_specific",
  "scope": "milvus_only",
  "database": "milvus",
  "statement": "Collections must be explicitly loaded before search operations",
  "rationale": "Milvus uses manual memory management for collections",
  "preconditions": ["Collection exists", "Collection NOT loaded"],
  "postconditions": ["Search operation fails with 'not loaded' error"],
  "invariants": ["Unloaded collections reject search"],
  "violation_criteria": {
    "condition": "search_succeeds AND collection_not_loaded",
    "severity": "medium"
  },
  "test_generation": {
    "legal_cases": [
      "Create collection, insert, load, search → success"
    ],
    "illegal_cases": [
      "Create collection, insert, search WITHOUT load → should fail (VIOLATION if succeeds)"
    ]
  },
  "oracle": {
    "check": "is_loaded(collection) OR search_fails",
    "violation_classification": "BUG (for Milvus)",
    "cross_database": "Allowed difference if other database doesn't require load"
  }
}
```

**Test Generation**:
- **Legal Cases**: Follow the database-specific requirements
- **Illegal Cases**: Violate requirements (to validate contract)
- **Cross-Database**: Compare against other databases (differences are ALLOWED)

**Correctness Judgment**:
- Within the specific database: COMPLIANT or VIOLATION
- Across databases: Differences are ALLOWED (architectural variation)

---

### 3. Operation-Level Contracts

**Definition**: Constraints on individual operation inputs and parameters.

**Characteristics**:
- Apply to single operations (not sequences)
- Specify valid parameter ranges, types, combinations
- Often derived from API signatures and documentation
- Used for parameter boundary testing

**Examples**:

| Contract ID | Operation | Contract | Violation Condition |
|-------------|-----------|----------|---------------------|
| **OP-001** | create_collection | Dimension must be positive integer | Dimension ≤ 0 |
| **OP-002** | create_collection | Dimension must be within supported range | Dimension > 32768 |
| **OP-003** | search | Top_K must be ≥ 0 | Top_K < 0 |
| **OP-004** | insert | Vector dimension must match collection dimension | Dimension mismatch |
| **OP-005** | delete | IDs must exist for deletion to have effect | Deleting non-existent ID has no effect |

**Information Content**:
```json
{
  "contract_id": "OP-001",
  "name": "Collection Dimension Validation",
  "type": "operation_level",
  "scope": "create_collection_operation",
  "operation": "create_collection",
  "statement": "Collection dimension must be a positive integer within supported range",
  "parameters": {
    "dimension": {
      "type": "integer",
      "min": 1,
      "max": 32768,
      "constraints": ["must_be_positive", "must_be_within_range"]
    }
  },
  "preconditions": ["dimension > 0", "dimension ≤ 32768"],
  "postconditions": ["Collection created with specified dimension"],
  "violation_criteria": {
    "condition": "dimension <= 0 OR dimension > 32768",
    "expected_outcome": "error with clear message",
    "severity": "medium"
  },
  "test_generation": {
    "legal_cases": [
      {"dimension": 1},
      {"dimension": 128},
      {"dimension": 32768}
    ],
    "illegal_cases": [
      {"dimension": 0, "expected": "error"},
      {"dimension": -1, "expected": "error"},
      {"dimension": 32769, "expected": "error"},
      {"dimension": "string", "expected": "error"}
    ],
    "boundary_cases": [
      {"dimension": 1, "description": "minimum valid"},
      {"dimension": 32768, "description": "maximum valid"}
    ]
  },
  "oracle": {
    "check": "dimension IN valid_range OR error_occurs",
    "violation_classification": "BUG if accepts invalid dimension"
  }
}
```

**Test Generation**:
- **Legal Cases**: Valid parameter values (including boundaries)
- **Illegal Cases**: Invalid parameter values (should be rejected)
- **Boundary Cases**: Min, max, and edge values

**Correctness Judgment**:
- Operation accepts invalid input: BUG
- Operation rejects invalid input with clear error: COMPLIANT
- Operation accepts valid input: COMPLIANT

---

### 4. Sequence/State Contracts

**Definition**: Constraints on valid operation sequences and state transitions.

**Characteristics**:
- Apply to sequences of operations (not single operations)
- Specify required operation ordering
- Define valid state transitions
- Used for state-transition testing

**Examples**:

| Contract ID | Contract | Violation Condition |
|-------------|----------|---------------------|
| **SS-001** | Collections must be created before operations | Operation succeeds on non-existent collection |
| **SS-002** | Load requires index | Load succeeds without index (Milvus) |
| **SS-003** | Delete is idempotent | Repeated delete has inconsistent behavior |
| **SS-004** | State transitions are deterministic | Same sequence has different outcomes |
| **SS-005** | Post-drop state is permanent | Operations succeed after drop |

**Information Content**:
```json
{
  "contract_id": "SS-001",
  "name": "Collection Creation Prerequisite",
  "type": "sequence_state",
  "scope": "all_operations_requiring_collection",
  "statement": "Collection must exist before any collection-specific operation",
  "rationale": "Operations must have a valid target collection",
  "state_machine": {
    "states": ["no_collection", "collection_created", "indexed", "loaded", "dropped"],
    "transitions": [
      {"from": "no_collection", "to": "collection_created", "operation": "create_collection"},
      {"from": "collection_created", "to": "dropped", "operation": "drop_collection"}
    ],
    "forbidden_transitions": [
      {"from": "no_collection", "operation": "insert"},
      {"from": "no_collection", "operation": "search"},
      {"from": "dropped", "operation": "search"}
    ]
  },
  "preconditions": {
    "insert": ["collection_exists"],
    "search": ["collection_exists"],
    "delete": ["collection_exists"],
    "drop": ["collection_exists"]
  },
  "postconditions": {
    "create_collection": ["collection_exists"],
    "drop_collection": ["collection_not_exists"]
  },
  "violation_criteria": {
    "condition": "operation_succeeds AND collection_not_exists",
    "expected_outcome": "error with 'collection not found'",
    "severity": "high"
  },
  "test_generation": {
    "legal_sequences": [
      ["create_collection", "insert", "search"],
      ["create_collection", "insert", "delete", "search"]
    ],
    "illegal_sequences": [
      ["insert"],  // No collection created
      ["search"],  // No collection created
      ["create_collection", "drop_collection", "search"]  // Search after drop
    ],
    "state_coverage": [
      "Test all valid state transitions",
      "Test all forbidden state transitions"
    ]
  },
  "oracle": {
    "check": "collection_exists OR operation_fails",
    "violation_classification": "BUG if operation succeeds without collection"
  }
}
```

**Test Generation**:
- **Legal Sequences**: Valid operation orderings
- **Illegal Sequences**: Invalid operation orderings (should fail)
- **State Coverage**: Cover all valid and invalid state transitions

**Correctness Judgment**:
- Forbidden sequence succeeds: BUG
- Required sequence fails: BUG
- Invalid state transition allowed: BUG

---

### 5. Result/Output Contracts

**Definition**: Constraints on operation output format and content.

**Characteristics**:
- Specify expected output structure
- Define content constraints (e.g., top_k results)
- Used for output validation
- Apply to both success and error cases

**Examples**:

| Contract ID | Operation | Contract | Violation Condition |
|-------------|-----------|----------|---------------------|
| **RS-001** | search | Returns ≤ top_k results | Returns > top_k results |
| **RS-002** | search | Results sorted by similarity | Results not sorted |
| **RS-003** | insert | Returns inserted entity IDs | No IDs returned |
| **RS-004** | create_collection | Returns success on valid creation | Returns error |
| **RS-005** | All operations | Error messages are descriptive | Error is unclear/misleading |

**Information Content**:
```json
{
  "contract_id": "RS-001",
  "name": "Search Result Count Limit",
  "type": "result_output",
  "scope": "search_operation",
  "operation": "search",
  "statement": "Search operation must return at most top_k results",
  "rationale": "top_k parameter limits result set size for performance and predictability",
  "output_schema": {
    "success": {
      "fields": ["results", "scores"],
      "constraints": [
        "length(results) <= top_k",
        "results sorted by score descending"
      ]
    },
    "error": {
      "fields": ["error_code", "error_message"],
      "constraints": [
        "error_message is descriptive",
        "error_code indicates failure reason"
      ]
    }
  },
  "preconditions": ["top_k >= 0"],
  "postconditions": ["result_count <= top_k"],
  "violation_criteria": {
    "condition": "length(search_results) > top_k",
    "severity": "high",
    "exceptions": ["top_k = 0 may return 0 results"]
  },
  "test_generation": {
    "legal_cases": [
      {"top_k": 10, "collection_size": 100, "expected": "10 results"},
      {"top_k": 10, "collection_size": 5, "expected": "5 results"},
      {"top_k": 0, "collection_size": 100, "expected": "0 results"}
    ],
    "illegal_cases": [
      {"top_k": 10, "expected": ">10 results (VIOLATION)"}
    ]
  },
  "oracle": {
    "check": "length(results) <= top_k",
    "violation_classification": "BUG if returns more than top_k"
  }
}
```

**Test Generation**:
- **Legal Cases**: Various input scenarios producing valid outputs
- **Boundary Cases**: Edge cases (top_k=0, top_k > collection size)
- **Format Validation**: Output structure matches schema

**Correctness Judgment**:
- Output violates constraint: BUG
- Output format invalid: BUG
- Error message unclear: USABILITY ISSUE

---

## Contract Taxonomy Summary

```
CONTRACTS
├── Strong Universal Contracts
│   ├── Deleted entity visibility
│   ├── Post-drop rejection
│   ├── Idempotency
│   ├── Data persistence
│   └── Error handling
├── Database-Specific Contracts
│   ├── Milvus load requirement
│   ├── Milvus index requirement
│   ├── Qdrant duplicate rejection
│   └── [database-specific state management]
├── Operation-Level Contracts
│   ├── Parameter validation
│   ├── Type checking
│   ├── Range constraints
│   └── Parameter dependencies
├── Sequence/State Contracts
│   ├── Creation prerequisites
│   ├── Operation ordering
│   ├── State transitions
│   └── Idempotency sequences
└── Result/Output Contracts
    ├── Result count limits
    ├── Result ordering
    ├── Return value formats
    └── Error message quality
```

---

## Contract Attributes

### Contract Strength

| Strength | Definition | Testing Implication |
|----------|------------|---------------------|
| **Strong** | Universal semantic invariant | Violations always bugs |
| **Medium** | Database-specific guarantee | Violations are bugs within database |
| **Weak** | Documentation-derived expectation | Violations may be documentation bugs |

### Contract Source

| Source | Reliability | Examples |
|--------|-------------|----------|
| **First Principles** | Highest | Data persistence, deletion visibility |
| **Industry Standards** | High | SQL-like behavior expectations |
| **Documentation** | Medium | Documented API contracts |
| **Observed Behavior** | Low | Empirically observed patterns |

### Contract Testability

| Testability | Characteristics | Examples |
|-------------|-----------------|----------|
| **High** | Clear violation criteria, easy to test | Parameter validation |
| **Medium** | Requires state setup, multi-step | State transitions |
| **Low** | Complex scenarios, subtle violations | Performance characteristics |

---

## Contract Usage Framework

### 1. Test Case Generation

For each contract, generate:

| Input Type | Purpose | Generation Strategy |
|------------|---------|---------------------|
| **Legal** | Validate compliant behavior | Satisfy all constraints |
| **Illegal** | Validate violation detection | Violate constraints intentionally |
| **Boundary** | Test edge cases | Min/max values, edge conditions |
| **Combinatorial** | Test constraint interactions | Multiple constraints together |

### 2. Correctness Judgment

For each contract, define:

| Component | Purpose | Example |
|-----------|---------|---------|
| **Violation Check** | Detect contract violations | `deleted_id IN results` |
| **Severity Assessment** | Prioritize findings | Critical vs. minor |
| **Classification Rules** | Categorize violations | BUG vs. ALLOWED vs. OBSERVATION |
| **Evidence Requirements** | Support triage decisions | Logs, traces, state snapshots |

### 3. Cross-Reference Mapping

Contracts can reference other contracts:

```json
{
  "contract_id": "SS-005",
  "depends_on": ["UC-002", "SS-001"],
  "rationale": "Post-drop rejection depends on collection existing and universal drop semantics"
}
```

---

## Contract Lifecycle

### 1. Contract Discovery

```
Sources (Documentation, APIs, Standards, Observation)
        ↓
Candidate Contract Identification
        ↓
Contract Formalization
        ↓
Contract Validation
        ↓
Accepted Contract
```

### 2. Contract Maintenance

```
Accepted Contract
        ↓
Monitor for Violations
        ↓
Analyze Violation Patterns
        ↓
Contract Update (if needed)
        ↓
Versioned Contract
```

### 3. Contract Deprecation

```
Contract
        ↓
Obsolete (API changed, database evolved)
        ↓
Deprecate Contract
        ↓
Archive with Historical Data
```

---

## Contract Metadata

- **Document**: Contract Model
- **Version**: 1.0
- **Date**: 2026-03-09
- **Contract Types**: 5 (Universal, Database-Specific, Operation-Level, Sequence/State, Result/Output)
- **Defined Contracts**: 20+ (examples across all types)

---

**END OF CONTRACT MODEL**

This document defines the formal foundation for contracts in the AI-DB-QC framework. For usage in test generation and workflow, see:
- `docs/CONTRACT_DRIVEN_TEST_GENERATION_WORKFLOW.md`
- `docs/CONTRACT_DRIVEN_FRAMEWORK_DESIGN.md`
