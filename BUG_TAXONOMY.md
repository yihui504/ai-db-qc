# Bug Taxonomy

## Overview

This document defines the unified four-type defect classification framework used throughout the AI-DB-QC system.

## Core Principles

1. **Four Top-Level Types**: There are exactly FOUR top-level bug types
2. **Mutual Exclusivity**: Each finding belongs to exactly one top-level type
3. **Red-Line Enforcement**: Type-3 and Type-4 require `precondition_pass=true`
4. **Evidence-Based**: Classification must be traceable to execution evidence
5. **LLM-Independent**: Final classification is never delegated to LLM

## The Four Types

### Type-1: Illegal Operation Succeeded

**Definition**: An operation that should have failed (based on contract) but succeeded.

**Formal Condition**:
```
input_validity = illegal
observed_success = true
final_type = Type-1
```

**Examples**:
- Inserting vectors with wrong dimensionality
- Searching with negative top_k
- Creating collection with invalid configuration
- Passing malformed filter expressions

---

### Type-2: Illegal Operation Failed (Poor Diagnostic)

**Definition**: An operation that correctly failed, but the error message lacks diagnostic value.

**Formal Condition**:
```
input_validity = illegal
observed_success = false
error_message_lacks_root_cause = true
final_type = Type-2
```

**Examples**:
- Generic "internal error" without root cause
- "Invalid parameter" without specifying which parameter
- "Operation failed" without explaining why

#### Type-2.PreconditionFailed (Subtype)

A request that is **contract-valid** but **precondition-fail** produces a non-diagnostic error:

```
input_validity = legal
precondition_pass = false
observed_success = false
error_message_lacks_root_cause = true
final_type = Type-2.PreconditionFailed
```

**Important**: This is a **subtype of Type-2**, NOT a fifth top-level bug type.

**Examples**:
- Search on non-existent collection with generic "collection not found" (doesn't explain which collection)
- Search before index load with "operation failed" (doesn't mention index requirement)
- Insert into non-existent collection with "error" (doesn't mention collection doesn't exist)

These are contract-valid (the parameters are correct) but precondition-fail (runtime state doesn't permit execution).

---

### Type-3: Legal Operation Failed

**Definition**: A contract-valid operation, with all preconditions satisfied, that failed, crashed, hung, or timed out.

**Formal Condition**:
```
input_validity = legal
precondition_pass = true
observed_success = false
final_type = Type-3
```

**RED-LINE**: `precondition_pass=true` is MANDATORY. If precondition_pass=false, the finding **MUST NOT** be classified as Type-3.

**Examples**:
- Valid insert fails after collection is loaded
- Valid search returns database error after index is built
- Valid operation causes crash or hang
- Valid operation times out unexpectedly

**Subtypes**:
- Type-3.A: Exception/Error thrown
- Type-3.B: Crash/segfault
- Type-3.C: Hang/infinite wait
- Type-3.D: Timeout

---

### Type-4: Semantic Violation

**Definition**: A contract-valid operation, with all preconditions satisfied, that succeeded but produces results that violate semantic invariants.

**Formal Condition**:
```
input_validity = legal
precondition_pass = true
observed_success = true
oracle_result = failed
final_type = Type-4
```

**RED-LINE**: `precondition_pass=true` is MANDATORY. If precondition_pass=false, the finding **MUST NOT** be classified as Type-4.

**Examples**:
- Top-K=10 returns fewer than K results without explanation
- Top-K monotonicity violated (K=5 returns more results than K=10)
- Filter doesn't actually filter
- Written data not returned on subsequent read
- Similarity scores don't respect metric properties

**Subtypes** (by oracle):
- Type-4.Monotonicity: Top-K monotonicity violation
- Type-4.Consistency: Write-read inconsistency
- Type-4.Strictness: Filter strictness violation

---

## Classification Decision Tree

```
┌─────────────────────────────────────┐
│     Is input contract-valid?        │
└─────────────┬───────────────────────┘
              │
     ┌────────┴────────┐
     │                 │
    NO                YES
     │                 │
     │     ┌───────────────────────────┐
     │     │ Did operation succeed?    │
     │     └───────────┬───────────────┘
     │                 │
     │        ┌────────┴────────┐
     │        │                 │
     │       NO                YES
     │        │                 │
     │        │     ┌───────────────────────┐
     │        │     │ precondition_pass?    │
     │        │     └───────────┬───────────┘
     │        │                 │
     │        │    ┌────────────┴────────────┐
     │        │    │                         │
     │        │   NO                        YES
     │        │    │                         │
     │        │    │           ┌─────────────────────────┐
     │        │    │           │ Did oracle pass?        │
     │        │    │           └──────────┬──────────────┘
     │        │    │                      │
     │        │    │         ┌────────────┴────────────┐
     │        │    │         │                         │
     │        │    │        NO                        YES
     │        │    │         │                         │
     │        │    │         │                    ✅ Valid
     │        │    │         │
     │        │    │    Type-4              Type-3
     │        │    │  (Semantic          (Runtime
     │        │    │   Violation)         Failure)
     │        │    │
     │        │    Type-2.PreconditionFailed
     │        │    (Type-2 subtype)
     │        │
     │   Type-2
     │  (Poor
     │  Diagnostic)
     │
  Type-1
(Illegal
 Succeeded)
```

## The Precondition Red Line

Without the `precondition_pass` gate, we cannot distinguish between:
- **Genuine bugs** (Type-3/4): Valid operations failing under valid conditions
- **Expected failures**: Operations failing because runtime prerequisites aren't met

### Examples of Pseudo-Valid Cases

A case may be **contract-valid** but **precondition-fail**:
- Search on non-existent collection
- Insert before collection is created
- Search before index is loaded
- Filter on unsupported field

These **should not** count as Type-3 or Type-4 because they represent expected failures.

---

## Key Distinction Summary

| Concept | Definition | Evaluated By |
|---------|------------|--------------|
| **Abstract Legality** | Does request satisfy contract constraints? | Contract validator (static) |
| **Runtime Readiness** | Does environment state permit execution? | Precondition gate (dynamic) |
| **precondition_pass** | Were ALL runtime preconditions satisfied? | Boolean flag in ExecutionResult |

The **abstract legality** determines whether a request *could* be valid.
The **runtime readiness** (precondition_pass) determines whether it *should* execute successfully.
