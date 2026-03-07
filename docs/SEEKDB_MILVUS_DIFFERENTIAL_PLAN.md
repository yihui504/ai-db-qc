# Milvus-vs-seekdb Differential Campaign Plan

> **Purpose**: Cross-database comparative value before deciding on seekdb S2 semantic extensions
> **Status**: Proposal
> **Estimated Duration**: 1-2 days
> **Goal**: Produce actionable differential insights on high-yield case families

---

## Overview

Instead of immediately proceeding to seekdb S2 (semantic extensions), we run a **differential campaign** that executes the same high-yield test families on both Milvus and seekdb, then compares results.

### Value Proposition

**Question**: Should we invest in seekdb-specific S2 semantic extensions?

**Answer depends on**:
- Are seekdb's patterns significantly different from Milvus?
- Do we find cross-database differential cases that reveal unique seekdb characteristics?
- Is there comparative value in understanding seekdb vs Milvus behavior?

### Success Criteria

1. **Differential Yield**: ≥2 taxonomy-consistent cross-database differential cases
2. **Actionable Insight**: Clear understanding of seekdb's unique characteristics vs Milvus
3. **S2 Decision**: Data-driven recommendation on whether S2 is warranted

---

## High-Yield Case Families

### Family 1: Parameter Boundary / Constraint Handling

**Focus**: How each database handles parameter validation at boundaries

**Test Cases**:
- `top_k` boundary values: -1, 0, 1, 10000, 1000000
- `dimension` boundary values: -1, 0, 1, 128, 99999
- `metric_type` invalid values: "", "INVALID", null, case variations
- Empty vectors, null vectors, malformed vectors

**Expected Differential Value**:
- seekdb (MySQL-based) may have different validation than Milvus (REST-based)
- SQL-level validation may be stricter or more permissive
- Error messages may differ in specificity

**Differential Questions**:
- Which database is more permissive at boundaries?
- Which has better error diagnostics?
- Are there Type-1 differences (accepts illegal input)?

### Family 2: Diagnostic Quality

**Focus**: Error message clarity and actionability

**Test Cases**:
- Reuse Type-2 cases from S1 (tmpl-invalid-002, tmpl-invalid-003)
- Additional invalid inputs with expected good vs poor diagnostics
- Edge cases: missing required fields, type mismatches, malformed JSON

**Expected Differential Value**:
- Direct comparison of error message quality
- Diagnostic mode vs naive mode triage behavior differences
- Characterize each database's "diagnostic personality"

**Differential Questions**:
- Which database provides more actionable error messages?
- Do diagnostic mode and naive mode differentiate differently on each DB?
- Are there patterns in error message structure?

### Family 3: Precondition / State Handling

**Focus**: How each database handles state-dependent operations

**Test Cases**:
- Search on non-existent collection
- Insert before schema creation
- Delete non-existent entities
- Search before index built
- Empty collection operations

**Expected Differential Value**:
- seekdb's automatic index management vs Milvus's explicit index lifecycle
- Different state machine models may produce different failure modes
- Precondition gate effectiveness comparison

**Differential Questions**:
- Which database is more forgiving of state violations?
- How do precondition gate results differ?
- Are there Type-2.PF patterns unique to each DB?

---

## Campaign Design

### Phase 1: Milvus Baseline (Day 1)

**Objective**: Establish Milvus baseline with same case families

**Steps**:
1. Run S1-style campaign on Milvus using `real_milvus_cases.yaml`
2. Use same triage mode (diagnostic) for fair comparison
3. Collect evidence in `runs/milvus_differential_baseline-{timestamp}/`

**Output**:
- Milvus execution results
- Milvus triage classifications
- Milvus bug candidates

### Phase 2: seekdb Campaign (Day 1, parallel if possible)

**Objective**: Run seekdb campaign with identical cases

**Steps**:
1. Reuse seekdb S1 adapter (MySQL-protocol)
2. Run campaign with same templates/cases as Milvus
3. Collect evidence in `runs/seekdb_differential_comparison-{timestamp}/`

**Output**:
- seekdb execution results
- seekdb triage classifications
- seekdb bug candidates

### Phase 3: Differential Analysis (Day 2)

**Objective**: Compare results and extract differential insights

**Analysis Steps**:
1. **Outcome Comparison**: For each case, compare Milvus vs seekdb outcomes
   - Did both succeed? Both fail? Different results?
