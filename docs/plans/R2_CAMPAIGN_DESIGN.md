# Campaign R2 Design (Revised): Parameter Validation Focus

**Goal**: Improve issue yield by focusing on parameter validation weaknesses
**Learned from R1**: cb-bound-005 (invalid metric_type) was the strongest finding
**Hypothesis**: Milvus may have weak validation for other enum/parameter types

## Design Principles

1. **Narrow & Deep**: Focus on clearly illegal values, avoid edge-case ambiguity
2. **High-Confidence Targets**: Cases similar to cb-bound-005 pattern
3. **Adjacent Parameters**: Test related parameter families (index, numeric, not multiple metric variants)
4. **Clear Illegality**: Every primary case uses values that are unambiguously invalid

---

## PRIMARY CASES (8 cases)

### Family 1: Metric Type (1 primary case)
Build on cb-bound-005 success with one clear metric_type edge case

| Case ID | Operation | Parameter | Value | Expected Yield |
|---------|-----------|-----------|-------|----------------|
| **param-metric-001** | create_collection | metric_type | "" (empty string) | Type-1 or Type-2 |

**Note**: Reduced from 3 to 1 primary case. Only testing empty string (clearly illegal).

### Family 2: Index Type (2 cases)
Test index_type parameter validation

| Case ID | Operation | Parameter | Value | Expected Yield |
|---------|-----------|-----------|-------|----------------|
| **param-index-001** | build_index | index_type | "INVALID_INDEX" | Type-1 or Type-2 |
| **param-index-002** | build_index | index_type | "" (empty string) | Type-1 or Type-2 |

### Family 3: Numeric Boundaries (4 cases)
Test clearly illegal numeric values

| Case ID | Operation | Parameter | Value | Expected Yield |
|---------|-----------|-----------|-------|----------------|
| **param-num-001** | create_collection | dimension | -1 (negative) | Type-1 or Type-2 |
| **param-num-002** | create_collection | dimension | 32769 (max+1) | Type-1 or Type-2 |
| **param-num-003** | search | top_k | -100 (negative) | Type-1 or Type-2 |
| **param-num-004** | search | top_k | 999999999 (absurd) | Type-1 or Type-2 |

**Changes**:
- param-num-001: Changed from `dimension=1` to `dimension=-1` (clearly illegal)
- param-num-003: Changed from `top_k=16385` to `top_k=-100` (clearly illegal)

### Family 4: DataType Validation (1 case)
Test vector field type validation

| Case ID | Operation | Parameter | Value | Expected Yield |
|---------|-----------|-----------|-------|----------------|
| **param-dtype-001** | create_collection | dtype | "INVALID_VECTOR_TYPE" | Type-1 or Type-2 |

---

## CALIBRATION CASES (2 cases)

| Case ID | Operation | Parameter | Value | Purpose |
|---------|-----------|-----------|-------|---------|
| **cal-metric-001** | create_collection | metric_type | "L2" (valid) | Confirm valid metric_type works |
| **cal-index-001** | build_index | index_type | "IVF_FLAT" (valid) | Confirm valid index_type works |

**Reduced to 2 calibration cases** (was 3). Removed dtype calibration as less critical.

---

## EXPLORATORY CASE (1 case)

| Case ID | Operation | Parameter | Value | Expected Yield |
|---------|-----------|-----------|-------|----------------|
| **exp-metric-001** | create_collection | metric_type | "l2" (lowercase) | Exploratory |

**Downgraded from primary**: Lowercase enum values may be valid (case-insensitive APIs). Treated as exploratory.

---

## Total Case Count: 11

**Distribution:**
- Primary: 8 cases
- Calibration: 2 cases
- Exploratory: 1 case

**By parameter family:**
- Metric type: 1 primary + 1 calibration + 1 exploratory = 3
- Index type: 2 primary + 1 calibration = 3
- Numeric boundaries: 4 primary = 4
- DataType: 1 primary = 1

---

## Expected Yield

**Minimum success**: >=1 high-confidence candidate
- At least one case like cb-bound-005 (invalid enum accepted)

**Stretch success**: 2-3 candidates
- If parameter validation is systematically weak across multiple families

---

## Success Criteria

### Minimum Success
- [ ] All 11 cases execute without framework errors
- [ ] At least 1 issue-ready candidate found
- [ ] Calibration cases pass as expected

### Stretch Success
- [ ] 2-3 issue-ready candidates
- [ ] At least 1 Type-1 finding
- [ ] Multiple parameter types show validation weaknesses

---

## R2 vs R1 Comparison

| Aspect | R1 | R2 |
|--------|----|----|
| Focus | General boundaries | Parameter validation |
| Cases | 10 total | 11 total (8 primary, 2 cal, 1 exp) |
| Minimum success | >=1 candidate | >=1 candidate |
| Stretch success | 3+ candidates | 2-3 candidates |
| Noise risk | Low | Reduced (removed ambiguous cases) |

---

## Key Revisions from Original Design

1. **Removed param-metric-002** ("l2") from primary → downgraded to exploratory
2. **Replaced param-num-001**: `dimension=1` → `dimension=-1` (clearly illegal)
3. **Replaced param-num-003**: `top_k=16385` → `top_k=-100` (clearly illegal)
4. **Reduced calibration**: 3 → 2 cases
5. **Reduced metric_type variants**: 3 → 1 primary case
6. **Revised yield expectations**: minimum >=1, stretch 2-3
