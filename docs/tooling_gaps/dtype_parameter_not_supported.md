# Tooling Gap: dtype Parameter Not Implemented

**Gap ID**: TOOLING-001
**Component**: MilvusAdapter._create_collection()
**Discovered**: R2 campaign (param-dtype-001)
**Date**: 2026-03-08
**Status**: Open

---

## Issue Description

The `param-dtype-001` test case from R2 was classified as a Type-1 finding (invalid dtype accepted), but investigation revealed this is a **tool-layer artifact**, not a database bug.

### What Happened

The test case specified:
```yaml
operation: create_collection
params:
  collection_name: "test_r2_invalid_dtype"
  dimension: 128
  metric_type: "L2"
  dtype: "INVALID_VECTOR_TYPE"  # ← This parameter was ignored
```

The test **passed** (collection created successfully), appearing to indicate that Milvus accepts invalid dtype values. However, the MilvusAdapter's `_create_collection()` method ignores the `dtype` parameter entirely:

```python
# adapters/milvus_adapter.py:178-199
def _create_collection(self, params: Dict) -> Dict[str, Any]:
    """Create a new collection."""
    collection_name = params.get("collection_name")
    dimension = params.get("dimension", 128)
    metric_type = params.get("metric_type", "L2")

    # Define schema with proper DataType enums
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=dimension)  # ← Hardcoded
    ]
    schema = CollectionSchema(fields, f"Auto generated schema for {collection_name}")

    # Create collection
    collection = Collection(name=collection_name, schema=schema, using=self.alias)
    ...
```

### Root Cause

The `_create_collection()` method:
1. Does not read the `dtype` parameter from `params`
2. Hardcodes the schema with fixed `DataType.INT64` and `DataType.FLOAT_VECTOR`
3. Cannot test different vector data types (e.g., `FLOAT16_VECTOR`, `BFLOAT16_VECTOR`)

---

## Impact

### Current Limitations

1. **Cannot test dtype validation**: The tool cannot verify whether Milvus validates vector data types
2. **Cannot test different vector types**: Binary vectors (`BINARY_VECTOR`), sparse vectors, etc. cannot be tested
3. **False positive risk**: Tests may appear to pass when the parameter is simply ignored

### Database Behavior Unknown

Since the tool doesn't pass `dtype` to Milvus, we don't know whether:
- Milvus validates dtype at all
- Milvus accepts invalid dtype values
- Milvus has strong dtype validation

---

## Fix Requirements

To properly test dtype validation, the `_create_collection()` method needs to:

1. **Read the dtype parameter**:
   ```python
   dtype_str = params.get("dtype", "FLOAT_VECTOR")
   ```

2. **Map string to DataType enum**:
   ```python
   dtype_map = {
       "FLOAT_VECTOR": DataType.FLOAT_VECTOR,
       "BINARY_VECTOR": DataType.BINARY_VECTOR,
       "FLOAT16_VECTOR": DataType.FLOAT16_VECTOR,
       "BFLOAT16_VECTOR": DataType.BFLOAT16_VECTOR,
   }
   vector_dtype = dtype_map.get(dtype_str, DataType.FLOAT_VECTOR)
   ```

3. **Handle invalid dtype values**:
   ```python
   if dtype_str not in dtype_map:
       # Let Milvus handle the validation
       # Or raise error early to test Milvus's behavior
       pass
   ```

4. **Pass dtype to FieldSchema**:
   ```python
   fields = [
       FieldSchema(name='id', dtype=DataType.INT64, is_primary=True),
       FieldSchema(name='vector', dtype=vector_dtype, dim=dimension)
   ]
   ```

---

## Workaround

Until fixed:
- **Do not** include dtype-based test cases in campaigns
- **Do not** file bugs based on dtype test results
- Focus on other parameter families (metric_type, index_type, dimension, top_k)

---

## Related Issues

None. This is a tooling limitation, not a database finding.

---

## Resolution Plan

1. Implement dtype parameter support in MilvusAdapter._create_collection()
2. Test with valid dtype values first (FLOAT_VECTOR, BINARY_VECTOR)
3. Then add invalid dtype test cases to verify Milvus's validation
4. Add dtype test cases to future campaigns after fix is verified

---

## Metadata

- **Campaign**: R2
- **Case**: param-dtype-001
- **Classification**: Tooling gap (not a database bug)
- **Component**: adapters/milvus_adapter.py
- **Lines**: 178-199 (_create_collection method)
