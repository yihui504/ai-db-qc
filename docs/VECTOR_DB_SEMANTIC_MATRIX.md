# Vector Database Semantic Behavior Matrix

**Document Version**: 1.0
**Date**: 2026-03-09
**Scope**: R4 Differential Testing Results (Milvus vs Qdrant)

---

## Overview

This matrix documents the comparative behavior of Milvus and Qdrant across 8 semantic properties tested during the R4 differential testing campaign. It serves as a reference for understanding behavioral differences, portability considerations, and semantic compatibility between vector databases.

---

## Complete Semantic Property Matrix

| Property ID | Property Name | Milvus Behavior | Qdrant Behavior | Classification | Oracle Rule |
|-------------|---------------|-----------------|-----------------|----------------|-------------|
| **R4-001** | Post-Drop Rejection | Fails with "collection not exist" | Fails with "collection not found" | ✅ PASS | Rule 1 |
| **R4-002** | Deleted Entity Visibility | Excludes deleted entity from results | Excludes deleted entity from results | ✅ PASS | Rule 2 |
| **R4-003** | Delete Idempotency | Allows repeated delete | Allows repeated delete | ✅ PASS | Rule 4 |
| **R4-004** | Index-Independent Search | Fails without explicit index | Succeeds (auto-creates HNSW) | ⚠️ ALLOWED | Rule 3 |
| **R4-005** | Load-State Enforcement | Fails without explicit load | Succeeds (auto-loads) | ⚠️ ALLOWED | Rule 7 |
| **R4-006** | Empty Collection Handling | Fails (requires load) | Succeeds (returns empty) | ⚠️ ALLOWED | Rule 5 |
| **R4-007** | Non-Existent Delete | Succeeds silently | Succeeds silently | ✅ PASS | Rule 4 |
| **R4-008** | Collection Creation Idempotency | Allows duplicate creation | Rejects duplicate creation | ⚠️ ALLOWED | Rule 6 |

---

## Classification Summary

| Classification | Count | Percentage | Properties |
|----------------|-------|------------|------------|
| **PASS (CONSISTENT)** | 4 | 50% | R4-001, R4-002, R4-003, R4-007 |
| **ALLOWED DIFFERENCE** | 4 | 50% | R4-004, R4-005, R4-006, R4-008 |
| **BUG (CONTRACT VIOLATION)** | 0 | 0% | - |
| **OBSERVATION** | 0 | 0% | - |

---

## Detailed Property Analysis

### R4-001: Post-Drop Rejection

**Semantic Contract**: Dropped collections must reject all subsequent operations.

| Aspect | Milvus | Qdrant |
|--------|--------|--------|
| **Behavior** | Correctly fails search after drop | Correctly fails search after drop |
| **Error Message** | "Collection not exist" | "Collection not found" |
| **Contract Compliance** | ✅ Compliant | ✅ Compliant |

**Classification**: PASS - Both databases uphold the semantic contract.

**Portability**: No special handling required.

---

### R4-002: Deleted Entity Visibility

**Semantic Contract**: Deleted entities must not appear in subsequent search results.

| Aspect | Milvus | Qdrant |
|--------|--------|--------|
| **Behavior** | Deleted entity excluded from results | Deleted entity excluded from results |
| **Test Entity** | ID=1 not in step 7 results | ID=1 not in step 7 results |
| **Contract Compliance** | ✅ Compliant | ✅ Compliant |

**Classification**: PASS - Both databases uphold data integrity contract.

**Portability**: No special handling required.

---

### R4-003: Delete Idempotency

**Semantic Contract**: Delete operations should be idempotent with consistent behavior.

| Aspect | Milvus | Qdrant |
|--------|--------|--------|
| **First Delete** | Succeeds | Succeeds |
| **Second Delete** | Succeeds | Succeeds |
| **Idempotency Strategy** | both-succeed | both-succeed |
| **Contract Compliance** | ✅ Compliant | ✅ Compliant |

**Classification**: PASS - Both databases implement consistent idempotency.

**Portability**: No special handling required.

---

### R4-004: Index-Independent Search

**Semantic Contract**: UNDEFINED - Search without explicit index is an architectural choice.

| Aspect | Milvus | Qdrant |
|--------|--------|--------|
| **Index Requirement** | Explicit `create_index()` required | Auto-creates HNSW on insert |
| **Search Without Index** | Fails with error | Succeeds |
| **Index Type** | User-specified (HNSW, IVF, etc.) | Fixed HNSW |
| **Contract Compliance** | ✅ Allowed (explicit design) | ✅ Allowed (automatic design) |

**Classification**: ALLOWED DIFFERENCE - Legitimate architectural variation.

**Portability**:
- **Milvus → Qdrant**: Remove `create_index()` calls
- **Qdrant → Milvus**: Add `create_index()` before search

---

### R4-005: Load-State Enforcement

**Semantic Contract**: UNDEFINED - Collection loading is an architectural choice.

| Aspect | Milvus | Qdrant |
|--------|--------|--------|
| **Load Requirement** | Explicit `load()` required | Auto-loads on access |
| **Search Without Load** | Fails with "not loaded" | Succeeds |
| **Memory Management** | Manual (user controls) | Automatic (system manages) |
| **Contract Compliance** | ✅ Allowed (explicit design) | ✅ Allowed (automatic design) |

**Classification**: ALLOWED DIFFERENCE - Legitimate architectural variation.

**Portability**:
- **Milvus → Qdrant**: Remove `load()` calls
- **Qdrant → Milvus**: Add `load()` before search

---

### R4-006: Empty Collection Handling

**Semantic Contract**: UNDEFINED - Empty collection search is an edge case.

