# Semantic Testing Framework for Vector Databases

**Document Version**: 1.0
**Date**: 2026-03-09
**Scope**: Complete Framework Overview (R1-R4)

---

## Executive Summary

This document describes the semantic testing framework developed through four testing campaigns (R1-R4). The framework provides a comprehensive approach to validating vector database behavior across multiple dimensions: parameter boundaries, API usability, state transitions, and cross-database compatibility.

**Framework Goal**: Establish a rigorous methodology for testing vector database semantics, distinguishing between bugs, allowed differences, and implementation variations.

---

## Framework Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SEMANTIC TESTING FRAMEWORK                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌────────────────┐    ┌────────────────┐    ┌────────────────┐  │
│  │      R1        │    │      R2        │    │      R3        │  │
│  │  Parameter     │    │  API           │    │  Sequence &    │  │
│  │  Boundary      │ →  │  Validation    │ →  │  State-        │  │
│  │  Testing       │    │  Usability     │    │  Transition     │  │
│  └────────────────┘    └────────────────┘    └────────────────┘  │
│                                                                     │
│                              ↓                                      │
│                                                                     │
│  ┌────────────────┐    ┌────────────────┐    ┌────────────────┐  │
│  │      R4        │    │   Framework    │    │   Output       │  │
│  │  Differential  │ →  │   Components   │ →  │   Reports      │  │
│  │  Semantic      │    │   (Oracle,     │    │   (Matrix,     │  │
│  │  Testing       │    │    Adapter)    │    │    Findings)   │  │
│  └────────────────┘    └────────────────┘    └────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Four Testing Dimensions

### R1: Parameter Boundary Testing

**Objective**: Validate parameter constraints and boundary conditions.

**Focus Areas**:
- Dimension limits (min, max, invalid values)
- Top-K boundaries (0, 1, large values)
- Metric type validation
- Vector data type validation

**Campaign**: R1 - 10 test cases on real Milvus

**Key Findings**:
- Dimension validation: rejects invalid dimensions correctly
- Top-K handling: accepts zero and positive values
- Metric types: supports L2, IP, COSINE
- Data types: validates float32 vectors

**Testing Technique**:
```python
# Boundary testing example
def test_dimension_boundaries():
    # Test minimum dimension
    test_create_collection(dimension=0)      # Expected: error
    test_create_collection(dimension=1)      # Expected: success
    test_create_collection(dimension=32768)  # Expected: success
    test_create_collection(dimension=32769)  # Expected: error
```

**Value**: Establishes baseline parameter validation behavior.

---

### R2: API Validation / Usability

**Objective**: Validate API contract and usability characteristics.

**Focus Areas**:
- Parameter acceptance (silently ignored vs. validated)
- Error message quality
- API consistency
- Documentation alignment

**Campaign**: R2 - 11 test cases on real Milvus

**Key Findings**:
- **API Usability Issue**: `metric_type` parameter silently ignored in `Collection()`
  - Actual behavior: Must be set during index creation
  - Severity: LOW-MEDIUM (documentation/UX issue)
- Parameter validation varies by operation
- Error messages are generally clear

**Testing Technique**:
```python
# API validation example
def test_parameter_validation():
    # Test undocumented parameter
    result = create_collection(name="test", metric_type="L2", undocumented_param="value")
    # Check: Is undocumented_param validated or silently ignored?
    assert result.status == "error" or result.warning == "parameter_ignored"
```

**Value**: Identifies usability issues and documentation gaps.

---

### R3: Sequence and State-Transition Testing

**Objective**: Validate behavior across operation sequences and state changes.

**Focus Areas**:
- State transitions (created → loaded → searched)
- Operation ordering constraints
- Idempotency of operations
- State-dependent behavior

**Campaign**: R3 - 11 test cases on real Milvus

**Key Findings**:
- All sequences executed correctly
- Idempotency validated (delete operations)
- State transitions well-defined
- No contract violations found

**Testing Technique**:
```python
# State-transition testing example
def test_state_transitions():
    # Define state machine
    states = ["created", "indexed", "loaded", "searched"]
    transitions = [
        ("created", "indexed"),     # create → build_index
        ("indexed", "loaded"),      # build_index → load
        ("loaded", "searched"),     # load → search
    ]

    # Test each transition
    for from_state, to_state in transitions:
        result = execute_transition(from_state, to_state)
        assert result.valid_state == to_state
```

**Value**: Validates state management and operation ordering requirements.

---

### R4: Cross-Database Differential Semantic Testing

**Objective**: Compare semantic behavior across different vector databases.

**Focus Areas**:
- Semantic property equivalence
- Contract compliance
- Architectural differences
- Portability considerations

**Campaign**: R4 - 8 semantic properties on Milvus + Qdrant

**Key Findings**:
- **Zero contract violations** across PRIMARY properties
- **4 allowed differences** identified (index, load, empty collection, creation)
- Strong semantic alignment between databases
- Clear portability path documented

