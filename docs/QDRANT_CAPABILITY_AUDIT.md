# Qdrant Capability Audit

**Document Version**: 1.0
**Date**: 2026-03-09
**Purpose**: Verify Qdrant operations required for R4 semantic properties testing
**Status**: AUDIT COMPLETE

---

## Executive Summary

This audit verifies that Qdrant supports all operations required by the 8 R4 semantic properties. All critical operations are **SUPPORTED**, with two key architectural differences from Milvus that require sequence adaptation:

1. **No explicit `load()` operation** - Qdrant auto-loads collections
2. **No explicit `build_index()` operation** - Qdrant auto-creates HNSW index

**Conclusion**: R4 can proceed with Qdrant as the second database using adaptive sequences.

---

## Operation Support Matrix

| Operation | Qdrant Support | Milvus Equivalent | Notes |
|-----------|---------------|-------------------|-------|
| **create_collection** | SUPPORTED | create_collection | ✅ Direct mapping |
| **upsert (insert)** | SUPPORTED | insert | ✅ Uses "upsert" terminology |
| **delete (by ID)** | SUPPORTED | delete | ✅ Direct mapping |
| **search** | SUPPORTED | search | ✅ Direct mapping |
| **delete_collection (drop)** | SUPPORTED | drop_collection | ✅ Direct mapping |
| **build_index** | NOT APPLICABLE | build_index | ⚠️ Qdrant auto-creates index |
| **load** | NOT APPLICABLE | load | ⚠️ Qdrant auto-loads |

---

## Detailed Operation Analysis

### 1. Collection Creation

**Status**: SUPPORTED

**Qdrant API**:
```python
from qdrant_client import QdrantClient, models

client = QdrantClient(url="http://localhost:6333")
client.create_collection(
    collection_name="{collection_name}",
    vectors_config=models.VectorParams(size=100, distance=models.Distance.COSINE),
)
```

**Milvus Equivalent**:
```python
from pymilvus import Collection, FieldSchema, CollectionSchema

collection = Collection(name="{collection_name}", schema=schema)
```

**Mapping**: ✅ **DIRECT** - Both databases support collection creation with dimension and metric configuration.

---

### 2. Insert / Upsert

**Status**: SUPPORTED

**Qdrant API**:
```python
from qdrant_client.models import PointStruct

client.upsert(
    collection_name="{collection_name}",
    points=[
        PointStruct(
            id=1,
            vector=[0.9, 0.1, 0.1],
            payload={"color": "red"},
        ),
    ],
)
```

**Milvus Equivalent**:
```python
collection.insert([{"vector": [0.9, 0.1, 0.1], "color": "red"}])
```

**Mapping**: ✅ **DIRECT** - Qdrant uses "upsert" terminology but behavior is equivalent to insert. Qdrant explicitly states all APIs are **idempotent**.

**Key Difference**: Qdrant uses explicit `PointStruct` with required `id` field, while Milvus can auto-generate IDs.

---

### 3. Delete by ID

**Status**: SUPPORTED

**Qdrant API**:
```python
client.delete(
    collection_name="{collection_name}",
    points_selector=models.PointIdsList(
        points=[0, 3, 100],
    ),
)
```

**Milvus Equivalent**:
```python
collection.delete(expr="id in [0, 3, 100]")
```

**Mapping**: ✅ **DIRECT** - Both support deletion by ID list.

**Additional**: Qdrant also supports filter-based deletion (similar to Milvus expr).

---

### 4. Search

**Status**: SUPPORTED

**Qdrant API**:
```python
hits = client.search(
    collection_name="{collection_name}",
    query_vector=query_vector,
    limit=5
)
```

**Alternative (newer API)**:
```python
search_result = client.query_points(
    collection_name="{collection_name}",
    query=[0.2, 0.1, 0.9, 0.7],
    with_payload=False,
    limit=3
).points
```

**Milvus Equivalent**:
```python
results = collection.search(
    data=[query_vector],
    limit=5,
    anns_field="vector",
    param={"metric_type": "L2", "params": {"nprobe": 10}}
)
```

