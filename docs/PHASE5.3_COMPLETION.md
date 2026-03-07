# Phase 5.3 Completion Report

## Status: COMPLETE

Phase 5.3 has addressed all result integrity and experiment repair requirements. Metrics are now internally consistent, case studies are complete with all bug types represented, and narratives are taxonomy-conservative.

## Deliverables

### 1. Corrected Aggregated Metrics

**File:** `runs/aggregated_metrics_phase5.3.json`

**Fix Applied:** Field name bug in `summarize_runs.py`
- **Before:** Read `case.get("input_validity", "legal")` from cases.jsonl
- **After:** Read `case.get("expected_validity", case.get("input_validity", "legal"))`
- **Impact:** `illegal_cases` now correctly counts cases with `expected_validity="illegal"`

**Verification:**
```
Run              illegal_cases  type1_count  type2_count  Consistency
baseline_mock     1             1             0            ✓ OK
baseline_real     1             0             1            ✓ OK
naive_triage_real 1             0             1            ✓ OK
no_gate_mock      1             1             0            ✓ OK
no_gate_real      1             0             1            ✓ OK
no_oracle_real    1             0             1            ✓ OK
```

All runs now pass consistency check: `illegal_cases = type1_count + type2_count`

### 2. Corrected Comparison Tables

**File:** `docs/experiments_phase5.3_summary.md`

**Table 1: Main Configuration Comparison**
| Run | Total | Precond Pass | Failures | T1 | T2 | T2.PF | T3 | T4 | Non-bug |
|---|---|---|---|---|---|---|---|---|---|
| baseline_mock | 4 | 2 | 0 | 1 | 0 | 2 | 0 | 0 | 1 |
| baseline_real | 4 | 2 | 4 | 0 | 1 | 2 | 1 | 0 | 0 |
| naive_triage_real | 4 | 2 | 4 | 0 | 1 | 2 | 1 | 0 | 0 |
| no_gate_mock | 4 | 2 | 0 | 1 | 0 | 2 | 0 | 0 | 1 |
| no_gate_real | 4 | 2 | 4 | 0 | 1 | 2 | 1 | 0 | 0 |
| no_oracle_real | 4 | 2 | 4 | 0 | 1 | 2 | 1 | 0 | 0 |

**Experiment Limitations Documented:**
- **Gate effect:** Shows flat results because gate filtering affects display, not triage counts
- **Oracle effect:** Shows `oracle_eval_count` difference (4 vs 0) but no Type-4 bugs detected
- **Triage effect:** Shows flat results because current test cases don't exercise diagnostic quality differences

### 3. Complete Case Studies

**File:** `docs/case_studies_phase5.3.md`

**Coverage:**
| Bug Type | Status | Source | Interpretation |
|---|---|---|---|---|
| Type-1 | ✓ Real | test-003 (mock) | Illegal input accepted: Illegal operation succeeded |
| Type-2 | ✓ Real | test-003 (real) | Illegal input rejected, lacks diagnostic: Illegal operation with poor diagnostic |
| Type-2.PF | ✓ Real | test-002 (real) | Expected failure (precondition not met): Contract-valid but precondition-fail |
| Type-3 | ✓ Real | test-001 (real) | Legal input failed: Legal operation failed (precondition satisfied) |
| Type-4 | ⚠ Synthetic | synthetic-type4-001 | Semantic oracle violation: Top-K=10 returned only 5 results without explanation |
| Non-bug | ✓ Real | test-001 (mock) | Expected behavior - operation succeeded as designed |

**Narrative Improvements:**
- Type-2.PF now emphasizes "Expected failure" (conservative, not alarmist)
- All narratives are taxonomy-consistent with BUG_TAXONOMY.md
- Synthetic Type-4 example clearly marked as such

### 4. Experiment Changes Explanation

**What Changed and Why:**

1. **Metrics Calculation Fix**
   - **Problem:** `illegal_cases` was always 0 despite Type-1/Type-2 bugs being present
   - **Root Cause:** Field name mismatch (`input_validity` vs `expected_validity`)
   - **Fix:** Updated `summarize_runs.py` to check both field names
   - **Impact:** All metrics now internally consistent

