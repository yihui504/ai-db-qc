# Extended Semantic Domain Coverage Report

**Generated**: 2026-03-17T11:25:40.476719
**Adapter**: weaviate
**Embedding**: sentence_transformers
**Domains**: finance

## Cross-Domain Summary

| Domain | MR-01 Violations | MR-03 Violations | MR-04 Violations | Total Tests |
|--------|-----------------|-----------------|-----------------|-------------|
| finance | 0 | 10 | 0 | 25 |

## Domain Detail

### Finance

**MR-01**: {'PASS': 10} (10 tests)

**MR-03**: {'VIOLATION': 10} (10 tests)
  - `finance-hard_negative-0015` | The merger was approved by regulators. ← → The merger was blocked by regulators.
    rank=2 notes=approved vs blocked
  - `finance-hard_negative-0016` | The credit rating was upgraded to AA. ← → The credit rating was downgraded to BB.
    rank=2 notes=upgrade vs downgrade
  - `finance-hard_negative-0017` | The credit rating was upgraded to AA. ← → The credit rating was downgraded to BB.
    rank=2 notes=upgrade vs downgrade

**MR-04**: {'PASS': 5} (5 tests)

## Key Observations

The extended domain tests above quantify whether the vector database's semantic
retrieval degrades in specialized legal and code domains compared to the baseline
finance/medical domains. MR-03 hard-negative violations in the `code` domain
are especially significant: opposite-meaning API semantics (sync/async, stable/unstable)
should be clearly separated by any competent embedding model.
