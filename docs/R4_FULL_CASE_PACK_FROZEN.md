# Full R4 Case Pack (Frozen)

**Version**: 1.0 (Frozen)
**Date**: 2026-03-09
**Status**: READY FOR EXECUTION
**Scope**: All 8 Semantic Properties

---

## Executive Summary

This document freezes the complete R4 test case pack consisting of 8 semantic properties to be tested across Milvus and Qdrant. Each property is classified by its testing priority and sensitivity to allowed implementation differences.

**Total Properties**: 8
**Primary Tests**: 5
**Allowed-Difference-Sensitive Tests**: 2
**Exploratory Tests**: 1

---

## Property Classification Matrix

| Property ID | Name | Category | Oracle Rule | Sensitivity |
|-------------|------|----------|-------------|-------------|
| **R4-001** | Post-Drop Rejection | PRIMARY | Rule 1 | None (bug if different) |
| **R4-002** | Deleted Entity Visibility | PRIMARY | Rule 2 | None (bug if different) |
| **R4-003** | Delete Idempotency | PRIMARY | Rule 4 | Low (strategies may differ) |
| **R4-004** | Index-Independent Search | ALLOWED-SENSITIVE | Rule 3 | High (architectural difference expected) |
| **R4-005** | Load-State Enforcement | ALLOWED-SENSITIVE | Rule 7 | High (architectural difference expected) |
| **R4-006** | Empty Collection Handling | EXPLORATORY | Rule 5 | Medium (edge case) |
| **R4-007** | Non-Existent Delete Tolerance | PRIMARY | Rule 4 | Low (strategies may differ) |
| **R4-008** | Collection Creation Idempotency | PRIMARY | Rule 6 | Low (philosophy may differ) |

---

## Category Definitions

### PRIMARY

**Definition**: Core semantic properties with clear contracts. Differences indicate bugs.

**Expected Outcome**: Both databases should behave identically.

**Failure Mode**: Any behavioral difference is a potential bug.

**Properties**: R4-001, R4-002, R4-003, R4-007, R4-008 (5 total)

---

### ALLOWED-SENSITIVE

**Definition**: Properties where architectural differences are expected and allowed.

**Expected Outcome**: Databases may behave differently due to legitimate design choices.

**Failure Mode**: Differences are classified as ALLOWED, not bugs.

**Properties**: R4-004, R4-005 (2 total)

**Expected Differences**:
- **R4-004** (Index-Independent Search): Milvus requires index, Qdrant auto-creates
- **R4-005** (Load-State Enforcement): Milvus requires load, Qdrant auto-loads

---

### EXPLORATORY

**Definition**: Edge cases or behaviors without clear standard specifications.

**Expected Outcome**: Any reasonable behavior is acceptable.

**Failure Mode**: Only crashes or inconsistency are bugs.

**Properties**: R4-006 (1 total)

---

## Detailed Property Specifications

### R4-001: Post-Drop Rejection (PRIMARY)

**Semantic Contract**: Collections, once dropped, must no longer exist and must reject all subsequent operations.

**Oracle Rule**: Rule 1 (Search After Drop)

**Test Sequence**:
```yaml
1. create_collection(name="r4_001", dimension=128)
2. insert(vectors=[[0.1]*128, [0.9]*128])
3. build_index()  # Optional: Milvus executes, Qdrant skips
4. load()         # Optional: Milvus executes, Qdrant skips
5. search(query_vector=[0.1]*128, top_k=10)  # Baseline
6. drop_collection(name="r4_001")
7. search(query_vector=[0.1]*128, top_k=10)  # TEST: must fail
```

**Expected**: Step 7 must fail with "not found" error on both databases.

**Bug Classification**: If one database allows post-drop search → BUG in that database

**Allowed Differences**: Different error message wording (same semantic meaning)

---

### R4-002: Deleted Entity Visibility (PRIMARY)

**Semantic Contract**: Entities that have been explicitly deleted must not appear in subsequent search results.

**Oracle Rule**: Rule 2 (Deleted Entity Visibility)

**Test Sequence**:
```yaml
1. create_collection(name="r4_002", dimension=128)
2. insert(vectors=[[0.1]*128, [0.5]*128, [0.9]*128], ids=[1, 2, 3])
3. build_index()  # Optional: Milvus executes, Qdrant skips
4. load()         # Optional: Milvus executes, Qdrant skips
5. search(query_vector=[0.1]*128, top_k=10)  # Verify entity 1 visible
6. delete(ids=[1])  # Delete entity 1
7. search(query_vector=[0.1]*128, top_k=10)  # TEST: entity 1 not visible
```

