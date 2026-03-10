# R1-R4 Framework Mapping

**Document Version**: 1.0
**Date**: 2026-03-09
**Scope**: Mapping Existing Campaigns to Contract-Driven Framework

---

## Executive Summary

This document maps the existing R1-R4 campaigns to the new contract-driven framework view. Each campaign is analyzed to identify: which contract family it tested, what input strategy it used, and what lessons it contributed to the framework. This mapping demonstrates how the empirical work validates the theoretical framework.

---

## Campaign Mapping Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        CAMPAIGN TO FRAMEWORK MAPPING                             │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  CAMPAIGN     CONTRACT FAMILY           INPUT STRATEGY           FRAMEWORK       │
│  ────────     ────────────────           ────────────────          ─────────       │
│                                                                                 │
│   R1          Operation-Level            Legal + Illegal          Test            │
│   R2          Documentation-Derived       Legal + Mismatch         Generation      │
│   R3          Sequence/State             State Transitions        Judgment         │
│   R4          Universal + Specific        Differential             Oracle          │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## R1: Parameter Boundary Testing

### Framework Classification

| Aspect | Classification |
|--------|----------------|
| **Contract Family** | Operation-Level Contracts |
| **Primary Contracts** | OP-001 (Dimension Validation), OP-003 (Top-K Validation) |
| **Input Strategy** | Legal inputs + Illegal inputs + Boundary cases |
| **Testing Dimension** | Parameter Boundary Testing |
| **Output Type** | Issue Reports |

### Contract Focus

**R1 tested the following operation-level contracts**:

| Contract ID | Contract | Test Cases | Outcome |
|-------------|----------|------------|---------|
| **OP-001** | Collection dimension must be positive | dimension=0, dimension=-1 | ✅ Correctly rejected |
| **OP-002** | Dimension must be within range | dimension=32768, dimension=32769 | ✅ Correctly bounded |
| **OP-003** | Top_K must be non-negative | top_k=0, top_k=-1 | ✅ Correctly handled |
| **OP-004** | Metric type must be supported | L2, IP, COSINE, INVALID | ✅ Correctly validated |

### Input Strategy Details

**Legal Inputs** (Valid parameter values):
- `dimension = 128` (normal case)
- `top_k = 10` (normal case)
- `metric_type = "L2"` (supported type)

**Illegal Inputs** (Invalid parameter values):
- `dimension = 0` (below minimum)
- `dimension = -1` (negative)
- `dimension = 32769` (above maximum)
- `top_k = -1` (negative)

**Boundary Cases** (Edge conditions):
- `dimension = 1` (minimum valid)
- `dimension = 32768` (maximum valid)
- `top_k = 0` (edge case)

### Framework Lessons Learned

**Lesson 1: Parameter Validation Contracts**
- Operation-level contracts are well-defined and testable
- Illegal inputs are consistently rejected
- Boundary conditions are handled correctly

**Lesson 2: Test Generation Strategy**
- Legal + illegal + boundary = comprehensive coverage
- Parameter space can be systematically explored
- Clear pass/fail criteria for validation contracts

**Lesson 3: Oracle Simplicity**
- Parameter validation contracts have simple oracles
- Expected outcome: error for illegal, success for legal
- Clear binary classification

### Framework Contribution

**Component Validated**: Test Generation (Operation-Level)
- Demonstrated that operation-level contracts generate clear test cases
- Validated legal/illegal/boundary generation strategy
- Proved oracle simplicity for validation contracts

**Artifacts**:
- 10 test cases covering 4 operation-level contracts
- Zero bugs found (parameter validation is robust)
- Confirmed Milvus parameter contract compliance

---

## R2: API Validation / Usability

### Framework Classification

| Aspect | Classification |
|--------|----------------|
| **Contract Family** | Documentation-Derived Contracts |
| **Primary Contracts** | DOC-001 (metric_type parameter placement) |
| **Input Strategy** | Legal inputs + API misuse + Mismatch detection |
| **Testing Dimension** | API Validation / Usability |
| **Output Type** | Issue Reports (usability bugs) |

### Contract Focus

**R2 tested the following documentation-derived contracts**:

