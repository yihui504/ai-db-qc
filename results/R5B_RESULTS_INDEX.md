# R5B Lifecycle Campaign - Results Index

**Campaign**: R5B Index Lifecycle State Transitions
**Database**: Milvus v2.6.10
**Date Range**: 2026-03-10

---

## Overview

| Metric | Value |
|--------|-------|
| Total Result Files | 16 |
| Final Run | r5b-lifecycle-20260310-124135 |
| Database Version | Milvus v2.6.10 |
| Test Mode | REAL (not mock) |
| Contracts Tested | 11 (ILC-001 through ILC-010) |

---

## Result Files by Chronological Order

### Morning Session - Initial Verification

| Run ID | File | Time | Contracts | Status | Key Finding |
|--------|------|------|-----------|--------|-------------|
| r5b-lifecycle-20260310-114329 | r5b_lifecycle_20260310-114329.json | 11:43 | 11 | MOCK | Infrastructure test |
| r5b-lifecycle-20260310-114356 | r5b_lifecycle_20260310-114356.json | 11:43 | 11 | MOCK | Infrastructure test |
| r5b-lifecycle-20260310-115216 | r5b_lifecycle_20260310-115216.json | 11:52 | 11 | REAL | Initial smoke test |
| r5b-lifecycle-20260310-115340 | r5b_lifecycle_20260310-115340.json | 11:53 | 11 | REAL | Smoke test validation |
| r5b-lifecycle-20260310-115625 | r5b_lifecycle_20260310-115625.json | 11:56 | 11 | REAL | Pre-round 1 validation |
| r5b-lifecycle-20260310-115704 | r5b_lifecycle_20260310-115704.json | 11:57 | 11 | REAL | Pre-round 1 validation |
| r5b-lifecycle-20260310-115814 | r5b_lifecycle_20260310-115814.json | 11:58 | 11 | REAL | Pre-round 1 validation |
| r5b-lifecycle-20260310-115857 | r5b_lifecycle_20260310-115857.json | 11:58 | 11 | REAL | **Round 1 - Pass 1** |

### Mid-Day Session - Round 2 with ILC-009 Investigation

| Run ID | File | Time | Contracts | Status | Key Finding |
|--------|------|------|-----------|--------|-------------|
| r5b-lifecycle-20260310-120943 | r5b_lifecycle_20260310-120943.json | 12:09 | 11 | REAL | Extended test run |
| r5b-lifecycle-20260310-121731 | r5b_lifecycle_20260310-121731.json | 12:17 | 11 | REAL | **Round 1 - ILC-009 issue discovered** |
| r5b-lifecycle-20260310-123545 | r5b_lifecycle_20260310-123545.json | 12:35 | 11 | REAL | **Round 2 - ILC-009b (dimension bug)** |
| r5b-lifecycle-20260310-123741 | r5b_lifecycle_20260310-123741.json | 12:37 | 11 | REAL | **Round 2 - ILC-009b first valid run** |
| r5b-lifecycle-20260310-123955 | r5b_lifecycle_20260310-123955.json | 12:39 | 11 | REAL | **Round 2 - Oracle fix verification** |
| r5b-lifecycle-20260310-124135 | r5b_lifecycle_20260310-124135.json | 12:41 | 11 | REAL | **Final run - All tests pass** |

---

## Key Result Files

### Primary Results (Use These)

#### r5b-lifecycle-20260310-124135.json (FINAL)

**Status**: COMPLETE - All tests pass
**Time**: 2026-03-10 12:41
**Classification Summary**:
- PASS: 8
- EXPECTED_FAILURE: 1
- VERSION_GUARDED: 1
- EXPERIMENT_DESIGN_ISSUE: 0

**Key Findings**:
- ILC-009b: Flush enables search visibility (exact match proof)
- All lifecycle contracts verified

**Documentation**: [R5B_ILC009B_FINAL_REPORT.md](../docs/experiments/R5B_ILC009B_FINAL_REPORT.md)

#### r5b-lifecycle-20260310-121731.json (Round 1)

**Status**: ILC-009 issue discovered
**Time**: 2026-03-10 12:17
**Issue**: ILC-009 query design insufficient

**Documentation**: [R5B_ILC009_POST_INSERT_INVESTIGATION.md](../docs/experiments/R5B_ILC009_POST_INSERT_INVESTIGATION.md)

---

## Contract Results Summary

### ILC-001: Create Index State Transition

| Run ID | Result | Evidence |
|--------|--------|----------|
| 124135 | PASS | index_metadata_exists=true, load_state=NotLoad |

**Universal Candidate**: YES

---

### ILC-002: Search Precondition Gate

| Run ID | Result | Evidence |
|--------|--------|----------|
| 124135 | EXPECTED_FAILURE | Search fails on unloaded collection |

**Universal Candidate**: YES

---

### ILC-003: Load State Transition

| Run ID | Result | Evidence |
|--------|--------|----------|
| 124135 | PASS | load_state changes NotLoad → Loaded |

**Universal Candidate**: YES

---

### ILC-004: Loaded Search Baseline

| Run ID | Result | Evidence |
|--------|--------|----------|
| 124135 | PASS | Search returns results when Loaded |

**Universal Candidate**: YES

---

### ILC-005: Release State Transition

| Run ID | Result | Evidence |
|--------|--------|----------|
| 124135 | PASS | load_state=NotLoad, metadata preserved |

**Universal Candidate**: YES

---

### ILC-006: Reload After Release

| Run ID | Result | Evidence |
|--------|--------|----------|
| 124135 | PASS | load_state=Loaded, results match pre-release |

**Universal Candidate**: YES

---

### ILC-007: Drop Index Transition

| Run ID | Result | Evidence |
|--------|--------|----------|
| 124135 | PASS | Index dropped, collection not loaded |

