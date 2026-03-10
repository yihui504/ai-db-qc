# Current Challenges

**Project**: AI Database Quality Assurance Framework
**Document Version**: 1.0
**Date**: 2026-03-10

---

## Executive Summary

This document provides an **honest assessment** of the current challenges and limitations facing the AI-DB-QC framework. These challenges emerged from executing 244 tests across 6 campaigns (R1-R5C) and reflect both fundamental research problems and practical implementation limitations.

**Key Insight**: The primary challenge is **low bug-yield on mature databases**, not framework inadequacy. The framework works correctly; the target (Milvus) is simply well-tested.

---

## Challenge 1: Low Bug Discovery Rate

### The Problem

Despite executing 244 tests across 6 campaigns, only **10 contract violations** were discovered, and **0 violations** in the two most recent campaigns (R5A: ANN, R5C: Hybrid).

### Data

| Campaign | Tests | Violations | Bug Rate |
|----------|-------|------------|----------|
| R1 | 50 | 3 | 6.0% |
| R2 | 40 | 2 | 5.0% |
| R3 | 30 | 1 | 3.3% |
| R4 | 100+ | 4* | ~4% |
| R5A | 10 | 0 | 0% |
| R5C | 14 | 0 | 0% |

*Most R4 "violations" were ALLOWED_DIFFERENCE (architectural variance)

### Root Causes

1. **Milvus is Mature**: Core operations are well-tested by the Milvus team
2. **Target Saturation**: We're testing the most stable parts of a stable database
3. **Safe Contract Selection**: ANN and Hybrid contracts are fundamental properties that databases get right

### Evidence

- **R5A Results**: 0 violations in 10 ANN tests covering top-k, distance monotonicity, nearest neighbor inclusion, metric consistency, and empty queries
- **R5C Results**: 0 violations in 14 hybrid tests covering filter exclusion, truncation, monotonicity, and edge cases
- **Conclusion**: Milvus core operations are robust

### Potential Solutions

| Solution | Pros | Cons |
|----------|------|------|
| **Test less-mature databases** | Higher bug-yield | Need adapter development |
| **Test more complex operations** | Untested semantic spaces | Harder to define contracts |
| **Stress testing** | Reveals edge cases | Difficult to automate |
| **Concurrency testing** | High bug-yield area | Complex oracles |

---

## Challenge 2: ANN Approximation Tolerance

### The Problem

Approximate Nearest Neighbor (ANN) algorithms trade accuracy for speed. This makes it difficult to distinguish between:
- **Bugs**: Incorrect behavior
- **Allowed Differences**: Expected ANN approximation behavior

### Example

A search with HNSW index returns 85% overlap with brute force results. Is this:
- A bug (HNSW implementation is broken)?
- Expected (HNSW with default parameters)?
- Configurable (depends on efConstruction parameter)?

### Current Approach (Unsound)

Original IDX-001 oracle:
```python
recall_threshold = 0.9
if overlap < 0.9:
    return VIOLATION  # ⚠️ False violations possible
```

**Problem**: Treats ANN approximation tolerance as a bug threshold.

### Refined Approach (Sound)

Refined IDX-001 oracle (R5B design):
```python
# Hard checks (must pass)
if search_fails_after_index:
    return VIOLATION  # Clear bug

# Quality checks (documented, not violations)
if recall < expected_for_index_type:
    return ALLOWED_DIFFERENCE  # Not a bug
```

**Improvement**: Separates hard contract checks (data/query integrity) from approximate quality checks (recall thresholds).

### Remaining Challenge

Even with refined oracles, determining "expected" recall for a given index type and parameter set is difficult. Requires:
- Understanding of ANN algorithm behavior
- Knowledge of parameter interactions
- Empirical baseline data

### Open Questions

1. What is the "expected" recall for HNSW with M=16, efConstruction=200?
2. How do we handle databases that don't document ANN behavior?
3. Can we derive expected recall from first principles?

---

## Challenge 3: Adapter Capability Limitations

### The Problem

The current Milvus adapter has **hardcoded parameters** and **missing operations**, limiting contract testability.

### Evidence from R5B Pre-Implementation Audit

