# R6A-001 First Slice Plan

**Campaign ID**: R6A-001
**Date**: 2026-03-10
**Status**: PLANNING

---

## Capability Audit (P1)

Based on `capabilities/milvus_capabilities.json`:

| Operation | Support Status | Validation Level | Campaign |
|-----------|----------------|------------------|----------|
| create_collection | supported | campaign_validated | R5B, R5D |
| insert | supported | campaign_validated | R5B, R5D |
| flush | supported | campaign_validated | R5B |
| load | supported | campaign_validated | R5B |
| search | supported | campaign_validated | R5B, R5D |
| count_entities | supported | campaign_validated | R5B |

**Conclusion**: All required operations are validated. No capability gaps.

---

## Contract Coverage Analysis (P2)

### Existing Coverage
- **ILC-009** (INDEX): Post-Insert Visibility - PASS (HIGH confidence)
  - Evidence: ILC-009b confirmed flush is required for search visibility
  - Note: This is in INDEX family, not CONS family

### Gaps in CONS Family
- No CONS family contracts exist yet
- R6A will establish the CONS family baseline

---

## First-Slice Contract List

### CONS-001: Insert Return vs Storage Visibility

**Statement**: insert() returns immediately, but storage_count visibility requires flush

**Oracle Strategy**: CONSERVATIVE

**Preconditions**:
- collection exists
- no prior data

**Operation Sequence**:
1. insert N entities
2. check insert_count (immediate return)
3. check num_entities (storage count, pre-flush)
4. flush
5. check num_entities (post-flush)

**Expected Classification**: OBSERVATION

**Evidence Needed**:
- insert_count == N (immediate)
- num_entities pre-flush: 0 or N (deterministic behavior)
- num_entities post-flush: N (flush enables storage visibility)

**Oracle Type**: CONSERVATIVE (document timing behavior)

---

### CONS-002: Flush Effect on Storage vs Search Visibility

**Statement**: flush enables storage_count visibility, but search visibility requires index update

**Oracle Strategy**: CONSERVATIVE

**Preconditions**:
- collection exists with index
- no prior data

**Operation Sequence**:
1. insert N entities
2. flush
3. check num_entities (storage count)
4. search without load (pre-index-update)
5. wait / load
6. search again (post-index-update)

**Expected Classification**: OBSERVATION

**Evidence Needed**:
- num_entities post-flush: N (storage visible)
- search pre-load: 0 results or error (index not updated)
- search post-load: N results (index updated, search visible)

**Oracle Type**: CONSERVATIVE (document index update timing)

---

### CONS-003: Load State Effect on Search Visibility

**Statement**: search requires loaded collection; unloaded collection returns EXPECTED_FAILURE or error

**Oracle Strategy**: STRICT

**Preconditions**:
- collection exists with data and index
- collection is unloaded

**Operation Sequence**:
1. verify collection unloaded (load_state = NotLoaded)
2. attempt search
3. load collection
4. attempt search again

**Expected Classification**: PASS (if strict gate enforced)

**Evidence Needed**:
- search pre-load: EXPECTED_FAILURE or error
- search post-load: returns results

**Oracle Type**: STRICT (gate violation = EXPECTED_FAILURE)

---

### CONS-004: Insert-Search Timing Window

**Statement**: insert → search without flush has deterministic (non-flush) behavior

**Oracle Strategy**: CONSERVATIVE

**Preconditions**:
- collection exists, loaded, with index
- no prior data

**Operation Sequence**:
1. insert N entities
2. immediate search (no flush, no wait)
3. wait 1 second
4. search again
5. flush
6. search final

**Expected Classification**: OBSERVATION or BUG_CANDIDATE

**Evidence Needed**:
- search immediate: 0 results (expected, no flush)
- search after wait: 0 results (expected, no flush)
- search after flush: N results (baseline)

