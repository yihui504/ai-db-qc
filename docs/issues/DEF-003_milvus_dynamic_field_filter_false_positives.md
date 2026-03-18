# [Bug] Filtered search with dynamic field predicates returns false positives for pre-extension entities

**Issue ID**: DEF-003  
**Component**: Milvus — Query Filtering / Dynamic Schema  
**Affected Version**: v2.6.10 (Docker: `milvusdb/milvus:v2.6.10`)  
**Severity**: High  
**Contract Violated**: SCH-002 — *"filtered search must only return entities satisfying the filter expression; untagged entities must not appear in tag-filtered results"*  
**Reproducibility**: 100% (confirmed across multiple runs)  
**Discovered by**: ai-db-qc contract-based runtime testing framework, Layer D (2026-03-17)

---

## Summary

After a Milvus collection with `enable_dynamic_field=True` undergoes schema extension (i.e., new dynamic fields are first used in a subsequent insert batch), executing a **filtered ANN search** using the new dynamic field as a predicate incorrectly returns entities that do **not** possess that field.

Specifically, entities inserted **before** the dynamic field was introduced ("pre-extension entities") appear in search results for a filter that should only match "post-extension" entities. This is a **false positive** bug: the filter predicate `tag_value > 0` is evaluated as *true* for entities where `tag_value` is absent.

No error is raised. The false positives are silently mixed into results.

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
    DataType
)
import numpy as np

connections.connect(alias="default", host="localhost", port=19530)

DIM = 128
N_BASE   = 200   # entities WITHOUT tag_value field
N_TAGGED = 300   # entities WITH tag_value > 0

# 1. Create collection with dynamic field enabled
fields = [
    FieldSchema(name="id",     dtype=DataType.INT64,        is_primary=True, auto_id=False),
    FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=DIM),
]
schema = CollectionSchema(fields, enable_dynamic_field=True)
coll = Collection(name="def003_repro", schema=schema)

# 2. Insert N_BASE baseline entities (no tag_value field)
base_ids     = list(range(N_BASE))
base_vectors = np.random.rand(N_BASE, DIM).astype(np.float32)
coll.insert([base_ids, base_vectors.tolist()])
coll.flush()

# 3. Insert N_TAGGED entities with tag_value dynamic field
tagged_ids     = list(range(N_BASE, N_BASE + N_TAGGED))
tagged_vectors = np.random.rand(N_TAGGED, DIM).astype(np.float32)
tagged_data = [
    {"id": tagged_ids[i], "vector": tagged_vectors[i].tolist(), "tag_value": i + 1}
    for i in range(N_TAGGED)
]
coll.insert(tagged_data)
coll.flush()

# 4. Build index and load
index_params = {"metric_type": "L2", "index_type": "HNSW", "params": {"M": 16, "efConstruction": 200}}
coll.create_index(field_name="vector", index_params=index_params)
coll.load()

# 5. Filtered ANN search — should ONLY return tagged entities
query_vec = np.random.rand(1, DIM).astype(np.float32)
results = coll.search(
    data=query_vec.tolist(),
    anns_field="vector",
    param={"metric_type": "L2", "params": {"ef": 64}},
    limit=N_TAGGED,
    expr="tag_value > 0",   # should match only tagged entities (ids 200–499)
    output_fields=["id", "tag_value"]
)

returned_ids = [r.id for r in results[0]]
false_positives = [i for i in returned_ids if i < N_BASE]   # pre-extension entities

