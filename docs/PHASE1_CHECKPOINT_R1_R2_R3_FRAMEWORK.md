# Phase 1 Checkpoint: R1, R2, and R3 Framework

**Checkpoint Date**: 2026-03-09
**Phase**: 1 Complete (Results Production Phase 1)
**Status**: ✅ Milestone 1 Finalized, R3 Framework Ready, Real R3 Pending

---

## Executive Summary

Phase 1 successfully validated the AI-DB-QC tool workflow through two real campaigns (R1, R2) and implemented the framework for R3 (sequence-based testing). The primary finding was reclassified from a "validation bug" to an "API silent-ignore usability issue" after pre-submission audit.

**CRITICAL**: Real R3 campaign has NOT yet been executed. Only the framework has been implemented and validated via mock dry-run.

---

## Milestone 1: Finalized (Prototype Level)

### Completion Criteria Met

| Criterion | Target | Actual | Status |
|-----------|--------|--------|--------|
| Tool workflow validated | Yes | Yes | ✅ |
| Real database campaigns executed | ≥1 | 2 (R1, R2) | ✅ |
| Pre-submission audit process | Yes | Yes | ✅ |
| Regression pack established | Yes | Yes | ✅ |
| Issue package ready | Yes | Yes | ✅ |

### Campaigns Completed

- **R1**: 10 cases (real Milvus)
- **R2**: 11 cases (real Milvus)
- **R3 Framework**: Implemented, mock dry-run completed
- **R3 Real Campaign**: NOT YET EXECUTED

---

## R1 Campaign Results

### Configuration
- **Date**: 2026-03-08
- **Database**: pymilvus v2.6.2, Milvus server v2.6.10
- **Adapter**: Real Milvus
- **Cases**: 10 (6 capability boundary, 2 precondition calibration, 2 exploratory)

### Primary Finding (Initially Incorrect)

**Initial Classification**: "metric_type validation weakness family"
- Assumed: pymilvus accepts invalid metric_type values (Type-1 parameter validation bug)

### Corrected Finding

**Actual Classification**: "API silent-ignore usability issue"
- `metric_type` is NOT a Collection() constructor parameter
- Collection signature: `Collection(self, name: str, schema: Optional[CollectionSchema] = None, using: str = 'default', **kwargs) -> None`
- Any value passed to Collection() is silently ignored via `**kwargs`
- **NOT a validation bug** - pymilvus correctly ignores undocumented parameters
- **Severity**: LOW-MEDIUM (user confusion, not data integrity risk)

### Key Learnings from R1

1. Pre-submission audit is essential for correct classification
2. API signature analysis (`inspect.signature()`) revealed **kwargs pattern
3. Tool artifacts (like dtype parameter not supported) can appear as bugs
4. Vector parsing and template substitution issues were fixed during execution

### Evidence
- **Results Directory**: `results/milvus_validation_20260308_223239/`
- **Issue Package**: `docs/issues/ISSUE_PACKAGE_silent_kwargs_ignore.md`

---

## R2 Campaign Results

### Configuration
- **Date**: 2026-03-08
- **Database**: pymilvus v2.6.2, Milvus server v2.6.10
- **Adapter**: Real Milvus
- **Cases**: 11 (parameter validation focus)

### Primary Finding

**Same underlying issue**: API silent-ignore usability issue
- R2's `param-metric-001` reproduced the same finding as R1's `cb-bound-005`
- Confirmed that metric_type is not a Collection parameter

### Exploratory Observations

| Observation | Type | Notes |
|-------------|------|-------|
| Lowercase "l2" accepted | API usability | Same silent-ignore behavior |
| cb-bound-006 (duplicate collection) | NOT A BUG | pymilvus Collection() is idempotent by design |
| cb-bound-002/003 | Poor diagnostics | Error mentions parameter but not valid range |
| param-dtype-001 | Tool artifact | Adapter ignores dtype parameter |

### False Positives Cleaned
- 4 cases removed or reclassified after audit

### Key Learnings from R2

1. Reproducibility confirmed across campaigns (same finding in R1 and R2)
2. Calibration cases passed as expected
3. Tooling gaps identified (dtype parameter not supported)

### Evidence
- **Results Directory**: `results/milvus_validation_20260308_225412/`
- **Templates**: `casegen/templates/r2_param_validation.yaml`

---

## Metric_Type Issue Reclassification

### What We Thought We Found (INCORRECT)

**Initial Classification**: Type-1 parameter validation bug
- pymilvus accepts invalid metric_type values in Collection() constructor
- Severity: HIGH (data integrity risk)

