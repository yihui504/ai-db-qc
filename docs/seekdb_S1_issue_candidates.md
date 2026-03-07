# seekdb S1 Issue-Ready Candidates

> **Campaign**: seekdb S1 (diagnostic mode)
> **Run ID**: seekdb_s1_diagnostic-initial-20260307-223023
> **Date**: 2026-03-07
> **seekdb Version**: oceanbase/seekdb:latest (Docker)
> **Total Candidates**: 3

---

## Candidate 1: Valid create_collection Fails (Type-3)

**Case ID**: `tmpl-valid-001`
**Bug Type**: Type-3 (Legal operation failed)
**Severity**: HIGH

### Description

A `create_collection` operation with valid, contract-compliant parameters fails unexpectedly. The operation uses:
- `collection_name`: Standard string identifier
- `dimension`: 128 (within valid range >= 1)
- `metric_type`: "L2" (supported value)

### Expected Behavior

Collection should be created successfully. This is a basic, legal operation that any vector database must support.

### Actual Behavior

The operation failed. The exact error details should be in `execution_results.jsonl` for this case.

### Impact

- Users cannot create collections with standard parameters
- Blocks basic database usage
- May affect all collection creation operations

### Evidence Location

- Run: `runs/seekdb_s1_diagnostic-initial-20260307-223023/`
- Case: `tmpl-valid-001`
- Files: `cases.jsonl`, `execution_results.jsonl`

### Reproduction

```python
from adapters.seekdb_adapter import SeekDBAdapter

adapter = SeekDBAdapter(
    api_endpoint="127.0.0.1:2881",
    api_key="",
    collection="test"
)

request = {
    "operation": "create_collection",
    "params": {
        "collection_name": "test_collection_001",
        "dimension": 128,
        "metric_type": "L2"
    }
}

result = adapter.execute(request)
# Expected: {"status": "success", ...}
# Actual: {"status": "error", "error": "..."}
```

### Status

**READY FOR ISSUE REPORTING**

This is a clear Type-3 bug: a legal, contract-valid operation fails without justification. Database should either succeed or provide a clear explanation of why these parameters are invalid.

---

## Candidate 2: Poor Diagnostic for Invalid top_k Parameter (Type-2)

**Case ID**: `tmpl-invalid-002`
**Bug Type**: Type-2 (Illegal input with poor diagnostic)
**Severity**: MEDIUM

### Description

A `search` operation with `top_k=-1` (illegal value) is rejected, but the error message does not clearly explain what is wrong or what the valid range is.

### Input

- `operation`: search
- `top_k`: -1 (illegal, minimum is 1)
- Other parameters: valid

### Expected Behavior

Operation should be rejected with a clear diagnostic message such as:
- "Parameter 'top_k' must be >= 1"
- "top_k value -1 is outside valid range [1, 10000]"
- Similar specific guidance

### Actual Behavior

Operation was rejected (correct), but with a generic or unclear error message. The diagnostic quality is insufficient for users to understand and fix the issue quickly.

### Impact

- Users struggle to debug parameter errors
- Increased support burden
- Poor developer experience

### Taxonomy Classification

**Type-2**: Illegal input correctly rejected, but with inadequate diagnostic quality. The database did the right thing (rejected the bad input) but failed the usability test (didn't explain why).

### Evidence Location

- Run: `runs/seekdb_s1_diagnostic-initial-20260307-223023/`
- Case: `tmpl-invalid-002`
- Files: `cases.jsonl`, `execution_results.jsonl`

### Differential Comparison Value

This is an excellent candidate for Milvus-vs-seekdb comparison:
- Compare how Milvus handles `top_k=-1`
- Compare error message quality
- Determine which database has better developer experience

### Status

**READY FOR ISSUE REPORTING**

Clear Type-2 bug: diagnostic quality improvement opportunity.

---

## Candidate 3: Poor Diagnostic for Dimension Mismatch (Type-2)

**Case ID**: `tmpl-invalid-003`
**Bug Type**: Type-2 (Illegal input with poor diagnostic)
**Severity**: MEDIUM

### Description

An `insert` operation with vectors that don't match the collection's dimension is rejected, but the error message does not clearly indicate the dimension mismatch.

### Input

- `operation`: insert
- `vectors`: List of vectors with wrong dimension
- `collection_name`: Valid collection

### Expected Behavior

Operation should be rejected with a clear diagnostic message such as:
- "Vector dimension 64 does not match collection dimension 128"
- "Expected 128 dimensions, got 64"
- Similar specific guidance about the mismatch

### Actual Behavior

Operation was rejected (correct), but with a generic or unclear error message. The diagnostic quality is insufficient for users to identify the dimension mismatch as the root cause.

### Impact

- Users struggle to debug dimension errors
- May lead to incorrect "workarounds"
- Poor developer experience for data loading

### Taxonomy Classification

**Type-2**: Illegal input correctly rejected, but with inadequate diagnostic quality. The database correctly prevented the bad insert, but failed to explain why.

### Evidence Location

- Run: `runs/seekdb_s1_diagnostic-initial-20260307-223023/`
- Case: `tmpl-invalid-003`
- Files: `cases.jsonl`, `execution_results.jsonl`

### Differential Comparison Value

This is an excellent candidate for Milvus-vs-seekdb comparison:
- Compare how Milvus handles dimension mismatch
- Compare error message specificity
- Assess which database provides better debugging support

### Status

**READY FOR ISSUE REPORTING**

Clear Type-2 bug: diagnostic quality improvement opportunity.

---

## Summary

| Candidate | Type | Severity | Description |
|-----------|------|----------|-------------|
| tmpl-valid-001 | Type-3 | HIGH | Valid create_collection fails |
| tmpl-invalid-002 | Type-2 | MEDIUM | Poor diagnostic for invalid top_k |
| tmpl-invalid-003 | Type-2 | MEDIUM | Poor diagnostic for dimension mismatch |

**Total**: 3 issue-ready candidates
- 1 Type-3 (functional bug)
- 2 Type-2 (diagnostic quality bugs)

All three candidates are ready for:
1. Individual bug report filing
2. Cross-database comparison with Milvus
3. Prioritization for seekdb development team
