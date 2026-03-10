# R1 + R2 Cumulative Results Summary (REVISED)

**Period**: 2026-03-08
**Campaigns**: 2 (R1, R2)
**Total Cases**: 21
**Status**: ✅ Phase 1 COMPLETE - Tool validated, findings corrected

---

## Executive Summary

The first results-driven production phase (R1 + R2) successfully validated the AI-DB-QC tool workflow. **IMPORTANT CORRECTION**: What was initially classified as a "metric_type validation weakness family" has been corrected to an "API silent-ignore issue" after pre-submission audit revealed that `metric_type` is not actually a Collection() constructor parameter.

**Corrected Finding**: pymilvus `Collection()` silently ignores undocumented parameters passed via `**kwargs`, creating a misleading API where users may think they're setting parameters that are actually being ignored.

---

## Campaign Overview

| Campaign | Focus | Cases | Primary Finding | Status |
|----------|-------|-------|-----------------|--------|
| **R1** | Core High-Yield | 10 | API silent-ignore (cb-bound-005) | ✅ Complete |
| **R2** | Parameter Validation | 11 | API silent-ignore (param-metric-001) | ✅ Complete |
| **Total** | - | 21 | 1 (same underlying issue) | ✅ Phase 1 COMPLETE |

---

## Corrected Understanding

### What We Thought We Found (INCORRECT)

Initially classified as "Type-1 parameter validation bug" where pymilvus accepts invalid metric_type values.

### What We Actually Found (CORRECTED)

**pymilvus `Collection()` constructor silently ignores undocumented parameters via `**kwargs`.**

The actual Collection signature:
```python
Collection(self, name: str, schema: Optional[CollectionSchema] = None,
           using: str = 'default', **kwargs) -> None
```

The `metric_type` parameter:
- Is **NOT** a Collection() constructor parameter
- Is set during **index creation**, not collection creation
- Any value passed to Collection() is silently ignored via `**kwargs`

---

## Primary Finding

### Silent kwargs Ignore Issue

| Attribute | Value |
|-----------|-------|
| **ID** | api-silent-kwargs-001 |
| **Type** | API usability / silent ignore |
| **Severity** | LOW-MEDIUM |
| **Impact** | User confusion, not data integrity |
| **Discovery** | R1 (cb-bound-005), R2 (param-metric-001) |
| **Root Cause** | Collection() accepts **kwargs and ignores without warning |

**Evidence**:
- `Collection(..., metric_type="INVALID_METRIC")` → Succeeds, parameter ignored
- `Collection(..., metric_type="")` → Succeeds, parameter ignored
- `hasattr(collection, 'metric_type')` → False (not stored)

**Correct API Usage**:
```python
# Collection creation: NO metric_type parameter
collection = Collection(name='my_collection', schema=schema)

# metric_type is set during index creation
collection.create_index(
    field_name='vector',
    index_params={'index_type': 'IVF_FLAT', 'metric_type': 'L2', ...}
)
```

---

## Exploratory Observations

| Observation | Type | Notes |
|-------------|------|-------|
| Lowercase "l2" accepted | API usability | Same silent-ignore behavior (not about case sensitivity) |
| cb-bound-006 (duplicate collection) | NOT A BUG | pymilvus Collection() is idempotent by design |
| cb-bound-002/003 | Poor diagnostics | Error mentions parameter but not valid range |
| param-dtype-001 | Tool artifact | Adapter ignores dtype parameter |

**False Positives Cleaned**: 4 cases

---

## Tool Validated

The R1 + R2 phase successfully validated the end-to-end workflow:

| Component | Status |
|-----------|--------|
| Case generation | ✅ Working |
| Validation | ✅ Working |
| Precondition evaluation | ✅ Working |
| Triage | ✅ Working |
| Export | ✅ Working |
| Vector parsing | ✅ Fixed during R1 |
| Template substitution | ✅ Fixed during R1 |

**Key Learning**: Pre-submission audit is critical to verify findings against actual API documentation.

---

## Success Criteria Assessment

### R1 Criteria
| Criterion | Target | Actual | Status |
|-----------|--------|--------|--------|
| Cases executed | 10 | 10 | ✅ |
| Artifacts produced | 5 | 5 | ✅ |

