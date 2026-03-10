# Next Roadmap

**Project**: AI Database Quality Assurance Framework
**Document Version": 1.0
**Date**: 2026-03-10

---

## Executive Summary

This document outlines the strategic direction for the AI-DB-QC framework following the R1-R5C milestone completion. The roadmap is organized into three time horizons: **short-term** (next milestone), **medium-term** (next 3-6 months), and **long-term** (vision for a general AI database QA framework).

**Current Focus**: Complete R5B (Index Behavior Contracts) with refined oracle design.

---

## Short-Term: Next Milestone (R5B)

**Timeline**: 1-2 weeks
**Goal**: Validate index behavior contracts with sound oracle design
**Status**: Design complete, awaiting implementation

### R5B Scope

Revised from original 16 tests to **6 focused tests**:

| Contract | Tests | Focus |
|----------|-------|-------|
| **IDX-001** | 4 | Semantic neutrality (refined oracle) |
| **IDX-002** | 2 | Data preservation (create only) |

**Postponed**: IDX-003 (parameter validation), IDX-004 (multi-index) due to adapter limitations

### Pre-Implementation Tasks

| Task | Effort | Priority | Status |
|------|--------|----------|--------|
| Implement refined IDX-001 oracle | 2 hours | HIGH | Pending |
| Add count retrieval to adapter | 1 hour | HIGH | Pending |
| Generate 6 test cases | 30 min | HIGH | Pending |
| Validate on real Milvus | 1 hour | HIGH | Pending |

### Expected Outcomes

- **Framework**: Validated on index contracts
- **Bugs**: 0-1 violations expected (based on R5A/R5C patterns)
- **Oracle**: Refined design separates hard checks from quality checks
- **Deliverable**: R5B_INDEX_PILOT_REPORT_REVISED.md

### Success Criteria

1. All 6 tests execute successfully
2. Refined oracle correctly classifies results
3. No false violations from ANN approximation tolerance
4. Clear documentation of results

### Documentation

- Design: `docs/R5B_INDEX_PILOT_REVISED.md`
- Audit: `docs/R5B_PREIMPLEMENTATION_AUDIT.md`
- Decision: `docs/R5B_vs_R5D_DECISION.md`

---

## Medium-Term: Next 3-6 Months

### Phase 1: Complete Contract Families (R5D + R5B Full)

**Timeline**: 2-4 weeks after R5B completion

#### R5D: Schema/Metadata Contracts

**Goal**: Validate schema evolution and metadata accuracy

**Scope**: 4 contracts, ~8-10 tests

| Contract | Tests | Focus |
|----------|-------|-------|
| **SCH-001** | 2 | Schema evolution data preservation |
| **SCH-002** | 2 | Query compatibility across schema changes |
| **SCH-003** | 2 | Index rebuild after schema change |
| **SCH-004** | 2-4 | Metadata accuracy |

**Challenge**: Milvus has limited dynamic schema support

**Mitigation**: Focus on supported operations; document limitations

#### R5B Full: Complete Index Contracts

**Goal**: Complete postponed index contracts (IDX-003, IDX-004)

**Prerequisites**:
- Implement drop_index operation
- Implement rebuild_index operation
- Expose HNSW/IVF parameters
- Add multi-index support

**Estimated Effort**: 2-3 weeks for adapter enhancements + testing

---

### Phase 2: Multi-Database Validation

**Timeline**: 4-8 weeks after R5B/R5D completion

**Goal**: Expand testing to multiple databases for differential validation

#### Target Databases

| Database | Priority | Effort | Bug Yield Potential |
|----------|----------|--------|---------------------|
| **Qdrant** | HIGH | 2-3 weeks | HIGH (less mature) |
| **Weaviate** | MEDIUM | 2-3 weeks | HIGH (less mature) |
| **Pinecone** | LOW | 3-4 weeks | UNKNOWN (cloud-only) |

#### Adapter Development Plan

For each database:
1. Implement core operations (create, insert, search)
2. Implement index operations
3. Implement hybrid query support
4. Validate with existing contract tests
5. Run differential testing vs Milvus

#### Expected Outcomes

- **Comparative Analysis**: Cross-database behavior differences
- **Bug Discovery**: Higher yield on less-mature databases
- **Allowed Differences**: Document architectural variations
- **Contract Refinement**: Universal vs database-specific contracts

---

### Phase 3: Framework Enhancements

**Timeline**: Ongoing during Phases 1-2

#### Oracle Improvements

| Enhancement | Effort | Impact |
|-------------|--------|--------|
| **Ground truth computation** | HIGH | Enables ANN-003 full testing |
| **Metric calculation library** | MEDIUM | Enables ANN-004 full testing |
| **Probabilistic oracles** | HIGH | Better ANN approximation handling |
| **Compositional oracles** | MEDIUM | Complex contract validation |

