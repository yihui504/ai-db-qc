# Differential Campaign Readiness - Revised Assessment

> **Date**: 2026-03-07
> **Status**: Framework ready, first subset ready, full campaign NOT ready

---

## Revised Status Summary

| Component | Status | Evidence |
|-----------|--------|----------|
| **Framework** | ✅ READY | Runner, analyzer, labels tested |
| **First comparison subset** | ✅ READY | 10 cases, 60% success rate |
| **Full 30-case pack** | ❌ NOT READY | 6/30 = 20% success rate |

**Key Point**: 6/30 successes is NOT "campaign ready." It's "framework working, cases need tuning."

---

## First Comparison Subset: 10 Cases

These are **ready for immediate Milvus-vs-seekdb comparison**:

| Case | Operation | seekdb | Why Ready |
|------|-----------|--------|-----------|
| subset-001-baseline | create valid | ✅ | Both should succeed |
| subset-002-drop-nonexistent | drop nonexistent | ✅ | **Confirmed difference** |
| subset-003-topk-zero | search top_k=0 | ✅ | Boundary case |
| subset-004-invalid-metric | create invalid metric | ✅ | Leniency test |
| subset-005-empty-metric | create empty metric | ✅ | Leniency test |
| subset-006-dim-zero | create dim=0 | ❌ Correct reject | Type-2 comparison |
| subset-007-dim-negative | create dim=-1 | ❌ Correct reject | Type-2 comparison |
| subset-008-search-nonexistent | search nonexistent | ❌ Expected fail | Diagnostic quality |
| subset-009-delete-nonexistent | delete nonexistent | ❌ Expected fail | Diagnostic quality |
| subset-010-valid-search | search valid | ✅ | Baseline |

**Success rate**: 6/10 = 60% ✅ Acceptable

---

## Remaining 20 Cases Classification

### Category A: Needs More Mapping (5 cases)

| Case | Issue | Fix |
|------|-------|-----|
| diff-boundary-003 | dimension=99999 | Test actual limits first |
| diff-boundary-006 | top_k=1000000 | Find actual max top_k |
| diff-diag-003 | top_k=-5 | SQL syntax error in adapter |
| diff-diag-006 | dimension mismatch | Vector validation needed |
| diff-diag-009 | empty query vector | Validation needed |

### Category B: Needs More Setup (10 cases)

| Cases | Dependency | Status |
|-------|------------|--------|
| diff-boundary-009, 010 | Empty vectors | Need validation logic |
| diff-diag-004, 005, 008 | Template uses wrong names | Already fixed in subset |
| diff-diag-007, 009 | Empty list handling | Need validation |
| diff-diag-010 | Valid insert | Works, covered in subset |
| diff-precond-004 | Empty collection | Need setup |
| diff-precond-005 | Index state | Need index control |
| diff-precond-006, 007 | Index dependent | Need setup |

### Category C: Defer (5 cases)

| Cases | Reason |
|-------|--------|
| diff-precond-002 | Duplicate of 001 |
| diff-precond-004 | Edge case, low value |
| diff-precond-006 | Unclear test intent |
| diff-precond-007 | Covered by subset-010 |
| diff-precond-008 | Covered by subset-009 |

---

## How to Run First Comparison

```bash
cd C:/Users/11428/Desktop/ai-db-qc

# Run first subset (10 cases)
PYTHONPATH="C:/Users/11428/Desktop/ai-db-qc" python scripts/run_differential_campaign.py \
    --run-tag first-subset-v1 \
    --templates casegen/templates/differential_first_subset.yaml \
    --milvus-endpoint localhost:19530 \
    --seekdb-endpoint 127.0.0.1:2881

# Analyze
python scripts/analyze_differential_results.py runs/differential-first-subset-v1-<timestamp>
```

**Expected output**: At least 2-3 meaningful behavioral differences between Milvus and seekdb.

---

## Path to Full Campaign Readiness

To get the full 30-case pack ready:

1. **Fix remaining adapter issues** (SQL syntax for negative values)
2. **Add proper validation** (empty vectors, empty lists)
3. **Test limits** (max dimension, max top_k)
4. **Simplify complex cases** (remove index-dependent tests or add setup)
5. **Re-validate** (target >70% success rate)

**Timeline**: 1-2 days of additional work

**Or**: Use first subset now, expand later based on findings.

---

## Summary

| Question | Answer |
|----------|--------|
| Is framework ready? | ✅ YES |
| Is first subset (10 cases) ready? | ✅ YES - 60% success |
| Is full pack (30 cases) ready? | ❌ NO - only 20% success |
| Can we run comparison now? | ✅ YES - use first subset |
| Should we claim "full ready"? | ❌ NO - that was overstated |
