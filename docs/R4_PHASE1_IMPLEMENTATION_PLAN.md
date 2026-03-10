# R4 Phase 1: Minimal Implementation Plan

**Plan Version**: 1.0
**Date**: 2026-03-09
**Phase**: R4 Phase 1 - Minimal Adapter + Pilot Differential Campaign
**Status**: Plan - Pending Approval

---

## Executive Summary

This plan defines a minimal, low-risk expansion for R4 Phase 1:
1. Implement a minimal Qdrant adapter
2. Run a pilot differential campaign on 3 semantic properties
3. Validate the differential framework is working correctly

**Scope**: Pilot only - NOT full R4 campaign

---

## Part 1: Minimal Qdrant Adapter Implementation

### 1.1 Adapter Specification

**File**: `adapters/qdrant_adapter.py`

**Base Class**: `AdapterBase` (from `adapters/base.py`)

**Operations to Implement**:

| Method | Operation | Implementation Notes |
|--------|-----------|---------------------|
| `execute()` | Operation dispatcher | Routes to internal methods |
| `_create_collection()` | Create collection | Maps to `client.create_collection()` |
| `_insert()` | Upsert vectors | Maps to `client.upsert()` with PointStruct |
| `_search()` | Vector search | Maps to `client.search()` |
| `_delete()` | Delete by IDs | Maps to `client.delete()` with PointIdsList |
| `_drop_collection()` | Drop collection | Maps to `client.delete_collection()` |
| `_build_index()` | Build index | **NO-OP** (Qdrant auto-creates) |
| `_load()` | Load collection | **NO-OP** (Qdrant auto-loads) |

---

### 1.2 Operation Mapping (From R4_CAMPAIGN_PROPOSAL.md)

**Already Documented** - Alignment Required:

```python
# Mapping from generic operation to Qdrant API
OPERATION_MAPPING = {
    "create_collection": "client.create_collection()",
    "insert": "client.upsert()",
    "search": "client.search()",
    "delete": "client.delete()",
    "drop_collection": "client.delete_collection()",
    "build_index": "NO-OP (auto-creates HNSW)",
    "load": "NO-OP (auto-loads)"
}
```

---

### 1.3 Request/Response Format

**Input Format** (compatible with existing framework):

```python
request = {
    "operation": "create_collection",  # Operation name
    "params": {
        "collection_name": "test_pilot_001",
        "dimension": 128,
        "metric_type": "COSINE"
    }
}
```

**Output Format** (normalized across adapters):

```python
response = {
    "status": "success",  # or "error"
    "data": {...},        # Operation-specific data
    "error": None         # Error message if status="error"
}
```

---

### 1.4 Key Implementation Details

#### ID Auto-Generation

**Problem**: Qdrant requires explicit IDs in `PointStruct`, Milvus can auto-generate

**Solution**: Adapter auto-generates IDs if not provided

```python
def _insert(self, params: Dict) -> Dict:
    vectors = params.get("vectors", [])
    ids = params.get("ids", None)

    # Auto-generate IDs if not provided
    if ids is None:
        ids = list(range(len(vectors)))

    points = [
        models.PointStruct(
            id=ids[i],
            vector=vectors[i],
            payload=params.get("payload", {})
        )
        for i in range(len(vectors))
    ]

    self.client.upsert(
        collection_name=params["collection_name"],
        points=points
    )
    return {"status": "success", "data": {"inserted_count": len(points)}}
```

---

#### No-Op Methods

**Implementation**:

```python
def _build_index(self, params: Dict) -> Dict:
    """Qdrant auto-creates HNSW index - no-op for compatibility."""
    return {"status": "success", "data": {"note": "Qdrant auto-creates index"}}

def _load(self, params: Dict) -> Dict:
    """Qdrant auto-loads collections - no-op for compatibility."""
    return {"status": "success", "data": {"note": "Qdrant auto-loads"}}
```

---

#### Connection Management

**Constructor**:

```python
def __init__(self, connection_config: Dict[str, Any]):
    """Initialize Qdrant adapter.

    Args:
        connection_config: Dict with keys:
            - url (str): Qdrant URL, default "http://localhost:6333"
            - timeout (float): Request timeout, default 30.0
    """
    self.url = connection_config.get("url", "http://localhost:6333")
    self.timeout = connection_config.get("timeout", 30.0)
    self._connect()
```

---

### 1.5 Error Handling

**Strategy**: Catch Qdrant exceptions and normalize to common format

