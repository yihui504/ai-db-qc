# Full R4 Execution Plan (Frozen)

**Version**: 1.0 (Frozen)
**Date**: 2026-03-09
**Status**: READY FOR EXECUTION
**Scope**: All 8 Semantic Properties across Milvus and Qdrant

---

## Executive Summary

This plan defines the complete execution workflow for the full R4 differential testing campaign. It specifies the exact property list, per-database execution flow, expected artifacts, post-run review flow, and success criteria.

**Total Properties**: 8
**Total Test Cases**: 8
**Total Test Steps**: 32 (aggregated)
**Estimated Duration**: 2-3 hours

---

## Exact Property List

From `docs/R4_FULL_CASE_PACK_FROZEN.md`:

| Case ID | Property | Category | Oracle Rule | Steps |
|---------|----------|----------|-------------|-------|
| **R4-001** | Post-Drop Rejection | PRIMARY | Rule 1 | 7 |
| **R4-002** | Deleted Entity Visibility | PRIMARY | Rule 2 | 7 |
| **R4-003** | Delete Idempotency | PRIMARY | Rule 4 | 6 |
| **R4-004** | Index-Independent Search | ALLOWED-SENSITIVE | Rule 3 | 3 |
| **R4-005** | Load-State Enforcement | ALLOWED-SENSITIVE | Rule 7 | 3 |
| **R4-006** | Empty Collection Handling | EXPLORATORY | Rule 5 | 2 |
| **R4-007** | Non-Existent Delete Tolerance | PRIMARY | Rule 4 | 2 |
| **R4-008** | Collection Creation Idempotency | PRIMARY | Rule 6 | 2 |

---

## Per-Database Execution Flow

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    R4 EXECUTION ORCHESTRATOR               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐         ┌──────────────┐               │
│  │   Milvus     │         │   Qdrant     │               │
│  │   Adapter    │         │   Adapter    │               │
│  └──────┬───────┘         └──────┬───────┘               │
│         │                       │                           │
│         ▼                       ▼                           │
│  ┌──────────────┐         ┌──────────────┐               │
│  │ Milvus       │         │ Qdrant       │               │
│  │ Database     │         │ Database     │               │
│  │ (localhost: │         │ (localhost:  │               │
│  │   19530)     │         │   6333)      │               │
│  └──────┬───────┘         └──────┬───────┘               │
│         │                       │                           │
│         └───────────┬───────────┘                           │
│                     ▼                                       │
│            ┌────────────────┐                            │
│            │ Differential    │                            │
│            │ Comparison     │                            │
│            │ Engine         │                            │
│            └────────┬───────┘                            │
│                     ▼                                       │
│            ┌────────────────┐                            │
│            │ Oracle         │                            │
│            │ Classification │                            │
│            └────────┬───────┘                            │
│                     ▼                                       │
│            ┌────────────────┐                            │
│            │ Report         │                            │
│            │ Generator      │                            │
│            └────────────────┘                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Execution Sequence

For each test case (R4-001 through R4-008):

1. **Initialize Adapters** (once at start)
   - Connect to Milvus (localhost:19530)
   - Connect to Qdrant (localhost:6333)
   - Verify health of both connections

2. **Execute Test Sequence on Milvus**
   - For each step in the test sequence:
     - Execute operation via Milvus adapter
     - Capture result (status, data, error)
     - Store in raw results

3. **Execute Test Sequence on Qdrant**
   - For each step in the test sequence:
     - Execute operation via Qdrant adapter
     - Capture result (status, data, error)
     - Store in raw results

4. **Compare Results**
   - Extract test step results from both databases
   - Compare statuses (success/error)
   - Compare data (if applicable)
   - Compare errors (if applicable)

5. **Apply Oracle Classification**
   - Retrieve applicable oracle rule
   - Apply classification logic
   - Determine category (BUG, ALLOWED, OBSERVATION)
   - Generate reasoning

