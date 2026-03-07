# Phase 2: Rule-Based Generation + MockAdapter + Minimal Execute Flow (Revised)

> **Make static templates executable with mock database**

**Goal**: Enable end-to-end test case execution from templates to ExecutionResult with controlled Type 1-4 generation.

**Scope**: Template instantiation → Gate stub → MockAdapter → Execute → ExecutionResult → Triage (no real oracle, minimal confirm stub)

---

## Phase 2 Deliverables

### 1. Rule-Based Case Generation
- **TemplateLoader**: Load basic_templates.yaml
- **TemplateInstantiator**: Convert templates → TestCase instances
  - Substitute placeholders: `{id}`, `{collection}`, `{k}`, `{vectors}`, etc.
  - Support required_preconditions as list[str]
- **Output**: Simple `list[TestCase]` (no registry needed)

### 2. Minimal Gate Stub
- **GateStub**: Separate layer for precondition evaluation
  - `check(case: TestCase) -> tuple[bool, list[GateTrace]]`
  - Returns `(precondition_pass, gate_trace)` based on configured mode
  - **Structurally separate from adapter** - gate is methodological source of `precondition_pass`
  - MockAdapter may simulate runtime conditions, but gate owns the precondition logic

### 3. MockAdapter
- **AdapterBase** (abstract interface)
  - `execute(request: dict) -> dict` (raw execution, no triage)
  - `health_check() -> bool`
- **MockAdapter** (simulated database behavior)
  - Configurable response modes: `success`, `failure`, `crash`, `hang`, `timeout`
  - Configurable diagnostic slot quality (for Type-2 detection)
  - Built-in fault injection modes

### 4. Minimal Executor
- **Executor** (single class, not split)
  - `__init__(adapter: AdapterBase, gate: GateStub)`
  - `execute_case(case: TestCase) -> ExecutionResult`
  - `execute_batch(cases: List[TestCase]) -> List[ExecutionResult]`
  - Flow: gate check → adapter execute → build result

### 5. Basic Triage
- **Triage** class
  - `classify(case: TestCase, result: ExecutionResult) -> TriageResult`
  - Consumes original TestCase + ExecutionResult (interface change)
  - Uses `case.expected_validity` (not passed separately)
  - Decision tree from BUG_TAXONOMY.md
  - Enforces red-line: Type-3/4 require `precondition_pass=true`

### 6. Type-4 Simulation (Mock Only)
- **Phase 2 does NOT implement real oracle semantics**
- Type-4 is simulated via mock oracle results in ExecutionResult
- MockAdapter can inject `OracleResult` to test Type-4 classification path
- Real oracles (topk_monotonicity, etc.) are Phase 3

### 7. Confirm Placeholder (Minimal)
- **`pipeline/confirm.py`** (stub file only)
- Empty class or pass-through methods
- Not a Phase 2 focus

### 8. Single Script
- **`scripts/run_mock_tests.py`** (main script only)
- Load templates → instantiate → execute → triage → summarize
- No separate generate_cases script unless needed

---

## File Checklist (16 new files)

### NEW FILES (16)

#### Generators (2 files)
**`casegen/generators/__init__.py`**
- Package init

**`casegen/generators/instantiator.py`**
- `load_templates(path: str) -> List[dict]`
- `instantiate_template(template: dict, substitutions: dict) -> TestCase`
- `instantiate_all(templates: List[dict], substitutions: dict) -> List[TestCase]`

#### Gate (1 file)
**`pipeline/gate.py`** (NEW - separate from adapter)
- `GateStub` class
- `__init__(mode: PreconditionMode)`
- `check(case: TestCase) -> tuple[bool, List[GateTrace]]`
- Returns `(precondition_pass, gate_trace)`

#### Adapters (3 files)
**`adapters/__init__.py`**
- Package init

**`adapters/base.py`**
- `AdapterBase(ABC)` with `execute(request: dict) -> dict`

**`adapters/mock.py`**
- `MockAdapter(AdapterBase)`
- `response_mode`: Enum (SUCCESS, FAILURE, CRASH, HANG, TIMEOUT)
- `diagnostic_quality`: Enum (FULL, PARTIAL, NONE)
- `mock_oracle_result`: Optional[OracleResult] (for Type-4 simulation)

#### Executor (1 file)
**`pipeline/executor.py`**
- `Executor` class (single class, not split)
- `__init__(adapter: AdapterBase, gate: GateStub)`
- `execute_case(case: TestCase) -> ExecutionResult`
- `execute_batch(cases: List[TestCase]) -> List[ExecutionResult]`

