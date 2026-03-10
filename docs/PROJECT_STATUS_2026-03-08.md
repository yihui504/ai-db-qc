# AI-DB-QC Project Status Snapshot

**Date**: 2026-03-08
**Milestone 1**: ✅ COMPLETE (Prototype Level)

---

## Completed Milestones

### Milestone 1: Results Production Phase 1 ✅

**Campaigns Executed**: 2 (R1, R2)

| Campaign | Focus | Cases | Status |
|----------|-------|-------|--------|
| **R1** | Core High-Yield | 10 | ✅ Complete |
| **R2** | Parameter Validation | 11 | ✅ Complete |

**Total Cases**: 21

---

## Confirmed Findings

### API Usability Issue (1)

| Attribute | Value |
|-----------|-------|
| **ID** | api-silent-kwargs-001 |
| **Type** | API usability / silent ignore |
| **Severity** | LOW-MEDIUM |
| **Impact** | User confusion, not data integrity |
| **Discovery** | R1 (cb-bound-005), R2 (param-metric-001) |

**Description**: pymilvus `Collection()` constructor silently ignores undocumented parameters via `**kwargs`.

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

**Issue Package**: `docs/issues/ISSUE_PACKAGE_silent_kwargs_ignore.md`

---

## Tooling Gaps Identified

| Gap ID | Parameter | Issue | Location |
|--------|-----------|-------|----------|
| TOOLING-001 | dtype | Parameter not supported | `adapters/milvus_adapter.py:_create_collection` |
| TOOLING-002 | consistency_level | Silent-ignore via **kwargs | `adapters/milvus_adapter.py:_create_collection` |
| TOOLING-003 | index_params | Hardcoded to {"nlist": 128} | `adapters/milvus_adapter.py:_build_index` |
| TOOLING-004 | search_params | Hardcoded to {"nprobe": 10} | `adapters/milvus_adapter.py:_search` |

---

## R3 Status: POSTPONED

**Reason**: All 4 planned R3 parameter families have adapter support issues.

| Parameter | Adapter Supports | DB Validates | Ready for Campaign |
|-----------|-----------------|--------------|-------------------|
| consistency_level | ❌ No (**kwargs) | ❌ Silent ignore | **NO** |
| index_params.nlist | ❌ No (hardcoded) | ✅ Good diagnostics | **NO** |
| index_params.m | ❌ No (hardcoded) | ❓ Unknown | **NO** |
| search_params.nprobe | ❌ No (hardcoded) | ❓ Unknown | **NO** |

**Decision**: POSTPONE until adapter gaps are resolved.

---

## Tool Validation Status

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

## Bug Classification (Corrected)

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

## Yield Analysis

| Metric | Value |
|--------|-------|
| **Total cases** | 21 |
| **API usability findings** | 1 (silent kwargs ignore) |
| **Exploratory observations** | 1-3 |
| **False positives cleaned** | 4 |
| **Validly exercised** | 19 (90%) |
| **Tooling gaps identified** | 4 (dtype, consistency_level, index_params, search_params) |

---

## Next Candidate Directions

### Option A: Enhance Adapter + Parameter Testing R3

**Work Required**:
1. Enhance MilvusAdapter to support custom index_params (nlist, m)
2. Enhance MilvusAdapter to support custom search_params (nprobe)
3. Verify Collection parameter support
4. Re-audit after adapter changes
5. Execute original R3 parameter validation design

### Option B: Operation Sequence Testing R3

**Work Required**:
1. Implement sequence test framework (new capability)
2. Precondition evaluation for state transitions
3. Oracle for state violation detection
4. Triage for state-transition bug classification

**Proposed Cases**: 8-9 operation sequence tests

### Option C: Cross-Database Campaign

**Work Required**:
1. Verify SeekDB adapter setup
2. Assess SeekDB parameter support
3. May have similar adapter gaps

---

## Regression Pack

**File**: `casegen/templates/regression_pack.yaml`

| Case ID | Type | Severity | Purpose |
|---------|------|----------|---------|
| regression-api-silent-kwargs-001 | API usability | LOW-MEDIUM | Track silent kwargs ignore issue |

**Status**: Updated with corrected classification (API usability, not validation bug)

---

## Documentation Artifacts

### Results
- `results/milvus_validation_20260308_223239/` (R1)
- `results/milvus_validation_20260308_225412/` (R2)

### Planning Documents
- `docs/plans/R3_REDESIGNED.md` - Option B proposal (operation sequences)
- `docs/plans/R3_CAMPAIGN_DESIGN_FINAL.md` - Original R3 design (blocked)

### Audit Reports
- `docs/tooling_gaps/R3_PARAMETER_SUPPORT_AUDIT.md` - Full adapter audit
- `docs/tooling_gaps/dtype_parameter_not_supported.md` - dtype gap documentation

### Status Documents
- `docs/R1_R2_CUMULATIVE_SUMMARY_REVISED.md` - Phase 1 summary
- `docs/R3_DECISION_STATUS.md` - R3 postponement decision
- `docs/NEXT_SESSION_START_HERE.md` - Session handoff

### Issue Packages
- `docs/issues/ISSUE_PACKAGE_silent_kwargs_ignore.md` - Ready for external filing

---

## Key Learnings

1. **Pre-submission audit is essential**: Verification against actual API documentation prevented misclassification

2. **API signature analysis**: `inspect.signature()` revealed **kwargs pattern, not validation bugs

3. **Tool artifacts matter**: Parameters that appear to be bugs may be tooling gaps

4. **Test-case correctness judgment**: Primary goal is reliable bug identification, not raw execution volume

5. **Adapter support verification**: Critical to verify adapter capabilities before campaign execution

---

## Environment

- **Tool Version**: 0.1.0
- **Database**: pymilvus v2.6.2, Milvus server v2.6.10
- **Platform**: Windows 11
- **Date**: 2026-03-08

---

**Phase 1 COMPLETE. R3 postponed pending direction decision.**