print(f"Total results: {len(returned_ids)}")
print(f"False positives (pre-extension entities in tagged-only search): {len(false_positives)}")
# ACTUAL: ~100 false positives — pre-extension entities pass the filter despite lacking tag_value
```

---

## Expected Behavior

```
Total results: up to 300
False positives: 0   ← pre-extension entities (ids 0–199) must not appear
```

---

## Actual Behavior

```
Total results: ~100
False positives: ~100   ← pre-extension entities appear despite lacking tag_value
```

Pre-extension entities (ids 0–199, which have no `tag_value` field) are returned by a filter `tag_value > 0`. The false positive rate is approximately **50%** of the baseline population.

---

## Quantitative Evidence

| Metric | Value |
|--------|-------|
| N_base (no tag_value) | 200 |
| N_tagged (tag_value > 0) | 300 |
| Filter expression | `tag_value > 0` |
| Expected: only tagged entities | ≤ 300 (ids 200–499) |
| Actual: pre-extension false positives | **~100** (ids 0–199) |
| False positive rate | **~50%** of pre-extension entities |

---

## Root Cause Analysis

Milvus's filter evaluation logic applies the filter expression against segment-level schema. For pre-extension entities stored in segments with schema version V0 (before `tag_value` was introduced), the field `tag_value` is absent.

The semantically correct behavior is: **a missing dynamic field should evaluate to null/false for any positive comparison predicate** (i.e., `tag_value > 0` where `tag_value` is absent should be `false`, not `true`).

Instead, Milvus appears to **skip filter evaluation entirely** for segments where the dynamic field is not present in the segment schema, allowing all entities from those segments to pass through unconditionally. This is equivalent to treating a missing field as `+∞` rather than `null`.

**Note**: This bug co-occurs with DEF-002. DEF-002 shows that post-extension entities are invisible to ANN search (false negatives at the index level); DEF-003 shows that pre-extension entities incorrectly pass dynamic field filters (false positives at the filter evaluation level). Together, both halves of the expected behavior are violated simultaneously.

---

## Cross-Database Comparison

| Database | False positives for missing dynamic field filter? |
|----------|--------------------------------------------------|
| Milvus v2.6.10 | ❌ **Yes** (~50% of pre-extension entities) |
| pgvector pg16 | ✅ No (filter correctly excludes NULL-column rows) |
| Weaviate 1.27.0 | ✅ No (missing property treated as absent/false) |

---

## Impact

Any application that:
- Uses `enable_dynamic_field=True`
- Inserts data in batches (first without, then with, a new dynamic field)
- Uses the new field as a **filter predicate in ANN search**

...will receive **semantically incorrect results** containing entities that do not satisfy the filter. This directly undermines the correctness guarantee of filtered vector search, which is a core use case for Milvus in RAG, recommendation, and retrieval systems.

**Severity rationale**: HIGH — incorrect filter results in a core query operation, with no error or warning, directly affects semantic search quality and application correctness.

---

## Workaround

Avoid relying on dynamic field filters when the collection contains a mix of pre-extension and post-extension entities. As a mitigation:

1. Use a dedicated boolean/integer **static schema field** (not a dynamic field) for filtering, populated for all entities including pre-extension ones.
2. Alternatively, recreate the collection with the extended static schema and re-insert all data to ensure a uniform schema version across all segments.

---

## Related Issues

- **DEF-002**: `enable_dynamic_field=True`: entities inserted after dynamic schema extension invisible to ANN search (same root cause — schema version boundary in segment management)
- **DEF-001**: `count_entities` does not reflect deletions until compaction (independent root cause but same collection state)
- **DEF-004**: `count_entities` incorrect after deletions in mixed-schema collections

---

## References

- **Test Campaign**: Layer D, Contract SCH-002 (ai-db-qc framework)
- **Contract Definition**: SCH-002 — "filtered search must only return entities satisfying the filter expression; untagged entities must not appear in tag-filtered results"
- **Test Script**: `scripts/run_r5d_schema.py --adapter milvus`
- **Reproducibility**: 100% across multiple runs

---

## Filing Checklist

- [x] Minimum reproduction script ready
- [x] Quantitative evidence (~100 false positives / 50% FP rate)
- [x] Cross-DB comparison (pgvector, Weaviate both pass SCH-002)
- [x] Root cause hypothesis documented (missing field treated as pass-through)
- [x] Impact assessed (High — semantic search correctness violation)
- [x] Related issues identified (DEF-002, DEF-004)
- [ ] Filed on https://github.com/milvus-io/milvus/issues
