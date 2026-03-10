# R5B Index Lifecycle Campaign - Final Summary

**Campaign**: R5B Index Lifecycle State Transitions
**Database**: Milvus v2.6.10
**Date Range**: 2026-03-10
**Status**: COMPLETE
**Final Run**: r5b-lifecycle-20260310-124135

---

## 1. Goals and Scope

### Primary Objectives

1. **Define a two-dimensional state model** for index lifecycle:
   - Index metadata state: NO_INDEX → INDEX_EXISTS → INDEX_DROPPED
   - Collection load state: NOT_LOADED → LOADED

2. **Verify state transition invariants** across create_index, load, search, release, reload, drop_index operations

3. **Distinguish universal behaviors** from implementation-specific quirks

4. **Establish framework-level contracts** applicable across vector databases

### In Scope

| Operation | Coverage |
|-----------|----------|
| create_index | Post-insert index creation, state verification |
| load | Collection loading, state transition verification |
| search | Precondition gates, loaded vs unloaded behavior |
| release | Metadata preservation, unload behavior |
| reload | State restoration after release |
| drop_index | Index deletion, post-drop search semantics |
| flush | Storage and search visibility for new inserts |
| insert | Post-insert visibility timing (ILC-009b) |

### Out of Scope

- Concurrent operations (multiple clients)
- Index type variations (HNSW only)
- Scalar indexing behavior
- Partition-specific behavior
- Bulk operations performance

---

## 2. State Model

### Two-Dimensional State Space

```
                    Index Metadata State
                    NO_INDEX  INDEX_EXISTS  INDEX_DROPPED
                    ─────────────────────────────────────
Collection      NOT │  EMPTY    INDEX_       INDEX_
Load State          │  _NO_     CREATED_      DROPPED
                    │  DATA     UNLOADED
                    ─────────────────────────────────────
                LOADED │   N/A    INDEX_        N/A
                        │          LOADED
                        └────────────────────────────
```

### Composite States (Verified)

| State | Index Metadata | Collection Load | Description |
|-------|----------------|-----------------|-------------|
| COLLECTION_EMPTY_NO_DATA | NO_INDEX | NOT_LOADED | Fresh collection, no data |
| DATA_NO_INDEX | NO_INDEX | NOT_LOADED | Data exists, no index |
| INDEX_CREATED_UNLOADED | INDEX_EXISTS | NOT_LOADED | Index created, not loaded |
| INDEX_LOADED | INDEX_EXISTS | LOADED | Index created and loaded |
| INDEX_RELEASED | INDEX_EXISTS | NOT_LOADED | Post-release, metadata preserved |
| INDEX_DROPPED | INDEX_DROPPED | NOT_LOADED | Index deleted |

### State Transition Diagram

```
create_collection → COLLECTION_EMPTY_NO_DATA
insert → DATA_NO_INDEX
build_index → INDEX_CREATED_UNLOADED
load → INDEX_LOADED
search (on INDEX_LOADED) → INDEX_LOADED
release → INDEX_RELEASED
reload → INDEX_LOADED
drop_index → INDEX_DROPPED
```

---

## 3. Verified Contracts

### Framework-Level Candidates (8 contracts)

| Contract ID | Name | Statement | Confidence | Universal Candidate |
|-------------|------|-----------|------------|---------------------|
| ILC-001 | Create Index State Transition | create_index creates index metadata without loading collection | HIGH | ✓ |
| ILC-002 | Search Precondition Gate | search on unloaded collection fails predictably | HIGH | ✓ |
| ILC-003 | Load State Transition | load transitions collection from NotLoad to Loaded | HIGH | ✓ |
| ILC-004 | Loaded Search Baseline | search on loaded collection succeeds | HIGH | ✓ |
| ILC-005 | Release State Transition | release unloads collection while preserving index metadata and data | HIGH | ✓ |
| ILC-006 | Reload After Release | reload restores searchable state with same data | HIGH | ✓ |
| ILC-009b | Post-Insert Search Timing | inserted vector requires flush for search visibility | HIGH | ✓ |
| ILC-010 | Documented NotLoad Behavior | create_collection without index results in NotLoad state | HIGH | ✓ |

### Milvus-Validated (1 contract)

| Contract ID | Name | Statement | Confidence | Note |
|-------------|------|-----------|------------|------|
| ILC-008 | Post-Drop Search Semantics | after drop_index, load fails and search is unavailable | MEDIUM | Other implementations may allow brute force search without index |

### Milvus-Specific Observed (2 behaviors)

