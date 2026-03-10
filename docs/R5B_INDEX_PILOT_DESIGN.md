# R5B Index Behavior Pilot Design

**Date**: 2026-03-10
**Run ID**: TBD (assigned at execution)
**Framing**: Index Behavior Contract-Driven Validation
**Status**: DESIGN READY

---

## Executive Summary

The R5B Index Behavior Pilot is a contract-family pilot focused on validating **index creation, modification, and semantic behavior** on vector databases. This pilot targets 4 index contracts with ~12-15 test cases to evaluate whether index operations preserve data integrity, maintain semantic neutrality, validate parameters correctly, and handle multiple indexes deterministically.

**Goal**: Validate that index behavior contracts can reveal real bugs in Milvus's index implementation, particularly in areas of semantic neutrality, parameter validation, and multi-index scenarios.

**Hypothesis**: Index contracts have **higher bug-yield potential** than ANN and Hybrid contracts due to:
1. Greater implementation complexity (index-ANN interaction)
2. More parameter space (different index types, parameters)
3. Less standardized behavior across databases
4. Edge cases in multi-index scenarios

---

## 1. Contract Definitions

### IDX-001: Index Semantic Neutrality

**Statement**: Creating an index must not change the semantic results of search operations.

**Type**: Universal

**Rationale**: Indexes are performance optimizations, not semantic changes. Users expect search results to remain consistent (within ANN approximation bounds) regardless of whether an index is used.

**Formal Contract**:
```json
{
  "contract_id": "IDX-001",
  "name": "Index Semantic Neutrality",
  "family": "INDEX",
  "type": "universal",
  "statement": "Creating an index must not change the semantic results of search operations",
  "rationale": "Indexes are performance optimizations, not semantic changes",
  "scope": {
    "databases": ["all"],
    "operations": ["create_index", "search"],
    "conditions": ["index_type_supported"]
  },
  "preconditions": [
    "collection_exists",
    "data_inserted",
    "search_executed_before_index"
  ],
  "postconditions": [
    "search_results_after_index == search_results_before_index (modulo ANN approximation)"
  ],
  "invariants": [
    "Index creation preserves semantic correctness"
  ],
  "violation_criteria": {
    "condition": "semantic_results_differ_significantly_beyond_ann_approximation",
    "severity": "critical"
  }
}
```

**Oracle**:
```python
def oracle_idx_semantic_neutrality(results_before, results_after, expected_recall=0.9):
    """
    Verify that indexed search results are semantically equivalent to brute force.

    Args:
        results_before: Search results BEFORE index (brute force)
        results_after: Search results AFTER index (using index)
        expected_recall: Minimum expected overlap (default 0.9 for ANN)

    Returns:
        PASS if overlap >= expected_recall
        VIOLATION if overlap < expected_recall
    """
    ids_before = set(r.id for r in results_before)
    ids_after = set(r.id for r in results_after)

    if len(ids_before) == 0:
        return len(ids_after) == 0

    overlap = len(ids_before & ids_after) / len(ids_before)
    return overlap >= expected_recall
```

---

### IDX-002: Index Data Preservation

**Statement**: Index operations (create, rebuild, delete) must not lose or corrupt data.

**Type**: Universal

**Rationale**: Indexes are derivatives of primary data. Data integrity is paramount; index operations must never cause data loss.

**Formal Contract**:
```json
{
  "contract_id": "IDX-002",
  "name": "Index Data Preservation",
  "family": "INDEX",
  "type": "universal",
  "statement": "Index operations must not cause data loss or corruption",
  "rationale": "Indexes are derivatives of primary data; data integrity is paramount",
  "scope": {
    "databases": ["all"],
    "operations": ["create_index", "drop_index", "rebuild_index"],
    "conditions": ["collection_exists"]
  },
  "preconditions": [
    "collection_exists",
    "data_inserted"
  ],
  "postconditions": [
    "all_inserted_data_still_accessible",
    "data_count_unchanged"
  ],
  "invariants": [
    "Data integrity maintained across index operations"
  ],
  "violation_criteria": {
    "condition": "data_count_before != data_count_after OR data_lost",
    "severity": "critical"
  }
}
```