#### Adapter Enhancements

| Enhancement | Effort | Impact |
|-------------|--------|--------|
| **Connection pooling** | LOW | Performance improvement |
| **Async operations** | HIGH | Parallel test execution |
| **Transaction support** | HIGH | Concurrency testing |
| **Comprehensive index operations** | MEDIUM | Full index contract coverage |

#### Test Generation Improvements

| Enhancement | Effort | Impact |
|-------------|--------|--------|
| **Property-based testing** | HIGH | Systematic input space exploration |
| **Combinatorial generation** | MEDIUM | Parameter interaction testing |
| **Adaptive test selection** | MEDIUM | Focus on high-yield areas |
| **Regression test selection** | LOW | Efficient re-testing |

---

## Long-Term: Vision (6-12 Months)

### Vision: General AI Database QA Framework

Transform AI-DB-QC into a **general-purpose quality assurance framework** for all AI databases, including:

- Vector databases (current focus)
- Graph databases (new)
- Time-series databases (new)
- Multi-model databases (new)

### Architecture Evolution

#### Current Architecture

```
Vector DB → Adapter → Oracle → Classification
```

#### Target Architecture

```
                    ┌─────────────────────────────────────┐
                    │        Contract Library             │
                    │  (Vector, Graph, Time-Series, etc.)  │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │      Contract-Driven Generator       │
                    └──────────────┬──────────────────────┘
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        │                          │                          │
┌───────▼────────┐      ┌─────────▼────────┐      ┌───────▼────────┐
│ Vector DB      │      │ Graph DB         │      │ Time-Series DB │
│ Adapter        │      │ Adapter           │      │ Adapter         │
└────────────────┘      └──────────────────┘      └────────────────┘
        │                          │                          │
        └──────────────────────────┼──────────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │         Universal Oracle Engine       │
                    │   (Domain-specific evaluation)        │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │          Classification Engine        │
                    │   (PASS, VIOLATION, ALLOWED_DIFF)    │
                    └──────────────────────────────────────┘
```

### New Contract Families

| Family | Focus | Complexity | Priority |
|--------|-------|------------|----------|
| **Concurrency** | Parallel operations, transactions | HIGH | HIGH |
| **Performance** | Latency, throughput, scaling | MEDIUM | MEDIUM |
| **Consistency** | Replication, synchronization | HIGH | HIGH |
| **Security** | Access control, encryption | MEDIUM | MEDIUM |
| **Reliability** | Fault tolerance, recovery | MEDIUM | MEDIUM |

### Advanced Oracle Techniques

#### 1. Probabilistic Oracles

For ANN and other approximate algorithms:

```python
class ProbabilisticOracle:
    """Oracle for probabilistic contracts."""

    def evaluate(self, result, contract):
        # Use statistical tests instead of binary thresholds
        # e.g., "recall is within 95% confidence interval"
        pass
```

#### 2. Property-Based Testing

Generate random inputs and check invariants:

```python
@given(search_vectors(), top_k(), index_types())
def test_search_invariants(vectors, k, index_type):
    """Property: search never crashes and returns valid results."""
    result = db.search(vectors, k, index_type)
    assert result is not None
    assert len(result) <= k
```

#### 3. Compositional Contracts

Combine multiple contracts:

```python
{
  "contract_id": "COMP-001",
  "name": "Hybrid Search Correctness",
  "components": ["HYB-001", "HYB-002", "ANN-002"],
  "composition": "ALL"
}
```

---

## Research Directions

### 1. Automatic Contract Discovery

**Problem**: Manual contract design is time-consuming

**Goal**: Automatically infer contracts from:
- Database documentation
- API specifications
- Observed behavior

**Approach**:
- NLP on documentation
- API reverse engineering
- Behavioral clustering

### 2. Oracle Learning

**Problem**: Manual oracle implementation is complex

**Goal**: Learn oracle decision boundaries from:
- Execution examples
- Human feedback
- Cross-database patterns

**Approach**:
- Supervised learning (classified results)
- Active learning (uncertainty sampling)
- Transfer learning (between databases)

### 3. Test Prioritization

**Problem**: Too many potential tests, limited execution time

**Goal**: Prioritize tests most likely to find bugs

**Approach**:
- Machine learning models trained on historical bugs
- Code coverage analysis
- Risk-based prioritization

---

## Productization Roadmap

### Phase 1: Research Prototype (Current)

**Status**: ✅ Complete

**Capabilities**:
- Contract-driven test generation
- Oracle-based evaluation
- Milvus adapter
- Basic CLI interface

**Users**: Researchers, academic collaborators

---

### Phase 2: Developer Tool (Next)

**Timeline**: 3-6 months

**Target Users**: Database developers, QA engineers

