# R6A-001 First Slice Plan (Revised)

**Campaign ID**: R6A-001
**Date**: 2026-03-10
**Status**: IMPLEMENTING

---

## Revisions (Tightening)

### 1. CONS-004 Tightened
**Before**: "wait without flush doesn't enable search" (预设强结论)
**After**: "observe insert-search visibility within tested wait window" (观察性)

- Default classification: OBSERVATION or EXPERIMENT_DESIGN_ISSUE
- Do not preset strong conclusions about timing behavior
- Document observed behavior only

### 2. CONS-006 Tightened
**Before**: "second flush has no effect" (绝对化)
**After**: "repeated flush should not introduce contradictory visibility regressions"

- Focus: no contradictory regressions in tested path
- Minimal evidence: storage/search state before/after second flush

### 3. CONS-002 vs CONS-003 Scope Clarified

| Contract | Focus | Separation |
|----------|-------|------------|
| **CONS-002** | Storage-visible vs Search-Visible | Flush enables storage; load state for search |
| **CONS-003** | Load/Release/Reload Gate | Load gate enforcement; data preservation |

### 4. Round Structure

| Round | Cases | Purpose |
|-------|-------|---------|
| **Round 1 Core** | R6A-001, R6A-002, R6A-003, R6A-005 | Establish CONS family baseline |
| **Round 2 Extended** | R6A-004, R6A-006 | Timing observation and flush stability |

---

## Round 1 Core Cases (4 cases)

### R6A-001: CONS-001 Insert Return vs Storage Visibility
**Operation Sequence**:
1. create_collection
2. insert (N=5)
3. check_insert_count
4. check_num_entities_pre_flush
5. flush
6. check_num_entities_post_flush

**Expected**: OBSERVATION
**Evidence**: insert_count=5, pre_flush=0or5, post_flush=5

---

### R6A-002: CONS-002 Storage-Visible vs Search-Visible
**Operation Sequence**:
1. create_collection (with index)
2. insert (N=5)
3. flush
4. check_storage_count
5. search_without_load
6. load
7. search_with_load

**Expected**: OBSERVATION
**Evidence**: storage=5, search_without=0/error, search_with=5

**Scope**: Flush enables storage-visible. Load state affects search (separate from CONS-003).

---

### R6A-003: CONS-003 Load/Release/Reload Gate
**Operation Sequence**:
1. create_collection (with index)
2. insert (N=3)
3. flush
4. build_index
5. load
6. search_baseline
7. release
8. verify_unloaded
9. search_unloaded (should fail)
10. reload
11. search_after_reload

**Expected**: PASS
**Evidence**: search_unloaded=EXPECTED_FAILURE, search_after_reload==baseline

**Scope**: Load gate enforcement. Data preservation across release/reload.

---

### R6A-005: CONS-005 Release Preserves Storage Data
**Operation Sequence**:
1. create_collection (with index)
2. insert (N=5)
3. flush
4. load
5. record_storage_count_baseline
6. search_baseline
7. release
8. check_storage_count_after_release
9. reload
10. search_after_reload

**Expected**: PASS
**Evidence**: storage_count unchanged, search_after_reload==baseline

---

## Round 2 Extended Cases (Deferred)

### R6A-004: CONS-004 Insert-Search Timing Window Observation
**Purpose**: Observe insert-search visibility within tested wait window

**Expected**: OBSERVATION or EXPERIMENT_DESIGN_ISSUE
**Note**: No strong conclusion预设. Document observed behavior only.

---

### R6A-006: CONS-006 Repeated Flush Stability
**Purpose**: Verify repeated flush doesn't introduce contradictory regressions

**Expected**: OBSERVATION
**Note**: Check storage/search state before/after second flush.

---

## Oracle Classifications (Supported)

| Classification | Meaning | Usage |
|----------------|---------|-------|
| **PASS** | Expected behavior confirmed | STRICT invariants (data preservation, load gate) |
| **OBSERVATION** | Deterministic behavior documented | Timing behavior, implementation-specific |
| **EXPERIMENT_DESIGN_ISSUE** | Test setup invalid | Precondition violation, data missing |
| **BUG_CANDIDATE** | Unexpected behavior requiring investigation | Data loss, non-deterministic results, gate violation |
| **INFRA_FAILURE** | Infrastructure issue (not a semantic bug) | Connection failure, timeout |
| **EXPECTED_FAILURE** | Precondition gate violation (intentional test) | Testing unload gate |

---

## Implementation Status

- [x] Contract definitions (revised)
- [x] Generator (round1_core only)
- [x] Oracle (all 6 contracts)
- [x] Smoke runner (implemented)
- [ ] First smoke execution

---

## Next Steps

1. Run first smoke (round 1 core: 4 cases)
2. Update results index (P4)
3. Generate R6A initial report
4. Review round 1 results before round 2
