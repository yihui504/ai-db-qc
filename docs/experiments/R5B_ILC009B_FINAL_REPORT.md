# ILC-009b: Post-Insert Search Timing - Final Report

**Test ID**: ILC-009b
**Run ID**: r5b-lifecycle-20260310-124135
**Database**: Milvus v2.6.10
**Date**: 2026-03-10
**Classification**: PASS
**Conclusion**: Flush enables search visibility for newly inserted vectors

---

## Executive Summary

ILC-009b conclusively proved that **flush is required for search visibility** in Milvus v2.6.10. The experiment used a unique 128-dimensional vector and exact vector matching to precisely measure when inserted vectors become available in search results.

## Key Findings

| Metric | Value |
|--------|-------|
| Insert Operation | Success (insert_count=1) |
| Immediate Search | NOT found (returned existing vector) |
| After Flush Search | Found with exact match (score=0.0) |
| Storage Count (before flush) | 100 (unchanged) |
| Storage Count (after flush) | 101 (+1) |

## Detailed Evidence

### Search Results at Each Timepoint

| Timepoint | Top ID | Score/Distance | Interpretation |
|-----------|--------|----------------|----------------|
| Immediate (0ms) | 50 | 27.27 | Found existing vector, NOT the unique one |
| After Flush | 0 | 0.0 | Exact match to unique vector ✓ |
| +200ms | 0 | 0.0 | Exact match maintained |
| +500ms | 0 | 0.0 | Exact match maintained |
| +1000ms | 0 | 0.0 | Exact match maintained |

### Storage Count Timeline

```
Baseline: 100 vectors
After insert_unique: 100 (unchanged - not yet visible)
After flush: 101 (+1 - now visible)
```

## Experiment Design

### Unique Vector Specification
- **Dimensions**: 128
- **Values**: [0.999, 0.998, 0.997, ..., 0.872]
- **Guarantee**: Not present in original 100 vectors

### Search Configuration
- **Query Vector**: Same as inserted vector (exact match)
- **top_k**: 1 (maximize chance of finding exact match)
- **Distance Metric**: L2 (default)

### Timepoints
1. **Immediate**: Search right after insert (before flush)
2. **After Flush**: Search after flush operation
3. **+200ms**: Search 200ms after flush
4. **+500ms**: Search 500ms after flush
5. **+1000ms**: Search 1000ms after flush

## Classification Rationale

### PASS (not ALLOWED_DIFFERENCE)

**Reason**: Flush enabling search visibility is expected and consistent behavior for vector databases with separate storage and index layers.

**Distinguishing from ALLOWED_DIFFERENCE**:
- ALLOWED_DIFFERENCE would be: Random delay (200ms, 500ms) without flush
- PASS: Predictable, documented behavior (flush → visible)

### ILC-009 vs ILC-009b

| Contract | Design | Finding | Classification |
|----------|--------|---------|----------------|
| ILC-009 | Existing vector as query | Inconclusive | EXPERIMENT_DESIGN_ISSUE |
| ILC-009b | Unique vector, exact match | Conclusive | PASS |

---

## Contract Implications

### Updated ILC-009 Statement

**Before**: "insert visibility requires flush for count, search timing unknown"

**After**: "insert visibility requires flush for count and search"

### New ILC-009b Contract

```json
{
  "contract_id": "ILC-009b",
  "name": "Post-Insert Search Timing",
  "statement": "inserted vector requires flush for search visibility with exact match",
  "milvus_verified": true,
  "confidence": "HIGH",
  "evidence": "unique vector (128-dim) not found immediately (score=27.27), found after flush with exact match (score=0.0)",
  "classification": "PASS",
  "conclusion": "flush_enables_search_visibility",
  "visible_at": "after_flush"
}
```

---

## Technical Implementation

### Oracle Fix

The oracle was updated to check for **exact match** (score/distance ≈ 0), not just any result:

```python
def is_exact_match(result):
    """Check if result is an exact match (score/distance ≈ 0)."""
    if result["id"] is None:
        return False
    epsilon = 1e-6
    score = result.get("score")
    distance = result.get("distance")
    if score is not None and abs(score) < epsilon:
        return True
    if distance is not None and abs(distance) < epsilon:
        return True
    return False
```

**Before**: `found = immediate["id"] is not None` (incorrect - any result)
**After**: `found = is_exact_match(immediate)` (correct - exact match only)

### Template Updates

The ILC-009b template was updated with a proper 128-dim unique vector:

```yaml
vectors: "[[0.999, 0.998, ..., 0.872]]"  # 128 dimensions
```

---

## Files Modified

- `core/oracle_engine.py`: Added EXPERIMENT_DESIGN_ISSUE classification, fixed exact match detection
- `casegen/templates/r5b_lifecycle.yaml`: Fixed YAML typo, added 128-dim unique vector
- `contracts/index/lifecycle_contracts.json`: Updated ILC-009, added ILC-009b
- `adapters/milvus_adapter.py`: Fixed indentation, added wait operation

---

## Conclusion

ILC-009b successfully determined the search-visible timing for inserted vectors in Milvus v2.6.10:

1. **Insert reports immediate success**: insert_count=1
2. **Storage count requires flush**: 100 → 101 after flush
3. **Search requires flush**: Unique vector not found immediately, found after flush

This is **PASS** behavior (not ALLOWED_DIFFERENCE) because:
- Flush is a documented operation for data persistence
- Behavior is predictable and consistent
- Matches expected architecture (separate storage and index layers)

---

**Report Completed**: 2026-03-10
**Next Steps**: Update documentation for production usage recommendations