| Area | Behavior | Classification |
|------|----------|----------------|
| drop_index | drop_index requires release before drop | MILVUS_SPECIFIC |
| api | utility.load_state() returns LoadState enum, not string | MILVUS_PYMILVUS_SPECIFIC |
| collection | collection names only allow [a-zA-Z0-9_] | MILVUS_NAMING_CONSTRAINT |
| persistence | collection.num_entities may not reflect recent inserts without flush | MILVUS_PERSISTENCE_BEHAVIOR |

### Experiment Design Issues (0 pending)

| Contract ID | Original Issue | Resolution |
|-------------|-----------------|------------|
| ILC-009 | Using existing vectors as query inconclusive | Resolved via ILC-009b with exact vector match |

---

## 4. Contract Classifications

### PASS (8 contracts)

Contract satisfied, invariants preserved, behavior matches expected semantics.

### EXPECTED_FAILURE (1 contract)

| Contract | Rationale |
|----------|-----------|
| ILC-002 | Search failed on unloaded collection (precondition gate violation) |

### VERSION_GUARDED (1 contract)

| Contract | Rationale |
|----------|-----------|
| ILC-008 | Post-drop search fails with "index not found" - other implementations may allow brute force |

### ALLOWED_DIFFERENCE (0 contracts)

No architectural differences that qualify as ALLOWED_DIFFERENCE.

### EXPERIMENT_DESIGN_ISSUE (0 pending)

All experiment design issues resolved.

---

## 5. Results by Round

### Round 1 (2026-03-10 morning)

**Run IDs**: r5b-lifecycle-20260310-115857, r5b-lifecycle-20260310-121731

| Contract | Classification | Key Finding |
|----------|----------------|-------------|
| ILC-001 | PASS | Index metadata created, collection not loaded |
| ILC-002 | PASS | Search precondition gate verified |
| ILC-003 | PASS | Load state transition verified |
| ILC-004 | PASS | Loaded search baseline works |
| ILC-005 | PASS | Release preserves metadata |
| ILC-006 | PASS | Reload restores state |
| ILC-007 | PASS | Drop index works |
| ILC-008 | VERSION_GUARDED | Post-drop search semantics verified |
| ILC-009 | EXPERIMENT_DESIGN_ISSUE | Query design insufficient |
| ILC-010 | PASS | NotLoad behavior confirmed |

**Issues Discovered**:
- ILC-009 query design insufficient for search visibility timing
- drop_index requires release before drop (Milvus-specific)

### Round 2 (2026-03-10 mid-day)

**Focus**: ILC-009 redesign with exact vector match

**Run IDs**: r5b-lifecycle-20260310-123741, r5b-lifecycle-20260310-124135

| Contract | Classification | Key Finding |
|----------|----------------|-------------|
| ILC-009b | PASS | Flush enables search visibility |

**Evidence**:
- Immediate search: Found existing vector (id=50, score=27.27)
- After flush: Exact match (id=0, score=0.0)
- Storage count: 100 → 101 after flush

---

## 6. Key Findings

### 6.1 create_index Does Not Imply Load

**Finding**: `create_index` creates index metadata but does NOT load the collection into memory.

**Evidence**:
- After `create_index`: `load_state = NotLoad`
- `search` fails until `load()` is called

**Universal Candidate**: YES
- Architecturally, index metadata is separate from runtime memory state
- This is a clean separation of concerns

### 6.2 Search on Unloaded Collection is Precondition-Gated

**Finding**: Search on unloaded collection fails with predictable error, not silent failure.

**Evidence**:
- Error: `collection not loaded`
- Classification: EXPECTED_FAILURE (precondition gate)

**Universal Candidate**: YES
- Precondition gates are a universal pattern for stateful operations

### 6.3 Release Unloads Searchable State

**Finding**: `release` unloads collection from memory while preserving index metadata and data.

**Evidence**:
- After `release`: `load_state = NotLoad`
- `index_metadata_exists = true`
- `storage_count` unchanged

**Universal Candidate**: YES
- Memory management is a universal concern

### 6.4 Reload Restores Searchable State

**Finding**: `reload` restores the searchable state with data consistency.

**Evidence**:
- After `reload`: `load_state = Loaded`
- Search results match pre-release (overlap=1.00)

**Universal Candidate**: YES
- Reload should restore previous state by definition

### 6.5 Post-Drop Behavior

**Finding**: After `drop_index`, `load` fails with "index not found" error.

**Evidence**:
- Error: `index not found[collection=...]`
- Search is unavailable

