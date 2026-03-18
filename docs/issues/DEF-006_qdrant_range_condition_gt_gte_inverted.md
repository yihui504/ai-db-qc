# DEF-006 — Qdrant Adapter: `_build_range_condition` Maps `gt`→`gte` and `gte`→`gt` (Inverted Comparators)

**ID:** DEF-006  
**Database / Component:** Qdrant adapter (`adapters/qdrant_adapter.py`)  
**Category:** Framework-level adapter bug (NOT a database bug)  
**Severity:** High (all range filter queries against Qdrant produce wrong results)  
**Status:** FIXED (2026-03-17)  
**Detected by:** Code review during triage of SUSPICIOUS verdicts on range-filter test cases  
**Oracle:** FUO (Filtered-vs-Unfiltered Oracle) — filtered result set did not shrink as expected  

---

## Summary

`QdrantAdapter._build_range_condition()` constructed Qdrant `models.Range` objects with the
`gt` and `gte` comparator fields swapped: a filter key `"gt"` was mapped to `Range(gte=...)`,
and `"gte"` was mapped to `Range(gt=...)`.

This caused every range condition to be semantically inverted relative to its intent:

| Intended filter       | Actual Qdrant condition |
|-----------------------|------------------------|
| `score > 5`          | `score >= 5` (includes boundary) |
| `score >= 5`         | `score > 5` (excludes boundary) |

The same swap also affected `lte`: `"lte"` was mapped to `Range(gt=...)` instead of `Range(lte=...)`.

---

## Root Cause

Lines 401–416 (pre-fix) in `qdrant_adapter.py`:

```python
# BUGGY CODE (before fix)
if "gt" in range_spec:
    range_conditions.append(
        models.Range(gte=float(range_spec["gt"]))   # ← wrong: should be gt=
    )
if "gte" in range_spec:
    range_conditions.append(
        models.Range(gt=float(range_spec["gte"]))   # ← wrong: should be gte=
    )
# ...
if "lte" in range_spec:
    range_conditions.append(
        models.Range(gt=float(range_spec["lte"]))   # ← wrong: should be lte=
    )
```

The likely cause is a copy-paste error when the `lt` branch (which was correct) was duplicated
for `lte`, and similarly for the `gt`/`gte` pair.

---

## Reproduction

```python
from adapters.qdrant_adapter import QdrantAdapter

adapter = QdrantAdapter(...)
# Insert 100 vectors with payload {"score": i} for i in range(100)
result = adapter.execute({
    "operation": "filtered_search",
    "params": {
        "collection_name": "test_col",
        "vector": [0.1] * 128,
        "filter": {"score": {"gt": 50}},   # intent: score STRICTLY > 50
        "top_k": 100,
    }
})
# Expected: entities with score 51..99 (49 entities)
# Actual:   entities with score 50..99 (50 entities — boundary included by gte bug)
```

The off-by-one error is detectable by the FUO oracle when comparing filtered vs. unfiltered
result counts against a ground truth derived from the inserted scalar data.

---

## Impact

- All range filter queries (`gt`, `gte`, `lte`) produce results that include or exclude the
  boundary value incorrectly.
- The `"gt"` comparator behaves as `"gte"` and vice versa, silently returning wrong entity sets.
- This caused FUO oracle verdicts to escalate to SUSPICIOUS/LIKELY_BUG on every range-filter
  test case in the Qdrant test campaign, all of which were false positives.
- Affected test dimensions: R5D filter tests with numeric range conditions.

---

## Fix

Corrected the comparator-to-field mapping in `_build_range_condition`:

```python
# FIXED CODE
if "gt" in range_spec:
    range_conditions.append(
        models.Range(gt=float(range_spec["gt"]))    # gt → gt ✓
    )
if "gte" in range_spec:
    range_conditions.append(
        models.Range(gte=float(range_spec["gte"]))  # gte → gte ✓
    )
if "lt" in range_spec:
    range_conditions.append(
        models.Range(lt=float(range_spec["lt"]))    # lt → lt ✓ (was already correct)
    )
if "lte" in range_spec:
    range_conditions.append(
        models.Range(lte=float(range_spec["lte"]))  # lte → lte ✓
    )
```

---

## Verification

After the fix:
- `{"score": {"gt": 50}}` → Qdrant `Range(gt=50.0)` → returns only score > 50 ✓
- `{"score": {"gte": 50}}` → Qdrant `Range(gte=50.0)` → returns score ≥ 50 ✓
- `{"score": {"lte": 50}}` → Qdrant `Range(lte=50.0)` → returns score ≤ 50 ✓
- `{"score": {"gt": 10, "lte": 100}}` → `Range(gt=10.0, lte=100.0)` ✓

---

## Lessons Learned

Range condition mappings between internal API semantics and database SDK field names are
error-prone and should be covered by unit tests that verify boundary inclusion/exclusion
behaviour for every comparator (`gt`, `gte`, `lt`, `lte`).

The framework should add a cross-adapter range-filter unit test suite that inserts a
known dataset and verifies exact result counts for each comparator type.
