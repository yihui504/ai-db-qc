# R5B Pre-Implementation Audit

**Date**: 2026-03-10
**Purpose**: Validate adapter capabilities and oracle soundness before R5B execution
**Status**: AUDIT COMPLETE - RECOMMENDATIONS PROVIDED

---

## Executive Summary

This audit examines the current Milvus adapter's capabilities against the requirements of the four proposed index contracts (IDX-001 through IDX-004). The audit identifies **critical limitations** that require scope adjustments for the initial R5B pilot.

**Key Findings**:
1. **IDX-001 Oracle Soundness**: Current oracle conflates ANN approximation tolerance with contract violations - needs redesign
2. **IDX-002 Partial Testability**: Data count can be verified, but index drop/rebuild are not supported
3. **IDX-003 Limited Testability**: Only index_type validation can be tested; HNSW/IVF parameters are hardcoded
4. **IDX-004 Not Testable**: No multi-index support in current adapter

**Recommendation**: Revise R5B pilot to focus on **IDX-001 (refined oracle)** and **IDX-002 (partial)**, postpone IDX-003 and IDX-004.

---

## 1. Adapter Capability Audit

### Current Milvus Adapter Index Support

**File**: `adapters/milvus_adapter.py`
**Relevant Method**: `_build_index()` (lines 250-275)

```python
def _build_index(self, params: Dict) -> Dict[str, Any]:
    """Build index on collection."""
    collection_name = params.get("collection_name")
    index_type = params.get("index_type", "IVF_FLAT")
    metric_type = params.get("metric_type", "L2")

    collection = Collection(collection_name, using=self.alias)

    # Create index on vector field
    index_params = {
        "index_type": index_type,
        "metric_type": metric_type,
        "params": {"nlist": 128}  # ⚠️ HARDCODED
    }

    collection.create_index(
        field_name="vector",
        index_params=index_params
    )
```

### Supported Operations

| Operation | Support | Notes |
|-----------|---------|-------|
| **create_index** | ✅ Partial | Only index_type and metric_type; nlist hardcoded to 128 |
| **drop_index** | ❌ No | Not implemented |
| **rebuild_index** | ❌ No | Not implemented |
| **list_indexes** | ❌ No | Not implemented |
| **get_index_info** | ❌ No | Not implemented |

### Parameter Support Matrix

| Parameter | Support | Default Value | Configurable? |
|-----------|---------|---------------|---------------|
| **index_type** | ✅ Yes | "IVF_FLAT" | Yes |
| **metric_type** | ✅ Yes | "L2" | Yes |
| **nlist (IVF)** | ⚠️ Hardcoded | 128 | **No** |
| **M (HNSW)** | ❌ No | - | No |
| **efConstruction (HNSW)** | ❌ No | - | No |
| **nprobe** | ⚠️ Hardcoded (search) | 10 | No |

---

## 2. Contract-by-Contract Audit

### IDX-001: Index Semantic Neutrality

**Contract Statement**: Creating an index must not change the semantic results of search operations.

#### Adapter Capability Analysis

| Requirement | Support | Implementation Path |
|-------------|---------|---------------------|
| **Brute force search before index** | ✅ Yes | Use FLAT index or search without index |
| **Create HNSW index** | ✅ Yes | index_type="HNSW" |
| **Create IVF_FLAT index** | ✅ Yes | index_type="IVF_FLAT" |
| **Search with index** | ✅ Yes | Normal search after load |
| **Compare results** | ✅ Yes | Python-level comparison |

**Verdict**: **DIRECTLY TESTABLE** ✅

**Limitations**:
- Cannot test different HNSW/IVF parameter combinations (all hardcoded)
- Can only test index_type differences, not parameter tuning effects

---

#### Oracle Soundness Analysis

**Current Oracle** (`core/oracle_engine.py`, lines 385-427):

```python
def _oracle_semantic_neutrality(self, result, contract):
    """Oracle: Index must not change semantic results."""
    results_before = result.get("results_before_index", [])
    results_after = result.get("results_after_index", [])

    recall_threshold = contract.get("oracle", {}).get("parameters", {}).get("expected_recall", 0.9)

    before_ids = set(r.get("id") for r in results_before)
    after_ids = set(r.get("id") for r in results_after)

    if len(before_ids) > 0:
        overlap = len(before_ids & after_ids) / len(before_ids)
    else:
        overlap = 1.0

    passed = overlap >= recall_threshold

    return self._oracle_result(
        contract["contract_id"] if contract else "idx-001",
        Classification.PASS if passed else Classification.VIOLATION,  # ⚠️ PROBLEM
        ...
    )
```

