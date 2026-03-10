# R5D Phase 1.5: P0 Executable Set Finalization

**Date**: 2026-03-10
**Phase**: 1.5 (P0 Finalization)
**Status**: COMPLETE
**Scope**: Multi-collection version comparison (not in-place schema mutation)

---

## A. Critical Clarification: Schema Evolution Scope

**IMPORTANT**: Due to Milvus SDK v2.6.10 limitations, **P0 evaluates schema evolution semantics via multi-collection version comparison, not in-place schema mutation.**

### A.1 What This Means

| Traditional Schema Evolution | R5D Approach (Multi-Collection) |
|------------------------------|---------------------------------|
| ALTER TABLE ADD COLUMN | CREATE collection_v2 with new field |
| Observe single collection before/after | Compare v1 vs v2 separately |
| Test in-place mutation effects | Test cross-version isolation |

### A.2 Operations NOT Supported (Confirmed)

```python
# These operations DO NOT EXIST in pymilvus SDK v2.6.10:
NOT_SUPPORTED_SCHEMA_OPERATIONS = {
    "alter_collection": "Not available in pymilvus SDK v2.6.10",
    "add_field": "Not available in pymilvus SDK v2.6.10",
    "drop_field": "Not available in pymilvus SDK v2.6.10",
    "rename_field": "Not available in pymilvus SDK v2.6.10"
}
```

### A.3 Workaround Strategy

**Multi-Collection Comparison**: Create separate collections (v1, v2) and test:
- Data isolation: Does v2 creation affect v1 data?
- Query compatibility: Do v1 queries still work after v2 exists?
- Schema isolation: Does v1 schema remain unchanged?

---

## B. Final P0 Executable Set

### B.1 Round 1 (P0) - 4 Core Cases

| Case ID | Contract | Name | Tests | Oracle Strategy | Status |
|---------|----------|------|-------|-----------------|--------|
| **R5D-001** | SCH-004 | Metadata Accuracy | describe returns correct schema | STRICT | ✓ READY |
| **R5D-002** | SCH-001 | Data Preservation | v1 count unchanged after v2 | STRICT | ✓ READY |
| **R5D-003** | SCH-002 | Query Compatibility | v1 query works after v2 | CONSERVATIVE | ✓ READY |
| **R5D-004** | SCH-008 | Schema Isolation | v1 schema unchanged after v2 | STRICT | ✓ READY |

**Total Round 1**: **4 cases**

**Focus**: Core schema evolution semantics (data integrity, isolation, compatibility)

---

### B.2 Round 2 (P0.5) - 2 Deferred Cases

| Case ID | Contract | Name | Tests | Oracle Strategy | Status |
|---------|----------|------|-------|-----------------|--------|
| **R5D-005** | SCH-005 | Null Semantics | Missing field behavior | CONSERVATIVE | DEFERRED |
| **R5D-006** | SCH-006 | Filter Semantics | Filter on new field works | CONSERVATIVE | DEFERRED |

**Total Round 2**: **2 cases**

**Focus**: Advanced field-level semantics

**Deferral Reason**: Round 1 validates core isolation; Round 2 explores behavioral details

---

## C. Dropped Cases

| Case ID | Contract | Reason |
|---------|----------|--------|
| ~~R5D-005~~ | SCH-007 (Forbidden Gate) | `alter_collection` operation not supported in SDK |

**Total Dropped**: **1 case**

---

## D. Case Sequences

### D.1 R5D-001: Metadata Accuracy (SCH-004)

**Purpose**: Validate describe_collection works

**Sequence**:
1. Create collection with schema: {id, vector[128]}
2. Insert 50 entities
3. describe_collection
4. Verify: fields=2, dimension=128, entity_count=50

**Oracle**: STRICT - PASS or BUG_CANDIDATE

**Contract Compliance**: SCH-004 (Metadata Accuracy)

---

### D.2 R5D-002: Data Preservation (SCH-001)

**Purpose**: Critical - v2 creation must not affect v1 data

**Sequence**:
1. Create collection_v1: {id, vector[128]}
2. Insert 100 entities into v1
3. count_entities(v1) → count_before
4. Create collection_v2: {id, vector[128], category}
5. count_entities(v1) → count_after
6. Verify: count_after == count_before

**Oracle**: STRICT - PASS or BUG_CANDIDATE

**Contract Compliance**: SCH-001 (Data Preservation)

**Multi-Collection Pattern**: v1 and v2 are separate collections

---

### D.3 R5D-003: Query Compatibility (SCH-002)

**Purpose**: Verify v1 queries still work after v2 creation

**Sequence**:
1. Create collection_v1: {id, vector[128]}
2. Insert 100 entities into v1
3. Search v1 with query_vector → results_before
4. Create collection_v2: {id, vector[128], category}
5. Search v1 with SAME query_vector → results_after
6. Verify: results semantically equivalent

**Oracle**: CONSERVATIVE - PASS, OBSERVATION, or ALLOWED_DIFFERENCE

**Contract Compliance**: SCH-002 (Query Compatibility)

**Multi-Collection Pattern**: Query v1, create v2, query v1 again

---

### D.4 R5D-004: Schema Isolation (SCH-008)

**Purpose**: Verify v1 schema unchanged after v2 creation

**Sequence**:
1. Create collection_v1: {id, vector[128]}
2. describe_collection(v1) → schema_v1_before
3. Create collection_v2: {id, vector[128], category}
4. describe_collection(v1) → schema_v1_after
5. Verify: schema_v1_before == schema_v1_after

**Oracle**: STRICT - PASS or BUG_CANDIDATE

**Contract Compliance**: SCH-008 (Schema Isolation After Change)

