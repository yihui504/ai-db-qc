# Phase 1: Compressed Implementation Checklist (Revised)

> **Minimal, Schema-First, Static Foundation**
> **24 files | 6 adjustments applied**

**Goal**: Establish the minimal static skeleton for AI-DB-QC research prototype.

**Scope**: Docs + Schemas + Contracts/Profiles + Templates + Tests (static only)

**Constraints**:
- NO real DB logic
- NO oracle logic
- NO full triage/confirm logic
- NO LLM integration
- Schema-first but minimal
- Core contract ≠ DB profile (keep separate)

---

## File Checklist (24 files)

**Adjustments applied**:
1. ✅ PROJECT_SCOPE.md separated into overall vs Phase 1
2. ✅ TestCase.preconditions uses extensible list[str] structure
3. ✅ TriageResult moved to schemas/triage.py (separate file)
4. ✅ PreconditionFailed documented as Type-2 subtype (not 5th class)
5. ✅ Added contracts/core/validator.py for static validation
6. ✅ DBProfile expanded with supported_operations, parameter_relaxations, supported_features, environment_requirements

### CONFIGURATION (3 files)

#### 1. `pyproject.toml`
**Purpose**: Project metadata and dependencies
**Content**:
```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "ai-db-qc"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["pydantic>=2.0.0", "pyyaml>=6.0"]

[project.optional-dependencies]
dev = ["pytest>=7.0.0", "pydantic>=2.0.0"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```
**Acceptance**: `pyproject.toml` exists

---

#### 2. `requirements.txt`
**Purpose**: Dependencies
**Content**:
```txt
pydantic>=2.0.0
pyyaml>=6.0
pytest>=7.0.0
```
**Acceptance**: File exists

---

#### 3. `.gitignore`
**Purpose**: Ignore build artifacts
**Content**: Standard Python gitignore (`__pycache__`, `*.pyc`, `.pytest_cache`, `venv/`)
**Acceptance**: File exists

---

### DOCUMENTATION (4 files)

#### 4. `README.md`
**Purpose**: Project overview
**Content**: Brief description of AI-DB-QC as research prototype with:
- Two core functions: generation + validation
- Four-type bug taxonomy
- Quick start commands
- Project structure
**Acceptance**: File exists with key sections

---

#### 5. `THEORY.md`
**Purpose**: Theoretical foundation
**Content**:
- Dual-layer validity model (abstract legality vs runtime readiness)
- Four-type taxonomy
- Contract-driven architecture
- Evidence-centric execution
- LLM positioning (not source of truth)
**Acceptance**: File exists with core concepts

---

#### 6. `PROJECT_SCOPE.md`
**Purpose**: Scope boundaries
**Content**:
- **Overall project scope**: structured generation + structured validation, Milvus support, 3 oracles
- **Phase 1 scope** (explicitly limited):
  - ✅ Static schemas only
  - ✅ Contract/profile loading and validation
  - ✅ Case template structure
  - ❌ NO oracle implementation
  - ❌ NO real DB execution
  - ❌ NO triage/confirm pipeline implementation
- **Out of scope**: platform features, multi-database abstraction, complex UI
- Success criteria
**Acceptance**: File clearly separates overall vs Phase 1 scope

---

#### 7. `BUG_TAXONOMY.md`
**Purpose**: Four-type classification with red-line
**Content**:
- **Four top-level types only**: Type-1, Type-2, Type-3, Type-4
- Type-1: Illegal succeeded (`illegal ∧ success`)
- Type-2: Illegal poor diagnostic (`illegal ∧ failed ∧ poor_error`)
- **Type-2.PreconditionFailed**: Subtype of Type-2 (NOT a 5th top-level type)
  - Contract-valid input but precondition-fail with poor diagnostic
  - Examples: search on non-existent collection, search before index load