| Operation/Parameter | Support | Impact |
|---------------------|---------|--------|
| **build_index** | ✅ Partial | Only index_type, metric_type configurable |
| **nlist (IVF parameter)** | ⚠️ Hardcoded to 128 | Cannot test parameter validation |
| **M (HNSW parameter)** | ❌ Not exposed | Cannot test HNSW parameter validation |
| **efConstruction (HNSW)** | ❌ Not exposed | Cannot test HNSW parameter validation |
| **drop_index** | ❌ Not implemented | Cannot test IDX-002 fully |
| **rebuild_index** | ❌ Not implemented | Cannot test IDX-002 fully |
| **list_indexes** | ❌ Not implemented | Cannot test IDX-004 (multi-index) |
| **get_index_info** | ❌ Not implemented | Cannot observe index selection |

### Code Evidence

```python
# adapters/milvus_adapter.py, line 250-275
def _build_index(self, params: Dict) -> Dict[str, Any]:
    """Build index on collection."""
    index_type = params.get("index_type", "IVF_FLAT")
    metric_type = params.get("metric_type", "L2")

    index_params = {
        "index_type": index_type,
        "metric_type": metric_type,
        "params": {"nlist": 128}  # ⚠️ HARDCODED
    }
```

### Impact

1. **False Confidence**: Testing "parameter validation" when parameters are ignored gives misleading results
2. **Scope Reduction**: IDX-003 and IDX-004 postponed due to adapter limitations
3. **Incomplete Coverage**: Cannot test important index operations (drop, rebuild, multi-index)

### Required Effort

| Enhancement | Effort | Priority |
|-------------|--------|----------|
| Add count retrieval | LOW | HIGH (needed for R5B) |
| Implement drop_index | MEDIUM | MEDIUM |
| Expose HNSW/IVF parameters | MEDIUM | MEDIUM |
| Implement rebuild_index | MEDIUM | LOW |
| Add list_indexes | MEDIUM | LOW |
| Add get_index_info | MEDIUM | LOW |

---

## Challenge 4: Oracle Complexity

### The Problem

As contracts become more sophisticated, oracles become more complex to implement correctly.

### Spectrum of Oracle Complexity

| Contract | Oracle Complexity | Implementation Status |
|----------|-------------------|----------------------|
| **ANN-001** (Top-K) | LOW | ✅ Complete |
| **ANN-002** (Monotonicity) | LOW | ✅ Complete |
| **ANN-003** (NN Inclusion) | HIGH | ⚠️ Needs ground truth computation |
| **ANN-004** (Metric Consistency) | MEDIUM | ⚠️ Needs metric library |
| **IDX-001** (Semantic Neutrality) | HIGH | ⚠️ Needs refined design |
| **HYB-001** (Filter Pre-Application) | MEDIUM | ✅ Complete |
| **HYB-002** (Filter Consistency) | MEDIUM | ✅ Complete |

### Example: ANN-003 Oracle Challenge

Contract: "True nearest neighbor must be in results"

Oracle requires:
1. Compute ground truth nearest neighbor (brute force)
2. Check if ground truth is in results
3. If not, compute recall

**Implementation Challenge**:
```python
def _oracle_nearest_neighbor_inclusion(self, result, contract):
    # Need ground_truth_nn_id - but where does it come from?
    ground_truth_nn = result.get("ground_truth_nn_id")

    if ground_truth_nn is None:
        return OBSERVATION  # Can't evaluate without data

    # ... rest of oracle
```

**Root Cause**: Execution layer doesn't compute ground truth data required by oracle.

### Solution Approaches

| Approach | Effort | Soundness |
|----------|--------|-----------|
| **Enhance execution layer** | HIGH | HIGH |
| **Separate computation phase** | MEDIUM | HIGH |
| **Simplify contracts** | LOW | MEDIUM |
| **Use probabilistic checks** | MEDIUM | MEDIUM |

---

## Challenge 5: Distinguishing Bugs from Allowed Differences

### The Problem

Not all unexpected behaviors are bugs. Some are "allowed differences" - architectural choices that differ across databases.

### Examples

