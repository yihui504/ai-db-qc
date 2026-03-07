# Representative Case Studies

This document contains representative examples for each bug type 
identified during testing.

## Case Study 1: type-1

**Run ID:** `phase5-baseline_mock-20260307-183121`  

**Case ID:** `test-003`  

**Operation:** `create_collection`  

**Expected Validity:** `illegal`  

**Precondition Pass:** `True`  

**Observed Outcome:** `success`  

**Bug Type:** `type-1`  

**Evidence Files:** `phase5-baseline_mock-20260307-183121/`  



**Interpretation:** Illegal input accepted: Illegal operation succeeded


---

## Case Study 2: type-2

**Run ID:** `phase5-baseline_real-20260307-183035`  

**Case ID:** `test-003`  

**Operation:** `create_collection`  

**Expected Validity:** `illegal`  

**Precondition Pass:** `True`  

**Observed Outcome:** `failure`  

**Bug Type:** `type-2`  

**Evidence Files:** `phase5-baseline_real-20260307-183035/`  



**Interpretation:** Illegal input rejected (poor diagnostic): Illegal operation with poor diagnostic


---

## Case Study 3: type-2.precondition_failed

**Run ID:** `phase5-baseline_mock-20260307-183121`  

**Case ID:** `test-002`  

**Operation:** `insert`  

**Expected Validity:** `legal`  

**Precondition Pass:** `False`  

**Observed Outcome:** `success`  

**Bug Type:** `type-2.precondition_failed`  

**Evidence Files:** `phase5-baseline_mock-20260307-183121/`  



**Interpretation:** Precondition violation: Contract-valid but precondition-fail


---

## Case Study 4: type-3

**Run ID:** `phase5-baseline_real-20260307-183035`  

**Case ID:** `test-001`  

**Operation:** `create_collection`  

**Expected Validity:** `legal`  

**Precondition Pass:** `True`  

**Observed Outcome:** `failure`  

**Bug Type:** `type-3`  

**Evidence Files:** `phase5-baseline_real-20260307-183035/`  



**Interpretation:** Legal input failed (runtime error): Legal operation failed (precondition satisfied)


---
