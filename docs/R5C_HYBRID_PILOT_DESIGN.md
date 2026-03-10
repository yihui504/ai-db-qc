# R5C-PILOT: Hybrid Query Contract-Driven Validation

**Date**: 2026-03-10
**Phase**: R5C-Hybrid Pilot
**Framing**: Contract-family pilot (NOT full campaign, NOT KPI bug hunting)
**Status**: Design Phase - Awaiting Execution Approval

---

## Executive Summary

The R5C-Hybrid Pilot validates the contract-driven framework on **Hybrid Query contracts**, which target the complex interaction between scalar filters and vector similarity search. This family was selected based on its **higher bug-yield potential** compared to ANN contracts.

**Objective**: Evaluate whether hybrid query contracts can reveal real bugs on Milvus, and validate the framework's capability for generating high-yield filter+vector tests.

**Scope**: 3 hybrid contracts, ~12-15 focused test cases, single-database (Milvus)

---

## 1. Hybrid Contracts Included

### Contract Breakdown

| Contract ID | Contract Name | Severity | Focus |
|-------------|---------------|----------|-------|
| **HYB-001** | Filter Pre-Application | **CRITICAL** | Excluded entities must never appear in results |
| **HYB-002** | Filter-Result Consistency | **HIGH** | Filtered search must equal manual filter application |
| **HYB-003** | Empty Filter Result Handling | **HIGH** | Empty filters must return empty results |

**Total Contracts**: 3
**Total Test Cases**: ~12-15 (estimated)

### Contract Details

#### HYB-001: Filter Pre-Application (CRITICAL)
- **Statement**: Scalar filters must be applied before vector ranking
- **Violation Condition**: `excluded_entity_appears_in_results`
- **Severity**: CRITICAL - Filter violations are correctness bugs
- **Oracle Check**: `all_results_satisfy_filter`
- **Why High-Yield**: Filter correctness is a common database bug source; Milvus implements filtering as post-filter (can leak excluded entities)

#### HYB-002: Filter-Result Consistency (HIGH)
- **Statement**: Filtered search results must match unfiltered search after applying filter
- **Violation Condition**: `filtered_results != filter(unfiltered_results)`
- **Severity**: HIGH - Inconsistent filtering indicates semantic errors
- **Oracle Check**: `filtered_equals_manual_filter(unfiltered)`
- **Why High-Yield**: Tests whether filter semantics are consistent; revealed ALLOWED_DIFFERENCES in R4

#### HYB-003: Empty Filter Result Handling (HIGH)
- **Statement**: Search with filter matching no entities must return empty results
- **Violation Condition**: `non_empty_results_when_filter_matches_nothing`
- **Severity**: HIGH - Incorrect empty handling causes logical errors
- **Oracle Check**: `results_empty OR consistent_empty_handling`
- **Why High-Yield**: Edge case that reveals inconsistent error handling

---

## 2. Generation Strategies

### Strategy 1: Filter Exclusion Tests (4-5 tests)
**Target Contract**: HYB-001
**Bug Yield**: **CRITICAL** - Filter violations are high-impact bugs

**Test Cases**:
1. **Basic exclusion**: Filter `color=red`, ensure no `color=blue` entities appear
2. **Vector similarity trap**: Entity B (blue) has very similar vector to query A (red), must still be excluded
3. **Multiple filters**: `color=red AND status=active`, ensure all conditions respected
4. **Complex expression**: `color IN (red, green) AND status=active`, test set semantics
5. **Degenerate filter**: `field=NULL` handling (null filter semantics)

**Oracle**: Verify NO excluded entities appear in results

### Strategy 2: Filter Consistency Tests (3-4 tests)
**Target Contract**: HYB-002
**Bug Yield**: **HIGH** - Inconsistent filtering reveals semantic bugs

**Test Cases**:
1. **Direct comparison**: Search with filter vs. manual filter on unfiltered results
2. **Ordering preservation**: Verify relative ranking within filtered results is preserved
3. **Top-K interaction**: Ensure filter is applied before top-K limiting
4. **Null handling**: Filter on null/missing fields behavior

**Oracle**: Verify `filtered_results == filter(unfiltered_results)`

