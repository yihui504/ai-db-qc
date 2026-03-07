# First Real Differential Run - Final Honest Assessment

> **Run ID**: differential-first-subset-v2-20260307-231611
> **Date**: 2026-03-07
> **Cases**: 10 (first subset)

---

## 1. Aggregate Comparison Summary

| Label | Count | Valid? |
|-------|-------|--------|
| milvus_stricter | 2 | **1 valid** (1 is adapter bug) |
| seekdb_stricter | 3 | **0 valid** (all setup noise) |
| same_behavior | 5 | **3 valid** (2 are setup noise) |

**Genuine differences**: 1 out of 10 cases

---

## 2. Label Distribution (After Filtering Noise)

| Label | Count | After Filtering Setup/Adapter Noise |
|-------|-------|----------------------------------------|
| milvus_stricter | 2 | 1 (top_k=0) |
| seekdb_stricter | 3 | 0 (all "table exists" errors) |
| same_behavior | 5 | 3 (2 are "table exists", 3 are genuine both-fail) |

---

## 3. Top 5 Most Meaningful Differential Cases

### Rank 1: subset-003-topk-zero ⭐ GENUINE DIFFERENCE

**Label**: milvus_stricter
**Milvus**: Failure - "limit value 0 is illegal"
**seekdb**: Success - Accepts top_k=0
**Type**: **Genuine behavioral difference**
**Value**: seekdb allows zero-limit searches (returns 0 results), Milvus rejects with clear error

**Assessment**: ✅ **Strong paper case study** - Clear behavioral difference with validation implications

---

### Rank 2: subset-002-drop-nonexistent ⚠️ PARTIAL FINDING

**Label**: milvus_stricter
**Milvus**: Failure - "Unknown operation: drop_collection"
**seekdb**: Success
**Type**: **Adapter limitation** (not behavioral difference)
**Value**: Milvus adapter doesn't implement drop_collection

**Assessment**: ❌ Not a behavioral difference - Milvus adapter missing operation. Would need to check if native Milvus supports DROP.

---

### Rank 3-5: Setup Noise (Not behavioral differences)

| Case | Label | Actual Issue |
|------|-------|--------------|
| subset-001-baseline | seekdb_stricter | Collection 'test_baseline' already exists (previous run) |
| subset-004-invalid-metric | seekdb_stricter | Collection 'test_invalid_metric' already exists |
| subset-005-empty-metric | seekdb_stricter | Collection 'test_empty_metric' already exists |

**Assessment**: ❌ Setup noise - These are not behavioral differences, just state pollution from previous runs.

---

### Same Behavior Cases (5 cases)

| Case | Both | Valid? |
|------|------|--------|
| subset-006-dim-zero | Failure (both reject) | ✅ Valid Type-2 comparison |
| subset-007-dim-negative | Failure (both reject) | ✅ Valid Type-2 comparison |
| subset-008-search-nonexistent | Failure (both reject) | ✅ Valid diagnostic comparison |
| subset-009-delete-nonexistent | Failure (both reject) | ✅ Valid diagnostic comparison |
| subset-010-valid-search | Failure (both failed) | ❌ Setup issue (collection not indexed) |

---

## 4. Issue-Ready Candidate(s)

### None Confirmed

After filtering, **no issue-ready candidates** emerged from this run.

**Reason**: The only genuine behavioral difference (top_k=0) is:
- seekdb accepts zero limit (returns 0 results) - this could be valid behavior
- Milvus rejects zero limit - also valid behavior
- Neither is necessarily "wrong" - this is a design choice difference

**Potential issue**: If seekdb accepting top_k=0 causes problems for applications expecting results, this could be documented as a compatibility note rather than a bug.

---

## 5. Distinguishing Genuine Differences from Noise

### Genuine Behavioral Differences (1)

1. **subset-003-topk-zero**: Milvus rejects top_k=0, seekdb accepts it
   - **Type**: Parameter boundary difference
   - **Valid**: Yes, both behaviors are reasonable
   - **Bug?**: No - design choice difference

### Adapter/Setup Noise (4)

1. **subset-002-drop-nonexistent**: Milvus adapter doesn't implement drop_collection
2. **subset-001-baseline**: Collection already exists from previous run
3. **subset-004-invalid-metric**: Collection already exists from previous run
4. **subset-005-empty-metric**: Collection already exists from previous run

### Valid Type-2 Comparisons (2)

1. **subset-006-dim-zero**: Both reject dimension=0 (good comparison of error messages)
2. **subset-007-dim-negative**: Both reject dimension=-1 (good comparison of error messages)

---

## 6. Is First Subset Strong Enough?

### For Paper Case Studies: ⚠️ WEAK

**Strength**: 1 genuine behavioral difference (top_k=0)

**Weaknesses**:
- Only 1 genuine difference from 10 cases (10% yield)
- 4 cases are setup/adapter noise (40% pollution)
- Need cleanup between runs to avoid collection name collisions

**Verdict**: **Marginal** - The top_k=0 difference is interesting, but the overall 10% genuine difference rate is weak.

---

### For Issue Selection: ❌ NO

**No issue-ready candidates found**.

The top_k=0 difference is a design choice, not a bug. Applications using seekdb should be aware that top_k=0 returns 0 results, which may not be the intended behavior.

---

## 7. Should Remaining Cases Be Promoted?

### Cases to Consider Promoting:

Based on what worked well, consider:

1. **subset-006, subset-007** (Type-2 comparisons)
   - Both correctly reject invalid dimensions
   - Good for comparing diagnostic quality
   - Low setup complexity
   - **Recommendation**: ✅ Promote to core set

2. **subset-008, subset-009** (Precondition diagnostics)
   - Both fail on nonexistent operations
   - Good for comparing error messages
   - **Recommendation**: ✅ Promote to core set

3. **subset-010** (Valid search)
   - Failed on both due to index not loaded
   - Needs better setup phase
   - **Recommendation**: ⚠️ Fix setup, then promote

### Cases to Keep as-Is:

1. **subset-003** (top_k=0) - Keep as is, good finding
2. **subset-004, subset-005** (Invalid metric) - Need collection name deduplication
3. **subset-002** (drop nonexistent) - Needs Milvus adapter implementation

---

## 8. Recommendations for Next Run

### Immediate Actions:

1. **Add collection cleanup** between runs
   - Drop all test collections before starting
   - Or use unique collection names per run (add timestamp)

2. **Fix Milvus drop_collection** support
   - Implement drop_collection in Milvus adapter
   - Or remove from shared pack

3. **Improve setup phase**
   - Ensure indexes are loaded before search operations
   - Handle collection existence checks

4. **Run subset v3 with fixes**
   - Expect ~30-40% genuine difference rate (up from 10%)

### Cases to Add:

From the remaining 20, consider promoting:
- Parameter boundary tests (dim validation, top_k limits)
- Diagnostic quality tests (error message comparison)
- Precondition handling tests (nonexistent operations)

---

## Summary

| Question | Answer |
|----------|--------|
| Were both databases tested? | ✅ Yes |
| Are results meaningful? | ⚠️ Partially - 1 genuine diff / 10 cases |
| Top differential cases? | subset-003-topk-zero only |
| Strong for papers? | ⚠️ Weak - 10% genuine difference rate |
| Issue-ready candidates? | ❌ None |
| Promote more cases? | ✅ Yes - Type-2 comparison cases |

**Overall Assessment**: The framework works and found 1 genuine behavioral difference, but setup noise and adapter limitations reduced the effective yield. First subset is **marginally useful** but needs cleanup and expansion before strong publication.