2. **Case Study Coverage**
   - **Problem:** Missing Type-4 and non-bug examples
   - **Solution:** Exported real examples for all present types; added synthetic Type-4
   - **Reasoning:** Current test set doesn't trigger oracle violations; Type-4 requires observable semantic violations

3. **Narrative Precision**
   - **Problem:** Type-2.PF described as "Precondition violation" (could imply bug)
   - **Fix:** Changed to "Expected failure (precondition not met)"
   - **Impact:** Emphasizes this is expected behavior, not a defect

**Why Ablation Tables Show Flat Results:**

The Phase 5 test set (4 cases) was designed for connectivity validation, not ablation demonstration. The results show:

- **Gate effect flat:** Gate filtering happens AFTER triage, so it doesn't affect bug classification counts
- **Oracle effect flat:** No Type-4 bugs in test set, so oracle has nothing to detect
- **Triage effect flat:** Current cases don't have diagnostic quality differences

**For Production Paper Results:**
- Expand test set to 100+ cases with proper state setup
- Include Type-4 triggers (filter violations, monotonicity violations)
- Include cases with good vs poor diagnostics
- Implement proper state management (collection creation, data loading, etc.)

### 5. Taxonomy Alignment Confirmation

**Formal Taxonomy Compliance:** ✓ VERIFIED

All outputs now align with `BUG_TAXONOMY.md`:

| Type | Formal Definition | Current Classification | Status |
|---|---|---|---|---|
| Type-1 | `input_validity=illegal` ∧ `observed_success=true` | test-003 (mock): illegal, success | ✓ |
| Type-2 | `input_validity=illegal` ∧ `observed_success=false` ∧ `poor_diagnostic=true` | test-003 (real): illegal, failure | ✓ |
| Type-2.PF | `input_validity=legal` ∧ `precondition_pass=false` | test-002, test-004: legal, precond=fail | ✓ |
| Type-3 | `input_validity=legal` ∧ `precondition_pass=true` ∧ `observed_success=false` | test-001 (real): legal, precond=pass, failure | ✓ |
| Type-4 | `precondition_pass=true` ∧ `observed_success=true` ∧ `oracle_fail=true` | Synthetic example | ✓ |
| Non-bug | Expected behavior, clear validation | test-001 (mock): legal, success | ✓ |

**Red-Line Enforcement:**
- ✓ Type-3 classifications require `precondition_pass=true`
- ✓ Type-4 classifications require `precondition_pass=true`
- ✓ Type-2.PF correctly marked as subtype (not top-level type)

## Summary

**Fixed Issues:**
1. ✅ Metrics consistency: Field name bug fixed, all metrics now internally consistent
2. ✅ Case study coverage: All 6 types represented (5 real, 1 synthetic)
3. ✅ Narrative precision: Conservative, taxonomy-consistent interpretations
4. ✅ Taxonomy alignment: All outputs verified against BUG_TAXONOMY.md

**Known Limitations:**
- Experiment ablation tables show flat results (by design of minimal test set)
- Type-4 is synthetic (not from actual runs due to test set limitations)
- Gate filtering affects display only, not triage counts (architectural constraint)

**Files Modified:**
1. `analysis/summarize_runs.py` - Fixed field name reading
2. `analysis/export_case_studies.py` - Fixed interpretation narratives
3. `analysis/export_case_studies_5.3.py` - Created comprehensive export
4. `docs/experiments_phase5.3_summary.md` - Regenerated tables
5. `docs/case_studies_phase5.3.md` - Complete case studies with all types

**Next Steps for Production Paper:**
- Expand test set to 100+ cases per run
- Implement proper state management infrastructure
- Add Type-4 trigger cases (filter violations, monotonicity violations)
- Add diagnostic quality variation cases
- Consider fixing gate filtering to affect triage (if needed)

---

**Date:** 2026-03-07
**Status:** Phase 5.3 COMPLETE
**Documentation:** `docs/PHASE5.3_COMPLETION.md`
