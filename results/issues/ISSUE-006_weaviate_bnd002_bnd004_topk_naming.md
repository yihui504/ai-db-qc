# ISSUE-006: Weaviate search error with top_k=0, accepts negative top_k, and lacks collection name uniqueness enforcement

## Metadata

| Field | Value |
|-------|-------|
| **Bug ID** | ISSUE-006 |
| **Database** | Weaviate v1.36.5 |
| **Contract** | BND-002 (Top-K Boundaries), BND-004 (Collection Name Boundaries) |
| **Bug Type** | TYPE-3 (top_k error), TYPE-1 (negative top_k, naming) |
| **Severity** | Medium |
| **Date Discovered** | 2026-03-18 |

## Evidence Chain

### 1. Documentation Evidence

**BND-002 - Top-K/Limit Parameter**:

**Source**: [Weaviate GraphQL Additional Operators](https://docs.weaviate.io/weaviate/api/graphql/additional-operators)

The `limit` parameter restricts the number of results returned. It can be set to any positive integer, subject to the `QUERY_MAXIMUM_RESULTS` system configuration. The documentation does not explicitly address limit=0 or negative values.

**BND-004 - Collection Naming**:

**Source**: [Weaviate Collection Definition](https://docs.weaviate.io/weaviate/config-refs/collections)

Collection names must:
- Start with an uppercase letter: `/^[A-Z][_0-9A-Za-z]*$/`
- Reserved property names include: `_additional`, `id`, `_id`
- No explicit collection-level reserved names are documented

### 2. Actual Behavior

**BND-002 - Top-K Test Results**:
```json
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
```

**BND-004 - Collection Naming Test Results**:
```json
{
  "name": "system",
  "checks": [
    {"name": "Rejected (expected)", "status": false}
  ],
  "verdict": "TYPE-1"
},
{
  "name": "Duplicate collection name",
  "checks": [
    {"name": "Duplicate name rejected", "status": false}
  ],
  "verdict": "TYPE-1"
}
```

### 3. Analysis

**top_k=0 Error**: While the search "succeeded" (returned true), an internal exception occurred: `"invalid literal for int() with base 10: 'empty'"`. This suggests Weaviate returns a sentinel value 'empty' instead of proper results when limit=0, and downstream code attempts to parse this as an integer. This is a TYPE-3 bug because it causes an unhandled exception.

**Negative top_k**: Negative limit values were accepted without rejection. A negative limit has no meaningful semantics and should be rejected with a validation error.

**Collection name 'system'**: "System" (capital S) conforms to Weaviate's naming rules. The test used lowercase "system" which should be rejected since the regex requires uppercase first letter. However, the test shows it was accepted, indicating the naming validation is not strictly enforced.

**Duplicate collection names**: Lack of uniqueness enforcement is a data integrity concern. Two collections with the same name could lead to ambiguous API calls and data retrieval confusion.

**Impact**: Unhandled exceptions in production, potential data ambiguity with duplicate names.

**Recommended Fix**: (1) Handle limit=0 gracefully - either return an empty array or a validation error. (2) Reject negative limit values. (3) Enforce strict collection name uniqueness. (4) Strictly enforce the naming regex `/^[A-Z][_0-9A-Za-z]*$/`.

## References

1. [Weaviate GraphQL Additional Operators](https://docs.weaviate.io/weaviate/api/graphql/additional-operators)
2. [Weaviate Collection Definition](https://docs.weaviate.io/weaviate/config-refs/collections)
3. [Test Results: weaviate_boundary_results.json](../boundary_2025_001/weaviate_boundary_results.json)
