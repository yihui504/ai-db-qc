# R5C-PILOT: Hybrid Query Contract-Driven Validation (REVISED)

**Date**: 2026-03-10
**Phase**: R5C-Hybrid Pilot (Design Phase)
**Framing**: Contract-family pilot (NOT full campaign, NOT KPI bug hunting)
**Status**: Revised Design - Awaiting Execution Approval

---

## Executive Summary

The R5C-Hybrid Pilot validates the contract-driven framework on **Hybrid Query contracts**, which target the interaction between scalar filters and vector similarity search. This family was selected for its **higher bug-yield potential** based on complex semantic interactions.

**Objective**: Evaluate whether hybrid query contracts can reveal real bugs on Milvus, and validate the framework's capability for generating sound filter+vector tests.

**Scope**: 3 hybrid contracts, ~12-15 focused test cases, single-database (Milvus)

---

## 1. Corrected Hybrid Oracle Design

### Oracle Soundness Principles

**Invalid Oracle Pattern**: "filtered top-K == filter(unfiltered top-K)"
- **Problem**: For ANN systems, filtered top-K on the filtered subset is NOT equal to filtering the unfiltered top-K result
- **Why Invalid**: ANN returns approximate results from the full index, then filters. The top-K over filtered subset may differ from top-K over all entities then filtered.

**Valid Oracle Patterns**:
1. **Filter Satisfaction**: All results must satisfy the filter criteria
2. **Exact Search Validation**: Use exact (brute-force) search for oracle ground truth
3. **Deterministic Datasets**: Use small, controlled datasets where expected results are computable

---

## 2. Contract Specifications

### HYB-001: Filter Pre-Application

**Precise Contract Statement**:
> When a scalar filter expression is provided with a vector search, all entities returned in the results MUST satisfy the filter criteria. Entities that do not satisfy the filter MUST NOT appear in the results, regardless of their vector similarity to the query.

**Valid Oracle Definition**:
```python
def oracle_filter_pre_application(search_results, filter_criteria):
    """
    Verify that all search results satisfy the filter criteria.

    Args:
        search_results: List of (id, distance, scalar_fields)
        filter_criteria: Filter expression

    Returns:
        PASS if every result satisfies filter_criteria
        VIOLATION (BUG) if any result violates filter_criteria
        OBSERVATION if filter cannot be evaluated
    """
    for result in search_results:
        if not satisfies_filter(result['scalar_fields'], filter_criteria):
            return OracleResult(
                classification=VIOLATION,
                passed=False,
                reasoning=f"Entity {result['id']} violates filter '{filter_criteria}': {result['scalar_fields']}",
                evidence={
                    'violating_entity': result['id'],
                    'scalar_fields': result['scalar_fields'],
                    'filter_criteria': filter_criteria
                }
            )

    return OracleResult(
        classification=PASS,
        passed=True,
        reasoning=f"All {len(search_results)} results satisfy filter '{filter_criteria}'"
    )
```

**Why Oracle is Sound**:
- Tests a fundamental correctness property: filters must exclude non-matching entities
- Does NOT assume any specific implementation (pre-filter, post-filter, etc.)
- Directly validates the contract statement: "all results MUST satisfy filter"
- Works for any search implementation (exact, ANN, filtered, etc.)

**Dataset Construction Strategy**:
- Small controlled datasets (10-20 entities) with known filter satisfaction
- Include "trap" entities: entities that DON'T satisfy filter but have VERY similar vectors to entities that DO satisfy filter
- This tests whether filter enforcement is strict regardless of vector similarity

---

### HYB-002: Filter-Result Consistency (REVISED)

**Precise Contract Statement**:
> When a scalar filter is applied, the search results must be semantically consistent with the filter. All results must satisfy the filter, and the ranking among matching entities must preserve the distance-based ordering from a brute-force (exact) search over the filtered subset.