6. **Store Results**
   - Save raw per-database results (JSON)
   - Save differential classification (JSON)
   - Append to campaign summary

7. **Repeat** for next test case

---

## Test Execution Template

### Generic Template (Applied to All Cases)

```python
def execute_r4_case(case_id, case_spec, adapters):
    """Execute a single R4 test case on both databases."""

    # 1. Execute on Milvus
    milvus_results = []
    for step in case_spec["sequence"]:
        result = adapters["milvus"].execute({
            "operation": step["operation"],
            "params": adapt_for_milvus(step["params"])
        })
        milvus_results.append({
            "step": step["step"],
            "operation": step["operation"],
            "status": result["status"],
            "data": result.get("data"),
            "error": result.get("error")
        })

    # 2. Execute on Qdrant
    qdrant_results = []
    for step in case_spec["sequence"]:
        result = adapters["qdrant"].execute({
            "operation": step["operation"],
            "params": adapt_for_qdrant(step["params"])
        })
        qdrant_results.append({
            "step": step["step"],
            "operation": step["operation"],
            "status": result["status"],
            "data": result.get("data"),
            "error": result.get("error")
        })

    # 3. Extract test step
    test_step = case_spec["test_step"]
    milvus_test = milvus_results[test_step - 1]
    qdrant_test = qdrant_results[test_step - 1]

    # 4. Compare and classify
    comparison = compare_step(milvus_test, qdrant_test)
    classification = apply_oracle(comparison, case_spec["oracle_rule"])

    # 5. Store results
    return {
        "case_id": case_id,
        "milvus_results": milvus_results,
        "qdrant_results": qdrant_results,
        "comparison": comparison,
        "classification": classification
    }
```

### Adaptation Functions

```python
def adapt_for_milvus(params):
    """Adapt parameters for Milvus (no-op for now)."""
    # Milvus uses explicit field names, vector specs
    return params  # Currently aligned

def adapt_for_qdrant(params):
    """Adapt parameters for Qdrant (ID handling)."""
    # Qdrant requires explicit IDs
    if "vectors" in params and "ids" not in params:
        params = params.copy()
        params["ids"] = list(range(len(params["vectors"])))
    return params
```

---

## Expected Artifacts

### Directory Structure

```
results/r4-full-YYYYMMDD-HHMMSS/
├── raw/
│   ├── r4_001_milvus.json
│   ├── r4_001_qdrant.json
│   ├── r4_002_milvus.json
│   ├── r4_002_qdrant.json
│   ...
│   └── r4_008_qdrant.json
├── differential/
│   ├── r4_001_classification.json
│   ├── r4_002_classification.json
│   ...
│   └── r4_008_classification.json
├── summary.json
└── logs/
    └── execution.log
```

### Raw Results Format (Per Database)

**File**: `raw/r4_XXX_milvus.json`

```json
{
  "database": "milvus",
  "case_id": "r4_001",
  "property": "Post-Drop Rejection",
  "property_number": 1,
  "oracle_rule": "Rule 1 (Search After Drop)",
  "timestamp": "2026-03-09T22:00:00Z",
  "steps": [
    {
      "step": 1,
      "operation": "create_collection",
      "status": "success",
      "data": {...},
      "error": null
    },
    ...
  ]
}
```

### Differential Classification Format

**File**: `differential/r4_XXX_classification.json`

```json
{
  "case_id": "r4_001",
  "property": "Post-Drop Rejection",
  "property_number": 1,
  "oracle_rule": "Rule 1 (Search After Drop)",
  "test_step": 7,
  "comparison": {
    "milvus_status": "error",
    "qdrant_status": "error",
    "milvus_error": "Collection not exist",
    "qdrant_error": "Collection not found"
  },
  "classification": {
    "result": "CONSISTENT",
    "category": "PASS",
    "reasoning": "Both databases correctly fail search on dropped collection"
  },
  "timestamp": "2026-03-09T22:00:00Z"
}
```

### Campaign Summary Format

**File**: `summary.json`

