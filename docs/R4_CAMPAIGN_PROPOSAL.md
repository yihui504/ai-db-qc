# R4 Campaign Proposal: Differential Testing Across Vector Databases

**Proposal Version**: 2.0 (Refined with Oracle Design)
**Date**: 2026-03-09
**Proposed Dimension**: Differential Cross-Database Testing
**Status**: Proposal - Not Yet Implemented

---

## Executive Summary

R4 proposes differential testing across multiple vector databases to identify behavioral differences in sequence semantics, state management, and API consistency. This extends the testing framework from single-database validation (R1-R3) to multi-database comparison.

**Primary Goal**: Find behavioral inconsistencies across databases that could impact application portability.

**NEW**: Strengthened with formal differential oracle design for accurate classification.

---

## Motivation

### Why Differential Testing Now?

**Progression from R1-R3**:
- **R1** (Parameter Boundaries): Tested Milvus parameter validation
- **R2** (API Validation): Deepened R1 findings, reproduced results
- **R3** (Sequence/State): Tested Milvus state management

**Gap Identified**: All testing so far has been **single-database** (Milvus only)

**Research Question**: How do other vector databases behave with the same operations?

### Why This Matters

**Application Portability**:
- Applications using vector databases need portability
- Behavioral differences create compatibility challenges
- Developers need to know database-specific requirements

**API Consistency**:
- Are operations consistent across databases?
- Do databases enforce similar constraints?
- Are error messages comparable?

**Sequence Semantics**:
- Do databases require similar operation ordering?
- Are state transitions handled consistently?
- Are idempotency guarantees similar?

---

## Strengthened Design

### NEW: Differential Oracle Framework

**Reference**: `docs/DIFFERENTIAL_ORACLE_DESIGN.md`

**Three Categories**:
1. **Contract Violation (BUG)**: Violates universal semantic contract
2. **Allowed Difference (NOT BUG)**: Legitimate architectural variation
3. **Undefined Behavior (NEITHER)**: Edge case with no standard

### NEW: Semantic Properties

**Reference**: `docs/SEQUENCE_SEMANTIC_PROPERTIES.md`

**8 Properties to Test**:
1. Post-Drop Rejection
2. Deleted Entity Visibility
3. Delete Idempotency
4. Index-Independent Search
5. Load-State Enforcement
6. Empty Collection Handling
7. Non-Existent Delete Tolerance
8. Collection Creation Idempotency

---

## Proposed Scope

### Target Databases

**Primary Target**: Milvus vs. Qdrant

**Rationale**:
- Both are popular vector databases
- Both have Python clients
- Both support similar operations
- Different architectures may reveal behavioral differences

**Secondary Targets** (Future):
- Milvus vs. Weaviate
- Qdrant vs. Weaviate
- Three-way comparisons

### Test Design Approach

**Reuse R3 with Enhancements**:
- Start with R3 sequences
- Add adaptive steps to handle different database requirements
- Ensure sequences work on both databases

**Adaptive Strategy**:
- Include optional build_index step (for databases that require it)
- Include optional load step (for databases that require it)
- Compare final state, not intermediate steps

---

## Test Case Definitions (Refined)

### Case R4-001: Post-Drop Rejection

**Semantic Property**: Property 1 (Post-Drop Rejection)

**Semantic Contract**: Collections, once dropped, must no longer exist and must reject all subsequent operations

**Generic Adaptive Sequence**:
```yaml
1. create_collection(name="test_r4_001", dimension=128)
2. insert(vectors)
3. search(query_vector, top_k=10)  # Baseline - verify it works
4. drop_collection(name="test_r4_001")
5. search(query_vector, top_k=10)  # TEST: should fail
```

**Expected Behavior**:
- Step 5: Must fail with "collection not found" or similar error

**Differential Oracle Rule**: **Rule 1 (Search After Drop)**

**Classification**:
- **CONSISTENT**: Both databases fail → PASS ✅
- **BUG**: One database allows post-drop operation → BUG in that database
- **ALLOWED**: Different error messages (same meaning) → ALLOWED DIFFERENCE ⚠️

**R3 Evidence**: Milvus fails correctly with "Collection not exist"

---

### Case R4-002: Deleted Entity Visibility

**Semantic Property**: Property 2 (Deleted Entity Visibility)

**Semantic Contract**: Entities that have been explicitly deleted must not appear in subsequent search results