#### Pipeline (2 files)
**`pipeline/__init__.py`**
- Package init

**`pipeline/triage.py`**
- `Triage` class
- `classify(case: TestCase, result: ExecutionResult) -> TriageResult` (interface changed)
- Decision tree implementation

**`pipeline/confirm.py`** (minimal stub)
- Empty class or pass-through
- Placeholder for Phase 3

#### Scripts (1 file)
**`scripts/run_mock_tests.py`** (single main script)
- Load templates
- Instantiate cases
- Create Executor with MockAdapter + GateStub
- Execute batch
- Run triage
- Print summary by bug type

#### Tests (4 files)
**`tests/unit/test_generators.py`**
- Test template loading and instantiation

**`tests/unit/test_gate.py`** (NEW)
- Test GateStub precondition modes

**`tests/unit/test_mock_adapter.py`**
- Test MockAdapter response modes
- Test diagnostic quality
- Test mock oracle injection (Type-4 simulation)

**`tests/unit/test_executor.py`**
- Test Executor
- E2E: template → case → gate → adapter → result → triage

---

## Architecture Flow (Revised)

```
1. Load templates (basic_templates.yaml)
   ↓
2. Instantiate templates → list[TestCase]
   ↓
3. For each case:
   a. GateStub.check(case) → (precondition_pass, gate_trace)
   b. MockAdapter.execute(request) → raw_response
   c. Build ExecutionResult
   ↓
4. Triage.classify(case, result) → TriageResult
   ↓
5. Summarize by bug type
```

**Key Point**: GateStub is **structurally separate** from MockAdapter. Gate owns `precondition_pass`, adapter only handles execution.

**GateStub Interface**: `check(case: TestCase) -> tuple[bool, list[GateTrace]]`

**Key Point**: GateStub is **structurally separate** from MockAdapter. Gate owns `precondition_pass`, adapter only handles execution.

---

## MockAdapter + GateStub Behavior

### GateStub Precondition Modes
| Mode | precondition_pass | gate_trace |
|------|-------------------|------------|
| ALL_PASS | true | All preconditions pass with reason "OK" |
| ALL_FAIL | false | All preconditions fail with reason "Not satisfied" |
| SELECTIVE | per-case list | Pass only preconditions in case.required_preconditions |

### MockAdapter Response Modes
| Mode | observed_outcome | error_message |
|------|------------------|---------------|
| SUCCESS | success | None |
| FAILURE | failure | Generic or configurable |
| CRASH | crash | "Process crashed" |
| HANG | hang | (timeout simulation) |
| TIMEOUT | timeout | "Operation timed out" |

### Diagnostic Quality (Type-2 detection)
| Quality | Error Message | missing_slots |
|---------|---------------|---------------|
| FULL | "Parameter 'top_k' has invalid value: -1" | [] |
| PARTIAL | "Invalid parameter value" | ["parameter_name"] |
| NONE | "Error" / "Failed" | All slots missing |

---

## Triage Interface (Changed)

```python
class Triage:
    def classify(self, case: TestCase, result: ExecutionResult) -> TriageResult:
        """
        Classify using case + result.

        Uses case.expected_validity (not passed as separate param).
        Enforces red-line: Type-3/4 require precondition_pass=true.
        Returns TriageResult object.
        """
        input_validity = case.expected_validity  # From TestCase

        # Step 1: Check precondition red-line
        if not result.precondition_pass:
            if input_validity == InputValidity.ILLEGAL:
                return TriageResult(
                    case_id=case.case_id,
                    run_id=result.run_id,
                    final_type=BugType.TYPE_2,
                    input_validity=input_validity.value,
                    observed_outcome=result.observed_outcome.value,
                    precondition_pass=False,
                    rationale="Illegal input with poor diagnostic"
                )
            else:
                return TriageResult(
                    case_id=case.case_id,
                    run_id=result.run_id,
                    final_type=BugType.TYPE_2_PRECONDITION_FAILED,
                    input_validity=input_validity.value,
                    observed_outcome=result.observed_outcome.value,
                    precondition_pass=False,
                    rationale="Contract-valid but precondition-fail"
                )

        # Step 2: Check input validity
        if input_validity == InputValidity.ILLEGAL:
            if result.observed_success:
                return TriageResult(
                    case_id=case.case_id,
                    run_id=result.run_id,
                    final_type=BugType.TYPE_1,
                    input_validity=input_validity.value,
                    observed_outcome=result.observed_outcome.value,
                    precondition_pass=True,
                    rationale="Illegal operation succeeded"
                )
            else:
                return TriageResult(
                    case_id=case.case_id,
                    run_id=result.run_id,
                    final_type=BugType.TYPE_2,
                    input_validity=input_validity.value,
                    observed_outcome=result.observed_outcome.value,
                    precondition_pass=True,
                    rationale="Illegal operation with poor diagnostic"
                )

        # Step 3: Legal input, precondition passed
        if not result.observed_success:
            return TriageResult(
                case_id=case.case_id,
                run_id=result.run_id,
                final_type=BugType.TYPE_3,
                input_validity=input_validity.value,
                observed_outcome=result.observed_outcome.value,
                precondition_pass=True,
                rationale="Legal operation failed (precondition satisfied)"
            )

        # Step 4: Legal input, precondition passed, succeeded
        # Phase 2: Check for mock oracle results only
        if result.oracle_results and any(not o.passed for o in result.oracle_results):
            return TriageResult(
                case_id=case.case_id,
                run_id=result.run_id,
                final_type=BugType.TYPE_4,
                input_validity=input_validity.value,
                observed_outcome=result.observed_outcome.value,
                precondition_pass=True,
                rationale="Semantic violation detected by oracle (mock)"
            )

        # Not a bug - could return None or create a "valid" result
        return None
```