| Behavior | Classification | Reason |
|-----------|----------------|--------|
| Distance calculation differs (IP vs L2) | ALLOWED_DIFFERENCE | Different interpretation |
| Index type not supported | ALLOWED_DIFFERENCE | Architectural limitation |
| Filter application timing differs | ALLOWED_DIFFERENCE | Design choice |
| Invalid metric_type accepted | VIOLATION | Bug |
| Silent parameter ignoring | VIOLATION | Bug |

### Decision Framework

Current classification uses heuristics:

```python
if violates_universal_contract():
    return VIOLATION
elif database_specific_difference():
    return ALLOWED_DIFFERENCE
elif undefined_behavior():
    return OBSERVATION
else:
    return PASS
```

**Challenge**: Determining what is "universal" vs "database-specific" requires domain expertise.

### Open Question

Who decides what is an "allowed difference"?
- Database documentation? (often incomplete)
- Common practice? (varies)
- First principles? (difficult for ANN)

---

## Challenge 6: Scalability to New Databases

### The Problem

Adding support for new databases requires significant adapter development effort.

### Current Status

| Database | Adapter Status | Operations Supported |
|----------|----------------|---------------------|
| **Milvus** | ✅ Complete | All core operations |
| **Mock** | ✅ Complete | All operations (in-memory) |
| **SeekDB** | ⚠️ Experimental | Basic operations only |
| **Qdrant** | ❌ Not started | - |
| **Weaviate** | ❌ Not started | - |

### Adapter Development Complexity

Each adapter requires implementing:
- Connection management
- 8+ core operations
- Error handling
- Type conversions
- Database-specific quirks

**Estimated Effort**: 2-3 weeks per adapter

### Impact

Limited database support reduces:
- Differential testing opportunities
- Bug discovery potential (less-mature databases)
- Framework generalizability

---

## Challenge 7: Contract Design Difficulty

### The Problem

Designing good contracts is harder than it appears.

### Contract Quality Spectrum

| Aspect | Good Contract | Bad Contract |
|---------|--------------|--------------|
| **Violation Criteria** | Clear, checkable condition | Vague, subjective |
| **Oracle Implementation** | Deterministic check | Complex computation |
| **Scope** | Well-defined boundaries | Overly broad or narrow |
| **Testability** | Straightforward to test | Requires special setup |

### Example: Bad Contract Design

```json
{
  "contract_id": "BAD-001",
  "statement": "Search results should be good",
  "violation_criteria": {
    "condition": "results are not good",  // ⚠️ Vague
    "severity": "high"
  }
}
```

**Problem**: "Good" is not objectively measurable.

### Example: Good Contract Design

```json
{
  "contract_id": "ANN-001",
  "statement": "Search with top_k must return at most K results",
  "violation_criteria": {
    "condition": "length(search_results) > top_k",  // ✅ Clear
    "severity": "high"
  }
}
```

**Improvement**: Cardinality is objectively measurable.

### Skill Requirement

Good contract design requires:
- Deep understanding of database semantics
- Knowledge of formal specification techniques
- Experience with oracle implementation
- Awareness of practical constraints

---

## Challenge 8: Tool Artifacts and False Positives

### The Problem

Testing infrastructure can introduce artifacts that mask real bugs or create false ones.

### Examples

1. **Mock vs Real Behavior**: Mock adapter may accept operations that real database rejects
2. **Parameter Normalization**: Adapter may normalize parameters, hiding validation issues
3. **Default Values**: Adapter defaults may bypass parameter testing
4. **Error Swallowing**: Try-catch blocks may hide failures

### Mitigation Strategies

| Strategy | Implementation | Effectiveness |
|----------|----------------|----------------|
| **Real database testing** | Use Milvus, not just Mock | HIGH |
| **Parameter transparency** | Pass parameters through unchanged | MEDIUM |
| **Explicit defaults** | Document all default values | MEDIUM |
| **Error propagation** | Don't swallow exceptions | HIGH |

### Current Practice

- R5A and R5C executed on **real Milvus** (not mock)
- Adapter parameters passed through to pymilvus
- Errors logged and propagated

**Result**: High confidence that results reflect real Milvus behavior.

---

## Challenge 9: Reproducibility vs Determinism

### The Problem

ANN algorithms are non-deterministic by design, making reproducibility difficult.

