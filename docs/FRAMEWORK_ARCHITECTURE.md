# AI-DB-QC Framework Architecture

**Project**: AI Database Quality Assurance Framework
**Document Version**: 1.0
**Date**: 2026-03-10

---

## Executive Summary

This document describes the technical architecture of the AI-DB-QC framework, a contract-driven testing system for AI databases. The architecture is organized around **three core layers**: contract definition, test generation, and execution with oracle evaluation.

**Key Design Principle**: Separation of concerns - contracts define expected behavior, generators create tests, adapters execute operations, and oracles classify results.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          AI-DB-QC Framework Architecture                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌─────────────┐      ┌──────────────┐      ┌─────────────┐      ┌─────────┐│
│  │             │      │              │      │             │      │         ││
│  │   Contract  │─────▶│    Test      │─────▶│  Execution  │─────▶│ Oracle  ││
│  │   Registry  │      │   Generator  │      │   Pipeline  │      │  Engine ││
│  │             │      │              │      │             │      │         ││
│  └─────────────┘      └──────────────┘      └──────┬──────┘      └────┬────┘│
│         │                     │                     │                │      │
│         │                     │                     ▼                ▼      │
│         ▼                     ▼              ┌─────────────┐  ┌──────────┐│
│  ┌─────────────┐      ┌──────────────┐      │             │  │          ││
│  │   Contract  │      │ Generated    │      │   Adapter   │  │Classification│
│  │    Files    │      │   Test Cases │      │    Layer    │  │  Result  ││
│  │   (JSON)    │      │   (JSON)     │      │             │  │          ││
│  └─────────────┘      └──────────────┘      └──────┬──────┘  └──────────┘│
│                                                      │                       │
│                                                      ▼                       │
│                                               ┌─────────────┐               │
│                                               │   Target    │               │
│                                               │  Database   │               │
│                                               │  (Milvus)   │               │
│                                               └─────────────┘               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Architecture

### 1. Contract Registry

**Purpose**: Central repository for contract definitions

**Location**: `contracts/core/loader.py`

**Key Classes**:
```python
class ContractRegistry:
    """Registry for contract definitions."""

    def load_all(self) -> int:
        """Load all contract JSON files."""

    def get_contract(self, contract_id: str) -> Dict:
        """Get contract by ID."""

    def get_contracts_by_family(self, family: str) -> List[Dict]:
        """Get all contracts in a family."""

    def get_statistics(self) -> Dict:
        """Get registry statistics."""
```

**Data Flow**:
```
JSON Files (contracts/{family}/*.json)
        ↓
ContractRegistry.load_all()
        ↓
In-Memory Contract Index
        ↓
Lookup by ID, family, or type
```

**Supported Contract Locations**:
- `contracts/ann/*.json` - ANN contracts
- `contracts/index/*.json` - Index contracts
- `contracts/hybrid/*.json` - Hybrid query contracts
- `contracts/schema/*.json` - Schema/metadata contracts

---

### 2. Contract Test Generator

**Purpose**: Generate executable test cases from contract definitions

**Location**: `core/contract_test_generator.py`

**Key Classes**:
```python
class ContractTestGenerator:
    """Generate test cases from contracts."""

    def generate_all(self) -> List[TestCase]:
        """Generate tests for all contracts."""

    def generate_by_family(self, family: str) -> List[TestCase]:
        """Generate tests for specific contract family."""

    def generate_by_contract(self, contract_id: str) -> List[TestCase]:
        """Generate tests for specific contract."""

    def save_tests(self, tests: List[TestCase], name: str) -> str:
        """Save tests to JSON file."""
```

**Generation Strategies**:

| Strategy | Description | Use Case |
|----------|-------------|----------|
| **Legal** | Valid inputs within constraints | Normal operation testing |
| **Illegal** | Invalid inputs (should fail) | Parameter validation |
| **Boundary** | Edge cases (min, max, empty) | Boundary condition testing |
| **Sequence** | Multi-step operations | State transition testing |

**Data Flow**:
```
Contract Definition
        ↓
Extract test_generation strategy
        ↓
Expand parameter ranges
        ↓
Generate test cases
        ↓
Attach oracle definitions
        ↓
Output: List[TestCase]
```