**Oracle**:
```python
def oracle_idx_data_preservation(count_before, count_after, ids_before, ids_after):
    """
    Verify that data count and accessibility are preserved across index operations.

    Args:
        count_before: Entity count before index operation
        count_after: Entity count after index operation
        ids_before: Set of entity IDs before index operation
        ids_after: Set of entity IDs after index operation

    Returns:
        PASS if count_before == count_after AND ids_before ⊆ ids_after
        VIOLATION if data count changed OR data lost
    """
    count_preserved = (count_before == count_after)
    data_accessible = ids_before.issubset(ids_after)

    return count_preserved and data_accessible
```

---

### IDX-003: Index Parameter Validation

**Statement**: Index creation must validate index type and parameters.

**Type**: Database-specific

**Rationale**: Invalid index parameters should be rejected with clear error messages. Silently accepting invalid parameters can lead to undefined behavior.

**Formal Contract**:
```json
{
  "contract_id": "IDX-003",
  "name": "Index Parameter Validation",
  "family": "INDEX",
  "type": "database_specific",
  "statement": "Index creation must validate index type and parameters",
  "rationale": "Invalid index parameters should be rejected with clear error",
  "scope": {
    "databases": ["milvus", "qdrant"],
    "operations": ["create_index"],
    "conditions": ["collection_exists"]
  },
  "preconditions": [
    "collection_exists"
  ],
  "postconditions": [
    "valid_parameters_succeed OR invalid_parameters_fail_with_clear_error"
  ],
  "invariants": [
    "Index creation is deterministic for given parameters"
  ],
  "violation_criteria": {
    "condition": "invalid_parameters_accepted OR unclear_error_message",
    "severity": "medium"
  }
}
```

**Oracle**:
```python
def oracle_idx_parameter_validation(result, parameters_expected_valid):
    """
    Verify that index creation handles parameters correctly.

    Args:
        result: Execution result (success/error)
        parameters_expected_valid: Whether parameters should be valid

    Returns:
        PASS if (valid_params AND success) OR (invalid_params AND clear_error)
        VIOLATION if (invalid_params AND success) OR (invalid_params AND unclear_error)
    """
    if parameters_expected_valid:
        return result.success  # Should succeed
    else:
        # Should fail with clear error
        return (not result.success) and result.has_clear_error_message()
```

---

### IDX-004: Multiple Index Behavior

**Statement**: Multiple indexes on same collection must have deterministic behavior.

**Type**: Database-specific

**Rationale**: When multiple indexes exist, the database must deterministically select which index to use or clearly document the selection strategy.

**Formal Contract**:
```json
{
  "contract_id": "IDX-004",
  "name": "Multiple Index Behavior",
  "family": "INDEX",
  "type": "database_specific",
  "statement": "Multiple indexes on same vector field must have deterministic behavior",
  "rationale": "Databases must handle multiple indexes consistently",
  "scope": {
    "databases": ["milvus", "qdrant"],
    "operations": ["create_index", "search"],
    "conditions": ["database_supports_multiple_indexes"]
  },
  "preconditions": [
    "collection_exists",
    "database_supports_multiple_indexes"
  ],
  "postconditions": [
    "search_uses_designated_index OR search_uses_all_indexes OR error_raised"
  ],
  "invariants": [
    "Index selection is deterministic"
  ],
  "violation_criteria": {
    "condition": "non_deterministic_index_selection",
    "severity": "medium"
  }
}
```

**Oracle**:
```python
def oracle_idx_multiple_index_consistency(results_list):
    """
    Verify that multiple searches with multiple indexes produce consistent results.

    Args:
        results_list: List of search results from repeated executions

    Returns:
        PASS if all executions produce the same index selection and results
        VIOLATION if index selection or results are non-deterministic
    """
    if not results_list:
        return True

    # Check if all results are identical
    first_result_ids = set(r.id for r in results_list[0])

    for results in results_list[1:]:
        result_ids = set(r.id for r in results)
        if result_ids != first_result_ids:
            return False  # Non-deterministic

    return True  # Deterministic behavior
```