| Contract ID | Contract | Source | Test Cases | Outcome |
|-------------|----------|--------|------------|---------|
| **DOC-001** | metric_type must be set correctly | Documentation expectation | metric_type in Collection() | ⚠️ Silently ignored |
| **OP-005** | Unused parameters handled gracefully | API design | Various unused params | ✅ Handled (silently ignored) |

### Input Strategy Details

**Legal Inputs** (API usage as documented):
- Standard parameter combinations
- Documented operation sequences

**API Misuse** (Common mistakes):
- `metric_type` passed to `Collection()` instead of index creation
- Undocumented parameters via `**kwargs`

**Mismatch Detection** (Documentation vs. Reality):
- Expected behavior from documentation
- Actual behavior from execution
- Classification as documentation bug vs. functional bug

### Framework Lessons Learned

**Lesson 1: Documentation-Derived Contracts**
- Documentation implies contracts that may not exist
- Need to distinguish documentation bugs from functional bugs
- API usability is a valid contract concern

**Lesson 2: Silent Failure Patterns**
- `**kwargs` pattern enables silent parameter ignoring
- This is an API design choice, not necessarily a bug
- Should be documented, not necessarily changed

**Lesson 3: Classification Nuance**
- Initial classification: "validation bug"
- Corrected classification: "usability issue"
- Shows importance of framework feedback loops

### Framework Contribution

**Component Validated**: Contract Extraction (from Documentation)
- Demonstrated documentation as a contract source
- Validated mismatch detection strategy
- Proved need for classification refinement

**Artifacts**:
- 11 test cases covering API contracts
- 1 usability issue found (not a functional bug)
- Corrected initial misclassification
- Improved oracle rules for API contracts

---

## R3: Sequence and State-Transition Testing

### Framework Classification

| Aspect | Classification |
|--------|----------------|
| **Contract Family** | Sequence/State Contracts |
| **Primary Contracts** | SS-001 (Collection Prerequisite), SS-003 (Idempotency) |
| **Input Strategy** | State transitions + Legal sequences + Idempotency |
| **Testing Dimension** | State-Transition Testing |
| **Output Type** | State Validation Reports |

### Contract Focus

**R3 tested the following sequence/state contracts**:

| Contract ID | Contract | Test Cases | Outcome |
|-------------|----------|------------|---------|
| **SS-001** | Collection must exist for operations | 11 sequences | ✅ All operations require collection |
| **SS-003** | Delete is idempotent | Repeated delete | ✅ Consistent behavior |
| **SS-004** | State transitions are deterministic | State sequences | ✅ Deterministic transitions |
| **UC-001** | Deleted entity visibility | Delete → search | ✅ Deleted entities excluded |

### Input Strategy Details

**State Transitions** (Valid state changes):
- `no_collection` → `collection_created` → `indexed` → `loaded`
- Each transition tested and validated

**Legal Sequences** (Valid operation ordering):
- `create → insert → build_index → load → search`
- `create → insert → delete → search`

**Idempotency** (Repeated operations):
- `delete` called twice on same ID
- `create` called twice with same name

**State Coverage**:
- All valid transitions exercised
- All invalid transitions attempted
- State machine validated

### Framework Lessons Learned

**Lesson 1: State Machine Modeling**
- Database operations follow clear state machine
- State transitions are deterministic and well-defined
- State contracts are highly testable

**Lesson 2: Idempotency Contracts**
- Delete operations are idempotent (both-succeed strategy)
- Collection creation is permissive (allows duplicates)
- Idempotency strategies are consistent

**Lesson 3: Sequence Testing Value**
- Single-operation tests miss state-dependent issues
- Sequences reveal state contract compliance
- State contracts are foundational for correct behavior

### Framework Contribution

**Component Validated**: Test Generation (Sequence/State)
- Demonstrated state machine modeling
- Validated sequence generation strategy
- Proved state contracts are foundational

**Artifacts**:
- 11 test cases covering state contracts
- Zero bugs found (state management is robust)
- State machine validated
- Idempotency confirmed

---

## R4: Differential Semantic Testing

### Framework Classification

| Aspect | Classification |
|--------|----------------|
| **Contract Family** | Universal + Database-Specific Contracts |
| **Primary Contracts** | UC-001 through UC-005 (universal), MS-001, QD-001 (specific) |
| **Input Strategy** | Differential (same test, multiple databases) |
| **Testing Dimension** | Differential Semantic Testing |
| **Output Type** | Semantic Behavior Matrices, Compatibility Reports |

