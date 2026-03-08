# Differential Campaign v2 Improvement Plan

> **Status**: Methodological calibration complete, v1 yielded 1 genuine difference from 10 cases
> **Goal**: v2 targets 3-5 genuine differences, 1-2 issue-ready candidates, <10% noise pollution

---

## Part 1: Noise Reduction Fixes

### Problem: Collection Name Collisions

**Current Issue**: Fixed collection names cause "Table already exists" errors
- subset-001-baseline → "test_baseline" → collides on re-run
- subset-004-invalid-metric → "test_invalid_metric" → collides
- subset-005-empty-metric → "test_empty_metric" → collides

**Solution**: Unique collection naming with timestamp prefix

```python
# In differential runner, modify instantiate_all to add prefix:
from datetime import datetime

timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
collection_prefix = f"diff_{timestamp}_"

# Then substitute into collection names
cases = instantiate_all(templates, {
    "collection": f"{collection_prefix}main",
    "query_vector": [0.1] * 128,
    ...
})
```

### Problem: No Cleanup Between Runs

**Current Issue**: seekdb/Milvus accumulate test collections across runs

**Solution**: Add cleanup phase to differential runner

```python
def cleanup_test_collections(adapter, adapter_name: str, prefix: str):
    """Drop all collections matching the run prefix."""
    try:
        snapshot = adapter.get_runtime_snapshot()
        for coll in snapshot.get("collections", []):
            if coll.startswith(prefix.replace("main", "")):
                adapter.execute({
                    "operation": "drop_collection",
                    "params": {"collection_name": coll}
                })
        print(f"[{adapter_name}] Cleaned up test collections")
    except Exception as e:
        print(f"[{adapter_name}] Cleanup warning: {e}")
```

### Problem: Adapter Operation Gaps

**Current Issue**: Milvus adapter doesn't support `drop_collection`
- subset-002-drop-nonexistent fails on Milvus with "Unknown operation"
- This creates false "milvus_stricter" labels

**Solution**: Implement missing operations in Milvus adapter

```python
# In adapters/milvus_adapter.py, add:

def _drop_collection(self, params: Dict) -> Dict[str, Any]:
    """Drop a collection."""
    collection_name = params.get("collection_name")

    try:
        utility.drop_collection(collection_name, using=self.alias)
        return {
            "status": "success",
            "operation": "drop_collection",
            "data": []
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "operation": "drop_collection"
        }
```

And add to execute() method:
```python
elif operation == "drop_collection":
    return self._drop_collection(params)
```

---

## Part 2: Higher-Yield Differential Case Design

### Expand to 18 Cases (from 10)

#### Category A: Parameter Boundaries (6 cases) - High Yield

Focus on **constraints that databases enforce differently**:

| Case ID | Operation | Parameter | Expected Difference |
|---------|-----------|-----------|---------------------|
| boundary-001 | create_collection | dimension=0 | Rejection message/content |
| boundary-002 | create_collection | dimension=65536 (max-1) | Limit differences |
| boundary-003 | create_collection | dimension=2 (min-1) | Edge of valid range |
| boundary-004 | search | top_k=1 (minimum) | Both should accept |
| boundary-005 | search | top_k=65536 (max-1) | Limit differences |
| boundary-006 | search | top_k=-1 | Negative handling |

**Rationale**: Boundary conditions often show different validation strictness.

#### Category B: Diagnostic Quality (5 cases) - Medium Yield

Focus on **error message clarity and specificity**:

| Case ID | Operation | Invalid Input | What to Compare |
|---------|-----------|--------------|------------------|
| diag-001 | create_collection | dimension=0 | Error message specificity |
| diag-002 | create_collection | dimension=-1 | Error message specificity |
| diag-003 | search | top_k=0 | Error clarity (Milvus already specific) |
| diag-004 | search | non-existent collection | Error message detail |
| diag-005 | insert | wrong dimension | Error mentions dimension mismatch |

**Rationale**: Same failures, different error quality = Type-2 comparison value.

#### Category C: Precondition Sensitivity (4 cases) - Medium Yield

Focus on **state-dependent operation behavior**:

| Case ID | Operation | Precondition | What to Compare |
|---------|-----------|--------------|------------------|
| precond-001 | search | collection doesn't exist | Error vs silent failure |
| precond-002 | insert | collection doesn't exist | Error vs silent failure |
| precond-003 | delete | collection doesn't exist | Error vs silent failure |
| precond-004 | search | empty collection | Empty result vs error |

**Rationale**: Precondition violations show different error handling philosophies.

#### Category D: Valid Operations (3 cases) - Baseline

| Case ID | Operation | Purpose |
|---------|-----------|---------|
| valid-001 | create_collection (valid params) | Should both succeed |
| valid-002 | search (valid, with data) | Should both succeed |
| valid-003 | insert (valid, with collection) | Should both succeed |

**Rationale**: Baseline validation that both databases work correctly.

---

## Part 3: Expected Signals to Increase vs v1

### Signal 1: Genuine Behavioral Differences