### Strategy 3: Empty Filter Edge Cases (3-4 tests)
**Target Contract**: HYB-003
**Bug Yield**: **MEDIUM** - Edge case handling errors

**Test Cases**:
1. **Impossible filter**: All entities are `color=red`, search with `color=blue`
2. **Empty collection**: Search with filter on empty collection
3. **Null filter**: Search with `field=NULL` when no nulls exist
4. **Contradictory filter**: `color=red AND color=blue` (impossible condition)

**Oracle**: Verify results are empty OR consistent error handling

### Strategy 4: Scalar Field Type Tests (2-3 tests)
**Target Contract**: HYB-001, HYB-002
**Bug Yield**: **MEDIUM** - Type-specific filter behavior

**Test Cases**:
1. **Integer field**: Filter on numeric ranges (`age > 25`)
2. **String field**: Filter on string matching (`name LIKE "A%"`)
3. **Boolean field**: Filter on boolean values (`is_active = true`)

**Oracle**: Verify filter semantics by type

---

## 3. Test Generation Summary

### Estimated Test Cases per Contract

| Contract ID | Strategy 1 | Strategy 2 | Strategy 3 | Strategy 4 | Total |
|-------------|------------|------------|------------|------------|-------|
| **HYB-001** | 4 tests | - | 1 test | 2 tests | **7 tests** |
| **HYB-002** | - | 3 tests | - | 1 test | **4 tests** |
| **HYB-003** | - | - | 3 tests | 1 test | **4 tests** |
| **TOTAL** | **4 tests** | **3 tests** | **4 tests** | **4 tests** | **15 tests** |

### Oracle Distribution

| Oracle | Tests | Classification |
|--------|-------|----------------|
| `all_results_satisfy_filter` | 7 | BUG if violated (filter_violation) |
| `filtered_equals_manual_filter` | 4 | BUG if violated (inconsistent_filtering) |
| `results_empty OR consistent_empty_handling` | 4 | BUG if violated, ALLOWED_DIFFERENCE for error handling variance |

---

## 4. Test Case Specifications

### HYB-001: Filter Pre-Application Tests

**Test hyb-001_exclusion_001: Basic Exclusion**
```
Setup:
  - Create collection with scalar field `color` (string)
  - Insert entity A: id=1, color="red", vector=[random]
  - Insert entity B: id=2, color="blue", vector=[very_similar_to_A]
  - Insert entity C: id=3, color="red", vector=[random]

Test:
  - Search query=[A.vector], filter="color == 'red'", top_k=10

Expected:
  - Results MUST contain entity A
  - Results MUST contain entity C
  - Results MUST NOT contain entity B (excluded by filter, despite vector similarity)

Oracle: all_results_satisfy_filter
Bug Yield: CRITICAL - Filter violation
```

**Test hyb-001_exclusion_002: Vector Similarity Trap**
```
Setup:
  - Create collection with scalar field `category` (string)
  - Insert entity A: id=1, category="electronics", vector=[0.1, 0.2, ...]
  - Insert entity B: id=2, category="books", vector=[0.1001, 0.2001, ...] (nearly identical)
  - Insert 98 other entities with category="electronics"

Test:
  - Search query=[A.vector], filter="category == 'electronics'", top_k=10

Expected:
  - Entity B MUST NOT appear (excluded by filter despite near-identical vector)
  - Entity A MUST appear (matches filter)
  - Top 10 must all have category="electronics"

Oracle: all_results_satisfy_filter
Bug Yield: CRITICAL - Tests whether ANN post-filter leaks excluded entities
```

### HYB-002: Filter-Result Consistency Tests

**Test hyb-002_consistency_001: Direct Comparison**
```
Setup:
  - Create collection with scalar field `status` (string)
  - Insert 100 entities with varying status values

Test Sequence:
  1. Search unfiltered: query=[random], filter="", top_k=10 → results_unfiltered
  2. Search filtered: query=[same_random], filter="status == 'active'", top_k=10 → results_filtered
  3. Extract active entities from unfiltered: results_manual = filter(results_unfiltered, status='active')

Expected:
  - results_filtered MUST equal results_manual (same IDs, same order)
  - Ranking within filtered results MUST be preserved

Oracle: filtered_equals_manual_filter
Bug Yield: HIGH - Tests filter semantic consistency
```

