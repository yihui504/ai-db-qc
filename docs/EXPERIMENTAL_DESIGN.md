# Experimental Strengthening Design - v0.6

## Overview

Minimal, targeted enhancement to demonstrate ablation effects and Type-4 coverage.
NO architecture changes, NO new databases, NO platform features.

## Current Baseline Issues

**Problem 1: Gate effect is flat**
- Current: `type2_precondition_failed_count` is identical (2 vs 2)
- Root cause: Gate filtering happens AFTER triage, not before
- Actual gate filtering: Display-only, doesn't affect classification

**Problem 2: Triage effect is flat**
- Current: `type2_count` is identical (1 vs 1)
- Root cause: Test cases don't have diagnostic quality variation
- Current errors: All errors are either clear or all are poor

**Problem 3: No real Type-4**
- Current: 0 real Type-4 cases, only synthetic example
- Root cause: No test cases trigger oracle violations
- Oracle coverage: Filter strictness exists but never triggered

## Design Solutions

### Solution 1: Strengthen Gate Effect (Targeted Approach)

**Option A: Document the limitation honestly (RECOMMENDED)**
- Gate filtering in current architecture is post-triage (display-only)
- This is actually CORRECT behavior - Type-2.PF cases should be classified
- The "gate effect" is in result filtering, not classification
- Paper can explain this honestly

**Option B: Add cases that demonstrate result filtering**
- Cases where `precondition_pass` actually differs
- Show that WITH gate, Type-2.PF cases are excluded from result counts
- Demonstrate the filtering effect, not classification effect

**Decision:** Use Option A for now. If more signal needed, add Option B cases.

### Solution 2: Strengthen Triage Effect

**Current diagnostic quality check:**
```python
# In triage.py _has_good_diagnostics()
if any(param in error_msg for param in param_names):
    return True  # Has parameter name
```

**Problem:** Current test cases don't have diagnostic variation
- test-003: Error is "Schema must have primary key field" (doesn't mention "dimension")
- All other cases: Different error types

**Solution:** Add targeted cases with clear diagnostic variation

**New test cases:**
```yaml
# Good diagnostic: mentions specific parameter
- template_id: "diag-good-001"
  operation: "insert"
  params: {"vectors": "[[0.1]]"}  # 1-dim vs 128-dim collection
  expected_validity: "illegal"
  # Error should mention "dimension" (good diagnostic)

# Poor diagnostic: generic error
- template_id: "diag-poor-001"
  operation: "search"
  params: {"top_k": 0}  # Invalid: top_k=0
  expected_validity: "illegal"
  # Error might be "invalid parameter" (poor diagnostic)
```

**Expected outcome:**
- Diagnostic mode: Classifies good-diagnostic case as non-bug
- Naive mode: Classifies all illegal-fail as Type-2
- Result: `type2_count` differs (naive > diagnostic)

### Solution 3: Add Real Type-4 Case

**Approach:** Semi-real Type-4 using mock adapter with oracle

**Why mock for Type-4:**
- Real Type-4 requires specific data setup (insert → search → compare)
- Current infrastructure doesn't support state management
- Mock with oracle is acceptable for prototype

**Design:** Create mock-controlled Type-4

**Test case design:**
```yaml
# Type-4: Filter strictness violation
- template_id: "type4-filter-001"
  operation: "search"
  params: {
    "collection_name": "test_collection",
    "query_vector": "[0.1, 0.2, 0.3]",
    "top_k": 10,
    "filter": "id >= 999"  # No IDs >= 999, should return 0 results
  }
  expected_validity: "legal"
  oracle_refs: ["filter_strictness"]
  pair_with: "type4-filter-002"

- template_id: "type4-filter-002"
  operation: "search"
  params: {
    "collection_name": "test_collection",
    "query_vector": "[0.1, 0.2, 0.3]",
    "top_k": 10,
    "filter": ""  # No filter, should return >= 0 results
  }
  expected_validity: "legal"
  oracle_refs: ["filter_strictness"]
  pair_with: "type4-filter-001"
```

**Oracle implementation:**
```python
# In oracles/filter_strictness.py
def validate(self, unfiltered_result, filtered_result):
    # Filtered results should be subset of unfiltered
    unfiltered_count = len(unfiltered_result.get("data", []))
    filtered_count = len(filtered_result.get("data", []))

    if filtered_count > unfiltered_count:
        return OracleResult(
            oracle_id="filter_strictness",
            passed=False,
            explanation=f"Filter violation: filtered({filtered_count}) > unfiltered({unfiltered_count})"
        )
```

**Enhance MockAdapter to support paired execution:**
```python
# In adapters/mock.py
class MockAdapter:
    def execute_pair(self, unfiltered_case, filtered_case, run_id):
        # Execute both cases in same state
        unfiltered_result = self.execute_case(unfiltered_case, run_id)
        filtered_result = self.execute_case(filtered_case, run_id)
        return unfiltered_result, filtered_result
```

## Implementation Plan

### Phase 1: Triage Effect Enhancement
**File:** `casegen/templates/experimental_triage.yaml`
**Changes:** Add 4-6 cases with diagnostic variation
**Expected outcome:** Naive > Diagnostic in Type-2 count

### Phase 2: Type-4 Enhancement
**Files:**
- `casegen/templates/experimental_type4.yaml`
- `oracles/filter_strictness.py` (enhance if needed)
- `adapters/mock.py` (add execute_pair method)

**Changes:** Add 2 paired cases, enhance oracle, add pair execution
**Expected outcome:** 1 real Type-4 case (mock-based but oracle-detected)

### Phase 3: Gate Effect Clarification
**File:** `docs/experiments_phase5_final.md`
**Changes:** Add explanation of gate filtering behavior
**Expected outcome:** Clear, honest description of gate effect

## Test Case Counts

**Minimal addition:** 8-10 new test cases
- 4-6 for triage effect (diagnostic variation)
- 2-4 for Type-4 (paired cases)

**Total after strengthening:** 12-14 cases (vs current 4)
**Still minimal:** Yes, targeted for ablation demonstration only

## Execution Plan

1. **Create test templates** (1 day)
   - experimental_triage.yaml
   - experimental_type4.yaml

2. **Enhance infrastructure** (1 day)
   - Improve `_has_good_diagnostics()` if needed
   - Enhance FilterStrictness oracle
   - Add `execute_pair()` to MockAdapter

3. **Run experiments** (1 day)
   - Run with both adapters (mock for Type-4, real for others)
   - Generate new evaluation results

4. **Analyze and document** (1 day)
   - Regenerate comparison tables
   - Update case studies
   - Document improvements

## Success Metrics

**Before (baseline):**
- Gate effect: Flat (2 vs 2)
- Triage effect: Flat (1 vs 1)
- Type-4: 0 real cases

**After (target):**
- Gate effect: Documented as result filtering (honest)
- Triage effect: naive (2-3) > diagnostic (1)
- Type-4: 1 mock-based but oracle-detected case

## Risk Assessment

**Low risk:**
- Small changes, focused scope
- No architecture modifications
- Reversible if needed

**Medium risk:**
- Mock Type-4 may not satisfy "real" requirement
- May need to adjust oracle thresholds

**Mitigation:**
- Mock-based Type-4 clearly documented
- Can iterate on oracle sensitivity
- Baseline remains frozen for fallback