**Testing Technique**:
```python
# Differential testing example
def test_semantic_property(property_spec):
    # Execute on both databases
    milvus_result = milvus_adapter.execute(property_spec.sequence)
    qdrant_result = qdrant_adapter.execute(property_spec.sequence)

    # Compare at test step
    comparison = compare_results(
        milvus_result[property_spec.test_step],
        qdrant_result[property_spec.test_step]
    )

    # Classify using oracle
    classification = oracle.classify(
        comparison,
        property_spec.oracle_rule
    )

    return classification
```

**Value**: Establishes semantic compatibility and portability insights.

---

## Framework Components

### 1. Semantic Properties

**Definition**: Testable behavioral contracts that define expected database behavior.

**Property Categories**:
- **PRIMARY**: Core semantic properties with clear contracts (differences indicate bugs)
- **ALLOWED-SENSITIVE**: Properties where architectural differences are expected
- **EXPLORATORY**: Edge cases without clear standard specifications

**Example Properties**:
- Post-Drop Rejection (PRIMARY)
- Deleted Entity Visibility (PRIMARY)
- Delete Idempotency (PRIMARY)
- Index-Independent Search (ALLOWED-SENSITIVE)

**Implementation**:
```python
SEMANTIC_PROPERTIES = {
    "r4_001": {
        "name": "Post-Drop Rejection",
        "category": "PRIMARY",
        "oracle_rule": "Rule 1",
        "test_sequence": [
            {"operation": "create_collection", ...},
            {"operation": "insert", ...},
            {"operation": "search", ...},
            {"operation": "drop_collection", ...},
            {"operation": "search", ...},  # TEST: must fail
        ],
        "test_step": 5,
    }
}
```

---

### 2. Differential Oracle

**Definition**: Classification framework that distinguishes bugs from allowed differences.

**Classification Categories**:
- **BUG (Contract Violation)**: Violates universally accepted semantic contract
- **ALLOWED DIFFERENCE**: Legitimate architectural or design variation
- **OBSERVATION**: Edge case with no clear standard

**Oracle Rules**:
- **Rule 1**: Search After Drop (must fail)
- **Rule 2**: Deleted Entity Visibility (must not appear)
- **Rule 3**: Search Without Index (undefined/allowed)
- **Rule 4**: Delete Idempotency (must be consistent)
- **Rule 5**: Empty Collection (undefined/observation)
- **Rule 6**: Creation Idempotency (undefined/allowed)
- **Rule 7**: Load Requirement (undefined/allowed)

**Decision Tree**:
```
Is there a clear semantic contract?
├─ NO → OBSERVATION
└─ YES → Does behavior violate contract?
    ├─ YES → BUG
    └─ NO → Is it an implementation difference?
        ├─ YES → ALLOWED DIFFERENCE
        └─ NO → Check specification
```

**Implementation**:
```python
class DifferentialOracle:
    def classify(self, comparison, oracle_rule):
        # Step 1: Check if contract exists
        if not self.has_contract(oracle_rule):
            return OBSERVATION

        # Step 2: Check if contract violated
        if self.is_contract_violation(comparison, oracle_rule):
            return BUG

        # Step 3: Check if implementation difference
        if self.is_implementation_difference(comparison):
            return ALLOWED_DIFFERENCE

        # Step 4: Consistent behavior
        return PASS
```

---

### 3. Adapter Abstraction

**Definition**: Normalized interface to different vector databases for differential testing.

**Adapter Interface**:
```python
class AdapterBase:
    def execute(self, request: Dict) -> Dict:
        """Execute operation and return normalized response."""
        pass

    # Core operations
    def create_collection(params): ...
    def insert(params): ...
    def search(params): ...
    def delete(params): ...
    def drop_collection(params): ...

    # Optional operations (database-specific)
    def build_index(params): ...  # No-op for Qdrant
    def load(params): ...         # No-op for Qdrant
```

**Adapters Implemented**:
- **MilvusAdapter**: Wrapper around pymilvus client
- **QdrantAdapter**: Wrapper around qdrant-client
- **MockAdapter**: For testing without real databases

**Response Normalization**:
```python
# All adapters return consistent format:
{
    "status": "success" | "error",
    "data": {...},        # Operation-specific data
    "error": "message",    # Error message if failed
    "error_type": "type"   # Exception type if failed
}
```

**Value**: Enables differential testing by normalizing different APIs.

---

### 4. Classification Pipeline

**Definition**: Automated workflow for executing differential tests and classifying results.

**Pipeline Stages**:

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Test       │ →  │   Compare    │ →  │  Classify    │
│  Execution   │    │   Results    │    │   Using      │
│              │    │              │    │   Oracle     │
└──────────────┘    └──────────────┘    └──────────────┘
      ↓                                       ↓
┌──────────────┐                      ┌──────────────┐
│   Store      │                      │    Report    │
│  Raw Results │                      │   Final      │
└──────────────┘                      │  Results     │
                                       └──────────────┘
