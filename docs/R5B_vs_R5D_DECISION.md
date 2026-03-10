# R5B vs R5D Decision Analysis

**Date**: 2026-03-10
**Context**: Selecting next contract-family pilot after R5A (ANN) and R5C (Hybrid) completion
**Status**: DECISION DOCUMENT

---

## Executive Summary

This document compares **R5B (Index Behavior Contracts)** against **R5D (Schema/Metadata Contracts)** as the next contract-family pilot for the AI-DB-QC framework. Based on seven evaluation criteria, **R5B is recommended as the next step**.

**Decision**: **CHOOSE R5B (Index Behavior) FIRST**

**Rationale**: Index behavior represents a higher-yield semantic space with stronger practical relevance, clearer violation potential, and better alignment with production QA needs.

---

## Current Context

### Completed Pilots

| Pilot | Tests | Violations | Key Finding |
|-------|-------|------------|-------------|
| **R5A: ANN** | 10 | 0 | Low bug-yield on Milvus; infrastructure validated |
| **R5C: Hybrid** | 14 | 0 | Low bug-yield on Milvus; filter semantics correct |

**Pattern**: Core search operations on Milvus are well-tested and robust. Need to explore different semantic spaces.

**Framework Status**: ✅ VALIDATED - Contract-driven generation, oracle evaluation, and execution pipeline all functional.

---

## R5B: Index Behavior Contracts

### Contract Overview

| Contract ID | Name | Type | Complexity | Strategy |
|-------------|------|------|------------|----------|
| **IDX-001** | Index Semantic Neutrality | Universal | High | Sequence |
| **IDX-002** | Index Data Preservation | Universal | Medium | Sequence |
| **IDX-003** | Index Parameter Validation | DB-Specific | Low | Illegal |
| **IDX-004** | Multiple Index Behavior | DB-Specific | Medium | Sequence |

**Test Count**: ~12 tests estimated
**Expected Duration**: 2 hours

### Evaluation by Criterion

#### 1. Contract Representativeness for Vector DB QA

**Score: HIGH**

**Rationale**:
- Indexes are fundamental to vector database performance and correctness
- Index-ANN interaction is a critical semantic boundary
- Different index types (HNSW, IVF, FLAT) produce different approximation behaviors
- Index operations are universal across all vector databases

**Representative Properties**:
- Performance optimization without semantic change
- Approximation tolerance management
- Multi-index coexistence semantics
- Parameter space validation

---

#### 2. Likelihood of Discovering Real Bugs

**Score: MEDIUM-HIGH**

**Rationale**:
- **Index creation bugs** are common: data loss, corruption, or semantic drift
- **Parameter validation gaps**: Invalid parameters may be silently accepted
- **Multi-index ambiguity**: Behavior when multiple indexes exist is often under-specified
- **ANN approximation**: Semantic neutrality violations due to recall thresholds

**Bug Yield Potential**:
- **IDX-001 (Semantic Neutrality)**: HIGH - Core contract, high complexity
- **IDX-002 (Data Preservation)**: MEDIUM - Straightforward but critical
- **IDX-003 (Parameter Validation)**: MEDIUM - Common source of bugs
- **IDX-004 (Multiple Index)**: MEDIUM - Edge case, under-tested

**Comparison to Previous Pilots**:
- Unlike ANN/Hybrid (well-tested core operations), index operations have more implementation variation
- Index semantics are more complex than simple search queries
- Multi-database differences more pronounced in index behavior

---

#### 3. Oracle Clarity

**Score: MEDIUM-HIGH**

**Oracle Analysis**:

| Contract | Oracle | Clarity | Notes |
|----------|--------|---------|-------|
| IDX-001 | Semantic equivalence (pre/post index) | Medium | Requires overlap threshold, recall calculation |
| IDX-002 | Count preservation | HIGH | Simple count comparison |
| IDX-003 | Error detection | HIGH | Clear pass/fail: error or no error |
| IDX-004 | Deterministic behavior | Medium | Requires repeated execution, verification of index selection |

**Overall**: Mixed complexity. Simple oracles (IDX-002, IDX-003) complement complex ones (IDX-001, IDX-004). All are well-defined and implementable.

