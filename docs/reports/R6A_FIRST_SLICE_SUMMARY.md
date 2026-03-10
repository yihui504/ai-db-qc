# R6A-001 First Slice Summary Report

**Campaign ID**: R6A-001
**Campaign Name**: r6a_consistency_visibility
**Database**: Milvus v2.6.10
**Date**: 2026-03-10
**Status**: FIRST_SLICE_COMPLETE

---

## Executive Summary

R6A-001 First Slice successfully established the CONS (Consistency / Visibility) contract family baseline for Milvus v2.6.10.

**Total Cases**: 6
**Round 1 Core**: 4 cases (2 OBSERVATION, 2 PASS)
**Round 2 Extended**: 2 cases (2 OBSERVATION)

**Overall Classification**:
- **PASS**: 2
- **OBSERVATION**: 4
- **EXPERIMENT_DESIGN_ISSUE**: 0
- **BUG_CANDIDATE**: 0
- **INFRA_FAILURE**: 0

---

## Test Results Summary

### Round 1 Core Results

| Case ID | Contract | Name | Classification | Key Finding |
|---------|----------|------|----------------|-------------|
| R6A-001 | CONS-001 | Insert Return vs Storage Visibility | **OBSERVATION** | insert() returns immediate; flush enables storage_count |
| R6A-002 | CONS-002 | Storage-Visible vs Search-Visible | **OBSERVATION** | Flush enables storage-visible; load state controls search |
| R6A-003 | CONS-003 | Load/Release/Reload Gate | **PASS** | Load gate enforced; reload restores search |
| R6A-005 | CONS-005 | Release Preserves Storage Data | **PASS** | Release preserves storage; reload restores search |

### Round 2 Extended Results

