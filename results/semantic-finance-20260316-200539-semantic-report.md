# Semantic Metamorphic Testing Campaign Report

**Run ID**: semantic-finance-20260316-200539
**Domain**: finance
**Timestamp**: 2026-03-16T20:06:09.544015

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

- Pair `finance-hard_negative-0013`: Hard negative appeared at rank 2 (should be far)
  - text_a: _The bond yield rose to 5%._
  - text_b: _The bond yield fell to 5%._
- Pair `finance-hard_negative-0014`: Hard negative appeared at rank 2 (should be far)
  - text_a: _The merger was approved by regulators._
  - text_b: _The merger was blocked by regulators._
- Pair `finance-hard_negative-0015`: Hard negative appeared at rank 2 (should be far)
  - text_a: _The merger was approved by regulators._
  - text_b: _The merger was blocked by regulators._
- Pair `finance-hard_negative-0016`: Hard negative appeared at rank 2 (should be far)
  - text_a: _The credit rating was upgraded to AA._
  - text_b: _The credit rating was downgraded to BB._
- Pair `finance-hard_negative-0017`: Hard negative appeared at rank 2 (should be far)
  - text_a: _The credit rating was upgraded to AA._
  - text_b: _The credit rating was downgraded to BB._

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