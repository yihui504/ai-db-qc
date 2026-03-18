# DEF-007 — Weaviate Adapter: Dynamic Properties Not Pre-Registered in Schema, Causing Empty Filtered Search Results

**ID:** DEF-007  
**Database / Component:** Weaviate adapter (`adapters/weaviate_adapter.py`)  
**Category:** Framework-level adapter bug (NOT a database bug)  
**Severity:** High (all filtered searches on non-`_orig_id` fields return empty results)  
**Status:** FIXED (2026-03-17)  
**Detected by:** Code review / oracle LIKELY_BUG escalation on schema-dimension test cases  
**Oracle:** FUO (Filtered-vs-Unfiltered Oracle) — filtered result count was 0 while unfiltered returned expected results  

---

## Summary

`WeaviateAdapter._create_collection()` only declared a single property (`_orig_id`) in the
Weaviate class schema at collection creation time. When vectors with additional scalar fields
(e.g., `{"tag": "new", "score": 7.5}`) were subsequently inserted via `_insert()`, those
properties were stored in the object payload but were **not registered in the Weaviate schema**.

In Weaviate v1, GraphQL `where` filters can only match fields that are declared in the class
schema. Filtering on an undeclared property silently returns zero results, even though the
objects exist in the collection.

---

## Root Cause

`_create_collection` (pre-fix):

```python
schema_body = {
    "class": wv_name,
    "vectorizer": "none",
    "vectorIndexConfig": {"distance": metric},
    "properties": [
        {"name": "_orig_id", "dataType": ["int"]},  # only _orig_id registered
        # dynamic fields (tag, score, ...) NOT registered here
    ],
}
```

`_insert` (pre-fix) populated `properties` with arbitrary scalar data:

```python
props: Dict[str, Any] = {"_orig_id": int(id_)}
if scalar and i < len(scalar):
    props.update(scalar[i])   # e.g., adds {"tag": "new"}
```

But those extra properties were never added to the class schema, so Weaviate's query engine
did not index them and the WHERE filter `{ path: ["tag"] operator: Equal valueText: "new" }`
produced an empty result set.

---

## Reproduction

```python
from adapters.weaviate_adapter import WeaviateAdapter

adapter = WeaviateAdapter(...)

# Create collection (only _orig_id in schema)
adapter.execute({"operation": "create_collection",
                 "params": {"collection_name": "test_col", "dim": 128}})

# Insert 100 vectors with scalar field "tag"
adapter.execute({"operation": "insert",
                 "params": {
                     "collection_name": "test_col",
                     "vectors": [[0.1]*128] * 100,
                     "ids": list(range(100)),
                     "scalar_data": [{"tag": "new"}] * 50 + [{"tag": "old"}] * 50,
                 }})

# Filtered search on "tag"
result = adapter.execute({"operation": "filtered_search",
                           "params": {
                               "collection_name": "test_col",
                               "vector": [0.1]*128,
                               "filter": {"tag": "new"},
                               "top_k": 10,
                           }})

# Expected: 10 results from the "new" half
# Actual:   0 results (tag property unknown to Weaviate schema)
```

---

## Impact

- All filtered searches on any property other than `_orig_id` return empty results in Weaviate.
- FUO oracle: filtered count (0) < unfiltered count → escalates to SUSPICIOUS/LIKELY_BUG.
- Entire R5D filter and schema test dimensions are affected for the Weaviate backend.
- False-positive bug verdicts were generated for every filter test case in the Weaviate campaign.

---

## Fix

Added `_ensure_properties(wv_name, props)` to `WeaviateAdapter`. This method:

1. Fetches the current property list from the Weaviate schema via `GET /schema/{wv_name}`.
2. For each key in `props` that is not already registered, infers the Weaviate data type
   (`boolean`, `int`, `number`, `text`) from the Python value type.
3. Registers each missing property via `POST /schema/{wv_name}/properties`.

`_insert` was updated to call `_ensure_properties` **before** the batch insert:

```python
def _insert(self, params):
    # ...
    if scalar:
        all_keys = {}
        for s in scalar:
            if isinstance(s, dict):
                all_keys.update(s)
        if all_keys:
            self._ensure_properties(wv_name, all_keys)   # register new props first
    # ... proceed with batch insert
```

Type inference rules:

| Python type | Weaviate dataType |
|-------------|------------------|
| `bool`      | `["boolean"]`    |
| `int`       | `["int"]`        |
| `float`     | `["number"]`     |
| `str` / other | `["text"]`     |

---

## Verification

After the fix:
- Inserting `scalar_data=[{"tag": "new"}]` → `tag` is auto-registered as `text` in schema ✓
- Subsequent `filtered_search(filter={"tag": "new"})` returns correct results ✓
- Re-inserting into the same collection does not cause duplicate-property errors (checked via
  `GET /schema` before registering) ✓
- Numeric properties (`score: 7.5`) are correctly registered as `number` and filterable ✓

---

## Lessons Learned

Weaviate requires explicit schema management that other vector databases (Milvus, Qdrant) do not.
Framework adapters targeting Weaviate must treat schema registration as part of the insert
lifecycle, not as a one-time setup step.

The framework should add a schema-consistency check to the adapter test suite: after inserting
with scalar data, verify that all inserted property names appear in the Weaviate class schema
before running any filter-based oracle checks.

A more robust long-term approach would be to accept a `schema` definition in `create_collection`
params that declares all expected properties up front, mirroring how Milvus handles field schemas.