**Multi-Collection Pattern**: Compare v1 schema before and after v2 creation

---

### D.5 R5D-005: Null Semantics (SCH-005) - DEFERRED to P0.5

**Purpose**: Document missing scalar field behavior

**Sequence**:
1. Create collection_v2: {id, vector[128], category}
2. Insert entities WITHOUT category value
3. Query v2, read category field
4. Document: null / default / error

**Oracle**: CONSERVATIVE - Document actual behavior

**Deferral Reason**: Secondary priority - behavioral documentation

---

### D.6 R5D-006: Filter Semantics (SCH-006) - DEFERRED to P0.5

**Purpose**: Verify filters work on new scalar fields

**Sequence**:
1. Create collection_v2: {id, vector[128], category}
2. Insert entities WITH category="A" and category="B"
3. filtered_search: category == "A"
4. Verify: Only category="A" entities returned

**Oracle**: CONSERVATIVE - PASS, EXPECTED_FAILURE (not supported), or VERSION_GUARDED

**Deferral Reason**: Depends on filter support validation (secondary priority)

---

## E. Revised Phase Sequence

### E.1 Phase Progression

| Phase | Name | Status | Deliverable |
|-------|------|--------|-------------|
| Phase 1 | Specification and Adapter Audit | COMPLETE | Supported ops, describe_collection |
| **Phase 1.5** | **P0 Finalization** | **COMPLETE** | **This document** |
| Phase 5 | Generator (Round 1) | NEXT | 4 P0 test templates |
| Phase 6 | Oracle (Round 1) | PENDING | SCH-001, SCH-002, SCH-004, SCH-008 |
| Phase 7 | Smoke Run (Round 1) | PENDING | Execute 4 P0 cases |
| Phase 5.5 | Generator (Round 2) | PENDING | 2 P0.5 test templates |
| Phase 6.5 | Oracle (Round 2) | PENDING | SCH-005, SCH-006 |
| Phase 7.5 | Smoke Run (Round 2) | PENDING | Execute 2 P0.5 cases |

### E.2 Exit Criteria

**Round 1 Complete** When:
- All 4 P0 cases have templates
- All 4 SCH oracles implemented
- Smoke run executed
- Results classified

**Round 2 Decision Point**:
- If Round 1 reveals issues → fix first
- If Round 1 clean → proceed to Round 2

---

## F. Contract Mapping (Final)

### F.1 Round 1 (4 Cases)

| Case | Contract | Contract Name | Layer |
|------|----------|---------------|-------|
| R5D-001 | SCH-004 | Metadata Accuracy | L1 Foundation |
| R5D-002 | SCH-001 | Data Preservation | L3 Data Integrity |
| R5D-003 | SCH-002 | Query Compatibility | L4 Query Behavior |
| R5D-004 | SCH-008 | Schema Isolation | L1 Foundation |

### F.2 Round 2 (2 Cases - Deferred)

| Case | Contract | Contract Name | Layer |
|------|----------|---------------|-------|
| R5D-005 | SCH-005 | Null Semantics | L5 Field Semantics |
| R5D-006 | SCH-006 | Filter Semantics | L4 Query Behavior |

### F.3 Dropped (1 Case)

| Original Case | Contract | Reason |
|---------------|----------|--------|
| ~~R5D-005~~ | SCH-007 (Forbidden Gate) | Operation not supported |

---

## G. Final Count Summary

| Category | Count |
|----------|-------|
| **Round 1 (P0)** | **4 cases** |
| **Round 2 (P0.5)** | **2 cases** |
| **Dropped** | **1 case** |
| **Original Plan** | 7 cases |
| **Final Executable** | 6 cases (4 + 2) |

---

## H. Multi-Collection vs In-Place Mutation

### H.1 Traditional Schema Evolution (NOT SUPPORTED)

```sql
-- Traditional SQL approach (NOT POSSIBLE in Milvus):
ALTER TABLE my_collection ADD COLUMN category VARCHAR(256);

-- Then observe effects:
DESCRIBE my_collection;  -- Should show new field
SELECT COUNT(*) FROM my_collection;  -- Should be unchanged
```

### H.2 R5D Multi-Collection Approach (SUPPORTED)

```python
# R5D approach (WHAT WE ACTUALLY TEST):

# Create v1 (original schema)
v1 = create_collection("collection_v1", schema={id, vector[128]})
insert(v1, data)
count_v1_before = count_entities(v1)

# Create v2 (evolved schema)
v2 = create_collection("collection_v2", schema={id, vector[128], category})

# Verify isolation
count_v1_after = count_entities(v1)
assert count_v1_after == count_v1_before  # SCH-001

schema_v1_after = describe_collection(v1)
assert schema_v1_after == schema_v1_before  # SCH-008
```

### H.3 Key Difference

| Aspect | Traditional (In-Place) | R5D (Multi-Collection) |
|--------|------------------------|------------------------|
| Schema change location | Single collection | Separate collections |
| Observation | Before/after same collection | Compare v1 vs v2 |
| Tests mutation effects | Direct ALTER effects | Cross-collection isolation |
| Supported in Milvus | NO | YES |

---

## I. Next Steps (After Approval)

**Phase 1.5 Complete** ✓

**Ready for**:
- Phase 5: Generator (Round 1) - create 4 P0 test templates
- Phase 6: Oracle (Round 1) - implement 4 SCH oracles
- Phase 7: Smoke Run (Round 1) - execute 4 P0 cases

**Round 2 (P0.5) Blocked Until**:
- Round 1 complete and validated
- No critical issues found

---

**Phase 1.5 Status**: COMPLETE - Awaiting approval to proceed to Phase 5 (Generator, Round 1)