**Generic Adaptive Sequence**:
```yaml
1. create_collection(name="test_r4_002", dimension=128)
2. insert(vectors)  # Insert entities with known IDs: [0, 1, 2]
3. build_index()  # If database requires
4. load()  # If database requires
5. search(query_vector, top_k=10)  # Verify entity 0 is visible
6. delete(ids=[0])  # Delete entity 0
7. search(query_vector, top_k=10)  # TEST: entity 0 should not appear
```

**Expected Behavior**:
- Step 7: Results must NOT include deleted entity (ID=0)
- May include other entities (IDs 1, 2) if they match query

**Differential Oracle Rule**: **Rule 2 (Deleted Entity Visibility)**

**Classification**:
- **CONSISTENT**: Both databases exclude deleted entity → PASS ✅
- **BUG**: One database includes deleted entity → BUG in that database
- **ALLOWED**: Different tombstone handling (if documented) → ALLOWED DIFFERENCE ⚠️

**R3 Evidence**: Not tested (blocked by load requirement) - R4 will validate

---

### Case R4-003: Delete Idempotency

**Semantic Property**: Property 3 (Delete Idempotency)

**Semantic Contract**: Delete operations should be idempotent - calling delete multiple times on same entity ID should have consistent, deterministic behavior

**Generic Adaptive Sequence**:
```yaml
1. create_collection(name="test_r4_003", dimension=128)
2. insert(vectors)  # Insert entity with known ID: 0
3. build_index()  # If database requires
4. load()  # If database requires
5. delete(ids=[0])  # First delete
6. delete(ids=[0])  # Second delete (TEST: should be deterministic)
```

**Expected Behavior**:
- Step 6: Either always succeeds OR always fails with "not found"

**Differential Oracle Rule**: **Rule 4 (Delete Idempotency)**

**Classification**:
- **CONSISTENT**: Both databases have same idempotency behavior → PASS ✅
- **ALLOWED**: Different strategies (all succeed vs. first-succeeds-rest-fail) → ALLOWED DIFFERENCE ⚠️
- **BUG**: Inconsistent behavior (random success/fail) → BUG

**R3 Evidence**: Milvus allows all deletes (idempotent success)

---

### Case R4-004: Index-Independent Search

**Semantic Property**: Property 4 (Index-Independent Search)

**Semantic Contract**: Search behavior should not depend on explicit index creation if database can perform search without one

**Generic Adaptive Sequence**:
```yaml
1. create_collection(name="test_r4_004", dimension=128)
2. insert(vectors)
3. search(query_vector, top_k=10)  # TEST: search without explicit index
```

**Expected Behavior**:
- Step 3: May succeed (brute force/auto-index) OR fail with clear error

**Differential Oracle Rule**: **Rule 3 (Search Without Index)**

**Classification**:
- **CONSISTENT**: Both have same requirement → PASS ✅
- **ALLOWED**: One requires index, other doesn't → ALLOWED DIFFERENCE ⚠️
- **UNDEFINED**: Neither approach clearly specified

**R3 Evidence**: Not tested (blocked by load requirement)

---

### Case R4-005: Load-State Enforcement

**Semantic Property**: Property 5 (Load-State Enforcement)

**Semantic Contract**: Collections may require explicit loading into memory before search operations

**Generic Adaptive Sequence**:
```yaml
1. create_collection(name="test_r4_005", dimension=128)
2. insert(vectors)
3. search(query_vector, top_k=10)  # TEST: reveals load requirement
```

**Expected Behavior**:
- Step 3: May succeed (auto-load) OR fail with clear "not loaded" error

**Differential Oracle Rule**: **Rule 7 (Load Requirement)**

**Classification**:
- **CONSISTENT**: Both databases have same requirement → PASS ✅
- **ALLOWED**: One requires load, other auto-loads → ALLOWED DIFFERENCE ⚠️
- **UNDEFINED**: Neither approach clearly specified

**R3 Evidence**: Milvus requires explicit load before search

---

### Case R4-006: Empty Collection Handling

**Semantic Property**: Property 6 (Empty Collection Handling)

**Semantic Contract**: Database behavior for searching empty collections is not universally specified (edge case)

**Generic Adaptive Sequence**:
```yaml
1. create_collection(name="test_r4_006", dimension=128)
2. search(query_vector, top_k=10)  # TEST: empty collection search
```

**Expected Behavior**:
- Step 2: Any reasonable behavior (empty results, error, auto-load, etc.)

**Differential Oracle Rule**: **Rule 5 (Empty Collection)**

