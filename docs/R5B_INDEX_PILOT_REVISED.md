# R5B Index Behavior Pilot - Revised Scope

**Date**: 2026-03-10
**Run ID**: TBD (assigned at execution)
**Framing**: Index Behavior Contract-Driven Validation (Revised After Pre-Implementation Audit)
**Status**: DESIGN READY - AWAITING IMPLEMENTATION

---

## Executive Summary

This is the **revised** R5B Index Behavior Pilot design, incorporating findings from the pre-implementation audit. The audit identified critical adapter limitations requiring scope reduction from 16 tests to **6 focused tests** on **2 contracts** (IDX-001 and IDX-002).

**Key Changes from Original Design**:
- **Reduced Scope**: 6 tests (down from 16)
- **Two Contracts Only**: IDX-001 (refined oracle) and IDX-002 (partial)
- **Postponed**: IDX-003 and IDX-004 due to adapter limitations
- **Refined Oracle**: IDX-001 now separates hard checks from approximate quality checks

---

## 1. Included Contracts

### IDX-001: Index Semantic Neutrality (Refined Oracle)

**Statement**: Creating an index must not change the semantic results of search operations.

**Type**: Universal

**Test Count**: 4 tests

**Oracle Design**: **Refined** - Separates hard contract checks from approximate quality checks

**Hard Checks** (must pass for PASS):
- Search succeeds after index creation
- Results are not empty (unless before was empty)

**Quality Checks** (documented, not VIOLATION):
- FLAT index: Expect recall ≥ 0.99 (exact search)
- HNSW index: Expect recall ≥ 0.85 (typical ANN range)
- IVF_FLAT index: Expect recall ≥ 0.80 (typical ANN range)

**Classification**:
- Hard check failures → **VIOLATION** (BUG)
- Low recall (below threshold) → **ALLOWED_DIFFERENCE** (expected ANN behavior)

---

### IDX-002: Index Data Preservation (Partial)

**Statement**: Index creation must not lose or corrupt data.

**Type**: Universal

**Test Count**: 2 tests

**Scope**: **Partial** - Only index creation tested; index drop and rebuild postponed

**Oracle Design**: Count preservation check (sound for supported operations)

**Check**: `count_before == count_after`

---

## 2. Excluded Contracts (Postponed)

### IDX-003: Index Parameter Validation

**Reason for Postponement**:
- Adapter hardcodes all numeric parameters (nlist=128)
- HNSW parameters (M, efConstruction) not exposed
- Only index_type and metric_type can be validated
- Testing numeric parameters would give false confidence

**Required for Future**: Expose HNSW/IVF parameters in adapter

---

### IDX-004: Multiple Index Behavior

**Reason for Postponement**:
- No multi-index support in adapter
- No way to query which index is used for search
- Cannot observe deterministic vs non-deterministic behavior
- Unknown if Milvus supports multiple indexes per vector field

**Required for Future**:
- Implement `list_indexes` operation
- Add ability to query active index
- Support creating multiple indexes on same field

---

## 3. Test Case Definitions

### IDX-001 Tests (4 tests)

#### Test: idx-001_hnsw_001

**Name**: HNSW Semantic Neutrality

**Description**: Compare brute force search results against HNSW-indexed search results

**Dataset**: Dataset 1 (Random vectors, 128D, 1000 entities)

**Sequence**:
1. Create collection
2. Insert 1000 entities
3. Search WITHOUT index (brute force baseline) → `results_before`
4. Create HNSW index
5. Load collection
6. Search WITH index → `results_after`
7. Compare results

**Oracle Evaluation**:
- **Hard Check**: Search succeeds after index
- **Quality Check**: Recall ≥ 0.85 (ALLOWED_DIFFERENCE if below)

**Priority**: HIGH

---

#### Test: idx-001_ivf_001

**Name**: IVF Semantic Neutrality

**Description**: Compare brute force search results against IVF_FLAT-indexed search results

**Dataset**: Dataset 1 (Random vectors, 128D, 1000 entities)

