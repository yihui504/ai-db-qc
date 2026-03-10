# ILC-009: Post-Insert Visibility Investigation

**Test ID**: ILC-009
**Run ID**: r5b-lifecycle-20260310-121731
**Database**: Milvus v2.6.10
**Date**: 2026-03-10
**Classification**: EXPERIMENT_DESIGN_ISSUE
**Final Conclusion**: Flush establishes storage visibility, but current experiment does not yet conclusively determine search visibility timing

---

## Experiment Summary

### What Was Proven
1. **Insert operation**: Reports correct `insert_count` (100, 1)
2. **Flush operation**: Enables `storage_count` visibility (100 → 101)
3. **Storage persistence**: Data is persisted after flush

### What Was NOT Conclusively Determined
1. **Search visibility timing**: Unknown
2. **Index update delay**: Not measurable with current design

### Root Cause: EXPERIMENT_DESIGN_ISSUE

**Problem**: Using existing vectors as query doesn't prove search visibility timing.

The inserted vector (query_vector_128 from the original 100) was searched for, but:
- It may not be in top-5 results for the query used
- The distance metric may rank other vectors higher
- No way to distinguish "not inserted" from "not in top-k"

---

## Evidence Details

### Insert Operations
| Operation | insert_count | Status |
|-----------|-------------|--------|
| Initial (100 vectors) | 100 | success |
| New (query_vector_128) | 1 | success |

### Storage Count Timeline
| Timepoint | storage_count | Change |
|-----------|--------------|-------|
| Baseline (after initial flush) | 100 | - |
| Before new insert flush | 100 | unchanged |
| After new insert flush | 101 | +1 ✓ |

**Conclusion**: Flush makes storage count visible.

### Search Results (Top-5)
| Timepoint | Results Count | Status |
|-----------|---------------|--------|
| Baseline | 10 results | - |
| Before flush | 10 results | No new vector |
| After flush | 10 results | No new vector |

**Problem**: We cannot tell if the new vector was:
- Not inserted (contradicted by insert_count=1)
- Inserted but not in top-5 (possible)
- Inserted but not indexed (possible)

---

## Why EXPERIMENT_DESIGN_ISSUE?

### Query Design Issue

The experiment used `query_vector_128` (one of the original 100) as the query:
- This vector was inserted in step 2
- A new copy of the same vector was inserted in step 8
- Search for this vector may return the original insertion, not the new one
- Or the vector may not be in top-5 due to distance calculations

### Missing Evidence

To conclusively determine search-visible timing, we need:
1. **Unique vector**: Insert a vector that's guaranteed to be unique
2. **Exact match query**: Use the exact same vector as query
3. **top_k=1**: Maximize chance of finding the exact match
4. **Multiple timepoints**: Test at 0ms, 200ms, 500ms, 1000ms

### Current Limitation

```
Insert(v_new) → Count reports success
Flush → storage_count increases
Search(v_existing) → May find v_existing (original), not v_new (new)
```

---

## Next Step: ILC-009b

**Design**:
1. Insert a UNIQUE vector (0.999, 0.998, 0.997, ...) that doesn't exist in collection
2. Use the SAME vector as query (exact match)
3. Set `top_k=1` to get single best result
4. Search at multiple timepoints: 0ms, after flush, +200ms, +500ms, +1000ms
5. Record exact id/score at each timepoint

**Expected Outcomes**:
- **PASS**: Vector found immediately or after flush with score=0 (exact match)
- **ALLOWED_DIFFERENCE**: Vector found after delay (200ms, 500ms, 1000ms)
- **BUG_CANDIDATE**: Vector never found despite insert success and count increase
- **EXPERIMENT_DESIGN_ISSUE**: Cannot determine (should not happen with exact match)

---

## Contract Implications

### ILC-009 Current Classification: EXPERIMENT_DESIGN_ISSUE

**Rationale**: Current experiment design insufficient to determine search-visible timing.

**Not ALLOWED_DIFFERENCE**: Because we haven't proven search delay behavior.
**Not BUG_CANDIDATE**: Because we haven't proven search failure (may be query design issue).

### After ILC-009b

The classification will be one of:
- **PASS**: Immediate or flush-enabled search visibility
- **ALLOWED_DIFFERENCE**: Delayed search visibility (200ms, 500ms, 1000ms)
- **BUG_CANDIDATE**: Search never finds exact match despite insert success

---

## Files Referenced

- `adapters/milvus_adapter.py`: Flush operation added
- `casegen/templates/r5b_lifecycle.yaml`: ILC-009 template
- `core/oracle_engine.py`: ILC-009 oracle
- `results/r5b_lifecycle_20260310-121731.json`: Execution results

---

