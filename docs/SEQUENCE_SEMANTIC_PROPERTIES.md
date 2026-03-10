# Sequence Semantic Properties

**Document Version**: 1.0
**Date**: 2026-03-09
**Purpose**: Define semantic properties to test across vector databases in R4

---

## Executive Summary

This document extracts the semantic properties tested in R3 and prepares them for cross-database testing in R4. Each property is defined with its contract, expected behavior, and differential oracle rule.

---

## Property Definition Framework

Each semantic property includes:

1. **Property Name**: Clear, descriptive name
2. **Contract Definition**: What universal semantic contract applies
3. **Expected Behavior**: What databases should do
4. **Test Method**: How to test the property
5. **Oracle Rule**: How to classify differences
6. **R3 Evidence**: What R3 revealed about Milvus

---

## Semantic Properties

### Property 1: Post-Drop Rejection

#### Definition

**Property Name**: Post-Drop Rejection

**Semantic Contract**: Collections, once dropped, must no longer exist and must reject all subsequent operations

**Rationale**: It violates data semantics for a dropped collection to be accessible or operable.

#### Expected Behavior

**When**: Database searches/operates on a dropped collection

**Must**: Fail with clear error indicating collection doesn't exist

**Error Types**: "Collection not found", "Collection doesn't exist", "Schema not ready"

**Must NOT**: Succeed, return stale data, or behave as if collection exists

#### Test Method

**Sequence**:
1. Create collection
2. Insert data
3. Search (validate it works before drop)
4. Drop collection
5. Search (TEST: should fail)

**Expected Results**:
- Step 5: FAIL with "not found" or similar error

#### Oracle Rule (Differential)

**From**: `DIFFERENTIAL_ORACLE_DESIGN.md`, Rule 1

**Classification**:
- ✅ **CONSISTENT**: Both databases fail (pass)
- ❌ **BUG**: One database allows post-drop operation
- ⚠️ **ALLOWED**: Different error messages (same semantic meaning)

#### R3 Evidence (Milvus)

**Behavior**: FAIL ✅ (correct behavior)

**Evidence**:
```
Step 5: search
Status: error
Error: SchemaNotReadyException: (code=1, message="Collection 'test_r3_seq004' not exist")
```

**Conclusion**: Milvus correctly enforces post-drop rejection contract

---

### Property 2: Deleted Entity Visibility

#### Definition

**Property Name**: Deleted Entity Visibility

**Semantic Contract**: Entities that have been explicitly deleted must not appear in subsequent search results

**Rationale**: Data integrity requires that deleted data is actually removed, not just marked as deleted.

#### Expected Behavior

**When**: Database searches after deleting specific entity IDs

**Must**: Exclude deleted entities from search results

**Allowed**:
- Return empty results (if no other entities match)
- Return other entities (if they match query)
- Return error (if search requires index/entity state)

**Must NOT**: Include deleted entities in results

#### Test Method

**Sequence**:
1. Create collection
2. Insert entity with known ID (e.g., ID=0)
3. Search (validate entity is visible)
4. Delete entity with ID=0
5. Search (TEST: deleted entity should not appear)

**Expected Results**:
- Step 5: Results should NOT contain deleted entity
- May contain other entities (if they exist and match)
- May error (if collection not loaded)

#### Oracle Rule (Differential)

**From**: `DIFFERENTIAL_ORACLE_DESIGN.md`, Rule 2

**Classification**:
- ✅ **CONSISTENT**: Both databases exclude deleted entities
- ❌ **BUG**: One database includes deleted entities in results
- ⚠️ **ALLOWED**: Different handling of tombstone records (if documented)

#### R3 Evidence (Milvus)

**Behavior**: Could not test (blocked by load requirement)

**Evidence**:
```
Step 3: search
Status: error
Error: collection not loaded
Step 5: search
Status: error
Error: collection not loaded
```

**Conclusion**: Test blocked by load requirement - property not validated

**Note**: Test design needs improvement (add load step) for R4

---

### Property 3: Delete Idempotency

#### Definition

**Property Name**: Delete Idempotency

**Semantic Contract**: Delete operations should be idempotent - calling delete multiple times on the same entity ID should have consistent, deterministic behavior