**Sequence**:
1. Create collection
2. Insert 1000 entities
3. Search WITHOUT index (brute force baseline) → `results_before`
4. Create IVF_FLAT index
5. Load collection
6. Search WITH index → `results_after`
7. Compare results

**Oracle Evaluation**:
- **Hard Check**: Search succeeds after index
- **Quality Check**: Recall ≥ 0.80 (ALLOWED_DIFFERENCE if below)

**Priority**: HIGH

---

#### Test: idx-001_flat_001

**Name**: FLAT Baseline

**Description**: Verify FLAT index produces near-exact results (should be ≈1.0 recall)

**Dataset**: Dataset 1 (Random vectors, 128D, 1000 entities)

**Sequence**:
1. Create collection
2. Insert 1000 entities
3. Search WITHOUT index (brute force baseline) → `results_before`
4. Create FLAT index
5. Load collection
6. Search WITH index → `results_after`
7. Compare results

**Oracle Evaluation**:
- **Hard Check**: Search succeeds after index
- **Quality Check**: Recall ≥ 0.99 (ALLOWED_DIFFERENCE if below, but unexpected for FLAT)

**Priority**: HIGH

**Note**: FLAT is exact search; recall should be near 1.0. Low recall here would be surprising.

---

#### Test: idx-001_ann_recall_001

**Name**: ANN Recall on Clustered Data

**Description**: Test ANN recall on more challenging clustered data structure

**Dataset**: Dataset 2 (Clustered vectors, 128D, 500 entities, 5 clusters)

**Sequence**:
1. Create collection
2. Insert 500 entities (clustered)
3. Search WITHOUT index (brute force baseline) → `results_before`
4. Create HNSW index
5. Load collection
6. Search WITH index → `results_after`
7. Compare results

**Oracle Evaluation**:
- **Hard Check**: Search succeeds after index
- **Quality Check**: Recall ≥ 0.80 (ALLOWED_DIFFERENCE if below)

**Priority**: MEDIUM

**Note**: Clustered data is more challenging for ANN; expect lower recall than random data.

---

### IDX-002 Tests (2 tests)

#### Test: idx-002_create_001

**Name**: Data Count After HNSW Creation

**Description**: Verify entity count preserved after HNSW index creation

**Dataset**: Dataset 1 (Random vectors, 128D, 1000 entities)

**Sequence**:
1. Create collection
2. Insert 1000 entities
3. Get entity count → `count_before`
4. Create HNSW index
5. Get entity count → `count_after`
6. Verify count_before == count_after

**Oracle Evaluation**:
- Check: `count_before == count_after`
- Pass: Counts match
- Violation: Counts differ (data loss or corruption)

**Priority**: HIGH

---

#### Test: idx-002_create_002

**Name**: Data Count After IVF Creation

**Description**: Verify entity count preserved after IVF_FLAT index creation

**Dataset**: Dataset 1 (Random vectors, 128D, 1000 entities)

**Sequence**:
1. Create collection
2. Insert 1000 entities
3. Get entity count → `count_before`
4. Create IVF_FLAT index
5. Get entity count → `count_after`
6. Verify count_before == count_after

**Oracle Evaluation**:
- Check: `count_before == count_after`
- Pass: Counts match
- Violation: Counts differ (data loss or corruption)

**Priority**: HIGH

---

## 4. Dataset Design

### Dataset 1: Random Vectors (Primary)

**Purpose**: General-purpose testing for semantic neutrality and data preservation

**Configuration**:
- **Dimension**: 128
- **Entity Count**: 1000
- **Generation Method**: Uniform random distribution [-1, 1]
- **Seed**: 42 (deterministic)

**Usage**:
- IDX-001: All tests except clustered test
- IDX-002: Both tests

---

### Dataset 2: Clustered Vectors (Secondary)

**Purpose**: Test ANN recall with more challenging data structure

**Configuration**:
- **Dimension**: 128
- **Entity Count**: 500
- **Generation Method**: 5 clusters with random assignment
  - Cluster centers: [±1, ±1, ...] at corners of hypercube
  - Points around centers with Gaussian noise (σ=0.1)
- **Seed**: 42 (deterministic)