```python
try:
    # Qdrant operation
    result = self.client.search(...)
    return {"status": "success", "data": result}
except Exception as e:
    return {
        "status": "error",
        "error": str(e),
        "error_type": type(e).__name__
    }
```

---

### 1.6 Minimal Adapter Interface Summary

**Public Methods**:
- `__init__(connection_config)` - Initialize adapter
- `execute(request)` - Execute operation (required by AdapterBase)
- `health_check()` - Check connection health (inherited from AdapterBase)

**Internal Methods** (operation implementations):
- `_create_collection(params)`
- `_insert(params)`
- `_search(params)`
- `_delete(params)`
- `_drop_collection(params)`
- `_build_index(params)` - NO-OP
- `_load(params)` - NO-OP

---

## Part 2: Pilot Differential Campaign

### 2.1 Selected Pilot Properties

**User-Selected Properties** (3 total):

| Property | Name | Test Complexity | Oracle Rule |
|----------|------|-----------------|-------------|
| **Property 1** | Post-Drop Rejection | Simple | Rule 1 |
| **Property 3** | Delete Idempotency | Simple | Rule 4 |
| **Property 7** | Non-Existent Delete Tolerance | Simple | Rule 4 |

**Rationale**: These 3 properties:
1. Cover core delete/drop behaviors
2. Have clear oracle rules
3. Require minimal setup (no complex state)
4. Can be tested with existing adapter operations

---

### 2.2 Pilot Test Cases

#### Case Pilot-001: Post-Drop Rejection (Property 1)

**Sequence**:
```yaml
1. create_collection(name="pilot_001", dimension=128)
2. insert(vectors=[[0.1]*128, [0.9]*128])
3. build_index()  # Optional: Milvus executes, Qdrant skips
4. load()         # Optional: Milvus executes, Qdrant skips
5. search(query_vector=[0.1]*128, top_k=10)  # Baseline
6. drop_collection(name="pilot_001")
7. search(query_vector=[0.1]*128, top_k=10)  # TEST: must fail
```

**Expected**:
- Step 7: Both databases must fail with "not found" error

**Oracle Classification**:
- ✅ **CONSISTENT**: Both fail → PASS
- ❌ **BUG**: One allows post-drop search → BUG in that database
- ⚠️ **ALLOWED**: Different error messages (same meaning)

---

#### Case Pilot-002: Delete Idempotency (Property 3)

**Sequence**:
```yaml
1. create_collection(name="pilot_002", dimension=128)
2. insert(vectors=[[0.1]*128], ids=[100])
3. build_index()  # Optional
4. load()         # Optional
5. delete(ids=[100])  # First delete
6. delete(ids=[100])  # TEST: Second delete - should be deterministic
```

**Expected**:
- Step 6: Either always succeeds OR always fails with "not found"

**Oracle Classification**:
- ✅ **CONSISTENT**: Both have same behavior → PASS
- ⚠️ **ALLOWED**: Different strategies (success vs. not found)
- ❌ **BUG**: Inconsistent behavior (random)

---

#### Case Pilot-003: Non-Existent Delete Tolerance (Property 7)

**Sequence**:
```yaml
1. create_collection(name="pilot_003", dimension=128)
2. delete(ids=[999])  # TEST: Delete non-existent ID
```

**Expected**:
- Step 2: Success OR fail with clear "not found"

**Oracle Classification**:
- ✅ **CONSISTENT**: Both handle consistently → PASS
- ⚠️ **ALLOWED**: Different approaches (silent vs. error)
- ❌ **BUG**: Inconsistent behavior

---

### 2.3 Pilot Execution Strategy

**File**: `scripts/run_pilot_differential_r4.py`

**Approach**: Sequential execution on both databases

```python
def run_pilot_differential():
    # 1. Initialize both adapters
    milvus = MilvusAdapter(config_milvus)
    qdrant = QdrantAdapter(config_qdrant)

    # 2. Execute each test case on both databases
    for test_case in pilot_cases:
        # Run on Milvus
        milvus_results = run_sequence(milvus, test_case)

        # Run on Qdrant
        qdrant_results = run_sequence(qdrant, test_case)

        # 3. Compare results
        comparison = compare_results(milvus_results, qdrant_results)

        # 4. Apply oracle classification
        classification = apply_oracle(comparison, test_case["oracle_rule"])

        # 5. Record findings
        record_finding(test_case, milvus_results, qdrant_results, classification)
```

---

### 2.4 Differential Comparison Logic

**What to Compare**:

| Aspect | Comparison Method | Oracle Treatment |
|--------|-------------------|------------------|
| **Step status** | success/error match | BUG if one succeeds, one fails (when both should fail) |
| **Error presence** | Both error vs. one errors | Check semantic meaning |
| **Error type** | Exact match | ALLOWED if same meaning |
| **Result data** | IDs returned, counts | BUG if deleted entity visible |

**What NOT to Compare** (Allowed Differences):
- Error message wording (same meaning, different phrasing)
- Performance characteristics
- Intermediate states (load, index existence)

---

## Part 3: Expected Artifact Outputs

### 3.1 Per-Database Raw Results

**File**: `results/r4-pilot-YYYYMMDD-HHMMSS/raw/`

**Format**: JSON files per database per case

```json
// milvus_pilot_001.json
{
  "database": "milvus",
  "case_id": "pilot_001",
  "property": "Post-Drop Rejection",
  "steps": [
    {
      "step": 1,
      "operation": "create_collection",
      "status": "success",
      "data": {...}
    },
    {
      "step": 7,
      "operation": "search",
      "status": "error",
      "error": "Collection not exist"
    }
  ]
}

// qdrant_pilot_001.json
{
  "database": "qdrant",
  "case_id": "pilot_001",
  "property": "Post-Drop Rejection",
  "steps": [...]
}
```

---

### 3.2 Differential Classification

**File**: `results/r4-pilot-YYYYMMDD-HHMMSS/differential/`

**Format**: JSON files with classification per case

```json
// pilot_001_classification.json
{
  "case_id": "pilot_001",
  "property": "Post-Drop Rejection",
  "oracle_rule": "Rule 1 (Search After Drop)",
  "comparison": {
    "milvus_step_7": {"status": "error", "error": "Collection not exist"},
    "qdrant_step_7": {"status": "error", "error": "collection not found"}
  },
  "classification": "CONSISTENT",
  "reasoning": "Both databases correctly fail with 'not found' error",
  "findings": []
}
```

---

### 3.3 Pilot Report

**File**: `docs/R4_PILOT_REPORT.md`

**Sections**:

1. **Executive Summary**
   - Pilot completion status
   - Framework validation result
   - Recommendation for full R4

2. **Test Execution Summary**
   - Test cases executed
   - Per-database success rate
   - Differential classification results

3. **Per-Property Results**
   - Property 1: Post-Drop Rejection
   - Property 3: Delete Idempotency
   - Property 7: Non-Existent Delete Tolerance

4. **Differential Findings**
   - CONSISTENT behaviors
   - ALLOWED differences found
   - BUGS found (if any)

5. **Framework Validation**
   - Is differential comparison working?
   - Is oracle classification correct?
   - Any adaptation issues?

6. **Recommendations**
   - Is framework ready for full R4?
   - Any adapter improvements needed?
   - Next steps

---

### 3.4 Artifact Checklist

| Artifact | Location | Purpose |
|----------|----------|---------|
| `adapters/qdrant_adapter.py` | Created | Minimal Qdrant adapter |
| `scripts/run_pilot_differential_r4.py` | Created | Pilot execution script |
| `results/r4-pilot-*/raw/*.json` | Generated | Per-database raw results |
| `results/r4-pilot-*/differential/*.json` | Generated | Differential classifications |
| `docs/R4_PILOT_REPORT.md` | Created | Pilot findings report |

---

## Part 4: Risk Mitigation

### 4.1 Implementation Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Adapter bugs cause false findings | Medium | High | Validate adapter with smoke test first |
| ID generation mismatch | Low | Medium | Use consistent ID scheme across both |
| Comparison logic errors | Medium | High | Manual verification of classifications |
| Oracle misclassification | Low | High | Review all classifications manually |

---

### 4.2 Scope Constraints

**Pilot Limitations** (will NOT do):
- Full 8-property testing
- Complex state management tests
- Performance comparisons
- Scalability tests
- Edge case exploration

**Pilot Focus** (will do):
- Validate adapter works
- Validate differential comparison
- Validate oracle classification
- Identify any blocking issues

---

## Part 5: Success Criteria

### 5.1 Technical Success

- ✅ Qdrant adapter implements all 7 operations
- ✅ Adapter passes smoke test (7/7 operations)
- ✅ Pilot executes on both databases
- ✅ Differential comparison produces output
- ✅ Oracle classification applied correctly

### 5.2 Framework Validation

- ✅ Differential results are generated per property
- ✅ Classifications are consistent with oracle rules
- ✅ Raw results are saved for both databases
- ✅ Report clearly states pilot vs. full R4 scope

### 5.3 Go/No-Go for Full R4

