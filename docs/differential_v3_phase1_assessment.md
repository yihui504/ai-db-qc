# Differential v3 Phase 1 Assessment

> **Run ID**: differential-v3-phase1-20260307_233850
> **Date**: 2026-03-07
> **Cases**: 6 capability-boundary cases
> **Stop Point**: Phase 1 complete - evaluating before proceeding to Phase 2

---

## Executive Summary

| Metric | Result | Target (Minimum) | Target (Stretch) | Status |
|--------|--------|------------------|------------------|--------|
| Genuine behavioral differences | 0 | ≥2 | ≥3 | ❌ Below minimum |
| Noise pollution | 67% (4/6) | ≤10% | <5% | ❌ Above target |
| Issue-ready candidates | 2 (Type-1) | ≥1 | ≥1 | ✅ Exceeded minimum |
| Paper-worthy cases | 0 | ≥1 | ≥1 | ❌ Below minimum |

**Recommendation**: Fix template setup issues, re-run Phase 1 with corrected cases before deciding on Phase 2.

---

## 1. Detailed Results by Case

### cap-001-invalid-metric: Both Accept Invalid Input ⚠️ TYPE-1 BUG

| Database | Result | metric_type |
|----------|--------|------------|
| Milvus | Success | "INVALID_METRIC" |
| seekdb | Success | "INVALID_METRIC" |

**Finding**: Both databases accept invalid metric_type strings without validation at collection creation time.

**Classification**: **Type-1 bug candidate** (illegal input accepted) for BOTH databases
- **Rationale**: Collection created with "INVALID_METRIC" should be rejected
- **Impact**: Metric type validation is deferred or not enforced
- **Paper value**: Medium - shows lack of input validation in both systems

**Verdict**: ✅ Issue-ready candidate (dual-database Type-1 bug)

---

### cap-002-metric-string-variant: Both Accept "IP"

| Database | Result | metric_type |
|----------|--------|------------|
| Milvus | Success | "IP" |
| seekdb | Success | "IP" |

**Finding**: Both databases accept "IP" as metric_type (no validation of "IP" vs "IP_IP").

**Classification**: Same behavior, but reveals validation gap
- **Rationale**: Unclear if "IP" is valid or validation is deferred
- **Impact**: Inconsistent metric type handling

**Verdict**: ⚠️ Lower priority - similar to cap-001

---

### cap-003-max-topk-large: Setup Issue ❌ NOISE

| Database | Result | Reason |
|----------|--------|--------|
| Milvus | Failure | Collection 'diff_20260307_233850_main' not exist |
| seekdb | Failure | Table 'diff_20260307_233850_main' doesn't exist |

**Finding**: Both fail due to collection not existing.

**Root Cause**: Template uses `{collection}` placeholder which resolves to `diff_20260307_233850_main`, but setup creates `diff_test`.

**Classification**: ❌ Setup noise - not a behavioral difference

---

### cap-004-max-topk-int-max: Setup Issue ❌ NOISE

Same issue as cap-003 - collection mismatch.

---

### cap-005-filter-type-coercion: Setup Issue ❌ NOISE

Same issue as cap-003 - collection mismatch.

---

### cap-006-invalid-index-type: Setup Issue ❌ FALSE DIFFERENTIAL

| Database | Result | Label |
|----------|--------|-------|
| Milvus | Failure (collection not exist) | milvus_stricter |
| seekdb | Success (?) | |

**Finding**: Labeled as "milvus_stricter" but actually a setup issue.

**Root Cause**: Same collection mismatch. seekdb's "success" is misleading - it's not actually building an index on a non-existent collection.

**Classification**: ❌ False differential due to setup issue

---

## 2. Noise Analysis

### Noise Breakdown (4 out of 6 cases = 67%)

| Case | Noise Type | Root Cause |
|------|------------|------------|
| cap-003 | Collection mismatch | Template placeholder vs setup name |
| cap-004 | Collection mismatch | Template placeholder vs setup name |
| cap-005 | Collection mismatch | Template placeholder vs setup name |
| cap-006 | Collection mismatch | Template placeholder vs setup name |

### Fix Required