**Universal Candidate**: PARTIAL
- Other implementations may allow brute force search without index
- Milvus v2.6.10 requires index for all search operations

### 6.6 Flush-Enabled Search Visibility for New Inserts

**Finding**: Inserted vectors require `flush` for search visibility.

**Evidence**:
- Immediate search: NOT found (returns existing vector)
- After flush: Found with exact match (score=0.0)
- Storage count increases only after flush

**Universal Candidate**: YES
- Flush is a documented operation for data persistence
- Behavior is predictable and consistent with storage/index layer separation

---

## 7. Paper-Worthiness Assessment

### Main Text Candidates

Strong theoretical or practical significance, clear universal applicability.

| Contract | Rationale | Section |
|----------|-----------|---------|
| ILC-002 | Precondition gates are fundamental to stateful systems | State Model |
| ILC-003 | Load state transition is core to lifecycle management | State Model |
| ILC-005 | Release semantics inform memory management | Lifecycle |
| ILC-006 | Reload guarantees are important for consistency | Lifecycle |
| ILC-009b | Flush-enabled visibility is a critical correctness property | Correctness |

### Appendix / Observations

Implementation-specific but valuable for practitioners.

| Contract | Rationale |
|----------|-----------|
| ILC-001 | create_index behavior varies by implementation |
| ILC-004 | Search semantics vary (top_k, scoring) |
| ILC-008 | Post-drop behavior not universal |
| ILC-010 | NotLoad as default is implementation choice |

### Not for Paper

Too implementation-specific or trivial.

| Contract | Rationale |
|----------|-----------|
| Milvus-specific behaviors | Naming constraints, enum types |

---

## 8. Current Limitations

### Scope Limitations

1. **Single Database Tested**: Only Milvus v2.6.10 verified
   - Need: Qdrant, Weaviate, pgvector for universal verification

2. **Single Index Type**: Only HNSW tested
   - Need: IVF, FLAT, other index types

3. **No Concurrency**: Single-threaded operations only
   - Need: Concurrent insert/search, concurrent load/drop

4. **No Scale Testing**: 100-1000 vectors only
   - Need: Million-scale tests

5. **No Failure Injection**: No network failures, crashes
   - Need: Fault tolerance verification

### Design Limitations

1. **State Model Gaps**: No explicit representation of:
   - Index building state (BUILDING)
   - Partial load states
   - Error states

2. **No Transaction Semantics**: Not tested:
   - Atomic insert + index operations
   - Rollback behavior

3. **No Consistency Levels**: Not tested:
   - Strong vs eventual consistency
   - Read-your-writes guarantees

### Measurement Limitations

1. **Timing Precision**: Second-level precision, not millisecond
2. **No Resource Profiling**: Memory, CPU not measured
3. **No Network Metrics**: Latency breakdown not available

---

## 9. Recommendations for R5D

### Why R5D is Next Priority

1. **Completeness**: Differential testing (R5D) complements state model (R5B)
2. **Bug Finding**: Differential testing is more effective for finding bugs
3. **Universal Verification**: Cross-database comparison is faster with differential

### R5B Follow-Up Items (If Returning Later)

1. **Expand Contract Coverage**:
   - Bulk insert operations
   - Partition-specific lifecycle
   - Index rebuild operations

2. **Cross-Database Verification**:
   - Port R5B contracts to Qdrant, Weaviate
   - Identify universal vs specific behaviors

3. **Advanced Scenarios**:
   - Concurrent operations
   - Failure recovery
   - Performance characteristics

4. **Formal Specification**:
   - TLA+ specification of state model
   - Proof of invariants

---

## 10. References

### Documentation

- [R5B Smoke Test Report](R5B_MILVUS_V2610_SMOKE_REPORT.md)
- [R5B Round 2 Experiments](R5B_ROUND2_SECOND_EXPERIMENTS.md)
- [ILC-009 Investigation](R5B_ILC009_POST_INSERT_INVESTIGATION.md)
- [ILC-009b Final Report](R5B_ILC009B_FINAL_REPORT.md)

### Contracts

- [Index Lifecycle Contracts](../../contracts/index/lifecycle_contracts.json)

### Results

- [R5B Results Index](../../results/R5B_RESULTS_INDEX.md)

### Handoffs

- [R5B Complete Handoff](../handoffs/R5B_COMPLETE_HANDOFF.md)

---

**Report Completed**: 2026-03-10
**Campaign Status**: COMPLETE
**Next Campaign**: R5D Differential Oracle
