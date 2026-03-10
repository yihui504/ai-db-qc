# R5D Schema Evolution Campaign - Implementation Plan v1.1

**Campaign Code**: R5D
**Full Name**: Schema Evolution Campaign
**Date**: 2026-03-10
**Status**: PLANNING - REVISED
**Previous Campaign**: R5B Index Lifecycle (COMPLETE)
**Version**: 1.1 (Revised based on feedback)

---

## Change Log v1.0 → v1.1

| Section | Change | Rationale |
|---------|--------|-----------|
| H (P0 Cases) | Reordered 6 cases | Better semantic layering |
| H (P0 Cases) | Removed "search stability" | Don't mix schema with ANN semantics |
| F (Sequence) | Reordered phases | Adapter audit before state model |
| F (Exit Criteria) | Changed from "all PASS" | Interpretability > perfection |
| G (Risks) | Added 2 new risks | Boundary and observation path |
| I (Strategies) | Solidified 4 decisions | Fixed answers documented |

---

## A. Why R5D is the Current Highest Priority

### A.1 Connection with R5B

**R5B Completed**:
- 11 index lifecycle contracts verified on Milvus v2.6.10
- State model defined (index metadata × collection load state)
- Focus: Runtime state transitions

**R5D Schema Evolution**:
- Natural extension: From **runtime state** to **structural state**
- R5B proved "how collections behave at runtime"
- R5D will prove "how schemas evolve and maintain compatibility"

**Semantic Layering**:
```
R5B (Round 1): Runtime lifecycle (load, release, reload, drop)
     ↓
R5D (Round 2): Structural evolution (schema versions, field changes)
     ↓
Future (Round 3): Combined scenarios (schema + runtime interaction)
```

**Critical Separation**: R5D P0 focuses on schema semantics ONLY, not ANN/search effects.

### A.2 Why NOT Distributed (R5C/R5A extension)

| Factor | Distributed | Schema Evolution |
|--------|-------------|-------------------|
| **Uncovered Semantic Space** | Low (ANN well-tested) | **High** (schema changes untested) |
| **Bug Yield** | Low (0 bugs in R5A) | **Unknown** (new territory) |
| **Framework Validation** | Already validated | **New validation needed** |
| **Production Impact** | Performance | **Correctness** |

**Decision**: Schema evolution represents correctness-critical semantic space that hasn't been explored.

### A.3 Why NOT Repeat Differential Oracle

**R4 Status**: COMPLETE
- 8 properties tested across Milvus + Qdrant
- Differential oracle validated
- 0 bugs found (databases are consistent)

**R5D Focus**: Single-database schema semantics (not cross-DB comparison)
- Goal: Understand how ONE database handles schema variations
- Later: Cross-DB schema comparison (if warranted)

**Key Distinction**:
```
R4 Differential: Do Milvus and Qdrant behave the SAME way?
R5D Schema:    How does Milvus behave across DIFFERENT schemas?
```

---

## B. Current Repository Reusable Capabilities

### B.1 Sequence/State System

**Location**: `schemas/`, `core/oracle_engine.py`

**Reusable Components**:

| Component | Location | R5D Reuse |
|-----------|----------|-----------|
| **Test sequences** | `casegen/templates/` | HIGH - Schema operations are sequential |
| **State capture** | `schemas/result.py` | HIGH - Pre/post schema state comparison |
| **Evidence bundle** | `schemas/evidence.py` | HIGH - Schema change evidence |
| **Oracle engine** | `core/oracle_engine.py` | HIGH - Schema oracles needed |

**Schema State Model** (extend R5B pattern):
```python
@dataclass
class SchemaState:
    """Structural state of a collection."""
    fields: List[str]              # Field names
    dimension: int                 # Vector dimension
    scalar_fields: Dict[str, str]  # Scalar field types
    entity_count: int              # Number of entities
    schema_version: str            # For tracking

    def can_query(self, field: str) -> bool:
        """Check if field can be queried."""
        return field in self.fields

    def is_subset_of(self, other: 'SchemaState') -> bool:
        """Check if this schema is subset of another."""
        return set(self.fields).issubset(set(other.fields))
```

### B.2 Contract Specification

**Location**: `contracts/schema/`

**Existing Contracts** (4 defined, need oracles):

| Contract | Status | R5D Action |
|----------|--------|------------|
| SCH-001 Data Preservation | Defined | Implement oracle |
| SCH-002 Query Compatibility | Defined | Implement oracle |
| SCH-003 Index Rebuild | Defined | Implement oracle |
| SCH-004 Metadata Accuracy | Defined | Implement oracle |

**New Contracts Needed** (P0):
- SCH-005: Nullable/Default Field Semantics
- SCH-006: Post-Change Filter Semantics
- SCH-007: Forbidden Change Gate
- SCH-008: Metadata Reflection After Change

### B.3 Oracle Classification

**Location**: `core/oracle_engine.py:16-26`

**All Classifications Reusable**:

| Classification | Meaning | R5D Use |
|----------------|---------|---------|
| PASS | Contract satisfied | Schema change works correctly |
| VIOLATION | Contract violated (BUG) | **Data loss/corruption** |
| ALLOWED_DIFFERENCE | Architectural variance | **Different schema semantics** |
| OBSERVATION | Undefined behavior | Schema edge cases, needs investigation |
| EXPECTED_FAILURE | Precondition gate | **Forbidden change rejected** |
| BUG_CANDIDATE | Invariant violated | Same as VIOLATION for R5D |
| VERSION_GUARDED | Version-specific | **Milvus-specific behavior** |
| INFRA_FAILURE | API error | Schema operation failed |
| EXPERIMENT_DESIGN_ISSUE | Test design issue | Schema test design flaw |

**R5D Oracle Strategy** (solidified):
```python
# Metadata/Gate checks: STRICT
if metadata_mismatch or forbidden_op_succeeded:
    return BUG_CANDIDATE

# Effect-layer semantics: CONSERVATIVE
if query_behavior_unclear:
    return OBSERVATION  # Don't over-classify
if results_differ_but_not_wrong:
    return ALLOWED_DIFFERENCE  # Allow variance
```

### B.4 Adapter Capabilities

**Location**: `adapters/milvus_adapter.py`

**Current Operations**:

| Operation | Supported | R5D Use |
|-----------|-----------|---------|
| create_collection | ✓ | Create different schema variants |
| insert | ✓ | Insert data with different schemas |
| search | ✓ | Vector search (Round 2) |
| filtered_search | ✓ | **P0: Filter on new fields** |
| count_entities | ✓ | Verify data preservation |
| **describe_collection** | ✗ | **NEED TO ADD** |
| **get_schema** | ✗ | **NEED TO ADD** |

**Schema Operation Support Boundary**:
```
SUPPORTED:
- Create collection with different schemas
- Insert with varying scalar fields
- Query existing fields
- Filter on scalar fields

NOT SUPPORTED (Milvus v2.6.10):
- Alter existing collection schema
- Add field to existing collection
- Drop field from existing collection
- Change field type

WORKAROUND: Multi-collection comparison
```

### B.5 Report/Evidence Bundle

**Location**: `schemas/evidence.py`, `schemas/result.py`

**R5D-Specific Evidence**:
```python
@dataclass
class SchemaChangeEvidence(EvidenceBundle):
    """Evidence for schema evolution operations."""

    # Schema states
    schema_v1: Dict[str, Any]
    schema_v2: Dict[str, Any]

    # Data counts
    v1_count_before: int
    v1_count_after: int
    v2_count: int

    # Query results
    v1_query_before: List[Dict]
    v1_query_after: List[Dict]
    v2_query: List[Dict]

    # Metadata
    v1_metadata: Dict[str, Any]
    v2_metadata: Dict[str, Any]

    # Classification hints
    data_preserved: bool
    query_compatible: bool
    metadata_accurate: bool
```

---

## C. R5D Contract Family Design

### C.1 Semantic Layering

```
LAYER 1: Foundation (Metadata)
├── SCH-004: Metadata Accuracy
├── SCH-008: Metadata Reflection After Change
└── Oracle Strategy: STRICT (PASS/BUG_CANDIDATE only)

LAYER 2: Protection (Gates)
├── SCH-007: Forbidden Schema Change Gate
└── Oracle Strategy: STRICT (EXPECTED_FAILURE or BUG_CANDIDATE)

LAYER 3: Data Integrity (Critical)
├── SCH-001: Data Preservation After Allowed Change
└── Oracle Strategy: STRICT (BUG_CANDIDATE if data loss)

LAYER 4: Query Behavior (Compatibility)
├── SCH-002: Backward Query Compatibility
├── SCH-006: Post-Change Filter Semantics
└── Oracle Strategy: CONSERVATIVE (PASS/OBSERVATION/ALLOWED_DIFFERENCE)

LAYER 5: Field Semantics (Edge Cases)
├── SCH-005: Nullable/Default Field Read Semantics
└── Oracle Strategy: CONSERVATIVE (document behavior)

LAYER 6: Search Effect (Round 2)
├── SCH-007: Search Stability Across Schemas
└── Oracle Strategy: STRICT (vector search should be schema-agnostic)
```

### C.2 P0 Contract Specifications

#### SCH-001: Data Preservation After Allowed Schema Change

**Statement**: Creating collection_v2 with extended schema must not affect data in collection_v1

**Layer**: LAYER 3 (Data Integrity)

**Preconditions**:
- collection_v1 exists with N entities
- collection_v2 created with additional scalar field

**Postconditions**:
- collection_v1 entity count == N (unchanged)
- collection_v1 entity data unchanged
- collection_v2 has its own entities

**Invariants**:
- Cross-collection data isolation

**Oracle**:
```python
def _oracle_sch001_data_preservation(self, result, contract):
    v1_count_before = result["v1_count_before"]
    v1_count_after = result["v1_count_after"]

    if v1_count_after != v1_count_before:
        return self._oracle_result(
            "SCH-001", Classification.BUG_CANDIDATE, False,
            f"Data loss in v1: {v1_count_before} → {v1_count_after}",
            {"loss": v1_count_before - v1_count_after}
        )

    return self._oracle_result(
        "SCH-001", Classification.PASS, True,
        "Data preserved across schema versions",
        {"v1_count": v1_count_after}
    )
```

---

#### SCH-002: Backward Query Compatibility

**Statement**: Queries on collection_v1 must continue working after collection_v2 with different schema is created

**Layer**: LAYER 4 (Query Behavior)

**Preconditions**:
- query works on collection_v1
- collection_v2 created with different schema

**Postconditions**:
- query on collection_v1 still succeeds
- query returns same results (semantically)

**Invariants**:
- Query stability

**Oracle**:
```python
def _oracle_sch002_query_compatibility(self, result, contract):
    query_before = result["v1_query_before"]
    query_after = result["v1_query_after"]

    if query_after["status"] == "error":
        return self._oracle_result(
            "SCH-002", Classification.BUG_CANDIDATE, False,
            f"Query broke after v2 creation: {query_after['error']}",
            {"error": query_after["error"]}
        )

    # Check if results are semantically equivalent
    if not results_semantically_equal(query_before, query_after):
        # Allow slight differences (order, floating point)
        return self._oracle_result(
            "SCH-002", Classification.ALLOWED_DIFFERENCE, True,
            "Query results differ (implementation variance)",
            {"difference": "documented"}
        )

    return self._oracle_result(
        "SCH-002", Classification.PASS, True,
        "Query compatible across schema versions",
        {"results": len(query_after["results"])}
    )
```

---

#### SCH-004: Metadata Accuracy

**Statement**: Collection metadata must accurately reflect actual schema

**Layer**: LAYER 1 (Foundation)

**Preconditions**:
- collection created with known schema

**Postconditions**:
- metadata.fields == actual fields
- metadata.dimension == actual dimension

**Invariants**:
- Metadata consistency

**Oracle**:
```python
def _oracle_sch004_metadata_accuracy(self, result, contract):
    metadata_dim = result["metadata"]["dimension"]
    created_dim = result["created_dimension"]

    if metadata_dim != created_dim:
        return self._oracle_result(
            "SCH-004", Classification.BUG_CANDIDATE, False,
            f"Dimension mismatch: metadata={metadata_dim}, created={created_dim}",
            {"metadata": metadata_dim, "created": created_dim}
        )

    return self._oracle_result(
        "SCH-004", Classification.PASS, True,
        "Metadata accurately reflects schema",
        metadata
    )
```

---

#### SCH-005: Nullable/Default Field Read Semantics