---

## 2. Test Case Generation

### Generation Strategy Overview

| Contract | Strategy | Test Cases | Priority |
|----------|----------|------------|----------|
| **IDX-001** | Sequence | 4 | HIGH |
| **IDX-002** | Sequence | 5 | HIGH |
| **IDX-003** | Illegal | 4 | MEDIUM |
| **IDX-004** | Sequence | 3 | MEDIUM |
| **TOTAL** | | **16** | |

### IDX-001 Test Cases (4 tests)

| Test ID | Name | Description | Dataset | Priority |
|---------|------|-------------|---------|----------|
| **idx-001_hnsw_001** | HNSW Semantic Neutrality | Compare brute force vs HNSW index | Dataset 1: Random vectors (128D, 1000 entities) | HIGH |
| **idx-001_ivf_001** | IVF Semantic Neutrality | Compare brute force vs IVF index | Dataset 1: Random vectors (128D, 1000 entities) | HIGH |
| **idx-001_flat_001** | FLAT Baseline | Verify FLAT index produces exact results | Dataset 1: Random vectors (128D, 1000 entities) | MEDIUM |
| **idx-001_ann_recall_001** | ANN Recall Threshold | Test with low expected_recall | Dataset 2: Clustered vectors (128D, 500 entities) | MEDIUM |

### IDX-002 Test Cases (5 tests)

| Test ID | Name | Description | Dataset | Priority |
|---------|------|-------------|---------|----------|
| **idx-002_create_001** | Data Count After Create | Verify count preserved after index creation | Dataset 1: Random vectors (128D, 1000 entities) | HIGH |
| **idx-002_create_002** | Data Accessibility After Create | Verify all data accessible after creation | Dataset 1: Random vectors (128D, 1000 entities) | HIGH |
| **idx-002_drop_001** | Data Count After Drop | Verify count preserved after index drop | Dataset 1: Random vectors (128D, 1000 entities) | HIGH |
| **idx-002_rebuild_001** | Data Count After Rebuild | Verify count preserved after index rebuild | Dataset 1: Random vectors (128D, 1000 entities) | MEDIUM |
| **idx-002_cycle_001** | Full Index Cycle | Create → Search → Drop → Create → Search | Dataset 1: Random vectors (128D, 1000 entities) | MEDIUM |

### IDX-003 Test Cases (4 tests)

| Test ID | Name | Parameters | Expected | Priority |
|---------|------|------------|----------|----------|
| **idx-003_invalid_type_001** | Invalid Index Type | index_type: "INVALID_TYPE" | Error | HIGH |
| **idx-003_invalid_param_001** | Invalid HNSW Parameter | index_type: "HNSW", M: -1 | Error | HIGH |
| **idx-003_invalid_param_002** | Invalid IVF Parameter | index_type: "IVF", nlist: 0 | Error | MEDIUM |
| **idx-003_invalid_param_003** | Out-of-Range Parameter | index_type: "HNSW", efConstruction: 1 | Error | MEDIUM |

### IDX-004 Test Cases (3 tests)

| Test ID | Name | Description | Dataset | Priority |
|---------|------|-------------|---------|----------|
| **idx-004_multi_type_001** | HNSW + IVF Coexistence | Create two indexes, verify behavior | Dataset 1: Random vectors (128D, 1000 entities) | MEDIUM |
| **idx-004_multi_create_001** | Multiple HNSW Variants | Create HNSW with different params | Dataset 1: Random vectors (128D, 1000 entities) | MEDIUM |
| **idx-004_determinism_001** | Index Selection Determinism | Repeat search 10x, verify consistency | Dataset 1: Random vectors (128D, 1000 entities) | MEDIUM |

---

## 3. Dataset Design

### Primary Dataset: Random Vectors (Dataset 1)

**Purpose**: General-purpose testing for semantic neutrality and data preservation