**Problem Identified**:

The current oracle uses a **single threshold (0.9)** to classify results as either PASS or VIOLATION. This is **unsound** for ANN indexes because:

1. **ANN is inherently approximate**: HNSW and IVF are designed to trade accuracy for speed
2. **Recall < 0.9 is not necessarily a bug**: It may be within expected ANN behavior
3. **Hard threshold treats approximation as violation**: Misclassifies acceptable ANN behavior as bugs

**Example of Unsound Classification**:
- If recall = 0.85, current oracle classifies as **VIOLATION** (BUG)
- But for HNSW with default parameters, 0.85 recall may be **expected behavior**, not a bug

---

#### Refined Oracle Design for IDX-001

**Separation of Concerns**:

IDX-001 should evaluate **two distinct aspects**:

1. **Hard Contract Checks** (data/query integrity after index build)
   - Search still works after index
   - Results are not empty (unless before was empty)
   - No crashes or undefined behavior

2. **Approximate Quality Checks** (overlap / recall measurement)
   - Measure actual recall
   - Classify as PASS/ALLOWED_DIFFERENCE based on index type
   - Document expected recall ranges

---

**Refined Oracle Specification**:

```python
def _oracle_semantic_neutrality_refined(self, result, contract):
    """Oracle: Index must not change semantic results (refined).

    Separates hard contract checks from approximate quality checks.

    Hard Checks (must pass):
    - Search succeeds after index
    - Results are not empty (unless before was empty)

    Quality Checks (documented, not VIOLATION):
    - FLAT index: Expect recall >= 0.99 (exact search)
    - HNSW index: Expect recall >= 0.85 (typical range)
    - IVF_FLAT index: Expect recall >= 0.80 (typical range)
    """
    results_before = result.get("results_before_index", [])
    results_after = result.get("results_after_index", [])
    index_type = result.get("index_type", "UNKNOWN")

    # ========== HARD CHECKS ==========
    # Check 1: Search still works
    if results_after is None:
        return self._oracle_result(
            contract["contract_id"] if contract else "idx-001",
            Classification.VIOLATION,
            False,
            "Search failed after index creation",
            {"hard_check": "search_succeeds", "result": "FAILED"}
        )

    # Check 2: Results not empty (unless before was empty)
    before_empty = len(results_before) == 0
    after_empty = len(results_after) == 0

    if not before_empty and after_empty:
        return self._oracle_result(
            contract["contract_id"] if contract else "idx-001",
            Classification.VIOLATION,
            False,
            "Index caused search to return empty results (non-empty before)",
            {"hard_check": "results_not_empty", "result": "VIOLATION"}
        )

    # ========== QUALITY CHECKS ==========
    before_ids = set(r.get("id") for r in results_before)
    after_ids = set(r.get("id") for r in results_after)

    if len(before_ids) > 0:
        recall = len(before_ids & after_ids) / len(before_ids)
    else:
        recall = 1.0

    # Define expected recall thresholds by index type
    # These are TYPICAL values, not strict requirements
    RECALL_THRESHOLDS = {
        "FLAT": 0.99,      # Exact search, near-perfect recall expected
        "HNSW": 0.85,      # ANN with good recall
        "IVF_FLAT": 0.80,  # ANN with moderate recall
        "IVF_SQ8": 0.75,   # Quantized, lower recall
        "UNKNOWN": 0.80    # Conservative default
    }

    expected_recall = RECALL_THRESHOLDS.get(index_type, 0.80)

    # Quality classification: PASS or ALLOWED_DIFFERENCE (not VIOLATION)
    if recall >= expected_recall:
        quality_classification = Classification.PASS
        quality_reasoning = f"Recall {recall:.3f} >= expected {expected_recall:.2f} for {index_type}"
    else:
        # Below expected recall, but this is ALLOWED for ANN (not a VIOLATION)
        quality_classification = Classification.ALLOWED_DIFFERENCE
        quality_reasoning = f"Recall {recall:.3f} below expected {expected_recall:.2f} for {index_type} (within ANN tolerance)"

    return self._oracle_result(
        contract["contract_id"] if contract else "idx-001",
        Classification.PASS,  # Hard checks passed
        True,
        f"Hard checks passed. Quality: {quality_reasoning}",
        {
            "hard_checks": "PASSED",
            "quality_classification": quality_classification.value,
            "recall": recall,
            "expected_recall": expected_recall,
            "index_type": index_type,
            "note": "Low recall classified as ALLOWED_DIFFERENCE, not VIOLATION"
        }
    )
```