**Capabilities**:
- Multi-database support (Qdrant, Weaviate)
- Enhanced CLI with workflows
- CI/CD integration
- Bug report export

**Deliverables**:
- `pip install ai-db-qc` package
- Docker images for easy deployment
- Documentation and tutorials
- Example campaigns

---

### Phase 3: Enterprise Platform (Future)

**Timeline**: 12-18 months

**Target Users**: Enterprise QA teams, database vendors

**Capabilities**:
- Web UI for test management
- Scheduling and automation
- Collaboration features
- Analytics and dashboards
- API for integration

**Deliverables**:
- SaaS platform
- On-premise deployment option
- Enterprise support
- Custom integrations

---

## Milestone Timeline

```
┌────────────┐     ┌────────────┐     ┌────────────┐     ┌────────────┐
│            │     │            │     │            │     │            │
│   R1-R5C   │────▶│    R5B     │────▶│   R5D      │────▶│ Multi-DB   │
│  Complete  │     │  (Index)   │     │  (Schema)   │     │   Testing   │
│            │     │            │     │            │     │            │
└────────────┘     └────────────┘     └────────────┘     └────────────┘
   Current            1-2 weeks         2-4 weeks          8-12 weeks
   Milestone                           after R5B          after R5D

┌─────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│                           Vision: General AI-DB QA                       │
│                                                                          │
│  • Vector DBs (current)                                                 │
│  • Graph DBs (new)                                                      │
│  • Time-Series DBs (new)                                                │
│  • Multi-Model DBs (new)                                                │
│                                                                          │
│  • Probabilistic Oracles                                                │
│  • Property-Based Testing                                                │
│  • Automatic Contract Discovery                                         │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
                        6-12 months from now
```

---

## Resource Requirements

### Short-Term (R5B)

| Resource | Need | Availability |
|----------|------|--------------|
| **Developer time** | 10-15 hours | Available |
| **Milvus instance** | Running | Available |
| **Compute** | Standard | Available |
| **Storage** | Minimal | Available |

### Medium-Term (R5D + Multi-DB)

| Resource | Need | Availability |
|----------|------|--------------|
| **Developer time** | 100-150 hours | Need allocation |
| **Database instances** | 3-4 DBs | Need setup |
| **Compute** | Standard | Available |
| **Storage** | Moderate | Available |

### Long-Term (Vision)

| Resource | Need | Availability |
|----------|------|--------------|
| **Team** | 2-3 developers | Need hiring |
| **Infrastructure** | Cloud deployment | Need setup |
| **Research** | ML expertise | Need collaboration |
| **Funding** | Sustained | Need sponsorship |

---

## Risk Assessment

### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Low bug-yield continues** | HIGH | MEDIUM | Target less-mature DBs |
| **Oracle complexity** | MEDIUM | HIGH | Research investment |
| **Adapter scalability** | MEDIUM | MEDIUM | Standardized interface |
| **Database evolution** | HIGH | LOW | Track releases, adapt |

### Strategic Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Competition** | MEDIUM | HIGH | Focus on unique value |
| **Adoption barriers** | HIGH | MEDIUM | Simplify onboarding |
| **Funding sustainability** | MEDIUM | HIGH | Demonstrate value early |
| **Talent acquisition** | MEDIUM | MEDIUM | Academic partnerships |

---

## Success Metrics

### Short-Term (R5B)

- [ ] R5B pilot completed successfully
- [ ] Refined oracle validated
- [ ] 6 tests executed with clear results
- [ ] Documentation updated

### Medium-Term (R5D + Multi-DB)

- [ ] All 4 contract families validated
- [ ] 3+ databases supported
- [ ] 50+ contract violations discovered
- [ ] Framework production-ready

### Long-Term (Vision)

- [ ] General AI database QA framework
- [ ] 10+ databases supported
- [ ] 100+ contracts across all families
- [ ] Automated contract discovery
- [ ] Learned oracles
- [ ] Enterprise platform launch

---

## Conclusion

The AI-DB-QC framework has achieved significant progress through R1-R5C, validating the contract-driven approach to AI database testing. The next phase (R5B) focuses on index behavior contracts with refined oracle design, addressing the ANN approximation tolerance challenge identified in recent campaigns.

**Strategic Direction**:
1. **Near-term**: Complete contract families with sound oracles
2. **Medium-term**: Expand to multiple databases for higher bug-yield
3. **Long-term**: Evolve into general AI database QA framework

The framework is **production-ready for contract-driven validation testing**. For high-yield bug discovery, we need to expand our target databases and develop more sophisticated contracts for less-tested semantic spaces (concurrency, transactions, distributed operations).

---

**Document Version**: 1.0
**Last Updated**: 2026-03-10
**Next Review**: After R5B completion
**Maintainer**: AI-DB-QC Framework Team