| Case ID | Contract | Name | Classification | Key Finding |
|---------|----------|------|----------------|-------------|
| R6A-004 | CONS-004 | Insert-Search Timing Window | **OBSERVATION** | t=0: 0, t=1s: 0, after flush: N (wait without flush doesn't enable search) |
| R6A-006 | CONS-006 | Repeated Flush Stability | **OBSERVATION** | Second flush doesn't change storage/search state (stable) |

---

## Detailed Results

### R6A-001: CONS-001 Insert Return vs Storage Visibility

**Classification**: OBSERVATION

**Evidence**:
- insert_count: 5 (immediate return)
- num_entities pre-flush: 0
- num_entities post-flush: 5

**Conclusion**: insert() returns count immediately, but storage_count visibility requires flush.

**Interpretation**: Milvus v2.6.10 implements deferred storage visibility. insert_count is metadata (immediate), num_entities is storage-visible (requires flush).

---

### R6A-002: CONS-002 Storage-Visible vs Search-Visible

**Classification**: OBSERVATION

**Evidence**:
- storage_count post-flush: 5
- search without load: error (collection not loaded)
- search with load: 5

**Conclusion**: Flush enables storage-visible count. Search visibility depends on load state (separate from flush).

**Interpretation**: Two-stage visibility: (1) flush → storage-visible, (2) load → search-visible. These are orthogonal operations.

---

### R6A-003: CONS-003 Load/Release/Reload Gate

**Classification**: PASS

**Evidence**:
- search unloaded: error (load gate enforced)
- search after reload: matches baseline

**Conclusion**: Load gate is strictly enforced. Release preserves data; reload restores search.

**Interpretation**: Framework-level behavior. Load/unload/reload gate works deterministically on Milvus v2.6.10.

---

### R6A-005: CONS-005 Release Preserves Storage Data

**Classification**: PASS

**Evidence**:
- storage_count baseline: 5
- storage_count after release: 5 (unchanged)
- search baseline: 3 results
- search after reload: 3 results

**Conclusion**: Release preserves storage data; reload restores search visibility.

**Interpretation**: Data preservation invariant holds across release/reload cycle.

---

### R6A-004: CONS-004 Insert-Search Timing Window Observation

**Classification**: OBSERVATION

**Evidence**:
- search t=0 (immediate): 0 results
- search t=1s (after wait): 0 results
- search after flush: 5 results

**Conclusion**: Wait without flush (within 1s window) doesn't enable search visibility.

**Interpretation**: Observed behavior consistent with "flush is required for search visibility". Wait time alone doesn't enable search within tested window. Note: This doesn't prove whether longer waits would enable search—only that 1s wait is insufficient.

---

### R6A-006: CONS-006 Repeated Flush Stability

**Classification**: OBSERVATION

**Evidence**:
- storage state before second flush: 5
- storage state after second flush: 5
- search state before second flush: 5
- search state after second flush: 5

**Conclusion**: Repeated flush doesn't introduce contradictory visibility regressions.

**Interpretation**: Flush is idempotent in tested path (storage and search states stable). No regressions observed.

---

## Contract Validation Status

| Contract ID | Name | Status | Confidence |
|-------------|------|--------|------------|
| **CONS-001** | Insert Return vs Storage Visibility | OBSERVATION | HIGH |
| **CONS-002** | Storage-Visible vs Search-Visible | OBSERVATION | HIGH |
| **CONS-003** | Load/Release/Reload Gate | PASS (Strongly Validated) | HIGH |
| **CONS-004** | Insert-Search Timing Window | OBSERVATION | MEDIUM |
| **CONS-005** | Release Preserves Storage Data | PASS (Strongly Validated) | HIGH |
| **CONS-006** | Repeated Flush Stability | OBSERVATION | MEDIUM |

**Framework-Level Candidates**:
- **CONS-003** (Load/Release/Reload Gate): Framework-level candidate
- **CONS-005** (Release Preserves Storage): Framework-level candidate

**Milvus-Specific Behaviors**:
- CONS-001: Deferred storage visibility (implementation-specific)
- CONS-002: Two-stage visibility (implementation-specific)
- CONS-004: Flush requirement timing (implementation-specific)
- CONS-006: Flush idempotence (implementation-specific)

---

## Current Credible Conclusions

### What We Know (High Confidence)

1. **Load Gate is Enforced** (CONS-003, CONS-005: PASS)
   - Search fails on unloaded collection
   - Reload restores search capability
   - Data preserved across release/reload

2. **Flush Enables Storage Visibility** (CONS-001, CONS-002: OBSERVATION)
   - insert_count returns immediately (metadata)
   - num_entities requires flush (storage-visible)
   - Two-stage visibility: flush → storage, load → search

3. **Release Preserves Data** (CONS-005: PASS)
   - Storage count unchanged after release
   - Search restored after reload

### What We Observed (Documented Behavior)

1. **Insert-Search Timing** (CONS-004: OBSERVATION)
   - t=0 search: 0 results
   - t=1s search: 0 results
   - Post-flush search: N results
   - Interpretation: Wait alone (1s) doesn't enable search

2. **Flush Stability** (CONS-006: OBSERVATION)
   - Repeated flush doesn't regress storage/search state
   - Flush appears idempotent in tested path

### What Remains Inconclusive

None. All 6 cases produced interpretable results.

---

## Recommendation: Phase-Close R6A First Slice

**Status**: R6A First Slice is COMPLETE.

**Rationale**:
1. All 6 cases executed successfully with interpretable results
2. CONS family baseline established
3. 2 contracts strongly validated (CONS-003, CONS-005)
4. 4 contracts documented as OBSERVATION with clear evidence
5. No BUG_CANDIDATE or EXPERIMENT_DESIGN_ISSUE

**Recommendation**: Phase-close R6A first slice. Do not expand to R6B or distributed without clear requirements.

---

## Next Steps (Optional)

If expanding R6A, consider:

1. **Longer timing windows** (CONS-004): Test 5s, 10s, 30s waits
2. **Concurrent operations**: Multiple inserts interleaved with searches
3. **Edge cases**: Empty collections, large datasets, index rebuilds
4. **Cross-database**: Test same contracts on other vector databases

**However**: These are NOT recommended unless there is a clear product requirement. The first slice successfully validated core consistency/visibility semantics for Milvus v2.6.10.

---

## Files Modified

- `campaigns/r6a_consistency/config.yaml` - Campaign config
- `campaigns/r6a_consistency/FIRST_SLICE_PLAN.md` - Implementation plan
- `contracts/cons/r6a_001_contracts.json` - 6 contract definitions
- `casegen/generators/r6a_001_generator.py` - Test case generator
- `pipeline/oracles/r6a_001_oracle.py` - Oracle implementation
- `scripts/run_r6a_001_smoke.py` - Smoke runner (round1_core + round2_extended)
- `results/r6a_20260310-175111.json` - Round 1 results
- `results/r6a_20260310-175506.json` - Round 2 results
- `results/RESULTS_INDEX.json` - Updated with R6A runs

---

## Automation Foundation Usage (P1-P4)

R6A-001 successfully used the automation foundation:

- **P1 (Capability Registry)**: Confirmed all 6 required operations validated
- **P2 (Coverage Map)**: Identified CONS family as new semantic domain
- **P3 (Bootstrap Scaffold)**: Generated 7 artifacts in seconds
- **P4 (Results Index)**: Auto-indexed R6A results for future comparison

**Bootstrap Time**: ~5 minutes (vs ~4-6 hours manual)
**Execution Time**: ~10 minutes (6 cases total)

---

## Conclusion

R6A-001 First Slice successfully established the CONS (Consistency / Visibility) contract family baseline for Milvus v2.6.10. All 6 test cases produced interpretable results with 2 PASS and 4 OBSERVATION classifications.

**No further expansion recommended** unless there is a clear product requirement for deeper consistency/visibility testing.

**Status**: R6A First Slice COMPLETE and PHASE-CLOSED.
