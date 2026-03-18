# Extended Semantic Domain Coverage Report

**Generated**: 2026-03-17T08:35:19.836995
**Adapter**: weaviate
**Embedding**: hash-fallback
**Domains**: finance, medical, legal, code

## Cross-Domain Summary

| Domain | MR-01 Violations | MR-03 Violations | MR-04 Violations | Total Tests |
|--------|-----------------|-----------------|-----------------|-------------|
| finance | 10 | 0 | 0 | 25 |
| medical | 10 | 2 | 0 | 25 |
| legal | 8 | 0 | 0 | 25 |
| code | 10 | 0 | 0 | 25 |

## Domain Detail

### Finance

**MR-01**: {'VIOLATION': 10} (10 tests)
  - `finance-positive-0000` | The company reported strong quarterly earnings gro ← → The firm achieved significant profit increases thi
  - `finance-positive-0001` | The company reported strong quarterly earnings gro ← → The firm achieved significant profit increases thi
  - `finance-positive-0002` | The stock price fell sharply after the earnings re ← → Share prices dropped significantly following the e

**MR-03**: {'OBSERVATION': 5, 'PASS': 5} (10 tests)

**MR-04**: {'OBSERVATION': 1, 'PASS': 4} (5 tests)

### Medical

**MR-01**: {'VIOLATION': 10} (10 tests)
  - `medical-positive-0000` | The drug inhibits tumor cell proliferation. ← → The medication prevents cancer cells from dividing
  - `medical-positive-0001` | The patient is recovering well after surgery. ← → The patient shows good post-operative progress.
  - `medical-positive-0002` | The patient is recovering well after surgery. ← → The patient shows good post-operative progress.

**MR-03**: {'OBSERVATION': 7, 'VIOLATION': 2, 'PASS': 1} (10 tests)
  - `medical-hard_negative-0017` | The medication is effective for treating hypertens ← → The medication is contraindicated for patients wit
    rank=2 notes=effective vs contraindicated
  - `medical-hard_negative-0023` | The medication is effective for treating hypertens ← → The medication is contraindicated for patients wit
    rank=2 notes=effective vs contraindicated

**MR-04**: {'PASS': 5} (5 tests)

### Legal

**MR-01**: {'VIOLATION': 8, 'PASS': 2} (10 tests)
  - `legal-positive-0000` | The defendant was found guilty of the charges. ← → The court convicted the accused on all counts.
  - `legal-positive-0001` | The defendant was found guilty of the charges. ← → The court convicted the accused on all counts.
  - `legal-positive-0002` | The court issued an injunction to halt the proceed ← → A court order was granted to stop the action.

**MR-03**: {'PASS': 6, 'OBSERVATION': 4} (10 tests)

**MR-04**: {'OBSERVATION': 5} (5 tests)

### Code

**MR-01**: {'VIOLATION': 10} (10 tests)
  - `code-positive-0000` | The function returns None if the input is invalid. ← → The method returns null when the provided argument
  - `code-positive-0001` | The function returns None if the input is invalid. ← → The method returns null when the provided argument
  - `code-positive-0002` | The variable is declared as a constant and cannot  ← → The identifier is defined as immutable and its val

**MR-03**: {'PASS': 6, 'OBSERVATION': 4} (10 tests)

**MR-04**: {'PASS': 1, 'OBSERVATION': 4} (5 tests)

## Key Observations

The extended domain tests above quantify whether the vector database's semantic
retrieval degrades in specialized legal and code domains compared to the baseline
finance/medical domains. MR-03 hard-negative violations in the `code` domain
are especially significant: opposite-meaning API semantics (sync/async, stable/unstable)
should be clearly separated by any competent embedding model.
