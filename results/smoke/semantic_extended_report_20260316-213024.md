# Extended Semantic Domain Coverage Report

**Generated**: 2026-03-16T21:30:27.885033
**Adapter**: mock
**Embedding**: sentence_transformers
**Domains**: legal, code

## Cross-Domain Summary

| Domain | MR-01 Violations | MR-03 Violations | MR-04 Violations | Total Tests |
|--------|-----------------|-----------------|-----------------|-------------|
| legal | 0 | 0 | 0 | 8 |
| code | 0 | 0 | 1 | 8 |

## Domain Detail

### Legal

**MR-01**: {'PASS': 3} (3 tests)

**MR-03**: {'PASS': 3} (3 tests)

**MR-04**: {'PASS': 2} (2 tests)

### Code

**MR-01**: {'PASS': 3} (3 tests)

**MR-03**: {'PASS': 2, 'OBSERVATION': 1} (3 tests)

**MR-04**: {'VIOLATION': 1, 'PASS': 1} (2 tests)
  - `code-negative-0003` | The class inherits from the base interface. ← → The patient's blood pressure is elevated.

## Key Observations

The extended domain tests above quantify whether the vector database's semantic
retrieval degrades in specialized legal and code domains compared to the baseline
finance/medical domains. MR-03 hard-negative violations in the `code` domain
are especially significant: opposite-meaning API semantics (sync/async, stable/unstable)
should be clearly separated by any competent embedding model.
