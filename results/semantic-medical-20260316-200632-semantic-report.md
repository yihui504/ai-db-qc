# Semantic Metamorphic Testing Campaign Report

**Run ID**: semantic-medical-20260316-200632
**Domain**: medical
**Timestamp**: 2026-03-16T20:07:02.396123

## Dataset Statistics

- **positive**: 8 pairs
- **negative**: 5 pairs
- **hard_negative**: 8 pairs
- **boundary**: 5 pairs

## Campaign Results by Metamorphic Relation

### MR-01

- **PASS**: 8

### MR-03

- **VIOLATION**: 8

**Violations (8):**

- Pair `medical-hard_negative-0013`: Hard negative appeared at rank 2 (should be far)
  - text_a: _The medication is effective for treating hypertension._
  - text_b: _The medication is contraindicated for patients with hypertension._
- Pair `medical-hard_negative-0014`: Hard negative appeared at rank 2 (should be far)
  - text_a: _The biopsy results were benign._
  - text_b: _The biopsy results were malignant._
- Pair `medical-hard_negative-0015`: Hard negative appeared at rank 2 (should be far)
  - text_a: _The biopsy results were benign._
  - text_b: _The biopsy results were malignant._
- Pair `medical-hard_negative-0016`: Hard negative appeared at rank 2 (should be far)
  - text_a: _The medication is effective for treating hypertension._
  - text_b: _The medication is contraindicated for patients with hypertension._
- Pair `medical-hard_negative-0017`: Hard negative appeared at rank 2 (should be far)
  - text_a: _The biopsy results were benign._
  - text_b: _The biopsy results were malignant._

### MR-04

- **PASS**: 5

## Summary

| Metric | Value |
|--------|-------|
| Total tests | 21 |
| Violations | 8 |
| Passes | 13 |
| Violation rate | 38.1% |

## Key Findings

Found **8 metamorphic violations** across 21 tests.
These indicate semantic correctness issues in the vector database's retrieval.