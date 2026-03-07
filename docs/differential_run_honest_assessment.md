# First Differential Subset Run - Honest Assessment

> **Run ID**: differential-first-subset-v1-20260307-231517
> **Date**: 2026-03-07
> **Cases**: 10

---

## Aggregate Summary

| Metric | Milvus | seekdb | Total |
|-------|--------|--------|-------|
| Successes | 0 | 3 | 3 |
| Failures | 10 | 7 | 17 |

---

## Label Distribution

| Label | Count | Valid? |
|-------|-------|--------|
| milvus_stricter | 3 | **NO** - Milvus adapter bug |
| same_behavior | 7 | **PARTIAL** - Both failed, often due to setup issues |

---

## Critical Finding: Milvus Adapter Bug

The "3 milvus_stricter" cases are **NOT genuine behavioral differences**:

| Case ID | Labeled As | Actual Issue |
|---------|-----------|-------------|
| subset-001-baseline | milvus_stricter | **Milvus adapter bug**: Schema creation fails - "Schema must have a primary key field" |
| subset-002-drop-nonexistent | milvus_stricter | **Cascade failure**: Collection doesn't exist due to baseline failure |
| subset-003-topk-zero | milvus_stricter | **Cascade failure**: Collection doesn't exist due to baseline failure |

**Root Cause**: Milvus adapter's `_create_collection` method creates a CollectionSchema but doesn't properly mark the `id` field as primary key. This is an **adapter bug**, not a behavioral difference.

---

## Genuine Behavioral Differences

### Confirmed: None

After accounting for the Milvus adapter bug, **there are NO confirmed genuine behavioral differences** in this run.

All 7 "same_behavior" cases are:
- Both databases rejecting invalid inputs (Type-2 comparisons)
- Both failing on precondition violations
- No meaningful differential value

---

## Remaining Noise (Setup/Mapping Issues)

| Issue | Affected Cases | Type |
|-------|----------------|------|
| Milvus schema creation bug | All 10 cases | Adapter bug |
| Missing collection (Milvus) | 7 dependent cases | Cascade from baseline failure |

---

## Assessment: First Subset NOT Strong Enough

**Verdict**: This run does **NOT** provide meaningful differential comparison.

**Issues**:
1. Milvus adapter has a schema creation bug (needs primary_key specification)
2. seekdb succeeded on 3 cases that Milvus failed on due to the bug
3. No genuine behavioral differences identified
4. All "same_behavior" cases are failures (no success comparison)

**Not Suitable For**:
- Paper case studies (findings are adapter bugs, not behavioral diffs)
- Issue selection (no genuine database differences found)

---

## Required Fixes Before Next Run

### Critical: Fix Milvus Adapter

File: `adapters/milvus_adapter.py`, method `_create_collection`

**Current code (line 143)**:
```python
schema = CollectionSchema(fields, f"Auto generated schema for {collection_name}")
```

**Needs to be**:
```python
schema = CollectionSchema(fields, f"Auto generated schema for {collection_name}", primary_field="id")
```

Or use Milvus's proper schema definition format.

### Secondary: Ensure Fair Comparison

Both adapters must:
- Accept identical parameter formats
- Create equivalent collection structures
- Handle errors consistently

---

## What This Run Actually Showed

### seekdb Working Correctly

seekdb succeeded on:
1. **subset-001-baseline**: Valid create_collection ✅
2. **subset-002-drop-nonexistent**: Drop nonexistent ✅ (interesting but needs validation)
3. **subset-003-topk-zero**: Search with top_k=0 ✅ (accepts zero limit)

### Milvus Not Working

Milvus failed on ALL cases due to schema creation bug.

---

## Honest Status

| Question | Answer |
|----------|--------|
| Did we run both databases? | ✅ Yes |
| Are results meaningful? | ❌ No - Milvus adapter bug |
| Are there genuine diffs? | ❌ None confirmed |
| Can we use for papers? | ❌ No - findings are adapter bugs |
| Should we promote more cases? | ❌ No - fix current cases first |

---

## Next Steps

1. **Fix Milvus adapter** - Add primary_key to schema creation
2. **Re-run first subset** - Get fair comparison
3. **Validate results** - Ensure both adapters work equally well
4. **Then** - Consider expanding to more cases

**Current Status**: Framework works, but adapter bug invalidates results.