**Usage**:
- IDX-001: idx-001_ann_recall_001 only

**Rationale**: Clustered data challenges ANN approximation more than uniform random data.

---

## 5. Oracle Implementation

### Refined IDX-001 Oracle

```python
def _oracle_semantic_neutrality_refined(
    self,
    result: Dict[str, Any],
    contract: Optional[Dict[str, Any]]
) -> OracleResult:
    """Oracle: Index must not change semantic results (refined).

    Separates hard contract checks from approximate quality checks.

    Hard Checks (must pass for VIOLATION-free):
    - Search succeeds after index
    - Results not empty (unless before was empty)

    Quality Checks (documented, not VIOLATION):
    - FLAT: recall ≥ 0.99 (exact search)
    - HNSW: recall ≥ 0.85 (typical ANN)
    - IVF_FLAT: recall ≥ 0.80 (typical ANN)

    Classification:
    - Hard check fail → VIOLATION (BUG)
    - Low recall → ALLOWED_DIFFERENCE (not a bug)
    """
    results_before = result.get("results_before_index", [])
    results_after = result.get("results_after_index", [])
    index_type = result.get("index_type", "UNKNOWN")

    # ========== HARD CHECKS ==========
    # Check 1: Search succeeded
    if results_after is None:
        return self._oracle_result(
            contract["contract_id"] if contract else "idx-001",
            Classification.VIOLATION,
            False,
            "Search failed after index creation (HARD CHECK FAILED)",
            {
                "hard_check": "search_succeeds",
                "result": "FAILED",
                "classification": "VIOLATION"
            }
        )

    # Check 2: Results not empty (unless before was empty)
    before_empty = len(results_before) == 0
    after_empty = len(results_after) == 0

    if not before_empty and after_empty:
        return self._oracle_result(
            contract["contract_id"] if contract else "idx-001",
            Classification.VIOLATION,
            False,
            "Index caused search to return empty results (HARD CHECK FAILED)",
            {
                "hard_check": "results_not_empty",
                "result": "FAILED",
                "classification": "VIOLATION"
            }
        )

    # ========== QUALITY CHECKS ==========
    before_ids = set(r.get("id") for r in results_before)
    after_ids = set(r.get("id") for r in results_after)

    if len(before_ids) > 0:
        recall = len(before_ids & after_ids) / len(before_ids)
    else:
        recall = 1.0

    # Index-type-specific recall thresholds
    RECALL_THRESHOLDS = {
        "FLAT": 0.99,
        "HNSW": 0.85,
        "IVF_FLAT": 0.80,
        "IVF_SQ8": 0.75,
        "UNKNOWN": 0.80
    }

    expected_recall = RECALL_THRESHOLDS.get(index_type, 0.80)

    # Quality classification (NOT VIOLATION)
    if recall >= expected_recall:
        quality_status = "PASS"
        quality_msg = f"Recall {recall:.3f} ≥ {expected_recall:.2f} for {index_type}"
    else:
        quality_status = "ALLOWED_DIFFERENCE"
        quality_msg = f"Recall {recall:.3f} < {expected_recall:.2f} for {index_type} (within ANN tolerance)"

    return self._oracle_result(
        contract["contract_id"] if contract else "idx-001",
        Classification.PASS,  # Hard checks passed
        True,
        f"Hard checks PASSED. Quality: {quality_msg}",
        {
            "hard_checks": "PASSED",
            "quality_classification": quality_status,
            "recall": recall,
            "expected_recall": expected_recall,
            "index_type": index_type,
            "note": "Low recall is ALLOWED_DIFFERENCE, not VIOLATION"
        }
    )
```

---

### IDX-002 Oracle (Unchanged)

```python
def _oracle_data_preservation(
    self,
    result: Dict[str, Any],
    contract: Optional[Dict[str, Any]]
) -> OracleResult:
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
        {
            "count_before": count_before,
            "count_after": count_after,
            "preserved": passed
        }
    )
```

---

## 6. Execution Plan

### Phase 0: Prerequisites (30 minutes)

1. **Implement Refined IDX-001 Oracle**
   - File: `core/oracle_engine.py`
   - Replace `_oracle_semantic_neutrality` with refined version
   - Add hard checks and quality checks separation