**Configuration**:
- **Dimension**: 128
- **Entity Count**: 1000
- **Generation Method**: Uniform random distribution [-1, 1]
- **Seed**: 42 (deterministic)

**Usage**:
- IDX-001: Semantic neutrality tests
- IDX-002: Data preservation tests
- IDX-004: Multi-index tests

**Properties**:
- Provides diverse vector space for comprehensive testing
- Large enough to test index effectiveness
- Small enough for fast execution

### Secondary Dataset: Clustered Vectors (Dataset 2)

**Purpose**: Test ANN recall with clustered data (harder for ANN)

**Configuration**:
- **Dimension**: 128
- **Entity Count**: 500
- **Generation Method**: 5 clusters, random assignment, cluster centers at [±1, ±1, ...]
- **Seed**: 42 (deterministic)

**Usage**:
- IDX-001: ANN recall threshold test

**Properties**:
- Clustered structure challenges ANN approximation
- Reveals recall issues more clearly than random data

### Dataset 1 Structure

```python
{
  "dataset_id": "random_vectors_128d_1000",
  "dimension": 128,
  "count": 1000,
  "seed": 42,
  "vectors": [
    [0.123, -0.456, ...],  # Entity 0
    [0.789, 0.234, ...],   # Entity 1
    ...
  ],
  "metadata": {
    "id_field": "id",
    "vector_field": "vector"
  }
}
```

---

## 4. Oracle Implementation

### Oracle Engine Extension

New oracle functions for index contracts:

```python
class IndexOracleEngine(OracleEngine):
    """Oracle engine for index behavior contracts."""

    def evaluate_idx_001(self, results_before, results_after, expected_recall=0.9):
        """
        IDX-001: Index Semantic Neutrality

        Verify semantic equivalence between brute force and indexed search.
        """
        if not results_before and not results_after:
            return OracleResult(PASS, "Both searches returned empty")

        ids_before = set(r.id for r in results_before)
        ids_after = set(r.id for r in results_after)

        if len(ids_before) == 0:
            classification = PASS if len(ids_after) == 0 else VIOLATION
            reasoning = f"Empty before, {len(ids_after)} after"
            return OracleResult(classification, reasoning)

        overlap = len(ids_before & ids_after) / len(ids_before)

        if overlap >= expected_recall:
            return OracleResult(PASS, f"Overlap {overlap:.2f} >= {expected_recall}")
        else:
            return OracleResult(VIOLATION, f"Overlap {overlap:.2f} < {expected_recall}")

    def evaluate_idx_002(self, count_before, count_after, ids_before, ids_after):
        """
        IDX-002: Index Data Preservation

        Verify data integrity across index operations.
        """
        count_ok = (count_before == count_after)
        data_accessible = ids_before.issubset(ids_after)

        if count_ok and data_accessible:
            return OracleResult(PASS, f"Count {count_after}, all data accessible")
        elif not count_ok:
            return OracleResult(VIOLATION, f"Count changed: {count_before} -> {count_after}")
        else:
            missing = ids_before - ids_after
            return OracleResult(VIOLATION, f"Data lost: {len(missing)} entities missing")

    def evaluate_idx_003(self, result, parameters_expected_valid):
        """
        IDX-003: Index Parameter Validation

        Verify parameter validation behavior.
        """
        if parameters_expected_valid:
            if result.success:
                return OracleResult(PASS, "Valid parameters accepted")
            else:
                return OracleResult(VIOLATION, f"Valid parameters rejected: {result.error}")
        else:
            if result.success:
                return OracleResult(VIOLATION, "Invalid parameters accepted (BUG)")
            elif result.has_clear_error_message():
                return OracleResult(PASS, f"Invalid parameters rejected: {result.error}")
            else:
                return OracleResult(VIOLATION, "Invalid parameters accepted with unclear error")

    def evaluate_idx_004(self, results_list):
        """
        IDX-004: Multiple Index Behavior

        Verify deterministic behavior with multiple indexes.
        """
        if len(results_list) < 2:
            return OracleResult(PASS, "Insufficient data for determinism check")

        first_ids = set(r.id for r in results_list[0])

        for i, results in enumerate(results_list[1:], 1):
            result_ids = set(r.id for r in results)
            if result_ids != first_ids:
                return OracleResult(VIOLATION, f"Run {i} differs from run 0")

        return OracleResult(PASS, f"All {len(results_list)} runs identical")
```