### HYB-003: Empty Filter Result Tests

**Test hyb-003_empty_001: Impossible Filter**
```
Setup:
  - Create collection with scalar field `color` (string)
  - Insert 50 entities: all have color="red"

Test:
  - Search query=[random], filter="color == 'blue'", top_k=10

Expected:
  - Results MUST be empty (0 results)
  - No error or crash

Oracle: results_empty
Bug Yield: HIGH - Tests impossible filter handling
```

---

## 5. Dataset and Filter Design

### Scalar Field Schemas

1. **String Field**: `color` (red, blue, green, yellow)
2. **Integer Field**: `quantity` (0-1000)
3. **String Field**: `status` (active, inactive, pending)
4. **Boolean Field**: `is_active` (true/false)
5. **String Field**: `category` (electronics, books, clothing, etc.)

### Filter Expressions

| Filter Type | Expression | Purpose |
|-------------|-----------|---------|
| **Equality** | `color == 'red'` | Basic filter correctness |
| **Inequality** | `quantity > 100` | Numeric filter |
| **Set Membership** | `color IN ['red', 'green']` | Set semantics |
| **Conjunction** | `color == 'red' AND status == 'active'` | Multi-field filter |
| **Null Check** | `field == NULL OR field != NULL` | Null filter semantics |
| **Impossible** | `color == 'red' AND color == 'blue'` | Contradiction handling |

---

## 6. Oracle Definitions

### HYB-001 Oracle: Filter Pre-Application
```python
def oracle_filter_pre_application(search_results, filter_criteria):
    """
    Verify that all search results satisfy the filter criteria.

    Args:
        search_results: List of (id, distance, scalar_fields)
        filter_criteria: Filter expression

    Returns:
        PASS if all results satisfy filter
        VIOLATION (BUG) if any result violates filter
    """
    for result in search_results:
        if not satisfies_filter(result['scalar_fields'], filter_criteria):
            return OracleResult(
                classification=VIOLATION,
                passed=False,
                reasoning=f"Entity {result['id']} violates filter: {filter_criteria}",
                evidence={'violating_entity': result['id']}
            )

    return OracleResult(classification=PASS, passed=True)
```

### HYB-002 Oracle: Filter-Result Consistency
```python
def oracle_filter_result_consistency(results_filtered, results_unfiltered, filter_criteria):
    """
    Verify that filtered search equals manual filter application.

    Args:
        results_filtered: Results from search with filter
        results_unfiltered: Results from search without filter
        filter_criteria: Filter expression

    Returns:
        PASS if filtered == manual_filter(unfiltered)
        VIOLATION (BUG) if inconsistent
    """
    # Manually apply filter to unfiltered results
    manual_filtered = [r for r in results_unfiltered
                      if satisfies_filter(r['scalar_fields'], filter_criteria)]

    # Compare IDs and ordering
    if len(results_filtered) != len(manual_filtered):
        return OracleResult(classification=VIOLATION, passed=False,
                         reasoning="Result count mismatch")

    for i, (filtered, manual) in enumerate(zip(results_filtered, manual_filtered)):
        if filtered['id'] != manual['id']:
            return OracleResult(classification=VIOLATION, passed=False,
                             reasoning=f"Position {i}: filtered={filtered['id']}, manual={manual['id']}")

    return OracleResult(classification=PASS, passed=True)
```

### HYB-003 Oracle: Empty Filter Handling
```python
def oracle_empty_filter_handling(search_results, filter_criteria, collection_state):
    """
    Verify that filters matching no entities return empty results.

    Args:
        search_results: Results from search
        filter_criteria: Filter expression
        collection_state: Whether filter matches any entities

    Returns:
        PASS if results are empty OR consistent error handling
        VIOLATION (BUG) if non-empty when filter matches nothing
        ALLOWED_DIFFERENCE if error handling differs but is consistent
    """
    if collection_state['filter_matches_nothing']:
        if len(search_results) > 0:
            return OracleResult(
                classification=VIOLATION,
                passed=False,
                reasoning=f"Filter matches nothing but returned {len(search_results)} results",
                evidence={'result_count': len(search_results)}
            )

    return OracleResult(classification=PASS, passed=True)
```

