# R6A-001 Final Summary Report

**Campaign ID**: R6A-001
**Campaign Name**: r6a_consistency_visibility
**Database**: Milvus v2.6.10
**Status**: COMPLETE & PHASE-CLOSED

---

## Executive Summary

R6A-001 First Slice successfully established the CONS (Consistency / Visibility) contract family baseline for Milvus v2.6.10.

**Total Cases**: 6
**Final Classification**: 2 PASS, 4 OBSERVATION
**Recommendation**: Phase-close R6A first slice.

---

## Final Contract Status (Tightened)

| Contract ID | Name | Status | Confidence | Classification |
|-------------|------|--------|------------|----------------|
| **CONS-001** | Insert Return vs Storage Visibility | OBSERVATION | HIGH | Milvus-validated |
| **CONS-002** | Storage-Visible vs Search-Visible | OBSERVATION | HIGH | Milvus-validated |
| **CONS-003** | Load/Release/Reload Gate | PASS | HIGH | **Framework-level candidate**, Milvus-validated |
| **CONS-004** | Insert-Search Timing Window | OBSERVATION | MEDIUM | Milvus-validated, tested path only |
| **CONS-005** | Release Preserves Storage Data | PASS | HIGH | **Framework-level candidate**, Milvus-validated |
| **CONS-006** | Repeated Flush Stability | OBSERVATION | MEDIUM | Milvus-validated, tested path only |

**Classification Definitions**:
- **PASS**: Expected behavior confirmed with high confidence
- **OBSERVATION**: Deterministic behavior documented (implementation-specific or tested-path-only)
- **Framework-level candidate**: Architecturally expected across implementations, but only Milvus-validated
- **Milvus-validated**: Validated on Milvus v2.6.10 only

---

## Test Results (All 6 Cases)

### R6A-001: CONS-001 Insert Return vs Storage Visibility

**Classification**: OBSERVATION (Milvus-validated)

**Evidence**:
- insert_count: 5 (immediate return)
- num_entities pre-flush: 0
- num_entities post-flush: 5

**Conclusion**: insert() returns immediate metadata; flush enables storage_count visibility.

---

### R6A-002: CONS-002 Storage-Visible vs Search-Visible

**Classification**: OBSERVATION (Milvus-validated)

**Evidence**:
- storage_count post-flush: 5
- search without load: error (collection not loaded)
- search with load: 5

**Conclusion**: Two-stage visibility: flush → storage-visible; load → search-visible.

---

### R6A-003: CONS-003 Load/Release/Reload Gate

**Classification**: PASS (Framework-level candidate, Milvus-validated)

**Evidence**:
- search unloaded: error (load gate enforced)
- search after reload: matches baseline

**Conclusion**: Load gate enforced; reload restores search. Architecturally expected behavior.

---

### R6A-004: CONS-004 Insert-Search Timing Window

**Classification**: OBSERVATION (Milvus-validated, tested path only)

**Evidence**:
- search t=0 (immediate): 0 results
- search t=1s (after wait): 0 results
- search after flush: 5 results

**Conclusion** (Tightened): Within the tested 1-second window, wait alone did not enable search visibility; flush was required in this tested path.

**Note**: This applies only to the tested path (1s wait, no flush). Does not make claims about longer wait windows or other configurations.

---

### R6A-005: CONS-005 Release Preserves Storage Data

**Classification**: PASS (Framework-level candidate, Milvus-validated)

**Evidence**:
- storage_count baseline: 5
- storage_count after release: 5 (unchanged)
- search after reload: matches baseline

**Conclusion**: Release preserves storage; reload restores search. Architecturally expected behavior.

---

### R6A-006: CONS-006 Repeated Flush Stability

**Classification**: OBSERVATION (Milvus-validated, tested path only)

**Evidence**:
- storage state: 5 → 5 (unchanged)
- search state: 5 → 5 (unchanged)

