# Paper Cases: Milvus vs seekdb Behavioral Differences

**Campaign**: Differential v3
**Date**: 2026-03-07
**Selection**: 3 strongest cases for publication

---

## Case Selection Criteria

Cases selected for paper publication must:
1. ✅ Be genuine behavioral differences (not bugs or noise)
2. ✅ Have clear implications for users
3. ✅ Be well-understood and explainable
4. ✅ Demonstrate interesting database design trade-offs

**Selected Cases**:
1. Dimension limit difference (capability boundary)
2. Index validation philosophy difference (validation strictness)
3. State management architectural difference (architectural)

---

## Case 1: Dimension Limit Difference

**Case ID**: boundary-002-dim-max (from v2)
**Type**: Capability-boundary difference
**Paper Value**: ⭐⭐⭐ High

### Description

Milvus and seekdb have different maximum dimension limits for vector columns:

| Database | Max Dimension | Behavior at Limit |
|----------|---------------|-------------------|
| **Milvus** | 32768 | Accepts dimension=32768 |
| **seekdb** | 16000 | Rejects dimension > 16000 |

### Reproduction

```python
# Attempt to create collection with dimension=32768
dimension = 32768

# Milvus: SUCCESS
# Creates collection with 32768-dimensional vectors

# seekdb: FAILURE
# Error: "vector column dim larger than 16000 is not supported"
```

### Analysis

**Technical Explanation**:
- Milvus uses a different storage/indexing format that supports higher dimensions
- seekdb has a lower dimension limit, possibly due to underlying storage constraints
- The difference (32768 vs 16000) is approximately 2x

**User Impact**:
- Applications with >16000 dimensions must use Milvus
- Applications with ≤16000 dimensions can use either database
- Dimensionality reduction techniques needed for seekdb with high-dim data

### Design Trade-offs

| Aspect | Milvus (higher limit) | seekdb (lower limit) |
|--------|----------------------|---------------------|
| Flexibility | Supports high-dim embeddings | Limited to lower dimensions |
| Performance | May trade performance for flexibility | Optimized for common dimensions |
| Storage | May require more overhead | Optimized for typical use cases |

### Research Significance

This case demonstrates that **vector databases have different capability boundaries** that impact:
- Application compatibility (high-dim embeddings require specific databases)
- Migration strategies (dimension reduction may be required)
- Database selection criteria (dimension limits are key differentiator)

---

## Case 2: Index Validation Philosophy Difference

**Case ID**: cap-006-invalid-index-type
**Type**: Validation strictness difference
**Paper Value**: ⭐⭐⭐ High

### Description

Milvus and seekdb have different validation philosophies for index type parameters:

| Database | index_type Validation | Behavior |
|----------|----------------------|----------|
| **Milvus** | Strict | Rejects invalid index_type with specific error |
| **seekdb** | Permissive | Accepts invalid index_type without validation |

### Reproduction

```python
# Attempt to build index with invalid type
index_type = "INVALID_INDEX"

# Milvus: FAILURE
# Error: "invalid index type: INVALID_INDEX"

# seekdb: SUCCESS
# No error - accepts invalid index type
```

### Analysis

**Technical Explanation**:
- Milvus validates index_type at index creation time (fail-fast)
- seekdb does not validate index_type (may defer or ignore)
- This represents a fundamental difference in validation philosophy

**User Impact**:
- Milvus: Immediate feedback on invalid input, clear error message
- seekdb: Silent acceptance may cause confusion or silent failures later

### Design Trade-offs

| Philosophy | Milvus (Strict) | seekdb (Permissive) |
|------------|-----------------|---------------------|
| **Error detection** | Immediate (fail-fast) | Deferred or never |
| **User experience** | Clear, actionable errors | May confuse with silent success |
| **Flexibility** | Less flexible (only supported types) | More flexible (accepts any string) |
| **Debugging** | Easy (error at source) | Difficult (failure elsewhere) |

### Research Significance

This case demonstrates **two competing philosophies in parameter validation**:

