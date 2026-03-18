# Extended Semantic Domain Coverage Report

**Generated**: 2026-03-17T07:56:34.469750
**Adapter**: milvus
**Embedding**: hash-fallback
**Domains**: finance

## Cross-Domain Summary

| Domain | MR-01 Violations | MR-03 Violations | MR-04 Violations | Total Tests |
|--------|-----------------|-----------------|-----------------|-------------|
| finance | 10 | 0 | 0 | 25 |

## Domain Detail

### Finance

**MR-01**: {'VIOLATION': 10} (10 tests)
  - `finance-positive-0000` | The company reported strong quarterly earnings gro ← → The firm achieved significant profit increases thi
  - `finance-positive-0001` | The company reported strong quarterly earnings gro ← → The firm achieved significant profit increases thi
  - `finance-positive-0002` | The stock price fell sharply after the earnings re ← → Share prices dropped significantly following the e

**MR-03**: {'OBSERVATION': 5, 'PASS': 5} (10 tests)

**MR-04**: {'OBSERVATION': 1, 'PASS': 4} (5 tests)

## Key Observations

The extended domain tests above quantify whether the vector database's semantic
retrieval degrades in specialized legal and code domains compared to the baseline
finance/medical domains. MR-03 hard-negative violations in the `code` domain
are especially significant: opposite-meaning API semantics (sync/async, stable/unstable)
should be clearly separated by any competent embedding model.
