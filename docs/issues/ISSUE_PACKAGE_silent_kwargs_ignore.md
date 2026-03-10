# Issue Package: pymilvus Collection() Silently Ignores Undocumented Parameters

**Issue ID**: PYMILVUS-SILENT-KWARGS-001
**Component**: pymilvus client library v2.6.2
**Database**: Milvus server v2.6.10
**Severity**: LOW-MEDIUM (API usability issue)
**Type**: API contract mismatch (silent ignore)
**Discovery**: R1 (cb-bound-005), R2 (param-metric-001)
**Date**: 2026-03-08
**Status**: Ready for filing

---

## Executive Summary

The pymilvus `Collection()` constructor accepts arbitrary keyword arguments via `**kwargs` and silently ignores them without warning or error. This creates a misleading API where users may believe they are setting parameters (like `metric_type`) that are actually being ignored.

**Clarification**: This is NOT a parameter validation bug. The actual `metric_type` parameter is set during index creation, not collection creation.

---

## Primary Evidence

### Evidence 1: Arbitrary kwargs Silently Ignored

**Test Case**: Pass `metric_type="INVALID_METRIC"` to Collection constructor

```python
from pymilvus import Collection, CollectionSchema, FieldSchema, DataType

fields = [
    FieldSchema(name='id', dtype=DataType.INT64, is_primary=True),
    FieldSchema(name='vector', dtype=DataType.FLOAT_VECTOR, dim=128)
]
schema = CollectionSchema(fields=fields)

# Pass metric_type as kwarg
collection = Collection(
    name='test_silent_ignore',
    schema=schema,
    using='default',
    metric_type="INVALID_METRIC"  # ← Accepted via **kwargs, silently ignored
)

# Verification
print(hasattr(collection, 'metric_type'))  # False - parameter was not stored
print(collection.indexes)  # [] - no indexes created yet
```

**Result**: Collection created successfully, `metric_type` was silently ignored.

**Expected**: Either:
1. Explicit error: "TypeError: Collection() got an unexpected keyword argument 'metric_type'"
2. Deprecation warning: "metric_type parameter is not used, set it during index creation"

---

### Evidence 2: Empty String Silently Ignored

**Test Case**: Pass `metric_type=""` (empty string)

```python
collection = Collection(
    name='test_empty_ignore',
    schema=schema,
    using='default',
    metric_type=""  # ← Accepted via **kwargs, silently ignored
)

# Verification
print(hasattr(collection, 'metric_type'))  # False
```

**Result**: Collection created successfully, empty string was silently ignored.

---

### Evidence 3: Lowercase "Silently Ignored" (Exploratory)

**Test Case**: Pass `metric_type="l2"` (lowercase)

```python
collection = Collection(
    name='test_lowercase_ignore',
    schema=schema,
    using='default',
    metric_type="l2"  # ← Accepted via **kwargs, silently ignored
)
```

**Result**: Collection created successfully. Note: Lowercase "l2" vs "L2" is irrelevant since the parameter is ignored entirely.

---

## Root Cause Analysis

### Actual Collection Constructor Signature

```python
Collection(self, name: str, schema: Union[CollectionSchema, NoneType] = None,
           using: str = 'default', **kwargs) -> None
```

The `**kwargs` parameter accepts any keyword argument and silently ignores it. This is a common Python pattern for flexibility, but creates usability issues when:

1. Users expect the parameter to do something (based on parameter name)
2. The parameter name conflicts with documented API concepts (like `metric_type`)
3. No warning or error is raised

---

### Correct API Usage

According to Milvus documentation:

1. **Collection creation**: Set schema only
   ```python
   Collection(name='my_collection', schema=schema, using='default')
   ```

2. **metric_type is set during index creation**:
   ```python
   collection.create_index(
       field_name='vector',
       index_params={
           'index_type': 'IVF_FLAT',
           'metric_type': 'L2',  # ← metric_type goes here
           'params': {'nlist': 128}
       }
   )
   ```

---

## Impact Assessment

**Severity**: LOW-MEDIUM

| Aspect | Impact |
|--------|--------|
| **Data Integrity** | None - collections work correctly |
| **User Confusion** | HIGH - users may think metric_type is set |
| **Debugging Difficulty** | MEDIUM - silent failures are hard to debug |
| **API Clarity** | LOW - official docs don't mention Collection metric_type |

**Key Point**: This is an **API usability issue**, not a data integrity bug. Collections created this way work correctly; the metric_type is properly set during index creation.

---

## Recommendations

1. **Short term**: Add explicit parameter list to Collection() constructor
   ```python
   def __init__(self, name: str, schema: Optional[CollectionSchema] = None,
                using: str = 'default') -> None:
       # Raise TypeError for unexpected kwargs
       ...
   ```

2. **Documentation**: Clarify in Collection() docs that `metric_type` should be set during index creation

3. **Backward compatibility**: Consider deprecation warning for unrecognized kwargs

---

## Reproducibility

**Version Information**:
- pymilvus client: v2.6.2
- Milvus server: v2.6.10

**Verification Steps**:
1. Create collection with arbitrary kwarg: `Collection(..., metric_type="ANY_VALUE")`
2. Verify collection is created: `utility.list_collections()`
3. Verify parameter is not stored: `hasattr(collection, 'metric_type')` → False

**Reproduced across**:
- differential v3 campaign (2026-03-07)
- R1 campaign (cb-bound-005)
- R2 campaign (param-metric-001)

---

## Documentation References

- [Milvus Metric Types](https://milvus.io/docs/metric.md) - metric_type is for index creation
- [pymilvus Collection API](https://milvus.io/api-reference/pymilvus/v2.2.x/Collection/Collection().md) - No metric_type parameter documented
- [Milvus Index Creation](https://milvus.io/docs/index-vector-fields.md) - Correct usage of metric_type

---

## Filing Checklist

- [x] Evidence verified: kwargs silently ignored
- [x] Root cause identified: **kwargs in constructor
- [x] Actual API usage documented
- [x] Impact assessed: API usability, not data integrity
- [x] Reproducibility confirmed
- [x] Severity adjusted: LOW-MEDIUM (not HIGH)
- [ ] Issue filed externally (pending)

---

## Change Log

**2026-03-08 - Initial Analysis**: Incorrectly classified as parameter validation bug
**2026-03-08 - Corrected Analysis**: Reclassified as silent kwargs ignore issue
- Reason: Collection() signature shows `**kwargs`, not explicit `metric_type` parameter
- Impact: Severity reduced from MEDIUM to LOW-MEDIUM
- Focus: API usability improvement, not validation enforcement
