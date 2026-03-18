# [Bug] `num_entities` / `count_entities` does not reflect deletions until compaction

**Issue ID**: DEF-001  
**Component**: Milvus — Query Processing / Storage Stats  
**Affected Version**: v2.6.10 (Docker: `milvusdb/milvus:v2.6.10`)  
**Severity**: High  
**Contract Violated**: R3B — *"count_entities after delete must equal pre-delete count minus N_deleted"*  
**Reproducibility**: 100% (confirmed across 4 collection sizes: 100, 300, 500, 1000)  
**Discovered by**: ai-db-qc contract-based runtime testing framework, Layer E–F (2026-03-17)

---

## Summary

After deleting N entities from a Milvus collection and calling `flush()`, `collection.num_entities` and the `count_entities` expression still return the **pre-deletion count** rather than the updated logical count. The deleted entities are correctly hidden from search and query results (deletion is functionally effective), but the count statistic is stale until background compaction runs.

This is a **semantic API contract violation**: the documented behavior of `num_entities` implies it reflects the current logical state of the collection, not the physical segment-level count.

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

# 1. Create collection
fields = [
    FieldSchema(name="id",     dtype=DataType.INT64,         is_primary=True, auto_id=False),
    FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR,  dim=128),
]
schema = CollectionSchema(fields, description="DEF-001 repro")
coll = Collection(name="def001_repro", schema=schema)

# 2. Insert 1000 entities
vectors = np.random.rand(1000, 128).astype(np.float32)
ids     = list(range(1000))
coll.insert([ids, vectors.tolist()])
coll.flush()

print(f"After insert: num_entities = {coll.num_entities}")   # Expected: 1000

# 3. Delete 100 entities
delete_ids = list(range(100))
expr = f"id in {delete_ids}"
coll.delete(expr)
coll.flush()    # <-- flush does NOT trigger compaction

# 4. Read count
print(f"After delete+flush: num_entities = {coll.num_entities}")  # ACTUAL: 1000, EXPECTED: 900

# 5. Verify deletion is actually effective via query
results = coll.query(expr="id >= 0", output_fields=["id"])
print(f"Query result count: {len(results)}")  # Returns 900 (deletion IS effective)
```

---

## Expected Behavior

```
After insert: num_entities = 1000
After delete+flush: num_entities = 900   ← should reflect the deletion
Query result count: 900
```

---

## Actual Behavior

```
After insert: num_entities = 1000
After delete+flush: num_entities = 1000  ← stale — deletion NOT reflected
Query result count: 900                  ← query IS correct
```

The discrepancy between `num_entities` and the actual logical count persists until Milvus background compaction runs (configurable interval, default ~60 seconds).

---

## Quantitative Evidence

Tested across four collection sizes to confirm the bug is systematic, not a size-specific artefact:

| Collection Size (M) | N Deleted | num_entities (Actual) | Expected | Discrepancy |
|--------------------:|----------:|----------------------:|----------:|------------:|
| 100 | 10 | 100 | 90 | **+10** |
| 300 | 20 | 300 | 280 | **+20** |
| 500 | 50 | 500 | 450 | **+50** |
| 1000 | 100 | 1000 | 900 | **+100** |

All four cases reproduce consistently. Calling `flush()` after deletion has no effect on `num_entities`.

---

## Root Cause Analysis

Milvus uses a segment-based storage architecture. Deletions are implemented via **delete bitmaps** at the segment level — deleted entities become logically invisible to search and query operations immediately. However, `num_entities` reads the **physical segment record count**, which is only updated after **compaction** (an async background process, not triggered by `flush()`).

The semantic contract of `num_entities` — as implied by its name and the documentation — is that it returns the number of *logically present* entities. Instead, it returns a physical count that includes tombstoned records.

**Key distinction**:
- `collection.query(expr="id >= 0")` → returns **logical** count (correct after delete)
- `collection.num_entities` → returns **physical** count (stale until compaction)

---

## Cross-Database Comparison

Tested with the same deletion workflow against three other vector databases:

| Database | Count after delete+flush | Correct? |
|----------|--------------------------|----------|
| Milvus v2.6.10 | Pre-deletion count (stale) | ❌ |
| Qdrant latest | Updated count | ✅ |
| Weaviate 1.27.0 | Updated count | ✅ |
| pgvector pg16 | Updated count | ✅ |

Milvus is the **sole outlier** among the four databases.

---

## Impact

Applications using `num_entities` for:
- **Capacity management** (e.g., "is the collection full?") — will receive incorrect readings
- **Billing / quota calculations** — will over-count storage usage
- **Deletion verification** (e.g., "did my bulk delete succeed?") — will always appear as if deletion had no effect
- **Consistency checks / CI pipelines** — tests asserting `num_entities == expected` will fail spuriously

The discrepancy is **proportional to the number of pending deletions** and does not self-heal without explicit compaction.

---

## Workaround

Use a query-based count instead of `num_entities`:

```python
# Workaround: get logical entity count via query
results = coll.query(expr="id >= 0", output_fields=["id"])
actual_count = len(results)
```

Or trigger manual compaction (note: compaction is async and may take seconds to complete):

```python
from pymilvus import utility
utility.do_bulk_insert(...)  # triggers compaction as a side effect
# -- or --
# Wait for background compaction (default interval ~60s)
```

---

## Suggested Fix

1. `num_entities` should read from a logical entity counter that is decremented synchronously on `flush()` after deletion, rather than from raw segment record counts.
2. Alternatively, document clearly that `num_entities` reflects physical (pre-compaction) counts and provide a separate API (e.g., `logical_count()` or a query hint) for logical entity count.
3. At minimum, the documentation should state the compaction dependency explicitly.

---

## References

- **Test Campaign**: Layer E–F, Contract R3B (ai-db-qc framework)
- **Contract Definition**: R3B — `count_entities(coll) after delete(N) and flush == pre_count - N`
- **Related Defect**: DEF-004 (count-delete inconsistency in mixed-schema collections, same root cause)
- **Reproducibility**: 100% across 4 collection sizes, multiple test runs
- **Test Script**: `scripts/run_r5d_schema.py --adapter milvus` (R3B variant)

---

## Filing Checklist

- [x] Minimum reproduction script ready
- [x] Quantitative evidence across 4 sizes
- [x] Cross-DB comparison confirming Milvus-specific behaviour
- [x] Root cause identified (lazy compaction)
- [x] Workaround documented
- [x] Impact assessed (High)
- [ ] Filed on https://github.com/milvus-io/milvus/issues