**v1 Result**: 1 genuine (top_k=0) from 10 cases (10%)

**v2 Target**: 3-5 genuine differences from 18 cases (~20-25%)

**New Differences to Find**:
1. **dimension limit differences**: Milvus (2-32768) vs seekdb (unknown)
2. **top_k limit differences**: seekdb (1000000 rejected) vs Milvus (unknown)
3. **negative number handling**: Different error messages
4. **empty collection behavior**: seekdb (empty result) vs Milvus (error?)
5. **non-existent operations**: Different error messages

### Signal 2: Issue-Ready Candidates

**v1 Result**: 0 from 10 cases

**v2 Target**: 1-2 from 18 cases

**Potential Candidates**:
1. **Poor diagnostic on invalid input**: If either DB gives unhelpful error
2. **Inconsistent validation**: If DB accepts parameter in one context but not another
3. **Silent failures**: If DB fails without error message

### Signal 3: Noise Pollution Reduction

**v1 Result**: 3/10 = 30% noise (table exists, adapter gaps)

**v2 Target**: <10% noise (0-2 from 18 cases)

**Noise Sources Eliminated**:
1. ✅ Collection collisions (unique naming)
2. ✅ Adapter gaps (drop_collection implemented)
3. ✅ State pollution (cleanup phase added)

---

## Part 4: Output Separation

### New Classification System

All 18 cases will be classified into one of:

#### Type A: Paper-Worthy Behavioral Differences

**Criteria**:
- Genuine behavioral difference (not adapter bug)
- Interesting implications for users
- Well-understood and explainable

**Expected**: 3-5 cases

**Output Format**: Paper-worthy case study format

#### Type B: Issue-Ready Bug Candidates

**Criteria**:
- Type-1: Illegal input accepted (validation weakness)
- Type-2: Poor diagnostic quality on invalid input
- Type-3: Legal operation fails unexpectedly
- Type-2.PF: Precondition fails with confusing error

**Expected**: 1-2 cases

**Output Format**: Bug report with taxonomy classification

#### Type C: Valid Type-2 Comparisons

**Criteria**:
- Both correctly reject invalid input
- Different error messages (diagnostic quality)
- Valuable for understanding database personalities

**Expected**: 3-5 cases

**Output Format**: Diagnostic quality comparison table

#### Type D: Baseline Validation

**Criteria**:
- Both databases succeed on valid input
- Confirms framework works

**Expected**: 3 cases

**Output Format**: Success confirmation (no paper value)

#### Type E: Noise (Eliminated)

**Criteria**:
- Setup issues, collection collisions
- Adapter limitations
- State pollution

**Expected**: 0-2 cases (down from 3)

---

## Part 5: Implementation Plan

### Step 1: Implement Fixes (1 file)

**File**: `adapters/milvus_adapter.py`
- Add `_drop_collection()` method
- Add to `execute()` dispatch
- Commit: "fix: add drop_collection to Milvus adapter"

**File**: `scripts/run_differential_campaign.py`
- Add cleanup phase function
- Add unique collection naming
- Commit: "fix: add cleanup and unique naming to differential runner"

### Step 2: Create v2 Case Pack (1 file)

**File**: `casegen/templates/differential_v2_subset.yaml`
- 18 cases organized into 4 categories
- Validated parameter mappings
- Commit: "feat: add differential v2 subset (18 cases)"

### Step 3: Run v2 Campaign

```bash
cd C:/Users/11428/Desktop/ai-db-qc

PYTHONPATH="C:/Users/11428/Desktop/ai-db-qc" python scripts/run_differential_campaign.py \
    --run-tag v2-improved \
    --templates casegen/templates/differential_v2_subset.yaml \
    --milvus-endpoint localhost:19530 \
    --seekdb-endpoint 127.0.0.1:2881

python scripts/analyze_differential_results.py runs/differential-v2-improved-<timestamp>
```

### Step 4: Generate Separated Outputs

Create three output documents:

1. **`docs/differential_v2_behavioral_differences.md`** - Paper-worthy cases
2. **`docs/differential_v2_issue_candidates.md`** - Bug reports
3. **`docs/differential_v2_diagnostic_comparison.md`** - Type-2 comparisons

---

## Part 6: Success Criteria for v2

| Metric | v1 Result | v2 Target |
|--------|-----------|-----------|
| Genuine behavioral differences | 1 (10%) | 3-5 (20-25%) |
| Issue-ready candidates | 0 | 1-2 |
| Noise pollution | 3 (30%) | <2 (<10%) |
| Total cases | 10 | 18 |
| Paper-worthy yield | 1 | 3+ |

---

## Summary

**v1 Achievements**:
- Framework validated
- Found 1 genuine behavioral difference (top_k=0)
- Identified noise sources
- Calibrated methodology

**v2 Goals**:
- Reduce noise from 30% to <10%
- Increase genuine differences from 1 to 3-5
- Find 1-2 issue-ready candidates
- Separate outputs into paper-worthy, issue-ready, diagnostic, noise

**Next Action**: Implement fixes, create v2 case pack, run improved campaign.