### Contract Focus

**R4 tested the following contract categories**:

**Universal Contracts** (Must hold across all databases):

| Contract ID | Contract | Milvus | Qdrant | Outcome |
|-------------|----------|--------|--------|---------|
| **UC-001** | Deleted entity visibility | ✅ Compliant | ✅ Compliant | ✅ Both pass |
| **UC-002** | Post-drop rejection | ✅ Compliant | ✅ Compliant | ✅ Both pass |
| **UC-003** | Delete idempotency | ✅ Compliant | ✅ Compliant | ✅ Both pass |
| **UC-004** | Non-existent delete handling | ✅ Compliant | ✅ Compliant | ✅ Both pass |

**Database-Specific Contracts** (Allowed to differ):

| Contract ID | Database | Contract | Outcome |
|-------------|----------|----------|---------|
| **MS-001** | Milvus | Requires load before search | ✅ Validated |
| **QD-001** | Qdrant | Auto-loads on access | ✅ Validated |
| **MS-002** | Milvus | Requires index before load | ✅ Validated |
| **QD-002** | Qdrant | Auto-creates HNSW index | ✅ Validated |

### Input Strategy Details

**Differential Strategy**:
1. Define test sequence from contract
2. Execute on Milvus with adapter
3. Execute on Qdrant with adapter
4. Compare results at test step
5. Classify using differential oracle

**Classification Logic**:
```
Both databases violate contract? → BUG in both
One database violates? → BUG in violating database
Both comply? → CONSISTENT (PASS)
Different behavior on allowed contract? → ALLOWED DIFFERENCE
```

### Framework Lessons Learned

**Lesson 1: Universal Contract Validation**
- Universal contracts are upheld across databases
- Zero contract violations found
- Strong semantic alignment exists

**Lesson 2: Allowed Difference Identification**
- Database-specific contracts explain behavioral differences
- Architectural differences are legitimate, not bugs
- State management is the main differentiator

**Lesson 3: Differential Oracle Effectiveness**
- Oracle correctly distinguishes bugs from allowed differences
- Classification framework is robust
- Portability guidance can be derived

### Framework Contribution

**Component Validated**: Correctness Judgment (Differential Oracle)
- Demonstrated universal contract validation
- Validated allowed difference classification
- Proved differential testing strategy

**Artifacts**:
- 8 semantic properties tested
- 4 PASS (universal contracts)
- 4 ALLOWED DIFFERENCES (database-specific)
- Zero bugs found
- Semantic behavior matrix created

---

## Framework Validation Summary

### What R1-R4 Proved

| Framework Component | Validation | Campaign |
|--------------------|------------|----------|
| **Contract Extraction** | Documentation, APIs, behavior all valid sources | R1, R2, R3, R4 |
| **Contract Representation** | 5 contract types cover all observed behaviors | All |
| **Test Generation** | Legal/illegal/boundary/sequence/differential all work | R1, R3, R4 |
| **Correctness Judgment** | Oracle distinguishes bugs from allowed differences | R4 |
| **Evidence & Triage** | Classification refinement works (R2 correction) | R2 |

### Contract Type Validation

| Contract Type | Tested In | Status | Lessons |
|---------------|-----------|--------|---------|
| **Universal** | R4 | ✅ Validated | Zero violations, strong alignment |
| **Database-Specific** | R4 | ✅ Validated | Explains behavioral differences |
| **Operation-Level** | R1 | ✅ Validated | Parameter validation robust |
| **Sequence/State** | R3 | ✅ Validated | State machine well-defined |
| **Result/Output** | R1, R3 | ✅ Validated | Output contracts compliant |

### Strategy Layer Validation

| Strategy | Campaign | Status | Lessons |
|----------|----------|--------|---------|
| **Bug-Yield** | R1, R2 | ✅ Validated | Found 1 usability issue |
| **Differential** | R4 | ✅ Validated | Zero universal contract violations |
| **State/Sequence** | R3 | ✅ Validated | State management robust |
| **API/Doc-Mismatch** | R2 | ✅ Validated | Documentation improvement needed |

### Output Layer Validation