**Valid Oracle Definition**:
```python
def oracle_filter_semantic_consistency(
    search_results,           # Results from filtered search
    filter_criteria,
    query_vector,
    filtered_subset_vectors    # All entities that satisfy filter
):
    """
    Verify that filtered search is semantically consistent with exact search.

    Strategy: Compare against brute-force top-K over filtered subset.

    Args:
        search_results: Results from ANN filtered search
        filter_criteria: Filter expression
        query_vector: Query vector
        filtered_subset_vectors: All entities that satisfy filter

    Returns:
        PASS if results are subset of exact top-K over filtered subset
        VIOLATION (BUG) if results include entities not in exact top-K or violate distance ordering
        ALLOWED_DIFFERENCE if ANN approximation within acceptable bounds
    """
    # Step 1: Verify all results satisfy filter
    for result in search_results:
        if not satisfies_filter(result['scalar_fields'], filter_criteria):
            return OracleResult(
                classification=VIOLATION,
                passed=False,
                reasoning=f"Result violates filter: {result['scalar_fields']}",
                evidence={'violating_entity': result['id']}
            )

    # Step 2: Compute exact top-K over filtered subset (ground truth)
    exact_distances = []
    for entity_id, entity_vector, entity_fields in filtered_subset_vectors:
        distance = compute_distance(query_vector, entity_vector)
        if satisfies_filter(entity_fields, filter_criteria):
            exact_distances.append((entity_id, distance, entity_fields))

    # Sort by distance (ascending)
    exact_distances.sort(key=lambda x: x[1])

    # Step 3: Compare ANN results with exact ground truth
    # Extract IDs from exact top-K (where K = len(search_results))
    k = len(search_results)
    exact_top_k_ids = [item[0] for item in exact_distances[:k]]

    # Step 4: Validate semantic consistency
    for result in search_results:
        result_id = result['id']

        # Check 1: Result must be in exact top-K over filtered subset
        if result_id not in exact_top_k_ids:
            # Check if it's due to ANN approximation
            exact_distance = next((d[1] for d in exact_distances if d[0] == result_id), None)
            if exact_distance is not None:
                # Entity is in filtered subset but not in top-K
                # Check if distance is reasonably close to the K-th distance
                kth_distance = exact_distances[min(k-1, len(exact_distances)-1)][1]
                if abs(exact_distance - kth_distance) / (kth_distance + 1e-9) <= 0.1:  # Within 10%
                    # ALLOWED: ANN approximation
                    pass
                else:
                    # POTENTIAL BUG: Entity not in top-K but distance is not close
                    return OracleResult(
                        classification=VIOLATION,
                        passed=False,
                        reasoning=f"Result {result_id} not in exact top-K over filtered subset (distance gap too large)",
                        evidence={
                            'result_id': result_id,
                            'result_distance': exact_distance,
                            'kth_distance': kth_distance
                        }
                    )
            else:
                # BUG: Result doesn't satisfy filter at all
                return OracleResult(
                    classification=VIOLATION,
                    passed=False,
                    reasoning=f"Result {result_id} not in filtered subset",
                    evidence={'result_id': result_id}
                )

    # Step 5: Verify distance ordering among results
    for i in range(len(search_results) - 1):
        curr_dist = search_results[i]['distance']
        next_dist = search_results[i + 1]['distance']

        if curr_dist > next_dist:
            return OracleResult(
                classification=VIOLATION,
                passed=False,
                reasoning=f"Distance ordering violated: [{i}]={curr_dist} > [{i+1}]={next_dist}",
                evidence={
                    'position_i': i,
                    'distance_i': curr_dist,
                    'position_j': i+1,
                    'distance_j': next_dist
                }
            )

    return OracleResult(
        classification=PASS,
        passed=True,
        reasoning=f"Filtered search results are semantically consistent with exact search over filtered subset"
    )
```

**Why Oracle is Sound**:
- Uses **brute-force exact search** as ground truth (computable over filtered subset)
- Does NOT compare filtered top-K with filtered unfiltered top-K (invalid comparison)
- Tests two properties:
  1. All results satisfy filter (HYB-001 property)
  2. Results are valid top-K over the filtered subset (distance ordering)
- Allows for ANN approximation within tolerance bounds (ALLOWED_DIFFERENCE)

**Dataset Construction Strategy**:
- **Small deterministic datasets** (10-20 entities) where exact ground truth is computable
- **Known vector positions**: Construct vectors with known distance relationships
- **Mix of matching/non-matching entities**: Some satisfy filter, some don't
- **Deterministic query vectors**: Use predefined vectors for reproducible results

---

### HYB-003: Empty Filter Result Handling

**Precise Contract Statement**:
> When a filter expression matches no entities in the collection, the search operation must return either an empty result set OR a consistent error behavior. The result must not return entities that do not satisfy the filter.