### What We Actually Found (CORRECTED)

**Corrected Classification**: API silent-ignore usability issue
- pymilvus `Collection()` silently ignores undocumented parameters via `**kwargs`
- `metric_type` is set during **index creation**, not collection creation
- Severity: LOW-MEDIUM (user confusion, not data integrity)

### API Signature Analysis

```python
# Actual pymilvus Collection signature
Collection(self, name: str, schema: Optional[CollectionSchema] = None,
           using: str = 'default', **kwargs) -> None

# metric_type is NOT an explicit parameter
# Any value passed via Collection(..., metric_type="X") is silently ignored
```

### Correct API Usage

```python
# WRONG: metric_type in Collection (silently ignored)
collection = Collection(name='my_collection', schema=schema, metric_type="L2")

# CORRECT: metric_type in create_index
collection.create_index(
    field_name='vector',
    index_params={'index_type': 'IVF_FLAT', 'metric_type': 'L2', ...}
)
```

### Impact

- **Issue Package**: Downgraded to "API usability improvement"
- **Severity**: LOW-MEDIUM (not HIGH)
- **Type**: Usability, not data integrity bug
- **Filing Status**: Package ready, but not a critical issue

---

## Adapter Capability Audit Results

### Original R3 Parameter Plan

The original R3 design focused on testing **documented parameter families**:
- consistency_level
- index_params.nlist
- index_params.m (HNSW)
- search_params.nprobe

### Audit Findings

**Critical Discovery**: ALL four planned R3 parameter families have **adapter support issues**

| Parameter | Issue | Status |
|-----------|-------|--------|
| **consistency_level** | Silent-ignore via **kwargs (like metric_type) | NOT SUITABLE |
| **index_params.nlist** | Adapter hardcodes nlist=128 | NOT SUITABLE |
| **index_params.m** | Adapter hardcodes nlist-based params | NOT SUITABLE |
| **search_params.nprobe** | Adapter hardcodes nprobe=10 | NOT SUITABLE |

### Tooling Gaps Identified

| Gap ID | Parameter | Issue | File |
|--------|-----------|-------|------|
| TOOLING-001 | dtype | Parameter not supported | adapters/milvus_adapter.py:_create_collection |
| TOOLING-002 | consistency_level | Silent-ignore via **kwargs | adapters/milvus_adapter.py:_create_collection |
| TOOLING-003 | index_params | Hardcoded to {"nlist": 128} | adapters/milvus_adapter.py:_build_index |
| TOOLING-004 | search_params | Hardcoded to {"nprobe": 10} | adapters/milvus_adapter.py:_search |

### Impact

**R3 Parameter Version**: BLOCKED by adapter gaps
- Testing these parameters would produce tool-layer artifacts, not database bugs
- Pre-execution audit prevented another metric_type-style misclassification
- **R3 execution postponed until adapter enhanced or alternative direction chosen**

### Evidence
- **Audit Document**: `docs/tooling_gaps/R3_PARAMETER_SUPPORT_AUDIT.md`

---

## Decision: Option B (Sequence-Based R3)

### Three Options Presented

| Option | Description | Pros | Cons | Status |
|--------|-------------|------|------|--------|
| **A** | Enhance adapter first | Enables original R3 | Requires adapter dev | POSTPONED |
| **B** | Operation sequences | No adapter changes needed | Different focus | CHOSEN |
| **C** | Cross-database | Uses existing workflow | May have similar gaps | NOT STARTED |

### Rationale for Option B

1. **Uses currently-supported features**: All operations fully supported by adapter
2. **Tests meaningful workflows**: State transitions, idempotency, data visibility
3. **Avoids silent-ignore issues**: No **kwargs parameter problems
4. **Aligns with goal**: "Test-case correctness judgment" not raw execution volume
5. **Research novelty**: Sequence testing is underexplored for vector DBs

### Sequence Test Design

11 cases (6 primary, 3 calibration, 2 exploratory):

| Case ID | Sequence | State Property |
|---------|----------|----------------|
| seq-001 | create → insert → search → delete → delete | Delete idempotency |
| seq-002 | create → insert → search (no index) → build_index → search | Index state dependency |
| seq-003 | create → insert → search → delete → search | Deleted entity visibility |
| seq-004 | create → insert → search → drop → search | Post-drop state bug |
| seq-005 | create → load → insert → search | Load-insert-search visibility |
| seq-006 | create → insert (multi) → delete (partial) → delete → search | Multi-delete state consistency |
| cal-seq-001 | create → insert → build_index → load → search → drop | Known-good lifecycle |
| cal-seq-002 | create → insert → create (duplicate) → drop | Duplicate creation idempotency |
| cal-seq-003 | create → insert → search → drop | Basic insert-search |
| exp-seq-001 | create → search (empty) → drop | Empty collection search |
| exp-seq-002 | create → delete (non-existent) → insert → search → drop | Delete non-existent entity |