### R2 Criteria
| Criterion | Target | Actual | Status |
|-----------|--------|--------|--------|
| Cases executed | 11 | 11 | ✅ |
| Calibration cases pass | 2 | 2 | ✅ |

**Minimum Success**: Tool workflow validated ✅
**Note**: "High-confidence bug" metric is no longer applicable after correction.

---

## Regression Pack

**File**: `casegen/templates/regression_pack.yaml`

| Case ID | Type | Severity | Purpose |
|---------|------|----------|---------|
| regression-api-silent-kwargs-001 | API usability | LOW-MEDIUM | Track silent kwargs ignore issue |

**Change**: Downgraded from "validation bug" to "API usability issue"

---

## Issue Filing Status

| Issue Package | Finding Type | Status |
|---------------|-------------|--------|
| Silent kwargs ignore | API usability | Package ready, severity LOW-MEDIUM |

**Issue Package**: `docs/issues/ISSUE_PACKAGE_silent_kwargs_ignore.md`

**Recommendation**: File as API usability improvement, not as a data integrity bug.

---

## Yield Analysis (Revised)

| Metric | Value |
|--------|-------|
| **Total cases** | 21 |
| **API usability findings** | 1 (silent kwargs ignore) |
| **Exploratory observations** | 1-3 |
| **False positives cleaned** | 4 |
| **Validly exercised** | 19 (90%) |
| **Tooling gaps identified** | 1 (dtype parameter) |

**Learning**: The tool successfully identified an API usability issue, though initial classification required correction after audit.

---

## Key Learnings

1. **Pre-submission audit is essential**: Verification against actual API documentation revealed the issue was different than initially classified

2. **Tool artifacts matter**: param-dtype-001 appeared to be a bug but was a tooling gap

3. **API signature analysis**: Checking `inspect.signature()` revealed **kwargs pattern, not a validation bug

4. **Reproducibility matters**: Finding reproduced across 3 campaigns, but interpretation was corrected

5. **Severity assessment matters**: Initial classification as HIGH severity bug was incorrect; corrected to LOW-MEDIUM API usability issue

---

## Corrected Findings Summary

### What We Found

| Category | Finding |
|----------|---------|
| **API usability** | Collection() silently ignores undocumented kwargs (LOW-MEDIUM severity) |
| **NOT a validation bug** | metric_type is not a Collection parameter at all |
| **NOT a data integrity risk** | Collections work correctly; metric_type set during index creation |

### What We Did NOT Find

| Category | Status |
|-----------|--------|
| Parameter validation bugs | None confirmed - all tested parameters (dimension, top_k, index_type) validated correctly |
| Database-level metric_type validation weakness | N/A - metric_type is for index creation, not Collection |

---

## Phase 1 vs Phase 2 Strategy

**Phase 1 (R1 + R2)**: COMPLETE
- ✅ Validated tool workflow
- ✅ Discovered API usability issue
- ✅ Established regression pack
- ✅ Learned importance of pre-submission audit

**Phase 2 (R3+)**: READY TO START
- Focus: **Documented parameter families** (schema, index, search)
- Avoid: Silently-ignored kwargs
- Target: Consistency_level, replica_number, nlist, m, nprobe

---

## Next Steps

1. **File silent kwargs issue** (when ready) as API usability improvement
2. **Execute R3** with corrected understanding:
   - Test documented parameters (consistency_level, replica_number)
   - Test index nested parameters (nlist, m)
   - Test search nested parameters (nprobe)
   - Avoid passing arbitrary kwargs to Collection()
3. **Fix dtype tooling gap** before any dtype testing
4. **Expand regression pack** based on R3 findings

---

## Metadata

- **Tool Version**: 0.1.0
- **Database**: pymilvus v2.6.2, Milvus server v2.6.10
- **Duration**: 1 day (2026-03-08)
- **Artifacts**:
  - R1: `results/milvus_validation_20260308_223239/`
  - R2: `results/milvus_validation_20260308_225412/`
- **Documentation**:
  - Issue Package: `docs/issues/ISSUE_PACKAGE_silent_kwargs_ignore.md`
  - R3 Proposal: `docs/plans/R3_CAMPAIGN_PROPOSAL.md`