2. **Add Count Retrieval to Milvus Adapter**
   - File: `adapters/milvus_adapter.py`
   - Add method to get entity count from collection
   - Use `collection.num_entities`

---

### Phase 1: Dataset Generation (15 minutes)

1. Generate Dataset 1 (random vectors, 1000 entities)
2. Generate Dataset 2 (clustered vectors, 500 entities)
3. Store as JSON for reproducibility

---

### Phase 2: Test Generation (30 minutes)

1. Generate IDX-001 tests (4 tests)
2. Generate IDX-002 tests (2 tests)
3. Attach refined oracle definitions
4. Output: `generated_tests/index_pilot_revised_<timestamp>.json`

---

### Phase 3: Execution (45-60 minutes)

1. Execute IDX-001 tests (4 tests)
2. Execute IDX-002 tests (2 tests)
3. Collect results and evidence
4. Verify all 6 tests complete

---

### Phase 4: Analysis and Reporting (30 minutes)

1. Classify results (PASS, VIOLATION, ALLOWED_DIFFERENCE)
2. Identify any contract violations
3. Assess oracle accuracy
4. Generate report: `docs/R5B_INDEX_PILOT_REPORT_REVISED.md`

---

## 7. Expected Outcomes

### Test Execution Estimates

| Metric | Estimate |
|--------|----------|
| **Total Test Cases** | 6 |
| **Estimated Execution Time** | 45-60 minutes |
| **Expected Hard Check Pass Rate** | 100% (no data corruption expected) |
| **Expected Quality Check Pass Rate** | 80-95% (ANN recall typically in range) |
| **Expected VIOLATIONS** | 0-1 (unlikely but possible) |

---

### Classification Distribution Forecast

| Classification | Expected Count | Rationale |
|----------------|----------------|-----------|
| **PASS** | 4-5 | Hard checks pass; quality within expected ranges |
| **ALLOWED_DIFFERENCE** | 1-2 | Low ANN recall documented, not bugs |
| **VIOLATION** | 0-1 | Unlikely but possible (e.g., empty results after index) |
| **OBSERVATION** | 0 | All oracles well-defined |

---

## 8. Success Criteria

### Primary Success Criteria

1. ✅ All 6 tests execute successfully
2. ✅ Refined IDX-001 oracle correctly classifies results
3. ✅ No false violations from ANN approximation tolerance
4. ✅ Hard checks (data integrity) verified correctly

### Secondary Success Criteria

1. ⚠️ At least 1 ALLOWED_DIFFERENCE classification (validates oracle refinement)
2. ⚠️ Clear documentation of ANN recall behavior per index type

### Failure Criteria

1. ❌ Infrastructure failures prevent execution
2. ❌ Oracle misclassifies hard failures as ALLOWED_DIFFERENCE
3. ❌ False violations from ANN approximation

---

## 9. Comparison to Original Design

| Aspect | Original | Revised | Change |
|--------|----------|---------|--------|
| **Test Count** | 16 | 6 | -10 tests |
| **Contracts** | 4 | 2 | IDX-003, IDX-004 postponed |
| **Oracle Design** | Single threshold | Hard + quality checks | Soundness improved |
| **ANN Recall Classification** | VIOLATION if < 0.9 | ALLOWED_DIFFERENCE | No false bugs |
| **Adapter Requirements** | Drop, rebuild, multi-index | Count retrieval only | Simpler |
| **Execution Time** | 60-90 min | 45-60 min | Faster |
| **Bug Yield Potential** | MEDIUM-HIGH | MEDIUM | Slightly reduced |

---

## 10. Post-Pilot Next Steps

### If Violations Found

1. Document with full evidence
2. Create issue reports for Milvus team
3. Consider expanding to full scope when adapter supports it

### If No Violations (Expected Outcome)

1. Document that index behavior is correct on tested operations
2. Classify IDX-001 and IDX-002 as correctness validation contracts
3. **Proceed to R5D** (Schema/Metadata contracts)
4. Plan adapter enhancements for IDX-003 and IDX-004