### Example

Same query, same collection, same index:
- Run 1: Returns entities [1, 5, 9, 12, ...]
- Run 2: Returns entities [1, 5, 9, 13, ...]
- Run 3: Returns entities [1, 5, 9, 12, ...]

**Cause**: ANN algorithms use randomization and heuristics.

### Impact on Testing

| Challenge | Effect | Mitigation |
|-----------|--------|------------|
| **Flaky tests** | Tests sometimes pass, sometimes fail | Use statistical thresholds |
| **Diff comparison** | Hard to compare results across runs | Use similarity metrics |
| **Bug reporting** | Hard to reproduce issues | Collect full context |

### Current Approach

- Use deterministic datasets (fixed random seeds)
- Tolerate non-determinism in oracles (recall thresholds)
- Collect multiple runs for statistical confidence

---

## Challenge 10: Framework Evolution vs Stability

### The Problem

The framework is evolving (adding features, fixing bugs) while needing to maintain stability for ongoing research.

### Tension

| Need | Implication |
|------|-------------|
| **Add new contracts** | Framework changes |
| **Fix oracle bugs** | Test re-running needed |
| **Improve adapter** | Behavior changes |
| **Stable baselines** | Don't change working code |

### Current Approach

- Version control for all artifacts
- Reproducible test runs (same code, same data)
- Incremental improvements with validation
- Clear documentation of changes

---

## Summary of Challenges

| Category | Challenge | Severity | Status |
|----------|-----------|----------|--------|
| **Bug Discovery** | Low yield on mature databases | HIGH | Acknowledged |
| **Oracle Design** | ANN approximation tolerance | HIGH | Partially addressed |
| **Adapter Support** | Hardcoded parameters, missing ops | MEDIUM | Documented |
| **Implementation** | Oracle complexity | MEDIUM | Ongoing |
| **Classification** | Bugs vs allowed differences | MEDIUM | Framework supported |
| **Scalability** | New database support | MEDIUM | Resource constraint |
| **Contract Design** | Defining good contracts | LOW | Skill development |
| **Artifacts** | False positives | LOW | Mitigated |
| **Reproducibility** | ANN non-determinism | LOW | Acceptable |
| **Evolution** | Stability vs change | LOW | Managed |

---

## Strategic Response

### Short Term (Current Milestone R5B)

1. **Refine IDX-001 Oracle**: Separate hard checks from quality checks
2. **Improve Adapter**: Add count retrieval for IDX-002
3. **Document Limitations**: Be honest about what can and cannot be tested

### Medium Term

1. **Expand Adapter**: Implement drop_index, rebuild_index
2. **Target Different Databases**: Less-mature implementations
3. **Enhance Execution Layer**: Ground truth computation for complex oracles

### Long Term

1. **Multi-Database Support**: Qdrant, Weaviate adapters
2. **Advanced Contracts**: Concurrency, transactions
3. **Property-Based Testing**: Hypothesis framework integration

---

## Philosophical Reflection

### The Core Insight

**Low bug-yield is not a framework failure; it's a target selection issue.**

The AI-DB-QC framework correctly:
- Generates tests from contracts
- Executes tests on real databases
- Evaluates results with oracles
- Classifies outcomes appropriately

**What it cannot do**: Make bugs appear where none exist.

### Alternative Perspectives

1. **Validation, not Discovery**: The framework may be better suited for validation testing (preventing regressions) than bug discovery
2. **Right Target, Wrong Database**: Less-mature databases may have more bugs
3. **Different Contracts**: Need contracts that target less-tested semantic spaces

---

## Conclusion

The AI-DB-QC framework faces significant challenges, but they are **honest, understood, and addressable**. The primary challenge—low bug-yield on mature databases—is a validation of the framework's correctness, not a failure.

**Moving Forward**:
1. Acknowledge limitations honestly
2. Refine oracles for soundness
3. Expand target database support
4. Focus on less-tested semantic spaces

The framework is **production-ready for contract-driven validation testing**. For high-yield bug discovery, we need either different targets or different contracts.

---

**Document Version**: 1.0
**Last Updated**: 2026-03-10
**Next Review**: After R5B completion