---

## Type-4 Simulation (Phase 2 Only)

Phase 2 does **not** implement real oracles. Type-4 classification is tested via:

```python
# MockAdapter can inject mock oracle result
mock_adapter = MockAdapter(
    response_mode=ResponseMode.SUCCESS,
    mock_oracle_result=OracleResult(
        oracle_id="mock_oracle",
        passed=False,
        explanation="Simulated oracle failure"
    )
)
```

This tests the Type-4 **classification path** without implementing real oracle semantics.

---

## Single Script Usage

```bash
# Run mock tests with default settings
python scripts/run_mock_tests.py

# Run with specific modes
python scripts/run_mock_tests.py --response SUCCESS --gate ALL_PASS

# Run to simulate Type-1 failures
python scripts/run_mock_tests.py --response SUCCESS --gate ALL_PASS --test-type-1

# Run all tests
pytest tests/unit/ -v
```

---

## Verification Commands

```bash
# Run main script
python scripts/run_mock_tests.py

# E2E test
python -c "
from casegen.generators.instantiator import load_templates, instantiate_all
from adapters.mock import MockAdapter, ResponseMode
from pipeline.gate import GateStub, PreconditionMode
from pipeline.executor import Executor
from pipeline.triage import Triage

templates = load_templates('casegen/templates/basic_templates.yaml')
cases = instantiate_all(templates, {'collection': 'test', 'k': 10})

adapter = MockAdapter(response_mode=ResponseMode.SUCCESS)
gate = GateStub(mode=PreconditionMode.ALL_PASS)
executor = Executor(adapter, gate)
triage = Triage()

results = executor.execute_batch(cases)
for r in results:
    t = triage.classify(r.case, r)
    print(f'{r.case_id}: {t.final_type if t else \"valid\"}')
"
```

---

## Summary

| Category | Files | Key Point |
|----------|-------|-----------|
| Generators | 2 | instantiator (list[TestCase], no registry) |
| Gate | 1 | GateStub (separate from adapter) |
| Adapters | 3 | base, mock (controllable), __init__ |
| Executor | 1 | Single class with execute_case + execute_batch |
| Triage | 1 | Triage.classify(case, result) |
| Confirm | 1 | Minimal stub file |
| Scripts | 1 | run_mock_tests.py (single main script) |
| Tests | 4 | test_generators, test_gate, test_mock_adapter, test_executor |
| **Total New** | **16** | Includes gate separation, simplified executor |

---

## Methodological Reminders

1. **Gate is structurally separate from adapter** - gate owns `precondition_pass`, adapter only executes
2. **Triage interface changed**: `classify(case, result)` not `classify(result, validity)`
3. **Type-4 is mock-only**: Phase 2 tests classification path, not real oracle semantics
4. **Executor is single class**: Not split into Simple/Batch
5. **No TestCaseRegistry**: Use simple `list[TestCase]`
6. **Confirm is minimal stub**: Not a Phase 2 focus
7. **Single script surface**: One main script for mock execution
8. **precondition_pass is STILL HARD constraint** for Type-3/4
9. **YAGNI**: Minimal working flow

---

## Next Phase (Phase 3 Preview)

Phase 3 will add:
- Real MilvusAdapter
- Real precondition gate (runtime checks)
- Real oracle implementations (topk_monotonicity, filter_strictness, write_read_consistency)
- Evidence bundle writing
- Enhanced confirm with rerun