| Aspect | Milvus | Qdrant |
|--------|--------|--------|
| **Empty Collection Search** | Fails (requires load) | Succeeds (returns empty) |
| **Error Handling** | Throws "not loaded" | Returns empty result set |
| **State Requirement** | Load even for empty | No explicit load needed |
| **Contract Compliance** | ✅ Allowed (stateful design) | ✅ Allowed (stateless design) |

**Classification**: ALLOWED DIFFERENCE (OBSERVATION) - Edge case with no standard.

**Portability**:
- **Milvus → Qdrant**: Handle empty collection success
- **Qdrant → Milvus**: Call `load()` even for empty collections

---

### R4-007: Non-Existent Delete Tolerance

**Semantic Contract**: Deleting non-existent ID should be handled gracefully.

| Aspect | Milvus | Qdrant |
|--------|--------|--------|
| **Delete Non-Existent** | Succeeds silently | Succeeds silently |
| **Error Behavior** | No error thrown | No error thrown |
| **Idempotency Strategy** | silent-success | silent-success |
| **Contract Compliance** | ✅ Compliant | ✅ Compliant |

**Classification**: PASS - Both databases handle gracefully with same strategy.

**Portability**: No special handling required.

---

### R4-008: Collection Creation Idempotency

**Semantic Contract**: UNDEFINED - Duplicate collection creation is an API design choice.

| Aspect | Milvus | Qdrant |
|--------|--------|--------|
| **Duplicate Creation** | Allows (succeeds silently) | Rejects (throws error) |
| **Error Behavior** | No error | "already exists" error |
| **API Philosophy** | Permissive | Strict |
| **Contract Compliance** | ✅ Allowed (permissive design) | ✅ Allowed (strict design) |

**Classification**: ALLOWED DIFFERENCE - Different API design philosophies.

**Portability**:
- **Milvus → Qdrant**: Add existence check or handle "already exists" error
- **Qdrant → Milvus**: Remove existence checks (optional)

---

## Architectural Difference Categories

### State Management

| Aspect | Milvus | Qdrant |
|--------|--------|--------|
| **Index Creation** | Explicit `create_index()` | Automatic (HNSW) |
| **Collection Loading** | Explicit `load()` | Automatic on access |
| **State Philosophy** | Manual control | Automatic management |

**Impact Properties**: R4-004, R4-005, R4-006

### API Philosophy

| Aspect | Milvus | Qdrant |
|--------|--------|--------|
| **Duplicate Operations** | Generally permissive | Generally strict |
| **Error Handling** | State-focused errors | Operation-focused errors |

**Impact Properties**: R4-008

---

## Portability Reference

### Code Pattern: Search Operation

**Milvus (Explicit State Management)**:
```python
collection.create_collection(name="test", dimension=128)
collection.insert(vectors)
collection.create_index(field_name="vector", index_type="HNSW")  # Required
collection.load()  # Required
results = collection.search(query_vector, top_k=10)
```

**Qdrant (Automatic State Management)**:
```python
client.create_collection(name="test", vectors_config=...)
client.upsert(collection_name="test", points=...)  # Auto-creates index
results = client.search(collection_name="test", ...)  # Auto-loads
```

### Portability Checklist

| Task | Milvus → Qdrant | Qdrant → Milvus |
|------|-----------------|-----------------|
| **Index Creation** | Remove `create_index()` | Add `create_index()` |
| **Collection Loading** | Remove `load()` | Add `load()` |
| **Empty Collections** | Handle success case | Call `load()` first |
| **Duplicate Creation** | Add existence check | Remove check (optional) |
| **Error Handling** | Reduce state error handling | Add state error handling |

---

## Contract Compliance Summary

### Universal Contracts (Must Pass)

| Contract | Properties | Status |
|----------|------------|--------|
| **Post-Drop Rejection** | R4-001 | ✅ Both pass |
| **Deleted Entity Visibility** | R4-002 | ✅ Both pass |
| **Idempotency Consistency** | R4-003, R4-007 | ✅ Both pass |

**Result**: Zero contract violations across all PRIMARY semantic properties.

### Architectural Variations (Allowed Differences)

| Variation | Properties | Status |
|-----------|------------|--------|
| **Index Strategy** | R4-004 | ⚠️ Explicit vs Automatic |
| **Load Strategy** | R4-005, R4-006 | ⚠️ Manual vs Automatic |
| **API Philosophy** | R4-008 | ⚠️ Permissive vs Strict |

**Result**: All differences are legitimate architectural choices, not bugs.

---

## Usage Notes

### For Application Developers

1. **Use this matrix** to understand behavioral differences before porting
2. **Check the "Portability" section** for each property to understand required code changes
3. **Test thoroughly** when migrating between databases

### For Database Evaluators

1. **PASS properties** indicate strong semantic alignment
2. **ALLOWED DIFFERENCE properties** indicate architectural trade-offs
3. **Zero BUGS** indicates both databases uphold universal semantic contracts

### For Framework Developers

1. **Adapter abstraction** normalizes state management differences
2. **Oracle classification** distinguishes bugs from allowed differences
3. **Portability layer** can automate code transformations

---

## Metadata

- **Document**: Vector Database Semantic Behavior Matrix
- **Version**: 1.0
- **Date**: 2026-03-09
- **Source**: R4 Full Differential Testing Campaign
- **Databases**: Milvus (v2.6.10), Qdrant (latest)
- **Test Properties**: 8
- **Categories**: 4 PASS, 4 ALLOWED, 0 BUGS

---

**END OF SEMANTIC BEHAVIOR MATRIX**

This matrix is based on empirical testing results from the R4 differential testing campaign. For detailed results and raw data, see:
- `docs/R4_FULL_REPORT.md`
- `results/r4-full-20260309-225359/`
