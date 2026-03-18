# Issue #15: Limit validation insufficient - unclear error messages

## Metadata

| Field | Value |
|-------|-------|
| **Bug ID** | #15 |
| **Database** | Weaviate |
| **Database Version** | v1.27.0 (Docker: cr.weaviate.io/semitechnologies/weaviate:1.27.0) |
| **Adapter** | `adapters/weaviate_adapter.py` |
| **Severity** | Medium |
| **Priority** | P2 |
| **Component** | Validation / Query |
| **Status** | Confirmed |
| **Reproduced** | Yes |
| **Date Discovered** | 2026-03-18 |

## Summary

Weaviate does not properly validate the limit parameter in search queries, or provides unclear error messages when validation fails.

## Reproduction Steps

1. Create a class with objects
2. Execute searches with invalid limit values (0, -1, very large)
3. Observe behavior and error messages

## Expected Result

Invalid limits rejected with clear error messages. System remains stable. Error messages specify valid range.

## Actual Result

Invalid values may cause issues or unclear errors. Validation may be insufficient.

## Root Cause

Missing or insufficient limit validation. Error messages may not include valid range. May not check for zero or negative values.

## Impact

- Invalid input may cause issues
- Poor error messages

## Workaround

Validate limit on client side, use reasonable default values, add client-side error handling.

## Proposed Fix

Add strict input validation, improve error messages with valid range, document valid limit range, add validation tests.

## Test Case

- **Contract**: BND-002
- **Test ID**: test_bnd002_topk_boundaries
- **Evidence**: `results/boundary_2025_001/weaviate_boundary_results.json`

## Related Issues

- Cross-database pattern: #4 (Milvus), #8 (Qdrant), #15 (Weaviate), #20 (Pgvector)

## Verification

- [x] Bug successfully reproduced
- [x] Root cause identified
- [ ] Fix implemented
- [ ] Fix tested
- [ ] Fix deployed to production

## References

- Original Bug Report: `ISSUES.json` entry #15
- Bug Mining Evidence: `BUG_EVIDENCE_CHAIN_REPORT.md`
- Reproduction Results: `reproduction_results/bug_reproduction_results.json`
