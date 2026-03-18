# Extended Semantic Domain Coverage Report

**Generated**: 2026-03-17T07:51:51.923542
**Adapter**: weaviate
**Embedding**: hash-fallback
**Domains**: finance, medical

## Cross-Domain Summary

| Domain | MR-01 Violations | MR-03 Violations | MR-04 Violations | Total Tests |
|--------|-----------------|-----------------|-----------------|-------------|
| finance | ERROR | ERROR | ERROR | — |
| medical | ERROR | ERROR | ERROR | — |

## Domain Detail

### Finance

> ERROR: collection setup failed

### Medical

> ERROR: collection setup failed

## Key Observations

The extended domain tests above quantify whether the vector database's semantic
retrieval degrades in specialized legal and code domains compared to the baseline
finance/medical domains. MR-03 hard-negative violations in the `code` domain
are especially significant: opposite-meaning API semantics (sync/async, stable/unstable)
should be clearly separated by any competent embedding model.