**Output Format** (TestCase):
```python
{
    "test_id": "ann-001_boundary_001",
    "contract_id": "ANN-001",
    "name": "Top-K Cardinality - Boundary: Zero top-K",
    "strategy": "boundary",
    "setup": [...],      # Pre-execution steps
    "steps": [...],      # Execution steps
    "cleanup": [...],    # Post-execution cleanup
    "oracle": {...},     # Oracle definition
    "priority": "high",
    "estimated_complexity": "low"
}
```

---

### 3. Oracle Engine

**Purpose**: Evaluate execution results against contract oracles

**Location**: `core/oracle_engine.py`

**Key Classes**:
```python
class OracleEngine:
    """Evaluate results against contract oracles."""

    def evaluate(self, contract_id: str,
                 execution_result: Dict,
                 contract_definition: Dict) -> OracleResult:
        """Evaluate execution result."""

    def _oracle_top_k_cardinality(self, result, contract) -> OracleResult:
        """Oracle: Top-K cardinality must not be exceeded."""

    def _oracle_semantic_neutrality(self, result, contract) -> OracleResult:
        """Oracle: Index must not change semantic results."""

    # ... other oracle methods
```

**Classification Categories**:

| Classification | Meaning | Use |
|----------------|---------|-----|
| **PASS** | Contract satisfied | Correct behavior |
| **VIOLATION** | Contract violated | Bug discovered |
| **ALLOWED_DIFFERENCE** | Architectural variance | Not a bug |
| **OBSERVATION** | Undefined behavior | Needs investigation |

**Data Flow**:
```
Execution Result
        ↓
Extract relevant fields
        ↓
Apply oracle logic
        ↓
Compute classification
        ↓
Generate reasoning and evidence
        ↓
Output: OracleResult
```

**Oracle Result Format**:
```python
{
    "contract_id": "ANN-001",
    "classification": "PASS",  # or VIOLATION, ALLOWED_DIFFERENCE, OBSERVATION
    "passed": True,
    "reasoning": "Result count: 5, top_k: 10",
    "evidence": {
        "result_count": 5,
        "top_k": 10
    },
    "confidence": "high"
}
```

---

### 4. Adapter Layer

**Purpose**: Abstract database-specific operations behind unified interface

**Location**: `adapters/`

**Base Interface**:
```python
class AdapterBase(ABC):
    """Base interface for database adapters."""

    @abstractmethod
    def execute(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Execute operation."""

    @abstractmethod
    def health_check(self) -> bool:
        """Check database connectivity."""

    @abstractmethod
    def get_runtime_snapshot(self) -> Dict[str, Any]:
        """Get current runtime state."""
```

**Supported Operations**:

| Operation | Purpose | Parameters |
|-----------|---------|------------|
| `create_collection` | Create new collection | collection_name, dimension, metric_type |
| `insert` | Insert vectors | collection_name, vectors, scalar_data |
| `build_index` | Create index | collection_name, index_type, metric_type |
| `load` | Load collection into memory | collection_name |
| `search` | Vector search | collection_name, vector, top_k |
| `filtered_search` | Hybrid query | collection_name, vector, filter, top_k |
| `drop_collection` | Delete collection | collection_name |
| `delete` | Delete entities | collection_name, ids |

**Milvus Adapter** (`adapters/milvus_adapter.py`):
```python
class MilvusAdapter(AdapterBase):
    """Milvus database adapter."""

    def __init__(self, connection_config: Dict):
        """Initialize with host, port, alias."""

    def execute(self, request: Dict) -> Dict:
        """Execute operation (dispatches to _operation methods)."""

    def _create_collection(self, params: Dict) -> Dict:
        """Create collection with schema."""

    def _insert(self, params: Dict) -> Dict:
        """Insert vectors with scalar fields."""

    def _build_index(self, params: Dict) -> Dict:
        """Build index (HNSW, IVF_FLAT, FLAT)."""

    def _search(self, params: Dict) -> Dict:
        """Vector search."""

    def _filtered_search(self, params: Dict) -> Dict:
        """Hybrid vector + filter search."""
```

**Mock Adapter** (`adapters/mock.py`):
- In-memory implementation for testing
- Simulates all operations without database
- Used for framework validation and CI/CD

---

### 5. Execution Pipeline

**Purpose**: Orchestrate test execution, result collection, and cleanup

**Location**: `pipeline/`

**Key Components**:

#### 5.1 Test Executor