**Oracle Type**: CONSERVATIVE (document that wait without flush doesn't enable search)

---

### CONS-005: Release Preserves Storage Data

**Statement**: release() preserves storage_count; reload restores search visibility

**Oracle Strategy**: STRICT

**Preconditions**:
- collection exists with data
- collection is loaded

**Operation Sequence**:
1. record num_entities (loaded)
2. search for baseline
3. release collection
4. check num_entities (storage count)
5. reload collection
6. search again
7. compare results

**Expected Classification**: PASS

**Evidence Needed**:
- num_entities unchanged after release
- search post-reload matches baseline

**Oracle Type**: STRICT (data preservation is invariant)

---

### CONS-006: Flush Idempotence

**Statement**: multiple flush calls are idempotent (no side effects)

**Oracle Strategy**: CONSERVATIVE

**Preconditions**:
- collection exists with data

**Operation Sequence**:
1. insert N entities
2. flush
3. check num_entities
4. flush again
5. check num_entities (should be unchanged)

**Expected Classification**: OBSERVATION

**Evidence Needed**:
- num_entities unchanged after second flush

**Oracle Type**: CONSERVATIVE (document idempotent behavior)

---

## Oracle Classifications

| Classification | Meaning | Usage |
|----------------|---------|-------|
| **PASS** | Expected behavior confirmed | STRICT invariants (data preservation) |
| **OBSERVATION** | Deterministic behavior documented | Timing behavior, implementation-specific |
| **EXPERIMENT_DESIGN_ISSUE** | Test setup invalid | Precondition violation, data missing |
| **BUG_CANDIDATE** | Unexpected behavior requiring investigation | Data loss, non-deterministic results |
| **INFRA_FAILURE** | Infrastructure issue (not a semantic bug) | Connection failure, timeout |
| **EXPECTED_FAILURE** | Precondition gate violation (intentional) | Testing unload gate, etc. |

---

## Implementation Plan

### Phase 1: Contract Definitions
- [x] Create CONS family directory
- [x] Define CONS-001 to CONS-006 contracts
- [ ] Write to `contracts/cons/r6a_001_contracts.json`

### Phase 2: Generator Implementation
- [ ] Implement `R6a001Generator.generate()`
- [ ] Generate 6 test cases (one per contract)
- [ ] Each case has: preconditions, operation_sequence, expected_classification

### Phase 3: Oracle Implementation
- [ ] Implement `R6a001Oracle.evaluate()`
- [ ] Support all 6 classification types
- [ ] Decision tree based on evidence collected

### Phase 4: Smoke Runner
- [ ] Implement smoke test execution
- [ ] Record execution trace with timestamps
- [ ] Call oracle for each case

### Phase 5: Execution
- [ ] Run smoke tests
- [ ] Update results index
- [ ] Generate report

---

## Minimal Implementation Files

1. `contracts/cons/r6a_001_contracts.json` - Contract definitions
2. `casegen/generators/r6a_001_generator.py` - Generate 6 cases
3. `pipeline/oracles/r6a_001_oracle.py` - Evaluate results
4. `scripts/run_r6a_001_smoke.py` - Execute tests

---

## Manual Review Required

1. **Contract definitions**: Are the 6 contracts covering the right semantic space?
2. **Expected classifications**: Are we being too strict or too loose?
3. **Case design**: Are preconditions and operation sequences correct?
4. **Oracle logic**: Does decision tree handle all edge cases?

---

## Success Criteria

- [ ] All 6 cases execute without INFRA_FAILURE
- [ ] Each case produces one of: PASS, OBSERVATION, EXPECTED_FAILURE
- [ ] No EXPERIMENT_DESIGN_ISSUE (indicates bad test design)
- [ ] Results are interpretable (not inconclusive)

---

## Next Steps

1. Review and approve first-slice plan
2. Implement generator with 6 cases
3. Implement oracle with decision tree
4. Run smoke tests
5. Summarize results