### Adapter Safety Verification

All operations used are **fully supported** and **safe from adapter artifacts**:

| Operation | Adapter Support | Safe from Artifacts |
|-----------|----------------|---------------------|
| create_collection | ✅ Fully supported | Yes |
| insert | ✅ Fully supported | Yes |
| search | ✅ Fully supported | Yes |
| delete | ✅ Fully supported | Yes |
| drop_collection | ✅ Fully supported | Yes |
| build_index | ✅ Supported (with nlist=128) | Yes - standard params used |
| load | ✅ Fully supported | Yes |

---

## R3 Framework Implementation

### Components Implemented

1. **Sequence Templates**: `casegen/templates/r3_sequence_state.yaml`
   - 11 multi-step sequence test cases
   - State property definitions
   - Expected behavior annotations

2. **Execution Script**: `scripts/run_r3_sequence.py`
   - Multi-step sequence execution
   - Post-run classification
   - Evidence collection

3. **Safety Mechanisms**:
   - `--require-real` flag (prevents silent fallback)
   - Explicit environment verification
   - Clear adapter status reporting
   - Metadata tracking (requested vs. actual adapter)

### Mock Dry-Run Results

**Run ID**: r3-sequence-r3-sequence-main-20260309-175203
**Date**: 2026-03-09
**Adapter**: Mock (Milvus connection failed - silent fallback)

### Framework Validation: ✅ SUCCESS

| Component | Status | Evidence |
|-----------|--------|----------|
| Sequence execution framework | ✅ Working | All 11 sequences executed |
| Multi-step test execution | ✅ Working | 2-6 step sequences completed |
| Template parsing (YAML) | ✅ Working | All templates parsed correctly |
| Operation routing | ✅ Working | All operations routed correctly |
| Result collection | ✅ Working | All step results captured |
| Post-run classification | ✅ Working | Classification logic executed |

### Real Campaign Status: ❌ NOT EXECUTED

| Requirement | Status | Gap |
|-------------|--------|-----|
| Real Milvus connection | ❌ NOT ESTABLISHED | Connection failed, silently fell back to mock |
| Real database behavior | ❌ NOT TESTED | Mock adapter always returns success |
| Valid issue findings | ❌ NONE CLAIMED | Cannot claim findings from mock data |

### Execution Transparency Gap

**Missing from Mock Dry-Run**:
- ❌ Docker container startup confirmation
- ❌ Milvus service status check
- ❌ Connection attempt logs (initial failure reason)
- ❌ Explicit adapter selection confirmation
- ❌ No-silent-fallback enforcement

**Problem**: The fallback to mock was silent and not clearly documented until post-run analysis.

---

## Corrected Status: R3

### Framework Implementation: ✅ COMPLETE

- Sequence testing framework implemented
- Templates defined and validated
- Execution script functional
- Mock dry-run validated framework
- Safety mechanisms added (--require-real, explicit verification)

### Real Campaign Execution: ❌ NOT COMPLETE

- No real Milvus connection established
- No real database behavior tested
- No valid issue findings to report
- Requires Milvus environment setup with transparency

---

## Regression Pack

**File**: `casegen/templates/regression_pack.yaml`

| Case ID | Type | Severity | Purpose |
|---------|------|----------|---------|
| regression-api-silent-kwargs-001 | API usability | LOW-MEDIUM | Track silent kwargs ignore issue |

**Change**: Downgraded from "validation bug" to "API usability issue" after audit.

---

## Documentation Artifacts

### Results
- R1: `results/milvus_validation_20260308_223239/` (real Milvus)
- R2: `results/milvus_validation_20260308_225412/` (real Milvus)
- R3: `results/r3-sequence-r3-sequence-main-20260309-175203/` (MOCK DRY-RUN ONLY)

### Issue Packages
- `docs/issues/ISSUE_PACKAGE_silent_kwargs_ignore.md` - Ready for external filing (LOW-MEDIUM severity)