1. **Strict validation** (Milvus):
   - Advantages: Fail-fast, clear errors, prevents invalid state
   - Disadvantages: Less flexible, more restrictive

2. **Permissive validation** (seekdb):
   - Advantages: More flexible, easier to experiment
   - Disadvantages: Silent failures, difficult debugging

The choice between these philosophies represents a **fundamental design decision** in database API design.

---

## Case 3: State Management Architectural Difference

**Case ID**: precond-002-search-no-index-no-data
**Type**: Architectural difference
**Paper Value**: ⭐⭐⭐ High

### Description

Milvus and seekdb have different state management requirements for search operations:

| Database | Empty Collection Search | State Management Philosophy |
|----------|------------------------|----------------------------|
| **Milvus** | Fails (requires load) | Strict: Explicit state control |
| **seekdb** | Succeeds (empty results) | Permissive: Implicit state handling |

### Reproduction

```python
# Create empty collection (no data, no index)
collection = create_collection("empty_test", dimension=128)

# Attempt search on empty collection
search(collection, vector=query_vector, top_k=10)

# Milvus: FAILURE
# Error: "collection not loaded"
# Requires explicit load() before any search

# seekdb: SUCCESS
# Returns empty results
# No explicit load() required
```

### Analysis

**Technical Explanation**:
- Milvus requires explicit `load()` operation before search (strict state)
- seekdb can search without explicit load (permissive state)
- This difference persists even for empty collections

**User Impact**:
- **Milvus**: More setup steps (create → insert → index → load → search)
- **seekdb**: Fewer setup steps (create → insert → search)
- **Milvus**: Explicit control over when data is loaded into memory
- **seekdb**: Implicit state management

### Design Trade-offs

| Aspect | Milvus (Strict) | seekdb (Permissive) |
|--------|-----------------|---------------------|
| **Setup complexity** | Higher (load required) | Lower (no load needed) |
| **Memory control** | Explicit (user controls) | Implicit (database manages) |
| **State transparency** | High (user knows state) | Low (state implicit) |
| **Beginner-friendliness** | Lower (more concepts) | Higher (fewer concepts) |

### Research Significance

This case demonstrates a **fundamental architectural difference** in state management:

1. **Explicit state management** (Milvus):
   - User controls when collections are loaded into memory
   - Better for resource-constrained environments
   - More complex API (requires understanding of load)
   - Predictable memory usage

2. **Implicit state management** (seekdb):
   - Database manages loading automatically
   - Better for ease of use
   - Simpler API (no load concept)
   - Less predictable resource usage

This is a **usability vs control trade-off** that impacts:
- API design (explicit vs implicit state)
- Resource management (user vs database controlled)
- Learning curve (more concepts vs fewer)

---

## Synthesis: Three Dimensions of Difference

The three cases represent **three distinct dimensions** of database difference:

### 1. Capability Boundaries (Case 1)
- **What**: Different limits on parameters
- **Example**: Dimension limits (32768 vs 16000)
- **Impact**: Application compatibility

### 2. Validation Philosophy (Case 2)
- **What**: When to validate input
- **Example**: Index type (strict vs permissive)
- **Impact**: Error detection and user experience

### 3. State Management (Case 3)
- **What**: How to manage runtime state
- **Example**: Load requirement (explicit vs implicit)
- **Impact**: API complexity and resource control

---

## Conclusion

These three cases demonstrate that **vector databases differ in multiple dimensions**:

1. **Capability**: What they can do (dimension limits)
2. **Validation**: How they validate input (strict vs permissive)
3. **Architecture**: How they manage state (explicit vs implicit)

Understanding these differences is critical for:
- **Database selection**: Choosing the right database for your use case
- **Migration planning**: Anticipating compatibility issues
- **API design**: Learning from different design philosophies

**Publication Recommendation**: All three cases are strong candidates for inclusion in a comparative study of vector databases.

---

## References

- **Differential Campaign**: v3 (2026-03-07)
- **Test Results**: `runs/differential-v3-phase1-*` and `runs/differential-v3-phase2-*`
- **Issue Reports**: `docs/issues/issue_*.md`
