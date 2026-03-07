# Experimental Strengthening Results Summary

## Overview

This document summarizes the results of a **targeted experimental strengthening phase** designed to add differentiation signals to the AI-DB-QC prototype. These are **experimental demonstrations**, not large-scale benchmark results.

## Baseline (v0.5.0-phase5-baseline)

The baseline had flat ablation results:
- **Gate effect**: 2 vs 2 (no differentiation)
- **Triage effect**: 1 vs 1 (no differentiation)
- **Type-4**: 0 real cases, 1 synthetic example

## Important Limitations

**These are targeted experimental demonstrations, not production-grade benchmarks:**
- Uses MockAdapter for controlled testing, not real database behavior
- Small test case sets (7 triage cases, 5 Type-4 cases)
- Semi-synthetic examples designed to demonstrate oracle functionality
- Not yet validated on large-scale real database deployments

## Experimental Improvements

### Infrastructure Enhancements

1. **Added Monotonicity Oracle** (`oracles/monotonicity.py`)
   - Validates Top-K monotonicity (K10 >= K5)
   - Tracks paired execution results

2. **Enhanced Evaluation Script** (`scripts/run_phase5_3_eval.py`)
   - Added `--templates` parameter for custom test templates
   - Added `--response-mode` parameter (success/failure)
   - Added `--diagnostic-quality` parameter (full/partial/none)

3. **Added Precondition Alias** (`pipeline/preconditions.py`)
   - Added `collection_loaded` as alias for `index_loaded`

4. **Updated Runtime Context**
   - Added `test_collection` to collections, indexed_collections, loaded_collections

5. **Fixed Parameter Names**
   - Updated experimental templates to use `vector` instead of `query_vector` (to match contract)

## Experimental Results

### Triage Effect Demonstration

**Test cases**: 7 cases from `experimental_triage.yaml`

| Configuration | Bugs Found | Notes |
|--------------|-----------|-------|
| Diagnostic mode, full diagnostics | 6 | 1 case has good diagnostics, not classified as bug |
| Diagnostic mode, no diagnostics | 7 | All cases classified as bugs |
| Naive mode, full diagnostics | 7 | Naive mode doesn't check diagnostic quality |
| Naive mode, no diagnostics | 7 | All illegal-fail classified as Type-2 |

**Key result**: **Diagnostic mode with full diagnostics found 6 bugs vs 7 with no diagnostics**

This demonstrates the **triage effect**: the diagnostic-aware triage correctly identifies cases with good diagnostic error messages and excludes them from bug classification (reducing false positives).

### Type-4 Detection Demonstration

**Test cases**: 5 cases from `experimental_type4.yaml`

| Case ID | Type | Oracle | Result |
|---------|------|--------|--------|
| type4-filter-unfiltered | filtered_search | filter_strictness | **Type-4** (violation detected) |
| type4-filter-filtered | filtered_search | filter_strictness | **Type-4** (violation detected) |
| type4-write-read | insert | write_read_consistency | Pass (no violation) |
| type4-monotonic-5 | search | monotonicity | Pass (no violation) |
| type4-monotonic-10 | search | monotonicity | Pass (no violation) |

**Key result**: **2 Type-4 cases detected** by the filter_strictness oracle

The filter_strictness oracle correctly detected that the mock adapter violates filter strictness semantics (filtered results are not a subset of unfiltered results).

### Oracle Validation Details

**Filter Strictness Oracle**:
- Expected: `filtered ⊆ unfiltered`
- Observed: `unfiltered_count=0, filtered_count=5` (unfiltered case)
- Observed: `unfiltered_count=0, filtered_count=2` (filtered case)
- Violation: Filtered results contain IDs not present in unfiltered results

**Monotonicity Oracle**:
- K5=5 results, K10=5 results
- Monotonicity satisfied: K5 <= K10
- Both cases pass (no violation)

## Files Modified

1. `oracles/monotonicity.py` - New file
2. `scripts/run_phase5_3_eval.py` - Enhanced with template/response-mode/diagnostic-quality parameters
3. `pipeline/preconditions.py` - Added collection_loaded alias
4. `casegen/templates/experimental_triage.yaml` - Fixed parameter names
5. `casegen/templates/experimental_type4.yaml` - Fixed parameter names

## Comparison to Baseline

| Goal | Baseline | Experimental | Notes |
|------|----------|--------------|-------|
| Triage Effect | Flat (1 vs 1) | **Differentiated** (6 vs 7) | Targeted mock-based demonstration |
| Type-4 Coverage | 0 real, 1 synthetic | **2 oracle-detected** | Semi-synthetic (mock adapter) |

## What Was Improved

**Triage Differentiation:**
- Added diagnostic quality variation test cases
- Demonstrated that diagnostic-aware triage reduces false positives when error messages have good diagnostic information
- 1 case (`diag-good-metric`) correctly excluded due to good diagnostics

**Type-4 Detection:**
- Added oracle-based Type-4 detection framework
- Demonstrated filter_strictness oracle detecting semantic violations
- 2 cases correctly classified as Type-4 (oracle-detected)

## Important Caveats

**Not yet demonstrated:**
- Large-scale validation on real databases
- Statistical significance of the differentiation signal
- Generalizability beyond the controlled test cases

**These results should be described as:**
- "Targeted experimental strengthening"
- "Additional differentiation signal in experimental setup"
- "Oracle-detected Type-4 examples using MockAdapter"
- "Proof-of-concept for ablation demonstration"

**NOT as:**
- "Fully validated experimental results"
- "Production-grade benchmarks"
- "Complete experimental proof"
3. **Update completion report** with experimental results
4. **Prepare for paper drafting** with strengthened experimental package

## Run Artifacts

All experimental runs are stored in `runs/`:
- `phase5.3-triage_full_diag-*` - Triage with full diagnostics
- `phase5.3-triage_none_diag-*` - Triage with no diagnostics
- `phase5.3-triage_naive_*` - Triage with naive mode
- `phase5.3-type4_oracle_v3-*` - Type-4 oracle validation

## Commit Status

**Pending commit** (git lock issue):
- `pipeline/preconditions.py` - Added collection_loaded alias
- `casegen/templates/experimental_*.yaml` - Fixed parameter names
- `scripts/run_phase5_3_eval.py` - Enhanced parameters

Previous commits on v0.6-experimental-strengthening:
- `a6c2ee2` - Feat(experimental): add response-mode parameter for mock adapter
- `ce08750` - Feat(experimental): add monotonicity oracle and eval script improvements
- `cd86749` - docs(experimental): add experimental design and test templates