**Key Improvements**:

1. **Separate hard checks from quality checks**: Hard violations are bugs; quality variances are documented
2. **Index-type-specific thresholds**: Different expectations for FLAT vs HNSW vs IVF
3. **No false violations**: Low recall is ALLOWED_DIFFERENCE, not VIOLATION
4. **Documentation of expectations**: Clear statement of typical recall ranges

**Oracle Soundness**: ✅ **SOUND** - No false positives from ANN approximation tolerance

---

### IDX-002: Index Data Preservation

**Contract Statement**: Index operations (create, rebuild, delete) must not lose or corrupt data.

#### Adapter Capability Analysis

| Requirement | Support | Implementation Path |
|-------------|---------|---------------------|
| **Count entities before index** | ✅ Yes | Use collection.num_entities |
| **Create index** | ✅ Yes | build_index operation |
| **Count entities after index** | ✅ Yes | Use collection.num_entities |
| **Drop index** | ❌ No | **Not supported** |
| **Rebuild index** | ❌ No | **Not supported** |
| **Verify all data accessible** | ⚠️ Partial | Can search, but cannot verify all IDs without knowing them |

**Verdict**: **PARTIALLY TESTABLE** ⚠️

**Testable Sub-Cases**:
- ✅ Data count after index creation
- ✅ Search returns results after index creation

**Not Testable**:
- ❌ Data count after index drop
- ❌ Data count after index rebuild
- ❌ Full accessibility verification (need to know all inserted IDs)

---

#### Oracle Soundness Analysis

**Current Oracle** (`core/oracle_engine.py`, lines 429-459):

```python
def _oracle_data_preservation(self, result, contract):
    """Oracle: Index operations must preserve data."""
    count_before = result.get("count_before")
    count_after = result.get("count_after")

    if None in [count_before, count_after]:
        return self._oracle_result(
            contract["contract_id"] if contract else "idx-002",
            Classification.OBSERVATION,
            False,
            "Incomplete count data",
            {}
        )

    passed = count_before == count_after

    return self._oracle_result(
        contract["contract_id"] if contract else "idx-002",
        Classification.PASS if passed else Classification.VIOLATION,
        passed,
        f"Data count: {count_before} → {count_after}",
        ...
    )
```

**Assessment**: ✅ **SOUND** for count preservation check

**Limitations**:
- Only checks count, not full data accessibility
- Cannot verify all specific IDs are still present

**Recommendation**: Keep oracle as-is for count preservation; note limitations in test design

---

### IDX-003: Index Parameter Validation

**Contract Statement**: Index creation must validate index type and parameters.

#### Adapter Capability Analysis

| Requirement | Support | Implementation Path |
|-------------|---------|---------------------|
| **Test invalid index_type** | ✅ Yes | Pass invalid string, expect error |
| **Test invalid metric_type** | ✅ Yes | Pass invalid string, expect error |
| **Test HNSW parameter M** | ❌ No | Parameter not exposed |
| **Test HNSW parameter efConstruction** | ❌ No | Parameter not exposed |
| **Test IVF parameter nlist** | ❌ No | Hardcoded to 128 |
| **Test negative/zero nlist** | ❌ No | Parameter not exposed |

**Verdict**: **LIMITED TESTABILITY** ⚠️

**Testable Sub-Cases**:
- ✅ Invalid index_type (e.g., "INVALID_TYPE")
- ✅ Invalid metric_type (e.g., "INVALID_METRIC")

**Not Testable**:
- ❌ Invalid numeric parameters (M, efConstruction, nlist)
- ❌ Out-of-range numeric parameters

---

#### Oracle Soundness Analysis

**Current Oracle** (`core/oracle_engine.py`, lines 461-497):

