# Campaign R3 Design: Documented Parameter Families

**Goal**: Test genuinely documented parameters with validation weaknesses
**Learned from R1+R2 correction**: Avoid kwargs-based testing; focus on documented Collection parameters
**Approach**: Test schema parameters, index nested parameters, search parameters

---

## Pre-submission Lesson from R1+R2

**Critical learning**: The "metric_type validation weakness" was actually an API silent-ignore issue, not a validation bug. The `metric_type` parameter is not part of the Collection constructor at all - it's silently ignored via `**kwargs`.

**R3 principle**: Only test **explicitly documented** parameters of Collection, index, and search operations.

---

## Documented Parameter Families

### Family 1: Collection Schema Parameters (4 cases)

**Source**: [Consistency Level - Milvus Documentation](https://milvus.io/docs/consistency.md)

| Parameter | Valid Values | Invalid Test Cases | Priority |
|-----------|--------------|-------------------|----------|
| **consistency_level** | "Strong", "Bounded", "Session", "Eventually" | "", "INVALID_LEVEL", 123 | HIGH |

**Note**: consistency_level is a documented Collection() parameter in newer pymilvus versions.

| Case ID | Operation | Parameter | Value | Expected Yield |
|---------|-----------|-----------|-------|----------------|
| param-consistency-001 | create_collection | consistency_level | "" (empty) | Type-1 or Type-2 |
| param-consistency-002 | create_collection | consistency_level | "INVALID_LEVEL" | Type-1 or Type-2 |

---

### Family 2: Index Nested Parameters (4 cases)

**Source**: [Index Vector Fields - Milvus Documentation](https://milvus.io/docs/index-vector-fields.md)

When creating indexes, `index_params` contains nested parameters:

| Parameter | Valid Values | Invalid Test Cases | Priority |
|-----------|--------------|-------------------|----------|
| **nlist** (IVF_FLAT) | 1-65536 | 0, -1, "INVALID" | HIGH |
| **m** (HNSW) | 8-1024 (power of 2) | 0, -1, 3, "INVALID" | MEDIUM |

| Case ID | Operation | Parameter | Value | Expected Yield |
|---------|-----------|-----------|-------|----------------|
| param-index-nlist-001 | build_index | index_params.nlist | 0 (zero) | Type-1 or Type-2 |
| param-index-nlist-002 | build_index | index_params.nlist | -1 (negative) | Type-1 or Type-2 |
| param-index-m-001 | build_index | index_params.m | 3 (not power of 2) | Type-1 or Type-2 |
| param-index-m-002 | build_index | index_params.m | -1 (negative) | Type-1 or Type-2 |

---

### Family 3: Search Nested Parameters (2 cases)

**Source**: Search parameter documentation

| Parameter | Valid Values | Invalid Test Cases | Priority |
|-----------|--------------|-------------------|----------|
| **nprobe** | 1-65536 | 0, -1, "INVALID" | MEDIUM |

| Case ID | Operation | Parameter | Value | Expected Yield |
|---------|-----------|-----------|-------|----------------|
| param-search-nprobe-001 | search | search_params.nprobe | 0 (zero) | Type-1 or Type-2 |
| param-search-nprobe-002 | search | search_params.nprobe | -1 (negative) | Type-1 or Type-2 |

---

## Calibration Cases (2 cases)

| Case ID | Operation | Parameter | Value | Purpose |
|---------|-----------|-----------|-------|---------|
| cal-consistency-001 | create_collection | consistency_level | "Strong" (valid) | Confirm valid value works |
| cal-index-nlist-001 | build_index | index_params.nlist | 128 (valid) | Confirm valid value works |

---

## Total Case Count: 10

**Distribution**:
- Primary cases: 8
- Calibration cases: 2

**By parameter family**:
- Collection schema: 2 cases
- Index nested parameters: 4 cases
- Search nested parameters: 2 cases

---

## Adapter Support Requirements

The MilvusAdapter needs to support these parameters:

1. **consistency_level**: Add to Collection() call in _create_collection()
2. **index_params.nlist**: Pass in build_index() method
3. **index_params.m**: Pass in build_index() method for HNSW index
4. **search_params.nprobe**: Pass in search() method

---

## Expected Yield

**Minimum success**: >=1 API usability or validation issue
- At least one documented parameter shows validation weakness

**Stretch success**: 2-3 issues
- Multiple parameter families show validation weaknesses
- Pattern suggests systematic validation gaps

**Hypothesis**:
- Nested parameters (nlist, m, nprobe) may have weaker validation than top-level parameters
- Collection schema parameters (consistency_level) may be newer and less validated

---

## Success Criteria

### Minimum Success
- All 10 cases execute without framework errors
- At least 1 issue-ready candidate found
- Calibration cases pass as expected

### Stretch Success
- 2-3 issue-ready candidates
- Multiple parameter families show validation weaknesses
- No silent-ignore artifacts

---

## R3 vs R1+R2 Comparison

| Aspect | R1+R2 | R3 (proposed) |
|--------|-------|---------------|
| Focus | General → metric_type | Documented parameters only |
| Cases | 21 | 10 |
| Avoid | Silent kwargs, undocumented params | All params documented |
| Hit rate expectation | 9.5% | 10-20% |

---

## Implementation Notes

1. **Pre-verification**: Check MilvusAdapter supports target parameters
2. **Avoid kwargs**: Only pass explicitly supported parameters
3. **Document sources**: Each test cites official Milvus documentation
4. **Adapter fixes**: May need to extend MilvusAdapter for new parameters

---

## Pre-R3 Checklist

Before execution:
- [ ] Verify MilvusAdapter supports consistency_level parameter
- [ ] Verify MilvusAdapter can pass index_params (nlist, m)
- [ ] Verify MilvusAdapter can pass search_params (nprobe)
- [ ] Test adapter modifications with valid cases first
- [ ] Confirm all parameters are documented in Milvus docs

---

## Post-R3 Actions

1. **If yield >= 2**: Validation weakness is systematic → Expand R4 to more parameter families
2. **If yield = 1**: Validation weakness is selective → Focus R4 on specific weak family
3. **If yield = 0**: Reassess strategy → Consider operation sequence or state-transition bugs