- Type-3: Legal failed (`legal ∧ precondition_pass=true ∧ failed`) ← RED LINE
- Type-4: Semantic violation (`legal ∧ precondition_pass=true ∧ oracle_failed`) ← RED LINE
- Decision tree showing PreconditionFailed as Type-2 branch
- Explicit statement: "There are exactly FOUR top-level bug types"
- Examples
**Acceptance**: File exists with red-line emphasized, PreconditionFailed clearly as Type-2 subtype

---

### SCHEMAS (5 files)

#### 8. `schemas/__init__.py`
**Purpose**: Schema exports
**Content**: Export all schemas
**Acceptance**: Imports work

---

#### 9. `schemas/common.py`
**Purpose**: Base types and enums
**Content**:
```python
from enum import Enum
from pydantic import BaseModel

class InputValidity(str, Enum):
    LEGAL = "legal"
    ILLEGAL = "illegal"

class BugType(str, Enum):
    TYPE_1 = "type-1"
    TYPE_2 = "type-2"
    TYPE_2_PRECONDITION_FAILED = "type-2.precondition_failed"
    TYPE_3 = "type-3"
    TYPE_4 = "type-4"

class OperationType(str, Enum):
    CREATE_COLLECTION = "create_collection"
    INSERT = "insert"
    SEARCH = "search"
    # ... others

class ObservedOutcome(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    CRASH = "crash"

class GateTrace(BaseModel):
    precondition_name: str
    passed: bool
    reason: str = ""
```
**Acceptance**: Enums defined, import works

---

#### 10. `schemas/case.py`
**Purpose**: Test case schema
**Content**:
```python
from pydantic import BaseModel, Field
from typing import Dict, Any, List
from schemas.common import InputValidity, OperationType

class TestCase(BaseModel):
    case_id: str
    operation: OperationType
    params: Dict[str, Any]
    expected_validity: InputValidity
    required_preconditions: List[str] = Field(
        default_factory=list,
        description="Runtime preconditions required (extensible, e.g., 'collection_exists', 'index_loaded')"
    )
    oracle_refs: List[str] = Field(default_factory=list)
    rationale: str = ""
```
**Acceptance**: Can serialize/deserialize, preconditions is extensible list[str]

---

#### 11. `schemas/result.py`
**Purpose**: Execution result schema (TriageResult moved to separate file)
**Content**:
```python
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from schemas.common import ObservedOutcome, GateTrace

class OracleResult(BaseModel):
    oracle_id: str
    passed: bool
    explanation: str = ""

class ExecutionResult(BaseModel):
    run_id: str
    case_id: str
    adapter_name: str
    request: Dict[str, Any]
    response: Optional[Dict[str, Any]] = None
    observed_outcome: ObservedOutcome
    error_message: Optional[str] = None
    latency_ms: float
    precondition_pass: bool  # CRITICAL for red-line
    gate_trace: List[GateTrace] = Field(default_factory=list)
    oracle_results: List[OracleResult] = Field(default_factory=list)

    @property
    def observed_success(self) -> bool:
        return self.observed_outcome == ObservedOutcome.SUCCESS
```
**Acceptance**: ExecutionResult serializes, precondition_pass field exists

---

#### 12. `schemas/triage.py`
**Purpose**: Triage result schema (separate from execution result)
**Content**:
```python
from pydantic import BaseModel
from schemas.common import BugType

class TriageResult(BaseModel):
    case_id: str
    run_id: str
    final_type: BugType
    input_validity: str
    observed_outcome: str
    precondition_pass: bool  # CRITICAL for red-line
    rationale: str
```
**Acceptance**: TriageResult separate from ExecutionResult, imports work

---

### CONTRACTS (5 files)

#### 13. `contracts/core/__init__.py`
**Purpose**: Core contract package
**Content**: Empty init
**Acceptance**: Package exists

---

#### 14. `contracts/core/schema.py`
**Purpose**: Core contract schema (database-agnostic)
**Content**:
```python
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from schemas.common import OperationType

class ParameterConstraint(BaseModel):
    name: str
    type: str
    required: bool = True
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    allowed_values: Optional[List] = None

class OperationContract(BaseModel):
    operation_type: OperationType
    parameters: Dict[str, ParameterConstraint]
    required_preconditions: List[str] = Field(default_factory=list)

class CoreContract(BaseModel):
    contract_name: str
    contract_version: str
    operations: Dict[OperationType, OperationContract]
```
**Acceptance**: Schema defined

