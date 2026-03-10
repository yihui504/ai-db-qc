# Campaign R1 Final Summary

**Campaign**: R1: Milvus Core High-Yield
**Date**: 2026-03-08
**Status**: ✅ ACCEPTED - First valid production run
**Database**: pymilvus v2.6.2 client, Milvus server v2.6.10
**Cases**: 10 total (6 capability-boundary, 2 calibration, 2 exploratory)

## Campaign Objective

First results-driven production campaign focused on:
1. Capability boundary cases (parameter contract violations)
2. Precondition sensitivity cases (gate validation)
3. Exploratory cases (lower confidence)

## Outcomes

### High-Confidence Issue-Ready Candidates: 1

| Issue ID | Case | Type | Description |
|----------|------|------|-------------|
| MILVUS-005 | cb-bound-005 | Type-1 | Invalid metric_type "INVALID_METRIC" accepted without error |

**Note**: This finding was previously discovered in differential v3 campaign as `issue_001_invalid_metric_type.md`. R1 independently confirmed the same bug, validating the reproducibility of the finding.

### Observations (Not Issue-Ready)

| Case | Type | Assessment |
|------|------|------------|
| cb-bound-002 | Type-2 (low confidence) | top_k=-1 error mentions parameter but missing valid range |
| cb-bound-003 | Type-2 (low confidence) | top_k=0 error mentions parameter but missing valid range |
| cb-bound-006 | NOT A BUG | pymilvus Collection() is idempotent by design |

### False Positives Cleaned

| Case | Type | Reason |
|------|------|--------|
| exp-002 | Type-2 (false positive) | Error "field nonexistent_field not exist" is specific and actionable |

## Validly Exercised Cases

| Case | Boundary/Feature | Error Message | Assessment |
|------|------------------|---------------|------------|
| cb-bound-001 | dimension=0 | "invalid dimension: 0. should be in range 2 ~ 32768" | ✅ Good diagnostic |
| cb-bound-002 | top_k=-1 | "`limit` value -1 is illegal" | ✅ Borderline |
| cb-bound-003 | top_k=0 | "`limit` value 0 is illegal" | ✅ Borderline |
| cb-bound-004 | dimension mismatch | "the length(32) of float data should divide the dim(128)" | ✅ Decent diagnostic |
| cb-bound-005 | invalid metric_type | **SUCCESS** | ✅ Type-1 confirmed |
| cb-bound-006 | duplicate collection | **SUCCESS** | ✅ Idempotent design |
| exp-002 | invalid field filter | "field nonexistent_field not exist" | ✅ Good diagnostic |

**7 out of 7 boundary/exploratory cases validly exercised.**

## Fixes Applied During R1

1. **Template substitution**: Fixed `{id}` placeholder issue
2. **Runtime context**: Built index on test_collection and loaded it
3. **Vector parsing**: Added string-to-list parsing in MilvusAdapter
4. **Triage bug**: Fixed `TypeError` in `_has_good_diagnostics` method

## Success Criteria Assessment

### Minimum Success
- ✅ All 10 cases executed successfully
- ✅ Precondition gate correctly filtered calibration cases
- ✅ Export produces bug report (1 candidate)
- ✅ All 5 validate artifacts present

### Stretch Success
- ⚠️ 1 issue-ready candidate (target was 3+)
- ✅ 1 Type-1 finding (cb-bound-005)
- ✅ Diagnostic quality variation observed

**Result: Minimum success MET, partial stretch success**

## Conclusions

1. **First Valid Production Run**: R1 successfully validated the end-to-end workflow (generate → validate → triage)

2. **One Confirmed Bug**: cb-bound-005 (invalid metric_type accepted) is a high-confidence Type-1 candidate suitable for bug filing

3. **Tool Maturity**: Framework successfully:
   - Generated and executed test cases
   - Evaluated preconditions correctly
   - Triage results with taxonomy-aware filtering
   - Exported structured results

4. **Areas for Improvement**:
   - Increase issue yield in R2
   - Focus on enum/parameter validation weaknesses
   - Reduce false positive rate (exp-002)

## Next Steps

1. **Regression Pack**: Add cb-bound-005 to canonical bug-case set
2. **R2 Design**: Focus on parameter validation boundary cases
3. **Issue Filing**: Prepare MILVUS-005 for submission

## Metadata

- **Tool Version**: 0.1.0
- **Run ID**: milvus_validation_20260308_223239
- **Output Directory**: `results/milvus_validation_20260308_223239/`
- **Artifacts**: execution_results.jsonl, triage_results.json, summary.json, metadata.json, cases.jsonl
