# Semantic Metamorphic Testing Campaign Report

**Run ID**: semantic-finance-20260316-195138
**Domain**: finance
**Timestamp**: 2026-03-16T19:52:51.135711

## Dataset Statistics

- **positive**: 8 pairs
- **negative**: 5 pairs
- **hard_negative**: 8 pairs
- **boundary**: 5 pairs

## Campaign Results by Metamorphic Relation

### MR-01

- **PASS**: 1
- **VIOLATION**: 7

**Violations (7):**

- Pair `finance-positive-0000`: 
  - text_a: _The company reported strong quarterly earnings growth._
  - text_b: _The firm achieved significant profit increases this quarter._
- Pair `finance-positive-0001`: 
  - text_a: _The company reported strong quarterly earnings growth._
  - text_b: _The firm achieved significant profit increases this quarter._
- Pair `finance-positive-0003`: 
  - text_a: _Interest rates were raised by the central bank._
  - text_b: _The central bank increased its benchmark interest rate._
- Pair `finance-positive-0004`: 
  - text_a: _Interest rates were raised by the central bank._
  - text_b: _The central bank increased its benchmark interest rate._
- Pair `finance-positive-0005`: 
  - text_a: _Interest rates were raised by the central bank._
  - text_b: _The central bank increased its benchmark interest rate._

### MR-03

- **OBSERVATION**: 3
- **PASS**: 5

### MR-04

- **OBSERVATION**: 1
- **PASS**: 4

## Summary

| Metric | Value |
|--------|-------|
| Total tests | 21 |
| Violations | 7 |
| Passes | 10 |
| Violation rate | 33.3% |

## Key Findings

Found **7 metamorphic violations** across 21 tests.
These indicate semantic correctness issues in the vector database's retrieval.