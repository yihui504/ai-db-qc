# Issue #14: Dimension validation issues with boundary values

## Metadata

| Field | Value |
|-------|-------|
| **Bug ID** | #14 |
| **Database** | Weaviate |
| **Database Version** | v1.27.0 (Docker: cr.weaviate.io/semitechnologies/weaviate:1.27.0) |
| **Adapter** | `adapters/weaviate_adapter.py` |
| **Severity** | Medium |
| **Priority** | P2 |
| **Component** | Validation / Schema |
| **Status** | Confirmed |
| **Reproduced** | Yes |
| **Date Discovered** | 2026-03-18 |

## Summary

Weaviate has issues with dimension validation in vector properties. Either valid boundary values are rejected, or error messages are unclear when invalid values are provided.

## Reproduction Steps

1. Attempt to create classes with various vector dimensions
2. Test boundary values
3. Observe validation behavior and error messages

## Expected Result

Valid dimensions accepted. Invalid dimensions rejected with clear error messages specifying valid range.

## Actual Result

Validation may reject valid values. Error messages may be unclear. Valid range not clearly communicated.

## Root Cause

Dimension validation logic may have incorrect bounds. Error messages may lack range information. Validation may be inconsistent.

## Impact

- Developers struggle with configuration
- Poor error messages hinder troubleshooting

## Workaround

Use common dimensions (e.g., 384, 768, 1024 for embeddings), check Weaviate documentation, experiment with different values.

## Proposed Fix

Update dimension validation to correct bounds, improve error messages with valid range, document valid dimension range, add validation tests.

## Test Case

- **Contract**: BND-001
- **Test ID**: test_bnd001_dimension_boundaries
- **Evidence**: `results/boundary_2025_001/weaviate_boundary_results.json`

## Related Issues

- Cross-database pattern: #2 (Milvus), #7 (Qdrant), #14 (Weaviate), #19 (Pgvector)

## Verification

- [x] Bug successfully reproduced
- [x] Root cause identified
- [ ] Fix implemented
- [ ] Fix tested
- [ ] Fix deployed to production

## References

- Original Bug Report: `ISSUES.json` entry #14
- Bug Mining Evidence: `BUG_EVIDENCE_CHAIN_REPORT.md`
- Reproduction Results: `reproduction_results/bug_reproduction_results.json`