**Mapping**: ✅ **DIRECT** - Both support vector similarity search with top_k/limit.

**Key Difference**: **Qdrant does NOT require explicit `load()` before search** - it auto-loads.

---

### 5. Delete Collection (Drop)

**Status**: SUPPORTED

**Qdrant API**:
```python
client.delete_collection(collection_name="{collection_name}")
```

**Milvus Equivalent**:
```python
collection.drop()
```

**Mapping**: ✅ **DIRECT** - Both support collection deletion.

**Post-drop behavior**: After deletion, operations should fail with "collection not found" error.

---

### 6. Build Index (Not Applicable)

**Status**: NOT APPLICABLE - Qdrant auto-creates HNSW index

**Qdrant Behavior**:
- Qdrant automatically builds HNSW index in the background
- Index creation is controlled by `hnsw_config` and `optimizers_config`
- No explicit "build index" operation required
- Index is built automatically when vectors are upserted

**Milvus Behavior**:
- Requires explicit `create_index()` call
- Index must exist before `load()` operation

**R4 Adaptation**:
```yaml
# Adaptive sequence
build_index():  # Optional for Milvus, skipped for Qdrant
```

---

### 7. Load Collection (Not Applicable)

**Status**: NOT APPLICABLE - Qdrant auto-loads

**Qdrant Behavior**:
- Qdrant automatically loads collections into memory when needed
- No explicit "load" operation required
- Search operations trigger automatic loading

**Milvus Behavior**:
- Requires explicit `load()` call before search
- Collection must be in "loaded" state for search to work

**R4 Adaptation**:
```yaml
# Adaptive sequence
load():  # Optional for Milvus, skipped for Qdrant
```

---

## Behavior After Drop

**Status**: SUPPORTED (Standard Behavior)

**Expected Behavior**: Operations on dropped collection should fail with clear error

**Qdrant Expected Error**: "collection not found" or similar

**Milvus Behavior** (from R3): `SchemaNotReadyException: (code=1, message="Collection 'test_r3_seq004' not exist")`

**Oracle Classification**: ✅ **CONSISTENT** - Both should fail with "not found" errors

---

## Empty Collection Search

**Status**: NEEDS EMPIRICAL VERIFICATION

**Qdrant Documentation**: Does not explicitly specify behavior for searching empty collections

**Expected Behaviors** (any is acceptable):
- Return empty results (most likely)
- Succeed with auto-load
- Error (unlikely)

**Milvus Behavior** (from R3): Requires `load()` even for empty collections

**Oracle Classification**: ⚠️ **ALLOWED DIFFERENCE** - Different behaviors are acceptable for this edge case

---

## Idempotency Guarantees

**Status**: EXPLICITLY SUPPORTED

**Qdrant Documentation**:
> "All APIs in Qdrant, including point loading, are idempotent. It means that executing the same method several times in a row is equivalent to a single execution."

**Milvus Behavior** (from R3):
- Delete operations are idempotent (all deletes succeed)
- Collection creation allows duplicates

**Oracle Classification**:
- Both databases support idempotency → ✅ **CONSISTENT**
- Different implementation strategies → ⚠️ **ALLOWED DIFFERENCE**

---

## Key Architectural Differences Summary

### 1. Memory Management

| Aspect | Milvus | Qdrant | Oracle Classification |
|--------|--------|--------|----------------------|
| **Load Requirement** | Explicit `load()` required | Auto-load on access | ALLOWED DIFFERENCE ⚠️ |
| **Index Creation** | Explicit `create_index()` | Auto-creates HNSW | ALLOWED DIFFERENCE ⚠️ |
| **Memory Model** | Load-based architecture | Auto-managed | Architectural choice |

### 2. Operation Terminology

| Operation | Milvus | Qdrant | Compatibility |
|-----------|--------|--------|---------------|
| **Insert data** | `insert()` | `upsert()` | ✅ Compatible |
| **Remove collection** | `drop()` | `delete_collection()` | ✅ Compatible |
| **ID requirement** | Optional | Required (PointStruct) | ⚠️ Adapter must handle |

### 3. State Management

