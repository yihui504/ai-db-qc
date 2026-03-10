# R4 Full Campaign Package (Frozen)

**Package Version**: 1.0
**Date**: 2026-03-09
**Status**: FROZEN - READY FOR EXECUTION (pending final approval)

---

## Package Overview

This frozen package contains all components needed to execute the full R4 differential testing campaign across 8 semantic properties on Milvus and Qdrant.

**Package Components**:
1. Full R4 Case Pack (Frozen)
2. Full R4 Classification Rules (Frozen)
3. Full R4 Execution Plan (Frozen)

---

## Quick Reference

### Test Scope

| Metric | Count |
|--------|-------|
| **Total Properties** | 8 |
| **Primary Tests** | 5 |
| **Allowed-Difference-Sensitive** | 2 |
| **Exploratory Tests** | 1 |
| **Total Test Steps** | 32 |

### Classification Categories

| Category | Definition | Oracle Source |
|----------|------------|---------------|
| **BUG** | Contract violation | `R4_FULL_CLASSIFICATION_RULES_FROZEN.md` |
| **ALLOWED DIFFERENCE** | Architectural variation | `R4_FULL_CLASSIFICATION_RULES_FROZEN.md` |
| **OBSERVATION** | Undefined/edge case | `R4_FULL_CLASSIFICATION_RULES_FROZEN.md` |

### Execution Details

| Aspect | Details |
|--------|---------|
| **Databases** | Milvus (localhost:19530), Qdrant (localhost:6333) |
| **Adapter Files** | `adapters/milvus_adapter.py`, `adapters/qdrant_adapter.py` |
| **Execution Script** | `scripts/run_full_r4_differential.py` (to be created) |
| **Estimated Duration** | 2-3 hours |
| **Results Directory** | `results/r4-full-YYYYMMDD-HHMMSS/` |

---

## Document Index

### 1. Full R4 Case Pack (Frozen)

**File**: `docs/R4_FULL_CASE_PACK_FROZEN.md`

**Contents**:
- All 8 semantic properties with detailed specifications
- Category classifications (PRIMARY, ALLOWED-SENSITIVE, EXPLORATORY)
- Test sequences for each property
- Oracle rule mappings
- Adaptive sequence template

**Key Sections**:
- Property Classification Matrix (quick reference table)
- Detailed Property Specifications (R4-001 through R4-008)
- Test Case Summary (steps and critical steps)
- Priority for Execution (Tier 1-4)

---

### 2. Full R4 Classification Rules (Frozen)

**File**: `docs/R4_FULL_CLASSIFICATION_RULES_FROZEN.md`

**Contents**:
- 3 classification categories with definitions
- Oracle rules for each property (Rules 1-7)
- Decision framework for classification
- Classification decision tree
- Examples of oracle application

**Key Sections**:
- Classification Categories (BUG, ALLOWED DIFFERENCE, OBSERVATION)
- Property-Specific Classification Rules
- Decision Framework
- Validation Checklist

---

### 3. Full R4 Execution Plan (Frozen)

**File**: `docs/R4_FULL_EXECUTION_PLAN_FROZEN.md`

**Contents**:
- Exact property list (8 properties)
- Per-database execution flow
- Expected artifacts (file formats and directory structure)
- Post-run review flow (4 steps)
- Success criteria (minimum and stretch)
- Risk mitigation and contingency plans

**Key Sections**:
- Exact Property List
- Per-Database Execution Flow (architecture diagram)
- Expected Artifacts (16 raw result files, 8 classification files)
- Post-Run Review Flow (validation, manual review, analysis, reporting)
- Success Criteria (minimum and stretch)

---

## Property Quick Reference

| Case ID | Property | Category | Oracle Rule | Test Step |
|---------|----------|----------|-------------|-----------|
| R4-001 | Post-Drop Rejection | PRIMARY | Rule 1 | Step 7 (search after drop) |
| R4-002 | Deleted Entity Visibility | PRIMARY | Rule 2 | Step 7 (search after delete) |
| R4-003 | Delete Idempotency | PRIMARY | Rule 4 | Step 6 (second delete) |
| R4-004 | Index-Independent Search | ALLOWED-SENSITIVE | Rule 3 | Step 3 (search without index) |
| R4-005 | Load-State Enforcement | ALLOWED-SENSITIVE | Rule 7 | Step 3 (search without load) |
| R4-006 | Empty Collection Handling | EXPLORATORY | Rule 5 | Step 2 (search empty) |
| R4-007 | Non-Existent Delete Tolerance | PRIMARY | Rule 4 | Step 2 (delete non-existent) |
| R4-008 | Collection Creation Idempotency | PRIMARY | Rule 6 | Step 2 (duplicate creation) |