**Statement**: Reading missing scalar fields must have deterministic behavior

**Layer**: LAYER 5 (Field Semantics)

**Preconditions**:
- collection_v2 created with scalar field
- Data inserted WITHOUT scalar field value

**Postconditions**:
- Missing field handled consistently
- Behavior is deterministic (null, default, or error)

**Invariants**:
- Null behavior consistency

**Oracle**:
```python
def _oracle_sch005_nullable_semantics(self, result, contract):
    null_behavior = result["null_field_behavior"]

    # Document actual behavior
    if null_behavior["mode"] == "null":
        return self._oracle_result(
            "SCH-005", Classification.PASS, True,
            "Missing fields return null",
            {"behavior": "null"}
        )
    elif null_behavior["mode"] == "default":
        return self._oracle_result(
            "SCH-005", Classification.PASS, True,
            "Missing fields return default value",
            {"behavior": "default", "value": null_behavior["default_value"]}
        )
    elif null_behavior["mode"] == "error":
        return self._oracle_result(
            "SCH-005", Classification.PASS, True,
            "Missing fields cause error",
            {"behavior": "error", "error_message": null_behavior["error"]}
        )
    elif null_behavior["inconsistent"]:
        return self._oracle_result(
            "SCH-005", Classification.BUG_CANDIDATE, False,
            "Inconsistent null behavior across reads",
            null_behavior
        )
    else:
        return self._oracle_result(
            "SCH-005", Classification.OBSERVATION, True,
            f"Unexpected null behavior: {null_behavior}",
            null_behavior
        )
```

---

#### SCH-006: Post-Change Filter Semantics

**Statement**: Filter queries on new scalar fields must work correctly

**Layer**: LAYER 4 (Query Behavior)

**Preconditions**:
- collection_v2 created with scalar field "category"
- Data inserted WITH category values

**Postconditions**:
- Filter on category works
- Filter returns correct entities
- Non-matching entities excluded

**Invariants**:
- Filter determinism

**Oracle**:
```python
def _oracle_sch006_filter_semantics(self, result, contract):
    filter_result = result["v2_filter_result"]

    if filter_result["status"] == "error":
        # Clear error = expected, unclear error = bug
        if is_clear_error(filter_result["error"]):
            return self._oracle_result(
                "SCH-006", Classification.EXPECTED_FAILURE, False,
                f"Filter not supported: {filter_result['error']}",
                {"error": filter_result["error"]}
            )
        else:
            return self._oracle_result(
                "SCH-006", Classification.BUG_CANDIDATE, False,
                f"Unclear filter error: {filter_result['error']}",
                {"error": filter_result["error"]}
            )

    # Check if filter actually filtered
    results = filter_result["results"]
    if not all(r.get("category") == filter_result["filter_value"] for r in results):
        return self._oracle_result(
            "SCH-006", Classification.BUG_CANDIDATE, False,
            "Filter returned non-matching entities",
            {"filter_value": filter_result["filter_value"], "results": results}
        )

    return self._oracle_result(
        "SCH-006", Classification.PASS, True,
        f"Filter works correctly ({len(results)} results)",
        {"results": len(results)}
    )
```

---

#### SCH-007: Forbidden Schema Change Gate

**Statement**: Attempts to change collection schema in forbidden ways must be rejected

**Layer**: LAYER 2 (Protection)

**Preconditions**:
- collection exists with data

**Postconditions**:
- Dimension change rejected
- Field type change rejected
- Primary key change rejected

**Invariants**:
- Data protection gates

**Oracle**:
```python
def _oracle_sch007_forbidden_gate(self, result, contract):
    forbidden_op = result["forbidden_operation"]

    if forbidden_op["status"] == "success":
        return self._oracle_result(
            "SCH-007", Classification.BUG_CANDIDATE, False,
            "Forbidden schema change succeeded!",
            {"operation": forbidden_op["operation"]}
        )

    error = forbidden_op.get("error", "")

    # Check if error message is clear
    if is_clear_error_message(error):
        return self._oracle_result(
            "SCH-007", Classification.EXPECTED_FAILURE, True,
            f"Correctly rejected: {error}",
            {"error": error}
        )

    # Unclear error - still a gate, but poor UX
    return self._oracle_result(
        "SCH-007", Classification.ALLOWED_DIFFERENCE, True,
        "Rejected but with unclear error",
        {"error": error}
    )
```

---

#### SCH-008: Metadata Reflection After Change

**Statement**: After creating collection_v2, collection_v1 metadata must remain accurate

**Layer**: LAYER 1 (Foundation)

**Preconditions**:
- collection_v1 exists
- collection_v2 created with different schema

**Postconditions**:
- v1 metadata unchanged
- v1 metadata still accurate

**Invariants**:
- Metadata isolation

**Oracle**:
```python
def _oracle_sch008_metadata_reflection(self, result, contract):
    v1_metadata_before = result["v1_metadata_before"]
    v1_metadata_after = result["v1_metadata_after"]

    if v1_metadata_before != v1_metadata_after:
        return self._oracle_result(
            "SCH-008", Classification.BUG_CANDIDATE, False,
            "v1 metadata changed after v2 creation",
            {"before": v1_metadata_before, "after": v1_metadata_after}
        )

    return self._oracle_result(
        "SCH-008", Classification.PASS, True,
        "v1 metadata unchanged after v2 creation",
        v1_metadata_after
    )
```

---

### C.3 Round 2 Contracts (Deferred)

| Contract | Statement | Why Round 2 |
|----------|-----------|-------------|
| SCH-009 | Search Stability Across Schemas | Don't mix schema with ANN semantics in P0 |
| SCH-010 | Index Isolation After Schema Change | Index behavior is complex, defer |
| SCH-011 | Complex Query Compatibility | Basic queries first |
| SCH-012 | Large Schema Diff | Start small |

---

## D. Case Design Matrix

### D.1 P0 First Slice (6 Cases) - REVISED