**Go Criteria** (all must be true):
1. Pilot executes without crashes
2. Differential comparison produces meaningful output
3. Oracle classifications are correct
4. No fundamental framework issues found

**No-Go Indicators** (any red flags):
1. Adapter cannot execute basic operations
2. Differential comparison logic is fundamentally flawed
3. Oracle classifications are consistently wrong
4. Major architectural incompatibility discovered

---

## Part 6: Timeline and Effort

### 6.1 Implementation Effort

| Task | Estimated Time |
|------|----------------|
| Qdrant adapter implementation | 2-3 hours |
| Adapter testing and debugging | 1-2 hours |
| Pilot script implementation | 2-3 hours |
| Pilot execution and validation | 1-2 hours |
| Report writing | 1-2 hours |
| **Total** | **7-12 hours** |

---

### 6.2 Dependencies

**Required**:
- ✅ R4.0 smoke test passed (Qdrant validated)
- ✅ Qdrant container running (localhost:6333)
- ✅ Milvus running (localhost:19530)
- ✅ qdrant-client installed (1.9.2)
- ✅ pymilvus installed (2.6.2)

**Optional**:
- Differential oracle design docs (reference)
- Semantic properties definitions (reference)

---

## Part 7: Implementation Order

### Phase 1: Adapter Implementation (2-3 hours)

1. Create `adapters/qdrant_adapter.py`
2. Implement `__init__()` and `_connect()`
3. Implement core operations:
   - `_create_collection()`
   - `_insert()` (with ID auto-generation)
   - `_search()`
   - `_delete()`
   - `_drop_collection()`
4. Implement no-op methods:
   - `_build_index()`
   - `_load()`
5. Test adapter with smoke test

### Phase 2: Pilot Script (2-3 hours)

1. Create `scripts/run_pilot_differential_r4.py`
2. Define 3 pilot test cases
3. Implement sequential execution logic
4. Implement differential comparison
5. Implement oracle classification
6. Implement result writing

### Phase 3: Execution and Reporting (2-4 hours)

1. Run pilot on both databases
2. Collect raw results
3. Apply differential comparison
4. Classify findings
5. Generate pilot report
6. Validate recommendations

---

## Part 8: Key Design Decisions

### 8.1 Minimal Adapter Scope

**Decision**: Implement only operations required for pilot

**Rationale**:
- Reduces implementation risk
- Validates framework before full investment
- Can extend adapter later if pilot succeeds

**Trade-off**: Not all R4 operations supported yet

---

### 8.2 No-Op Methods for State Management

**Decision**: `_build_index()` and `_load()` are no-ops for Qdrant

**Rationale**:
- Qdrant auto-indexes and auto-loads
- Keeps adapter interface compatible with Milvus
- Aligns with operation mapping in R4 proposal

**Trade-off**: Caller must understand these are no-ops for Qdrant

---

### 8.3 Sequential Execution (Not Parallel)

**Decision**: Execute tests sequentially on each database

**Rationale**:
- Simpler implementation
- Easier debugging
- No concurrency issues

**Trade-off**: Slower than parallel execution (acceptable for pilot)

---

### 8.4 Manual Classification Review

**Decision**: Report includes recommendation but requires manual review

**Rationale**:
- Oracle framework is new
- Pilot should validate framework correctness
- Human judgment needed for edge cases

**Trade-off**: Not fully automated (acceptable for pilot)

---

## Metadata

- **Plan**: R4 Phase 1 Minimal Implementation Plan
- **Version**: 1.0
- **Date**: 2026-03-09
- **Phase**: R4 Phase 1 - Pilot Only
- **Pilot Properties**: 3 (Properties 1, 3, 7)
- **Estimated Effort**: 7-12 hours
- **Status**: Plan - Pending Approval

---

## Summary for User Approval

**Before Implementation**:

1. **Minimal Adapter Implementation Plan** ✅ (Part 1)
   - 7 operations: create, insert, search, delete, drop, build_index (no-op), load (no-op)
   - Aligns with R4_CAMPAIGN_PROPOSAL.md operation mapping
   - ID auto-generation for Qdrant compatibility

2. **Selected Pilot Properties** ✅ (Part 2)
   - Property 1: Post-Drop Rejection
   - Property 3: Delete Idempotency
   - Property 7: Non-Existent Delete Tolerance

3. **Expected Artifact Outputs** ✅ (Part 3)
   - Per-database raw results (JSON)
   - Differential classifications (JSON)
   - Pilot report (markdown)
   - NOT full R4 results

---

**END OF R4 PHASE 1 IMPLEMENTATION PLAN**

**Awaiting**: User approval to proceed with implementation
