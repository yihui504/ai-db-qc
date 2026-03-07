# Multi-Database Strategy: AI-Native Coverage

> **Status**: Revised strategy for Phase 1+ expansion
> **Updated**: 2026-03-07

## Overview

This document revises the multi-database bug-mining strategy to explicitly include **seekdb** as a first-class AI-native database target, alongside classic vector databases.

### Strategic Shift

**Previous framing**: "Multi-vector-database mining"
**Revised framing**: "Classic vector database + AI-native database coverage"

This distinction matters because:
- **Classic vector databases** (Milvus, Qdrant, Weaviate) focus on vector similarity search
- **AI-native databases** (seekdb) integrate search, multi-model data, and in-database AI workflows

The research topic—**AI database quality control**—requires coverage of both paradigms.

---

## Database Priority

### Primary Targets (Required for publication)

| Database | Type | Why It Matters |
|----------|------|----------------|
| **Milvus** | Classic Vector DB | Open-source baseline, established in research |
| **Qdrant** | Classic Vector DB | High-performance Rust implementation, growing adoption |
| **seekdb** | AI-Native Search DB | **First-class target**: hybrid search, multi-model, AI workflows |

### Secondary Validation Target

| Database | Type | Why It Matters |
|----------|------|----------------|
| **Weaviate** | Classic Vector DB | GraphQL-based vector database, provides validation diversity |

---

## Why seekdb Is a First-Class Target

seekdb is not just another vector database. Its architecture makes it **especially relevant** to AI database quality control research:

### 1. AI-Native Architecture

**Hybrid Search**: Combines vector similarity with keyword search, requiring consistency validation across multiple query modes.

**Multi-Model Data**: Supports text, vectors, images, and structured data in a unified index—testing cross-modal constraint handling.

**In-Database AI Workflows**: Embeddings generation, reranking, and semantic analysis happen within the database—testing pipeline integrity.

### 2. Research Relevance

**Quality Control Challenges**:
- **Hybrid search consistency**: Does keyword + vector search return coherent results?
- **Multi-model schema constraints**: Do text/vector/image references maintain integrity?
- **Pipeline correctness**: Do in-database AI workflows produce deterministic outputs?
- **State management**: How does seekdb handle complex multi-stage queries?

**Different Failure Modes**:
- Classic vector databases: mostly Type 1-3 (input validity, diagnostics, legal failures)
- AI-native databases: plus Type 4 (semantic violations in hybrid/multi-model contexts)

### 3. Publication Value

Including seekdb strengthens the paper by:
- Demonstrating applicability beyond pure vector search
- Showing the framework handles AI-native database complexity
- Providing forward-looking validation (AI-native is the trend)

---

## Minimal Adapter Work for seekdb

### Adapter Architecture (Stable)

The existing `AdapterBase` interface is sufficient:

```python
class AdapterBase(ABC):
    @abstractmethod
    def execute(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a request and return raw response."""
        pass

    def health_check(self) -> bool:
        """Check if adapter is healthy."""
        return True
```

### seekdb-Specific Requirements

seekdb has different APIs and semantics than Milvus. The minimal adapter needs:

1. **Connection Management**
   - REST API endpoint or SDK connection
   - Authentication (API key or token)
   - Health check endpoint

2. **Operation Mapping**
   - Hybrid search (vector + keyword)
   - Multi-model data insertion
   - Schema creation with multi-model fields
   - Complex query execution

3. **Response Normalization**
   - Convert seekdb responses to standard schema
   - Extract error messages for triage
   - Return results in consistent format

### Implementation Estimate

**Minimal seekdb adapter**: ~400-600 lines
- Connection and authentication: 50 lines
- Operation execution: 200 lines
- Response normalization: 150 lines
- Error handling: 100 lines

**No architecture changes required**—seekdb adapter is a drop-in extension.

---

## High-Yield Case Families for seekdb

### 1. Hybrid Search Consistency

**Research Question**: When a query combines vector similarity and keyword search, are results coherent?

**Test Cases**:
- **Pure vector search**: Results should be ranked by similarity
- **Pure keyword search**: Results should match keywords exactly
- **Hybrid search (both)**: Results should be coherent fusion of both modes
- **Hybrid with mismatch**: Vector says "relevant", keyword says "not found" → what happens?

**Expected Bugs**:
- **Type 4**: Hybrid fusion violates monotonicity (better vector score makes result worse)
- **Type 4**: Keyword match overrides strong vector similarity without explanation
- **Type 2**: "Invalid hybrid query" without specifying which mode failed

**Oracle**: `HybridSearchConsistency`
- Validates: `hybrid_score` is monotonic with respect to both vector and keyword scores
- Checks: Results present in both pure modes appear in hybrid mode
- Detects: Fusion function breaks expected ranking properties

### 2. Multi-Model Schema Constraints

