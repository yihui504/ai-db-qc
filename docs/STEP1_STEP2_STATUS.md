# Step 1 Complete: Repository Organization / Milestone Freeze

## ✅ Baseline v0.5.0-phase5-baseline FROZEN

### Commits Made (v1.2b branch)
1. `797089e` - Fix(phase5.3): metrics consistency and taxonomy alignment
2. `0f65a5b` - Docs(phase5.3): completion reports and comprehensive case studies
3. `bc900b6` - Docs(baseline): baseline reference and freeze plan

### Baseline Tag Created
- **Tag:** `v0.5.0-phase5-baseline`
- **Annotated:** Full milestone description
- **Status:** Frozen reference for paper drafting

### Branch Structure
```
v1.2b (baseline branch) ─── v0.5.0-phase5-baseline (tag)
                                         │
                                         │ (frozen reference)
                                         │
v0.6-experimental-strengthening ────────┘ (current branch)
```

### Baseline Reference Documentation
- **File:** `docs/BASELINE_v0.5.0_REFERENCE.md`
- **Usage:** Paper drafting reference point
- **Artifacts:** Use runs matching IDs in `docs/experiments_phase5.3_summary.md`

---

## Step 2: Experimental Strengthening Design Complete

### Design Document Created
**File:** `docs/EXPERIMENTAL_DESIGN.md`

### Three Target Goals Addressed

#### Goal 1: Gate Effect Strengthening
**Approach:** Honest documentation over artificial signal
- Current architecture: Gate filtering is post-triage (display-only)
- This is CORRECT behavior - Type-2.PF should be classified
- Paper will explain this honestly
- **Alternative (if needed):** Add cases demonstrating result filtering

#### Goal 2: Triage Effect Strengthening
**Approach:** Diagnostic quality variation test cases

**Test template created:** `casegen/templates/experimental_triage.yaml`

**Cases added:**
- **Good diagnostic (3 cases):**
  - `diag-good-dim`: Wrong dimension - should mention "dimension"
  - `diag-good-topk`: top_k=0 - should mention "top_k"
  - `diag-good-metric`: Invalid metric - should list valid metrics

- **Poor diagnostic (2 cases):**
  - `diag-poor-generic`: Generic "invalid parameter"
  - `diag-poor-vague`: Vague "operation failed"

- **Edge cases (2 cases):**
  - `diag-edge-empty`: Empty vectors
  - `diag-edge-null`: Null query vector

**Infrastructure enhancement:** `pipeline/triage.py`
- Enhanced `_has_good_diagnostics()` with:
  - Parameter context checking
  - Actionable guidance detection
  - Technical term recognition
  - Exception type classification

**Expected outcome:**
- Diagnostic mode: Classifies good-diagnostic cases as non-bug
- Naive mode: Classifies all illegal-fail as Type-2
- **Result:** `type2_count` should differ (naive > diagnostic)

#### Goal 3: Type-4 Coverage
**Approach:** Semi-real Type-4 using MockAdapter with oracle

**Test template created:** `casegen/templates/experimental_type4.yaml`

**Cases added:**
- **Type-4 Filter Strictness (2 paired cases):**
  - `type4-filter-unfiltered`: Unfiltered search (10 results expected)
  - `type4-filter-filtered`: Filtered with impossible condition (0 results)
  - Oracle validates: `filtered ⊆ unfiltered`

- **Type-4 Write-Read Consistency (1 case):**
  - `type4-write-read`: Insert operation
  - Oracle validates: Written data can be read back

- **Type-4 Monotonicity (2 paired cases):**
  - `type4-monotonic-5`: Top-K=5 search
  - `type4-monotonic-10`: Top-K=10 search
  - Oracle validates: K10 >= K5 (monotonicity)

**Infrastructure enhancements:**
1. **Executor:** Added `execute_pair()` method for paired execution
2. **MockAdapter:** Enhanced with filter support
   - Added `filter_reduction_factor` parameter
   - Improved filter semantics in execute()
   - Added `_current_data` caching for oracle validation

---

## Implementation Status

### Files Modified
1. `pipeline/triage.py` - Enhanced diagnostic quality assessment
2. `pipeline/executor.py` - Added paired execution support
3. `adapters/mock.py` - Enhanced filter semantics

### Files Created
1. `docs/MILESTONE_v0.5.0_FREEZE_PLAN.md` - Freeze plan
2. `docs/BASELINE_v0.5.0_REFERENCE.md` - Baseline reference
3. `docs/EXPERIMENTAL_STRENGTHENING.md` - Experimental plan
4. `docs/EXPERIMENTAL_DESIGN.md` - Experimental design
5. `casegen/templates/experimental_triage.yaml` - Triage test cases
6. `casegen/templates/experimental_type4.yaml` - Type-4 test cases

### Next Steps to Execute

1. **Commit experimental changes** to v0.6-experimental-strengthening branch
2. **Run experimental evaluations** with new test cases
3. **Generate updated comparison tables** showing ablation effects
4. **Update case studies** with new examples
5. **Document improvements** in completion report

---

## Current State

**Branch:** `v0.6-experimental-strengthening`
**Baseline:** `v0.5.0-phase5-baseline` (frozen)
**Status:** Design complete, infrastructure ready, ready to execute experiments

**Constraints checklist:**
- ✅ NO architecture expansion (only enhanced existing components)
- ✅ NO new databases (still Milvus-only)
- ✅ NO platform features (only diagnostic accuracy improvements)
- ✅ Small, targeted enhancement (3 modules modified, 2 templates added)

**Ready for:** Experiment execution and validation of ablation effects.