**Classification**:
- **ALLOWED**: Any behavior is acceptable
- **ALLOWED**: Different behaviors between databases
- **BUG**: Crash or inconsistent behavior

**R3 Evidence**: Milvus requires load even for empty collections

---

### Case R4-007: Non-Existent Delete Tolerance

**Semantic Property**: Property 7 (Non-Existent Delete Tolerance)

**Semantic Contract**: Deleting a non-existent entity ID should be handled gracefully

**Generic Adaptive Sequence**:
```yaml
1. create_collection(name="test_r4_007", dimension=128)
2. delete(ids=[999])  # TEST: delete non-existent ID
```

**Expected Behavior**:
- Step 2: Success (silent) OR fail with clear "not found" error

**Differential Oracle Rule**: **Rule 4 (Idempotency Extension)**

**Classification**:
- **CONSISTENT**: Both databases handle consistently → PASS ✅
- **ALLOWED**: Different approaches (silent vs. error) → ALLOWED DIFFERENCE ⚠️
- **BUG**: Inconsistent behavior

**R3 Evidence**: Milvus succeeds silently

---

### Case R4-008: Collection Creation Idempotency

**Semantic Property**: Property 8 (Collection Creation Idempotency)

**Semantic Contract**: Creating a collection with an already-existing name should have deterministic behavior

**Generic Adaptive Sequence**:
```yaml
1. create_collection(name="test_r4_008", dimension=128)
2. create_collection(name="test_r4_008", dimension=128)  # TEST: duplicate creation
```

**Expected Behavior**:
- Step 2: Success (allows duplicate) OR fail with "already exists" error

**Differential Oracle Rule**: **Rule 6 (Creation Idempotency)**

**Classification**:
- **CONSISTENT**: Both databases have same behavior → PASS ✅
- **ALLOWED**: Different philosophies (allow vs. reject) → ALLOWED DIFFERENCE ⚠️
- **BUG**: Inconsistent behavior

**R3 Evidence**: Milvus allows duplicate creation

---

### Calibration Cases

#### R4-CAL-001: Known-Good Lifecycle

**Purpose**: Validate correct workflow for each database

**Milvus Workflow** (from R3 cal-seq-001):
```
create → insert → build_index → load → search → drop
```

**Qdrant Question**: What is Qdrant's correct workflow?

**Test**: Adapt sequence to each database's requirements

---

#### R4-CAL-002: Multi-Database Consistency

**Purpose**: Test same operations on both databases to ensure they exist

**Sequence**: Basic operations (create, insert, search, drop)

**Goal**: Verify Qdrant supports equivalent operations

---

## Cross-Database Operation Mapping

**Purpose**: Define how sequence operations adapt between Milvus and Qdrant

**Source**: Capability audit in `docs/QDRANT_CAPABILITY_AUDIT.md`

---

### Core Operation Mapping

| Generic Operation | Milvus API | Qdrant API | Adaptation Strategy |
|-------------------|------------|------------|---------------------|
| **create_collection** | `Collection(name, schema)` | `create_collection(collection_name, vectors_config)` | Direct mapping ✅ |
| **insert / upsert** | `collection.insert(data)` | `client.upsert(collection_name, points=[PointStruct...])` | Terminology difference ⚠️ |
| **build_index** | `collection.create_index()` | NOT APPLICABLE (auto-creates) | Optional for Milvus, skip for Qdrant |
| **load** | `collection.load()` | NOT APPLICABLE (auto-loads) | Optional for Milvus, skip for Qdrant |
| **search** | `collection.search(data=[query])` | `client.search(collection_name, query_vector)` | Direct mapping ✅ |
| **delete (by ID)** | `collection.delete(expr="id in [...]")` | `client.delete(collection_name, points_selector=PointIdsList(...))` | Direct mapping ✅ |
| **drop_collection** | `collection.drop()` | `client.delete_collection(collection_name)` | Terminology difference ⚠️ |

---

### Adaptive Sequence Template

**Generic Sequence** (adapts to both databases):