**Research Question**: When text, vectors, and images reference the same entities, do constraints maintain integrity?

**Test Cases**:
- **Insert text entity**: Document with text field
- **Insert vector entity**: Same document ID with vector embedding
- **Insert image entity**: Same document ID with image reference
- **Query across modes**: Search by text, retrieve by vector, reference by image
- **Delete cascade**: Delete text entity, what happens to vector/image references?

**Expected Bugs**:
- **Type 4**: Multi-model reference violation (text deleted but vector still searchable)
- **Type 4**: Schema constraint violated (image references non-existent text entity)
- **Type 2**: "Invalid multi-model insert" without specifying which field failed

**Oracle**: `MultiModelConsistency`
- Validates: Cross-modal references maintain referential integrity
- Checks: Delete operations cascade correctly across all models
- Detects: Orphaned references (one model deleted, others remain)

### 3. Diagnostic Quality for AI Workflows

**Research Question**: When in-database AI workflows (embedding, reranking) fail, are errors diagnostic?

**Test Cases**:
- **Embedding generation fails**: "Out of quota" vs "Embedding service error: quota exceeded (1000/1000)"
- **Reranking fails**: "Invalid rerank parameters" vs "rerank_model='invalid' (must be one of: cohere, jina)"
- **Pipeline state errors**: "Workflow failed" vs "Step 2 (rerank) failed: input format incompatible with model"

**Expected Bugs**:
- **Type 2**: Poor diagnostics for AI workflow failures
- **Type 2.PF**: Precondition fails (API key missing) without clear explanation
- **Type 1**: AI workflow succeeds with invalid parameters (should fail)

**Oracle**: `AIPipelineCorrectness`
- Validates: Workflow steps execute in valid order
- Checks: Input/output formats between pipeline stages are compatible
- Detects: Stage skips, type mismatches, missing required state

### 4. Precondition/State Handling for Complex Queries

**Research Question**: When seekdb manages complex multi-stage queries, are preconditions checked correctly?

**Test Cases**:
- **Index must be built**: Search without building index first
- **Schema must exist**: Multi-model insert without schema creation
- **API key required**: AI workflow without authentication
- **Collection must be loaded**: Search on unloaded collection
- **State-dependent operations**: Rerank requires search results first

**Expected Bugs**:
- **Type 2.PF**: Precondition fails with generic "operation failed"
- **Type 2**: State error without specifying which precondition failed
- **Type 3**: Legal operation fails after all preconditions satisfied

**Oracle**: `StatefulPrecondition`
- Validates: Complex preconditions are checked in correct order
- Checks: State dependencies between operations are maintained
- Detects: State corruption, skipped initialization, premature cleanup

---

## Campaign Design with seekdb

### Phase 1: Foundation (Current) ✅
- **Target**: Milvus only
- **Status**: Complete

### Phase 2: Multi-Vector Coverage (Next)
- **Target**: Add Qdrant
- **Adapter Work**: ~300 lines (simpler than Milvus)
- **Case Families**: Same as Milvus (basic CRUD, search, filtering)
- **Timeline**: 2-3 weeks

### Phase 3: AI-Native Coverage (Key Addition)
- **Target**: Add seekdb
- **Adapter Work**: ~400-600 lines (more complex due to hybrid/multi-model)
- **Case Families**: Hybrid search, multi-model constraints, AI workflows
- **Timeline**: 4-6 weeks

### Phase 4: Validation & Diversity
- **Target**: Add Weaviate (validation)
- **Adapter Work**: ~300 lines
- **Case Families**: Cross-database comparison cases
- **Timeline**: 2-3 weeks

### Publication Readiness

After Phase 3, the paper can claim:
- **Coverage**: 2 classic vector DBs (Milvus, Qdrant) + 1 AI-native DB (seekdb)
- **Diversity**: Pure vector search + hybrid search + AI workflows
- **Bug Types**: All 4 types demonstrated across databases
- **Scalability**: Framework adapts to different database paradigms

---

## Architecture Stability

### No Changes Required

The existing architecture supports seekdb without modification:

**Adapter Interface**: Unchanged, seekdb adapter implements `AdapterBase`

**Contract System**: seekdb operations added to `default_contract.yaml`

**Profile System**: `seekdb_profile.yaml` defines seekdb-specific parameters

**Oracle System**: New oracles (`HybridSearchConsistency`, `MultiModelConsistency`) work with existing infrastructure

**Triage Pipeline**: No changes—handles seekdb responses like any other database

**Evidence Writing**: No changes—output format is database-agnostic

### Extension Points

seekdb integration uses existing extension points:

1. **Adapters**: New `SeekDBAdapter` in `adapters/`
2. **Contracts**: Extend `default_contract.yaml` with seekdb operations
3. **Profiles**: Add `seekdb_profile.yaml` in `contracts/db_profiles/`
4. **Oracles**: Add seekdb-specific oracles in `oracles/`
5. **Templates**: Add seekdb-specific cases in `casegen/templates/`

