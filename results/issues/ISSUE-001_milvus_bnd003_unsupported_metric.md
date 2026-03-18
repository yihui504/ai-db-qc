# ISSUE-001: Milvus accepts unsupported metric type 'MANHATTAN' and empty metric string

## Metadata

| Field | Value |
|-------|-------|
| **Bug ID** | ISSUE-001 |
| **Database** | Milvus v2.6.12 |
| **Contract** | BND-003 (Metric Type Validation) |
| **Bug Type** | TYPE-1 (Invalid Input Accepted) |
| **Severity** | Medium |
| **Date Discovered** | 2026-03-18 |

## Evidence Chain

### 1. Documentation Evidence (What Should Happen)

**Source**: [Milvus Metric Types Documentation](https://milvus.io/docs/metric.md)

The official Milvus documentation explicitly lists all supported metric types:

| Metric Type | Applicable Field Types |
|:---|:---|
| `L2` (Euclidean Distance) | `FLOAT_VECTOR`, `FLOAT16_VECTOR`, `BFLOAT16_VECTOR`, `INT8_VECTOR` |
| `IP` (Inner Product) | `FLOAT_VECTOR`, `FLOAT16_VECTOR`, `BFLOAT16_VECTOR`, `INT8_VECTOR`, `SPARSE_FLOAT_VECTOR` |
| `COSINE` (Cosine Similarity) | `FLOAT_VECTOR`, `FLOAT16_VECTOR`, `BFLOAT16_VECTOR`, `INT8_VECTOR` |
| `JACCARD` | `BINARY_VECTOR` |
| `MHJACCARD` (MinHash Jaccard) | `BINARY_VECTOR` |
| `HAMMING` (Hamming Distance) | `BINARY_VECTOR` |
| `BM25` | `SPARSE_FLOAT_VECTOR` (full text search only) |

**MANHATTAN is NOT in the list of supported metric types.**

### 2. Actual Behavior (What Happened)

Test results from `results/boundary_2025_001/milvus_boundary_results.json`:

```json
{
  "contract_id": "BND-003",
  "database": "milvus",
  "test_cases": [
    {
      "name": "Unsupported metric 'MANHATTAN'",
      "checks": [
        {"name": "Rejected (expected)", "status": false},
        {"name": "Good error diagnostics", "status": false, "message": ""}
      ],
      "verdict": "TYPE-1"
    },
    {
      "name": "Empty metric",
      "checks": [
        {"name": "Rejected (expected)", "status": false},
        {"name": "Good error diagnostics", "status": false, "message": ""}
      ],
      "verdict": "TYPE-1"
    }
  ]
}
```

Milvus accepted both 'MANHATTAN' (unsupported metric) and an empty metric string without any error.

### 3. Analysis

When an unsupported metric type is silently accepted during collection creation, the subsequent search behavior becomes undefined. The database may silently fall back to a default metric or produce incorrect similarity calculations without the user's awareness. This is a data integrity risk because:

1. Users may unknowingly use an incorrect distance metric, leading to poor search results.
2. The error only manifests during runtime searches, making it difficult to diagnose.
3. An empty metric string being accepted is particularly dangerous as it provides zero guidance on the distance calculation being used.

**Impact**: Silent data corruption in similarity calculations, difficult to debug production issues.

**Recommended Fix**: Milvus should validate metric types at collection creation time and reject any value not in the documented list of supported metrics with a clear error message listing valid options.

## References

1. [Milvus Metric Types Documentation](https://milvus.io/docs/metric.md)
2. [Test Results: milvus_boundary_results.json](../boundary_2025_001/milvus_boundary_results.json)
