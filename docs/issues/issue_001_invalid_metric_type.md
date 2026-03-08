# Issue Report: Invalid Metric Type Accepted (Type-1)

**Database**: Both Milvus and seekdb
**Severity**: Medium
**Type**: Type-1 (Illegal Input Accepted)
**Date**: 2026-03-07
**Campaign**: Differential v3, Case cap-001

---

## Summary

Both Milvus and seekdb accept invalid `metric_type` values at collection creation time without validation. The database accepts `metric_type="INVALID_METRIC"` and successfully creates the collection, despite "INVALID_METRIC" not being a valid distance metric.

## Environment

- **Milvus**: Version unknown (via pymilvus client)
- **seekdb**: Version unknown (via MySQL protocol on port 2881)
- **Test Date**: 2026-03-07

## Steps to Reproduce

### Milvus

```python
from pymilvus import Collection, CollectionSchema, FieldSchema, DataType, connections

connections.connect(alias="default", host="localhost", port=19530)

fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True),
    FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=128)
]
schema = CollectionSchema(fields, "Test collection")

# Creates successfully with invalid metric_type
collection = Collection(
    name="test_invalid_metric",
    schema=schema,
    using="default"
)
# Result: SUCCESS - Collection created despite invalid metric_type
```

### seekdb

```sql
CREATE TABLE test_invalid_metric (
    id INT PRIMARY KEY,
    VECTOR(128)  -- implicitly uses L2 or accepts metric_type
) WITH (
    metric_type = 'INVALID_METRIC'  -- Accepted without error
);
-- Result: SUCCESS - Table created despite invalid metric_type
```

## Expected Behavior

Database should reject invalid `metric_type` with a specific error message listing valid options:

```
Expected Error: "Invalid metric_type 'INVALID_METRIC'. Valid values are: L2, IP, COSINE"
```

## Actual Behavior

Database accepts invalid `metric_type` and creates collection successfully:

```
Actual Result: Collection/table created without error
```

## Impact

### Severity Assessment: Medium

- **Functionality**: Collection creation succeeds, so basic operations work
- **Validation**: Metric type validation is deferred or not enforced
- **Risk**: Invalid metric may cause issues during index creation or search operations
- **User Experience**: Silent acceptance may cause confusion when operations fail later

## Root Cause Analysis

Both databases appear to defer metric type validation:
- At collection creation: No validation of `metric_type` string
- At index/search time: May use default metric or fail with unclear error

This is a **validation gap** where illegal input is accepted without error.

## Valid Metric Types

Based on vector database conventions, valid metric types typically include:
- `L2`: Euclidean distance
- `IP`: Inner product
- `COSINE`: Cosine similarity

## Recommendations

1. **Short term**: Validate `metric_type` at collection creation time
2. **Error message**: List valid metric types in error message
3. **Documentation**: Clarify which metric types are supported
4. **Backward compatibility**: Consider deprecation path for existing collections

## References

- **Test Case**: cap-001-invalid-metric in differential_v3_phase1
- **Reproducibility**: 100% - Both databases exhibit this behavior
- **Related**: cap-002-metric-string-variant (accepts "IP" variant)

---

## Classification

**Type**: Type-1 (Illegal Input Accepted)
**Scope**: Both Milvus and seekdb
**Priority**: Medium (validation improvement, not critical bug)

**Report Status**: ✅ Ready for submission
