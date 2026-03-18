# [Bug] `enable_dynamic_field=True`: entities inserted after dynamic schema extension are invisible to ANN search

**Issue ID**: DEF-002  
**Component**: Milvus — Indexing Pipeline / Dynamic Schema  
**Affected Version**: v2.6.10 (Docker: `milvusdb/milvus:v2.6.10`)  
**Severity**: High  
**Contract Violated**: SCH-001 — *"entities inserted after dynamic field extension must be retrievable via standard ANN search"*  
**Reproducibility**: 100% (confirmed across multiple runs)  
**Discovered by**: ai-db-qc contract-based runtime testing framework, Layer D (2026-03-17)

---

## Summary

When a Milvus collection is created with `enable_dynamic_field=True`, inserting entities **after** a new dynamic field has been introduced causes those entities to be **completely invisible to ANN (approximate nearest-neighbor) search**. The entities are stored (queryable via `collection.query()`), but do not appear in ANN search results regardless of `top_k`.

No error is raised at insert, flush, or search time. The data loss is **silent**.

---

## Environment

| Item | Value |
|------|-------|
| Milvus | v2.6.10 (`milvusdb/milvus:v2.6.10`, Docker) |
| pymilvus | 2.6.2 |
| Python | 3.10 |
| OS | Windows 11 / Docker Desktop |
| Date Discovered | 2026-03-17 |

---

## Steps to Reproduce

```python
from pymilvus import (
    connections, Collection, CollectionSchema, FieldSchema,
    DataType, utility
)
import numpy as np

connections.connect(alias="default", host="localhost", port=19530)

DIM = 128
N_BASE   = 200   # entities without extra fields
N_TAGGED = 300   # entities with new dynamic field "tag_value"

# 1. Create collection with dynamic field enabled
fields = [
    FieldSchema(name="id",     dtype=DataType.INT64,        is_primary=True, auto_id=False),
    FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=DIM),
]
schema = CollectionSchema(fields, enable_dynamic_field=True)
coll = Collection(name="def002_repro", schema=schema)

# 2. Insert N_BASE baseline entities (no extra fields)
base_ids     = list(range(N_BASE))
base_vectors = np.random.rand(N_BASE, DIM).astype(np.float32)
coll.insert([base_ids, base_vectors.tolist()])
coll.flush()

# 3. Insert N_TAGGED "tagged" entities with a new dynamic field
tagged_ids     = list(range(N_BASE, N_BASE + N_TAGGED))
tagged_vectors = np.random.rand(N_TAGGED, DIM).astype(np.float32)

tagged_data = [
    {"id": tagged_ids[i], "vector": tagged_vectors[i].tolist(), "tag_value": i + 1}
    for i in range(N_TAGGED)
]
coll.insert(tagged_data)
coll.flush()

# 4. Build HNSW index and load
index_params = {"metric_type": "L2", "index_type": "HNSW", "params": {"M": 16, "efConstruction": 200}}
coll.create_index(field_name="vector", index_params=index_params)
coll.load()

# 5. ANN search — top_k = N_BASE + N_TAGGED to retrieve everything
query_vec = np.random.rand(1, DIM).astype(np.float32)
results = coll.search(
    data=query_vec.tolist(),
    anns_field="vector",
    param={"metric_type": "L2", "params": {"ef": 64}},
    limit=N_BASE + N_TAGGED,
    output_fields=["id"]
)

returned_ids = [r.id for r in results[0]]
print(f"Search returned: {len(returned_ids)} entities")      # ACTUAL: 200

# 6. Verify via query that tagged entities DO exist
all_entities = coll.query(expr="id >= 0", output_fields=["id"])
print(f"Query (ground truth): {len(all_entities)} entities")  # Returns 500

tagged_in_search = [i for i in returned_ids if i >= N_BASE]
print(f"Tagged entities in search results: {len(tagged_in_search)}")  # ACTUAL: 0
```

---

## Expected Behavior