---

#### 15. `contracts/core/default_contract.yaml`
**Purpose**: Default core contract (database-agnostic)
**Content**: YAML with:
- contract_name: "ai_db_core_v1"
- Operations: create_collection, insert, search, etc.
- Each operation has: parameters with constraints, required_preconditions
**Key for search**: top_k min=1, preconditions list includes "collection_exists", "index_loaded"
**Acceptance**: Valid YAML, loadable

---

#### 16. `contracts/core/loader.py`
**Purpose**: Load core contract from YAML
**Content**:
```python
import yaml
from pathlib import Path
from contracts.core.schema import CoreContract

def load_contract(path: str | Path) -> CoreContract:
    data = yaml.safe_load(Path(path).read_text())
    return CoreContract(**data)

def get_default_contract() -> CoreContract:
    return load_contract(Path(__file__).parent / "default_contract.yaml")
```
**Acceptance**: Can load default_contract.yaml

---

#### 17. `contracts/core/validator.py`
**Purpose**: Static validation of contracts
**Content**:
```python
from contracts.core.schema import CoreContract
from schemas.common import OperationType

class ContractValidationError(Exception):
    pass

def validate_contract(contract: CoreContract) -> list[str]:
    """
    Perform static validation on loaded contract.
    Returns list of error messages (empty if valid).
    """
    errors = []

    # Check required top-level fields
    if not contract.contract_name:
        errors.append("contract_name is required")
    if not contract.contract_version:
        errors.append("contract_version is required")
    if not contract.operations:
        errors.append("operations must not be empty")

    # Check operation references consistency
    for op_type, op_contract in contract.operations.items():
        if not isinstance(op_type, OperationType):
            errors.append(f"Invalid operation type: {op_type}")

    return errors
```
**Acceptance**: validate_contract returns empty list for valid contract

---

### DB PROFILES (3 files)

#### 18. `contracts/db_profiles/__init__.py`
**Purpose**: DB profiles package
**Content**: Empty init
**Acceptance**: Package exists

---

#### 19. `contracts/db_profiles/schema.py`
**Purpose**: DB profile schema (database-specific)
**Content**:
```python
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from schemas.common import OperationType

class DBProfile(BaseModel):
    profile_name: str
    db_type: str
    db_version: str = ""

    # Operation support
    supported_operations: List[str] = Field(default_factory=list)

    # Operation mappings (core op -> DB-specific API)
    operation_mappings: Dict[str, Dict[str, str]] = Field(default_factory=dict)

    # Parameter relaxations (override core constraints)
    parameter_relaxations: Dict[str, Dict[str, any]] = Field(
        default_factory=dict,
        description="Key: operation_name, value: {param: {min/max/allowed}}"
    )

    # Supported features
    supported_features: List[str] = Field(
        default_factory=list,
        description="e.g., IVF_FLAT, HNSW, scalar_index"
    )

    # Environment requirements
    environment_requirements: Dict[str, str] = Field(
        default_factory=dict,
        description="e.g., min_memory, service_dependencies"
    )
```
**Acceptance**: Schema defined with all required fields

---

#### 20. `contracts/db_profiles/milvus_profile.yaml`
**Purpose**: Milvus-specific profile
**Content**: YAML with:
- profile_name: "milvus-2.3"
- db_type: "milvus"
- db_version: "2.3.x"
- supported_operations: [create_collection, insert, search, ...]
- operation_mappings: map core ops to Milvus API endpoints
- parameter_relaxations: search.top_k max=16384
- supported_features: [IVF_FLAT, HNSW, scalar_index, filtered_search]
- environment_requirements: {service: "milvus-standalone", min_memory: "4GB"}
**Acceptance**: Valid YAML, all sections populated

---

