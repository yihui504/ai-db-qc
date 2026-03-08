# Differential v3 Phase 1 - Corrected Taxonomy

> **Run ID**: differential-v3-phase1-fixed-20260307_234037
> **Date**: 2026-03-07
> **Cases**: 6 capability-boundary cases

---

## Corrected Taxonomy Summary

### Issue-Ready Candidates (3 cases)

| Case | Type | Database | Bug Description |
|------|------|----------|----------------|
| cap-001-invalid-metric | **Type-1** | BOTH | Accept invalid metric_type "INVALID_METRIC" without validation |
| cap-006-invalid-index-type | **Type-1** | seekdb | Accept invalid index_type "INVALID_INDEX" without validation |
| cap-003-max-topk-large | **Type-2** | seekdb | Poor diagnostic on illegal top_k: "Invalid argument" vs Milvus specific range |

### Valid Type-2 Comparisons (2 cases)

| Case | Value | Comparison |
|------|-------|------------|
| cap-004-max-topk-int-max | Diagnostic quality | Both reject INT_MAX, Milvus specific / seekdb generic |
| cap-005-filter-type-coercion | Diagnostic quality | Both reject type mismatch, different error messages |

### Genuine Behavioral Differences (2)

1. **cap-006**: Milvus validates index_type, seekdb doesn't (validation philosophy difference)
2. **cap-003/004**: Milvus top_k limit [1, 16384] with specific diagnostic, seekdb limit unknown with generic error

### Same Behavior (1)

| Case | Behavior |
|------|----------|
| cap-002-metric-string-variant | Both accept "IP" metric_type (validation deferred or "IP" is valid) |

---

## Taxonomy Corrections Applied

### Before: Incorrect Classification
- cap-003/cap-004 were potentially labeled as Type-2.PF (Precondition Failed)

### After: Correct Classification
- cap-003/cap-004 are **Type-2** (Poor Diagnostic), not Type-2.PF
- **Rationale**: The input is **illegal** (top_k overflow), not a precondition failure
- Type-2.PF is specifically for when a valid contract request fails due to precondition violation with confusing error
- Here, the contract request itself is invalid (illegal top_k value), so poor diagnostic = Type-2

### Type-2 vs Type-2.PF Distinction

| Aspect | Type-2 | Type-2.PF |
|--------|--------|-----------|
| Input validity | **Illegal input** | **Valid input, invalid runtime state** |
| Failure cause | Parameter violates constraints | Precondition not met |
| Example | top_k=1000000 (overflow) | search on non-existent collection |
| Poor diagnostic = | Type-2 | Type-2.PF |

---

## Final Phase 1 Metrics (Corrected)

| Metric | Result | Target | Status |
|--------|--------|--------|--------|
| Genuine behavioral differences | 2 | ≥2 | ✅ |
| Noise pollution | 0% | ≤10% | ✅ |
| Issue-ready candidates | 3 (1 Type-1 dual, 1 Type-1 seekdb, 1 Type-2) | ≥1 | ✅ |
| Paper-worthy cases | 2 | ≥1 | ✅ |

### Issue-Ready Breakdown by Type

| Type | Count | Cases |
|------|-------|-------|
| Type-1 (illegal accepted) | 2 | cap-001 (both), cap-006 (seekdb) |
| Type-2 (poor diagnostic) | 1 | cap-003 (seekdb) |
| **Total** | **3** | |

---

## Summary

**Correction**: Reclassified cap-003 from potential Type-2.PF to **Type-2** (Poor Diagnostic).

**Reasoning**: The input (top_k=1000000) is illegal, not a precondition violation. Type-2.PF is reserved for valid inputs that fail due to runtime precondition violations with confusing errors.

**Phase 1 Status**: ✅ Still meets all success criteria with corrected taxonomy.