**Rationale**: Idempotency is a fundamental semantic property for distributed systems - users should be able to retry delete operations without side effects.

#### Expected Behavior

**When**: Database processes multiple delete calls for same entity ID

**Must**: Behave consistently (one of):
- **Option A**: All calls succeed (idempotent success)
- **Option B**: First call succeeds, subsequent calls fail with "not found"

**Acceptable**: Either option is valid, but database must be deterministic

**Must NOT**: Randomly succeed or fail

#### Test Method

**Sequence**:
1. Create collection
2. Insert entities with known IDs
3. Delete entity with ID=0 (first delete)
4. Delete entity with ID=0 (second delete - TEST)

**Expected Results**:
- Step 4: Succeeds (second delete succeeds) OR fails consistently with "not found"

**Oracle Rule (Differential)

**From**: `DIFFERENTIAL_ORACLE_DESIGN.md`, Rule 4

**Classification**:
- ✅ **CONSISTENT**: Both databases have same idempotency behavior
- ⚠️ **ALLOWED**: Different idempotency strategies (success vs. not found)
- ❌ **BUG**: Inconsistent behavior (random success/fail)

#### R3 Evidence (Milvus)

**Behavior**: SUCCESS (idempotent)

**Evidence**:
```
Step 4: delete(ids=[0])
Status: success
Step 5: delete(ids=[0])
Status: success
```

**Conclusion**: Milvus implements Option A (all deletes succeed)

---

### Property 4: Index-Independent Search

#### Definition

**Property Name**: Index-Independent Search

**Semantic Contract**: Search behavior should not depend on explicit index creation if the database can perform search without one

**Rationale**: Different databases have different indexing strategies - some require explicit indexes, others use brute force or automatic indexing.

#### Expected Behavior

**When**: Database searches collection without explicit index

**Must**: Either:
- **Option A**: Succeed (may use brute force or automatic index)
- **Option B**: Fail with clear error explaining index requirement

**Acceptable**: Both options are valid architectural choices

**Must NOT**: Succeed silently without indicating approach

#### Test Method

**Sequence**:
1. Create collection
2. Insert vectors
3. Search without explicit index (TEST)

**Expected Results**:
- Step 3: Success (auto-index or brute force) OR fail with clear error

**Oracle Rule (Differential)

**From**: `DIFFERENTIAL_ORACLE_DESIGN.md`, Rule 3

**Classification**:
- ✅ **CONSISTENT**: Both databases have same requirement
- ⚠️ **ALLOWED**: One requires index, other doesn't (architectural difference)
- ❌ **BUG**: Neither classification (allowed difference)

#### R3 Evidence (Milvus)

**Behavior**: Could not test (blocked by load requirement)

**Evidence**:
```
Step 3: search (no index)
Status: error
Error: collection not loaded
```

**Conclusion**: Test blocked by load requirement - property not validated

**Note**: Test design needs improvement for R4

---

### Property 5: Load-State Enforcement

#### Definition

**Property Name**: Load-State Enforcement

**Semantic Contract**: Collections may require explicit loading into memory before certain operations (typically search)

**Rationale**: Different databases use different memory management strategies - some require explicit load, others auto-load.

#### Expected Behavior

**When**: Database searches collection

**Must**: Either:
- **Option A**: Require explicit load before search (Milvus-style)
- **Option B**: Auto-load on first access

**Acceptable**: Both approaches are valid

**Must NOT**: Allow search when collection is unavailable (in any state)

#### Test Method

**Sequence**:
1. Create collection
2. Insert vectors
3. Search (TEST: should work or fail predictably)

**Expected Results**:
- Step 3: Success (auto-loaded) OR fail with clear "not loaded" error

**Oracle Rule (Differential)

**From**: `DIFFERENTIAL_ORACLE_DESIGN.md`, Rule 7

**Classification**:
- ✅ **CONSISTENT**: Both databases have same load requirement
- ⚠️ **ALLOWED**: One requires load, other auto-loads (architectural difference)
- ❌ **BUG**: Neither classification (allowed difference)

#### R3 Evidence (Milvus)

**Behavior**: Requires explicit load

