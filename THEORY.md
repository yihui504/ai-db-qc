# Theoretical Foundation

## Abstract

This document outlines the theoretical foundation for the AI-DB-QC system: a contract-driven, adapter-based, evidence-backed approach to quality assurance for AI databases.

## Problem Statement

AI databases present unique quality assurance challenges:

1. **Complex Data Types**: High-dimensional vectors, embeddings
2. **Semantic Query Semantics**: Similarity search, hybrid retrieval
3. **Approximate Algorithms**: ANN search with tunable trade-offs
4. **Stateful Operations**: Collection lifecycle, index building, loading
5. **Diagnostic Challenges**: Error messages often lack root-cause information

## Core Research Hypothesis

A quality assurance system for AI databases should provide:

1. **Structured Test Case Generation**: Systematic exploration of input space
2. **Structured Correctness Judgment**: Oracle-based validation with traceability

## Theoretical Framework

### 1. Dual-Layer Validity Model

We distinguish two orthogonal validity dimensions:

#### Abstract Legality (Contract-Valid)
A request is **abstractly legal** if it satisfies type constraints, parameter ranges, and required fields. This is purely syntactic and can be checked against a contract.

#### Runtime Readiness (Precondition-Pass)
A request is **runtime-ready** if the environment state permits execution (collection exists, index loaded, etc.). This is stateful and can only be evaluated at runtime.

**Key Insight**: A request can be contract-valid but precondition-fail. This distinction is critical for valid bug classification.

### 2. Four-Type Defect Taxonomy

| Type | Name | Condition |
|------|------|-----------|
| Type-1 | Illegal Succeeded | `illegal ∧ success` |
| Type-2 | Poor Diagnostic | `illegal ∧ failed ∧ poor_error` |
| Type-2.PreconditionFailed | Runtime Precondition Fail | `legal ∧ precondition_fail ∧ poor_error` (Type-2 subtype) |
| Type-3 | Runtime Failure | `legal ∧ precondition_pass=true ∧ failed` |
| Type-4 | Semantic Violation | `legal ∧ precondition_pass=true ∧ oracle_failed` |

**The Red Line**: Type-3 and Type-4 **require** `precondition_pass = true`. Without this, we cannot distinguish genuine bugs from expected failures.

### 3. Contract-Driven Architecture

#### Core Contracts (Database-Agnostic)
Abstract semantic rules defining what operations exist, what parameters they accept, and what constraints apply. Core contracts are research artifacts.

#### DB Profiles (Database-Specific)
Concrete mappings defining how core contracts map to specific database APIs, what relaxations exist, and what quirks exist. DB profiles are implementation artifacts.

### 4. Evidence-Centric Execution

Every test execution produces an **EvidenceBundle** containing:
- Run metadata and environment fingerprint
- Case, request, and response snapshots
- Oracle results with metrics
- Gate trace (precondition evaluation)
- Replay information

### 5. Oracle-Based Semantic Validation

For Type-4 detection, we use **semantic oracles**:
- **Monotonicity**: Increasing top-K should expand result sets
- **Consistency**: Write-then-read should return written data
- **Strictness**: Filters should constrain, not expand, results

## Methodological Implications

### LLM Positioning

LLMs are **never** sources of truth for final classification. They may assist with generating candidate test cases but must not decide final bug type, correctness, or confirmation.

### Separation of Concerns

| Component | Responsibility | Must NOT |
|-----------|----------------|----------|
| Adapter | Execute and normalize | Classify or validate |
| Oracle | Check semantic invariants | Report or classify |
| Gate | Evaluate runtime readiness | Classify failures |
| Triage | Classify into Type 1-4 | Execute or validate |

### Minimal Publishable Prototype

The goal is a **research artifact** that demonstrates the dual-layer validity model and validates the four-type taxonomy. Complexity is the enemy.