| Case ID | Contract | Schema Change | Operation | Oracle Strategy |
|---------|----------|--------------|-----------|-----------------|
| **R5D-001** | SCH-004 | N/A | describe_collection | STRICT |
| **R5D-002** | SCH-008 | v1 → v2 | Describe v1 after v2 created | STRICT |
| **R5D-003** | SCH-001 | v1 → v2 | Count v1 before/after v2 | STRICT |
| **R5D-004** | SCH-002 | v1 → v2 | Query v1 before/after v2 | CONSERVATIVE |
| **R5D-005** | SCH-007 | Dimension change | Try to change dimension | STRICT |
| **R5D-006** | SCH-005 | v2 with null scalar | Insert without scalar | CONSERVATIVE |
| **R5D-007** | SCH-006 | v2 with scalar | Filter on new field | CONSERVATIVE |

### D.2 Case Specifications

#### R5D-001: Metadata Accuracy Check

**Purpose**: Validate foundation - describe_collection works

**Sequence**:
1. Create collection with schema: {id, vector[128], category}
2. Insert 50 entities
3. Call describe_collection
4. Verify: fields=3, dimension=128

**Expected**: PASS (metadata accurate)

**Oracle**: STRICT - PASS or BUG_CANDIDATE only

---

#### R5D-002: Metadata Reflection After Schema Change

**Purpose**: Verify v1 metadata stable after v2 creation

**Sequence**:
1. Create collection_v1: {id, vector[128]}
2. describe_collection(v1) → metadata_v1_before
3. Create collection_v2: {id, vector[128], category}
4. describe_collection(v1) → metadata_v1_after
5. Verify: metadata_v1_before == metadata_v1_after

**Expected**: PASS (v1 metadata unchanged)

**Oracle**: STRICT - PASS or BUG_CANDIDATE only

---

#### R5D-003: Data Preservation After Schema Change

**Purpose**: Critical - v2 creation must not affect v1 data

**Sequence**:
1. Create collection_v1: {id, vector[128]}
2. Insert 100 entities into v1
3. count_entities(v1) → count_before
4. Create collection_v2: {id, vector[128], category}
5. count_entities(v1) → count_after
6. Verify: count_after == count_before

**Expected**: PASS (100)

**Oracle**: STRICT - PASS or BUG_CANDIDATE only

---

#### R5D-004: Backward Query Compatibility

**Purpose**: Verify v1 queries still work after v2 creation

**Sequence**:
1. Create collection_v1: {id, vector[128]}
2. Insert 100 entities into v1
3. Search v1 with query_vector → results_before
4. Create collection_v2: {id, vector[128], category}
5. Search v1 with SAME query_vector → results_after
6. Verify: results semantically equivalent

**Expected**: PASS (same results)

**Oracle**: CONSERVATIVE - PASS, ALLOWED_DIFFERENCE, or OBSERVATION

---

#### R5D-005: Forbidden Schema Change Gate

**Purpose**: Verify dimension changes are rejected