#### 21. `contracts/db_profiles/loader.py`
**Purpose**: Load DB profile
**Content**:
```python
import yaml
from pathlib import Path
from contracts.db_profiles.schema import DBProfile

def load_profile(path: str | Path) -> DBProfile:
    data = yaml.safe_load(Path(path).read_text())
    return DBProfile(**data)
```
**Acceptance**: Can load milvus_profile.yaml

---

### CASE TEMPLATES (1 file)

#### 22. `casegen/templates/basic_templates.yaml`
**Purpose**: 10 basic case templates
**Content**: YAML with 10 templates:
- 3 valid: create_collection, insert, search (all contract-valid)
- 4 invalid: negative top_k, zero dimension, wrong metric, dimension mismatch
- 3 pseudo-valid: search on non-existent collection, search before load, insert to non-existent
**Key**: Use `required_preconditions: ["collection_exists", "index_loaded"]` format (list of strings)
**Acceptance**: 10 templates, covers 3 categories, preconditions as list[str]

---

### UNIT TESTS (3 files)

#### 23. `tests/unit/test_schemas.py`
**Purpose**: Test schemas
**Content**: Tests for:
- Enum values (BugType has 4 top-level + 1 subtype)
- TestCase creation and serialization with required_preconditions as list[str]
- ExecutionResult with precondition_pass field
- TriageResult (from schemas.triage) with BugType
**Acceptance**: `pytest tests/unit/test_schemas.py` passes

---

#### 24. `tests/unit/test_contracts.py`
**Purpose**: Test contracts
**Content**: Tests for:
- Load default contract
- Parameter constraints exist
- Required preconditions defined as list[str]
- validate_contract returns empty list for valid contract
**Acceptance**: `pytest tests/unit/test_contracts.py` passes

---

#### 25. `tests/unit/test_profiles.py`
**Purpose**: Test DB profiles
**Content**: Tests for:
- Load milvus_profile.yaml
- DBProfile has all required fields (supported_operations, parameter_relaxations, etc.)
**Acceptance**: `pytest tests/unit/test_profiles.py` passes

---

## Verification Commands

```bash
# Create directory structure
mkdir -p contracts/core contracts/db_profiles schemas casegen/templates tests/unit

# Run all tests
pytest tests/unit/ -v

# Verify imports
python -c "from schemas import TestCase, ExecutionResult, BugType; from schemas.triage import TriageResult; print('OK')"

# Verify loading
python -c "from contracts.core.loader import get_default_contract; from contracts.core.validator import validate_contract; c=get_default_contract(); errors=validate_contract(c); print(f'{c.contract_name}: {len(c.operations)} ops, {len(errors)} errors')"

# Verify profile loading
python -c "from contracts.db_profiles.loader import load_profile; p=load_profile('contracts/db_profiles/milvus_profile.yaml'); print(f'{p.profile_name}: {len(p.supported_operations)} ops')"
```

---

## Summary

| Category | Files | Key Point |
|----------|-------|-----------|
| Config | 3 | pyproject.toml, requirements, gitignore |
| Docs | 4 | README, THEORY, SCOPE (overall vs Phase 1), TAXONOMY (4 top-level types) |
| Schemas | 5 | common, case (list[str] preconds), result, triage (separate), __init__ |
| Contracts | 5 | schema, YAML (core), loader, validator, __init__ |
| Profiles | 3 | schema, YAML (milvus with richer structure), loader, __init__ |
| Templates | 1 | 10 templates (3/4/3 split, preconds as list[str]) |
| Tests | 3 | test_schemas, test_contracts, test_profiles |
| **Total** | **24** | Minimal static foundation |

---

## Methodological Reminders

1. **precondition_pass is HARD constraint for Type-3/4**
2. **abstract legality (contract) ≠ runtime readiness (precondition)**
3. **core contract (agnostic) ≠ db profile (specific)**
4. **LLM is never source of truth**
5. **PreconditionFailed is Type-2 subtype, NOT 5th top-level type**
6. **YAGNI: minimal, research-oriented, not platform**
7. **Phase 1 explicitly excludes: oracle implementation, real DB execution, triage/confirm pipeline**