### Adapter Enhancements for Full R5B

| Enhancement | Effort | Enables |
|-------------|--------|---------|
| Add count retrieval | LOW | IDX-002 (done in Phase 0) |
| Implement drop_index | MEDIUM | IDX-002 full scope |
| Expose HNSW/IVF parameters | MEDIUM | IDX-003 full scope |
| Add list_indexes | MEDIUM | IDX-004 testing |
| Add index_info query | MEDIUM | IDX-004 determinism testing |

---

## 11. Risk Assessment

### Resolved Risks

| Risk | Resolution |
|------|------------|
| IDX-001 oracle unsoundness | Refined oracle separates hard from quality checks |
| IDX-003 false confidence | Postponed until parameters exposed |
| IDX-004 not testable | Postponed until multi-index support added |

### Remaining Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Count retrieval not implemented | MEDIUM | HIGH | Add in Phase 0 (prerequisite) |
| FLAT index not available | LOW | MEDIUM | Use pre-index search as baseline |
| ANN recall below thresholds | MEDIUM | LOW | Classify as ALLOWED_DIFFERENCE |
| Milvus doesn't support index-free search | LOW | MEDIUM | Use small collection (brute force is fast) |

---

## 12. Deliverables

### Artifacts

1. **Test Specification**: `generated_tests/index_pilot_revised_<timestamp>.json`
2. **Execution Results**: `results/index_pilot_revised_<timestamp>.json`
3. **Pilot Report**: `docs/R5B_INDEX_PILOT_REPORT_REVISED.md`

### Report Contents

- Test execution summary (6 tests)
- Per-contract results with refined oracle classifications
- Hard check results (all should pass)
- Quality check results with recall measurements by index type
- Comparison of ANN recall across HNSW, IVF_FLAT, and FLAT
- Issue candidates (if any violations)
- Recommendations for next steps (R5D or adapter enhancements)

---

## 13. Acceptance Checklist

The revised R5B pilot is ready for execution when:

- [ ] Refined IDX-001 oracle implemented in `core/oracle_engine.py`
- [ ] Count retrieval added to `adapters/milvus_adapter.py`
- [ ] Test generator produces exactly 6 tests
- [ ] All IDX-001 tests use refined oracle with index-type-specific thresholds
- [ ] Documentation reflects revised scope
- [ ] Prerequisites (Phase 0) completed

---

**Revised Pilot Design Version**: 1.0
**Date**: 2026-03-10
**Based On**: Pre-Implementation Audit findings
**Status**: READY FOR IMPLEMENTATION (Phase 0 prerequisites first)
**Next Action**: Implement refined oracle and count retrieval, then execute

---

## Appendix: Summary of Changes from Original Design

### What Was Removed

1. **IDX-003 Tests** (4 tests)
   - Invalid parameter testing beyond index_type/metric_type
   - Numeric parameter validation (M, nlist, efConstruction)
   - Reason: Parameters not exposed in adapter; would give false confidence

2. **IDX-004 Tests** (3 tests)
   - Multiple index coexistence testing
   - Index selection determinism
   - Reason: No multi-index support in adapter

3. **IDX-002 Tests** (3 tests)
   - Index drop data preservation
   - Index rebuild data preservation
   - Full index cycle testing
   - Reason: drop_index and rebuild_index not implemented

### What Was Added

1. **Refined IDX-001 Oracle**
   - Hard checks (search succeeds, results not empty)
   - Quality checks (index-type-specific thresholds)
   - ALLOWED_DIFFERENCE classification for low recall
   - Soundness: No false violations from ANN approximation

2. **Prerequisites Phase**
   - Oracle implementation task
   - Adapter enhancement task (count retrieval)

### Net Change

| Metric | Original | Revised | Delta |
|--------|----------|---------|-------|
| Tests | 16 | 6 | -10 |
| Contracts | 4 | 2 | -2 |
| Oracle Soundness | Unsound | Sound | Improved |
| Adapter Changes | 0 | 1 (count) | +1 |
| Implementation Time | 2-3 hrs | 1.5-2 hrs | Faster |
