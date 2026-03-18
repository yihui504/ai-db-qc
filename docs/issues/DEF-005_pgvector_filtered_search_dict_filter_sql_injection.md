# DEF-005 — pgvector Adapter: `_filtered_search` Renders Dict Filter as Python `repr` Instead of SQL Predicate

**ID:** DEF-005  
**Database / Component:** pgvector adapter (`adapters/pgvector_adapter.py`)  
**Category:** Framework-level adapter bug (NOT a database bug)  
**Severity:** High (all filtered searches against pgvector with dict-format filters produce broken SQL)  
**Status:** FIXED (2026-03-17)  
**Detected by:** Code review / manual triage of LIKELY_BUG verdicts  
**Oracle:** N/A — SQL syntax error surfaced during test execution  

---

## Summary

`PgvectorAdapter._filtered_search()` accepted the `filter` parameter as either a `str` (raw SQL predicate) or a `dict` (structured condition identical to Milvus/Qdrant dict filters). When a `dict` was passed, the adapter appended it to the SQL query verbatim via Python f-string interpolation:

```python
where = f"WHERE {filter_expr}" if filter_expr else ""
```

A dict such as `{"tag": "new"}` was rendered as the Python string `WHERE {'tag': 'new'}`, producing an invalid SQL statement that PostgreSQL rejects with a syntax error.

---

## Root Cause

Line 339 (pre-fix) in `pgvector_adapter.py`:

```python
# BUGGY CODE (before fix)
where = f"WHERE {filter_expr}" if filter_expr else ""
```

When `filter_expr` is a `dict`, Python's f-string calls `str(filter_expr)`, producing the Python dict representation (`{'tag': 'new'}`) rather than a valid SQL WHERE clause (`tag = 'new'`).

---

## Reproduction

```python
from adapters.pgvector_adapter import PgvectorAdapter

adapter = PgvectorAdapter(...)
result = adapter.execute({
    "operation": "filtered_search",
    "params": {
        "collection_name": "test_col",
        "vector": [0.1] * 128,
        "filter": {"tag": "new"},   # dict filter — triggers the bug
        "top_k": 10,
    }
})
# Expected: valid SQL results filtered by tag = 'new'
# Actual:   SQL error — "WHERE {'tag': 'new'}" is invalid SQL
```

PostgreSQL error output (via docker exec psql):
```
ERROR:  syntax error at or near "{"
LINE 1: SELECT id, embedding <-> '...'::vector AS dist FROM "test_col" WHERE {'tag': 'new'} ...
```

---

## Impact

- **All** filtered search test cases targeting pgvector with dict-format filters fail with a SQL error.
- Test oracle reports `ERROR` status, not a genuine database bug.
- False-positive LIKELY_BUG verdicts were generated because the oracle saw zero results where results were expected.
- Affected test dimensions: R5D filter, hybrid, schema tests wherever `filter` is a dict.

---

## Fix

Added a new static method `_filter_to_sql(filter_expr)` to `PgvectorAdapter` that converts a `dict` or `str` filter into a valid PostgreSQL WHERE predicate:

```python
@staticmethod
def _filter_to_sql(filter_expr):
    """Convert filter expression (str or dict) to a valid SQL predicate string."""
    if not filter_expr:
        return ""
    if isinstance(filter_expr, str):
        return filter_expr          # already raw SQL
    if not isinstance(filter_expr, dict):
        return ""
    op_map = {"gt": ">", "gte": ">=", "lt": "<", "lte": "<="}
    parts = []
    for key, val in filter_expr.items():
        if isinstance(val, dict):   # range condition
            for range_op, range_val in val.items():
                sql_op = op_map.get(range_op)
                if sql_op:
                    parts.append(f"{key} {sql_op} {range_val!r}")
        elif isinstance(val, str):
            parts.append(f"{key} = '{val.replace(chr(39), chr(39)*2)}'")
        elif isinstance(val, bool):
            parts.append(f"{key} = {str(val).upper()}")
        elif val is None:
            parts.append(f"{key} IS NULL")
        else:
            parts.append(f"{key} = {val}")
    return " AND ".join(parts)
```

`_filtered_search` was updated to call `_filter_to_sql` before constructing the WHERE clause:

```python
sql_predicate = self._filter_to_sql(filter_expr)
where = f"WHERE {sql_predicate}" if sql_predicate else ""
```

---

## Verification

After the fix:
- `{"tag": "new"}` → `WHERE tag = 'new'` ✓
- `{"score": {"gt": 5.0, "lte": 10.0}}` → `WHERE score > 5.0 AND score <= 10.0` ✓
- `"tag == 'new'"` (raw SQL string) → `WHERE tag == 'new'` ✓ (pass-through)
- Empty dict / None → no WHERE clause ✓

---

## Lessons Learned

Adapter interfaces that accept structured filter dicts must explicitly document the expected type and perform type-aware conversion to the target query language. A generic f-string interpolation of `filter_expr` is never safe when the parameter type is not guaranteed to be a string.

The framework should enforce a consistent filter contract across all adapters and add integration tests that verify dict-format filters produce correct SQL/query output before running oracle evaluations.