```yaml
# Generic adaptive sequence (works on both databases)
1. create_collection(name="test_r4_XXX", dimension=128)
   - Milvus: Collection(name, schema)
   - Qdrant: create_collection(name, vectors_config)

2. insert/upsert(vectors)
   - Milvus: collection.insert([...])
   - Qdrant: client.upsert(name, points=[PointStruct...])
   - Note: Qdrant requires explicit IDs in PointStruct

3. build_index()  # OPTIONAL
   - Milvus: collection.create_index() (required before search)
   - Qdrant: SKIP (auto-creates HNSW index)

4. load()  # OPTIONAL
   - Milvus: collection.load() (required before search)
   - Qdrant: SKIP (auto-loads on access)

5. search(query_vector, top_k=10)
   - Milvus: collection.search(data=[query])
   - Qdrant: client.search(name, query_vector, limit=10)
   - Comparison Point: Compare search results here

6. delete(ids=[...])
   - Milvus: collection.delete(expr="id in [...]")
   - Qdrant: client.delete(name, points_selector=PointIdsList([...]))
   - Test step: Compare behavior

7. search(query_vector, top_k=10)  # TEST STEP
   - Compare results after deletion
   - Verify deleted entities not visible (Property 2)

8. drop_collection()
   - Milvus: collection.drop()
   - Qdrant: delete_collection(name)

9. search(query_vector, top_k=10)  # TEST STEP
   - Both must fail (Property 1: Post-Drop Rejection)
```

---

### Key Implementation Differences

#### 1. ID Handling

**Milvus**:
```python
# Can auto-generate IDs
collection.insert([
    {"vector": [0.1, 0.2, 0.3], "color": "red"}
])
```

**Qdrant**:
```python
# Requires explicit IDs in PointStruct
client.upsert(
    collection_name="test",
    points=[PointStruct(
        id=1,  # Required
        vector=[0.1, 0.2, 0.3],
        payload={"color": "red"}
    )]
)
```

**Adapter Implication**: Qdrant adapter must auto-generate IDs if not provided.

---

#### 2. State Management

**Milvus Architecture** (Load-Based):
```
create → insert → create_index → load → search
                              ↑        ↑
                         Required   Required
```

**Qdrant Architecture** (Auto-Managed):
```
create → upsert → search
                  ↑
            Works immediately
```

**Oracle Classification**: ALLOWED DIFFERENCE ⚠️

**Adapter Implication**: Qdrant adapter should have no-op methods for `build_index()` and `load()`.

---

#### 3. Search API Differences

**Milvus**:
```python
results = collection.search(
    data=[query_vector],  # List of vectors
    limit=10,
    anns_field="vector"
)
```

**Qdrant**:
```python
results = client.search(
    collection_name="test",
    query_vector=query_vector,  # Single vector (or query_points for batch)
    limit=10
)
```

**Adapter Implication**: Normalize return format for differential comparison.

---

#### 4. Delete API Differences

**Milvus** (Expression-based):
```python
collection.delete(expr="id in [0, 3, 100]")
```

**Qdrant** (Selector-based):
```python
client.delete(
    collection_name="test",
    points_selector=models.PointIdsList(points=[0, 3, 100])
)
```

**Adapter Implication**: Both support ID-based deletion - normalize to generic "delete by IDs" operation.

---

### Test Case Adaptations

#### Property 1: Post-Drop Rejection

**Generic Sequence**:
```yaml
1. create_collection
2. insert(vectors)
3. search  # Baseline
4. drop_collection
5. search  # TEST: must fail on both databases
```

**Expected Behavior**:
- Milvus: `SchemaNotReadyException: Collection not exist`
- Qdrant: Expected error: "collection not found"

**Oracle**: Both must fail → CONSISTENT ✅

---

#### Property 2: Deleted Entity Visibility

**Generic Sequence**:
```yaml
1. create_collection
2. insert(vectors, known IDs)
3. build_index  # Milvus only
4. load  # Milvus only
5. search  # Baseline
6. delete(ids=[target_id])
7. search  # TEST: deleted entity must not appear
```

**Comparison Point**: Step 7 search results

**Oracle**: Both must exclude deleted entity → CONSISTENT ✅

---

#### Property 4: Index-Independent Search

**Generic Sequence**:
```yaml
1. create_collection
2. insert(vectors)
3. search  # TEST: without explicit index
```

**Expected Behaviors**:
- Milvus: May fail (requires load after index) OR succeed if auto-index works
- Qdrant: Succeeds (auto-creates HNSW index)

**Oracle**: ALLOWED DIFFERENCE ⚠️ (architectural choice)

---

#### Property 5: Load-State Enforcement

**Generic Sequence**:
```yaml
1. create_collection
2. insert(vectors)
3. search  # TEST: reveals load requirement
```

**Expected Behaviors**:
- Milvus: Fails with "collection not loaded" error
- Qdrant: Succeeds (auto-loads on first access)