---

#### 4. Implementation Complexity

**Score: MEDIUM**

**Complexity Analysis**:

| Operation | Complexity | Notes |
|-----------|------------|-------|
| Index creation (various types) | Medium | Multiple index types (HNSW, IVF, FLAT) |
| Pre/post search comparison | Medium | Requires storing and comparing result sets |
| Data count verification | Low | Simple count operation |
| Invalid parameter testing | Low | Error detection only |
| Multi-index creation | Medium | Requires database to support multiple indexes |

**Implementation Effort**:
- **Index Operations**: Standard Milvus adapter functionality
- **Result Comparison**: Requires overlap calculation (similar to R5A ANN-003)
- **Parameter Testing**: Straightforward error detection
- **Determinism Testing**: Repeated execution pattern

**Estimate**: 2-3 hours for full implementation

---

#### 5. Risk of Tool Artifacts

**Score: LOW**

**Analysis**:
- Index behavior is fundamental to vector databases
- Violations would indicate real semantic issues, not test infrastructure problems
- Oracle checks are direct (count preservation, error detection)
- Low risk of false positives from test framework

**Artifact Mitigation**:
- Pre/post index comparison uses same data and query
- Count preservation is deterministic and unambiguous
- Error detection is binary (error occurred or not)

---

#### 6. Relevance to Practical Quality Assurance

**Score: HIGH**

**Production Impact**:

| Contract | Production Relevance | Impact if Violated |
|----------|---------------------|-------------------|
| IDX-001 | HIGH | Search results change after index creation (data corruption) |
| IDX-002 | CRITICAL | Data loss during index operations |
| IDX-003 | MEDIUM | Invalid indexes created, leading to undefined behavior |
| IDX-004 | MEDIUM | Non-deterministic search results |

**Use Cases**:
- **Pre-deployment validation**: Ensure index creation doesn't break search
- **Performance regression testing**: Index changes shouldn't affect correctness
- **Multi-environment testing**: Different index types across environments
- **Migration testing**: Index rebuild or migration scenarios

---

#### 7. Suitability for Contract-Driven Generation

**Score: HIGH**

**Generation Strategy Alignment**:

| Strategy | R5B Contracts | Suitability |
|----------|---------------|-------------|
| **Sequence** | IDX-001, IDX-002, IDX-004 | HIGH - Index operations are inherently sequential |
| **Illegal** | IDX-003 | HIGH - Parameter validation is classic illegal input testing |
| **Legal** | IDX-002 | MEDIUM - Count preservation is straightforward |
| **Boundary** | - | LOW - No clear boundary conditions in index contracts |

**Generation Strengths**:
- **Sequential nature**: Index operations (create → search → compare) map naturally to sequence strategy
- **Clear pre/post conditions**: Before/after index state is well-defined
- **Determinate outcomes**: Pass/fail classification is unambiguous

---

## R5D: Schema/Metadata Contracts

### Contract Overview

| Contract ID | Name | Type | Complexity | Strategy |
|-------------|------|------|------------|----------|
| **SCH-001** | Schema Evolution Data Preservation | Universal | Medium | Sequence |
| **SCH-002** | Query Compatibility Across Schema Updates | Universal | Medium | Sequence |
| **SCH-003** | Index Rebuild After Schema Change | DB-Specific | Medium | Sequence |
| **SCH-004** | Metadata Accuracy | Universal | Low | Legal |

**Test Count**: ~10 tests estimated
**Expected Duration**: 1.5-2 hours

### Evaluation by Criterion

#### 1. Contract Representativeness for Vector DB QA

**Score: MEDIUM**

**Rationale**:
- Schema operations are important but less central than index operations
- Schema changes are infrequent in production compared to index operations
- Metadata accuracy is a basic sanity check, not deep semantic testing
- Schema evolution is critical but represents a narrower semantic space

**Representative Properties**:
- Data preservation across schema changes
- Backward compatibility of queries
- Index lifecycle management
- Metadata consistency

---

#### 2. Likelihood of Discovering Real Bugs

**Score: LOW-MEDIUM**