**Valid Oracle Definition**:
```python
def oracle_empty_filter_handling(
    search_results,
    filter_criteria,
    collection_state
):
    """
    Verify that filters matching no entities produce appropriate results.

    Args:
        search_results: Results from search
        filter_criteria: Filter expression
        collection_state: Metadata about collection and filter match

    Returns:
        PASS if results are empty when filter matches nothing
        PASS if results are non-empty with consistent error behavior
        VIOLATION (BUG) if non-empty results when filter should match nothing
        ALLOWED_DIFFERENCE if error handling differs but is consistent
    """
    # Check if filter matches any entities in collection
    filter_matches_something = collection_state['entities_matching_filter'] > 0

    if not filter_matches_something:
        # Filter matches nothing - results MUST be empty
        if len(search_results) > 0:
            return OracleResult(
                classification=VIOLATION,
                passed=False,
                reasoning=f"Filter matches nothing but returned {len(search_results)} results",
                evidence={
                    'result_count': len(search_results),
                    'filter_criteria': filter_criteria
                }
            )
    else:
        # Filter matches something - non-empty results acceptable
        pass

    return OracleResult(
        classification=PASS,
        passed=True,
        reasoning="Empty filter handling is correct"
    )
```

**Why Oracle is Sound**:
- Tests edge case behavior: what happens when filter matches nothing
- Validates fundamental property: filters should exclude non-matching entities
- Allows for empty results OR consistent error behavior (database discretion)
- Does NOT mandate specific implementation (post-filter vs pre-filter)

**Dataset Construction Strategy**:
- **Datasets with known filter satisfaction**: All entities have specific scalar values
- **Impossible filters**: Filter that no entity can satisfy
- **Edge cases**: Empty collection, single entity, etc.

---

## 3. Small Deterministic Dataset Design

### Dataset Design Principles

1. **Small Size**: 10-20 entities (exact ground truth computable)
2. **Deterministic Vectors**: Predefined vectors with known distance relationships
3. **Known Scalar Values**: Controlled filter attribute values
4. **Reproducibility**: Same vectors and values produce consistent results

### Dataset 1: "Vector Trap" for HYB-001 (Filter Exclusion)

**Purpose**: Test whether entities with very similar vectors but wrong filter values are correctly excluded

**Entities** (15 total):
```
Entity  ID    Color      Vector Pattern
------- -----  --------  --------------
E1      1      red       [0.1, 0.2, 0.3, ...]  (base)
E2      2      blue      [0.1001, 0.2001, 0.3001, ...]  (nearly identical to E1)
E3      3      red       [0.2, 0.3, 0.4, ...]
E4      4      red       [0.3, 0.4, 0.5, ...]
...
E15     15     red       [1.5, 1.6, 1.7, ...]
```

**Query Vector**: Same as E1 (exact match distance = 0)

**Filter**: `color == 'red'`

**Expected Behavior**:
- E2 (blue) MUST be excluded even though its vector is nearly identical to query
- Results SHOULD include E1, E3-E15 (all red entities)
- Oracle: All results must have `color == 'red'`

**Why High Bug Yield**:
- Tests strict filter enforcement regardless of vector similarity
- If post-filter leaks excluded entities into top-K, this test catches it
- Small, deterministic, computable expected results

---

### Dataset 2: "Controlled Top-K" for HYB-002 (Semantic Consistency)

**Purpose**: Test whether filtered search produces valid top-K over filtered subset using exact ground truth

**Entities** (12 total, 8 match filter):
```
Entity  ID    Color      Vector (2D for clarity)         Distance to Query
------- -----  --------  -----------------------------  ------------------
E1      1      red       [0.0, 0.0] (query origin)    0.0 (exact match)
E2      2      red       [0.1, 0.0]                      0.1
E3      3      blue      [0.2, 0.0]                      0.2
E4      4      red       [0.15, 0.0]                     0.15
E5      5      red       [0.3, 0.0]                      0.3
E6      6      blue      [0.4, 0.0]                      0.4
E7      7      red       [0.5, 0.0]                      0.5
E8      8      red       [0.6, 0.0]                      0.6
E9      9      blue      [0.7, 0.0]                      0.7
E10     10     red       [0.8, 0.0]                      0.8
E11     11     red       [0.9, 0.0]                      0.9
E12     12     blue      [1.0, 0.0]                      1.0
```

**Query Vector**: `[0.0, 0.0]` (same as E1)

**Filter**: `color == 'red'`

**Filtered Subset**: {E1, E2, E4, E5, E7, E8, E10, E11} (8 red entities)