```

**Implementation**:
```python
def run_differential_campaign(properties, adapters):
    results = []

    for property_spec in properties:
        # Execute on both databases
        for db_name, adapter in adapters.items():
            raw_results[db_name] = execute_sequence(
                adapter, property_spec.sequence
            )

        # Extract test step
        test_step = property_spec.test_step
        comparison = compare_step(
            raw_results["milvus"][test_step],
            raw_results["qdrant"][test_step]
        )

        # Classify using oracle
        classification = oracle.classify(
            comparison, property_spec.oracle_rule
        )

        # Store results
        results.append({
            "property": property_spec.name,
            "raw_results": raw_results,
            "comparison": comparison,
            "classification": classification
        })

    return results
```

---

## Framework Outputs

### 1. Semantic Behavior Matrix

**File**: `docs/VECTOR_DB_SEMANTIC_MATRIX.md`

**Content**:
- Comparison table of Milvus vs Qdrant behavior
- Classification for each property
- Portability guidance
- Architectural difference categories

**Purpose**: Quick reference for behavioral differences and portability.

### 2. Project Findings Summary

**File**: `docs/PROJECT_FINDINGS_SUMMARY.md`

**Content**:
- Total campaigns and test cases
- Confirmed issues
- Semantic compatibility results
- Allowed implementation differences

**Purpose**: Executive summary of all testing results.

### 3. Detailed Campaign Reports

**Files**:
- `docs/R1_REPORT.md`
- `docs/R2_REPORT.md`
- `docs/R3_REPORT.md`
- `docs/R4_FULL_REPORT.md`

**Content**:
- Per-campaign detailed results
- Test case descriptions
- Findings and classifications

**Purpose**: Comprehensive record of each campaign.

---

## Framework Principles

### 1. Semantic Contract First

**Principle**: Test behavior against semantic contracts, not just API specifications.

**Application**:
- Define clear semantic contracts (e.g., "deleted entities must not appear")
- Test contract compliance across databases
- Classify violations as bugs

### 2. Architectural Neutrality

**Principle**: Allow legitimate architectural differences without classifying as bugs.

**Application**:
- Distinguish between contract violations and implementation differences
- Classify state management approaches as allowed differences
- Document trade-offs without judgment

### 3. Reproducibility

**Principle**: All tests must be reproducible with documented environment.

**Application**:
- Capture environment snapshots (versions, images)
- Use unique collection names for test isolation
- Store raw results for re-analysis

### 4. Incremental Validation

**Principle**: Build understanding incrementally across testing dimensions.

**Application**:
- R1: Establish parameter baselines
- R2: Validate API contracts
- R3: Understand state transitions
- R4: Compare across databases

---

## Usage Guide

### For Database Evaluators

**Step 1**: Run R1-R3 on single database to establish baseline behavior
**Step 2**: Run R4 on multiple databases to compare semantic compatibility
**Step 3**: Consult Semantic Matrix for behavioral differences
**Step 4**: Use Findings Summary for overall assessment

### For Application Developers

**Step 1**: Consult Semantic Matrix for portability guidance
**Step 2**: Review allowed differences before porting
**Step 3**: Test critical semantic properties on target database
**Step 4**: Use adapter abstraction for multi-database support

### For Framework Developers

**Step 1**: Extend adapter interface for new databases
**Step 2**: Add semantic properties for new behaviors
**Step 3**: Extend oracle rules for new contracts
**Step 4**: Update classification pipeline as needed

---

## Framework Extensions

### Adding New Databases

```python
# Step 1: Implement adapter
class NewDatabaseAdapter(AdapterBase):
    def create_collection(self, params): ...
    def insert(self, params): ...
    # ... implement all operations

# Step 2: Add to differential testing
adapters = {
    "milvus": MilvusAdapter(config),
    "qdrant": QdrantAdapter(config),
    "new_db": NewDatabaseAdapter(config),
}

# Step 3: Run R4 campaign
results = run_differential_campaign(properties, adapters)
```

### Adding New Semantic Properties

```python
# Define new property
NEW_PROPERTY = {
    "name": "Concurrent Insert Safety",
    "category": "PRIMARY",
    "oracle_rule": "Rule 8",
    "test_sequence": [
        # Define test steps
    ],
    "test_step": N,
}

# Add to campaign
properties.append(NEW_PROPERTY)
```

---

## Metadata

- **Document**: Semantic Testing Framework
- **Version**: 1.0
- **Date**: 2026-03-09
- **Campaigns**: R1, R2, R3, R4
- **Total Test Cases**: 58
- **Databases Tested**: Milvus, Qdrant
- **Framework Components**: Semantic Properties, Differential Oracle, Adapter Abstraction, Classification Pipeline

---

**END OF SEMANTIC TESTING FRAMEWORK**

This framework provides a comprehensive methodology for vector database semantic testing. For detailed results, see:
- `docs/VECTOR_DB_SEMANTIC_MATRIX.md`
- `docs/PROJECT_FINDINGS_SUMMARY.md`
- Campaign reports: `docs/R*_REPORT.md`