---

## Implementation Roadmap

### Milestone 1: seekdb Adapter (Week 1-2)

**Tasks**:
1. Create `adapters/seekdb_adapter.py`
2. Implement connection and authentication
3. Implement basic operations (search, insert, delete)
4. Implement hybrid search operation
5. Add response normalization
6. Add error message extraction

**Deliverable**: Working seekdb adapter with basic functionality

### Milestone 2: seekdb Contract & Profile (Week 2)

**Tasks**:
1. Define seekdb operations in `contracts/core/default_contract.yaml`
2. Create `contracts/db_profiles/seekdb_profile.yaml`
3. Define parameter schemas for hybrid search
4. Define parameter schemas for multi-model data
5. Document seekdb-specific preconditions

**Deliverable**: seekdb contract and profile with complete operation coverage

### Milestone 3: Hybrid Search Oracle (Week 3)

**Tasks**:
1. Create `oracles/hybrid_search_consistency.py`
2. Implement fusion validation logic
3. Implement mode comparison (pure vector vs pure keyword vs hybrid)
4. Add monotonicity checks for hybrid scores
5. Test on real seekdb instances

**Deliverable**: `HybridSearchConsistency` oracle with validation logic

### Milestone 4: Multi-Model Consistency Oracle (Week 4)

**Tasks**:
1. Create `oracles/multimodel_consistency.py`
2. Implement cross-modal reference checking
3. Implement cascade validation for deletes
4. Add orphaned reference detection
5. Test on multi-model seekdb collections

**Deliverable**: `MultiModelConsistency` oracle with cross-modal validation

### Milestone 5: seekdb Test Templates (Week 4-5)

**Tasks**:
1. Create `casegen/templates/seekdb_hybrid_search.yaml`
2. Create `casegen/templates/seekdb_multimodel.yaml`
3. Create `casegen/templates/seekdb_ai_workflows.yaml`
4. Create `casegen/templates/seekdb_preconditions.yaml`
5. Validate templates generate correct test cases

**Deliverable**: 4 seekdb-specific template files with 20-30 test cases

### Milestone 6: seekdb Bug Mining Campaign (Week 5-6)

**Tasks**:
1. Run bug-mining campaigns on seekdb instances
2. Collect evidence and classify findings
3. Analyze bug type distribution
4. Compare with Milvus/Qdrant results
5. Document seekdb-specific findings

**Deliverable**: Complete seekdb bug-mining campaign with documented findings

---

## Success Criteria

### Technical Success Criteria

1. **Adapter Completeness**: seekdb adapter supports all targeted operations
2. **Oracle Coverage**: Hybrid search and multi-model oracles detect violations
3. **Template Quality**: seekdb templates generate valid, diverse test cases
4. **Bug Discovery**: Campaign discovers novel bugs in at least 2 case families

### Research Success Criteria

1. **Cross-Paradigm Coverage**: Framework handles both vector DB and AI-native DB
2. **Bug Diversity**: All 4 bug types found across at least 2 databases
3. **Type-4 Representation**: seekdb contributes unique Type-4 cases (hybrid/multi-model)
4. **Publication Readiness**: Results demonstrate framework generality

---

## Risk Assessment

### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| seekdb API complexity | Medium | Medium | Start with basic operations, extend incrementally |
| Hybrid search semantic ambiguity | High | High | Define clear fusion properties to validate |
| Multi-model state explosion | Medium | Medium | Focus on 2-3 modalities (text, vector, image) |
| seekdb instance availability | Medium | Low | Use cloud trials or local Docker setup |

### Research Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| seekdb findings duplicate Milvus | Low | Low | Focus on seekdb-specific features (hybrid, AI) |
| Oracles too conservative | Medium | Medium | Tune oracle thresholds on known-good cases |
| Paper reviewers question AI-native relevance | Low | Medium | Emphasize forward-looking nature of AI databases |

---

## Summary

**Strategic shift**: From "multi-vector-database" to "vector database + AI-native database coverage"

**Why seekdb matters**:
- AI-native architecture (hybrid search, multi-model, AI workflows)
- Different failure modes from classic vector databases
- Strengthens paper's forward-looking relevance

**Minimal architecture change**: seekdb is a drop-in adapter using existing extension points

**High-yield case families**:
1. Hybrid search consistency (unique to seekdb)
2. Multi-model schema constraints (unique to seekdb)
3. Diagnostic quality for AI workflows (seekdb-specific)
4. Precondition/state handling for complex queries (seekdb-specific)

**Timeline**: 4-6 weeks to full seekdb integration, aligned with Phase 3 of overall roadmap

**Architecture stability**: ✅ No changes required—seekdb extends, doesn't modify existing architecture