```python
def _oracle_parameter_validation(self, result, contract):
    """Oracle: Invalid parameters must be rejected."""
    params = result.get("parameters", {})
    error = result.get("error")
    success = result.get("success", False)

    # Determine if parameters are invalid
    is_invalid = (
        params.get("index_type") == "INVALID_TYPE" or
        params.get("M", -1) == -1 or
        params.get("nlist", 1) == 0
    )

    # Invalid parameters should fail
    if is_invalid:
        passed = not success  # Should fail
        expected = "error"
    else:
        passed = success  # Should succeed
        expected = "success"

    return self._oracle_result(
        contract["contract_id"] if contract else "idx-003",
        Classification.PASS if passed else Classification.VIOLATION,
        passed,
        f"Invalid params: {params}, outcome: {error if not success else 'success'} (expected: {expected})",
        ...
    )
```

**Problem Identified**:

The oracle checks for `params.get("M", -1) == -1` and `params.get("nlist", 1) == 0`, but **these parameters are never passed to the adapter**. The adapter ignores them and uses hardcoded values.

**Result**: Any test of M or nlist parameters will appear to "pass" regardless of actual Milvus behavior, creating **false confidence**.

**Oracle Soundness**: ⚠️ **UNSOUND** for parameter validation beyond index_type/metric_type

**Recommendation**: Limit IDX-003 to index_type and metric_type validation only; document numeric parameter testing as not feasible with current adapter

---

### IDX-004: Multiple Index Behavior

**Contract Statement**: Multiple indexes on same collection must have deterministic behavior.

#### Adapter Capability Analysis

| Requirement | Support | Implementation Path |
|-------------|---------|---------------------|
| **Create first index** | ✅ Yes | build_index |
| **Create second index on same field** | ❌ Unknown | Milvus may replace or reject |
| **Query which index is used** | ❌ No | No index_info or list_indexes operation |
| **Force index selection** | ❌ No | No mechanism to specify which index |
| **Determinism testing** | ❌ No | Cannot observe index selection |

**Verdict**: **NOT TESTABLE** ❌

**Blockers**:
1. No way to determine if multiple indexes can coexist
2. No way to query which index is used for search
3. No way to force specific index selection
4. Cannot observe deterministic vs non-deterministic behavior

**Recommendation**: **POSTPONE** until adapter support is added

---

## 3. Oracle Refinement Summary

### IDX-001 Refined Oracle: Key Changes

| Aspect | Before | After |
|--------|--------|-------|
| **Classification Model** | Single threshold (0.9) → PASS/VIOLATION | Hard checks + quality checks → PASS/ALLOWED_DIFFERENCE |
| **ANN Recall < 0.9** | Classified as VIOLATION (BUG) | Classified as ALLOWED_DIFFERENCE (expected) |
| **Index Type Awareness** | No | Type-specific thresholds (FLAT: 0.99, HNSW: 0.85, IVF: 0.80) |
| **Hard Checks** | Implicit | Explicit (search succeeds, results not empty) |
| **Soundness** | ⚠️ Unsound (false violations) | ✅ Sound (no false violations) |

---

## 4. Contract Priority Classification After Audit

### Safe for Pilot

| Contract | Status | Rationale |
|----------|--------|-----------|
| **IDX-001** | ✅ **SAFE FOR PILOT** (with refined oracle) | Directly testable; oracle can be made sound |
| **IDX-002** | ✅ **SAFE FOR PILOT** (partial) | Count preservation testable; drop/rebuild deferred |

### Postpone

| Contract | Status | Rationale |
|----------|--------|-----------|
| **IDX-003** | ⚠️ **POSTPONE** | Only index_type/metric_type testable; numeric parameters not exposed |
| **IDX-004** | ❌ **POSTPONE** | No multi-index support in adapter; cannot observe behavior |

---

## 5. Revised R5B Pilot Scope

### Original Scope (16 tests)

| Contract | Tests | Status |
|----------|-------|--------|
| IDX-001 | 4 | Keep (with refined oracle) |
| IDX-002 | 5 | Reduce to 2 (create only) |
| IDX-003 | 4 | Postpone |
| IDX-004 | 3 | Postpone |
| **TOTAL** | **16** | |

### Revised Scope (6 tests)

| Contract | Tests | Test Names | Priority |
|----------|-------|------------|----------|
| **IDX-001** | 4 | idx-001_hnsw_001, idx-001_ivf_001, idx-001_flat_001, idx-001_ann_recall_001 | HIGH |
| **IDX-002** | 2 | idx-002_create_001, idx-002_create_002 | HIGH |
| **IDX-003** | 0 | (Postponed) | - |
| **IDX-004** | 0 | (Postponed) | - |
| **TOTAL** | **6** | | |

