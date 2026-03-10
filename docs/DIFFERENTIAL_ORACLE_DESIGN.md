# Differential Oracle Design

**Document Version**: 1.0
**Date**: 2026-03-09
**Purpose**: Define classification criteria for cross-database behavioral differences

---

## Executive Summary

This document defines the **differential oracle** - a framework for classifying behavioral differences between vector databases as **bugs**, **allowed differences**, or **undefined behavior**. The oracle ensures that R4 differential testing can produce meaningful, actionable results rather than cataloging trivial differences.

---

## Core Concepts

### Differential Testing Context

**Definition**: Testing the same operations across multiple databases to identify behavioral differences

**Challenge**: Not all differences are bugs - some reflect legitimate architectural or design choices

**Oracle Purpose**: Classify differences into meaningful categories:
- **Contract Violation**: True bug - violates accepted semantic contract
- **Allowed Difference**: Legitimate implementation variation
- **Undefined Behavior**: Behavior not specified by any standard

---

## Classification Framework

### Category 1: Contract Violation (BUG)

**Definition**: Behavior that violates universally accepted semantic contracts for vector databases

**Principle**: If reasonable users would expect consistent behavior, inconsistency is a bug.

#### Subcategory 1.1: Data Integrity Violations

**Violation Types**:

| Behavior | Contract | Violation Example |
|----------|----------|-------------------|
| **Deleted entity visibility** | Deleted entities must not appear in search results | Database A: Deleted entity disappears ✅<br>Database B: Deleted entity still appears ❌ **BUG in B** |
| **Insert durability** | Inserted data must persist across operations | Database A: Insert persists ✅<br>Database B: Insert lost on restart ❌ **BUG** |
| **Update consistency** | Updates must be visible to subsequent reads | Database A: Update visible ✅<br>Database B: Update not visible ❌ **BUG** |

**Oracle Rule**: **ANY database that shows deleted data in search results violates semantic contract**

---

#### Subcategory 1.2: Idempotency Violations

**Violation Types**:

| Operation | Contract | Violation Example |
|------------|----------|-------------------|
| **Duplicate delete** | Calling delete twice on same ID should have same effect | Database A: Second delete succeeds ✅<br>Database B: Second delete errors inconsistently ❌ **POTENTIAL BUG** |
| **Duplicate creation** | Creating same collection twice should be deterministic | Database A: Second create succeeds ✅<br>Database B: Second create fails randomly ❌ **POTENTIAL BUG** |

**Oracle Rule**: **Idempotent operations should behave consistently on repeated calls**

**Nuance**: "Deterministic" means either always succeeds or always fails - not random

---

#### Subcategory 1.3: State Inconsistency

**Violation Types**:

| State Transition | Contract | Violation Example |
|-----------------|----------|-------------------|
| **Post-drop rejection** | Operations on dropped collection must fail | Database A: Post-drop search fails ✅<br>Database B: Post-drop search succeeds ❌ **BUG in B** |
| **Non-existent operations** | Operations on non-existent entities must fail | Database A: Insert to non-existent collection fails ✅<br>Database B: Succeeds silently ❌ **BUG in B** |

**Oracle Rule**: **Dropped collections and non-existent entities must be consistently rejected**

---

### Category 2: Allowed Implementation Differences (NOT BUGS)

**Definition**: Behaviors that may legitimately differ due to architectural or design choices

#### Subcategory 2.1: State Management Requirements

**Allowed Differences**:

| Behavior | Milvus | Qdrant | Oracle Rule |
|----------|--------|--------|-------------|
| **Load requirement** | Must load before search | May not require load | **ALLOWED** - Architectural difference |
| **Index requirement** | Must create index before load | May auto-create index | **ALLOWED** - Different indexing strategy |
| **Collection loading** | Explicit load() call | May load automatically | **ALLOWED** - Different memory management |

**Oracle Rule**: **Different state management approaches are ALLOWED if documented**

**Key Insight**: Requiring load vs. auto-loading are different design choices, not bugs.

---

#### Subcategory 2.2: Error Message Wording

**Allowed Differences**:

| Error Type | Milvus | Qdrant | Oracle Rule |
|------------|--------|--------|-------------|
| **Collection not found** | "Collection not exist" | "Collection not found" | **ALLOWED** - Wording difference |
| **Invalid dimension** | "invalid dimension" | "dimension out of range" | **ALLOWED** - Same meaning, different phrasing |