**Rationale**:
- **Schema evolution bugs** are serious but schema changes are rare
- **Metadata accuracy** is basic; most databases get this right
- **Index rebuild after schema** is database-specific; many databases don't support dynamic schema changes
- **Query compatibility** is important but well-tested in mature databases

**Bug Yield Potential**:
- **SCH-001 (Data Preservation)**: LOW - Basic integrity, usually correct
- **SCH-002 (Query Compatibility)**: LOW-MEDIUM - Backward compatibility is usually maintained
- **SCH-003 (Index Rebuild)**: LOW - Database-specific, many don't support
- **SCH-004 (Metadata Accuracy)**: LOW - Basic sanity check

**Comparison to R5B**:
- Schema operations are less complex than index operations
- Mature databases have extensive schema testing
- Limited implementation space (Milvus has limited schema modification support)

---

#### 3. Oracle Clarity

**Score: HIGH**

**Oracle Analysis**:

| Contract | Oracle | Clarity | Notes |
|----------|--------|---------|-------|
| SCH-001 | Data count preservation | HIGH | Simple count comparison |
| SCH-002 | Query success and result equivalence | HIGH | Query execution + result comparison |
| SCH-003 | Index works or rebuild required | MEDIUM | May require interpretation of error messages |
| SCH-004 | Metadata matches actual | HIGH | Direct count/dimension comparison |

**Overall**: Clearer oracles than R5B on average. SCH-001, SCH-002, and SCH-004 have simple, unambiguous checks.

---

#### 4. Implementation Complexity

**Score: MEDIUM-HIGH**

**Complexity Analysis**:

| Operation | Complexity | Notes |
|-----------|------------|-------|
| Schema modification (add field) | HIGH | **Milvus doesn't support dynamic schema changes** |
| Pre/post schema query execution | Medium | Requires storing query results |
| Index rebuild verification | Medium | May not be supported by database |
| Metadata retrieval and comparison | Low | Simple describe operations |

**Implementation Challenge**:
- **Milvus limitation**: Cannot add fields to existing collections dynamically
- **Workaround required**: Create new collection with different schema, or use limited supported operations
- **Test scope**: May be limited by database capabilities

**Estimate**: 2-3 hours with workarounds

---

#### 5. Risk of Tool Artifacts

**Score: LOW-MEDIUM**

**Analysis**:
- Schema operations are fundamental; violations would be real bugs
- Metadata accuracy is unambiguous
- **Potential issue**: Limited schema modification support may require workarounds that introduce artifacts

**Artifact Risk**:
- If schema tests use mock/wrapper implementations, results may not reflect real behavior
- Limited operations may reduce test coverage

---

#### 6. Relevance to Practical Quality Assurance

**Score: MEDIUM**

**Production Impact**:

| Contract | Production Relevance | Frequency |
|----------|---------------------|-----------|
| SCH-001 | HIGH (if schema changes) | Rare |
| SCH-002 | HIGH (if schema changes) | Rare |
| SCH-003 | MEDIUM | Rare |
| SCH-004 | LOW | Continuous (but basic) |

**Use Cases**:
- **Migration testing**: Schema changes during version upgrades
- **Metadata monitoring**: Continuous sanity checks
- **Backward compatibility**: Version rollback scenarios

**Limitation**: Schema changes are infrequent; most production issues occur during index/search operations, not schema evolution.

---

#### 7. Suitability for Contract-Driven Generation

**Score: MEDIUM**

**Generation Strategy Alignment**:

| Strategy | R5D Contracts | Suitability |
|----------|---------------|-------------|
| **Sequence** | SCH-001, SCH-002, SCH-003 | MEDIUM - Schema sequences but limited by database support |
| **Legal** | SCH-004 | HIGH - Simple metadata queries |
| **Boundary** | - | LOW - No clear boundary conditions |