**Sequence**:
1. Create collection_v1: {id, vector[128]}
2. Insert 50 entities
3. Attempt to change dimension to 256 (operation that doesn't exist)
4. Verify: Operation fails with clear error

**Expected**: EXPECTED_FAILURE (correctly rejected)

**Oracle**: STRICT - EXPECTED_FAILURE or BUG_CANDIDATE only

**Note**: Since Milvus doesn't support alter_collection, this may test a non-existent operation. If so, classify as VERSION_GUARDED (operation not supported).

---

#### R5D-006: Nullable/Default Field Read Semantics

**Purpose**: Document null behavior for missing scalar fields

**Sequence**:
1. Create collection_v2: {id, vector[128], category (nullable)}
2. Insert entities WITHOUT category value
3. Query v2, read category field
4. Document behavior: null / default / error

**Expected**: PASS (deterministic behavior)

**Oracle**: CONSERVATIVE - Document behavior, PASS if consistent

---

#### R5D-007: Post-Change Filter Semantics

**Purpose**: Verify filters work on new scalar fields

**Sequence**:
1. Create collection_v2: {id, vector[128], category}
2. Insert entities WITH category="A" and category="B"
3. Filter: category == "A"
4. Verify: Only category="A" entities returned

**Expected**: PASS (filter works)

**Oracle**: CONSERVATIVE - PASS, EXPECTED_FAILURE (not supported), or OBSERVATION

---

### D.3 Execution Order

```
Phase 1: Foundation (Quick Wins)
├── R5D-001: Metadata accuracy → Validates adapter
└── R5D-002: Metadata reflection → Validates isolation

Phase 2: Critical (Data Integrity)
├── R5D-003: Data preservation → Tests isolation
└── R5D-004: Query compatibility → Tests stability

Phase 3: Edge Cases
├── R5D-005: Forbidden gate → Tests protection
├── R5D-006: Null semantics → Documents behavior
└── R5D-007: Filter semantics → Tests new fields
```

---

## E. Oracle Design

### E.1 Oracle Strategy Matrix

| Layer | Contracts | Strategy | Classifications |
|-------|-----------|----------|-----------------|
| **L1: Foundation** | SCH-004, SCH-008 | STRICT | PASS, BUG_CANDIDATE |
| **L2: Protection** | SCH-007 | STRICT | EXPECTED_FAILURE, BUG_CANDIDATE, ALLOWED_DIFFERENCE |
| **L3: Data Integrity** | SCH-001 | STRICT | PASS, BUG_CANDIDATE |
| **L4: Query Behavior** | SCH-002, SCH-006 | CONSERVATIVE | PASS, ALLOWED_DIFFERENCE, OBSERVATION, EXPECTED_FAILURE |
| **L5: Field Semantics** | SCH-005 | CONSERVATIVE | PASS, OBSERVATION, ALLOWED_DIFFERENCE |

### E.2 Oracle Implementation Functions

```python
def _oracle_sch004_metadata_accuracy(self, result, contract):
    """LAYER 1: STRICT - Metadata must match actual schema."""
    metadata = result.get("describe_result", {})
    created = result.get("created_schema", {})

    if metadata.get("dimension") != created.get("dimension"):
        return self._oracle_result(
            "SCH-004", Classification.BUG_CANDIDATE, False,
            f"Dimension mismatch: {metadata.get('dimension')} != {created.get('dimension')}",
            result
        )

    return self._oracle_result(
        "SCH-004", Classification.PASS, True,
        "Metadata accurate",
        metadata
    )

def _oracle_sch008_metadata_reflection(self, result, contract):
    """LAYER 1: STRICT - v1 metadata must be stable."""
    before = result.get("v1_metadata_before", {})
    after = result.get("v1_metadata_after", {})

    if before != after:
        return self._oracle_result(
            "SCH-008", Classification.BUG_CANDIDATE, False,
            "v1 metadata changed after v2 creation",
            {"before": before, "after": after}
        )

    return self._oracle_result(
        "SCH-008", Classification.PASS, True,
        "v1 metadata stable",
        after
    )

def _oracle_sch001_data_preservation(self, result, contract):
    """LAYER 3: STRICT - Data loss is never acceptable."""
    v1_before = result.get("v1_count_before", 0)
    v1_after = result.get("v1_count_after", 0)

    if v1_after < v1_before:
        return self._oracle_result(
            "SCH-001", Classification.BUG_CANDIDATE, False,
            f"Data loss: {v1_before} → {v1_after}",
            {"loss": v1_before - v1_after}
        )

    return self._oracle_result(
        "SCH-001", Classification.PASS, True,
        "Data preserved",
        {"v1_count": v1_after}
    )

def _oracle_sch002_query_compatibility(self, result, contract):
    """LAYER 4: CONSERVATIVE - Query behavior may vary."""
    query_before = result.get("v1_query_before", {})
    query_after = result.get("v1_query_after", {})

    if query_after.get("status") == "error":
        return self._oracle_result(
            "SCH-002", Classification.BUG_CANDIDATE, False,
            f"Query broke: {query_after.get('error')}",
            result
        )

    results_before = query_before.get("results", [])
    results_after = query_after.get("results", [])

    if not results_semantically_equal(results_before, results_after):
        # Allow variance, but document it
        return self._oracle_result(
            "SCH-002", Classification.ALLOWED_DIFFERENCE, True,
            "Query results differ (implementation variance)",
            {"before": len(results_before), "after": len(results_after)}
        )

    return self._oracle_result(
        "SCH-002", Classification.PASS, True,
        "Query compatible",
        {"results": len(results_after)}
    )

def _oracle_sch007_forbidden_gate(self, result, contract):
    """LAYER 2: STRICT - Gates must be enforced."""
    forbidden = result.get("forbidden_operation", {})

    if forbidden.get("status") == "success":
        return self._oracle_result(
            "SCH-007", Classification.BUG_CANDIDATE, False,
            "Forbidden change succeeded!",
            result
        )

    error = forbidden.get("error", "")

    if is_clear_error_message(error):
        return self._oracle_result(
            "SCH-007", Classification.EXPECTED_FAILURE, True,
            f"Correctly rejected: {error}",
            result
        )

    # Poor error message, but still rejected
    return self._oracle_result(
        "SCH-007", Classification.ALLOWED_DIFFERENCE, True,
        "Rejected (unclear error)",
        result
    )

def _oracle_sch005_nullable_semantics(self, result, contract):
    """LAYER 5: CONSERVATIVE - Document actual behavior."""
    behavior = result.get("null_field_behavior", {})

    if behavior.get("inconsistent"):
        return self._oracle_result(
            "SCH-005", Classification.BUG_CANDIDATE, False,
            "Inconsistent null behavior",
            result
        )

    # Document the actual mode
    mode = behavior.get("mode", "unknown")
    return self._oracle_result(
        "SCH-005", Classification.PASS, True,
        f"Null behavior: {mode}",
        {"mode": mode, "behavior": behavior}
    )

def _oracle_sch006_filter_semantics(self, result, contract):
    """LAYER 4: CONSERVATIVE - Filter may not be supported."""
    filter_result = result.get("v2_filter_result", {})

    if filter_result.get("status") == "error":
        if "not supported" in filter_result.get("error", "").lower():
            return self._oracle_result(
                "SCH-006", Classification.VERSION_GUARDED, True,
                "Filters not supported (Milvus v2.6.10)",
                result
            )
        elif is_clear_error_message(filter_result.get("error")):
            return self._oracle_result(
                "SCH-006", Classification.EXPECTED_FAILURE, True,
                f"Filter failed: {filter_result.get('error')}",
                result
            )
        else:
            return self._oracle_result(
                "SCH-006", Classification.OBSERVATION, True,
                f"Unclear filter behavior: {filter_result.get('error')}",
                result
            )

    # Verify filter actually filtered
    results = filter_result.get("results", [])
    filter_value = result.get("filter_value")

    if results and not all(r.get(filter_result["filter_field"]) == filter_value for r in results):
        return self._oracle_result(
            "SCH-006", Classification.BUG_CANDIDATE, False,
            "Filter returned non-matching entities",
            result
        )

    return self._oracle_result(
        "SCH-006", Classification.PASS, True,
        f"Filter works ({len(results)} results)",
        result
    )
```

### E.3 Helper Functions

```python
def is_clear_error_message(error: str) -> bool:
    """Check if error message is clear and actionable."""
    if not error:
        return False
    clear_keywords = ["not supported", "cannot", "invalid", "must", "required", "doesn't exist"]
    error_lower = error.lower()
    return any(kw in error_lower for kw in clear_keywords)

def results_semantically_equal(results1, results2, epsilon=1e-6) -> bool:
    """Check if query results are semantically equivalent."""
    if len(results1) != len(results2):
        return False
    for r1, r2 in zip(results1, results2):
        if r1.get("id") != r2.get("id"):
            return False
        if abs(r1.get("score", 0) - r2.get("score", 0)) > epsilon:
            return False
    return True
```

---

## F. Implementation Sequence

### F.1 Vertical Slice Order (REVISED)

```
┌─────────────────────────────────────────────────────────────┐
│ Phase 1: Specification (1 hour)                              │
├─────────────────────────────────────────────────────────────┤
│ 1.1 Define SCH contracts (JSON specs)                        │
│ 1.2 Solidify P0 case specifications                          │
│ 1.3 Document oracle strategy matrix                         │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 2: Adapter Capability Audit (30 min)                   │
├─────────────────────────────────────────────────────────────┤
│ 2.1 Document current Milvus adapter operations              │
│ 2.2 Identify schema operation support boundary               │
│ 2.3 Document multi-collection workaround                    │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 3: State/Effect Matrix (1 hour)                        │
├─────────────────────────────────────────────────────────────┤
│ 3.1 Define SchemaState dataclass                            │
│ 3.2 Document state transitions (create → describe)           │
│ 3.3 Document effect relationships (v2 → v1 impact)           │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 4: Minimal Adapter Patch (1 hour)                      │
├─────────────────────────────────────────────────────────────┤
│ 4.1 Implement describe_collection                           │
│ 4.2 Test describe_collection on REAL Milvus                 │
│ 4.3 Validate adapter returns correct metadata               │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 5: Generator (1-2 hours)                               │
├─────────────────────────────────────────────────────────────┤
│ 5.1 Add schema operation templates                          │
│ 5.2 Implement R5D test generation                           │
│ 5.3 Generate P0 test cases (7 cases)                        │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 6: Oracle Implementation (2-3 hours)                   │
├─────────────────────────────────────────────────────────────┤
│ 6.1 Implement SCH-001 through SCH-008 oracles               │
│ 6.2 Add helper functions (comparison, error detection)       │
│ 6.3 Unit test oracles with mock data                         │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 7: Smoke Run (30 min)                                  │
├─────────────────────────────────────────────────────────────┤
│ 7.1 Run P0 cases on MOCK mode                               │
│ 7.2 Fix any infrastructure issues                           │
│ 7.3 Run P0 cases on REAL mode (Milvus)                      │
│ 7.4 Analyze classifications                                 │
└─────────────────────────────────────────────────────────────┘
```

### F.2 Phase Exit Criteria (REVISED)

**Phase 1 Exit**:
- [ ] All 8 SCH contracts defined in JSON (SCH-001 through SCH-008)
- [ ] P0 case specifications documented
- [ ] Oracle strategy matrix finalized

**Phase 2 Exit**:
- [ ] Current capabilities documented
- [ ] Schema operation support boundary identified
- [ ] Multi-collection workaround specified

**Phase 3 Exit**:
- [ ] SchemaState dataclass defined
- [ ] State transitions documented
- [ ] Effect relationships mapped (v2 → v1)

**Phase 4 Exit**:
- [ ] describe_collection implemented
- [ ] describe_collection tested on REAL Milvus
- [ ] Metadata format validated

**Phase 5 Exit**:
- [ ] 7 P0 test cases generated
- [ ] Test templates validated
- [ ] Mock execution succeeds

**Phase 6 Exit**:
- [ ] All 8 SCH oracles implemented
- [ ] Oracle unit tests pass
- [ ] Helper functions tested

**Phase 7 Exit** (REVISED - Not "all PASS"):
- [ ] All 7 P0 cases executed
- [ ] All cases have interpretable classification
- [ ] 0 untriaged failures
- [ ] 0 adapter-caused false positives
- [ ] Results documented

### F.3 Estimated Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1: Spec | 1 hour | None |
| Phase 2: Audit | 30 min | None |
| Phase 3: State Model | 1 hour | Phase 1 |
| Phase 4: Adapter Patch | 1 hour | Phase 2 |
| Phase 5: Generator | 1-2 hours | Phase 1, 3 |
| Phase 6: Oracle | 2-3 hours | Phase 1 |
| Phase 7: Smoke | 30 min | Phase 4, 5, 6 |
| **Total** | **7-9 hours** | |

---

## G. Risk Points

### G.1 Documentation Semantics vs Implementation Mismatch

**Risk**: Milvus documentation says one thing, implementation does another

**Example**: Doc says "schema changes supported", but actually they're not

**Mitigation**:
- Test-driven: Start with REAL mode smoke tests
- Document actual behavior, not documented behavior
- Use VERSION_GUARDED for implementation-specific behavior

**Detection**:
```python
# If test fails but doc says it should pass
if test_failed and documentation_says_pass:
    classification = VERSION_GUARDED  # Doc wrong, not bug
    note = "Documented behavior not observed"
```

---

### G.2 Schema Change: Mixed Data Visibility

**Risk**: After creating v2 collection, v1 data becomes partially invisible

**Example**: v2 creation somehow affects v1 query results

**Detection**:
- R5D-002 explicitly tests metadata stability
- R5D-003 explicitly tests data preservation
- R5D-004 explicitly tests query compatibility

**Mitigation**:
- Multiple observation points (before/after v2 creation)
- Cross-collection isolation tests

---

### G.3 Adapter Misjudgment

**Risk**: Adapter reports success but operation actually failed (or vice versa)

**Example**: describe_collection returns fields but actual schema is different

**Detection**:
```python
# Cross-check adapter results
adapter_result = adapter.describe_collection(...)
actual_count = adapter.count_entities(...)

if adapter_result["count"] != actual_count["data"][0]["num_entities"]:
    return INFRA_FAILURE, "Adapter metadata inaccurate"
```

**Mitigation**:
- Adapter tests in Phase 4
- Cross-check operations (describe vs count)

---

### G.4 "Forbidden Operation" Misclassified as Bug

**Risk**: Test expects operation to be rejected, but database allows it

**Example**: Dimension change is "forbidden" in our mental model, but Milvus allows it (or doesn't support the operation at all)

**Detection**:
```python
# SCH-007 tests this
try:
    result = change_dimension(...)
    if result["status"] == "success":
        # Is data corrupted?
        if data_corrupted(result):
            return BUG_CANDIDATE, "Allowed but corrupt!"
        else:
            return OBSERVATION, "Operation allowed (unexpected)"
except Exception as e:
    if is_clear_error(e):
        return EXPECTED_FAILURE, "Correctly rejected"
    else:
        return OBSERVATION, f"Operation unclear: {e}"
```

**Mitigation**:
- Separate "mental model" from "actual contract"
- Update mental model based on evidence
- Use OBSERVATION for unexpected-but-not-wrong behavior

---

### G.5 Floating Point Comparison in Oracle

**Risk**: Scores differ due to floating point precision, not semantic difference

**Example**: Score differs by 1e-10, classified as BUG_CANDIDATE incorrectly

**Detection**:
```python
def scores_equal(score1, score2, epsilon=1e-6) -> bool:
    return abs(score1 - score2) < epsilon

if not scores_equal(v1_score, v2_score):
    diff = abs(v1_score - v2_score)
    if diff < 1e-10:
        return OBSERVATION, f"Tiny floating point difference: {diff}"
    elif diff < 1e-6:
        return ALLOWED_DIFFERENCE, f"Acceptable floating point difference: {diff}"
    else:
        return BUG_CANDIDATE, f"Significant score difference: {diff}"
```

**Mitigation**:
- Use epsilon comparison
- Log actual differences for investigation
- Document threshold decisions

---

### G.6 Multi-Collection State Interference

**Risk**: Creating v2 affects v1's runtime state

**Example**: v2 index somehow interferes with v1 search

**Detection**:
- R5D-002: v1 metadata check after v2 creation
- R5D-003: v1 data count check after v2 creation
- R5D-004: v1 query check after v2 creation

**Mitigation**:
- Cross-collection isolation tests (all P0 cases)
- Multiple observation points

---

### G.7 Schema Operation Support Boundary Risk (NEW)

**Risk**: Assuming Milvus supports schema operations that it doesn't

**Example**: Test assumes alter_collection works, but Milvus doesn't support it

**Detection**:
- Phase 2 audit explicitly identifies supported operations
- Phase 3 state model documents actual capabilities

**Mitigation**:
```python
# Document actual support boundary
SUPPORTED_OPERATIONS = {
    "create_collection": True,
    "describe_collection": True,  # After Phase 4
    "insert": True,
    "search": True,
    "filtered_search": True,
    "alter_collection": False,  # NOT SUPPORTED
    "add_field": False,  # NOT SUPPORTED
    "drop_field": False,  # NOT SUPPORTED
}

# Test generator checks support
if not SUPPORTED_OPERATIONS.get(operation):
    classification = VERSION_GUARDED
    note = f"Operation {operation} not supported in Milvus v2.6.10"
```

**Workaround**: Multi-collection comparison instead of single-collection evolution

---

### G.8 Observation-Path Mismatch Risk (NEW)

**Risk**: Oracle observes behavior through wrong path, misclassifies

**Example**: Query fails, but oracle checks wrong error field, misclassifies as BUG_CANDIDATE instead of EXPECTED_FAILURE

**Detection**:
```python
# Example: Observation path mismatch
# Adapter returns: {"status": "error", "message": "..."}
# Oracle checks: result["error"]  # Wrong path!

# Correct observation path
error = result.get("message") or result.get("error") or result.get("reason")
```

**Mitigation**:
- Phase 4: Validate adapter returns consistent structure
- Phase 6: Oracle unit tests with various result shapes
- Document observation paths in oracle functions

**Example Fix**:
```python
def _extract_error(result):
    """Extract error from multiple possible paths."""
    return (
        result.get("error") or
        result.get("message") or
        result.get("reason") or
        result.get("data", [{}])[0].get("error")
    )
```

---

## H. P0 First Slice Cases

### H.1 Recommended P0 Cases (7 cases) - REVISED

| Case | Contract | Layer | Tests | Oracle Strategy |
|------|----------|-------|-------|-----------------|
| **R5D-001** | SCH-004 | L1 (Foundation) | Metadata accuracy | STRICT |
| **R5D-002** | SCH-008 | L1 (Foundation) | Metadata reflection after v2 | STRICT |
| **R5D-003** | SCH-001 | L3 (Data Integrity) | Data preservation | STRICT |
| **R5D-004** | SCH-002 | L4 (Query Behavior) | Backward compatibility | CONSERVATIVE |
| **R5D-005** | SCH-007 | L2 (Protection) | Forbidden gate | STRICT |
| **R5D-006** | SCH-005 | L5 (Field Semantics) | Null behavior | CONSERVATIVE |
| **R5D-007** | SCH-006 | L4 (Query Behavior) | Filter on new field | CONSERVATIVE |

### H.2 Execution Order

```
Round 1: Foundation (Validate adapter)
├── R5D-001: Metadata accuracy
└── R5D-002: Metadata reflection after v2

Round 2: Critical (Validate isolation)
├── R5D-003: Data preservation
└── R5D-004: Backward query compatibility

Round 3: Edge Cases (Document behavior)
├── R5D-005: Forbidden gate
├── R5D-006: Null semantics
└── R5D-007: Filter semantics
```

### H.3 Search Stability (Round 2)

**Why Not P0**:
- Search involves ANN semantics (approximation, scoring)
- Schema semantics should be validated first
- Round 2 can test: "Do schemas affect vector search results?"

**Round 2 Case**:
```
R5D-101: SCH-009 - Search Stability Across Schemas
- Same vectors in v1 and v2
- Search with same query
- Verify: Same top-k IDs, same scores
```

---

## I. Solidified Strategies

### I.1 Milvus-Only for P0

**Decision**: P0 uses Milvus v2.6.10 only

**Rationale**:
- Single-database validation first
- Understand Milvus schema behavior before cross-DB
- Qdrant can be added in Round 2 if needed

**Cross-DB Plan** (Round 2):
- After Milvus P0 complete
- Port to Qdrant
- Compare SCH contract classifications
- Document ALLOWED_DIFFERENCE cases

---

### I.2 Multi-Collection Comparison

**Decision**: Use multi-collection comparison instead of single-collection evolution

**Rationale**:
- Milvus v2.6.10 doesn't support alter_collection
- Can't add fields to existing collection
- Workaround: Create v1 and v2 separately, compare behavior

**Pattern**:
```python
# Instead of:
collection.create()
collection.add_field("category")  # NOT SUPPORTED

# Use:
collection_v1 = create({id, vector})
collection_v2 = create({id, vector, category})
# Compare v1 behavior before/after v2 creation
```

---

### I.3 Fixed Schema for P0

**Decision**: Use fixed, hardcoded schemas for P0

**Schema_v1**: {id, vector[128]}
**Schema_v2**: {id, vector[128], category}

**Rationale**:
- Simplicity: No parameterization needed
- Reproducibility: Same schemas every test
- Clarity: Exact field behavior known

**Parameterization** (Round 2):
- If P0 successful, can add schema variations
- Different dimensions, different field types
- But P0 keeps it simple

---

### I.4 Oracle Strategy: Strict vs Conservative

**Decision**:
- **STRICT** for metadata, gates, data integrity
- **CONSERVATIVE** for query/field semantics

**Definitions**:

| Strategy | Meaning | Classifications |
|----------|---------|-----------------|
| **STRICT** | Binary: correct or bug | PASS, BUG_CANDIDATE only |
| **CONSERVATIVE** | Document variance | PASS, OBSERVATION, ALLOWED_DIFFERENCE, EXPECTED_FAILURE |

**Application**:

| Layer | Strategy | Contracts |
|-------|----------|-----------|
| L1: Foundation | STRICT | SCH-004, SCH-008 |
| L2: Protection | STRICT | SCH-007 |
| L3: Data Integrity | STRICT | SCH-001 |
| L4: Query Behavior | CONSERVATIVE | SCH-002, SCH-006 |
| L5: Field Semantics | CONSERVATIVE | SCH-005 |

---

### I.5 BUG_CANDIDATE Does Not Auto-Stop

**Decision**: Finding a BUG_CANDIDATE does NOT stop the run

**Rationale**:
- P0 is exploratory: discovering actual behavior
- BUG_CANDIDATE may be our misunderstanding, not real bug
- Need complete picture before deciding

**Process**:
```
If BUG_CANDIDATE found:
  1. Document evidence
  2. Continue remaining tests
  3. Re-evaluate after all P0 complete
  4. Decide: investigation needed or design flaw
```

**Example**:
- R5D-004 finds query results differ slightly
- Classify as OBSERVATION (not BUG_CANDIDATE)
- Continue to see if pattern emerges
- If all queries differ slightly → ALLOWED_DIFFERENCE
- If only one query differs → investigate further

---

## J. Exit Criteria (REVISED)

### J.1 P0 Smoke Run Success (Not "All PASS")

**Minimum Acceptable**:
- [ ] All 7 P0 cases executed without INFRA_FAILURE
- [ ] All cases have interpretable classification
- [ ] 0 untriaged failures (all have clear classification)
- [ ] 0 adapter-caused false positives

**Full Success**:
- [ ] Foundation cases (R5D-001, R5D-002) are PASS
- [ ] Data integrity (R5D-003) is PASS
- [ ] Query behavior (R5D-004) is PASS or OBSERVATION
- [ ] Gates (R5D-005) are EXPECTED_FAILURE or VERSION_GUARDED
- [ ] Field semantics (R5D-006, R5D-007) are PASS/OBSERVATION/ALLOWED_DIFFERENCE

**Unacceptable** (must fix before proceeding):
- [ ] Any INFRA_FAILURE (adapter broken)
- [ ] UNCLASSIFIED behavior (can't interpret results)
- [ ] Adapter false positive (adapter bug, not database bug)

### J.2 Classification Interpretability

Each case must have clear rationale:

| Classification | When to Use | Example |
|----------------|-------------|---------|
| PASS | Behavior as expected | Metadata accurate |
| BUG_CANDIDATE | Clear violation | Data count decreased |
| EXPECTED_FAILURE | Gate enforced | Forbidden operation rejected |
| ALLOWED_DIFFERENCE | Acceptable variance | Filter returns different order |
| OBSERVATION | Unexpected but not wrong | Unclear null behavior, needs investigation |
| VERSION_GUARDED | Operation not supported | alter_collection doesn't exist |

**Unacceptable**:
- "Don't know what happened"
- "Oracle confused"
- "Need more info"

---

## K. Next Steps After Approval

### K.1 Immediate Actions (After Approval)

1. **Create contract specs** (Phase 1):
   - `contracts/schema/sch-005.json` through `sch-008.json`
   - Update existing `sch-001.json` through `sch-004.json`

2. **Extend adapter** (Phase 4):
   - Add `describe_collection` to Milvus adapter
   - Test on REAL Milvus

3. **Implement oracles** (Phase 6):
   - Add `_oracle_sch_*` functions to `core/oracle_engine.py`
   - Unit test with mock data

4. **Create test templates** (Phase 5):
   - `casegen/templates/r5d_schema.yaml`
   - Define P0 case sequences

5. **Generate tests** (Phase 5):
   - `scripts/generate_r5d_tests.py`
   - Generate 7 P0 cases

6. **Smoke run** (Phase 7):
   - Execute on MOCK mode first
   - Execute on REAL Milvus
   - Analyze classifications

### K.2 Deliverables

| Deliverable | Location | Due |
|-------------|----------|-----|
| Contract specs | `contracts/schema/` | Phase 1 |
| State model doc | `docs/R5D_STATE_MODEL.md` | Phase 3 |
| Adapter extension | `adapters/milvus_adapter.py` | Phase 4 |
| Oracle code | `core/oracle_engine.py` | Phase 6 |
| Test templates | `casegen/templates/r5d_schema.yaml` | Phase 5 |
| Generated tests | `generated_tests/r5d_schema_*.json` | Phase 5 |
| Execution results | `results/r5d_schema_*.json` | Phase 7 |

---

## L. Manual Review Summary

### L.1 Strategic Decisions (Solidified)

| Decision | Value | Status |
|----------|-------|--------|
| **Schema evolution approach** | Multi-collection comparison | ✓ SOLIDIFIED |
| **Test database** | Milvus-only for P0 | ✓ SOLIDIFIED |
| **Scope of first slice** | 7 cases | ✓ SOLIDIFIED |
| **Oracle strategy** | STRICT for metadata/gates, CONSERVATIVE for semantics | ✓ SOLIDIFIED |

### L.2 Technical Decisions (Solidified)

| Decision | Value | Status |
|----------|-------|--------|
| **Adapter extension** | Implement `describe_collection` | ✓ SOLIDIFIED |
| **Epsilon for floating point** | 1e-6 | ✓ SOLIDIFIED |
| **Schema types** | Fixed for P0 | ✓ SOLIDIFIED |
| **BUG_CANDIDATE handling** | Don't auto-stop | ✓ SOLIDIFIED |

### L.3 Risk Acceptance (Solidified)

| Risk | Mitigation | Status |
|------|------------|--------|
| **Milvus behavior surprises** | Document actual, use VERSION_GUARDED | ✓ SOLIDIFIED |
| **Oracle ambiguity** | CONSERVATIVE for effect layer | ✓ SOLIDIFIED |
| **Support boundary** | Audit in Phase 2, document clearly | ✓ SOLIDIFIED |
| **Observation path mismatch** | Validate in Phase 4, document paths | ✓ SOLIDIFIED |

---

**Plan Version**: 1.1 (Revised)
**Date**: 2026-03-10
**Status**: AWAITING FINAL APPROVAL
**Changes from v1.0**:
- Reordered P0 cases (7 cases, search stability removed)
- Modified implementation sequence
- Changed exit criteria (not all PASS)
- Added 2 new risks
- Solidified 4 key strategies

**Next Action**: Final approval, then begin Phase 1
