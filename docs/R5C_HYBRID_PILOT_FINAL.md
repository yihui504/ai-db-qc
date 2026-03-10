# R5C-HYBRID PILOT: Final Design (Ready for Execution)

**Date**: 2026-03-10
**Phase**: R5C-Hybrid Pilot (Execution Ready)
**Status**: Final Design - Approved for Execution

---

## Final Oracle Summary

### HYB-001: Filter Pre-Application
**Oracle**: All results must satisfy filter criteria
**Check**: `satisfies_filter(result.scalar_fields, filter_criteria)`
**Classification**: BUG if violation

### HYB-002: Filter-Result Consistency (CORRECTED)
**Oracle**:
1. All returned entities satisfy filter
2. Distances are monotonically increasing within filtered subset
**Check**:
```python
# Check 1: Filter satisfaction
for result in results:
    assert satisfies_filter(result['scalar_fields'], filter_criteria)

# Check 2: Distance monotonicity (within filtered entities)
for i in range(len(results) - 1):
    assert results[i]['distance'] <= results[i+1]['distance']
```
**Classification**: BUG if violation

### HYB-003: Empty Filter Result Handling
**Oracle**: Results must be empty when filter matches nothing
**Check**: `len(results) == 0` when filter matches zero entities
**Classification**: BUG if violation, ALLOWED_DIFFERENCE for error variance

---

## Final Deterministic Datasets

### Dataset 1: "Vector Trap" for HYB-001 (15 entities)

**Purpose**: Test whether entities with wrong filter values are correctly excluded, even with similar vectors

**Query Vector**: `[0.0, 0.0, 0.0, ...]`

**Entities**:
```
ID  Color  Vector (128D, first 8 shown)
1   red    [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, ...]  (exact match to query)
2   blue   [0.0001, 0.0001, 0.0001, 0.0001, 0.0001, 0.0, ...]  (nearly identical!)
3   red    [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, ...]
4   red    [0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.4, ...]
...
15  red    [1.4, 2.8, 4.2, 5.6, 7.0, 8.4, 9.8, ...]
```

**Filter**: `color == 'red'`
**Query**: Entity 1's vector (exact match)
**top_k**: 10

**Expected**:
- Entity 2 (blue) MUST be excluded (violates filter despite vector similarity)
- All results must have `color == 'red'`

---

### Dataset 2: "Controlled Axis" for HYB-002 (12 entities, FULLY DETERMINISTIC)

**Purpose**: Test distance monotonicity and filter satisfaction in filtered search

**Query Vector**: `[0.0, 0.0, 0.0, ...]`

**Entities** (placed on x-axis for deterministic distances):
```
ID  Color  Vector (128D, first 4 shown)        Distance to Query
1   red    [0.0, 0.0, 0.0, ...]              0.0   (exact match)
2   red    [0.1, 0.0, 0.0, ...]              0.1
3   blue   [0.2, 0.0, 0.0, ...]              0.2
4   red    [0.3, 0.0, 0.0, ...]              0.3
5   red    [0.5, 0.0, 0.0, ...]              0.5
6   blue   [0.7, 0.0, 0.0, ...]              0.7
7   red    [0.9, 0.0, 0.0, ...]              0.9
8   red    [1.1, 0.0, 0.0, ...]              1.1
9   blue   [1.3, 0.0, 0.0, ...]              1.3
10  red    [1.5, 0.0, 0.0, ...]              1.5
11  red    [1.7, 0.0, 0.0, ...]              1.7
12  blue   [1.9, 0.0, 0.0, ...]              1.9
```

**Filtered Subset** (color='red'): {1, 2, 4, 5, 7, 8, 10, 11}
**Filtered Subset Sorted by Distance**: [1(0.0), 2(0.1), 4(0.3), 5(0.5), 7(0.9), 8(1.1), 10(1.5), 11(1.7)]

**Test**: Search with `filter="color == 'red'"`, `top_k=5`