**Expected**: Step 7 results must NOT include deleted entity (ID=1).

**Bug Classification**: If one database includes deleted entity in results → BUG in that database

**Allowed Differences**: Different handling of tombstone records (if documented)

---

### R4-003: Delete Idempotency (PRIMARY)

**Semantic Contract**: Delete operations should be idempotent - calling delete multiple times on the same entity ID should have consistent, deterministic behavior.

**Oracle Rule**: Rule 4 (Delete Idempotency)

**Test Sequence**:
```yaml
1. create_collection(name="r4_003", dimension=128)
2. insert(vectors=[[0.1]*128], ids=[100])
3. build_index()  # Optional: Milvus executes, Qdrant skips
4. load()         # Optional: Milvus executes, Qdrant skips
5. delete(ids=[100])  # First delete
6. delete(ids=[100])  # TEST: Second delete - must be deterministic
```

**Expected**: Step 6 succeeds (all succeed strategy) OR fails with "not found" (first-succeeds-rest-fail), but must be consistent.

**Bug Classification**: Inconsistent behavior (random success/fail) → BUG

**Allowed Differences**: Different idempotency strategies (both-succeed vs. first-succeeds-rest-fail)

---

### R4-004: Index-Independent Search (ALLOWED-SENSITIVE)

**Semantic Contract**: Search behavior should not depend on explicit index creation if the database can perform search without one.

**Oracle Rule**: Rule 3 (Search Without Index)

**Test Sequence**:
```yaml
1. create_collection(name="r4_004", dimension=128)
2. insert(vectors=[[0.1]*128, [0.9]*128])
3. search(query_vector=[0.1]*128, top_k=10)  # TEST: search without explicit index
```

**Expected**: Step 3 may succeed (brute force/auto-index) OR fail with clear error, both are acceptable.

**Bug Classification**: Neither classification - this is an allowed difference

**Allowed Differences**: One requires index, other doesn't (architectural difference)

**Note**: Qdrant expected to succeed (auto-creates HNSW), Milvus may fail or succeed depending on implementation.

---

### R4-005: Load-State Enforcement (ALLOWED-SENSITIVE)

**Semantic Contract**: Collections may require explicit loading into memory before certain operations (typically search).

**Oracle Rule**: Rule 7 (Load Requirement)

**Test Sequence**:
```yaml
1. create_collection(name="r4_005", dimension=128)
2. insert(vectors=[[0.1]*128])
3. search(query_vector=[0.1]*128, top_k=10)  # TEST: reveals load requirement
```

**Expected**: Step 3 may succeed (auto-load) OR fail with clear "not loaded" error, both are acceptable.

**Bug Classification**: Neither classification - this is an allowed difference

**Allowed Differences**: One requires load, other auto-loads (architectural difference)

**Note**: Qdrant expected to succeed (auto-loads), Milvus expected to fail (requires explicit load).

---

### R4-006: Empty Collection Handling (EXPLORATORY)

**Semantic Contract**: Database behavior for searching empty collections is not universally specified (edge case).

**Oracle Rule**: Rule 5 (Empty Collection)

**Test Sequence**:
```yaml
1. create_collection(name="r4_006", dimension=128)
2. search(query_vector=[0.1]*128, top_k=10)  # TEST: empty collection search
```

**Expected**: Step 2 may return empty results, error, or auto-create index - any reasonable behavior is acceptable.

**Bug Classification**: Crash or inconsistent behavior → BUG

**Allowed Differences**: Any behavior is acceptable for this edge case

**Note**: Exploratory test to understand edge case handling across databases.

---

### R4-007: Non-Existent Delete Tolerance (PRIMARY)

**Semantic Contract**: Deleting a non-existent entity ID should be handled gracefully.

**Oracle Rule**: Rule 4 (Idempotency Extension)

**Test Sequence**:
```yaml
1. create_collection(name="r4_007", dimension=128)
2. delete(ids=[999])  # TEST: delete non-existent ID
```

**Expected**: Step 2 succeeds (silent) OR fails with clear "not found" error.

**Bug Classification**: Inconsistent behavior → BUG

**Allowed Differences**: Different approaches (silent vs. error)

**Note**: From R3, Milvus succeeds silently. Qdrant behavior to be validated.

---

### R4-008: Collection Creation Idempotency (PRIMARY)

**Semantic Contract**: Creating a collection with an already-existing name should have deterministic behavior.

**Oracle Rule**: Rule 6 (Creation Idempotency)

