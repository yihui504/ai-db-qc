# Issue #17: Class name validation insufficient checks

## Metadata

| Field | Value |
|-------|-------|
| **Bug ID** | #17 |
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

Weaviate accepts class names that should be reserved or invalid, including system names or names with invalid characters.

## Reproduction Steps

1. Attempt to create classes with various names
2. Test reserved names, special characters
3. Observe validation behavior

## Expected Result

Reserved names rejected. Invalid characters rejected. Clear error messages with naming rules.

## Actual Result

Some invalid names may be accepted. Validation may be insufficient.

## Root Cause

No list of reserved system names. May only check basic validity. Does not prevent conflicts.

## Impact

- May conflict with system classes
- Potential for confusion
- Unclear naming rules

## Workaround

Use a naming convention, avoid obviously reserved names, check existing classes before creating.

## Proposed Fix

Implement strict name validation, document naming rules clearly, add validation tests, provide clear error messages.

## Test Case

- **Contract**: BND-004
- **Test ID**: test_bnd004_collection_name_validation
- **Evidence**: `results/boundary_2025_001/weaviate_boundary_results.json`

## Related Issues

- Cross-database pattern: #5 (Milvus), #10 (Qdrant), #17 (Weaviate), #22 (Pgvector)

## Verification

- [x] Bug successfully reproduced
- [x] Root cause identified
- [ ] Fix implemented
- [ ] Fix tested
- [ ] Fix deployed to production

## References

- Original Bug Report: `ISSUES.json` entry #17
- Bug Mining Evidence: `BUG_EVIDENCE_CHAIN_REPORT.md`
- Reproduction Results: `reproduction_results/bug_reproduction_results.json`
