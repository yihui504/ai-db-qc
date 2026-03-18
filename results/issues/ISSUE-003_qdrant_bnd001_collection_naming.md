# ISSUE-003: Qdrant accepts collection names with spaces and reserved name 'system' without proper validation

## Metadata

| Field | Value |
|-------|-------|
| **Bug ID** | ISSUE-003 |
| **Database** | Qdrant v1.17.0 |
| **Contract** | BND-004 (Collection Name Boundaries) |
| **Bug Type** | TYPE-1 (Invalid Input Accepted) / TYPE-2 (Poor Diagnostics) |
| **Severity** | Medium |
| **Date Discovered** | 2026-03-18 |

## Evidence Chain

### 1. Documentation Evidence (What Should Happen)

**Source**: [Qdrant Collections Documentation](https://qdrant.tech/documentation/concepts/collections/)

Collection naming rules:
- Must be valid UTF-8 string
- Maximum 255 bytes length
- Must be URL path compatible (collection names are used in REST API endpoints like `/collections/{collection_name}`)
- No special reserved word restrictions documented

**Source**: [Qdrant Create Collection API](https://api.qdrant.tech/api-reference/collections/create-collection)

Collection names are path parameters in the REST API: `/collections/{collection_name}`. URL path parameters have strict character requirements - spaces and certain special characters are technically valid in URLs but can cause encoding issues.

### 2. Actual Behavior (What Happened)

Test results from `results/boundary_2025_001/qdrant_boundary_results.json`:

```json
{
  "contract_id": "BND-004",
  "database": "qdrant",
  "test_cases": [
    {
      "name": "my collection",
      "checks": [
        {"name": "Rejected (expected)", "status": false},
        {"name": "Good error diagnostics", "status": false, "message": ""}
      ],
      "verdict": "TYPE-1"
    },
    {
      "name": "system",
      "checks": [
        {"name": "Rejected (expected)", "status": false},
        {"name": "Good error diagnostics", "status": false, "message": ""}
      ],
      "verdict": "TYPE-1"
    },
    {
      "name": "Duplicate collection name",
      "checks": [
        {"name": "Duplicate name rejected", "status": false},
        {"name": "Good error diagnostics", "status": false, "message": ""}
      ],
      "verdict": "TYPE-1"
    }
  ]
}
```

Qdrant accepted collection names with spaces ("my collection"), the reserved name "system", and did not properly reject duplicate collection names.

### 3. Analysis

**Collection name with spaces**: While technically allowed as UTF-8, using collection names with spaces creates URL encoding complications. The API endpoint `/collections/my collection` requires the space to be encoded as `%20` or `+`, which can lead to client-side bugs, logging issues, and API gateway misconfigurations.

**Reserved name 'system'**: The name "system" is commonly used as a reserved keyword or namespace in many systems. While Qdrant's documentation doesn't explicitly reserve it, accepting it without warning could cause conflicts with internal system operations, monitoring tools, or future Qdrant features.

**Duplicate collection names**: If Qdrant does not properly reject duplicate names, this could lead to data being split across identically-named collections or unexpected overwrites, both of which are serious data integrity issues.

**Impact**: API compatibility issues with spaces in names, potential naming conflicts with reserved words, data integrity risk with duplicate names.

**Recommended Fix**: Add explicit validation for collection names that rejects or at least warns about: (1) names containing spaces or URL-unsafe characters, (2) common reserved names like 'system', 'default', 'qdrant', and (3) enforce strict uniqueness with clear error messages on duplicates.

## References

1. [Qdrant Collections Documentation](https://qdrant.tech/documentation/concepts/collections/)
2. [Qdrant Create Collection API Reference](https://api.qdrant.tech/api-reference/collections/create-collection)
3. [Test Results: qdrant_boundary_results.json](../boundary_2025_001/qdrant_boundary_results.json)
