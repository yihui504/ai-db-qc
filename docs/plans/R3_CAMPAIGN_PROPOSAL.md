# Campaign R3 Design: Adjacent Parameter Families

**Goal**: Expand beyond metric_type validation to test adjacent parameter families
**Learned from R2**: metric_type validation is weak; other parameters may have similar issues
**Approach**: Test parameter families related to collection schema and search operations

---

## Candidate Parameter Families

### Priority 1: Collection Schema Parameters (HIGH)
Building on metric_type findings, test related collection creation parameters

| Parameter | Valid Values | Invalid Test Cases | Priority |
|-----------|--------------|-------------------|----------|
| **consistency_level** | STRONG, BOUNDED, etc. | "", "INVALID_LEVEL", 0, -1 | HIGH |
| **replica_number** | 1-16 (typically) | 0, -1, 999999999 | HIGH |
| **auto_id** | true/false | "yes", "maybe", "", 2 | MEDIUM |

**Rationale**: These parameters are closely related to metric_type in collection creation. If metric_type validation is weak, these may also have gaps.

---

### Priority 2: Index Parameters (HIGH)
Test beyond index_type to related index configuration

| Parameter | Valid Values | Invalid Test Cases | Priority |
|-----------|--------------|-------------------|----------|
| **index_params.nlist** | 1-65536 | 0, -1, "INVALID" | HIGH |
| **index_params.m** | 8-1024 | 0, -1, 3 | MEDIUM |
| **index_params.ef_construction** | 8-512 | 0, -1, "INVALID" | MEDIUM |

**Rationale**: R2 found that index_type validation is good (param-index-001/002 failed with errors). Test if nested parameters have the same strength.

---

### Priority 3: Search Parameters (MEDIUM)
Test beyond top_k to related search configuration

| Parameter | Valid Values | Invalid Test Cases | Priority |
|-----------|--------------|-------------------|----------|
| **search_params.nprobe** | 1-65536 | 0, -1, "INVALID" | MEDIUM |
| **search_params.round_decimal** | -1, 0-6 | -2, 7, "INVALID" | LOW |
| **guarantee_timestamp** | uint64 | -1, 0, "INVALID" | LOW |

**Rationale**: R2 found top_k validation is good with range information. Test if related parameters have similar quality.

---

## Excluded Families (Do Not Test in R3)

| Family | Reason |
|--------|--------|
| **metric_type variants** | Already well-covered in R1+R2 |
| **dimension boundaries** | R2 showed good validation with range info |
| **top_k boundaries** | R2 showed good validation with range info |
| **dtype** | Tooling gap - cannot test until adapter is fixed |

---

## Proposed R3 Case Allocation

### Target: 10-12 cases total

**Family 1: Collection Schema (4 cases)**
- param-consistency-001: consistency_level="" (empty)
- param-consistency-002: consistency_level="INVALID_LEVEL"
- param-replica-001: replica_number=-1 (negative)
- param-replica-002: replica_number=999999999 (absurd)

**Family 2: Index Parameters (4 cases)**
- param-index-nlist-001: nlist=0 (min boundary)
- param-index-nlist-002: nlist=-1 (negative)
- param-index-m-001: m=-1 (negative)
- param-index-m-002: m=3 (invalid - should be power of 2)

**Family 3: Search Parameters (2-3 cases)**
- param-search-nprobe-001: nprobe=-1 (negative)
- param-search-nprobe-002: nprobe="INVALID" (string for numeric param)

**Calibration (1-2 cases)**
- cal-consistency-001: consistency_level="STRONG" (valid)
- cal-index-nlist-001: nlist=128 (valid)

**Total**: 11-12 cases

---

## Expected Yield

**Minimum success**: >=1 high-confidence candidate
- At least one parameter family shows validation weakness

**Stretch success**: 2-3 candidates
- Multiple parameter families show validation gaps
- Pattern suggests systematic validation weakness

**Hypothesis**:
- R1+R2 found metric_type validation is weak
- Collection schema parameters (consistency_level, replica_number) may have similar weakness
- Index/search nested parameters may have less validation than top-level parameters

---

## Success Criteria

### Minimum Success
- All cases execute without framework errors
- At least 1 issue-ready candidate found
- New parameter family tested (not metric_type)

### Stretch Success
- 2-3 issue-ready candidates
- Multiple parameter families show validation weaknesses
- Pattern emerges suggesting systematic validation gaps

---

## R3 vs R1+R2 Comparison

| Aspect | R1 | R2 | R3 (proposed) |
|--------|----|----|---------------|
| Focus | General boundaries | metric_type focus | Adjacent families |
| Cases | 10 | 11 | 11-12 |
| Hit rate | 10% (1/10) | 9% (1/11 primary) | Target 10-20% |
| New territory | Mixed (known + new) | metric_type deep dive | Collection schema params |

---

## Implementation Notes

1. **Adapter support**: MilvusAdapter needs to support consistency_level, replica_number, and index_params
2. **Precondition handling**: Ensure collections exist before index/search tests
3. **Parameter nesting**: Some parameters (nlist, m) are nested within index_params - need to test correctly

---

## Post-R3 Decision Points

1. **If yield >= 2**: Validation weakness is systematic → Expand to R4 with broader parameter coverage
2. **If yield = 1**: Validation weakness is selective → Focus R4 on specific weak parameter family
3. **If yield = 0**: Reassess hypothesis → Consider operation sequence testing or state-transition bugs
