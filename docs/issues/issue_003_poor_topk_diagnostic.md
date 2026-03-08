# Issue Report: Poor Diagnostic on top_k Overflow (Type-2)

**Database**: seekdb
**Severity**: Low
**Type**: Type-2 (Poor Diagnostic on Illegal Input)
**Date**: 2026-03-07
**Campaign**: Differential v3, Case cap-003

---

## Summary

When an illegal `top_k` value is provided (outside the valid range), seekdb returns a generic "Invalid argument" error without specifying the valid range. Milvus provides a superior error message that explicitly states the valid range: "topk [N] is invalid, it should be in range [1, 16384]".

## Environment

- **seekdb**: Version unknown (via MySQL protocol on port 2881)
- **Milvus**: Version unknown (via pymilvus client) - for comparison
- **Test Date**: 2026-03-07

## Steps to Reproduce

### seekdb (Poor Diagnostic)

```sql
-- Search with illegal top_k value
SELECT id, l2_distance(embedding, '[0.1, 0.1, ...]') AS distance
FROM test_collection
ORDER BY distance
LIMIT 1000000;  -- Illegal top_k value

-- Result: ERROR - "Invalid argument"
-- No indication of valid range or why it's invalid
```

### Milvus (Superior Diagnostic)

```python
from pymilvus import Collection

collection = Collection("test_collection")

# Search with illegal top_k value
results = collection.search(
    data=[[0.1] * 128],
    anns_field="vector",
    param={"metric_type": "L2", "params": {"nprobe": 10}},
    limit=1000000  # Illegal top_k value
)

# Result: ERROR - "topk [1000000] is invalid, it should be in range [1, 16384]"
# Specific range information provided
```

## Expected Behavior

When `top_k` exceeds the valid range, database should:

1. **Reject the request** (both do this correctly)
2. **Provide specific error** indicating:
   - What parameter was invalid
   - What the valid range is
   - What value was provided

**Expected Error Format**:
```
"Invalid top_k value: 1000000. Valid range is [1, <MAX_LIMIT>]"
```

## Actual Behavior

| Database | Rejects Invalid top_k? | Error Quality |
|----------|------------------------|---------------|
| **Milvus** | ✅ Yes | ✅ Excellent: "topk [1000000] is invalid, it should be in range [1, 16384]" |
| **seekdb** | ✅ Yes | ❌ Poor: "Invalid argument" |

### Error Message Comparison

```
Milvus: "topk [1000000] is invalid, it should be in range [1, 16384]"
seekdb: "Invalid argument"
```

The Milvus error is **actionable** - it tells the user:
1. What parameter failed (topk)
2. What value was provided (1000000)
3. What the valid range is ([1, 16384])

The seekdb error is **not actionable** - it doesn't tell the user:
1. Which parameter was invalid
2. What the valid range is
3. How to fix the problem

## Impact

### Severity Assessment: Low

- **Functionality**: Both correctly reject invalid input (prevents bad behavior)
- **User Experience**: seekdb error is frustrating (user must guess the problem)
- **Debugging**: Difficult to diagnose without specific error
- **Workaround**: Users must consult documentation or trial-and-error

### User Experience Impact

When a user provides `top_k=1000000`:

**Milvus User**:
```
Error: topk [1000000] is invalid, it should be in range [1, 16384]
Action: Use top_k <= 16384
Time to fix: ~5 seconds
```

**seekdb User**:
```
Error: Invalid argument
Thought: What argument? Which parameter? What's the valid range?
Action: Check documentation, try smaller values, search online...
Time to fix: ~5-15 minutes
```

## Valid Range Information

### Milvus (Known)
- **top_k Range**: [1, 16384]
- **Explicitly stated**: Yes, in error message

### seekdb (Unknown)
- **top_k Range**: Unknown
- **Error message**: Does not specify range
- **Documentation**: May or may not document the limit

## Root Cause Analysis

The issue is **diagnostic quality**, not functional correctness:

1. **Functional**: Both correctly reject invalid top_k
2. **Diagnostic**: Milvus provides specific range, seekdb does not
3. **Root cause**: Error handling in seekdb uses generic message

## Recommendations

1. **High priority**: Update error message to include valid range
   ```
   Recommended: "Invalid top_k value: <provided>. Valid range is [1, <MAX>]"
   ```

2. **Medium priority**: Include parameter name in error
   ```
   Improvement: "top_k parameter: Invalid argument"
   ```

3. **Low priority**: Document top_k limits in user guide

## Additional Test Cases

The same poor diagnostic affects multiple scenarios:

| Case | Input | Milvus Error | seekdb Error |
|------|-------|--------------|--------------|
| Large value | top_k=1000000 | Specific range | "Invalid argument" |
| INT_MAX | top_k=2147483647 | Specific range | "Invalid argument" |
| Negative | top_k=-1 | Specific range | "Invalid argument" |
| Zero | top_k=0 | Specific range | "Invalid argument" |

All cases show the same pattern: Milvus specific, seekdb generic.

## Comparison with Other Databases

Industry standard for parameter validation errors:

| Database | Error Quality |
|----------|---------------|
| **Milvus** | ⭐⭐⭐ Excellent - Specific range provided |
| **PostgreSQL** | ⭐⭐⭐ Good - Usually specifies parameter and constraint |
| **seekdb** | ⭐ Poor - Generic "Invalid argument" |

## References

- **Test Case**: cap-003-max-topk-large in differential_v3_phase1
- **Related**: cap-004-max-topk-int-max (same pattern)
- **Reproducibility**: 100% - Consistent behavior across all illegal top_k values

---

## Classification

**Type**: Type-2 (Poor Diagnostic on Illegal Input)
**Scope**: seekdb only (Milvus has excellent diagnostic)
**Severity**: Low (functional correctness maintained)
**Priority**: Medium (user experience improvement)

**Report Status**: ✅ Ready for submission