---

## 5. Execution Plan

### Phase 1: Infrastructure Setup (30 minutes)

1. **Dataset Generation**
   - Generate Dataset 1 (random vectors, 1000 entities)
   - Generate Dataset 2 (clustered vectors, 500 entities)
   - Store as JSON for reproducibility

2. **Oracle Implementation**
   - Implement IndexOracleEngine class
   - Add idx_001 through idx_004 evaluation functions
   - Unit test oracles with known inputs

3. **Adapter Verification**
   - Verify Milvus adapter supports:
     - HNSW, IVF, FLAT index types
     - Index creation, dropping, rebuilding
     - Multiple index creation (if supported)
     - Brute force search (index_type="FLAT")

### Phase 2: Test Generation (30 minutes)

1. **Generate IDX-001 Tests** (4 tests)
   - Sequence strategy: insert → brute force search → create index → indexed search
   - Configure expected_recall=0.9 for HNSW/IVF tests
   - Configure expected_recall=1.0 for FLAT test

2. **Generate IDX-002 Tests** (5 tests)
   - Sequence strategy: insert → count → index operation → count → verify accessibility
   - Cover create, drop, rebuild operations

3. **Generate IDX-003 Tests** (4 tests)
   - Illegal strategy: create index with invalid parameters
   - Verify error messages are clear

4. **Generate IDX-004 Tests** (3 tests)
   - Sequence strategy: create multiple indexes → search repeatedly
   - Verify deterministic behavior

### Phase 3: Execution (60-90 minutes)

1. **Execute IDX-001 Tests**
   - Run on real Milvus
   - Collect before/after results
   - Evaluate semantic neutrality

2. **Execute IDX-002 Tests**
   - Run index operations
   - Count entities before/after
   - Verify all entities accessible

3. **Execute IDX-003 Tests**
   - Attempt invalid index creation
   - Record success/failure
   - Verify error message clarity

4. **Execute IDX-004 Tests**
   - Create multiple indexes
   - Execute repeated searches
   - Verify deterministic behavior

### Phase 4: Analysis and Reporting (30 minutes)

1. **Classification Analysis**
   - Count PASS, VIOLATION, OBSERVATION, ALLOWED_DIFFERENCE
   - Identify any contract violations (bugs)

2. **Issue Candidate Extraction**
   - Document any violations with evidence
   - Assess severity and reproducibility
   - Prepare issue-ready bug reports

3. **Framework Validation**
   - Verify oracle accuracy
   - Identify any implementation gaps
   - Note any execution issues

4. **Report Generation**
   - Create R5B_INDEX_PILOT_REPORT.md
   - Include test results, findings, and recommendations

---

## 6. Expected Outcomes

### Test Execution Estimates

| Metric | Estimate |
|--------|----------|
| **Total Test Cases** | 16 |
| **Estimated Execution Time** | 60-90 minutes |
| **Expected Pass Rate** | 80-95% (assuming Milvus quality) |
| **Expected Violations** | 0-2 (potential bugs in edge cases) |

### Potential Bug Categories

Based on contract analysis, potential bugs include:

| Contract | Potential Bug | Severity |
|----------|---------------|----------|
| IDX-001 | Semantic drift when switching index types | CRITICAL |
| IDX-001 | ANN recall below 90% on specific data | HIGH |
| IDX-002 | Data count changes after index operations | CRITICAL |
| IDX-002 | Data inaccessibility after index operations | CRITICAL |
| IDX-003 | Invalid parameters silently accepted | HIGH |
| IDX-003 | Unclear error messages for invalid parameters | MEDIUM |
| IDX-004 | Non-deterministic index selection | HIGH |
| IDX-004 | Inconsistent results with multiple indexes | HIGH |

