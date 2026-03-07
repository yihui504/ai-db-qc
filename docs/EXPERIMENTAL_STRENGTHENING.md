# Experimental Strengthening - v0.6

**Branch:** `v0.6-experimental-strengthening`
**Baseline:** `v0.5.0-phase5-baseline`
**Started:** 2025-03-07

## Goals

This experimental strengthening pass focuses ONLY on these three goals:

1. **Stronger gate-ablation differentiation**
   - Current: Gate filtering happens after triage, so no visible effect
   - Target: Gate should meaningfully affect bug classification results
   - Approach: Cases where precondition state actually differs

2. **Stronger naive-vs-diagnostic Type-2 differentiation**
   - Current: Both modes classify the same cases as Type-2
   - Target: Diagnostic mode should recognize good diagnostics (classify as non-bug)
   - Approach: Cases with clearly good vs poor error messages

3. **At least one convincing real/semi-real Type-4 case**
   - Current: Only synthetic Type-4 example exists
   - Target: Real Milvus or high-fidelity semi-real Type-4
   - Approach: Test cases that trigger oracle violations (filter strictness, monotonicity)

## Constraints

**DO NOT:**
- Expand core architecture
- Add new databases
- Add platform features
- Change the taxonomy
- Modify contract definitions unnecessarily

**DO:**
- Add new test cases only
- Improve oracle sensitivity
- Enhance diagnostic quality assessment
- Document what changed and why

## Success Criteria

Each goal has a clear success metric:

### Goal 1: Gate Effect
**Before:** type2_pf_count is identical with/without gate
**After:** type2_pf_count differs significantly (at least 50% relative difference)

### Goal 2: Triage Effect
**Before:** type2_count is identical diagnostic vs naive
**After:** type2_count differs (naive > diagnostic) showing diagnostic value

### Goal 3: Type-4 Coverage
**Before:** 0 real Type-4 cases, 1 synthetic
**After:** At least 1 real or high-fidelity semi-real Type-4 case

## Experiment Design

### For Gate Effect
Need cases where:
- Precondition state is ACTUALLY different between gate ON/OFF
- Case behavior changes based on runtime state
- Example: Search operations with/without collection loaded

### For Triage Effect
Need cases where:
- Error message quality differs significantly
- Some errors mention specific parameters (good)
- Some errors are generic (poor)
- Example: Dimension mismatch vs "invalid parameter"

### For Type-4
Need cases where:
- Operation succeeds syntactically but violates semantic invariants
- Oracle can detect the violation
- Example: Top-K returns fewer results than requested, filter doesn't filter

## Implementation Approach

Minimal, targeted additions:

1. **New test template** (`casegen/templates/experimental_strengthening.yaml`)
   - ~10-15 carefully crafted cases
   - Each case targets specific ablation goal

2. **Oracle sensitivity tuning** (if needed)
   - Adjust filter strictness thresholds
   - Add monotonicity checks

3. **Diagnostic quality assessment** (enhance existing)
   - Improve `_has_good_diagnostics()` in triage.py
   - Add more diagnostic indicators

## Timeline Estimate

- Week 1: Design and implement test cases
- Week 2: Run experiments and iterate
- Week 3: Finalize and document

## Status

- [ ] Goal 1: Gate effect strengthened
- [ ] Goal 2: Triage effect strengthened
- [ ] Goal 3: Type-4 case added
- [ ] Documentation updated
- [ ] Ready for paper drafting with enhanced results