**Conclusion**: Repeated flush doesn't introduce contradictory visibility regressions in tested path.

---

## Contract Classification Summary

### By Status

| Status | Count | Contracts |
|--------|-------|-----------|
| **PASS** | 2 | CONS-003, CONS-005 |
| **OBSERVATION** | 4 | CONS-001, CONS-002, CONS-004, CONS-006 |

### By Category

| Category | Count | Contracts |
|----------|-------|-----------|
| **Framework-level candidate (Milvus-validated)** | 2 | CONS-003, CONS-005 |
| **Milvus-validated (documented behavior)** | 4 | CONS-001, CONS-002, CONS-004, CONS-006 |

### By Confidence

| Confidence | Count | Contracts |
|------------|-------|-----------|
| **HIGH** | 4 | CONS-001, CONS-002, CONS-003, CONS-005 |
| **MEDIUM** | 2 | CONS-004, CONS-006 |

---

## Credible Conclusions

### High Confidence (Milvus v2.6.10)

1. **Load Gate Enforcement** (CONS-003: PASS)
   - Search fails on unloaded collection
   - Reload restores search capability
   - Data preserved across release/reload
   - **Framework-level candidate**

2. **Data Preservation** (CONS-005: PASS)
   - Release preserves storage count
   - Reload restores search visibility
   - **Framework-level candidate**

3. **Deferred Storage Visibility** (CONS-001: OBSERVATION)
   - insert_count returns immediately (metadata)
   - num_entities requires flush (storage-visible)

4. **Two-Stage Visibility** (CONS-002: OBSERVATION)
   - Flush enables storage-visible
   - Load controls search-visible

### Medium Confidence (Tested Path Only)

5. **Flush Requirement Timing** (CONS-004: OBSERVATION)
   - Within tested 1s window: wait alone insufficient
   - Flush required in tested path
   - **Tested path only**: doesn't generalize to all timing windows

6. **Flush Stability** (CONS-006: OBSERVATION)
   - Repeated flush doesn't regress in tested path
   - **Tested path only**: doesn't cover all scenarios

---

## What R6A Did NOT Validate

- Timing behavior beyond 1-second wait window
- Concurrent operations
- Edge cases (empty collections, large datasets, index rebuilds)
- Cross-database behavior
- Distributed consistency

---

## Recommendation: Phase-Close R6A First Slice

**Status**: R6A First Slice is COMPLETE and PHASE-CLOSED.

**Rationale**:
1. All 6 cases produced interpretable results
2. CONS family baseline established
3. 2 framework-level candidates identified (Milvus-validated only)
4. 4 documented behaviors (implementation-specific)
5. No BUG_CANDIDATE or EXPERIMENT_DESIGN_ISSUE

**Do NOT expand R6A** unless:
- Clear product requirement for deeper timing analysis
- Need for cross-database validation
- Edge case testing required

---

## Next Steps (Optional)

If expanding R6A, consider:
1. Longer timing windows (5s, 10s, 30s)
2. Concurrent operations
3. Edge cases
4. Cross-database validation

**However**: These are NOT recommended without clear requirements. The first slice successfully validated core consistency/visibility semantics.

---

## Files Modified

- `campaigns/r6a_consistency/` - Campaign artifacts
- `contracts/cons/r6a_001_contracts.json` - Contract definitions
- `casegen/generators/r6a_001_generator.py` - Generator
- `pipeline/oracles/r6a_001_oracle.py` - Oracle
- `scripts/run_r6a_001_smoke.py` - Smoke runner
- `results/r6a_*.json` - Test results
- `docs/reports/R6A_FINAL_SUMMARY.md` - This file

---

## Conclusion

R6A-001 First Slice successfully established the CONS contract family baseline for Milvus v2.6.10. With 2 PASS and 4 OBSERVATION classifications across 6 test cases, all producing interpretable results.

**Status**: R6A First Slice COMPLETE and PHASE-CLOSED.