```
Search returned: 500 entities      ← all inserted entities should be searchable
Query (ground truth): 500 entities
Tagged entities in search results: 300
```

---

## Actual Behavior

```
Search returned: 200 entities      ← only baseline (pre-extension) entities visible
Query (ground truth): 500 entities ← all entities exist in storage
Tagged entities in search results: 0  ← 300 tagged entities completely missing
```

Entities inserted after the dynamic schema extension are **completely absent from ANN search results**, despite being correctly stored and queryable.

---

## Quantitative Evidence

| Metric | Value |
|--------|-------|
| N_base (pre-extension) | 200 |
| N_tagged (post-extension) | 300 |
| ANN search top_k | 500 (= N_base + N_tagged) |
| Search results returned | **200** (only baseline) |
| Tagged entities in results | **0 / 300** (0% recall on tagged segment) |
| Query ground truth | 500 (all entities present in storage) |

The recall drop on tagged entities is **100%** — not a partial indexing issue but a complete indexing failure for the post-extension segment.

---

## Root Cause Analysis

The dynamic field extension appears to create a **schema version boundary** in Milvus's internal segment management. Entities inserted after the dynamic field was first used are stored in a new logical segment that carries an updated schema version. The HNSW index, however, does not incorporate this new segment into the search graph — possibly because the index was built against the original schema version and is not automatically updated when a new segment with a different schema version arrives.

This is distinct from a missing `rebuild_index` step: the bug manifests even when `create_index` / `rebuild_index` is called **after** all insertions are complete.

**Suspected failure path**:
1. `create_index()` is called after both batches are inserted
2. The index builder processes segments from schema version V0 (N_base) but skips or incorrectly handles segments from schema version V1 (N_tagged)
3. Result: ANN search graph covers only V0 segments

---

## Cross-Database Comparison

Schema evolution behavior for dynamic columns across other databases:

| Database | Entities after schema extension visible in ANN? |
|----------|-------------------------------------------------|
| Milvus v2.6.10 | ❌ **No** (0% recall on post-extension entities) |
| pgvector pg16 | ✅ Yes (SCH-001 PASS) |
| Weaviate 1.27.0 | ✅ Yes (SCH-001 PASS) |

---

## Impact

Any application that:
- Uses `enable_dynamic_field=True`
- Inserts data with new fields after initial population
- Performs ANN similarity search

...will **silently lose all recall** on the post-extension entities with no error, warning, or indication that data is missing from search.

**Severity rationale**: HIGH — silent data loss in a primary database operation (ANN search) is a correctness regression, not a performance issue.

---

## Workaround

None confirmed. The following do **not** fix the issue:
- Calling `coll.flush()` after all insertions before index creation
- Dropping and recreating the index after all insertions
- Using different index types (IVF_FLAT, FLAT)

Potential mitigation: avoid inserting dynamic-field entities into a live collection. Instead, create a new collection with the extended schema and re-insert all data.

---

## Related Issues

- **DEF-003**: Filtered search with dynamic field predicates returns false positives for pre-extension entities (same root cause, different symptom — affects filter evaluation rather than indexing)
- **DEF-004**: count_entities incorrect after deletions in mixed-schema collections

---

## References

- **Test Campaign**: Layer D, Contract SCH-001 (ai-db-qc framework)
- **Contract Definition**: SCH-001 — entities inserted after dynamic field extension must be retrievable via standard ANN search
- **Test Script**: `scripts/run_r5d_schema.py --adapter milvus`
- **Reproducibility**: 100% across multiple collection sizes and test runs

---

## Filing Checklist

- [x] Minimum reproduction script ready
- [x] Quantitative evidence (0/300 recall on tagged segment)
- [x] Cross-DB comparison (Weaviate/pgvector both pass SCH-001)
- [x] Root cause hypothesis documented
- [x] Impact assessed (High — silent data loss)
- [x] Related issues identified (DEF-003, DEF-004)
- [ ] Filed on https://github.com/milvus-io/milvus/issues