---

## Expected Outcomes

### Minimum Success

**Criteria**: All 8 properties execute successfully

**Expected Distribution**:
- PRIMARY (5 properties): Expected 4-5 CONSISTENT, 0-1 ALLOWED DIFFERENCE
- ALLOWED-SENSITIVE (2 properties): Expected 0-2 ALLOWED DIFFERENCES
- EXPLORATORY (1 property): Expected OBSERVATION

**Outcome**: Campaign considered successful if all criteria met

---

### Stretch Success

**Criteria**: Meaningful behavioral insights and clear documentation

**Expected Distribution**:
- PRIMARY (5 properties): 5 CONSISTENT, 0 bugs (all must be consistent or allowed)
- ALLOWED-SENSITIVE (2 properties): 2 ALLOWED DIFFERENCES (architectural differences documented)
- EXPLORATORY (1 property): 1 OBSERVATION (edge case characterized)

**Outcome**: Campaign considered highly successful if all expected differences are documented

---

## Quality Gates

### Gate 1: Pre-Execution (Current)

**Entry Criteria**:
- ✅ R4 Phase 1 pilot completed (3/3 CONSISTENT)
- ✅ Frozen case pack created and validated
- ✅ Frozen classification rules created and validated
- ✅ Frozen execution plan created and validated
- ⏳ Full R4 package approval (PENDING)

---

### Gate 2: Post-Execution

**Entry Criteria**:
- ⏳ All 8 cases executed
- ⏳ Automated validation passes
- ⏳ Manual classification review complete
- ⏳ Full report generated

**Owner**: Manual approval

---

## Checklist for Execution Approval

Before executing full R4 campaign:

### Documentation Review
- [ ] Case pack reviewed and understood
- [ ] Classification rules reviewed and understood
- [ ] Execution plan reviewed and understood
- [ ] All three frozen documents aligned

### Environment Readiness
- [ ] Milvus running and accessible (localhost:19530)
- [ ] Qdrant running and accessible (localhost:6333)
- [ ] Both adapters implemented and tested
- [ ] Pilot campaign passed (GO status)

### Contingency Planning
- [ ] Risk mitigation reviewed
- [ ] Contingency plans understood
- [ ] Success criteria accepted

---

## How to Use This Package

### For Execution

1. **Review all three frozen documents**
2. **Verify environment readiness**
3. **Execute using execution script** (to be created)
4. **Follow post-run review flow**
5. **Generate final report**

### For Review

Each frozen document can be reviewed independently:
- `R4_FULL_CASE_PACK_FROZEN.md` - WHAT to test
- `R4_FULL_CLASSIFICATION_RULES_FROZEN.md` - HOW to classify
- `R4_FULL_EXECUTION_PLAN_FROZEN.md` - HOW to execute

---

## Changes from Pilot

### What's New in Full R4

**Scope Expansion**:
- Pilot: 3 properties
- Full R4: 8 properties (+5 properties)

**New Properties**:
- R4-002: Deleted Entity Visibility (PRIMARY)
- R4-004: Index-Independent Search (ALLOWED-SENSITIVE)
- R4-005: Load-State Enforcement (ALLOWED-SENSITIVE)
- R4-006: Empty Collection Handling (EXPLORATORY)
- R4-008: Collection Creation Idempotency (PRIMARY)

**Enhanced Artifacts**:
- Comprehensive raw results (16 files vs. 6)
- More classifications (8 vs. 3)
- Full campaign report (vs. pilot report)

---

## Metadata

- **Package**: R4 Full Campaign (Frozen)
- **Version**: 1.0
- **Date**: 2026-03-09
- **Status**: FROZEN - Ready for Execution (pending final approval)
- **Components**: 3 frozen documents
- **Test Properties**: 8
- **Test Cases**: 8
- **Databases**: Milvus, Qdrant

---

## Approval Status

| Component | Status | Approver | Date |
|-----------|--------|----------|------|
| R4 Phase 1 Pilot | ✅ Complete | Auto | 2026-03-09 |
| R4 Full Case Pack | ⏳ Frozen | Pending | 2026-03-09 |
| R4 Classification Rules | ⏳ Frozen | Pending | 2026-03-09 |
| R4 Execution Plan | ⏳ Frozen | Pending | 2026-03-09 |
| Full R4 Execution | ⏳ Pending | Pending | Pending |

---

**END OF R4 FULL CAMPAIGN PACKAGE (FROZEN)**

**Current Status**: Package complete and frozen. Awaiting final approval to proceed with full R4 execution.

**Next Step**: Upon approval, proceed with full R4 campaign execution.
