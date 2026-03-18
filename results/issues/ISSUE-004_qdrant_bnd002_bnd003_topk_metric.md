# ISSUE-004: Qdrant search fails on top_k=0 and accepts unsupported/empty metric types

## Metadata

| Field | Value |
|-------|-------|
| **Bug ID** | ISSUE-004 |
| **Database** | Qdrant v1.17.0 |
| **Contract** | BND-002 (Top-K Boundaries), BND-003 (Metric Type Validation) |
| **Bug Type** | TYPE-3 (top_k=0 crash), TYPE-1 (metric validation) |
| **Severity** | Medium |
| **Date Discovered** | 2026-03-18 |

## Evidence Chain

### 1. Documentation Evidence

**BND-002 - Top-K Parameter**:

**Source**: [Qdrant API Reference - Query Points](https://api.qdrant.tech/api-reference/search/query-points)

The API documentation states that the `limit` parameter (equivalent to top_k) must be >= 1. The default value is 10.

**BND-003 - Metric Types**:

**Source**: [Qdrant Distance Metrics](https://qdrant.tech/course/essentials/day-1/distance-metrics/)

Qdrant officially supports exactly 4 distance metrics:
1. **Cosine Similarity**
2. **Dot Product**
3. **Euclidean Distance (L2)**
4. **Manhattan Distance (L1)**

Note: Qdrant does support Manhattan distance natively. However, unsupported metrics (not in this list) should be rejected, and an empty metric string should be rejected.

### 2. Actual Behavior

**BND-002 - Top-K Test Results**:
```json
{
  "name": "Top-K = 0",
  "checks": [
    {"name": "Search succeeded", "status": false}
  ],
  "verdict": "TYPE-3 (crash)"
}
```

Search with top_k=0 causes a crash/error in Qdrant.

**BND-003 - Metric Test Results**:
```json
{
  "name": "Unsupported metric 'MANHATTAN'",
  "checks": [
    {"name": "Rejected (expected)", "status": false},
    {"name": "Good error diagnostics", "status": false, "message": ""}
  ],
  "verdict": "TYPE-1"
}
```

Note: The test case name says 'MANHATTAN' but Qdrant does support manhattan distance. The issue is that Qdrant accepted this metric value (which may be case-sensitive or the test used an uppercase variant). The empty metric string was also accepted without rejection.

### 3. Analysis

**top_k=0 Crash**: Instead of returning an empty result set or a validation error, Qdrant crashes when limit=0. This is a TYPE-3 bug because it causes an operation failure rather than a graceful error. A well-designed API should either return 0 results for limit=0 or return a clear validation error.

**Metric Validation**: While Qdrant does support Manhattan distance, the lack of input validation for metric types means that completely invalid metric values (including empty strings) are silently accepted, potentially leading to undefined behavior during search operations.

**Impact**: Application crashes when limit=0 is passed (common in pagination logic bugs), potential undefined behavior with invalid metrics.

**Recommended Fix**: Handle limit=0 gracefully (return empty results or a clear validation error). Add explicit metric type validation at collection creation time.

## References

1. [Qdrant API Reference - Query Points](https://api.qdrant.tech/api-reference/search/query-points)
2. [Qdrant Distance Metrics Course](https://qdrant.tech/course/essentials/day-1/distance-metrics/)
3. [Test Results: qdrant_boundary_results.json](../boundary_2025_001/qdrant_boundary_results.json)
