# ISSUE-005: Weaviate accepts invalid vector dimensions (dim=0, dim=-1, dim=100000) and dimension mismatch without rejection

## Metadata

| Field | Value |
|-------|-------|
| **Bug ID** | ISSUE-005 |
| **Database** | Weaviate v1.36.5 |
| **Contract** | BND-001 (Vector Dimension Boundaries) |
| **Bug Type** | TYPE-1 (Invalid Input Accepted) |
| **Severity** | High |
| **Date Discovered** | 2026-03-18 |

## Evidence Chain

### 1. Documentation Evidence (What Should Happen)

**Source**: [Weaviate Community Forum - Maximum Vector Length](https://forum.weaviate.io/t/tip-maximum-vector-length-in-weaviate/154)

Official Weaviate team member (jphwang) stated:

> "The looooongest, or maximum, vector length possible in Weaviate is 65535. This is because it's stored as a uint16 datatype."

**Source**: [Weaviate Collection Definition](https://docs.weaviate.io/weaviate/config-refs/collections)

Collection names must follow the regex pattern `/^[A-Z][_0-9A-Za-z]*$/` (first letter uppercase). Vector dimensions must be positive integers within the uint16 range (1-65535).

**Source**: [Weaviate Vector Index Configuration](https://docs.weaviate.io/weaviate/config-refs/indexing/vector-index)

Vector dimensions must be positive integers. A dimension of 0 or negative values is mathematically meaningless for vector operations.

### 2. Actual Behavior (What Happened)

Test results from `results/boundary_2025_001/weaviate_boundary_results.json`:

```json
{
  "contract_id": "BND-001",
  "database": "weaviate",
  "test_cases": [
    {
      "name": "Zero dimension",
      "verdict": "TYPE-1 (invalid accepted)"
    },
    {
      "name": "Negative dimension",
      "verdict": "TYPE-1 (invalid accepted)"
    },
    {
      "name": "Excessive dimension (100000)",
      "verdict": "TYPE-1 (invalid accepted)"
    },
    {
      "name": "Vector dimension mismatch",
      "verdict": "TYPE-1 (invalid accepted)"
    }
  ]
}
```

Weaviate accepted ALL invalid dimension values: dim=0, dim=-1, dim=100000 (exceeds 65535 uint16 limit), and vectors with dimensions that don't match the collection schema.

### 3. Analysis

This is a **high-severity** issue because accepting invalid dimensions creates fundamental data integrity problems:

1. **dim=0**: A zero-dimensional vector is mathematically undefined. Any distance calculation or similarity search on such data will produce meaningless or error-inducing results.
2. **dim=-1**: A negative dimension is nonsensical and indicates a serious validation gap.
3. **dim=100000**: Exceeds the documented uint16 maximum of 65535. Storing vectors with this dimension could cause integer overflow, memory corruption, or silent data truncation.
4. **Dimension mismatch**: Allowing vectors with different dimensions in the same collection undermines the entire premise of vector similarity search, which requires all vectors to have the same dimensionality for distance calculations to be valid.

**Impact**: Silent data corruption, potential memory issues with oversized vectors, meaningless search results, and possible integer overflow with dimensions exceeding 65535.

**Recommended Fix**: Implement strict dimension validation at both collection creation and data insertion time. Reject dimensions outside [1, 65535] with clear error messages. Enforce dimension consistency for all vectors within a collection.

## References

1. [Weaviate Community Forum - Maximum Vector Length](https://forum.weaviate.io/t/tip-maximum-vector-length-in-weaviate/154)
2. [Weaviate Collection Definition](https://docs.weaviate.io/weaviate/config-refs/collections)
3. [Weaviate Vector Index Configuration](https://docs.weaviate.io/weaviate/config-refs/indexing/vector-index)
4. [Test Results: weaviate_boundary_results.json](../boundary_2025_001/weaviate_boundary_results.json)