### Test Templates
- `casegen/templates/r1_core.yaml` - 10 R1 cases
- `casegen/templates/r2_param_validation.yaml` - 11 R2 cases
- `casegen/templates/r3_sequence_state.yaml` - 11 R3 cases (framework ready)
- `casegen/templates/regression_pack.yaml` - Regression cases

### Campaign Configs
- `campaigns/r1_milvus_core.yaml`
- `campaigns/r2_param_validation.yaml`

### Key Documentation
- `docs/NEXT_SESSION_START_HERE.md` - Current project status
- `docs/R3_DECISION_STATUS.md` - R3 decision record
- `docs/R3_MOCK_DRY_RUN_REPORT.md` - Corrected mock dry-run report
- `docs/R3_CORRECTIONS_SUMMARY.md` - Correction record
- `docs/tooling_gaps/R3_PARAMETER_SUPPORT_AUDIT.md` - Adapter audit
- `docs/plans/R3_REDESIGNED.md` - Option B design

---

## Option A Status: POSTPONED (Not Abandoned)

**Future Work Required**:
1. Enhance MilvusAdapter to support custom index_params
2. Enhance MilvusAdapter to support custom search_params
3. Verify which Collection parameters are actually supported
4. Re-audit after adapter changes
5. Then proceed with original R3 parameter validation design

**Timeline**: After Option B real execution completes

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

### R3 Framework Criteria
| Criterion | Target | Actual | Status |
|-----------|--------|--------|--------|
| Framework implemented | Yes | Yes | ✅ |
| Templates defined | 11 | 11 | ✅ |
| Mock dry-run | Yes | Yes | ✅ |
| Real campaign | Yes | NO | ❌ |

---

## Key Learnings

### From R1 + R2

1. **Pre-submission audit is essential**: Verification against actual API documentation revealed the issue was different than initially classified
2. **Tool artifacts matter**: param-dtype-001 appeared to be a bug but was a tooling gap
3. **API signature analysis**: Checking `inspect.signature()` revealed **kwargs pattern, not a validation bug
4. **Reproducibility matters**: Finding reproduced across 2 campaigns, but interpretation was corrected
5. **Severity assessment matters**: Initial classification as HIGH severity bug was incorrect; corrected to LOW-MEDIUM API usability issue

### From R3 Framework Development

1. **Silent fallback is dangerous**: Mock fallback was not prominent in output
2. **Framework validation ≠ campaign success**: Must distinguish clearly
3. **Issue-ready claims require real data**: Mock findings are not real findings
4. **Environment transparency is required**: Must show Milvus is running before claiming real results

---

## Phase 1 Completion Summary

### Completed
- ✅ Milestone 1 (Prototype Level) - FINALIZED
- ✅ R1 Campaign - 10 cases executed (real Milvus)
- ✅ R2 Campaign - 11 cases executed (real Milvus)
- ✅ Tool workflow validated
- ✅ Pre-submission audit process established
- ✅ Regression pack established
- ✅ Issue package ready
- ✅ R3 Framework implemented
- ✅ R3 Mock dry-run completed

### Pending
- ❌ Real R3 Campaign - NOT YET EXECUTED
- ⏸️ Option A (Adapter Enhancement) - POSTPONED

---

## Critical Reminders

### For Next Session

1. **REAL R3 HAS NOT BEEN EXECUTED**
   - Only framework validation completed via mock dry-run
   - No real Milvus behavior tested
   - No valid issue findings from R3

2. **ENVIRONMENT TRANSPARENCY REQUIRED**
   - Must show Milvus is running before real R3
   - Must use `--require-real` flag
   - Must capture real environment evidence

3. **FINDINGS CLASSIFICATION**
   - Only R1 + R2 findings are real (API silent-ignore usability issue)
   - R3 findings from mock dry-run are NOT real findings
   - Issue-ready claims require real database execution

---

## Metadata

- **Checkpoint Date**: 2026-03-09
- **Phase**: 1 Complete (Results Production Phase 1)
- **Milestone 1**: Finalized (Prototype Level)
- **R1 Status**: Complete (real Milvus)
- **R2 Status**: Complete (real Milvus)
- **R3 Framework Status**: Complete
- **R3 Real Campaign Status**: NOT EXECUTED
- **Primary Finding**: API silent-ignore usability issue (LOW-MEDIUM severity)
- **Option A**: Postponed (not abandoned)
- **Option B**: Framework ready, real execution pending

---

**END OF PHASE 1 CHECKPOINT**

Next: See `docs/NEXT_SESSION_REAL_R3_PLAN.md` for real R3 execution plan.
