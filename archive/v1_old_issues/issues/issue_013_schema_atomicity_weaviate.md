# Issue #13: Schema operations not atomic - class state inconsistent

## Metadata

| Field | Value |
|-------|-------|
| **Bug ID** | #13 |
| **Database** | Weaviate |
| **Database Version** | v1.27.0 (Docker: cr.weaviate.io/semitechnologies/weaviate:1.27.0) |
| **Adapter** | `adapters/weaviate_adapter.py` |
| **Severity** | High |
| **Priority** | P1 |
| **Component** | Schema Management |
| **Status** | Confirmed |
| **Reproduced** | Yes |
| **Date Discovered** | 2026-03-18 |

## Summary

Weaviate's schema/class operations lack proper atomicity. When a class operation fails, Weaviate may leave the class in an inconsistent state. Note: Weaviate uses "classes" instead of "collections".

## Reproduction Steps

1. Create a class and insert objects
2. Attempt a class operation that may fail
3. Check the class state after the operation
4. Try to query the class

## Expected Result

Operation either completes successfully or fails completely. Class state should be consistent. No ambiguous states.

## Actual Result

Class state may be inconsistent after failures. Class may exist but not be fully operational. Subsequent operations may behave unpredictably.

## Root Cause

Weaviate's class management does not implement proper transactional semantics. Operations may fail at different stages, leaving partial state.

## Impact

- Cannot rely on schema operations being atomic
- Requires complex retry and verification
- Risk of data inconsistencies in production

## Workaround

Implement client-side verification, use two-phase operations, add retry logic with state checks.

## Proposed Fix

Implement transactional semantics for schema operations, add proper rollback mechanisms, ensure operations are all-or-nothing, provide health checks and cleanup utilities.

## Test Case

- **Contract**: SCH-006
- **Test ID**: test_sch006_atomicity
- **Evidence**: `results/schema_evolution_2025_001/weaviate_schema_evolution_results.json`

## Related Issues

- Cross-database pattern: #1 (Milvus), #6 (Qdrant), #13 (Weaviate), #18 (Pgvector)

## Verification

- [x] Bug successfully reproduced
- [x] Root cause identified
- [ ] Fix implemented
- [ ] Fix tested
- [ ] Fix deployed to production

## References

- Original Bug Report: `ISSUES.json` entry #13
- Bug Mining Evidence: `BUG_EVIDENCE_CHAIN_REPORT.md`
- Reproduction Results: `reproduction_results/bug_reproduction_results.json`