### Bug Yield Potential Assessment

**Compared to R5A (ANN) and R5C (Hybrid)**:

| Aspect | R5A/R5C Result | R5B Expectation |
|--------|----------------|-----------------|
| **Core Operation Maturity** | HIGH (well-tested) | MEDIUM (index ops more complex) |
| **Implementation Variation** | LOW (standardized) | MEDIUM (different index types) |
| **Edge Case Surface** | MEDIUM | HIGH (parameters, multi-index) |
| **Bug Discovery Potential** | LOW | **MEDIUM-HIGH** |

**R5B Advantage**:
- Index-ANN interaction is less standardized than pure ANN search
- Parameter validation is often under-tested
- Multi-index scenarios are edge cases
- Index rebuild/drop operations are less frequent than search operations

---

## 7. Success Criteria

### Primary Success Criteria

1. **Framework Validation**: ✅ All 16 tests execute successfully without infrastructure failures
2. **Oracle Accuracy**: ✅ Oracle classifications are correct (verified by manual inspection of samples)
3. **Contract Coverage**: ✅ All 4 index contracts tested with appropriate strategies

### Secondary Success Criteria

1. **Bug Discovery**: ⚠️ At least 1 contract violation found (validates bug-yield potential)
2. **Implementation Gaps Identified**: Document any areas needing enhancement
3. **Milvus Index Behavior Validated**: Comprehensive understanding of Milvus index semantics

### Failure Criteria

1. **Infrastructure Failure**: Tests cannot execute due to adapter/infrastructure issues
2. **Oracle Inaccuracy**: Classifications are incorrect (needs oracle refinement)
3. **Database Limitations**: Milvus doesn't support required operations (unlikely)

---

## 8. Risk Assessment

### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Milvus doesn't support multiple indexes | MEDIUM | MEDIUM | Test IDX-004 last, skip if not supported |
| ANN recall < 90% false positives | LOW | MEDIUM | Tune expected_recall based on data characteristics |
| Index rebuild not supported | LOW | LOW | Skip rebuild tests if not supported |
| Brute force search not available | LOW | HIGH | Use FLAT index as proxy for brute force |

### Mitigation Strategies

1. **Multiple Index Support**: Test MILVUS capability before IDX-004; adapt if needed
2. **ANN Recall Threshold**: Start with expected_recall=0.85, adjust based on results
3. **Brute Force Baseline**: Use FLAT index (exact search) as baseline for IDX-001
4. **Index Rebuild**: If not supported, document as ALLOWED_DIFFERENCE

---

## 9. Deliverables

### Artifacts

1. **Test Specification**: `generated_tests/index_pilot_<timestamp>.json`
2. **Execution Results**: `results/index_pilot_<timestamp>.json`
3. **Pilot Report**: `docs/R5B_INDEX_PILOT_REPORT.md`

### Report Contents

- Test execution summary (pass/fail/violation counts)
- Per-contract results and analysis
- Issue candidates (if any violations found)
- Oracle validation results
- Framework assessment
- Recommendations for next steps

---

## 10. Next Steps After R5B

### If Violations Found (High Bug-Yield)

1. **Document violations** with full evidence
2. **Create issue reports** for Milvus team
3. **Consider expansion** to full R5B campaign with more index types

### If No Violations (Low Bug-Yield)

1. **Document findings**: Index contracts validated, no bugs found
2. **Classify index contracts**: Correctness validation vs. bug discovery
3. **Proceed to R5D**: Schema/Metadata contracts
4. **Consider alternative targets**: Test on less-mature vector databases

### In Either Case

1. **Update framework**: Enhance oracles based on execution experience
2. **Consolidate findings**: Compare R5A, R5B, R5C bug-yield results
3. **Decide next phase**: R5D, alternative targets, or research consolidation

---

**Pilot Design Version**: 1.0
**Date**: 2026-03-10
**Designed By**: AI-DB-QC Framework
**Status**: READY FOR IMPLEMENTATION
**Next Action**: Implement Phase 1 (Infrastructure Setup)