```json
{
  "campaign": "R4 Full Differential Testing",
  "version": "1.0",
  "timestamp": "2026-03-09T22:00:00Z",
  "databases": ["milvus", "qdrant"],
  "total_cases": 8,
  "results": {
    "total_cases": 8,
    "pass_consistent": 0,
    "allowed_difference": 0,
    "bugs": 0,
    "observation": 0
  },
  "by_category": {
    "primary": {
      "total": 5,
      "pass": 0,
      "allowed": 0,
      "bugs": 0,
      "observation": 0
    },
    "allowed_sensitive": {
      "total": 2,
      "pass": 0,
      "allowed": 0,
      "bugs": 0,
      "observation": 0
    },
    "exploratory": {
      "total": 1,
      "pass": 0,
      "allowed": 0,
      "bugs": 0,
      "observation": 0
    }
  }
}
```

---

## Post-Run Review Flow

### Step 1: Automated Validation

**Checks**:
- [ ] All 8 cases executed on both databases
- [ ] All raw results files created (16 files)
- [ ] All classification files created (8 files)
- [ ] Summary file created
- [ ] No execution crashes or unhandled exceptions

**Output**: Validation report

---

### Step 2: Manual Classification Review

**Process**: Review each differential classification

**For each case**:
1. Read raw results for both databases
2. Read automated classification
3. Verify oracle rule application
4. Confirm reasoning is accurate
5. Approve or flag for review

**Output**: Classification validation report

---

### Step 3: Behavioral Analysis

**Process**: Analyze patterns across all cases

**Analysis**:
1. Count categories (PASS, ALLOWED, BUG, OBSERVATION)
2. Identify any unexpected classifications
3. Document any real behavioral differences
4. Document any adapter artifacts

**Output**: Behavioral analysis summary

---

### Step 4: Report Generation

**Process**: Generate comprehensive campaign report

**Report Sections**:
1. Executive Summary
2. Campaign Statistics
3. Per-Property Results
4. Differential Findings
5. Behavioral Catalog
6. Classification Validation
7. Recommendations

**Output**: `docs/R4_FULL_REPORT.md`

---

## Success Criteria

### Minimum Success (Go/No-Go)

**Criteria**: All 8 properties execute successfully

**Requirements**:
- ✅ All 8 cases execute without crashes
- ✅ All raw results captured (16 files)
- ✅ All classifications generated (8 files)
- ✅ Classification validation passes
- ✅ Report generated

**Outcome**: Campaign considered successful if all criteria met

---

### Stretch Success

**Criteria**: Meaningful behavioral insights

**Requirements**:
- ✅ All minimum success criteria met
- ✅ Clear behavioral differences documented
- ✅ Classification validation passes with 100% confidence
- ✅ Insights into architectural trade-offs identified
- ✅ Portability guide sections completed

**Outcome**: Campaign considered highly successful

---

### Failure Conditions

**Automatic Failure** (any red flag):
- ❌ Campaign crashes before completion
- ❌ More than 50% of cases fail to execute
- ❌ Classification validation fails
- ❌ Cannot generate report

**Investigation Required**:
- ⚠️ Unexpected BUG classifications (require manual verification)
- ⚠️ Adapter artifacts interfering with classification
- ⚠️ High rate of execution errors

---

## Risk Mitigation

### Pre-Execution Checks

**Before running full campaign**:

1. **Environment Validation**
   - [ ] Milvus running and accessible (localhost:19530)
   - [ ] Qdrant running and accessible (localhost:6333)
   - [ ] Both adapters import successfully
   - [ ] Adapter health checks pass

2. **Configuration Validation**
   - [ ] Results directory writable
   - [ ] Sufficient disk space for results
   - [ ] Python dependencies installed

3. **Data Validation**
   - [ ] Frozen case pack loaded correctly
   - [ ] Classification rules loaded correctly
   - [ ] All test cases parse successfully

---

### During Execution Monitoring