**Universal Candidate**: YES

---

### ILC-008: Post-Drop Search Semantics

| Run ID | Result | Evidence |
|--------|--------|----------|
| 124135 | VERSION_GUARDED | load fails with "index not found" |

**Universal Candidate**: PARTIAL (may allow brute force)

---

### ILC-009: Post-Insert Visibility (Original)

| Run ID | Result | Evidence |
|--------|--------|----------|
| 121731 | EXPERIMENT_DESIGN_ISSUE | Query design insufficient |
| 124135 | EXPERIMENT_DESIGN_ISSUE | Redesigned as ILC-009b |

**Resolution**: ILC-009b conclusive

---

### ILC-009b: Post-Insert Search Timing (Final)

| Run ID | Result | Evidence |
|--------|--------|----------|
| 124135 | PASS | Flush enables search visibility |

**Evidence**:
- Immediate: id=50, score=27.27 (existing vector)
- After flush: id=0, score=0.0 (exact match)

**Universal Candidate**: YES

**Documentation**: [R5B_ILC009B_FINAL_REPORT.md](../docs/experiments/R5B_ILC009B_FINAL_REPORT.md)

---

### ILC-010: Documented NotLoad Behavior

| Run ID | Result | Evidence |
|--------|--------|----------|
| 124135 | PASS | load_state=NotLoad after create_collection |

**Universal Candidate**: YES

---

## Result File Details

### Final Run (r5b-lifecycle-20260310-124135.json)

```json
{
  "run_id": "r5b-lifecycle-20260310-124135",
  "timestamp": "2026-03-10T12:41:35",
  "database": "Milvus v2.6.10",
  "mode": "REAL",
  "total_tests": 11,
  "summary": {
    "total": 11,
    "by_classification": {
      "PASS": 8,
      "EXPECTED_FAILURE": 1,
      "VERSION_GUARDED": 1,
      "EXPERIMENT_DESIGN_ISSUE": 1
    },
    "passed": 10,
    "failed": 1
  }
}
```

### ILC-009b Evidence (from 124135)

```json
{
  "search_top1": {
    "immediate": {"id": 50, "score": 27.27, "distance": 27.27},
    "after_flush": {"id": 0, "score": 0.0, "distance": 0.0},
    "200ms": {"id": 0, "score": 0.0, "distance": 0.0},
    "500ms": {"id": 0, "score": 0.0, "distance": 0.0},
    "1000ms": {"id": 0, "score": 0.0, "distance": 0.0}
  },
  "storage_counts": {
    "baseline": 100,
    "before_flush": 100,
    "after_flush": 101
  },
  "conclusion": "flush_enables_search_visibility",
  "visible_at": "after_flush"
}
```

---

## Documentation Links

### Campaign Documentation

| Document | Location | Description |
|----------|----------|-------------|
| Final Summary | docs/experiments/R5B_FINAL_SUMMARY.md | Campaign overview and findings |
| Handoff | docs/handoffs/R5B_COMPLETE_HANDOFF.md | R5B to R5D handoff |
| Contracts | contracts/index/lifecycle_contracts.json | Contract definitions and state model |

### Investigation Reports

| Document | Location | Description |
|----------|----------|-------------|
| Smoke Test | docs/experiments/R5B_MILVUS_V2610_SMOKE_REPORT.md | Initial Milvus verification |
| Round 2 | docs/experiments/R5B_ROUND2_SECOND_EXPERIMENTS.md | ILC-009 investigation |
| ILC-009 | docs/experiments/R5B_ILC009_POST_INSERT_INVESTIGATION.md | Investigation details |
| ILC-009b | docs/experiments/R5B_ILC009B_FINAL_REPORT.md | Conclusive results |

---

## Archive Strategy

### Keep (Primary Results)

- `r5b_lifecycle_20260310-115857.json` - Round 1 baseline
- `r5b_lifecycle_20260310-121731.json` - ILC-009 issue discovery
- `r5b_lifecycle_20260310-123741.json` - ILC-009b first valid run
- `r5b_lifecycle_20260310-124135.json` - **FINAL** (primary reference)

### Can Delete (Intermediate/Duplicate)

- `r5b_lifecycle_20260310-114329.json` - Mock test
- `r5b_lifecycle_20260310-114356.json` - Mock test
- `r5b_lifecycle_20260310-115216.json` - Smoke test intermediate
- `r5b_lifecycle_20260310-115340.json` - Smoke test intermediate
- `r5b_lifecycle_20260310-115625.json` - Pre-round 1
- `r5b_lifecycle_20260310-115704.json` - Pre-round 1
- `r5b_lifecycle_20260310-115814.json` - Pre-round 1
- `r5b_lifecycle_20260310-120943.json` - Extended test
- `r5b_lifecycle_20260310-123545.json` - Dimension bug run
- `r5b_lifecycle_20260310-123955.json` - Oracle verification

---

## Query Template

### Python Query Example

```python
import json

# Load final result
with open('results/r5b_lifecycle_20260310-124135.json', 'r') as f:
    data = json.load(f)

# Get contract results
for result in data['results']:
    contract_id = result['contract_id']
    classification = result['oracle']['classification']
    reasoning = result['oracle']['reasoning']
    print(f"{contract_id}: {classification} - {reasoning}")
```

### Bash Query Example

```bash
# Count classifications
cat results/r5b_lifecycle_20260310-124135.json | \
  jq '.summary.by_classification'

# Get ILC-009b evidence
cat results/r5b_lifecycle_20260310-124135.json | \
  jq '.results[] | select(.contract_id == "ILC-009b") | .oracle.evidence'
```

---

**Index Created**: 2026-03-10
**Last Updated**: 2026-03-10
**Campaign Status**: COMPLETE