2. **Triage Comparison**: For failures, compare triage classifications
   - Same bug type on both? Different types?
3. **Diagnostic Comparison**: For Type-2 cases, compare error messages
   - Which has better diagnostics?
4. **Precondition Comparison**: For Type-2.PF cases, compare gate behavior
   - Which database filtered more cases?

**Output**:
- Differential report: `docs/milvus_seekdb_differential_report.md`
- Cross-database differential case catalog
- S2 recommendation

---

## Implementation Plan

### New Files Required

**1. Differential Campaign Runner**
- `scripts/run_differential_campaign.py`
- Runs campaign on both databases (configurable)
- Outputs side-by-side comparison results

**2. Differential Analysis Script**
- `scripts/analyze_differential_results.py`
- Takes two run directories as input
- Generates differential report

**3. Template File (enhanced)**
- `casegen/templates/differential_high_yield.yaml`
- Consolidates high-yield cases from existing templates
- Organized by family (boundaries, diagnostics, preconditions)

### Existing Files to Reuse

- `adapters/seekdb_adapter.py` (seekdb connection)
- `adapters/milvus_adapter.py` (Milvus connection, assumed to exist)
- `scripts/run_seekdb_s1.py` (campaign runner pattern)
- Existing oracles (FilterStrictness, WriteReadConsistency, Monotonicity)
- Existing triage logic

---

## Timeline

| Day | Activity | Deliverable |
|-----|----------|-------------|
| 1 | Create differential templates | `differential_high_yield.yaml` |
| 1 | Run Milvus baseline campaign | `runs/milvus_differential_*/` |
| 1 | Run seekdb comparison campaign | `runs/seekdb_differential_*/` |
| 2 | Implement differential analysis script | `analyze_differential_results.py` |
| 2 | Generate differential report | `docs/milvus_seekdb_differential_report.md` |
| 2 | S2 recommendation | Included in report |

---

## Success Criteria

### Quantitative

- [ ] Both campaigns complete successfully (no crashes)
- [ ] ≥30 test cases executed per database
- [ ] ≥2 cross-database differential cases identified

### Qualitative

- [ ] Clear characterization of seekdb vs Milvus differences
- [ ] Actionable S2 recommendation (proceed / modify / defer)
- [ ] Differential catalog useful for future comparisons

### Decision Output

**After differential analysis, provide recommendation on S2**:

1. **PROCEED with S2**: If seekdb shows unique characteristics that merit semantic extension oracles
   - Example: seekdb hybrid search has bugs not caught by generic oracles
   - Example: seekdb multi-model has unique failure modes

2. **MODIFY S2 scope**: If differential analysis reveals different priorities
   - Example: Focus on diagnostic quality rather than hybrid search
   - Example: Defer S2 pending seekdb improvements

3. **DEFER S2**: If seekdb behaves similarly to Milvus
   - Example: No significant differential findings
   - Example: Generic oracles already catch seekdb issues
   - Recommendation: Use existing framework as-is for seekdb

---

## Risk Mitigation

### Risk 1: Milvus instance not available

**Mitigation**: Use existing Milvus run results if available, or skip Milvus baseline and focus on seekdb-only characterization

### Risk 2: seekdb adapter issues discovered

**Mitigation**: S1 validation already completed; smoke test passed. If new issues arise, add to issue candidates list

### Risk 3: Incompatible case templates

**Mitigation**: Use parameter mapping layer in seekdb adapter; filter out cases that don't map cleanly

---

## Next Steps

1. **Review and approve this plan**
2. **Create differential template file** (`differential_high_yield.yaml`)
3. **Set up Milvus connection** (if not already available)
4. **Run differential campaigns** (Milvus + seekdb)
5. **Generate differential report**
6. **Make S2 decision based on findings**

---

## Appendix: Differential Case Catalog Template

```markdown
| Case ID | Family | Milvus Result | seekdb Result | Differential? | Notes |
|---------|--------|---------------|---------------|----------------|-------|
| diff-001 | boundaries | Success | Failure | YES | seekdb rejects top_k=0, Milvus accepts |
| diff-002 | diagnostics | Type-2 (good) | Type-2 (poor) | YES | seekdb has worse error message |
| diff-003 | preconditions | Type-2.PF | Success | YES | seekdb more forgiving |
```

This catalog will be populated during Phase 3 analysis.
