# Issue #16: Distance metric validation accepts invalid metrics

## Metadata

| Field | Value |
|-------|-------|
| **Bug ID** | #16 |
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

Weaviate accepts invalid distance metric types when creating vector properties without proper validation.

## Reproduction Steps

1. Attempt to create a class with an invalid distance metric
2. Observe validation behavior

## Expected Result

Invalid metrics rejected with clear error messages. Only supported metrics accepted.

## Actual Result

Invalid metrics may be accepted without clear validation error.

## Root Cause

Metric type validation may be missing. Whitelist not enforced.

## Impact

- Invalid configurations cause issues
- No immediate feedback

## Workaround

Use only well-documented metrics (cosine, dot, l2-squared, hamming, manhattan), check Weaviate documentation, validate on client side.

## Proposed Fix

Implement strict metric validation, document all supported metrics, add validation tests, improve error messages.

## Test Case

- **Contract**: BND-003
- **Test ID**: test_bnd003_metric_validation
- **Evidence**: `results/boundary_2025_001/weaviate_boundary_results.json`

## Related Issues

- Cross-database pattern: #4 (Milvus), #9 (Qdrant), #16 (Weaviate), #21 (Pgvector)

## Verification

- [x] Bug successfully reproduced
- [x] Root cause identified
- [ ] Fix implemented
- [ ] Fix tested
- [ ] Fix deployed to production

## References

- Original Bug Report: `ISSUES.json` entry #16
- Bug Mining Evidence: `BUG_EVIDENCE_CHAIN_REPORT.md`
- Reproduction Results: `reproduction_results/bug_reproduction_results.json`
