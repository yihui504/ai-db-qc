# SeekDB Extended Contract Coverage — Step 1

**Generated**: 2026-03-16T21:31:17.430976
**Adapter**: mock
**Step**: 1 (New contract families)
**Total Violations**: 2

## Summary

| Test Family | Violations | Status |
|-------------|-----------|--------|
| MR-03 | 0 | PASS |
| R7 | 0 | PASS |
| R8 | 0 | PASS |
| R5D | 2 | VIOLATION |

## Detail

### MR-03

**Summary**: {"PASS": 10, "VIOLATION": 0}

No violations.

### R7

**Summary**: {"R7A": {"n_threads": 8, "violations": 0}, "R7B": {"violations": 0, "counts": [0, 0, 0, 0, 0, 0]}}

No violations.

### R8

**Summary**: {"violations": 0}

No violations.

### R5D

**Summary**: {"SCH-001": "PASS", "SCH-002": "VIOLATION", "SCH-003": "PASS", "SCH-004": "VIOLATION"}

- `SCH-002-WRONG-DIM-ACCEPTED`: Vector with dim=26 was accepted into collection with dim=16
- `SCH-004-COUNT-MISMATCH`: Expected 5 entities after insert, got -1