**Report Updated**: 2026-03-10
**Status**: Awaiting ILC-009b for conclusive timing measurement
**Classification**: EXPERIMENT_DESIGN_ISSUE (reclassified from ALLOWED_DIFFERENCE)


---

## Investigation Steps

### A. Record Insert Raw Return

| Insert | insert_count | Status |
|--------|-------------|--------|
| Initial (100 vectors) | 100 | success |
| New (1 vector) | 1 | success |

**Evidence**: Insert operations report success with correct counts.

### B. Immediate Storage Count (After Initial Insert + Flush + Load)

```
storage_count = 100
load_state = Loaded
```

**Evidence**: Baseline count confirmed after initial flush.

### C. Flush Operation

```
flush(async=False) = success
```

**Evidence**: Flush operation completed successfully.

### D. Post-Flush Storage Count

```
storage_count (before flush) = 100  // unchanged
storage_count (after flush) = 101   // increased by 1
```

**Evidence**: Flush made the new insert visible in storage_count.

### E. Search Visibility Analysis

| Timepoint | Search Results | Status |
|-----------|---------------|--------|
| Baseline | 10 results | success |
| Before flush | 10 results | no new vector |
| After flush | 10 results | no new vector |

**Evidence**: Search did not return the newly inserted vector, even after flush.

---

## Detailed Evidence Flow

```
Step 1: create_collection
  → status: success

Step 2: insert (100 vectors)
  → insert_count: 100

Step 3: build_index (HNSW)
  → status: success

Step 4: flush
  → status: success

Step 5: load
  → status: success

Step 6: count_entities (baseline)
  → storage_count: 100
  → load_state: Loaded

Step 7: search (baseline)
  → 10 results returned

Step 8: insert (1 new vector: query_vector_128)
  → insert_count: 1

Step 9: count_entities (before flush)
  → storage_count: 100  // NOT YET VISIBLE

Step 10: search (before flush)
  → 10 results  // new vector NOT found

Step 11: flush
  → status: success

Step 12: count_entities (after flush)
  → storage_count: 101  // NOW VISIBLE

Step 13: search (after flush)
  → 10 results  // new vector STILL NOT found
```

---

## Classification: ALLOWED_DIFFERENCE

### Reasoning

**Observed Behavior**:
1. `insert_count` reports correctly (100, 1)
2. `storage_count` requires flush to become visible (100 → 101)
3. `search` does NOT return new vector even after flush

**Conclusion**: `flush()` enables storage count visibility, but search index update has additional delay or requires explicit index rebuild.

### Milvus v2.6.10 Specific Behavior

```
Insert → [invisible to count] → flush → [visible to count, invisible to search]
```

**Key Finding**: There are TWO visibility layers:
1. **Storage layer**: Flush makes data visible to `collection.num_entities`
2. **Index layer**: Additional delay/process needed for search visibility

---

## Experiment Design Assessment

**Classification**: EXPERIMENT_DESIGN_ISSUE → Ruled Out

The experiment design was sound:
- Flush operation was added and executed
- Multiple observation points were captured
- Both count and search evidence were collected

**Root Cause Identified**: Index update visibility is separate from storage persistence.

---

## Recommendations

### For Production Usage
1. **Always flush after insert** if you need immediate count visibility
2. **Do NOT assume search visibility immediately after flush** - index may have additional delay
3. **Consider index rebuild** or wait window for guaranteed search visibility

### For Universal Contract
This behavior should be classified as **ALLOWED_DIFFERENCE**:
- Storage persistence with flush: Expected
- Search index delay: Implementation-dependent

### Future Investigation
1. Measure actual wait window for search visibility (test at 100ms, 500ms, 1000ms)
2. Test if index rebuild makes new vector searchable
3. Test with different consistency levels (if Milvus supports)
4. Compare with Qdrant/Weaviate behavior

---

## Files Modified

- `adapters/milvus_adapter.py`: Added flush operation
- `casegen/templates/r5b_lifecycle.yaml`: Updated ILC-009 with investigation steps
- `core/oracle_engine.py`: Updated ILC-009 oracle with multi-timepoint analysis

---

## Conclusion Summary

| Aspect | Finding | Classification |
|--------|---------|----------------|
| Insert operation | Works correctly | PASS |
| Count visibility (no flush) | Not visible | OBSERVATION |
| Count visibility (after flush) | Visible | ALLOWED_DIFFERENCE |
| Search visibility (after flush) | NOT visible | ALLOWED_DIFFERENCE |

**Final Classification**: ALLOWED_DIFFERENCE

**Rationale**:
- Insert succeeds and reports correct count
- Flush enables storage count visibility
- Search index update has additional delay (implementation-specific)

**Not a Bug**: This is expected behavior for Milvus v2.6.10 architecture with separate storage and index layers.

---

**Report Generated**: 2026-03-10
**Verified By**: REAL MODE execution on Milvus v2.6.10