**Oracle Rule**: **Error message wording differences are ALLOWED if semantic meaning is preserved**

---

#### Subcategory 2.3: Operational Semantics

**Allowed Differences**:

| Operation | Milvus | Qdrant | Oracle Rule |
|------------|--------|--------|-------------|
| **Search without index** | Fails (not loaded) | May succeed (auto-index) | **ALLOWED** - Different search strategy |
| **Empty collection** | Requires load | May succeed without load | **ALLOWED** - Different handling |
| **Collection naming** | Case-sensitive? | Case-insensitive? | **ALLOWED** - Different conventions |

**Oracle Rule**: **Operational semantics may differ if architectural approach differs**

---

### Category 3: Undefined Behavior (NEITHER BUG NOR DIFFERENCE)

**Definition**: Behavior not specified by any standard or reasonable expectation

#### Subcategory 3.1: Ambiguous Edge Cases

**Undefined Behaviors**:

| Edge Case | Oracle Rule |
|------------|-------------|
| **Delete from empty collection** | **UNDEFINED** - Not specified, not clearly expected |
| **Search with zero top_k** | **UNDEFINED** - May error or return empty (both reasonable) |
| **Insert with mixed dimensions** | **UNDEFINED** - May reject or partition |

**Oracle Rule**: **For truly undefined behaviors, do not classify as bugs - document as implementation-specific**

---

#### Subcategory 3.2: Performance Characteristics

**Out of Scope**:

| Aspect | Oracle Rule |
|--------|-------------|
| **Query speed** | **UNDEFINED** - Performance is not a correctness concern |
| **Memory usage** | **UNDEFINED** - Different memory strategies are allowed |
| **Throughput** | **UNDEFINED** - Performance optimizations vary |

**Oracle Rule**: **Performance differences are NOT bugs (unless contracts specify SLAs)**

---

## Specific Oracle Rules by Behavior

### Rule 1: Search After Drop

**Contract**: Dropped collection must reject subsequent operations

**Expected Behavior**: Operation must fail with clear error

**Classification**:
- ✅ **PASS**: Both databases fail with error
- ❌ **BUG**: One database allows operation on dropped collection
- ⚠️ **ALLOWED**: Different error messages (same meaning)

---

### Rule 2: Deleted Entity Visibility

**Contract**: Deleted entities must not appear in subsequent search results

**Expected Behavior**: Search results must not contain deleted entities

**Classification**:
- ✅ **PASS**: Both databases exclude deleted entities
- ❌ **BUG**: One database includes deleted entities in results
- ⚠️ **ALLOWED**: Different handling of "tombstone" records (if documented)

---

### Rule 3: Search Without Index

**Contract**: UNDEFINED (architectural choice)

**Expected Behavior**: May succeed or fail depending on implementation

**Classification**:
- ✅ **PASS**: Both databases behave consistently (both fail or both succeed)
- ⚠️ **ALLOWED**: One fails (requires load), one succeeds (auto-index)
- ❌ **BUG**: Neither classification - this is allowed difference

---

### Rule 4: Delete Idempotency

**Contract**: Idempotent operations must have consistent, deterministic behavior

**Expected Behavior**: Repeated calls should have same effect

**Classification**:
- ✅ **PASS**: Both databases allow repeated delete
- ✅ **PASS**: Both databases reject repeated delete
- ❌ **BUG**: One database behaves inconsistently (random behavior)

---

### Rule 5: Empty Collection Search

**Contract**: UNDEFINED (edge case, not commonly specified)

**Expected Behavior**: May return empty, error, or auto-create index

**Classification**:
- ⚠️ **ALLOWED**: Any behavior is acceptable
- ⚠️ **ALLOWED**: Different behaviors between databases
- ❌ **BUG**: Neither classification - this is allowed difference

---

### Rule 6: Collection Creation Idempotency

**Contract**: UNDEFINED (API design choice)

**Expected Behavior**: May allow or reject duplicate collection creation

**Classification**:
- ✅ **PASS**: Both databases allow duplicates
- ✅ **PASS**: Both databases reject duplicates
- ⚠️ **ALLOWED**: Different approaches (not bugs)

---

### Rule 7: Load Requirement

**Contract**: UNDEFINED (architectural choice)

**Expected Behavior**: May require explicit load or auto-load

**Classification**:
- ⚠️ **ALLOWED**: One requires load, other doesn't
- ✅ **PASS**: Both have same requirement
- ❌ **BUG**: Neither classification - this is allowed difference

