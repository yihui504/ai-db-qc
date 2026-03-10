# R3 Campaign Decision Status

**Date**: 2026-03-09 (Updated)
**Decision**: Option B (Sequence-Based R3) - Framework Ready, Real Execution Pending
**Status**: Framework Implemented, Mock Dry-Run Complete, **REAL R3 NOT YET EXECUTED**

---

## Current Status

### Option B: Sequence-Based R3

**Framework Implementation**: ✅ COMPLETE
- Sequence testing framework implemented in `scripts/run_r3_sequence.py`
- 11 test cases defined in `casegen/templates/r3_sequence_state.yaml`
- Mock dry-run executed successfully
- All framework components validated

**Real Campaign Execution**: ❌ NOT COMPLETE
- First attempt used mock adapter (Milvus connection failed)
- Silent fallback to mock occurred
- No real Milvus behavior tested
- No valid issue findings can be claimed

### Next Required Step

**Execute real R3 campaign with proper environment transparency**:
1. Start Milvus (Docker or native)
2. Verify connection explicitly
3. Re-run with `--require-real` flag
4. Capture real environment evidence
5. Report only real findings

---

## Why R3 Parameter Version is Blocked (Original Decision)

The original R3 design focused on testing **documented parameter families** (consistency_level, index_params.nlist, index_params.m, search_params.nprobe) for validation weaknesses.

**Critical Finding**: ALL four planned R3 parameter families have **adapter support issues** that make them unsuitable for campaign use:

| Parameter | Issue | Status |
|-----------|-------|--------|
| **consistency_level** | Silent-ignore via **kwargs (like metric_type) | NOT SUITABLE |
| **index_params.nlist** | Adapter hardcodes nlist=128 | NOT SUITABLE |
| **index_params.m** | Adapter hardcodes nlist-based params | NOT SUITABLE |
| **search_params.nprobe** | Adapter hardcodes nprobe=10 | NOT SUITABLE |

Testing these parameters now would produce **tool-layer artifacts**, not actual database behavior findings.

---

## Option B: Operation Sequences (Current Direction)

### Design Focus

Test **sequences of operations** rather than individual parameter validation:

| Case ID | Sequence | Test Focus |
|---------|----------|------------|
| seq-001 | create → insert → search → delete → delete | Delete idempotency |
| seq-002 | create → insert → search (no index) → build_index → search | Index state dependency |
| seq-003 | create → insert → search → delete → search | Deleted entity visibility |
| seq-004 | create → insert → search → drop → search | Post-drop state bug |
| seq-005 | create → load → insert → search | Load-insert-search visibility |
| seq-006 | create → insert (multi) → delete (partial) → delete (remaining) → search | Multi-delete state consistency |

**Total**: 11 cases (6 primary, 3 calibration, 2 exploratory)

### Framework Validation Results

**Mock Dry-Run** (2026-03-09):
- ✅ All 11 sequences executed successfully
- ✅ No syntax or routing errors
- ✅ Post-run classification functional
- ❌ No real Milvus behavior tested
- ❌ No valid issue findings from mock data

### Adapter Support Verification

All operations used in sequence tests are fully supported:

| Operation | Adapter Support | Safe from Artifacts |
|-----------|----------------|---------------------|
| create_collection | ✅ Fully supported | Yes |
| insert | ✅ Fully supported | Yes |
| search | ✅ Fully supported | Yes |
| delete | ✅ Fully supported | Yes |
| drop_collection | ✅ Fully supported | Yes |
| build_index | ✅ Supported (with nlist=128) | Yes - standard params used |
| load | ✅ Fully supported | Yes |

**Conclusion**: Sequence testing uses currently-supported features, avoiding tool-layer artifacts.

---

## Why Option B (Operation Sequences) Was Chosen

Given the adapter gaps, three options were presented:

| Option | Description | Status |
|--------|-------------|--------|
| **A: Postpone R3** | Wait until adapter enhanced | POSTPONED (not abandoned) |
| **B: Operation Sequences** | Test state transitions with supported features | FRAMEWORK READY, REAL EXECUTION PENDING |
| **C: Cross-Database** | Compare Milvus vs SeekDB | NOT STARTED |

**Rationale for Option B**:
1. Uses currently-supported features (no adapter modifications needed)
2. Tests meaningful workflows (state transitions, idempotency)
3. Avoids kwargs/silent-ignore issues that plagued R1+R2
4. Aligns with "test-case correctness judgment" goal

---

## Execution Transparency Gap

### Missing from First Attempt

The mock dry-run did NOT provide:
- ❌ Docker/Milvus environment startup confirmation
- ❌ Milvus service status check
- ❌ Explicit connection verification
- ❌ No-silent-fallback enforcement

### Required for Real Execution

Before real R3 run, MUST:

1. **Show environment is running**:
   ```bash
   docker ps | grep milvus
   curl http://localhost:19530/health
   ```

2. **Verify connection explicitly**:
   ```bash
   python -c "from pymilvus import connections; connections.connect(...); print('OK')"
   ```

3. **Use --require-real flag**:
   ```bash
   python scripts/run_r3_sequence.py --adapter milvus --require-real
   ```

4. **Capture real evidence**:
   - Milvus version/capacity snapshot
   - Connection establishment confirmation
   - Real responses (not mock)

---

## Expected Outcomes (Real R3 Execution)

**Minimum Success**: >=1 state-transition or idempotency issue

**Stretch Success**: 2-3 issues

**Hypothesis**: Operation sequences may reveal:
- Idempotency violations (operations not truly idempotent)
- State dependency bugs (operations succeed when they shouldn't)
- Precondition bypass (operations succeed in wrong state)

---

## Documentation References

- **Full audit**: `docs/tooling_gaps/R3_PARAMETER_SUPPORT_AUDIT.md`
- **Redesigned R3**: `docs/plans/R3_REDESIGNED.md` (Option B proposal)
- **Original R3 design**: `docs/plans/R3_CAMPAIGN_DESIGN_FINAL.md`
- **Framework templates**: `casegen/templates/r3_sequence_state.yaml`
- **Mock dry-run report**: `docs/R3_MOCK_DRY_RUN_REPORT.md`

---

## Decision Rationale

**Quote from project goals**: "Our goal is not only to find issues, but to build a reliable AI-database QA method and tool."

The decision to pursue Option B reflects this broader goal:
- Tool-layer artifacts (silent-ignore, hardcoded values) undermine test validity
- Testing unsupported parameters creates misleading results
- Adapter gaps must be resolved before parameter validation campaigns can succeed
- Sequence testing offers immediate research novelty with minimal technical risk

**Option B will proceed when the real Milvus environment is properly established.**

---

## Option A Status: POSTPONED (Not Abandoned)

**Future Work Required**:
1. Enhance MilvusAdapter to support custom index_params
2. Enhance MilvusAdapter to support custom search_params
3. Verify which Collection parameters are actually supported
4. Re-audit after adapter changes
5. Then proceed with original R3 parameter validation design

**Timeline**: After Option B real execution completes

---

## Metadata

- **Decision Date**: 2026-03-08 (original), 2026-03-09 (updated)
- **Option Chosen**: Option B (Operation Sequences)
- **Framework Status**: Complete
- **Real Campaign Status**: Pending (requires Milvus environment setup)
- **Mock Dry-Run**: Complete (validated framework, not real findings)
- **See**: `docs/R3_MOCK_DRY_RUN_REPORT.md` for corrected framing
