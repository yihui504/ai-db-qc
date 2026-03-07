# Representative Case Studies

This document contains representative examples for each bug type 
identified during Phase 5.3 evaluation.

## Case Study 1: type-1

**Case ID:** `test-003`

**Run ID:** `phase5-baseline_mock-20260307-183121`

**Operation:** `create_collection`

**Expected Validity:** `illegal`

**Precondition Pass:** `True`

**Observed Outcome:** `success`


**Parameters:**

```json
{
  "collection_name": "test_collection",
  "dimension": -1,
  "metric_type": "L2"
}
```


**Interpretation:** Illegal input accepted: Illegal operation succeeded


---

## Case Study 2: type-2

**Case ID:** `test-003`

**Run ID:** `phase5-baseline_real-20260307-183035`

**Operation:** `create_collection`

**Expected Validity:** `illegal`

**Precondition Pass:** `True`

**Observed Outcome:** `failure`


**Parameters:**

```json
{
  "collection_name": "test_collection",
  "dimension": -1,
  "metric_type": "L2"
}
```


**Error Message:**
```
<PrimaryKeyException: (code=1, message=Schema must have a primary key field.)>
```


**Interpretation:** Illegal input rejected, lacks diagnostic: Illegal operation with poor diagnostic


---

## Case Study 3: type-2.precondition_failed

**Case ID:** `test-002`

**Run ID:** `phase5-baseline_real-20260307-183035`

**Operation:** `insert`

**Expected Validity:** `legal`

**Precondition Pass:** `False`

**Observed Outcome:** `failure`


**Parameters:**

```json
{
  "collection_name": "test_collection",
  "vectors": [
    [
      0.1,
      0.2,
      0.3
    ]
  ]
}
```


**Error Message:**
```
<SchemaNotReadyException: (code=1, message=Collection 'test_collection' not exist, or you can pass in schema to create one.)>
```


**Interpretation:** Expected failure (precondition not met): Contract-valid but precondition-fail


---

## Case Study 4: type-3

**Case ID:** `test-001`

**Run ID:** `phase5-baseline_real-20260307-183035`

**Operation:** `create_collection`

**Expected Validity:** `legal`

**Precondition Pass:** `True`

**Observed Outcome:** `failure`


**Parameters:**

```json
{
  "collection_name": "test_collection",
  "dimension": 128,
  "metric_type": "L2"
}
```


**Error Message:**
```
<PrimaryKeyException: (code=1, message=Schema must have a primary key field.)>
```


**Interpretation:** Legal input failed: Legal operation failed (precondition satisfied)


---

## Case Study 5: type-4

**Case ID:** `synthetic-type4-001`

**Run ID:** `synthetic`

**Operation:** `search`

**Expected Validity:** `legal`

**Precondition Pass:** `True`

**Observed Outcome:** `success`

**Note:** SYNTHETIC EXAMPLE - Type-4 requires oracle-visible violations not present in current test set


**Parameters:**

```json
{
  "collection_name": "test_collection",
  "query_vector": "[0.1, 0.2, 0.3]",
  "top_k": 10
}
```


**Interpretation:** Semantic oracle violation: Top-K=10 returned only 5 results without explanation


---

## Case Study 6: non-bug

**Case ID:** `test-001`

**Run ID:** `phase5-baseline_mock-20260307-183121`

**Operation:** `create_collection`

**Expected Validity:** `legal`

**Precondition Pass:** `True`

**Observed Outcome:** `success`


**Parameters:**

```json
{
  "collection_name": "test_collection",
  "dimension": 128,
  "metric_type": "L2"
}
```


**Interpretation:** Expected behavior - operation succeeded as designed


---