**Exact Top-5 Over Filtered Subset**: [E1, E2, E4, E5, E7] (by distance)

**Test**: Search with `filter="color == 'red'"`, `top_k=5`

**Expected Behavior** (Exact Search):
- Results MUST be [E1, E2, E4, E5, E7] (top-5 by distance over red entities)
- E3, E6, E9, E12 (blue) MUST NOT appear

**Expected Behavior** (ANN Search with top_k=5):
- Results MUST all satisfy filter (`color == 'red'`)
- Results should be subset of exact top-8 (red entities by distance)
- Minor reordering allowed due to ANN approximation (ALLOWED_DIFFERENCE)
- No blue entities allowed (VIOLATION)

**Oracle Validation**:
1. Check all results satisfy filter
2. Check results are subset of exact top-K over filtered subset
3. Check distance monotonicity (if strict ordering required)

---

### Dataset 3: "Impossible Filter" for HYB-003 (Empty Filter)

**Purpose**: Test behavior when filter matches no entities

**Entities** (10 total):
```
Entity  ID    Color      Vector
------- -----  --------  --------
E1      1      red       [random1]
E2      2      red       [random2]
...
E10     10     red       [random10]
```

**Filter**: `color == 'blue'` (impossible - no blue entities)

**Query Vector**: Any vector

**Expected Behavior**:
- Results MUST be empty (0 results)
- No crashes, no errors

**Oracle**: Empty results when filter matches nothing

---

## 4. Revised Execution Plan

### Phase 1: Dataset Generation (First)
**Goal**: Create small, deterministic datasets with known expected results

**Tasks**:
1. Generate Dataset 1 (15 entities, vector trap for HYB-001)
2. Generate Dataset 2 (12 entities, controlled top-K for HYB-002)
3. Generate Dataset 3 (10 entities, impossible filter for HYB-003)
4. Pre-compute exact ground truth for Dataset 2
5. Validate datasets meet contract preconditions

### Phase 2: Test Case Generation
**Goal**: Generate ~12-15 test cases from 3 contracts

**Tasks**:
1. HYB-001: Generate 5-6 filter exclusion tests using Dataset 1
   - Basic exclusion: `color == 'red'`
   - Vector similarity trap: Entity with wrong color but similar vector
   - Multiple filters: `color == 'red' AND status == 'active'`
   - Set membership: `color IN ['red', 'green']`
   - Null filter: `field IS NULL`

2. HYB-002: Generate 4-5 semantic consistency tests using Dataset 2
   - Compare ANN filtered search vs exact ground truth
   - Test with different top_k values (3, 5, 10)
   - Validate distance ordering in filtered results
   - Test subset correctness

3. HYB-003: Generate 3-4 empty filter tests using Dataset 3
   - Impossible filter on non-empty collection
   - Empty collection + any filter
   - Contradictory filter: `color == 'red' AND color == 'blue'`

4. Save to `generated_tests/hybrid_pilot_*.json`

### Phase 3: Milvus Execution
**Goal**: Execute all tests on real Milvus

**Tasks**:
1. For each test:
   - Create collection with scalar fields (color, status, etc.)
   - Insert entities from dataset
   - Create index
   - Load collection
   - Execute filtered_search with query and filter
2. Collect raw results (IDs, distances, scalar fields)
3. Clean up (drop collection)

**Constraints**:
- Use real Milvus (not mock)
- Record full result data for oracle evaluation
- Handle errors gracefully (record error, continue)

### Phase 4: Oracle Evaluation
**Goal**: Evaluate results against corrected oracles

**Tasks**:
1. For each test result:
   - Run through appropriate oracle function
   - Generate OracleResult with classification
   - Record reasoning and evidence
2. Classify results:
   - PASS: Contract satisfied
   - VIOLATION (BUG): Contract violated
   - ALLOWED_DIFFERENCE: Acceptable implementation variance
   - OBSERVATION: Cannot determine (data missing)

### Phase 5: Pilot Report
**Goal**: Document findings and assess bug-yield potential

**Report Contents**:
1. Test execution summary
2. Classification distribution (PASS/VIOLATION/ALLOWED/OBSERVATION)
3. Issue candidates discovered (if any)
4. Oracle effectiveness assessment
5. Hybrid contract bug-yield assessment
6. Recommendation: proceed to R5C full OR try next family

---

## 5. Success Criteria (Revised)