| Aspect | Milvus | Qdrant | R4 Impact |
|--------|--------|--------|-----------|
| **Collection states** | Not loaded → Loaded | Always ready | Sequences must adapt |
| **Index states** | No index → Indexed | Auto-indexed | Sequences must adapt |
| **Search prerequisite** | Must load() | No prerequisite | Adaptive steps |

---

## R4 Adaptation Strategy

### Adaptive Sequence Template

For each R4 test case, sequences will use the following adaptive pattern:

```yaml
# Generic adaptive sequence (works on both databases)
1. create_collection(name="test_r4_XXX", dimension=128)
2. upsert(vectors)  # Both databases support
3. build_index()  # OPTIONAL: Milvus executes, Qdrant skips
4. load()         # OPTIONAL: Milvus executes, Qdrant skips
5. search(query_vector)  # Works on both
6. delete(ids=[...])     # Works on both
7. search(query_vector)  # TEST step
8. delete_collection()   # Works on both
```

### Adapter Implementation Notes

**Qdrant Adapter Requirements**:
1. **ID handling**: Qdrant requires explicit IDs in `PointStruct` - adapter must generate or use provided IDs
2. **Skip strategy**: Adapter should have no-op methods for `build_index()` and `load()`
3. **Error mapping**: Map Qdrant errors to consistent format for differential comparison
4. **Wait option**: Qdrant supports `wait=True` for synchronous operations - use for consistency

---

## Semantic Property Testability

### Property 1: Post-Drop Rejection
**Status**: DIRECTLY TESTABLE ✅
- Qdrant supports collection deletion
- Post-drop operations will fail with "not found"
- No adaptation needed

### Property 2: Deleted Entity Visibility
**Status**: DIRECTLY TESTABLE ✅
- Qdrant supports delete by ID
- Qdrant supports search
- Delete idempotency is guaranteed

### Property 3: Delete Idempotency
**Status**: DIRECTLY TESTABLE ✅
- Qdrant explicitly guarantees idempotency
- Multiple deletes on same ID should behave consistently

### Property 4: Index-Independent Search
**Status**: REQUIRES ADAPTATION ⚠️
- Qdrant always has index (auto-created)
- Milvus requires index
- **Oracle Classification**: ALLOWED DIFFERENCE (architectural)

### Property 5: Load-State Enforcement
**Status**: REQUIRES ADAPTATION ⚠️
- Qdrant auto-loads (no load operation)
- Milvus requires explicit load
- **Oracle Classification**: ALLOWED DIFFERENCE (architectural)

### Property 6: Empty Collection Handling
**Status**: DIRECTLY TESTABLE ✅
- Both support empty collection creation
- Both support search on empty collections
- Any behavior is acceptable (undefined edge case)

### Property 7: Non-Existent Delete Tolerance
**Status**: DIRECTLY TESTABLE ✅
- Qdrant supports delete by ID
- Idempotency guarantees consistent behavior

### Property 8: Collection Creation Idempotency
**Status**: DIRECTLY TESTABLE ✅
- Qdrant has `collection_exists()` check
- Can handle duplicate creation attempts
- **Note**: Need empirical verification of exact behavior

---

## Sources

**Qdrant Documentation**:
- [Qdrant Quickstart](https://qdrant.tech/documentation/quickstart/) - Basic operations
- [Qdrant Python Client](https://python-client.qdrant.tech/) - API reference
- [Points](https://qdrant.tech/documentation/concepts/points/) - Point operations and idempotency
- [Collections](https://qdrant.tech/documentation/concepts/collections/) - Collection management

**Milvus Documentation**:
- pymilvus v2.6.2
- Milvus server v2.6.10

---

## Conclusion

**Capability Audit Result**: ✅ **PASS**

All 8 R4 semantic properties can be tested on Qdrant. The two architectural differences (no explicit load/index operations) are **ALLOWED DIFFERENCES** according to the differential oracle framework.

**Recommendation**: Proceed with R4 implementation using Qdrant as the second database with adaptive sequence design.

---

**END OF QDRANT CAPABILITY AUDIT**

**Status**: Audit complete. All required operations supported. Ready for Qdrant adapter implementation.
