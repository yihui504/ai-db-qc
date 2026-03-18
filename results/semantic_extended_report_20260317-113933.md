# Extended Semantic Domain Coverage Report

**Generated**: 2026-03-17T11:39:54.095563
**Adapter**: pgvector
**Embedding**: sentence_transformers
**Domains**: code, legal

## Cross-Domain Summary

| Domain | MR-01 Violations | MR-03 Violations | MR-04 Violations | Total Tests |
|--------|-----------------|-----------------|-----------------|-------------|
| code | 1 | 10 | 0 | 25 |
| legal | 2 | 10 | 0 | 25 |

## Domain Detail

### Code

**MR-01**: {'PASS': 9, 'VIOLATION': 1} (10 tests)
  - `code-positive-0002` | The variable is declared as a constant and cannot  ← → The identifier is defined as immutable and its val

**MR-03**: {'VIOLATION': 10} (10 tests)
  - `code-hard_negative-0015` | The loop terminates when the condition is True. ← → The loop terminates when the condition is False.
    rank=2 notes=True vs False termination
  - `code-hard_negative-0016` | The cache stores the result of the computation. ← → The cache invalidates and discards the result of t
    rank=2 notes=stores vs invalidates
  - `code-hard_negative-0017` | The cache stores the result of the computation. ← → The cache invalidates and discards the result of t
    rank=2 notes=stores vs invalidates

**MR-04**: {'PASS': 5} (5 tests)

### Legal

**MR-01**: {'PASS': 8, 'VIOLATION': 2} (10 tests)
  - `legal-positive-0007` | The statute of limitations has expired. ← → The legal time limit for filing the claim has pass
  - `legal-positive-0009` | The statute of limitations has expired. ← → The legal time limit for filing the claim has pass

**MR-03**: {'VIOLATION': 10} (10 tests)
  - `legal-hard_negative-0015` | The contract is enforceable under current law. ← → The contract is unenforceable under current law.
    rank=2 notes=enforceable vs unenforceable
  - `legal-hard_negative-0016` | The injunction was granted by the judge. ← → The injunction was denied by the judge.
    rank=2 notes=granted vs denied
  - `legal-hard_negative-0017` | The injunction was granted by the judge. ← → The injunction was denied by the judge.
    rank=2 notes=granted vs denied

**MR-04**: {'PASS': 5} (5 tests)

## Key Observations

The extended domain tests above quantify whether the vector database's semantic
retrieval degrades in specialized legal and code domains compared to the baseline
finance/medical domains. MR-03 hard-negative violations in the `code` domain
are especially significant: opposite-meaning API semantics (sync/async, stable/unstable)
should be clearly separated by any competent embedding model.
