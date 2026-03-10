# R5B Round 2: Second-Round Lifecycle Experiments

**Run ID**: r5b-lifecycle-20260310-120943
**Database**: Milvus v2.6.10
**Date**: 2026-03-10
**Focus**: Post-drop search semantics and post-insert visibility

---

## Executive Summary

| Test | Status | Classification | Finding |
|------|--------|----------------|---------|
| ILC-008 | Passed | VERSION_GUARDED | Search fails after drop (load fails without index) |
| ILC-009 | Failed | INFRA_FAILURE | Insert count tracking issue (needs investigation) |

---

## ILC-008: Post-Drop Search Semantics

### Test Design
1. Create collection with data and index
2. Load and search (baseline)
3. Release and drop index
4. Attempt to load (without index)
5. Attempt to search

### Milvus v2.6.10 Behavior

**Load after drop fails**:
```
MilvusException: (code=700, message=index not found[collection=test_r5b_ilc_008_20260310120917])
```

**Search fails**:
```
MilvusException: (code=101, message=failed to search: collection not loaded)
```

### Classification: VERSION_GUARDED

**Observed Behavior**: After `drop_index`:
1. `load()` operation fails (no index to load)
2. Collection remains in NotLoad state
3. Search fails with precondition gate violation

**Interpretation**:
- This is **expected** behavior for Milvus v2.6.10
- Search requires both: loaded collection AND index
- Without index, load fails and search precondition gate triggers

**Contract Implication**:
- `drop_index` → search becomes impossible (not just slow)
- Must recreate index to enable search again
- This is more restrictive than "degraded performance" fallback

---

## ILC-009: Post-Insert Visibility

### Test Design
1. Create collection with data and index
2. Load and establish baseline
3. Count entities (baseline)
4. Insert new vector
5. Count entities (after insert)
6. Search for new vector

### Issue: INFRA_FAILURE

**Oracle Observation**: "Insert did not increase storage count: 0 -> 0"

**Root Cause** (suspected):
- The `count_entities` operation returns `collection.num_entities`
- Milvus may have delay in entity count visibility
- Or insert operation may not be persisting correctly

**Investigation Needed**:
1. Verify insert operation succeeded (check return value)
2. Check if flush/refresh is needed for count visibility
3. Test with explicit flush after insert

**Workaround Options**:
- Add `flush()` call after insert
- Use search results to verify visibility instead of count
- Test with different consistency levels

---

## Comparison: Round 1 vs Round 2

| Round | Tests | Passed | New Findings |
|-------|-------|--------|--------------|
| Round 1 | 8 | 8 | Basic lifecycle transitions verified |
| Round 2 | 10 | 9 | Post-drop behavior: load fails without index |

---

## Next Steps

### ILC-009 Investigation (High Priority)
1. Add flush/refresh after insert
2. Verify insert operation return codes
3. Alternative: use search visibility instead of count

### Future Experiments
1. ILC-009v2: Post-insert with flush
2. Cross-version: Test on Milvus v2.3.x, v2.4.x
3. Index rebuild: Test search after index recreation

---

## Files Modified

- `casegen/templates/r5b_lifecycle.yaml`: Added ILC-008, ILC-009
- `core/oracle_engine.py`: Added post-drop and post-insert oracles
- `scripts/run_lifecycle_pilot.py: No changes (existing executor)

---

## Contract Implications

### ILC-008 Finding (VERSION_GUARDED)
```
drop_index → load fails → search fails
```

**Universal Clause**:
> After drop_index, search operations fail because:
> 1. load() requires index metadata
> 2. Without load, search precondition gate triggers

**Milvus-Specific**:
- Error: "index not found" on load after drop
- Search fails with precondition gate, not "empty results"

### ILC-009 Finding (INFRA_FAILURE)
**Pending Investigation**:
- Need to verify insert visibility behavior
- May require flush/refresh or consistency level adjustment

---

**Report Generated**: 2026-03-10
**Status**: ILC-008 complete, ILC-009 needs investigation
