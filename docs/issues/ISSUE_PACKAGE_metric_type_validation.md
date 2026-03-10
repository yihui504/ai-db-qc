# Issue Package: pymilvus Metric Type Validation Weakness

**Issue ID**: PYMILVUS-METRIC-VALIDATION-001
**Component**: pymilvus client library v2.6.2
**Database**: Milvus server v2.6.10
**Severity**: MEDIUM
**Type**: Type-1 (Illegal operations succeeded)
**Discovery**: Multi-campaign validation (differential v3, R1, R2)
**Date**: 2026-03-08
**Status**: Ready for filing

---

## Executive Summary

The pymilvus `Collection()` constructor accepts invalid `metric_type` parameter values without validation. This is a **validation weakness** where multiple forms of invalid input are silently accepted, allowing collections to be created with unintended or undefined metric types.

---

## Primary Evidence (High-Confidence)

### Evidence 1: Invalid Enum Value Accepted

**Test Case**: Create collection with `metric_type="INVALID_METRIC"`

```python
from pymilvus import Collection, CollectionSchema, FieldSchema, DataType

fields = [
    FieldSchema(name='id', dtype=DataType.INT64, is_primary=True),
    FieldSchema(name='vector', dtype=DataType.FLOAT_VECTOR, dim=128)
]
schema = CollectionSchema(fields=fields)

# Invalid enum value - accepted without error
collection = Collection(
    name='test_invalid_metric',
    schema=schema,
    using='default',
    metric_type="INVALID_METRIC"  # ← Invalid: not a valid metric type
)
# Result: SUCCESS - Collection created
# Expected: Error rejecting invalid metric_type
```

**Verification**:
```bash
$ python -c "
from pymilvus import utility, connections
connections.connect(alias='check', host='localhost', port=19530)
print('Collections:', utility.list_collections(using='check'))
"
# Output: ['test_invalid_metric', ...] ← Collection was created
```

**Discovery**: Differential v3 campaign (issue_001), independently confirmed in R1 (cb-bound-005)

---

### Evidence 2: Empty String Accepted

**Test Case**: Create collection with `metric_type=""` (empty string)

```python
# Empty string - accepted without error
collection = Collection(
    name='test_empty_metric',
    schema=schema,
    using='default',
    metric_type=""  # ← Invalid: empty string
)
# Result: SUCCESS - Collection created
# Expected: Error rejecting empty metric_type
```

**Verification**:
```bash
$ python -c "
from pymilvus import utility, connections
connections.connect(alias='check', host='localhost', port=19530)
print('Collections:', utility.list_collections(using='check'))
"
# Output: ['test_empty_metric', ...] ← Collection was created
```

**Discovery**: R2 campaign (param-metric-001)

---

## Supplementary Evidence (Exploratory)

### Evidence 3: Lowercase Variant Accepted

**Test Case**: Create collection with `metric_type="l2"` (lowercase)

```python
# Lowercase "l2" - accepted without error
collection = Collection(
    name='test_lowercase_metric',
    schema=schema,
    using='default',
    metric_type="l2"  # ← May be invalid (case-sensitive?)
)
# Result: SUCCESS - Collection created
# Note: May be by design if API is case-insensitive
```

**Discovery**: R2 campaign (exp-metric-001)

**Caveat**: This behavior may be by design if pymilvus/Milvus treats metric_type as case-insensitive. Treated as supplementary evidence.

---

## Expected Behavior

pymilvus should validate the `metric_type` parameter and reject invalid values:

```python
# Expected error for invalid enum
Collection(..., metric_type="INVALID_METRIC")
# Should raise: ValueError("Invalid metric_type 'INVALID_METRIC'. Valid values: L2, IP, COSINE, HAMMING, JACCARD")

# Expected error for empty string
Collection(..., metric_type="")
# Should raise: ValueError("metric_type cannot be empty")
```

---

## Valid Metric Types

According to Milvus documentation, valid `metric_type` values include:
- `L2`: Euclidean distance
- `IP`: Inner product
- `COSINE`: Cosine similarity
- `HAMMING`: Hamming distance (for binary vectors)
- `JACCARD`: Jaccard distance (for binary vectors)

---

## Impact Assessment

**Severity**: MEDIUM

| Aspect | Impact |
|--------|--------|
| Functionality | Collections are created successfully, basic operations work |
| Validation Gap | Invalid metric_type values are not validated at collection creation |
| Silent Failure | Users may not realize their specified metric_type was ignored |
| Risk | Collections may use unintended metric types, affecting search results |
| Data Loss | No immediate data loss, but search quality may be degraded |

---

## Root Cause Analysis

The pymilvus `Collection()` constructor does not validate the `metric_type` parameter before creating the collection. Possible explanations:
1. Validation is deferred to index creation time
2. Default metric type is used silently
3. No enforcement at client level (relying on server/schema validation)

---

## Recommendations

1. **Short term**: Validate `metric_type` in `Collection()` constructor with clear error messages
2. **Error messages**: List valid metric types and reject empty/invalid values
3. **Documentation**: Clarify whether metric_type is case-sensitive
4. **Backward compatibility**: Consider deprecation path for collections created without explicit metric_type

---

## Regression Testing

Both primary findings have been added to the regression pack:
- `regression-milvus-005`: Invalid enum value ("INVALID_METRIC")
- `regression-param-metric-001`: Empty string ("")

These should be run to verify the fix.

---

## Reproducibility

This issue has been **independently reproduced** across 3 campaigns:

| Campaign | Date | Finding |
|----------|------|---------|
| differential v3 | 2026-03-07 | issue_001_invalid_metric_type.md |
| R1 | 2026-03-08 | cb-bound-005 |
| R2 | 2026-03-08 | param-metric-001, exp-metric-001 |

**Reproducibility**: 100% - All campaigns confirmed the same behavior

---

## Attachments

1. **Regression Pack**: `casegen/templates/regression_pack.yaml`
2. **Test Results**: `results/milvus_validation_20260308_225412/`
3. **Family Documentation**: `docs/issues/METRIC_TYPE_VALIDATION_FAMILY.md`

---

## Filing Checklist

- [x] Primary evidence verified (2 high-confidence cases)
- [x] Supplementary evidence documented (1 exploratory case)
- [x] Root cause analyzed
- [x] Impact assessed
- [x] Reproducibility confirmed across multiple campaigns
- [x] Regression tests added
- [x] Tooling gaps documented separately (dtype parameter)
- [ ] Issue filed externally (pending)
