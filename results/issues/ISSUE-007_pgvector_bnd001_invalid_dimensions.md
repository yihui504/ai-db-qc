# ISSUE-007: Pgvector accepts invalid vector dimensions (dim=0, dim=-1, dim=100000) and dimension mismatch

## Metadata

| Field | Value |
|-------|-------|
| **Bug ID** | ISSUE-007 |
| **Database** | Pgvector v0.8.2 (PostgreSQL 17) |
| **Contract** | BND-001 (Vector Dimension Boundaries) |
| **Bug Type** | TYPE-1 (Invalid Input Accepted) |
| **Severity** | High |
| **Date Discovered** | 2026-03-18 |

## Evidence Chain

### 1. Documentation Evidence (What Should Happen)

**Source**: [Pgvector Vector Data Types](https://github.com/pgvector/pgvector)

Pgvector supports the following dimension limits:
- `vector` type: Maximum **16,000** dimensions (4 bytes per element, float32)
- `halfvec` type: Maximum **16,000** dimensions (2 bytes per element, float16)
- `sparsevec` type: Total dimension up to 1 billion, non-zero elements up to 16,000
- HNSW index: Maximum **2,000** dimensions
- Minimum dimensions: At least **1** dimension required for all types

**Source**: [PostgreSQL Lexical Structure](https://www.postgresql.org/docs/current/sql-syntax-lexical.html)

PostgreSQL uses type modifiers for vector dimensions (e.g., `vector(128)`). The system should validate these modifiers are within acceptable ranges.

### 2. Actual Behavior (What Happened)

Test results from `results/boundary_2025_001/pgvector_boundary_results.json`:

```json
{
  "contract_id": "BND-001",
  "database": "pgvector",
  "test_cases": [
    {
      "name": "Zero dimension",
      "checks": [
        {"name": "Rejected (expected)", "status": false}
      ],
      "verdict": "TYPE-1 (invalid accepted)"
    },
    {
      "name": "Negative dimension",
      "checks": [
        {"name": "Rejected (expected)", "status": false}
      ],
      "verdict": "TYPE-1 (invalid accepted)"
    },
    {
      "name": "Excessive dimension (100000)",
      "checks": [
        {"name": "Rejected (expected)", "status": false}
      ],
      "verdict": "TYPE-1 (invalid accepted)"
    },
    {
      "name": "Vector dimension mismatch",
      "checks": [
        {"name": "Wrong dimension vector rejected", "status": false}
      ],
      "verdict": "TYPE-1 (invalid accepted)"
    }
  ]
}
```

Pgvector accepted ALL invalid dimension values without any validation error.

### 3. Analysis

Pgvector inherits PostgreSQL's minimal input validation approach, which prioritizes flexibility over strict checking. However, for vector operations, this creates serious problems:

1. **dim=0**: Creating a table with `embedding vector(0)` or inserting zero-dimensional vectors should be rejected. Distance calculations on zero-dimensional vectors are mathematically undefined.
2. **dim=-1**: A negative dimension column definition is nonsensical and should trigger a type modifier validation error.
3. **dim=100000**: Far exceeds the documented maximum of 16,000 for storage and 2,000 for HNSW indexing. This could cause silent truncation, excessive memory allocation, or index creation failures later.
4. **Dimension mismatch**: PostgreSQL's type system does not enforce dimension consistency between column definition and inserted values. A column defined as `vector(128)` can accept vectors of any dimension, which breaks the fundamental assumption of vector similarity search.

**Why this matters more for Pgvector**: Unlike dedicated vector databases that have their own validation layers, Pgvector relies heavily on PostgreSQL's type system. The lack of dimension enforcement means that data integrity must be maintained entirely at the application level, which is error-prone.

**Impact**: Silent data corruption, index creation failures for oversized dimensions, meaningless search results from dimension mismatches, potential denial-of-service via extremely large dimension allocations.

**Recommended Fix**: Add dimension validation in pgvector's type input functions. Reject dimensions outside [1, 16000] for the vector type and [1, 2000] for HNSW index creation. Consider adding runtime dimension consistency checks (configurable via GUC) for INSERT operations.

## References

1. [Pgvector GitHub Repository](https://github.com/pgvector/pgvector)
2. [Pgvector Vector Data Types (DeepWiki)](https://deepwiki.com/pgvector/pgvector/3-vector-data-types)
3. [PostgreSQL Lexical Structure](https://www.postgresql.org/docs/current/sql-syntax-lexical.html)
4. [Test Results: pgvector_boundary_results.json](../boundary_2025_001/pgvector_boundary_results.json)
