# DEF-004: `count_entities` returns stale count after deletion in mixed-schema (dynamic field) collection

**Database**: Milvus  
**Version**: 2.4.x (reproduced on 2.4.13)  
**Severity**: Medium  
**Oracle**: Count consistency (CCO)  
**Related**: DEF-001 (same root cause, different collection configuration)

---

## Summary

When a Milvus collection is created with `enable_dynamic_field=True` (mixed-schema mode), inserting entities in two batches (one base batch without extra fields, one tagged batch with dynamic fields) and then deleting a subset of entities causes `count_entities()` to return a stale value that does not reflect the deletions. The count corresponds to the total number of inserted entities rather than the number of surviving entities.

---

## Environment

- **Milvus**: 2.4.13 (standalone Docker, `milvusdb/milvus:v2.4.13`)
- **pymilvus**: 2.4.9
- **Host OS**: Ubuntu 22.04 / Windows 11 WSL2
- **Collection config**: `enable_dynamic_field=True`, IVF_FLAT index, L2 metric

---

## Steps to Reproduce

```python
from pymilvus import MilvusClient
import numpy as np

client = MilvusClient(uri="http://localhost:19530")

# Create collection with dynamic field enabled
client.create_collection(
    collection_name="test_mixed",
    dimension=128,
    enable_dynamic_field=True,
)

# Phase A: insert base batch (no dynamic fields)
N_BASE = 200
base_data = [{"id": i, "vector": np.random.rand(128).tolist()} for i in range(N_BASE)]
client.insert("test_mixed", base_data)

# Phase B: insert tagged batch (with dynamic field "tag")
N_TAGGED = 300
tagged_data = [
    {"id": N_BASE + i, "vector": np.random.rand(128).tolist(), "tag": "new"}
    for i in range(N_TAGGED)
]
client.insert("test_mixed", tagged_data)

# Flush to ensure persistence
client.flush("test_mixed")

# Delete a subset of entities
DELETE_IDS = list(range(0, 50))  # delete 50 entities from base batch
client.delete("test_mixed", ids=DELETE_IDS)

# Wait and check count
import time
time.sleep(2)

count = client.query("test_mixed", filter="", output_fields=["count(*)"])
print(f"count_entities: {count}")  # Expected: 450, Actual: 500
```

---

## Expected Behavior

After inserting 200 + 300 = 500 entities and deleting 50, `count_entities()` (or `query` with `count(*)`) should return **450**.

---

## Actual Behavior

`count_entities()` returns **500**, reflecting the total number of inserted entities before deletion. The deletion is not visible to the count operation.

Querying actual records confirms the deletions took effect (i.e., the deleted IDs are not returned by vector search or `query` operations), but the aggregate count does not update until a compaction cycle completes.

---

## Root Cause Analysis

This is consistent with DEF-001 (lazy compaction). Milvus uses a log-structured merge (LSM) approach where delete operations are recorded as tombstone markers in a delete log, not applied immediately to the segments. The `count_entities` / `count(*)` path reads the segment metadata (row count) without applying tombstone offsets, causing a discrepancy between the logical count and the physical segment count.

The mixed-schema (dynamic field) configuration adds an additional dimension: when Phase A and Phase B data reside in different segments (since they have different schema shapes), the compaction that would normally merge and apply tombstones across segments is further deferred.

---

## Workaround

Calling `client.compact("test_mixed")` and waiting for the compaction job to complete before querying the count returns the correct value. Alternatively, use a filtered `query` to count surviving entities:

```python
# Workaround: count via query instead of count_entities
result = client.query("test_mixed", filter='id >= 0', output_fields=["id"])
actual_count = len(result)
```

---

## Additional Notes

- This bug affects any workload that uses `enable_dynamic_field=True` with multi-phase inserts followed by deletions.
- The issue is observable under normal operating conditions without artificial load, making it a correctness concern for applications that rely on `count_entities` for data integrity checks.
- A related bug (DEF-001) was observed in standard (non-dynamic-field) collections under similar conditions, suggesting the root cause is in the shared compaction path rather than the dynamic field code.

---

## Suggested Fix

The `count_entities` / `count(*)` implementation should apply pending tombstone counts from the delete log before returning the aggregate count, similar to how `query` and `search` operations apply tombstone filters. Alternatively, document clearly that `count_entities` may be stale until the next compaction cycle and provide a `consistent_count()` API with linearizable semantics.