```python
def execute_test_sequence(test: TestCase, adapter: AdapterBase) -> Dict:
    """Execute a test sequence end-to-end."""

    # 1. Setup phase
    for step in test.setup:
        result = adapter.execute(step)

    # 2. Execution phase
    execution_results = []
    for step in test.steps:
        result = adapter.execute(step)
        execution_results.append(result)

    # 3. Cleanup phase
    for step in test.cleanup:
        adapter.execute(step)

    return {
        "test_id": test.test_id,
        "results": execution_results,
        "status": "complete"
    }
```

#### 5.2 Precondition Gate

```python
class PreconditionEvaluator:
    """Evaluate test preconditions against runtime state."""

    def evaluate(self, test: TestCase,
                 runtime_snapshot: Dict) -> PreconditionResult:
        """Check if preconditions are satisfied."""

    def check_collection_exists(self, collection_name: str) -> bool:
        """Check if collection exists."""

    def check_index_exists(self, collection_name: str) -> bool:
        """Check if index exists."""

    def check_data_count(self, collection_name: str,
                         min_count: int) -> bool:
        """Check if collection has minimum entities."""
```

#### 5.3 Result Processor

```python
def process_execution_result(
    execution_result: Dict,
    test: TestCase,
    oracle_engine: OracleEngine
) -> ProcessedResult:
    """Process raw execution result with oracle evaluation."""

    # Extract relevant data from execution result
    relevant_data = extract_relevant_fields(execution_result, test.oracle)

    # Evaluate against oracle
    oracle_result = oracle_engine.evaluate(
        test.contract_id,
        relevant_data,
        test.contract_definition
    )

    return ProcessedResult(
        test_id=test.test_id,
        execution_result=execution_result,
        oracle_result=oracle_result,
        classification=oracle_result.classification
    )
```

---

## Data Flow: End-to-End

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Test Execution Flow                           │
└─────────────────────────────────────────────────────────────────────────┘

1. CONTRACT DEFINITION
   contracts/ann/ann-001-top-k-cardinality.json
   │
   ▼
2. CONTRACT REGISTRY
   ContractRegistry.load_all()
   │
   ▼
3. TEST GENERATION
   ContractTestGenerator.generate_by_contract("ANN-001")
   │
   ▼
4. TEST CASE (JSON)
   {
     "test_id": "ann-001_boundary_001",
     "contract_id": "ANN-001",
     "setup": [{"operation": "create_collection", ...}],
     "steps": [{"operation": "insert", ...},
               {"operation": "search", "top_k": 0}],
     "cleanup": [{"operation": "drop_collection"}],
     "oracle": {"check": "count(results) <= top_k"}
   }
   │
   ▼
5. EXECUTION (Adapter)
   MilvusAdapter.execute({"operation": "search", "top_k": 0})
   │
   ▼
6. EXECUTION RESULT
   {
     "status": "success",
     "operation": "search",
     "data": []  # Empty results (correct for top_k=0)
   }
   │
   ▼
7. ORACLE EVALUATION
   OracleEngine.evaluate("ANN-001", execution_result)
   │
   ▼
8. ORACLE RESULT
   {
     "contract_id": "ANN-001",
     "classification": "PASS",
     "reasoning": "Result count: 0, top_k: 0",
     "evidence": {"result_count": 0, "top_k": 0}
   }
