# Differential Campaign Audit & Refinement

> **Date**: 2026-03-07
> **Purpose**: Analyze seekdb dry run (1 success, 29 failures) and refine shared case pack

---

## Part A: Seekdb Failure Audit

### Root Causes Identified

| Issue | Cases Affected | Root Cause | Fix Required |
|-------|----------------|------------|--------------|
| **Template substitution failure** | 1-30 (create_collection) | `{id}` not substituted, appears literally in SQL | Fix instantiator or use literal names |
| **Missing collection setup** | 4-30 (search/insert/delete) | `diff_test` collection never created | Add setup phase or skip dependent ops |
| **SQL injection vulnerability** | All | Direct string interpolation in SQL | Use parameterized queries |
| **Empty vector handling** | diff-boundary-009, diff-diag-007 | Empty lists cause SQL syntax errors | Add validation |

### Failure Breakdown (29 total)

| Category | Count | Cases | Real Finding? |
|----------|-------|-------|---------------|
| Template substitution bug | ~10 | diff-boundary-001 to 010, diff-diag-001-010 | **NO** - Framework bug |
| Missing collection | ~15 | All search/insert/delete ops | **NO** - Setup issue |
| Empty vector parameter | 2 | diff-boundary-009, diff-diag-007 | **MAYBE** - Needs validation |
| Collection doesn't exist | 10 | All precondition tests | **YES** - Expected for precond tests |

### Actual Successes (1)

| Case | Why it succeeded |
|------|------------------|
| diff-precond-010 | `drop_collection` on non-existent collection - seekdb succeeds silently (interesting difference!) |

---

## Part B: Case Pack Classification (30 cases)

### Category 1: Directly Runnable (5 cases)
*Valid syntax, no setup dependencies*

| Case ID | Operation | Status |
|---------|-----------|--------|
| diff-precond-009 | create_collection (valid) | ✅ Runnable |
| diff-precond-010 | drop_collection | ✅ Runnable (found diff!) |
| diff-diag-010 | insert (needs collection) | ⚠️ Needs setup |
| diff-precond-007 | search (needs collection+index) | ⚠️ Needs setup |
| diff-precond-008 | insert (needs collection) | ⚠️ Needs setup |

### Category 2: Needs Template Fix (10 cases)
*`{id}` substitution not working*

| Case ID | Operation | Issue | Fix |
|---------|-----------|-------|-----|
| diff-boundary-001 to 010 | create_collection | `{id}` in table name | Use literal names |
| diff-diag-001, 002 | create_collection | `{id}` in table name | Use literal names |
| diff-precond-009 | create_collection | `{id}` in table name | Already uses literal |

### Category 3: Needs Setup Phase (12 cases)
*Depend on collection existing*

| Case ID | Operation | Dependency |
|---------|-----------|------------|
| diff-boundary-004 to 006 | search | collection exists |
| diff-boundary-009, 010 | insert | collection exists |
| diff-diag-003 to 010 | search/insert/delete | collection exists |
| diff-precond-001 to 008 | Various | collection exists |

### Category 4: Precondition Tests (10 cases)
*Expected to fail without proper setup*

| Case ID | Operation | Expected behavior |
|---------|-----------|-------------------|
| diff-precond-001 to 006 | Operations on non-existent | Should fail gracefully |
| diff-precond-004 | Search on empty | Should return empty |
| diff-precond-005 | Search before index load | Should fail or succeed |

---

## Part C: Campaign-Ready Subset (v1)

After pruning cases with framework bugs, here's the **campaign-ready subset**:

### Core Set: 12 Fair Cases

| Case ID | Operation | Comparison Value | Both DBs Ready |
|---------|-----------|------------------|----------------|
| diff-precond-009 | create_collection (valid) | Baseline success | ✅ |
| diff-precond-010 | drop_nonexistent | **Already found diff!** | ✅ |
| diff-boundary-001 | create dim=0 | Invalid param handling | ⚠️ Fix template |
| diff-boundary-002 | create dim=-1 | Invalid param handling | ⚠️ Fix template |
| diff-boundary-007 | create invalid metric | Invalid param handling | ⚠️ Fix template |
| diff-diag-001 | create dim=0 | Diagnostic quality | ⚠️ Fix template |
| diff-diag-002 | create invalid metric | Diagnostic quality | ⚠️ Fix template |
| diff-precond-001 | search nonexistent | Precondition handling | ✅ |
| diff-precond-002 | insert nonexistent | Precondition handling | ✅ |
| diff-precond-003 | delete nonexistent | Precondition handling | ✅ |
| diff-diag-004 | search nonexistent | Diagnostic quality | ✅ |
| diff-diag-005 | insert nonexistent | Diagnostic quality | ✅ |

**Status**: 6 ✅ immediately runnable, 6 need template fix

---

## Part D: Required Fixes

### Fix 1: Template Substitution (CRITICAL)

The instantiator is not substituting `{id}` in collection names.

**Problem**: `collection_name: "test_boundary_{id}"` → SQL contains literal `{id}`

**Solution Options**:
1. Fix instantiator to handle `{id}` substitution
2. Use literal collection names in templates
3. Use a different substitution pattern like `@@id@@`

**Recommendation**: Use literal names for v1 campaign

### Fix 2: Setup Phase (RECOMMENDED)

Add a setup phase that:
1. Creates test collections with valid schemas
2. Inserts test data
3. Builds/loads indexes
4. Handles cleanup

**Implementation**: Add `setup` and `teardown` operations to campaign runner

### Fix 3: seekdb Adapter SQL Safety (REQUIRED)

The seekdb adapter uses direct string interpolation:

```python
# CURRENT (unsafe):
sql = f"CREATE TABLE {collection_name} ..."
# If collection_name contains "{id}", SQL breaks

# NEEDED (safe):
# 1. Validate collection_name format
# 2. Use proper SQL escaping
# 3. Handle edge cases
```

---

## Part E: Milvus Adapter Interface Check

### Current Milvus Adapter Interface

Need to verify `adapters/milvus_adapter.py`:

```python
# How does MilvusAdapter.__init__ work?
# Expected: MilvusAdapter(api_endpoint="...", collection="...")

# Current assumption in differential runner:
milvus_adapter = MilvusAdapter(
    api_endpoint=args.milvus_endpoint,  # http://localhost:19530
    collection="diff_test"
)
```

**Action**: Read `adapters/milvus_adapter.py` to verify interface compatibility

---

## Recommendations

### Immediate Actions (Before Full Campaign)

1. **Fix template substitution** - Use literal collection names
2. **Add setup phase** - Create collections before dependent operations
3. **Verify Milvus adapter** - Confirm interface compatibility
4. **Run reduced campaign** - Start with 12 core cases

### Campaign v1.1 Target

- **12 core cases** (6 immediately runnable, 6 after template fix)
- **Setup phase** included
- **Meaningful comparison** on:
  - Invalid parameter handling
  - Precondition failure modes
  - Diagnostic quality

### Defer to v2

- Empty vector edge cases (need validation logic)
- Very large dimension tests (may timeout)
- Index state testing (complex setup)

---

## Summary

| Metric | Value |
|--------|-------|
| Original cases | 30 |
| Template bugs | ~10 |
| Setup dependencies | ~12 |
| Immediately runnable | 6 |
| Campaign-ready (after fixes) | 12 |
| Actual findings (preliminary) | 1 (drop_nonexistent behavior) |

**Judgment**: The framework works, but the shared case pack needs tuning before full differential comparison. Fix template substitution and add setup phase, then run with 12 core cases.
