# Bug Issue Files Summary

**Generated**: 2026-03-18  
**Campaign**: AGGRESSIVE_BUG_MINING_2025_001  
**Total Issues Generated**: 8

## Issues with Complete Evidence Chains

| Issue ID | Database | Contract | Bug Type | Severity | File |
|----------|----------|----------|----------|----------|------|
| ISSUE-001 | Milvus v2.6.12 | BND-003 | TYPE-1 | Medium | [ISSUE-001_milvus_bnd003_unsupported_metric.md](ISSUE-001_milvus_bnd003_unsupported_metric.md) |
| ISSUE-002 | Qdrant v1.17.0 | STR-001, STR-002 | TYPE-3 | Critical | [ISSUE-002_qdrant_str001_str002_502_crash.md](ISSUE-002_qdrant_str001_str002_502_crash.md) |
| ISSUE-003 | Qdrant v1.17.0 | BND-004 | TYPE-1/TYPE-2 | Medium | [ISSUE-003_qdrant_bnd001_collection_naming.md](ISSUE-003_qdrant_bnd001_collection_naming.md) |
| ISSUE-004 | Qdrant v1.17.0 | BND-002, BND-003 | TYPE-3/TYPE-1 | Medium | [ISSUE-004_qdrant_bnd002_bnd003_topk_metric.md](ISSUE-004_qdrant_bnd002_bnd003_topk_metric.md) |
| ISSUE-005 | Weaviate v1.36.5 | BND-001 | TYPE-1 | High | [ISSUE-005_weaviate_bnd001_invalid_dimensions.md](ISSUE-005_weaviate_bnd001_invalid_dimensions.md) |
| ISSUE-006 | Weaviate v1.36.5 | BND-002, BND-004 | TYPE-3/TYPE-1 | Medium | [ISSUE-006_weaviate_bnd002_bnd004_topk_naming.md](ISSUE-006_weaviate_bnd002_bnd004_topk_naming.md) |
| ISSUE-007 | Pgvector v0.8.2 | BND-001 | TYPE-1 | High | [ISSUE-007_pgvector_bnd001_invalid_dimensions.md](ISSUE-007_pgvector_bnd001_invalid_dimensions.md) |
| ISSUE-008 | Pgvector v0.8.2 | BND-002 | TYPE-3/TYPE-1 | High | [ISSUE-008_pgvector_bnd002_topk_error.md](ISSUE-008_pgvector_bnd002_topk_error.md) |

## Bugs Without Complete Evidence Chains (Not Filed as Issues)

The following bugs from the original report were NOT filed as individual issues because the documentation evidence either confirms the behavior is expected or the evidence is insufficient:

### Milvus (4 bugs not filed)

| Contract | Reason Not Filed |
|----------|-----------------|
| BND-001 (dim=1 rejected) | **Not a bug** - PyMilvus API docs explicitly state "dim should be an integer greater than 1" (min=2). Rejecting dim=1 is correct behavior per documentation. |
| BND-002 (top_k=0 rejected) | **Likely expected** - API docs state limit is a "positive integer". The poor diagnostics are a usability issue but not a functional bug. |
| BND-004 (collection naming) | **Insufficient evidence** - Documentation shows 'system' is a valid name per naming rules. Duplicate name issue needs further investigation. |
| SCH-006 (schema atomicity) | **By design** - Milvus explicitly does not guarantee ACID compliance. Per GitHub Discussion #16651, Milvus prioritizes performance over transactional guarantees. |

### SCH-006 (Schema Atomicity) - All 4 Databases

Schema operation atomicity was flagged as LIKELY_BUG for all 4 databases. However, this is a systemic design limitation rather than a specific bug:
- **Milvus**: Explicitly does not guarantee ACID (confirmed by maintainers)
- **Qdrant/Weaviate/Pgvector**: No documentation about schema transaction guarantees

This is a cross-database architectural concern that would be better addressed as a feature request across all projects rather than individual bug reports.

### Milvus/Qdrant BND-003 - Metric Case Sensitivity

The original report mentioned case-sensitive metric names (e.g., "l2" rejected but "L2" accepted). Upon reviewing the raw test data, both lowercase and uppercase variants were actually PASS for Milvus and Qdrant. This was a reporting discrepancy in BUG_MINING_REPORT_v2.md and does not represent a confirmed bug.

### Weaviate/Pgvector BND-003 - MANHATTAN Metric

The original report stated MANHATTAN was an unsupported metric. Research confirms that both Weaviate and Pgvector **officially support** Manhattan distance:
- **Weaviate**: Listed in [Distance Metrics docs](https://docs.weaviate.io/weaviate/config-refs/distances) as `manhattan`
- **Pgvector**: Supported via `<+>` operator and `l1_distance()` function

Accepting MANHATTAN is correct behavior, NOT a bug.

## Evidence Chain Structure

Each issue file follows the three-part evidence chain structure:

1. **Documentation Evidence** - Official documentation quotes and URLs establishing the expected behavior
2. **Actual Behavior** - Raw test results from JSON files showing the observed behavior
3. **Analysis** - Impact assessment, root cause analysis, and recommended fix

## Severity Distribution

| Severity | Count | Issues |
|----------|-------|--------|
| Critical | 1 | ISSUE-002 (Qdrant 502 crash) |
| High | 3 | ISSUE-005, ISSUE-007, ISSUE-008 |
| Medium | 4 | ISSUE-001, ISSUE-003, ISSUE-004, ISSUE-006 |
