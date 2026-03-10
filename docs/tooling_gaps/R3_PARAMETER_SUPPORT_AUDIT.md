# R3 Parameter Support Audit

**Date**: 2026-03-08
**Purpose**: Verify adapter support for planned R3 parameters before campaign creation

---

## Audit Methodology

For each parameter:
1. Check official pymilvus documentation
2. Verify Collection/Method signature supports it
3. Test actual parameter passing behavior
4. Check current MilvusAdapter implementation
5. Assess failure attribution capability
6. Determine suitability for formal campaign use

---

## Parameter 1: consistency_level

### Official Documentation
- **Source**: [Consistency Level - Milvus Documentation](https://milvus.io/docs/consistency.md)
- **Documented**: "Set Consistency Level upon Creating Collection"
- **Valid values**: "Strong", "Bounded", "Session", "Eventually"

### Collection Constructor Support
```python
Collection(self, name: str, schema: Optional[CollectionSchema] = None,
           using: str = 'default', **kwargs) -> None
```

**Finding**: `consistency_level` is **NOT** an explicit parameter. It would be passed via `**kwargs`.

### Test Result
```python
Collection(..., consistency_level="Strong")
# Result: Collection created successfully
# Verification: hasattr(collection, 'consistency_level') → False
```

### MilvusAdapter Implementation
```python
def _create_collection(self, params: Dict) -> Dict[str, Any]:
    collection_name = params.get("collection_name")
    dimension = params.get("dimension", 128)
    metric_type = params.get("metric_type", "L2")
    # consistency_level is NOT extracted or passed
    ...
    collection = Collection(name=collection_name, schema=schema, using=self.alias)
```

**Status**: **NOT SUPPORTED** - Parameter not extracted from params

### Assessment

| Aspect | Status | Notes |
|--------|--------|-------|
| Officially documented | ✅ Yes | In Milvus docs |
| Supported in pymilvus API | ❌ No | Only **kwargs, not explicit parameter |
| Passed by MilvusAdapter | ❌ No | Not extracted from params dict |
| Failures attributable | ❌ No | Parameter doesn't reach database |
| Suitable for campaign | ❌ NO | Tool-layer artifact, like dtype |

**Conclusion**: **DO NOT INCLUDE** in R3. This would be another silent-ignore issue like metric_type.

---

## Parameter 2: index_params.nlist

### Official Documentation
- **Source**: [Index Vector Fields - Milvus Documentation](https://milvus.io/docs/index-vector-fields.md)
- **Documented**: IVF_FLAT index parameter `nlist` (cluster units)
- **Valid range**: [1, 65536]

### Collection.create_index() Support
```python
create_index(field_name: str, index_params: Union[Dict, NoneType] = None, ...)
```

**Finding**: `index_params` is an **explicitly supported parameter**.

### Test Result
```python
index_params = {
    'index_type': 'IVF_FLAT',
    'metric_type': 'L2',
    'params': {'nlist': 0}  # Invalid
}
collection.create_index(field_name='vector', index_params=index_params)
# Result: MilvusException: "param 'nlist' (0) should be in range [1, 65536]"
```

**Validation**: **EXCELLENT** - Error message specifies valid range clearly.

### MilvusAdapter Implementation
```python
def _build_index(self, params: Dict) -> Dict[str, Any]:
    collection_name = params.get("collection_name")
    index_type = params.get("index_type", "IVF_FLAT")
    metric_type = params.get("metric_type", "L2")

    # Create index on vector field
    index_params = {
        "index_type": index_type,
        "metric_type": metric_type,
        "params": {"nlist": 128}  # ← HARDCODED
    }
```

**Status**: **PARTIALLY SUPPORTED** - Hardcoded to nlist=128, doesn't accept custom values

### Gap Analysis

| Issue | Impact |
|-------|--------|
| Hardcoded nlist=128 | Cannot test invalid nlist values |
| Parameter not extracted from params | Template values ignored |

### Assessment

| Aspect | Status | Notes |
|--------|--------|-------|
| Officially documented | ✅ Yes | In Milvus docs with valid range |
| Supported in pymilvus API | ✅ Yes | index_params parameter exists |
| Database validates | ✅ YES | Clear error with range information |
| Passed by MilvusAdapter | ❌ NO | Hardcoded, doesn't use params |
| Failures attributable | ⚠️ PARTIAL | If adapter fixed, attribution would be clear |
| Suitable for campaign | ❌ NO | **Requires adapter fix first** |

**Conclusion**: **DO NOT INCLUDE** in R3 until adapter is fixed. Current behavior is tool-layer artifact (adapter ignores params).

---

## Parameter 3: index_params.m (HNSW)

### Official Documentation
- **Source**: HNSW index documentation
- **Documented**: Parameter `M` for HNSW index
- **Valid values**: Powers of 2, typically 8-1024

### Test Result
```python
index_params = {
    'index_type': 'HNSW',
    'metric_type': 'L2',
    'params': {'M': 3}  # Potentially invalid (not power of 2)
}
collection.create_index(field_name='vector', index_params=index_params)
# Result: Success (M=3 accepted)
```

**Note**: M=3 may actually be valid - HNSW documentation may not require powers of 2.

### MilvusAdapter Implementation

**Status**: **NOT SUPPORTED** - Like nlist, hardcoded to `{"nlist": 128}`

### Assessment

| Aspect | Status | Notes |
|--------|--------|-------|
| Officially documented | ⚠️ UNCLEAR | HNSW docs need verification |
| Supported in pymilvus API | ✅ Yes | index_params accepts dict |
| Database validates | ❓ UNKNOWN | M=3 was accepted (may be valid) |
| Passed by MilvusAdapter | ❌ NO | Hardcoded params |
| Failures attributable | ❌ NO | Tool-layer artifact |
| Suitable for campaign | ❌ NO | **Requires adapter fix + documentation verification** |

**Conclusion**: **DO NOT INCLUDE** in R3. Requires adapter fix and documentation verification.

---

## Parameter 4: search_params.nprobe

### Official Documentation
- **Source**: Search parameter documentation
- **Documented**: `nprobe` parameter (number of query nodes to access)
- **Typical range**: [1, 65536]

### Collection.search() Support
```python
search(
    data=[...],
    anns_field='vector',
    param: Dict,  # ← Contains search_params
    limit: int,
    ...
)
```

**Finding**: `param` dict can contain `params` sub-dict with `nprobe`.

### Test Result
```python
# Current adapter hardcodes nprobe=10
search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
collection.search(data=[...], param=search_params, ...)

# Test with nprobe=0 or nprobe=-1
search_params = {"metric_type": "L2", "params": {"nprobe": 0}}
# Result: Success (but adapter ignores it, uses nprobe=10)
```

**Finding**: Test results are **MISLEADING** - adapter hardcodes nprobe=10, so invalid nprobe values are never actually tested.

### MilvusAdapter Implementation
```python
# _search method - line 280
search_params = {"metric_type": "L2", "params": {"nprobe": 10}}  # ← HARDCODED
```

**Status**: **NOT SUPPORTED** - Hardcoded to nprobe=10

### Gap Analysis

| Issue | Impact |
|-------|--------|
| Hardcoded nprobe=10 | Cannot test invalid nprobe values |
| Parameter not extracted from params | Template values ignored |

### Assessment

| Aspect | Status | Notes |
|--------|--------|-------|
| Officially documented | ✅ Yes | nprobe is documented search parameter |
| Supported in pymilvus API | ✅ Yes | param.params accepts nprobe |
| Database validation | ❓ UNKNOWN | Adapter doesn't pass custom values |
| Passed by MilvusAdapter | ❌ NO | Hardcoded to nprobe=10 |
| Failures attributable | ❌ NO | Tool-layer artifact |
| Suitable for campaign | ❌ NO | **Requires adapter fix first** |

**Conclusion**: **DO NOT INCLUDE** in R3. Current behavior is tool-layer artifact.

---

## Summary Table

| Parameter | Documented | API Supports | Adapter Supports | DB Validates | Ready for Campaign |
|-----------|------------|--------------|-----------------|--------------|-------------------|
| consistency_level | ✅ Yes | ❌ **kwargs only | ❌ No | ❌ Silent ignore | **NO** |
| index_params.nlist | ✅ Yes | ✅ Yes | ❌ No (hardcoded) | ✅ Good diagnostics | **NO** (adapter gap) |
| index_params.m | ⚠️ Unclear | ✅ Yes | ❌ No (hardcoded) | ❓ Unknown | **NO** (adapter gap + doc verification needed) |
| search_params.nprobe | ✅ Yes | ✅ Yes | ❌ No (hardcoded) | ❓ Unknown | **NO** (adapter gap) |

---

## Critical Finding

**ALL four planned R3 parameter families have adapter support issues:**

1. **consistency_level**: Silent-ignore via **kwargs (like metric_type)
2. **index_params.nlist**: Adapter hardcodes nlist=128
3. **index_params.m**: Adapter hardcodes to nlist-based params
4. **search_params.nprobe**: Adapter hardcodes nprobe=10

**R3 CANNOT BE EXECUTED** without adapter fixes. Testing these parameters now would produce misleading results (either silent-ignore or hardcoded values).

---

## Recommendations

### Immediate Actions

1. **Suspend R3 execution** until adapter gaps are resolved
2. **Document adapter gaps** as tooling issues (similar to dtype)
3. **Create adapter enhancement plan** to support:
   - Custom index_params (nlist, m, etc.)
   - Custom search_params (nprobe, etc.)
   - Documented Collection parameters (if any exist)

### Alternative R3 Direction

If we want to proceed with R3 without adapter modifications, consider:

**Option A**: Test parameters the adapter CURRENTLY supports
- dimension (already tested in R1/R2)
- top_k (already tested in R1/R2)
- metric_type (silent-ignore - not recommended)
- filter expressions (tested in R2)

**Option B**: Focus on operation sequences
- State transitions (create → insert → search → delete)
- Precondition violations
- Error handling chains

**Option C**: Focus on cross-database testing
- Compare Milvus vs SeekDB on same operations
- Test differential behavior

---

## Tooling Gaps to Document

| Gap ID | Parameter | Issue | File |
|--------|-----------|-------|------|
| TOOLING-002 | consistency_level | Silent-ignore via **kwargs | `adapters/milvus_adapter.py:_create_collection` |
| TOOLING-003 | index_params | Hardcoded to {"nlist": 128} | `adapters/milvus_adapter.py:_build_index` |
| TOOLING-004 | search_params | Hardcoded to {"nprobe": 10} | `adapters/milvus_adapter.py:_search` and `_filtered_search` |
| TOOLING-001 | dtype | Parameter not supported | `docs/tooling_gaps/dtype_parameter_not_supported.md` |

---

## Metadata

- **Audit Date**: 2026-03-08
- **Auditor**: AI-DB-QC automated audit
- **Method**: Signature inspection + parameter testing + adapter code review
- **Conclusion**: R3 must be redesigned or postponed until adapter gaps are resolved
