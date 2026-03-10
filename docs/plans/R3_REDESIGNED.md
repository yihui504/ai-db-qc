# Campaign R3: Revised Direction

**Date**: 2026-03-08
**Status**: PLANNED BUT NOT EXECUTED - Option A chosen (Postpone R3 until adapter enhanced)

> **Decision**: R3 is postponed. Option B (Operation Sequences) was proposed as an alternative direction, but the session stopped before execution. See `docs/R3_DECISION_STATUS.md` for full context.

---

## Audit Summary

**Critical Finding**: ALL four planned R3 parameter families have **adapter support issues**:

| Parameter | Issue | Status |
|-----------|-------|--------|
| **consistency_level** | Silent-ignore via **kwargs (like metric_type) | NOT SUITABLE |
| **index_params.nlist** | Adapter hardcodes nlist=128 | NOT SUITABLE |
| **index_params.m** | Adapter hardcodes nlist-based params | NOT SUITABLE |
| **search_params.nprobe** | Adapter hardcodes nprobe=10 | NOT SUITABLE |

**Full audit**: `docs/tooling_gaps/R3_PARAMETER_SUPPORT_AUDIT.md`

---

## Redesigned R3 Strategy

Given the adapter support gaps, R3 has three options:

### Option A: Postpone R3 Until Adapter Enhanced

**Pros**:
- Ensures test correctness (primary goal)
- Avoids tool-layer artifacts
- Aligns with proposal goal of "test-case correctness judgment"

**Cons**:
- Requires adapter development work first
- Delays R3 execution

**Work Required**:
1. Enhance MilvusAdapter to support custom index_params
2. Enhance MilvusAdapter to support custom search_params
3. Verify which Collection parameters are actually supported
4. Re-audit after adapter changes

---

### Option B: Redesign R3 Using CURRENTLY Supported Features

**Test parameters the adapter CURRENTLY supports:**

| Parameter | Status | Test Cases |
|-----------|--------|------------|
| **dimension** | ✅ Fully supported | Already tested in R1 (boundary=0, overflow=32769) |
| **top_k** | ✅ Fully supported | Already tested in R1 (negative, zero, absurd values) |
| **metric_type** | ⚠️ Silent-ignore | Documented, but creates misleading results |
| **filter** | ✅ Partially supported | Tested in R2 (invalid field) |
| **index_type** | ✅ Partially supported | Tested in R2 (invalid enum, empty string) |

**New R3 Focus**: Operation Sequences and State Transitions

Test **sequences of operations** rather than individual parameter validation:

| Case ID | Sequence | Test Focus |
|---------|----------|------------|
| seq-001 | create → insert → search → delete → delete | Basic lifecycle (idempotency of delete) |
| seq-002 | create → insert → create_index → search → drop | Index creation state dependency |
| seq-003 | create → insert → load → search → unload → drop | Load/unload state transitions |
| seq-004 | create → insert → create → drop | Duplicate creation state (idempotency) |

**Pros**:
- Uses currently-supported features
- Tests actual workflows, not parameter validation
- Avoids kwargs/unclear parameter issues
- Aligns with "test-case correctness judgment" goal

**Cons**:
- Different from original parameter validation focus
- May have different bug yield profile

---

### Option C: Redesign R3 as Cross-Database Campaign

**Compare Milvus vs SeekDB on identical operations:**

| Operation | Test Focus |
|-----------|------------|
| diff-001 | create_collection with same schema |
| diff-002 | insert with same data |
| diff-003 | search with same query |
| diff-004 | build_index with same parameters |

**Pros**:
- Uses existing differential workflow
- Tests actual database behavior
- Validates differential assertions

**Cons**:
- Requires SeekDB adapter setup
- May have similar adapter support issues

---

## Recommended Approach: Option B (Operation Sequences)

**Rationale**:
1. Supports primary goal of "test-case correctness judgment"
2. Uses currently-supported features (no adapter modifications needed)
3. Tests meaningful workflows (not just parameter validation)
4. Avoids silent-ignore/kwargs issues that plagued R1+R2

---

## Revised R3 Case List (Option B - Operation Sequences)

### PRIMARY CASES (6-7)

```
seq-001  create→insert→search→delete→delete    Duplicate delete idempotency
seq-002  create→insert→index→search→drop      Index state dependency
seq-003  create→insert→load→search→unload→drop  Load/unload state transitions
seq-004  create→insert→create→drop              Duplicate creation idempotency
seq-005  create→insert→search→drop→search      Search after drop (state bug)
seq-006  create→insert→load→drop→search         Search after drop without load (precondition)
```

### CALIBRATION CASES (2-3)

```
cal-seq-001  create→insert→search                Basic lifecycle (no issues expected)
cal-seq-002  create→insert→drop               Basic cleanup (no issues expected)
```

**Total**: 8-9 cases

---

## Expected Yield (Operation Sequences)

**Minimum success**: >=1 state-transition or idempotency issue

**Stretch success**: 2-3 issues

**Hypothesis**: Operation sequences may reveal:
- Idempotency violations (operations not truly idempotent)
- State dependency bugs (operations succeed when they shouldn't)
- Precondition bypass (operations succeed in wrong state)

---

## Success Criteria

### Minimum Success
- All cases execute without framework errors
- At least 1 issue-ready candidate found
- Calibration cases pass as expected

### Stretch Success
- 2-3 issue-ready candidates
- State-transition or idempotency weakness confirmed

---

## R3 Readiness Checklist

### Required Before Execution

- [ ] Sequence test framework implemented (new capability)
- [ ] Precondition evaluation handles state transitions
- [ ] Oracle can detect state violations
- [ ] Triage can classify state-transition bugs

### Adapter Status
- [x] create_collection: ✅ Working
- [x] insert: ✅ Working
- [x] search: ✅ Working
- [x] build_index: ✅ Working (with limitations)
- [x] load: ✅ Working
- [x] drop_collection: ✅ Working
- [x] delete: ✅ Working

**All required operations are supported.**

---

## Decision Point

**DECISION MADE (2026-03-08)**: **Option A - Postpone R3 until adapter enhanced**

**Rationale**:
- Testing parameters with adapter gaps produces tool-layer artifacts, not database bugs
- Primary goal is "test-case correctness judgment," not raw execution volume
- Pre-execution audit prevented another metric_type-style misclassification

**Option B (Operation Sequences) remains available** as an alternative direction for future sessions.

**See**: `docs/R3_DECISION_STATUS.md` for complete decision record and next-session options.

---

## Metadata

- **Original Design**: Parameter validation focus
- **Blocked By**: 4 adapter support gaps (TOOLING-002, TOOLING-003, TOOLING-004)
- **Redesigned Focus**: Operation sequences and state transitions (Option B proposal)
- **Case Count**: 8-9 cases (reduced from 10)
- **Status**: **POSTPONED** - Option A chosen (enhance adapter first)
- **Decision Date**: 2026-03-08
- **See**: `docs/R3_DECISION_STATUS.md` for full decision rationale
