# Differential Campaign v2 - Honest Assessment

> **Run ID**: differential-v2-final-20260307_232900
> **Date**: 2026-03-07
> **Cases**: 18 (v2 expanded pack)

---

## Executive Summary

| Metric | v1 Result | v2 Result | Target | Status |
|--------|-----------|-----------|--------|--------|
| Genuine behavioral differences | 1 | 1 | 3-5 | ❌ Below target |
| Issue-ready candidates | 0 | 0 | 1-2 | ❌ Below target |
| Noise pollution | 40% (4/10) | 17% (3/18) | <10% | ⚠️ Improved but not met |
| Total cases | 10 | 18 | 18 | ✅ Met |

**Overall**: v2 achieved noise reduction (40% → 17%) but genuine difference yield remained flat at 1 case.

---

## 1. Genuine Behavioral Differences (1 case)

### boundary-002-dim-max ⭐ GENUINE

**Label**: seekdb_stricter
**Milvus**: Success - accepts dimension=32768
**seekdb**: Failure - "vector column dim less or equal to zero or larger than 16000 is not supported"
**Type**: **Parameter boundary difference**

**Assessment**: ✅ **Strong paper case study**
- Milvus supports dimensions up to 32768
- seekdb supports dimensions up to 16000
- Clear difference in maximum dimension limits
- Implications for high-dimensional vector use cases

---

## 2. False Differentials (2 cases) - Noise

### boundary-003-dim-min ❌ COLLECTION COLLISION

**Label**: seekdb_stricter (false)
**Actual Issue**: "Table 'dim_min_test' already exists"
**Root Cause**: Collection name collision from previous v2-fixed run
**Fix**: Already addressed by unique collection naming with timestamp

**Assessment**: ❌ Not a behavioral difference - setup noise

---

### valid-002-search-valid ❌ SETUP GAP

**Label**: milvus_stricter (false)
**Actual Issue**:
- Milvus: Collection not loaded for search
- seekdb: Returns empty results (works without explicit index)

**Root Cause**: v2 template uses `{collection}` placeholder but setup only creates `diff_test`

**Assessment**: ⚠️ Partial - reveals architectural difference (Milvus requires explicit index/load, seekdb doesn't), but setup issue masks the true behavioral comparison

---

## 3. Type-2 Diagnostic Comparisons (2 valid cases)

These cases show both databases correctly rejecting invalid input with different error messages:

| Case | Parameter | Both Reject? | Value |
|------|-----------|--------------|-------|
| boundary-001-dim-zero | dimension=0 | ✅ Yes | Both reject with clear errors |
| boundary-006-dim-negative | dimension=-1 | ✅ Yes | Both reject with clear errors |

**Assessment**: ✅ Valid Type-2 comparisons - good for understanding database "personalities"

---

## 4. v2 Improvement Effectiveness

### Noise Reduction: 40% → 17% ✅ Improved

| Noise Source | v1 Count | v2 Count | Status |
|--------------|----------|----------|--------|
| Collection collisions | 3 | 1 | ✅ Improved (unique naming) |
| Adapter gaps | 1 | 0 | ✅ Fixed (drop_collection added) |
| Setup issues | 0 | 1 | ⚠️ New (template mismatch) |

### Genuine Differences: 1 → 1 ❌ Flat

Despite expanding from 10 to 18 cases, only 1 genuine behavioral difference was found.

**Why?**
1. Milvus and seekdb have similar parameter validation for most inputs
2. The dimension limit difference (16000 vs 32768) was already known
3. Most boundary cases (dimension=0, dimension=-1) show identical rejection behavior
4. top_k parameter validation is similar across both databases

---

## 5. Key Finding: Architectural Difference

### valid-002-search-valid Reveals Index Requirement Gap

While marked as setup noise, this case reveals a genuine architectural difference:

- **Milvus**: Requires explicit `build_index` + `load` before search
- **seekdb**: Can search immediately after insert (no explicit index required)

**Implications**:
- seekdb has lower setup complexity for basic operations
- Milvus requires more explicit state management
- Different user experience for vector search workflows

**Recommendation**: Create dedicated test case for this architectural difference.

---

## 6. Lessons Learned

### What Worked

1. **Unique collection naming** with timestamp prefix reduced collisions from 3 to 1
2. **Adapter parity** (drop_collection) eliminated false "unknown operation" differences
3. **18-case expansion** provided better coverage of parameter boundaries

### What Didn't Work

1. **Low genuine difference yield**: Only 1 from 18 cases (5.5%)
2. **Template setup mismatch**: Cases using `{collection}` don't find the setup `diff_test` collection
3. **Many "same_behavior" failures**: 15/18 cases show identical behavior (mostly failures)

### Root Causes

1. **Parameter validation is similar**: Both databases follow similar validation logic
2. **Case design may be too conservative**: Focused on obvious invalid inputs that both reject
3. **Missing higher-yield categories**: Need cases that probe:
   - Implicit behavior differences (index requirements, auto-commit)
   - Edge cases in data handling (empty vectors, special characters)
   - Transaction and isolation semantics

---

## 7. Recommendations for v3

### Option A: Pivot to Architectural Differences

Focus on cases that probe workflow differences rather than parameter validation:

1. **Index requirement differences**: search without explicit index/load
2. **Auto-commit behavior**: insert visibility without explicit commit
3. **Empty collection handling**: search on collection with 0 vectors
4. **Vector format flexibility**: handling of malformed vector literals
5. **Concurrent operation handling**: simultaneous insert/search

**Expected yield**: 3-5 genuine differences from ~15 cases

### Option B: Deeper Parameter Probing

Focus on edge cases that might reveal validation differences:

1. **Vector content boundaries**: NaN, Infinity, very large values
2. **Filter expression syntax**: differences in boolean and comparison operators
3. **Metric type validation**: invalid metric_type values
4. **ID type handling**: negative IDs, very large IDs, duplicate IDs

**Expected yield**: 1-2 genuine differences from ~20 cases

### Option C: Accept Current Yield

1 genuine difference from 18 cases is valuable:
- Documents dimension limit difference (16000 vs 32768)
- Valid Type-2 comparisons for diagnostic quality
- Framework proven to work across two databases

**Action**: Publish findings as-is, focus on improving methodology for next comparison.

---

## 8. Honest Conclusion

### v2 Achievements

1. ✅ Reduced noise from 40% to 17%
2. ✅ Found 1 genuine behavioral difference (dimension limits)
3. ✅ Validated 2 Type-2 diagnostic comparisons
4. ✅ Framework improvements (unique naming, adapter parity, cleanup)

### v2 Shortcomings

1. ❌ Genuine difference yield flat at 1 case (target was 3-5)
2. ❌ No issue-ready bug candidates found
3. ❌ Many cases (15/18) showed identical behavior
4. ❌ Setup mismatch created false differentials

### Verdict

**v2 is a methodological improvement over v1, but the case design didn't achieve the target yield of 3-5 genuine differences.**

The framework is working correctly - it's detecting that Milvus and seekdb have very similar parameter validation behavior. To find more differences, we need to probe architectural and workflow differences rather than obvious parameter boundaries.

**Recommendation**: Proceed with Option A (architectural differences focus) for v3, or accept current yield and document the dimension limit finding as a solid case study.