---

### Detailed Test Cases for Revised Pilot

#### IDX-001 Tests (4 tests)

| Test ID | Name | Description | Dataset | Index Type | Expected Recall |
|---------|------|-------------|---------|------------|-----------------|
| **idx-001_hnsw_001** | HNSW Semantic Neutrality | Compare brute force vs HNSW | Dataset 1 (random, 1000) | HNSW | ≥ 0.85 |
| **idx-001_ivf_001** | IVF Semantic Neutrality | Compare brute force vs IVF_FLAT | Dataset 1 (random, 1000) | IVF_FLAT | ≥ 0.80 |
| **idx-001_flat_001** | FLAT Baseline | Verify FLAT produces exact results | Dataset 1 (random, 1000) | FLAT | ≥ 0.99 |
| **idx-001_ann_recall_001** | ANN Recall on Clustered Data | Test ANN on challenging data | Dataset 2 (clustered, 500) | HNSW | ≥ 0.80 |

#### IDX-002 Tests (2 tests)

| Test ID | Name | Description | Dataset |
|---------|------|-------------|---------|
| **idx-002_create_001** | Data Count After Create | Verify count preserved after HNSW creation | Dataset 1 (random, 1000) |
| **idx-002_create_002** | Data Count After Create (IVF) | Verify count preserved after IVF_FLAT creation | Dataset 1 (random, 1000) |

---

## 6. Implementation Requirements for Revised Pilot

### Immediate Requirements (Must Fix)

1. **Implement Refined IDX-001 Oracle**
   - Separate hard checks from quality checks
   - Add index-type-specific recall thresholds
   - Use ALLOWED_DIFFERENCE for low recall (not VIOLATION)
   - File: `core/oracle_engine.py`

2. **Add Count Retrieval to Adapter**
   - Need `collection.num_entities` support
   - For IDX-002 data preservation tests
   - File: `adapters/milvus_adapter.py`

### Deferred Requirements (Not Needed for Revised Pilot)

1. ~~Multi-index support~~ (IDX-004 postponed)
2. ~~Index drop operation~~ (IDX-002 reduced scope)
3. ~~Index rebuild operation~~ (IDX-002 reduced scope)
4. ~~HNSW/IVF parameter exposure~~ (IDX-003 postponed)

---

## 7. Risk Assessment for Revised Pilot

### Resolved Risks

| Risk | Status | Resolution |
|------|--------|------------|
| IDX-001 oracle unsoundness | ✅ Resolved | Refined oracle separates hard checks from quality |
| IDX-003 false confidence | ✅ Resolved | Postponed until parameters are exposed |
| IDX-004 not testable | ✅ Resolved | Postponed until multi-index support added |

### Remaining Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| FLAT index not available for brute force baseline | Low | Medium | Use search before any index as baseline |
| Count retrieval not implemented | Medium | Medium | Add to adapter before pilot |
| ANN recall below expected thresholds | Medium | Low | Classify as ALLOWED_DIFFERENCE, not VIOLATION |

---

## 8. Recommendations

### For R5B Pilot (Immediate)

1. ✅ **PROCEED** with revised pilot scope (6 tests, IDX-001 and IDX-002 only)
2. ✅ **IMPLEMENT** refined IDX-001 oracle before execution
3. ✅ **ADD** count retrieval to Milvus adapter
4. ✅ **DOCUMENT** limitations in pilot report

### For Post-Pilot (Future Enhancements)

1. **Implement index drop operation** → Expand IDX-002 to full scope
2. **Implement index rebuild operation** → Expand IDX-002 to full scope
3. **Expose HNSW/IVF parameters** → Enable IDX-003 full testing
4. **Add multi-index support** → Enable IDX-004 testing

---

## 9. Acceptance Criteria for Pilot Execution

The revised R5B pilot is ready for execution when:

- [ ] Refined IDX-001 oracle is implemented in `core/oracle_engine.py`
- [ ] Count retrieval is added to `adapters/milvus_adapter.py`
- [ ] Test generator produces 6 tests (4 for IDX-001, 2 for IDX-002)
- [ ] All tests reference refined oracle with index-type-specific thresholds
- [ ] Documentation reflects revised scope (6 tests, not 16)

---

**Audit Version**: 1.0
**Date**: 2026-03-10
**Auditor**: AI-DB-QC Framework
**Status**: COMPLETE - Ready for implementation of revised scope