**Generation Challenges**:
- **Limited operations**: Milvus doesn't support dynamic schema changes
- **Sequential constraints**: Schema changes are often one-way (can't rollback)
- **Database limitations**: Many schema operations are not supported

---

## Comparative Summary

### Criterion-by-Criterion Comparison

| Criterion | R5B (Index) | R5D (Schema) | Winner |
|-----------|-------------|-------------|--------|
| **1. Contract Representativeness** | HIGH | MEDIUM | **R5B** |
| **2. Bug Discovery Potential** | MEDIUM-HIGH | LOW-MEDIUM | **R5B** |
| **3. Oracle Clarity** | MEDIUM-HIGH | HIGH | R5D |
| **4. Implementation Complexity** | MEDIUM | MEDIUM-HIGH | **R5B** |
| **5. Tool Artifact Risk** | LOW | LOW-MEDIUM | **R5B** |
| **6. Practical QA Relevance** | HIGH | MEDIUM | **R5B** |
| **7. Contract-Driven Suitability** | HIGH | MEDIUM | **R5B** |

**Score**: R5B wins 6/7 criteria; R5D wins 1/7

### Strategic Considerations

#### Advantages of R5B First

1. **Higher Bug Yield**: Index operations are more complex and less standardized than schema operations
2. **Production Relevance**: Index issues affect daily operations; schema issues are rare
3. **Better Semantic Coverage**: Index-ANN interaction is a critical semantic boundary not yet tested
4. **Implementation Feasibility**: No database limitations; all index operations are supported
5. **Natural Next Step**: Builds on R5A (ANN) by testing index's impact on ANN results

#### Advantages of R5D First

1. **Clearer Oracles**: Simpler verification (count preservation, metadata accuracy)
2. **Completeness**: Validates another important semantic space
3. **Data Integrity Focus**: Critical for long-running production systems

#### Disadvantages of R5D First

1. **Milvus Limitations**: Dynamic schema changes not supported; tests require workarounds
2. **Lower Bug Yield**: Schema operations are well-tested in mature databases
3. **Lower Relevance**: Schema changes are infrequent in production
4. **Implementation Complexity**: Higher due to database limitations

---

## Decision Matrix

### Weighted Evaluation

| Criterion | Weight | R5B Score | R5D Score | R5B Weighted | R5D Weighted |
|-----------|--------|-----------|-----------|--------------|--------------|
| Contract Representativeness | 15% | 9 | 6 | 1.35 | 0.90 |
| Bug Discovery Potential | 25% | 7 | 4 | 1.75 | 1.00 |
| Oracle Clarity | 10% | 7 | 9 | 0.70 | 0.90 |
| Implementation Complexity | 15% | 8 | 5 | 1.20 | 0.75 |
| Tool Artifact Risk | 10% | 9 | 7 | 0.90 | 0.70 |
| Practical QA Relevance | 15% | 9 | 6 | 1.35 | 0.90 |
| Contract-Driven Suitability | 10% | 9 | 6 | 0.90 | 0.60 |
| **TOTAL** | **100%** | | | **8.05** | **5.75** |

**Result**: R5B scores significantly higher (8.05 vs 5.75)

---

## Final Recommendation

### Decision: **CHOOSE R5B (INDEX BEHAVIOR) FIRST**

### Summary Rationale

**R5B (Index Behavior)** is the better next step for the following reasons:

1. **Higher Bug Yield Potential**: Index operations are complex, with more implementation variation and edge cases than schema operations
2. **Stronger Production Relevance**: Index issues affect daily operations; schema changes are rare
3. **Better Implementation Feasibility**: No database limitations; all index operations are fully supported
4. **Natural Progression**: Builds on R5A (ANN) by testing how indexes impact ANN search results
5. **Superior Semantic Coverage**: Index-ANN interaction is a critical semantic boundary not yet explored

**R5D (Schema/Metadata)** should be pursued **after R5B**, as it:
- Has clearer oracles but lower bug-yield potential
- Faces database limitations (Milvus doesn't support dynamic schema changes)
- Is less relevant to day-to-day QA operations

---

## Next Steps

1. **Proceed with R5B Index Pilot Design**
2. **Implement R5B test generation and execution**
3. **Evaluate results and bug yield**
4. **After R5B completion, proceed to R5D**

---

**Decision Document Version**: 1.0
**Date**: 2026-03-10
**Decision**: R5B (Index Behavior Contracts) FIRST
**Next Phase**: R5B Index Pilot Design