**Problem**: Cases using `{collection}` placeholder expect to use `diff_<timestamp>_main`, but setup only creates `diff_test`.

**Solutions**:
1. **Option A**: Update setup to create the timestamped collection name
2. **Option B**: Update cases to use `diff_test` directly instead of `{collection}`
3. **Option C**: Create a separate setup for cases that need indexed collections

**Recommended**: Option B - Update cases to use `diff_test` directly for Phase 1.

---

## 3. Capability-Boundary Family Assessment

### Yield Analysis

| Aspect | Result | Assessment |
|--------|--------|------------|
| Genuine differences | 0 | ❌ Capability boundaries showed no differential behavior |
| Type-1 bugs | 2 (cap-001, cap-002) | ✅ Found validation gaps |
| Noise | 67% | ❌ Template design issues |
| Overall yield | Low | ❌ Family underperformed expectations |

### Why Low Yield?

1. **Metric type validation is similar**: Both defer or skip validation at collection creation
2. **Template design flaw**: Placeholder mismatch prevented 4/6 cases from running
3. **Index type not tested**: cap-006 couldn't execute due to setup issue

### Is Capability-Boundary Family High-Yield?

**Verdict**: ⚠️ **Inconclusive - needs re-run with fixed templates**

**Rationale**:
- The 1 genuine difference from v2 (dim-max) was capability-boundary
- Current results show 0 differences but 67% noise
- Metric type validation appears weak in both databases (Type-1 bug)
- Index type validation and top_k limits remain untested due to setup issues

**Recommendation**: Fix templates, re-run cap-003 through cap-006 with proper setup before concluding on this family.

---

## 4. Issue-Ready Candidates

### Candidate 1: cap-001-invalid-metric (Type-1)

**Bug**: Both databases accept invalid metric_type "INVALID_METRIC"

**Evidence**:
- Milvus: Creates collection successfully with "INVALID_METRIC"
- seekdb: Creates table successfully with "INVALID_METRIC"

**Reportable**: ✅ Yes
- Clear violation of input validation
- Affects both databases equally
- Easy to reproduce

**Priority**: Medium - doesn't cause immediate failure, validation is deferred

---

### Candidate 2: cap-002-metric-string-variant (Type-1)

**Bug**: Both databases accept "IP" without validating against "IP_IP"

**Evidence**:
- Milvus: Creates collection with "IP"
- seekdb: Creates table with "IP"

**Reportable**: ⚠️ Lower priority
- "IP" might be valid (unclear)
- Similar to cap-001
- Duplicate finding

---

## 5. Recommendations

### Immediate Actions

1. **Fix template setup mismatch**:
   - Update cap-003, cap-004, cap-005, cap-006 to use `diff_test` directly
   - Or update setup to create and index the timestamped collection

2. **Re-run Phase 1** with fixed cases to get clean results

3. **Evaluate after re-run**:
   - If ≥2 genuine differences: Proceed to Phase 2
   - If still <2 genuine differences: Reconsider case family strategy

### Alternative: Skip to Phase 2

If capability-boundary family continues to show low yield after fix:

**Precondition-sensitivity family may have higher differential potential**:
- Index requirement differences (architectural)
- Empty collection handling
- State-dependent behavior

---

## 6. Decision Point

### Proceed to Phase 2?

**Condition**: Only if re-run shows ≥2 genuine differences AND noise <10%

**Current State**: ❌ Does not meet conditions
- 0 genuine differences
- 67% noise

**Recommendation**: Fix and re-run Phase 1 before deciding on Phase 2.

---

## 7. Success Criteria Scorecard

| Criterion | Minimum Target | Stretch Target | Phase 1 Result | Status |
|-----------|----------------|----------------|----------------|--------|
| Genuine differences | ≥2 | ≥3 | 0 | ❌ Below minimum |
| Noise pollution | ≤10% | <5% | 67% | ❌ Above target |
| Issue-ready candidates | ≥1 | ≥1 | 2 | ✅ Exceeded |
| Paper-worthy cases | ≥1 | ≥1 | 0 | ❌ Below minimum |

**Overall**: Phase 1 ❌ **Did not meet minimum success criteria**

**Path Forward**: Fix template issues, re-run Phase 1, then re-evaluate.
