# R1 + R2 Cumulative Results Summary

**Period**: 2026-03-08
**Campaigns**: 2 (R1, R2)
**Total Cases**: 21
**Status**: ✅ Phase 1 COMPLETE - First results-driven production phase validated

---

## Executive Summary

The first results-driven production phase (R1 + R2) successfully validated the AI-DB-QC tool and produced **2 high-confidence Type-1 findings** within the metric_type validation weakness family. Both campaigns met minimum success criteria and established a reproducible workflow for automated bug discovery.

---

## Campaign Overview

| Campaign | Focus | Cases | High-Confidence Findings | Status |
|----------|-------|-------|--------------------------|--------|
| **R1** | Core High-Yield | 10 | 1 (cb-bound-005) | ✅ Complete |
| **R2** | Parameter Validation | 11 | 1 (param-metric-001) | ✅ Complete |
| **Total** | - | 21 | 2 (same family) | ✅ Phase 1 COMPLETE |

---

## High-Confidence Findings

### Finding 1: Invalid metric_type Enum Value

| Attribute | Value |
|-----------|-------|
| **ID** | metric-001 / cb-bound-005 |
| **Type** | Type-1 (illegal operation succeeded) |
| **Severity** | MEDIUM |
| **Discovery** | R1, previously in differential v3 |
| **Description** | `metric_type="INVALID_METRIC"` accepted without error |

### Finding 2: Empty metric_type String

| Attribute | Value |
|-----------|-------|
| **ID** | metric-002 / param-metric-001 |
| **Type** | Type-1 (illegal operation succeeded) |
| **Severity** | MEDIUM |
| **Discovery** | R2 |
| **Description** | `metric_type=""` (empty string) accepted without error |

**Note**: Both findings represent the same underlying weakness (lack of metric_type validation) and should be filed as a unified issue family.

---

## Exploratory Observations

| Finding | Type | Confidence | Notes |
|---------|------|------------|-------|
| Lowercase "l2" accepted | Type-1 | LOW | May be by design (case-insensitive API) |
| cb-bound-002/003 | Type-2 | LOW | Error mentions parameter, missing valid range |
| cb-bound-006 | NOT A BUG | - | pymilvus Collection() is idempotent by design |

**False Positives Cleaned**: 4 cases
- param-num-002/004: Had good diagnostics with range information
- param-dtype-001: Tool artifact (adapter ignores dtype parameter)
- exp-002: Error message was specific ("field nonexistent_field not exist")

---

## Tool Validated

The R1 + R2 phase successfully validated the end-to-end workflow:

| Component | Status | Notes |
|-----------|--------|-------|
| Case generation | ✅ Working | Templates → case packs |
| Validation | ✅ Working | Cases executed against real database |
| Precondition evaluation | ✅ Working | Runtime context detected correctly |
| Triage | ✅ Working | Taxonomy-aware classification working |
| Export | ✅ Working | 5 validate artifacts produced consistently |
| Vector parsing | ✅ Fixed during R1 | String-to-list parsing added |
| Template substitution | ✅ Fixed during R1 | {id} placeholder issue resolved |

---

## Key Improvements Made

**During R1**:
1. Fixed template substitution ({id} placeholder)
2. Fixed runtime context (index built/loaded)
3. Fixed vector parsing (string-to-list conversion)
4. Fixed triage TypeError in _has_good_diagnostics

**During R2**:
1. Documented tooling gap (dtype parameter not supported)
2. Organized findings as issue family (not separate bugs)
3. Removed false positives (good diagnostics)
4. Downgraded ambiguous cases to exploratory

---

## Success Criteria Assessment

### R1 Criteria
| Criterion | Target | Actual | Status |
|-----------|--------|--------|--------|
| Cases executed | 10 | 10 | ✅ |
| High-confidence candidates | >=1 | 1 | ✅ |
| Artifacts produced | 5 | 5 | ✅ |

### R2 Criteria
| Criterion | Target | Actual | Status |
|-----------|--------|--------|--------|
| Cases executed | 11 | 11 | ✅ |
| High-confidence candidates | >=1 | 1 | ✅ |
| Calibration cases pass | 2 | 2 | ✅ |

**Overall Phase 1**: ✅ ALL CRITERIA MET

---

## Regression Pack Established

**File**: `casegen/templates/regression_pack.yaml`

| Case ID | Original Campaign | Parameter | Invalid Value |
|---------|-------------------|-----------|---------------|
| regression-milvus-005 | R1 (cb-bound-005) | metric_type | "INVALID_METRIC" |
| regression-param-metric-001 | R2 (param-metric-001) | metric_type | "" (empty string) |

**Purpose**: These cases will be used to verify fixes and prevent regressions.

---

## Issue Filing Status

| Issue Family | Findings | Status |
|--------------|----------|--------|
| metric_type validation weakness | 2 high-confidence | Package ready, not yet filed |

**Issue Package**: `docs/issues/ISSUE_PACKAGE_metric_type_validation.md`

---

## Yield Analysis

| Metric | Value |
|--------|-------|
| **Total cases** | 21 |
| **High-confidence findings** | 2 (9.5%) |
| **Exploratory observations** | 1 (4.8%) |
| **False positives** | 4 (19%) |
| **Validly exercised** | 19 (90%) |
| **Tooling gaps identified** | 1 |

**Hit rate**: 9.5% high-confidence findings per case

---

## Key Learnings

1. **Parameter validation is selective**: metric_type has weak validation; dimension, top_k, index_type have strong validation with good diagnostics

2. **Tool artifacts matter**: param-dtype-001 appeared to be a bug but was actually a tooling gap (adapter ignored the parameter)

3. **Diagnostic quality varies**: Some errors mention valid ranges (good), others just say "illegal" (borderline)

4. **Reproducibility matters**: metric_type issue was found in 3 independent campaigns, confirming reliability

5. **Calibration is essential**: Valid value tests confirmed the tool was working correctly

---

## Phase 1 vs Phase 2 Strategy

**Phase 1 (R1 + R2)**: COMPLETE
- Validated tool workflow
- Confirmed metric_type validation weakness
- Established regression pack
- 2 high-confidence findings

**Phase 2 (R3+)**: READY TO START
- Focus: Adjacent parameter families
- Target: Collection schema params (consistency_level, replica_number)
- Expected yield: 1-3 candidates
- Goal: Expand breadth beyond metric_type

---

## Next Steps

1. **File metric_type validation issue** (when ready)
2. **Execute R3** to test adjacent parameter families
3. **Fix dtype tooling gap** before any dtype-focused campaign
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
  - R1 Summary: `docs/R1_FINAL_SUMMARY.md`
  - Issue Family: `docs/issues/METRIC_TYPE_VALIDATION_FAMILY.md`
  - R3 Proposal: `docs/plans/R3_CAMPAIGN_PROPOSAL.md`
