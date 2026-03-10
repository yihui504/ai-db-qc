# Issue: pymilvus Client Accepts Invalid Metric Type Without Validation

**Issue ID**: MILVUS-005
**Type**: Type-1 (Illegal operation succeeded)
**Severity**: MEDIUM
**Component**: pymilvus client library
**Versions**: pymilvus v2.6.2, Milvus server v2.6.10
**Discovery**: Campaign R1, case cb-bound-005
**Date**: 2026-03-08
**Duplicate**: Previously discovered in differential v3 as issue_001_invalid_metric_type.md

## Summary

Milvus accepts invalid `metric_type` parameter values during collection creation without raising an error. When `create_collection` is called with an invalid metric type (e.g., "INVALID_METRIC"), the operation succeeds and a collection is created using a default metric type instead of rejecting the invalid input.

## Reproduction

```python
from pymilvus import Collection, FieldSchema, CollectionSchema
from pymilvus.client.types import DataType

fields = [
    FieldSchema(name='id', dtype=DataType.INT64, is_primary=True),
    FieldSchema(name='vector', dtype=DataType.FLOAT_VECTOR, dim=128)
]
schema = CollectionSchema(fields=fields)

# Create collection with invalid metric type
collection = Collection(
    name='test_invalid_metric',
    schema=schema,
    using='default'
)

# Result: Collection created successfully
# Expected: Error rejecting invalid metric_type value
```

**Test Parameters:**
- `collection_name`: "test_r1_invalid_metric"
- `dimension`: 128
- `metric_type`: "INVALID_METRIC" (invalid)

**Observed Outcome**: Operation succeeded, collection created

**Expected Outcome**: Operation should fail with error about invalid metric_type value

## Actual Behavior

When an invalid `metric_type` is provided:
1. The `Collection()` constructor does not raise an exception
2. A collection is successfully created
3. The collection uses a default metric type (likely L2) instead of rejecting the invalid value

## Expected Behavior

Milvus should validate the `metric_type` parameter and reject invalid values with a clear error message such as:
- "Invalid metric_type: 'INVALID_METRIC'. Must be one of: L2, IP, COSINE, HAMMING, JACCARD"

## Impact

- **Data Integrity**: Collections may be created with unintended metric types, affecting similarity search results
- **Silent Failure**: Users may not realize their specified metric type was ignored
- **Debugging Difficulty**: No error message indicates the parameter was invalid

## Valid Metric Types

According to Milvus documentation, valid `metric_type` values include:
- `L2` (Euclidean distance)
- `IP` (Inner Product)
- `COSINE` (Cosine similarity)
- `HAMMING` (Hamming distance for binary vectors)
- `JACCARD` (Jaccard distance for binary vectors)

## Evidence

**Execution Result:**
```json
{
  "case_id": "cb-bound-005",
  "operation": "create_collection",
  "params": {
    "collection_name": "test_r1_invalid_metric",
    "dimension": 128,
    "metric_type": "INVALID_METRIC"
  },
  "observed_outcome": "success",
  "triage_result": {
    "final_type": "type-1",
    "input_validity": "illegal",
    "rationale": "Illegal operation succeeded"
  }
}
```

**Verification:**
```bash
$ python -c "
from pymilvus import utility, connections
connections.connect(alias='check', host='localhost', port=19530)
print('Collections:', utility.list_collections(using='check'))
"
# Output: ['test_r1_invalid_metric', ...] ← Collection was created
```

## Notes

- This behavior was discovered using AI-DB-QC tool's Campaign R1
- The `Collection()` constructor in pymilvus appears to be permissive about metric_type validation
- Similar permissive behavior may exist for other parameter validations