```

---

## File Organization

```
ai-db-qc/
│
├── contracts/                    # Contract definitions
│   ├── core/                      # Core contract infrastructure
│   │   ├── loader.py              # Contract registry
│   │   ├── schema.py              # Contract schema validation
│   │   └── validator.py           # Contract validation logic
│   ├── db_profiles/               # Database-specific profiles
│   │   ├── milvus_profile.yaml    # Milvus configuration
│   │   └── seekdb_profile.yaml    # SeekDB configuration
│   ├── ann/                       # ANN contracts (5 files)
│   ├── index/                     # Index contracts (4 files)
│   ├── hybrid/                    # Hybrid contracts (3 files)
│   └── schema/                    # Schema contracts (4 files)
│
├── core/                          # Core framework components
│   ├── contract_registry.py       # Contract registry implementation
│   ├── contract_test_generator.py # Test generator implementation
│   └── oracle_engine.py           # Oracle engine implementation
│
├── adapters/                      # Database adapters
│   ├── base.py                    # Base adapter interface
│   ├── milvus_adapter.py          # Milvus implementation
│   ├── mock.py                    # Mock implementation
│   ├── qdrant_adapter.py          # Qdrant implementation (planned)
│   └── seekdb_adapter.py          # SeekDB implementation (experimental)
│
├── pipeline/                      # Execution pipeline
│   ├── execute.py                 # Test execution orchestration
│   ├── preconditions.py           # Precondition evaluation
│   ├── gate.py                    # Precondition gate logic
│   └── confirm.py                 # User confirmation prompts
│
├── schemas/                       # Pydantic schemas
│   ├── test_case.py               # TestCase schema
│   ├── contract.py                # Contract schema
│   └── execution_result.py        # Execution result schema
│
├── casegen/                       # Test case templates (legacy)
│   └── templates/                 # YAML templates for test generation
│
├── campaigns/                     # Campaign configurations
│   └── *.yaml                     # Campaign definition files
│
├── scripts/                       # Execution scripts
│   ├── run_ann_pilot.py           # Run R5A pilot
│   ├── run_hybrid_pilot.py        # Run R5C pilot
│   └── run_phase3.py              # Run R3 campaign
│
├── docs/                          # Documentation
│   ├── PROJECT_OVERVIEW.md        # High-level project description
│   ├── PROJECT_PROGRESS_SUMMARY.md # Campaign history
│   ├── FRAMEWORK_ARCHITECTURE.md  # This file
│   ├── CURRENT_CHALLENGES.md      # Known limitations
│   └── NEXT_ROADMAP.md            # Future plans
│
├── generated_tests/               # Generated test cases
│   └── *_pilot_*.json             # Test case files
│
└── results/                       # Test execution results
    └── *_pilot_*.json             # Result files
```

---

## Design Patterns

### 1. Adapter Pattern

**Purpose**: Abstract database-specific operations

**Implementation**:
```python
# Base interface
class AdapterBase(ABC):
    @abstractmethod
    def execute(self, request: Dict) -> Dict:
        pass

# Concrete implementations
class MilvusAdapter(AdapterBase):
    def execute(self, request: Dict) -> Dict:
        # Milvus-specific implementation

class MockAdapter(AdapterBase):
    def execute(self, request: Dict) -> Dict:
        # In-memory implementation
```

**Benefits**:
- Unified interface for all databases
- Easy to add new databases
- Testable with mock implementations

### 2. Registry Pattern

**Purpose**: Central repository for contracts

**Implementation**:
```python
class ContractRegistry:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

**Benefits**:
- Single source of truth for contracts
- Lazy loading of contract files
- Efficient lookup by ID, family, or type

### 3. Strategy Pattern

**Purpose**: Different test generation strategies

**Implementation**:
```python
class ContractTestGenerator:
    STRATEGIES = {
        "legal": self._generate_legal_cases,
        "illegal": self._generate_illegal_cases,
        "boundary": self._generate_boundary_cases,
        "sequence": self._generate_sequence_cases
    }

    def generate(self, contract):
        strategy = contract.test_generation.strategy
        return self.STRATEGIES[strategy](contract)
```

**Benefits**:
- Extensible (add new strategies)
- Contract specifies preferred strategy
- Clear separation of generation logic

### 4. Template Method Pattern

**Purpose**: Oracle evaluation framework

**Implementation**:
```python
class OracleEngine:
    def evaluate(self, contract_id, result, contract):
        oracle_func = self._oracle_functions[contract_id]
        return oracle_func(result, contract)

    def _oracle_top_k_cardinality(self, result, contract):
        # Specific oracle implementation
        pass
```

**Benefits**:
- Consistent evaluation interface
- Easy to add new oracles
- Oracle logic isolated by contract

---

## Extension Points

### Adding a New Database Adapter

1. Create `adapters/{db}_adapter.py`
2. Inherit from `AdapterBase`
3. Implement `execute()` method
4. Add operation handlers (`_create_collection`, `_search`, etc.)
5. Register in factory if needed

**Example**:
```python
# adapters/qdrant_adapter.py
from adapters.base import AdapterBase

class QdrantAdapter(AdapterBase):
    def execute(self, request: Dict) -> Dict:
        operation = request.get("operation")
        if operation == "create_collection":
            return self._create_collection(request.get("params"))
        # ... other operations
```

### Adding a New Contract

1. Create `contracts/{family}/{contract_id}.json`
2. Define contract structure (statement, preconditions, postconditions, oracle)
3. Implement oracle function in `OracleEngine`
4. Register in `_oracle_functions` dictionary

