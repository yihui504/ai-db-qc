# ISSUE-008: Pgvector search produces internal error with top_k=0 and accepts negative top_k values

## Metadata

| Field | Value |
|-------|-------|
| **Bug ID** | ISSUE-008 |
| **Database** | Pgvector v0.8.2 (PostgreSQL 17) |
| **Contract** | BND-002 (Top-K Parameter Boundaries) |
| **Bug Type** | TYPE-3 (top_k=0 error), TYPE-1 (negative top_k accepted) |
| **Severity** | High |
| **Date Discovered** | 2026-03-18 |

## Evidence Chain

### 1. Documentation Evidence (What Should Happen)

**Source**: [PostgreSQL LIMIT Clause](https://www.postgresql.org/docs/current/queries-limit.html)

PostgreSQL's standard `LIMIT` clause:
- `LIMIT 0` is valid SQL and returns zero rows (not an error)
- Negative LIMIT values should produce an error
- LIMIT must be a non-negative integer constant

For pgvector specifically, queries use the pattern:
```sql
SELECT * FROM items ORDER BY embedding <-> '[1,2,3]' LIMIT k;
```

The LIMIT parameter is handled by PostgreSQL's query engine, not pgvector directly.

### 2. Actual Behavior (What Happened)

Test results from `results/boundary_2025_001/pgvector_boundary_results.json`:

```json
{
  "contract_id": "BND-002",
  "database": "pgvector",
  "test_cases": [
    {
      "name": "Top-K = 0",
      "checks": [
        {"name": "Search succeeded", "status": true},
        {"name": "Exception during test", "status": false, "error": "invalid literal for int() with base 10: 'empty'"}
      ],
      "verdict": "TYPE-3"
    },
    {
      "name": "Negative top-K",
      "checks": [
        {"name": "Rejected (expected)", "status": false}
      ],
      "verdict": "TYPE-1"
    }
  ]
}
```

**top_k=0**: The query "succeeded" but produced an internal exception: `"invalid literal for int() with base 10: 'empty'"`. This error originates from the test adapter trying to parse the result count, suggesting that LIMIT 0 with pgvector's vector operators returns an unexpected result format.

**Negative top_k**: Negative LIMIT values were accepted. In standard PostgreSQL, negative LIMIT should produce an error: `ERROR: LIMIT must not be negative`. The fact that it was accepted suggests the test adapter may be formatting the query differently.

### 3. Analysis

**top_k=0 Error**: While `LIMIT 0` is valid in standard PostgreSQL (it returns zero rows), the combination of `LIMIT 0` with pgvector's vector distance operators (`<->`, `<=>`, etc.) and `ORDER BY` may produce unexpected behavior. The error `"invalid literal for int() with base 10: 'empty'"` suggests the result processing layer encounters an unexpected empty or sentinel value.

This is classified as TYPE-3 because the operation produces an unhandled exception rather than returning a clean empty result set. In a production application using a Pgvector client library, this could manifest as an unhandled exception crashing the application.

**Negative top_k**: PostgreSQL should reject negative LIMIT values. If the adapter is passing negative values that are accepted, this could be an adapter-level bug rather than a pgvector bug. However, pgvector's own documentation should clarify the valid range for LIMIT.

**Impact**: Application crashes in production when LIMIT=0 is encountered (e.g., in dynamic pagination where page size can be 0), unexpected error messages.

**Recommended Fix**: Ensure that LIMIT 0 with vector distance queries returns a clean empty result set. Verify that negative LIMIT values are properly rejected by PostgreSQL when combined with vector operators.

## References

1. [PostgreSQL LIMIT Clause Documentation](https://www.postgresql.org/docs/current/queries-limit.html)
2. [Pgvector Distance Functions and Operators (DeepWiki)](https://deepwiki.com/pgvector/pgvector/4-distance-functions-and-operators)
3. [Test Results: pgvector_boundary_results.json](../boundary_2025_001/pgvector_boundary_results.json)