---

## 7. Execution Plan

### Phase 1: Test Generation (NOT EXECUTING YET)
- Generate ~15 hybrid test cases from 3 contracts
- Use contract-driven generator with hybrid-specific strategies
- Save to `generated_tests/hybrid_pilot_*.json`

### Phase 2: Milvus Execution (AWAITING APPROVAL)
- Execute tests on real Milvus
- Use filtered_search operation where available
- For unfiltered comparison, use standard search + manual filter

### Phase 3: Oracle Evaluation (AUTOMATED)
- Evaluate results against hybrid contract oracles
- Classify as PASS, VIOLATION (BUG), ALLOWED_DIFFERENCE, OBSERVATION

### Phase 4: Pilot Report (TO BE CREATED)
- Document results and classifications
- Identify any issue candidates
- Assess bug-yield potential of hybrid contracts
- Recommend: proceed to R5C full campaign OR try different contract family

---

## 8. Expected Bug-Yield Assessment

### Why Hybrid Contracts Have Higher Bug-Yield Potential

1. **Filter Implementation Complexity**
   - Milvus uses post-filtering (can leak excluded entities in top-K)
   - Early filter vs. late filter implementation differences
   - Index-aware filtering vs. naïve filtering

2. **Previous R4 Findings**
   - R4 showed ALLOWED_DIFFERENCES in filter behavior between Milvus and Qdrant
   - Suggests filter semantics vary by implementation
   - Higher likelihood of semantic bugs

3. **Critical Severity**
   - HYB-001 is CRITICAL severity
   - Filter violations are correctness bugs, not just performance issues
   - Higher impact = higher bug yield

4. **Complex Interactions**
   - Filter + top-K interaction edge cases
   - Filter + ANN approximation interaction
   - Multi-field filter combinations

### Bug-Yield Prediction

| Contract | Bug Yield Probability | Rationale |
|----------|---------------------|-----------|
| **HYB-001** | **HIGH** | Post-filter implementations often leak excluded entities |
| **HYB-002** | **MEDIUM-HIGH** | Filter semantics inconsistency common in distributed systems |
| **HYB-003** | **MEDIUM** | Edge case, but implementation often correct |

---

## 9. Success Criteria

### Minimum Success (Go/No-Go)
- ✅ Generate 12-15 hybrid test cases successfully
- ✅ Execute all tests on real Milvus without crashes
- ✅ Oracle classification working correctly
- ✅ At least 1 contract violation OR clear understanding of why none found

### Stretch Success
- ✅ Discover 1+ contract violations (bugs)
- ✅ Clear bug-yield demonstration for hybrid contracts
- ✅ Validation of framework on complex contract family

### Failure Modes
- ❌ Cannot generate valid hybrid tests (framework limitation)
- ❌ Execution crashes or infrastructure failures
- ❌ Oracle classification completely inaccurate

---

## 10. Framing and Constraints

### This Is NOT
- ❌ A full R5C campaign
- ❌ KPI-oriented bug hunting
- ❌ A comprehensive hybrid query validation
- ❌ Performance or optimization testing

### This IS
- ✅ A contract-family pilot in the framework validation sequence
- ✅ An evaluation of hybrid contracts' bug-yield potential
- ✅ A test of the framework's capability for filter+vector tests
- ✅ A focused investigation of filter correctness on Milvus

### Next Steps After Pilot
1. If bugs found: **PROCEED** to R5C full campaign
2. If no bugs but high-yield potential seen: **EXPAND** pilot with more aggressive tests
3. If no bugs and low-yield potential: **TRY NEXT FAMILY** (Index or Schema contracts)
4. If framework issues: **FIX INFRASTRUCTURE** before proceeding

---

**Pilot Status**: Design Complete - Awaiting Execution Approval
**Author**: AI-DB-QC Framework
**Version**: 1.0
**Phase**: R5C-Hybrid Pilot (Contract-Family Validation)