### Minimum Success (Go/No-Go)
- ✅ Generate 12-15 hybrid test cases successfully
- ✅ Generate small deterministic datasets with known expected results
- ✅ Execute all tests on real Milvus without crashes
- ✅ Oracle evaluation produces valid classifications
- ✅ At least 1 contract violation OR clear understanding of why none found

### Stretch Success
- ✅ Discover 1+ contract violations (bugs)
- ✅ Clear demonstration of hybrid contracts' bug-yield potential
- ✅ Oracle validated as sound and accurate

### Failure Modes
- ❌ Cannot generate valid hybrid tests or datasets
- ❌ Execution crashes or infrastructure failures
- ❌ Oracle produces false positives or invalid classifications

---

## 6. Corrected Framing

### This Pilot Tests

**What IS being tested**:
- ✅ Whether hybrid query contracts can reveal bugs on Milvus
- ✅ Whether the oracle design is sound for filter+vector tests
- ✅ Framework capability for complex semantic contracts

**What is NOT being tested**:
- ❌ Specific implementation assumptions (no assumptions about post-filter vs pre-filter)
- ❌ Known bugs (we don't assume specific defects in advance)
- ❌ Comprehensive validation (this is a pilot, not full campaign)

### Why No Implementation Assumptions

**Original (INCORRECT)**: "Milvus uses post-filtering and may leak excluded entities"

**Corrected**: We don't know how Milvus implements filtering. The pilot will reveal:
- Whether filter enforcement is strict (HYB-001)
- Whether filtered search is semantically consistent (HYB-002)
- Whether empty filter handling is correct (HYB-003)

The oracle tests the **contract statement**, not the implementation mechanism.

---

## 7. Expected Test Case Distribution

| Contract | Test Type | Count | Bug Yield | Dataset |
|----------|-----------|-------|------------|---------|
| **HYB-001** | Filter Exclusion | 5-6 | **CRITICAL** | Dataset 1 (15 entities, vector trap) |
| **HYB-002** | Semantic Consistency | 4-5 | **HIGH** | Dataset 2 (12 entities, controlled) |
| **HYB-003** | Empty Filter | 3-4 | **MEDIUM** | Dataset 3 (10 entities, impossible filter) |
| **TOTAL** | | **12-15** | | |

---

## 8. Oracle Soundness Justification

### Why These Oracles Are Valid

**HYB-001 Oracle (Filter Satisfaction)**:
- **Sound**: Directly tests contract statement: "all results MUST satisfy filter"
- **Complete**: Checks every result against filter criteria
- **Implementation-agnostic**: Works for pre-filter, post-filter, or any other approach
- **No Invalid Assumptions**: Does not assume implementation details

**HYB-002 Oracle (Semantic Consistency)**:
- **Sound**: Compares ANN results against brute-force exact search ground truth
- **Complete**: Tests both filter satisfaction AND distance ordering
- **Implementation-agnostic**: Does not assume pre-filter vs post-filter
- **Allows Approximation**: Recognizes ANN approximation as ALLOWED_DIFFERENCE

**HYB-003 Oracle (Empty Filter)**:
- **Sound**: Tests fundamental property: filters should exclude non-matching entities
- **Complete**: Checks that no results appear when filter matches nothing
- **Implementation-agnostic**: Allows empty results OR consistent error handling
- **No Invalid Assumptions**: Does not mandate specific error handling

---

## 9. Next Steps

### Current Status: **DESIGN COMPLETE - AWAITING APPROVAL**

**Completed**:
- ✅ Corrected hybrid oracle design (removed invalid comparisons)
- ✅ Precise contract statements for all 3 contracts
- ✅ Valid oracle definitions with soundness justification
- ✅ Dataset construction strategies for each contract
- ✅ Small deterministic dataset designs for highest-value cases
- ✅ Revised execution plan (5 phases)

**Awaiting**:
- ⏳ User approval to proceed with dataset generation
- ⏳ User approval to proceed with test case generation
- ⏳ User approval to proceed with Milvus execution

**After Approval**:
1. Generate datasets and test cases
2. Execute on real Milvus
3. Evaluate with corrected oracles
4. Generate R5C-Hybrid Pilot Report

---

**Pilot Status**: Revised Design Complete - Awaiting Execution Approval
**Author**: AI-DB-QC Framework
**Version**: 2.0 (Revised)
**Phase**: R5C-Hybrid Pilot (Contract-Family Validation)
**Key Corrections**: Fixed HYB-002 oracle, removed implementation assumptions, added deterministic datasets