**Oracle**: ALLOWED DIFFERENCE ⚠️ (architectural choice)

---

### Adapter Implementation Notes

**Qdrant Adapter Requirements**:

1. **ID Generation**: Auto-generate IDs if not provided in `upsert()`
2. **No-Op Methods**: `build_index()` and `load()` should be no-ops
3. **Error Normalization**: Map Qdrant errors to consistent format
4. **Result Normalization**: Standardize search result format for comparison

**Milvus Adapter Notes**:

1. **Load Requirement**: Must call `load()` before `search()`
2. **Index Requirement**: Must call `create_index()` before `load()`
3. **ID Flexibility**: Can auto-generate or accept explicit IDs

---

### Differential Comparison Strategy

**What to Compare**:

| Aspect | Compare Method | Oracle Treatment |
|--------|----------------|------------------|
| **Success/Failure** | Did operation succeed or fail? | BUG if inconsistent |
| **Error Messages** | Exact error text | ALLOWED if same meaning |
| **Search Results** | Entities returned, scores, IDs | BUG if deleted entity visible |
| **State After** | Final collection state | BUG if state inconsistent |

**What NOT to Compare** (Allowed Differences):

| Aspect | Reason |
|--------|--------|
| **Error Wording** | Different phrasing for same meaning |
| **Performance** | Different architectural approaches |
| **Intermediate States** | Different state management |

---

### Capability Validation Summary

**Audit Result**: ✅ **PASS** - All operations supported

**From**: `docs/QDRANT_CAPABILITY_AUDIT.md`

| Operation | Qdrant Support | Compatibility |
|-----------|---------------|---------------|
| create_collection | SUPPORTED | ✅ Direct mapping |
| upsert | SUPPORTED | ✅ Terminology difference only |
| delete (by ID) | SUPPORTED | ✅ Direct mapping |
| search | SUPPORTED | ✅ No load required |
| delete_collection | SUPPORTED | ✅ Terminology difference only |
| build_index | NOT APPLICABLE | ⚠️ Auto-creates HNSW |
| load | NOT APPLICABLE | ⚠️ Auto-loads |

**Conclusion**: All 8 semantic properties can be tested on both databases using adaptive sequences.

---

## Implementation Plan

### Phase 1: Qdrant Setup

**Tasks**:
1. Install Qdrant (Docker: `docker run -d -p 6333:6333 qdrant/qdrant`)
2. Verify Qdrant connection
3. Install Qdrant Python client (`pip install qdrant-client`)
4. Test basic Qdrant operations

**Estimated Effort**: 2-3 hours

### Phase 2: Qdrant Adapter

**Tasks**:
1. Implement `adapters/qdrant_adapter.py`
2. Support required operations (create_collection, insert, search, delete, drop)
3. Handle Qdrant-specific features (vectors, payloads, filtering)
4. Test adapter with basic operations

**Estimated Effort**: 4-6 hours

### Phase 3: Differential Framework

**Tasks**:
1. Create `scripts/run_differential_r4.py`
2. Implement adaptive sequence execution (add optional build_index/load steps)
3. Implement differential comparison logic
4. Integrate differential oracle classification
5. Create differential report generator

**Estimated Effort**: 6-8 hours

### Phase 4: Test Execution

**Tasks**:
1. Execute all R4 test cases on both databases
2. Capture differential results
3. Apply oracle classification to each difference
4. Generate differential report

**Estimated Effort**: 2-3 hours

### Phase 5: Analysis and Reporting

**Tasks**:
1. Analyze classified differences
2. Document database-specific requirements
3. Create portability guide
4. Generate research findings report

**Estimated Effort**: 3-4 hours

**Total Estimated Effort**: 17-24 hours

---

## Expected Outcomes

### Minimum Success

**Criteria**: All 8 semantic properties tested on both databases

**Expected**: At least 2-3 behavioral differences identified (classified as ALLOWED DIFFERENCES or BUGS)

### Stretch Success

**Criteria**: Significant behavioral differences with portability implications

**Expected**:
- Clear documentation of database-specific requirements
- Portability guide for vector database applications
- Insights into architectural trade-offs

### Research Value

**Contributions**:
1. **Portability Guide**: Document which behaviors differ across databases
2. **Behavior Catalog**: Systematic catalog of behavioral differences
3. **Design Insights**: Understand architectural trade-offs
4. **Framework Validation**: Demonstrate differential testing methodology

---

## Risk Assessment

### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Qdrant API significantly different | Medium | High | Review Qdrant docs first, prototype early |
| Adapter bugs cause false positives | Medium | High | Thorough adapter testing, validate findings manually |
| Sequences not portable to Qdrant | Low | Medium | Adaptive sequence design allows flexibility |
| Oracle misclassification | Low | High | Clear oracle rules, manual review of edge cases |

### Research Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| No differences found | Medium | Low | Still valuable - validates consistency |
| Differences are trivial | Low | Medium | Focus on significant semantic differences |
| Results not generalizable | Low | Low | Document as Milvus-Qdrant specific |

---

## Success Criteria

### Technical Success

- ✅ All 8 properties tested on both Milvus and Qdrant
- ✅ Differential comparison logic working correctly
- ✅ Oracle classification applied correctly to all differences
- ✅ Comprehensive differential report generated

### Research Success

- ✅ Behavioral differences clearly classified (bugs vs. allowed differences)
- ✅ Database-specific requirements documented
- ✅ Portability implications identified
- ✅ Insights into architectural trade-offs documented

---

## Artifacts to Produce

### Code Artifacts

1. **Qdrant Adapter** (`adapters/qdrant_adapter.py`)
2. **Differential Executor** (`scripts/run_differential_r4.py`)
3. **Differential Templates** (`casegen/templates/r4_differential.yaml`)

### Documentation Artifacts

1. **Qdrant Setup Guide** (`docs/qdrant_setup.md`)
2. **Differential Execution Report** (`docs/R4_DIFFERENTIAL_RESULTS.md`)
3. **Portability Guide** (`docs/VECTOR_DB_PORTABILITY.md`)
4. **Behavior Catalog** (`docs/BEHAVIOR_CATALOG.md`)

### Evidence Artifacts

1. **Differential Execution Results** (`results/r4-differential-YYYYMMDD-HHMMSS/`)
2. **Comparison Tables** (per-property comparisons)
3. **Oracle Classifications** (with reasoning)

---

## Comparison with Original Proposal

| Aspect | Original v1.0 | Refined v2.0 |
|--------|-------------|-------------|
| **Oracle** | Implicit | **Explicit framework** (DIFFERENTIAL_ORACLE_DESIGN.md) |
| **Properties** | Implied from sequences | **Explicitly defined** (8 properties) |
| **Test Cases** | Reuse R3 directly | **R4-specific** with oracle rules |
| **Classification** | Basic (same/different) | ** nuanced** (bug/allowed/undefined) |
| **Research Value** | Comparison catalog | **Meaningful classification** |

---

## Next Steps

### Immediate Actions

1. **Review Oracle Design**: Validate differential oracle framework
2. **Review Semantic Properties**: Ensure properties are well-defined
3. **Approve R4 Proposal**: Decide whether to proceed with implementation

### Decision Points

**Go/No-Go Criteria**:
- Is differential oracle design sound?
- Are semantic properties clear?
- Is R4 scope appropriate for current goals?
- Are resources available for implementation?

---

## Conclusion

R4 proposes strengthened differential testing with:
- **Formal oracle framework** for accurate classification
- **8 explicit semantic properties** to test
- **Clear classification criteria** (bug vs. allowed difference vs. undefined)
- **Adaptive sequence design** to handle different database requirements

**Research Value**:
- Systematic cross-database comparison
- Meaningful classification of differences
- Portability guidance for applications
- Validation of differential testing methodology

**Readiness**: Framework validated in R1-R3, oracle design complete, ready for R4 implementation upon approval.

---

## Metadata

- **Proposal**: R4 Differential Testing Campaign (Refined v2.1)
- **Date**: 2026-03-09
- **Proposed Dimension**: Differential Cross-Database Testing
- **Primary Targets**: Milvus vs. Qdrant
- **Test Cases**: 8 (semantic properties) + 2 calibration
- **Oracle Framework**: Explicit (DIFFERENTIAL_ORACLE_DESIGN.md)
- **Semantic Properties**: 8 defined (SEQUENCE_SEMANTIC_PROPERTIES.md)
- **Capability Audit**: Complete (QDRANT_CAPABILITY_AUDIT.md)
- **Operation Mapping**: Complete (Cross-Database Operation Mapping section)
- **Estimated Effort**: 17-24 hours
- **Status**: Proposal - Ready for Implementation

---

**END OF R4 CAMPAIGN PROPOSAL (Refined v2.1)**

**Next Step**: Proceed with Qdrant adapter implementation per Implementation Plan.