**Evidence**:
```
Successful sequence: create → insert → build_index → load → search
Failed sequences (missing load): All search attempts failed
```

**Conclusion**: Milvus requires explicit load before search

---

### Property 6: Empty Collection Handling

#### Definition

**Property Name**: Empty Collection Handling

**Semantic Contract**: Database behavior for searching empty collections is not universally specified

**Rationale**: Empty collections are an edge case - different databases may handle them differently.

#### Expected Behavior

**When**: Database searches collection with no data

**May**:
- Return empty results
- Return error (with or without load)
- Auto-create index
- Require explicit load first

**Acceptable**: Any behavior is acceptable for this edge case

**Must Not**: Crash or behave inconsistently

#### Test Method

**Sequence**:
1. Create collection
2. Search (no data inserted, no index) (TEST)

**Expected Results**:
- Step 2: Any reasonable behavior (empty results, error, etc.)

**Oracle Rule (Differential)

**From**: `DIFFERENTIAL_ORACLE_DESIGN.md`, Rule 5

**Classification**:
- ⚠️ **ALLOWED**: Any behavior is acceptable
- ⚠️ **ALLOWED**: Different behaviors between databases
- ❌ **BUG**: Crash or inconsistent behavior

#### R3 Evidence (Milvus)

**Behavior**: Requires load even for empty collection

**Evidence**:
```
Step 2: search (empty collection)
Status: error
Error: collection not loaded
```

**Conclusion**: Milvus requires load regardless of collection content

---

### Property 7: Non-Existent Delete Tolerance

#### Definition

**Property Name**: Non-Existent Delete Tolerance

**Semantic Contract**: Deleting a non-existent entity ID should be handled gracefully

**Rationale**: In distributed systems, entities may not exist due to eventual consistency. Delete operations should handle this.

#### Expected Behavior

**When**: Database deletes entity ID that doesn't exist

**Must**: Behave deterministically (one of):
- **Option A**: Succeed silently (idempotent)
- **Option B**: Fail with clear "not found" error

**Acceptable**: Either option is valid

**Must NOT**: Behave inconsistently or fail with unclear error

#### Test Method

**Sequence**:
1. Create collection
2. Delete non-existent ID (TEST)

**Expected Results**:
- Step 2: Success OR fail with clear "not found"

**Oracle Rule (Differential)

**From**: `DIFFERENTIAL_ORACLE_DESIGN.md`, Rule 4 (idempotency extension)

**Classification**:
- ✅ **CONSISTENT**: Both databases handle consistently
- ⚠️ **ALLOWED**: Different approaches (silent vs. error)
- ❌ **BUG**: Inconsistent behavior

#### R3 Evidence (Milvus)

**Behavior**: Succeeds silently

**Evidence**:
```
Step 2: delete(ids=[999])  # Non-existent ID
Status: success
```

**Conclusion**: Milvus implements Option A (silent success)

---

### Property 8: Collection Creation Idempotency

#### Definition

**Property Name**: Collection Creation Idempotency

**Semantic Contract**: Creating a collection with an already-existing name should have deterministic behavior

**Rationale**: Different databases have different philosophies on duplicate collection names.

#### Expected Behavior

**When**: Database attempts to create collection with existing name

**Must**: Behave deterministically (one of):
- **Option A**: Allow duplicate (idempotent success)
- **Option B**: Reject with clear "already exists" error
- **Option C**: Update existing collection (if schema compatible)

**Acceptable**: Any deterministic approach is valid

**Must NOT**: Behave inconsistently

#### Test Method

**Sequence**:
1. Create collection with name "test"
2. Create collection with same name "test" (TEST)

**Expected Results**:
- Step 2: Success (allows duplicate) OR fail with "already exists"

**Oracle Rule (Differential)

**From**: `DIFFERENTIAL_ORACLE_DESIGN.md`, Rule 6

**Classification**:
- ✅ **CONSISTENT**: Both databases have same behavior
- ⚠️ **ALLOWED**: Different philosophies (allow vs. reject)
- ❌ **BUG**: Inconsistent behavior

#### R3 Evidence (Milvus)

**Behavior**: Allows duplicate creation