**Example**:
```python
# core/oracle_engine.py
class OracleEngine:
    def __init__(self):
        self._oracle_functions = {
            "existing-001": self._oracle_existing_001,
            "new-contract": self._oracle_new_contract  # Add here
        }

    def _oracle_new_contract(self, result, contract):
        # Oracle implementation
        pass
```

### Adding a New Test Generation Strategy

1. Define strategy logic in `ContractTestGenerator`
2. Add to `STRATEGIES` dictionary
3. Specify in contract's `test_generation.strategy` field

**Example**:
```python
class ContractTestGenerator:
    STRATEGIES = {
        "legal": self._generate_legal_cases,
        "fuzzing": self._generate_fuzzing_cases  # New strategy
    }

    def _generate_fuzzing_cases(self, contract):
        # Fuzzing logic
        pass
```

---

## Configuration

### Contract Configuration

Contracts are configured via JSON files with schema validation:

```json
{
  "contract_id": "ANN-001",
  "name": "Top-K Cardinality Correctness",
  "family": "ANN",
  "type": "universal",
  "statement": "Search with top_k must return at most K results",
  "scope": {
    "databases": ["all"],
    "operations": ["search"],
    "conditions": ["top_k >= 0"]
  },
  "test_generation": {
    "strategy": "boundary",
    "parameters": {"top_k": [0, 1, 10, 100]}
  },
  "oracle": {
    "check": "count(results) <= top_k",
    "classification": "VIOLATION if check fails"
  }
}
```

### Database Profile Configuration

Database-specific configuration via YAML:

```yaml
# contracts/db_profiles/milvus_profile.yaml
database:
  name: milvus
  version: "2.3+"

supported_operations:
  - create_collection
  - insert
  - build_index
  - search
  - filtered_search
  - drop_collection

index_types:
  - FLAT
  - IVF_FLAT
  - HNSW
  - IVF_SQ8

metric_types:
  - L2
  - IP
  - COSINE

limitations:
  - dynamic_schema_changes: false
  - multiple_indexes: unknown
  - index_rebuild: false
```

---

## Error Handling

### Adapter Errors

```python
try:
    result = adapter.execute(request)
except DatabaseConnectionError:
    # Handle connection issues
except InvalidOperationError:
    # Handle invalid operations
except DatabaseTimeout:
    # Handle timeout
```

### Oracle Errors

```python
def evaluate(self, contract_id, result, contract):
    try:
        oracle_func = self._oracle_functions[contract_id]
        return oracle_func(result, contract)
    except KeyError:
        # No oracle defined - return OBSERVATION
        return OracleResult(
            contract_id=contract_id,
            classification=Classification.OBSERVATION,
            reasoning=f"No oracle for {contract_id}"
        )
    except Exception as e:
        # Oracle evaluation failed - return OBSERVATION
        return OracleResult(
            contract_id=contract_id,
            classification=Classification.OBSERVATION,
            reasoning=f"Oracle evaluation failed: {str(e)}"
        )
```

---

## Performance Considerations

### Test Execution Optimization

1. **Parallel Test Execution**: Independent tests can run in parallel
2. **Connection Pooling**: Reuse database connections
3. **Batch Operations**: Group insert operations
4. **Incremental Loading**: Load only required collections

### Oracle Evaluation Optimization

1. **Lazy Evaluation**: Compute metrics only when needed
2. **Caching**: Cache expensive computations (ground truth NN)
3. **Early Exit**: Fail fast on hard check violations

---

## Security Considerations

1. **Credential Management**: Don't hardcode credentials
2. **Input Validation**: Validate all user inputs
3. **SQL Injection**: Use parameterized queries (for SQL-based databases)
4. **Resource Limits**: Limit test execution time and resources

---

## Testing the Framework

### Unit Tests

```bash
pytest tests/unit/ -v
```

Test coverage:
- Contract registry
- Test generator
- Oracle engine
- Adapter methods

### Integration Tests

```bash
pytest tests/integration/ -v
```

Test coverage:
- End-to-end contract-to-execution flow
- Multi-contract scenarios
- Database adapter integration

### Framework Validation

The framework validates itself through:
- R5A ANN pilot (10 tests, all passed)
- R5C Hybrid pilot (14 tests, all passed)
- Mock adapter testing (all operations)

---

**Document Version**: 1.0
**Last Updated**: 2026-03-10
**Maintainer**: AI-DB-QC Framework Team
