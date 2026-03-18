# Extended Semantic Domain Coverage Report

**Generated**: 2026-03-17T11:25:27.010150
**Adapter**: qdrant
**Embedding**: sentence_transformers
**Domains**: finance, medical

## Cross-Domain Summary

| Domain | MR-01 Violations | MR-03 Violations | MR-04 Violations | Total Tests |
|--------|-----------------|-----------------|-----------------|-------------|
| finance | 0 | 10 | 0 | 25 |
| medical | 0 | 10 | 0 | 25 |

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

### Medical

**MR-01**: {'PASS': 10} (10 tests)

**MR-03**: {'VIOLATION': 10} (10 tests)
  - `medical-hard_negative-0015` | The biopsy results were benign. ← → The biopsy results were malignant.
    rank=2 notes=benign vs malignant
  - `medical-hard_negative-0016` | The biopsy results were benign. ← → The biopsy results were malignant.
    rank=2 notes=benign vs malignant
  - `medical-hard_negative-0017` | The medication is effective for treating hypertens ← → The medication is contraindicated for patients wit
    rank=2 notes=effective vs contraindicated

**MR-04**: {'PASS': 5} (5 tests)

## Key Observations

The extended domain tests above quantify whether the vector database's semantic
retrieval degrades in specialized legal and code domains compared to the baseline
finance/medical domains. MR-03 hard-negative violations in the `code` domain
are especially significant: opposite-meaning API semantics (sync/async, stable/unstable)
should be clearly separated by any competent embedding model.