**Evidence**:
```
Step 3: create_collection(name="test_r3_cal002")  # Duplicate
Status: success
```

**Conclusion**: Milvus implements Option A (allows duplicates)

---

## Property Comparison Table

| Property | Contract | Milvus Behavior | Oracle Rule | Bug Classification |
|----------|----------|-----------------|-------------|-------------------|
| **Post-Drop Rejection** | Must fail | Fails correctly | Rule 1 | One that succeeds = BUG |
| **Deleted Entity Visibility** | Must not show | Not tested* | Rule 2 | One that shows = BUG |
| **Delete Idempotency** | Consistent | Consistent success | Rule 4 | Inconsistent = BUG |
| **Index-Independent Search** | No standard | Not tested* | Rule 3 | N/A (undefined) |
| **Load-State Enforcement** | No standard | Requires load | Rule 7 | N/A (undefined) |
| **Empty Collection** | No standard | Requires load | Rule 5 | N/A (undefined) |
| **Non-Existent Delete** | Graceful handling | Silent success | Rule 4 | Inconsistent = BUG |
| **Creation Idempotency** | Deterministic | Allows duplicate | Rule 6 | Inconsistent = BUG |

*Not tested due to load requirement blocking test

---

## Test Design Implications for R4

### Issues Identified in R3

**Problem**: Several R3 cases were blocked by Milvus's load requirement

**Affected Properties**:
- Deleted Entity Visibility (Property 2)
- Index-Independent Search (Property 4)
- Empty Collection Handling (Property 6)

**Root Cause**: R3 sequences didn't include load step, so search couldn't execute

### Solution for R4

**For Each Property**: Design sequence that satisfies both databases' requirements

**Example**: For Property 2 (Deleted Entity Visibility)

**R4 Sequence**:
```yaml
# Generic sequence (adapts to both databases)
1. create_collection
2. insert (vectors)
3. build_index (if required by database)
4. load (if required by database)
5. search (validate entity visible)
6. delete (specific entity)
7. search (TEST: deleted entity not visible)
8. drop_collection
```

**Adaptation Strategy**:
- **Milvus**: Steps 3-4 required
- **Qdrant**: May skip steps 3-4 if auto-index/auto-load

**Comparison Point**: Compare final search results (step 7)

---

## Classification Decision Tree

For each differential result, apply this decision tree:

```
Is there a clear semantic contract?
├─ NO → UNDEFINED (allowed difference)
└─ YES → Does behavior violate contract?
    ├─ YES → BUG (contract violation)
    └─ NO → Is it an implementation difference?
        ├─ YES → ALLOWED DIFFERENCE
        └─ NO → Check if specified
            ├─ Specified → Check consistency with spec
            └─ Not specified → UNDEFINED
```

---

## Research Value

### Why These Properties Matter

**1. Post-Drop Rejection**
- Critical for data integrity
- Prevents "zombie" collection references
- Tests memory management correctness

**2. Deleted Entity Visibility**
- Validates data deletion semantics
- Tests eventual consistency
- Critical for data integrity

**3. Delete Idempotency**
- Validates distributed system design
- Tests retry safety
- Important for automation

**4. Index-Independent Search**
- Tests indexing strategy flexibility
- May reveal architectural differences
- Important for ease of use

**5. Load-State Enforcement**
- Tests memory management approach
- May reveal architectural differences
- Important for performance characteristics

**6. Empty Collection Handling**
- Tests edge case behavior
- May reveal different design philosophies
- Important for robustness

**7. Non-Existent Delete Tolerance**
- Tests error handling robustness
- Tests eventual consistency handling
- Important for distributed systems

**8. Collection Creation Idempotency**
- Tests API design philosophy
- May reveal different approaches
- Important for developer experience

---

## Metadata

- **Document**: Sequence Semantic Properties
- **Version**: 1.0
- **Date**: 2026-03-09
- **Purpose**: Define testable properties for R4 cross-database testing
- **Properties Defined**: 8
- **Status**: Ready for R4 implementation

---

**END OF SEQUENCE SEMANTIC PROPERTIES**

**Next**: Use these properties to design R4 test cases with clear oracle rules.