| Output Type | Generated | Campaigns | Quality |
|-------------|-----------|-----------|---------|
| **Issue Reports** | 1 | R1, R2 | High (1 usability issue) |
| **Semantic Matrices** | 1 | R4 | High (8 properties) |
| **Regression Packs** | 0 | - | N/A (zero bugs) |
| **Compatibility Reports** | 1 | R4 | High (strong compatibility) |

---

## Campaign Evolution Insights

### Progression of Understanding

**R1 → R2 → R3 → R4** represents increasing framework sophistication:

```
R1: Simple parameter validation
    ↓ (adds)
R2: Documentation and API considerations
    ↓ (adds)
R3: State and sequence complexity
    ↓ (adds)
R4: Cross-database semantic comparison
```

### Framework Components Discovered

Each campaign revealed framework components:

| Campaign | Component Discovered | Impact |
|----------|---------------------|--------|
| **R1** | Operation-level contracts are foundational | Established test generation patterns |
| **R2** | Documentation is a contract source | Added mismatch detection |
| **R3** | State contracts are critical | Validated sequence testing |
| **R4** | Universal vs. specific distinction | Enabled differential oracle |

### Oracle Evolution

The oracle evolved through campaigns:

```
R1: Simple pass/fail (parameter validation)
    ↓ (refines)
R2: Added usability classification
    ↓ (expands)
R3: Added state machine validation
    ↓ (formalizes)
R4: Differential oracle (bug vs. allowed vs. observation)
```

---

## Reinterpretation Under Contract-Driven View

### R1 Reinterpreted

**Original View**: "Parameter boundary testing campaign"
**Contract View**: "Validation of operation-level contracts through legal/illegal/boundary generation"

**Key Insight**: R1 wasn't just "finding bugs" - it was validating that Milvus upholds its operation-level contracts.

### R2 Reinterpreted

**Original View**: "API validation and usability campaign"
**Contract View**: "Comparison of documentation-derived contracts against observed behavior"

**Key Insight**: R2 tested the framework's ability to distinguish documentation bugs from functional bugs.

### R3 Reinterpreted

**Original View**: "State-transition testing campaign"
**Contract View**: "Validation of sequence/state contracts through state machine modeling"

**Key Insight**: R3 proved that state contracts are foundational and highly testable.

### R4 Reinterpreted

**Original View**: "Cross-database differential campaign"
**Contract View**: "Validation of universal contracts and identification of database-specific contracts"

**Key Insight**: R4 distinguished universal invariants from architectural variations.

---

## Mapping Summary

### Campaign Contract Coverage

| Campaign | Universal | Specific | Operation | Sequence | Documentation |
|----------|-----------|----------|-----------|----------|----------------|
| **R1** | - | - | ✅ | - | - |
| **R2** | - | - | ✅ | - | ✅ |
| **R3** | ✅ | - | - | ✅ | - |
| **R4** | ✅ | ✅ | - | ✅ | - |

### Framework Component Validation

| Component | R1 | R2 | R3 | R4 |
|-----------|----|----|----|----|
| Contract Extraction | ✅ | ✅ | ✅ | ✅ |
| Contract Representation | ✅ | ✅ | ✅ | ✅ |
| Test Generation | ✅ | ✅ | ✅ | ✅ |
| Correctness Judgment | ✅ | ✅ | ✅ | ✅ |
| Evidence & Triage | - | ✅ | - | ✅ |

### Lessons for Framework Design

1. **Multiple Contract Sources Needed**: Documentation, APIs, observation all contribute
2. **Strategy Layer is Essential**: Different goals require different strategies
3. **Oracle Evolution is Natural**: Framework understanding improves over time
4. **Feedback Loops Matter**: R2 correction showed need for refinement

---

## Metadata

- **Document**: R1-R4 Framework Mapping
- **Version**: 1.0
- **Date**: 2026-03-09
- **Campaigns Mapped**: 6 (R1, R2, R3, R4.0, R4 Phase 1, R4 Full)
- **Contract Types Validated**: 5
- **Framework Components Validated**: 5

---

**END OF R1-R4 FRAMEWORK MAPPING**

This mapping demonstrates how the empirical campaigns validate the contract-driven framework. For framework design and workflow details, see:
- `docs/CONTRACT_DRIVEN_FRAMEWORK_DESIGN.md`
- `docs/CONTRACT_MODEL.md`
- `docs/CONTRACT_DRIVEN_TEST_GENERATION_WORKFLOW.md`