---

## Decision Framework

### How to Classify a Difference

**Step 1**: Is there a clear semantic contract?

- **YES** → Go to Step 2
- **NO** → UNDEFINED (allowed difference)

**Step 2**: Does the behavior violate the contract?

- **YES** → BUG (contract violation)
- **NO** → Go to Step 3

**Step 3**: Is the difference in implementation approach?

- **YES** → ALLOWED DIFFERENCE
- **NO** → Go to Step 4

**Step 4**: Is the behavior clearly specified?

- **YES** → Check if consistent with spec
- **NO** → UNDEFINED

---

## Examples: Applying the Oracle

### Example 1: Post-Drop Search

**Scenario**: Database A allows search after drop, Database B rejects it

**Oracle Analysis**:
1. Contract: Dropped collections should not be accessible
2. Database A violates contract → **BUG in Database A**

**Classification**: BUG (Contract Violation)

---

### Example 2: Search Without Load

**Scenario**: Database A requires load, Database B auto-loads

**Oracle Analysis**:
1. Contract: UNDEFINED (no standard requires load)
2. Both approaches are valid architectural choices
3. Different implementations → **ALLOWED DIFFERENCE**

**Classification**: ALLOWED DIFFERENCE (Architectural Choice)

---

### Example 3: Deleted Entity Visibility

**Scenario**: Database A shows deleted entity, Database B doesn't

**Oracle Analysis**:
1. Contract: Deleted data must not be visible
2. Database A violates contract → **BUG in Database A**

**Classification**: BUG (Data Integrity Violation)

---

### Example 4: Error Message Wording

**Scenario**: Database A: "Collection not exist", Database B: "Collection not found"

**Oracle Analysis**:
1. Contract: Error should communicate collection doesn't exist
2. Both messages communicate the same meaning
3. Different wording → **ALLOWED DIFFERENCE**

**Classification**: ALLOWED DIFFERENCE (Wording)

---

## Implementation Guidelines

### For R4 Test Cases

Each R4 test case must specify:

1. **Semantic Property**: What is being tested
2. **Expected Cross-Database Behavior**: What is the contract
3. **Oracle Rule**: Which rule applies
4. **Classification Criteria**: How to interpret results

**Example**:

```yaml
test_case: r4-drop-rejection
semantic_property: Post-drop state consistency
expected_behavior: All databases must reject operations on dropped collections
oracle_rule: Rule 1 (Search After Drop)
classification:
  - consistent_fail: PASS
  - one_succeeds: BUG
  - different_errors: ALLOWED (same meaning)
```

---

## Validation Checklist

For each differential finding, validate:

- [ ] Oracle rule clearly identified
- [ ] Contract/warranty clearly defined
- [ ] Classification criteria applied correctly
- [ ] Documentation supports oracle judgment
- [ ] No alternative interpretations are equally valid

---

## Summary Table

| Behavior | Contract | Difference | Bug | Allowed | Undefined |
|----------|----------|------------|-----|---------|-----------|
| **Post-drop rejection** | Must fail | One succeeds | YES | NO | NO |
| **Deleted entity visibility** | Must not appear | One appears | YES | NO | NO |
| **Search without load** | No standard | Different approaches | NO | YES | NO |
| **Delete idempotency** | Consistent | Different consistent behaviors | NO | YES | NO |
| **Empty collection search** | No standard | Any behavior | NO | YES | YES |
| **Error message wording** | Clear meaning | Different phrasing | NO | YES | NO |
| **Load requirement** | No standard | Different approaches | NO | YES | NO |

---

## Key Principles

### 1. Default to Conservative Classification

**When in doubt**, classify as:
- **ALLOWED DIFFERENCE** (if architectural choice)
- **UNDEFINED** (if truly unclear)
- **BUG** (only if clear contract violation)

### 2. Document Assumptions

**Before classifying**, document:
- What semantic contract applies
- Why it's a valid contract
- What evidence supports it
- What alternatives exist

### 3. Allow for Evolution

**Oracle can be refined** as:
- Industry standards emerge
- Best practices clarify
- Community consensus develops

---

## Metadata

- **Document**: Differential Oracle Design
- **Version**: 1.0
- **Date**: 2026-03-09
- **Purpose**: Define classification framework for R4 differential testing
- **Status**: Ready for application

---

**END OF DIFFERENTIAL ORACLE DESIGN**

**Next**: Use this oracle when implementing R4 differential testing.