**Test Sequence**:
```yaml
1. create_collection(name="r4_008", dimension=128)
2. create_collection(name="r4_008", dimension=128)  # TEST: duplicate creation
```

**Expected**: Step 2 succeeds (allows duplicate) OR fails with "already exists" error.

**Bug Classification**: Inconsistent behavior → BUG

**Allowed Differences**: Different philosophies (allow vs. reject)

**Note**: From R3, Milvus allows duplicate creation. Qdrant behavior to be validated.

---

## Test Case Summary

| Case ID | Property | Category | Steps | Critical Step |
|---------|----------|----------|-------|---------------|
| **R4-001** | Post-Drop Rejection | PRIMARY | 7 | 7 (search after drop) |
| **R4-002** | Deleted Entity Visibility | PRIMARY | 7 | 7 (search after delete) |
| **R4-003** | Delete Idempotency | PRIMARY | 6 | 6 (second delete) |
| **R4-004** | Index-Independent Search | ALLOWED-SENSITIVE | 3 | 3 (search without index) |
| **R4-005** | Load-State Enforcement | ALLOWED-SENSITIVE | 3 | 3 (search without load) |
| **R4-006** | Empty Collection Handling | EXPLORATORY | 2 | 2 (search empty collection) |
| **R4-007** | Non-Existent Delete Tolerance | PRIMARY | 2 | 2 (delete non-existent) |
| **R4-008** | Collection Creation Idempotency | PRIMARY | 2 | 2 (duplicate creation) |

**Total Test Steps**: 32 (sum of all steps)

---

## Priority for Execution

### Tier 1 (Must Pass)

**Properties**: R4-001, R4-002, R4-007 (3 properties)

**Rationale**: These are critical data integrity properties where differences indicate bugs.

**Expected Outcome**: 100% CONSISTENT (bugs if different)

---

### Tier 2 (Primary - High Value)

**Properties**: R4-003, R4-008 (2 properties)

**Rationale**: Important API contract properties, though some strategies may differ.

**Expected Outcome**: CONSISTENT or ALLOWED DIFFERENCE (both acceptable)

---

### Tier 3 (Architectural Differences)

**Properties**: R4-004, R4-005 (2 properties)

**Rationale**: These will reveal architectural differences, which is expected and allowed.

**Expected Outcome**: ALLOWED DIFFERENCE (expected, not a bug)

---

### Tier 4 (Exploratory)

**Properties**: R4-006 (1 property)

**Rationale**: Edge case exploration to understand behavior consistency.

**Expected Outcome**: OBSERVATION (any reasonable behavior acceptable)

---

## Success Criteria

### Minimum Success

**Criteria**: All 8 properties execute successfully on both databases

**Expected**:
- All PRIMARY properties: CONSISTENT or ALLOWED DIFFERENCE
- All ALLOWED-SENSITIVE properties: Show expected differences
- EXPLORATORY properties: No crashes

### Stretch Success

**Criteria**: Clear behavioral catalog with meaningful classifications

**Expected**:
- All PRIMARY properties: 100% CONSISTENT
- ALLOWED-SENSITIVE properties: Documented architectural differences
- EXPLORATORY properties: Characterized edge case behaviors

---

## Adaptive Sequence Template

All R4 test cases use this adaptive sequence template:

```yaml
# Generic adaptive sequence (works on both databases)
1. create_collection(name="r4_XXX", dimension=128, metric_type="COSINE")
   - Milvus: Collection(name, schema)
   - Qdrant: create_collection(name, vectors_config)

2. insert(vectors)
   - Milvus: collection.insert([...])
   - Qdrant: client.upsert(name, points=[PointStruct...])
   - Note: Qdrant requires explicit IDs

3. build_index()  # OPTIONAL
   - Milvus: collection.create_index() (required)
   - Qdrant: SKIP (auto-creates HNSW)

4. load()         # OPTIONAL
   - Milvus: collection.load() (required)
   - Qdrant: SKIP (auto-loads)

5. [TEST STEP]
   - Property-specific test operation

# Additional steps as needed per property
```

**Adapter Implementation**:
- **Milvus**: Steps 3-4 required before search
- **Qdrant**: Steps 3-4 optional (no-op, returns success)

---

## Metadata

- **Document**: Full R4 Case Pack (Frozen)
- **Version**: 1.0
- **Date**: 2026-03-09
- **Total Properties**: 8
- **Status**: FROZEN - Ready for Execution
- **Next Step**: Execute full R4 campaign using this case pack

---

**END OF FULL R4 CASE PACK (FROZEN)**