**Expected Behavior**:
- All results must satisfy `color == 'red'`
- Distances must be monotonically increasing
- Results should be from filtered subset, ordered by distance
- No requirement to match exact top-5 list (ANN approximation allowed)

---

### Dataset 3: "Top-K Truncation" for HYB-001 (NEW TEST)

**Purpose**: Test whether system correctly returns full filtered top-k when filtered subset is smaller than top_k

**Query Vector**: `[0.0, 0.0, 0.0, ...]`

**Entities**:
```
ID  Color  Vector (128D)                    Distance
1   red    [0.0, 0.0, 0.0, ...]              0.0
2   red    [0.1, 0.0, 0.0, ...]              0.1
3   red    [0.2, 0.0, 0.0, ...]              0.2
4   blue   [0.3, 0.0, 0.0, ...]              0.3
5   red    [0.4, 0.0, 0.0, ...]              0.4
6   red    [0.5, 0.0, 0.0, ...]              0.5
...
15  blue   [1.4, 0.0, 0.0, ...]              1.4
```

**Filter**: `color == 'red'`
**Filtered Subset**: {1, 2, 3, 5, 6, ...} (only 3 entities!)
**top_k**: 10

**Expected Behavior** (CORRECT):
- System searches within filtered subset (not just top-k from ANN)
- Returns all 3 red entities (full filtered top-k)
- Does NOT return 7 blue entities to fill top_k=10
- Result count = 3 (all entities satisfying filter)

**Incorrect Behavior** (BUG):
- System returns 10 entities (7 blue + 3 red) to fill top_k
- Filtering applied after top-k truncation

---

### Dataset 4: "Impossible Filter" for HYB-003 (10 entities)

**Purpose**: Test empty filter result handling

**Entities**:
```
ID  Color  Vector
1   red    [random1]
2   red    [random2]
...
10  red    [random10]
```

**Filter**: `color == 'blue'` (impossible)
**Query**: Any vector

**Expected**: Empty results (0 entities)

---

## Test Case Summary

| Contract | Test Cases | Dataset | Bug Yield |
|----------|------------|---------|------------|
| **HYB-001** | 6 tests | Dataset 1, 3 | CRITICAL |
| **HYB-002** | 4 tests | Dataset 2 | HIGH |
| **HYB-003** | 4 tests | Dataset 4 | MEDIUM |
| **TOTAL** | **14 tests** | 4 datasets | |

---

## Test Case Specifications

### HYB-001 Test Cases (6 tests)

1. **exclusion_basic**: Filter `color='red'`, ensure no blues appear
2. **exclusion_similarity_trap**: Entity with wrong color but nearly identical vector must be excluded
3. **exclusion_multiple_filters**: `color='red' AND status='active'`
4. **exclusion_set_membership**: `color IN ['red', 'green']`
5. **exclusion_null_filter**: `field IS NULL` handling
6. **truncation_full_filtered_topk**: top_k=10, only 3 red entities exist (Dataset 3)

### HYB-002 Test Cases (4 tests)

1. **consistency_filter_satisfaction**: All results must satisfy filter
2. **consistency_distance_monotonicity**: Distances monotonically increasing
3. **consistency_different_topk**: Test with top_k=3, 5, 8
4. **consistency_exact_reference**: Compare with exact ground truth (ALLOWED_DIFFERENCE)

### HYB-003 Test Cases (4 tests)

1. **empty_impossible_filter**: All red entities, filter for blue
2. **empty_collection**: Empty collection + any filter
3. **empty_null_filter**: Filter on null field
4. **empty_contradictory**: `color='red' AND color='blue'`

---

## Execution Plan

**Phase 1: Dataset Generation** → Create 4 deterministic datasets
**Phase 2: Test Generation** → Generate 14 test cases
**Phase 3: Milvus Execution** → Execute all tests on real Milvus
**Phase 4: Oracle Evaluation** → Evaluate with corrected oracles
**Phase 5: Pilot Report** → Document findings and recommendations

---

**Status**: **READY FOR EXECUTION**
**Total Tests**: 14
**Datasets**: 4 deterministic datasets
**Target**: Real Milvus database