**Watch for**:
- Connection drops (automatic retry may be needed)
- Timeout errors (increase timeout if needed)
- Memory issues (monitor process)
- Disk space issues (check available space)

---

### Post-Execution Validation

**Checks**:
- [ ] All expected files created
- [ ] File contents parse as valid JSON
- [ ] Summary statistics are accurate
- [ ] No data corruption or truncation

---

## Execution Timeline

### Estimated Duration

| Phase | Duration | Notes |
|-------|----------|-------|
| Environment Setup | 5 min | Verify connections |
| Case Execution | 90-120 min | ~12-15 min per case |
| Automated Validation | 5 min | Check outputs |
| Manual Review | 30-60 min | Review classifications |
| Report Generation | 30-45 min | Write report |
| **Total** | **2.5-3.5 hours** | |

---

## Command-Line Execution

### Run Full Campaign

```bash
# From project root
python scripts/run_full_r4_differential.py

# Output directory will be created with timestamp:
# results/r4-full-YYYYMMDD-HHMMSS/
```

### Run with Custom Configuration

```bash
python scripts/run_full_r4_differential.py \
    --milvus-host localhost \
    --milvus-port 19530 \
    --qdrant-url http://localhost:6333 \
    --output-dir results/r4-custom
```

---

## Contingency Plans

### Issue: Case Execution Failure

**Scenario**: A test case fails partway through execution

**Mitigation**:
1. Log failure details
2. Continue with remaining cases
3. Mark failed case as "ERRORED" in summary
4. Re-run failed case after fixing issue

---

### Issue: Database Connection Loss

**Scenario**: Database connection drops during execution

**Mitigation**:
1. Implement retry logic (3 attempts)
2. If retry fails, mark case as "ERRORED"
3. Log connection error details
4. Provide option to resume after fixing connection

---

### Issue: Classification Validation Failure

**Scenario**: Automated classification may be incorrect

**Mitigation**:
1. Flag case for manual review
2. Do not fail entire campaign
3. Document manual classification
4. Continue with remaining cases

---

## Quality Gates

### Gate 1: Pre-Execution

**Entry Criteria**:
- [ ] R4 Phase 1 pilot approved
- [ ] Frozen case pack validated
- [ ] Frozen classification rules validated
- [ ] Execution plan approved

**Owner**: Manual approval

---

### Gate 2: Post-Execution

**Entry Criteria**:
- [ ] All 8 cases executed (or documented failures)
- [ ] Automated validation passes
- [ ] Classification review complete
- [ ] Report generated

**Owner**: Manual approval

---

## Metadata

- **Plan**: Full R4 Execution Plan (Frozen)
- **Version**: 1.0
- **Date**: 2026-03-09
- **Scope**: All 8 Semantic Properties
- **Test Cases**: 8
- **Databases**: Milvus, Qdrant
- **Estimated Duration**: 2-3 hours
- **Status**: FROZEN - Ready for Execution

---

## Summary of Frozen Components

### Frozen Documents

1. **`docs/R4_FULL_CASE_PACK_FROZEN.md`**
   - 8 semantic properties
   - Category classifications (PRIMARY, ALLOWED-SENSITIVE, EXPLORATORY)
   - Detailed test sequences
   - Oracle rule mappings

2. **`docs/R4_FULL_CLASSIFICATION_RULES_FROZEN.md`**
   - 3 classification categories (BUG, ALLOWED DIFFERENCE, OBSERVATION)
   - Oracle rules per property
   - Decision framework
   - Classification decision tree

3. **`docs/R4_FULL_EXECUTION_PLAN_FROZEN.md`** (this document)
   - Exact property list
   - Per-database execution flow
   - Expected artifacts
   - Post-run review flow
   - Success criteria

---

**END OF FULL R4 EXECUTION PLAN (FROZEN)**

**Status**: FROZEN PACKAGE READY - Awaiting final approval to execute full R4 campaign.

**Next**: Upon approval, execute `scripts/run_full_r4_differential.py` to run the full campaign.
