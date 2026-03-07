# Phase 3: Methodological Hardening - Precondition Gate, Evidence, Oracles (Revised)

> **Upgrade Phase 2 mock-only to formal methodological skeleton**

**Goal**: Contract/profile-aware, evidence-backed, oracle-ready, still local and minimal

**Scope**: PreconditionEvaluator → MockAdapter → Oracle → Triage → EvidenceWriter (no real DB/LLM)

---

## Phase 3 Deliverables

### 1. PreconditionEvaluator (Replaces GateStub)
- Formal PreconditionEvaluator in `pipeline/preconditions.py`
- Contract-aware: checks core contract + DB profile constraints
- Returns `(precondition_pass, gate_trace)` with structured reasoning
- Keeps abstract legality (contract) separate from runtime readiness

### 2. EvidenceWriter
- Minimal EvidenceWriter in `evidence/writer.py`
- Run-scoped artifact output: run directory with metadata, snapshots, results
- No complex replay - just structured JSON/YAML files
- EvidenceBundle schema already exists in Phase 1 (use or extend)

### 3. Oracle Layer
- **OracleBase** in `oracles/base.py`
  - `validate(case, result, context) -> OracleResult`
  - Abstract interface
- **WriteReadConsistency** oracle in `oracles/write_read_consistency.py`
  - Validates: data written can be read back
- **FilterStrictness** oracle in `oracles/filter_strictness.py`
  - Validates: filtered results are subset of unfiltered

### 4. Upgraded Triage
- Type-4 triggered by **actual oracle failure**, not mock placeholder
- Consumes structured oracle outputs
- Returns TriageResult with oracle references

### 5. Upgraded Run Script
- Single script for full mock flow with evidence output
- Templates → Cases → PreconditionEvaluator → MockAdapter → Oracles → Triage → Evidence

---

## File Checklist (14 new files, 5 modified)

### NEW FILES (14)

#### Preconditions (1 file)
**`pipeline/preconditions.py`**
- `PreconditionEvaluator` class (replaces GateStub)
- `__init__(contract: CoreContract, profile: DBProfile, runtime_context: Dict)`
- `evaluate(case: TestCase) -> tuple[bool, List[GateTrace]]`
- Checks: operation supported, required params, runtime constraints
- **GateTrace.check_type distinguishes**:
  - `"legality"` - abstract contract compliance (operation exists, params defined)
  - `"runtime"` - runtime readiness (collection exists, connection active)
- Runtime evaluation uses runtime_context for realistic failures

#### Evidence (2 files)
**`evidence/__init__.py`**
- Package init

**`evidence/writer.py`**
- `EvidenceWriter` class
- `create_run_dir(run_id: str) -> Path`
- `write_run_metadata(run_id, config, env_info)`
- `write_cases(cases: List[TestCase])` → **NEW** write cases.jsonl
- `write_execution_results(results: List[ExecutionResult])`
- `write_triage_results(triage_results: List[TriageResult])`
- Output: JSON files per run, structured directory layout including case snapshots

#### Oracles (4 files)
**`oracles/__init__.py`**
- Package init

**`oracles/base.py`**
- `OracleBase(ABC)` with abstract `validate()` method
- `validate(case, result, context) -> OracleResult`
- Context includes: mock_state from executor, unfiltered_result_ids for subset checks

**`oracles/write_read_consistency.py`**
- `WriteReadConsistency(OracleBase)`
- **No internal state** - reads from context.mock_state
- Validates: written data appears in subsequent read/search
- Executor provides mock_state in context: `{"collection_id": [vectors]}`
- Returns OracleResult with metrics

**`oracles/filter_strictness.py`**
- `FilterStrictness(OracleBase)`
- Validates: filtered search result IDs ⊆ unfiltered search result IDs
- **MockAdapter returns results with IDs**: `{"data": [{"id": 1, ...}, ...]}`
- **Baseline from executor context**: `context.get("unfiltered_result_ids")`
- Returns OracleResult with unexpected IDs if subset violated

#### Pipeline Upgrades (2 files)
**`pipeline/triage.py`** (MODIFIED)
- Remove mock-only Type-4 logic
- Type-4 only from actual oracle failure
- Consume oracle outputs in classification

**`pipeline/executor.py`** (MODIFIED)
- Add oracle execution step with context management
- `execute_case()` now manages mock_state for writes and passes to oracles via context
- Tracks unfiltered_result_ids (list of IDs) for FilterStrictness oracle subset validation
- Returns ExecutionResult with oracle_results populated
- Context structure: `{"mock_state": Dict, "unfiltered_result_ids": List[int]}`

#### Scripts (1 file)
**`scripts/run_phase3.py`**
- Full mock flow: templates → cases → PreconditionEvaluator → MockAdapter → Oracles → Triage → Evidence
- Arguments: `--output-dir`, `--diagnostic-quality`, `--gate-mode`
- Creates evidence bundle in output directory

#### Tests (4 files)
**`tests/unit/test_preconditions.py`**
- Test PreconditionEvaluator
- Test contract-aware checks (legality vs runtime)
- Test gate trace structure with check_type field
- Test runtime precondition evaluation against runtime_context
- Test collection_exists, has_index, connection_active checks

**`tests/unit/test_evidence_writer.py`**
- Test EvidenceWriter
- Test run directory creation
- Test file structure

**`tests/unit/test_oracles.py`**
- Test OracleBase interface
- Test WriteReadConsistency oracle (context consumption)
- Test FilterStrictness oracle (ID-based subset validation)
- Test subset violation detection with unexpected IDs

**`tests/unit/test_e2e_phase3.py`**
- End-to-end: templates → cases → PreconditionEvaluator → MockAdapter → Oracles → Triage → Evidence
- Verify Type-4 from actual oracle failure
- Verify GateTrace.check_type distinguishes legality vs runtime checks
- Verify runtime preconditions fail against runtime_context

---

## MODIFIED FILES (5)

**`schemas/common.py`** (MODIFIED - add check_type field to GateTrace)
- Add `check_type: Literal["legality", "runtime"]` field to GateTrace
- Distinguishes abstract legality (contract) from runtime readiness checks

**`pipeline/gate.py`** (DEPRECATED - kept for compatibility, PreconditionEvaluator replaces it)

**`schemas/evidence.py`** (already exists from Phase 1, use or extend if needed)

**`schemas/triage.py`** (no changes needed - already supports oracle_refs)

**`docs/plans/2026-03-07-phase3-compressed.md`** (this file)

---

## Architecture Flow (Phase 3)

```
1. Load templates → list[TestCase]
   ↓
2. For each case:
   a. PreconditionEvaluator.evaluate(case) → (precondition_pass, gate_trace)
   b. MockAdapter.execute(request) → raw_response
   c. Build ExecutionResult
   d. Executor tracks mock_state for writes, passes context to oracles
   e. Oracles.validate(case, result, context) → list[OracleResult]
   f. Triage.classify(case, result) → TriageResult
   ↓
3. EvidenceWriter.write_all(run_dir)
   - run_metadata.json
   - cases.jsonl
   - execution_results.jsonl
   - triage_report.json
   - evidence.json (optional)
```

---

## Oracle Interface

```python
class OracleBase(ABC):
    """Base class for semantic oracles."""

    @abstractmethod
    def validate(
        self,
        case: TestCase,
        result: ExecutionResult,
        context: Dict[str, Any]
    ) -> OracleResult:
        """
        Validate semantic correctness.

        Args:
            case: Original test case
            result: Execution result
            context: Additional context (e.g., mock state for consistency checks)

        Returns:
            OracleResult with passed/failed, metrics, explanation
        """
        pass
```

---

## PreconditionEvaluator Design

```python
from typing import Literal

class PreconditionEvaluator:
    """Formal precondition evaluation (contract-aware)."""

    def __init__(self, contract: CoreContract, profile: DBProfile, runtime_context: Dict):
        self.contract = contract
        self.profile = profile
        self.runtime_context = runtime_context  # {"collections": [], "connected": bool}

    def evaluate(self, case: TestCase) -> tuple[bool, List[GateTrace]]:
        """
        Evaluate preconditions for a case.

        Checks:
        1. Operation is supported (from profile) - LEGALITY check
        2. Required parameters present (from contract) - LEGALITY check
        3. Runtime constraints (from runtime_context) - RUNTIME check
        """
        gate_trace = []
        all_passed = True

        # Check 1: Operation supported (legality)
        op_contract = self.contract.operations.get(case.operation)
        if op_contract is None:
            gate_trace.append(GateTrace(
                precondition_name="operation_supported",
                check_type="legality",
                passed=False,
                reason=f"Operation {case.operation} not in core contract"
            ))
            return False, gate_trace

        # Check 2: Operation in profile (legality)
        if case.operation.value not in self.profile.supported_operations:
            gate_trace.append(GateTrace(
                precondition_name="operation_in_profile",
                check_type="legality",
                passed=False,
                reason=f"Operation {case.operation} not in DB profile"
            ))
            return False, gate_trace

        # Check 3: Required parameters (legality)
        for param_name, param_constraint in op_contract.parameters.items():
            if param_constraint.required and param_name not in case.params:
                gate_trace.append(GateTrace(
                    precondition_name=f"param_{param_name}",
                    check_type="legality",
                    passed=False,
                    reason=f"Required parameter '{param_name}' missing"
                ))
                all_passed = False

        # Check 4: Runtime preconditions (runtime)
        for precond in case.required_preconditions:
            passed = self._check_runtime_precondition(precond)
            gate_trace.append(GateTrace(
                precondition_name=precond,
                check_type="runtime",
                passed=passed,
                reason="Satisfied" if passed else "Not available in runtime context"
            ))
            if not passed:
                all_passed = False

        return all_passed, gate_trace

    def _check_runtime_precondition(self, precond: str) -> bool:
        """Check runtime precondition against runtime_context."""
        if precond == "collection_exists":
            collection_name = self.runtime_context.get("target_collection")
            available_collections = self.runtime_context.get("collections", [])
            return collection_name in available_collections

        if precond == "has_index":
            collection_name = self.runtime_context.get("target_collection")
            indexed_collections = self.runtime_context.get("indexed_collections", [])
            return collection_name in indexed_collections

        if precond == "connection_active":
            return self.runtime_context.get("connected", False)

        # Unknown precondition - assume not satisfied
        return False
```

---

## EvidenceWriter Design

```python
class EvidenceWriter:
    """Write evidence artifacts to run-scoped directory."""

    def create_run_dir(self, run_id: str, base_path: str = "runs") -> Path:
        """Create run directory and return path."""
        run_dir = Path(base_path) / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    def write_all(
        self,
        run_dir: Path,
        run_metadata: Dict[str, Any],
        cases: List[TestCase],
        results: List[ExecutionResult],
        triage_results: List[TriageResult]
    ) -> None:
        """Write all evidence files."""
        self._write_run_metadata(run_dir, run_metadata)
        self._write_cases(run_dir, cases)  # NEW: write case snapshots
        self._write_execution_results(run_dir, results)
        self._write_triage_report(run_dir, triage_results)

    def _write_run_metadata(self, run_dir: Path, metadata: Dict) -> None:
        """Write run_metadata.json."""
        import json
        with open(run_dir / "run_metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

    def _write_cases(self, run_dir: Path, cases: List[TestCase]) -> None:
        """Write cases.jsonl."""
        import json
        with open(run_dir / "cases.jsonl", "w") as f:
            for c in cases:
                json.dump(c.model_dump(mode="json"), f)
                f.write("\n")

    def _write_execution_results(self, run_dir: Path, results: List) -> None:
        """Write execution_results.jsonl."""
        import json
        with open(run_dir / "execution_results.jsonl", "w") as f:
            for r in results:
                json.dump(r.model_dump(mode="json"), f)
                f.write("\n")

    def _write_triage_report(self, run_dir: Path, triage_results: List) -> None:
        """Write triage_report.json."""
        import json
        # Filter out None (not bugs)
        bugs = [t.model_dump(mode="json") for t in triage_results if t]
        with open(run_dir / "triage_report.json", "w") as f:
            json.dump(bugs, f, indent=2)
```

---

## WriteReadConsistency Oracle

```python
class WriteReadConsistency(OracleBase):
    """Validate: written data can be read back."""

    def __init__(self):
        # No internal state - consumes context.mock_state provided by executor
        pass

    def validate(self, case: TestCase, result: ExecutionResult, context: Dict) -> OracleResult:
        mock_state = context.get("mock_state", {})

        # Validate reads/searches against written data in context
        if case.operation in [OperationType.SEARCH, OperationType.FILTERED_SEARCH]:
            collection = case.params.get("collection_name")
            if collection and collection in mock_state:
                written_count = len(mock_state[collection])
                result_count = len(result.response.get("data", []))
                # Result count should not exceed written count
                if result_count > written_count:
                    return OracleResult(
                        oracle_id="write_read_consistency",
                        passed=False,
                        metrics={"written": written_count, "returned": result_count},
                        expected_relation=f"returned <= written",
                        observed_relation=f"returned ({result_count}) > written ({written_count})",
                        explanation="More results returned than were written"
                    )

        return OracleResult(
            oracle_id="write_read_consistency",
            passed=True,
            metrics={},
            explanation="Write-read consistency satisfied"
        )
```

---

## FilterStrictness Oracle

```python
class FilterStrictness(OracleBase):
    """Validate: filtered results are subset of unfiltered."""

    def validate(self, case: TestCase, result: ExecutionResult, context: Dict) -> OracleResult:
        # Only applies to filtered_search
        if case.operation != OperationType.FILTERED_SEARCH:
            return OracleResult(oracle_id="filter_strictness", passed=True, explanation="N/A")

        # Get unfiltered result IDs from executor context
        # Executor populates this: {"result_ids": [1, 2, 3, 4, 5]}
        unfiltered_ids = set(context.get("unfiltered_result_ids", []))

        # Extract IDs from filtered response
        # MockAdapter returns: {"data": [{"id": 1}, {"id": 3}]}
        filtered_ids = set(item.get("id") for item in result.response.get("data", []))

        # Check subset: filtered_ids ⊆ unfiltered_ids
        if not filtered_ids.issubset(unfiltered_ids):
            unexpected_ids = filtered_ids - unfiltered_ids
            return OracleResult(
                oracle_id="filter_strictness",
                passed=False,
                metrics={
                    "unfiltered_count": len(unfiltered_ids),
                    "filtered_count": len(filtered_ids),
                    "unexpected_ids": list(unexpected_ids)
                },
                expected_relation="filtered ⊆ unfiltered",
                observed_relation=f"filtered has IDs {list(unexpected_ids)} not in unfiltered",
                explanation="Filter produced results not present in unfiltered search"
            )

        return OracleResult(
            oracle_id="filter_strictness",
            passed=True,
            metrics={
                "unfiltered_count": len(unfiltered_ids),
                "filtered_count": len(filtered_ids)
            },
            explanation="Filter strictness satisfied: all filtered results in unfiltered"
        )
```

---

## MockAdapter Enhancements (Phase 3)

MockAdapter is modified to return results with IDs for subset validation:

```python
class MockAdapter(AdapterBase):
    """Mock adapter for controllable test behavior."""

    def __init__(
        self,
        response_mode: ResponseMode = ResponseMode.SUCCESS,
        diagnostic_quality: DiagnosticQuality = DiagnosticQuality.FULL,
        mock_oracle_result: Optional[OracleResult] = None,
        result_id_start: int = 1,  # NEW: for generating IDs
        result_count: int = 5      # NEW: number of mock results
    ):
        self.response_mode = response_mode
        self.diagnostic_quality = diagnostic_quality
        self.mock_oracle_result = mock_oracle_result
        self.result_id_start = result_id_start
        self.result_count = result_count

    def execute(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Execute request and return simulated response."""
        operation = request.get("operation", "unknown")

        if self.response_mode == ResponseMode.SUCCESS:
            # Generate results with IDs
            data = [
                {"id": self.result_id_start + i, "score": 0.9 - i * 0.1}
                for i in range(self.result_count)
            ]
            return {
                "status": "success",
                "data": data,
                "operation": operation
            }
        # ... other modes unchanged
```

---

## Updated Triage Type-4 Logic

```python
# OLD (Phase 2) - mock oracle placeholder
if result.oracle_results and any(not o.passed for o in result.oracle_results):
    return Type-4  # Simulated via mock oracle

# NEW (Phase 3) - actual oracle validation
if result.oracle_results and any(not o.passed for o in result.oracle_results):
    # Check which oracles failed
    failed_oracles = [o for o in result.oracle_results if not o.passed]
    return TriageResult(
        case_id=case.case_id,
        run_id=result.run_id,
        final_type=BugType.TYPE_4,
        input_validity=input_validity.value,
        observed_outcome=result.observed_outcome.value,
        precondition_pass=True,  # RED-LINE verified
        rationale=f"Semantic violation: {', '.join(o.oracle_id for o in failed_oracles)}"
    )
```

---

## Directory Layout (Run Output)

```
runs/
  run-001/
    run_metadata.json          # Run info, config, env
    cases.jsonl                # TestCase snapshots (what was executed)
    execution_results.jsonl    # One JSON per ExecutionResult
    triage_report.json         # TriageResult[] (bugs only)
    evidence.json              # Optional: EvidenceBundle
```

---

## Verification Commands

```bash
# Run Phase 3 mock flow
python scripts/run_phase3.py --output-dir runs/test

# Run all tests
pytest tests/unit/ -v

# E2E test
python -c "
from casegen.generators.instantiator import load_templates, instantiate_all
from contracts.core.loader import get_default_contract
from contracts.db_profiles.loader import load_profile
from pipeline.preconditions import PreconditionEvaluator
from adapters.mock import MockAdapter, ResponseMode
from oracles.write_read_consistency import WriteReadConsistency
from oracles.filter_strictness import FilterStrictness
from pipeline.executor import Executor
from pipeline.triage import Triage
from evidence.writer import EvidenceWriter

templates = load_templates()
cases = instantiate_all(templates, {'collection': 'test', 'k': 10})
contract = get_default_contract()
profile = load_profile('contracts/db_profiles/milvus_profile.yaml')

# Runtime context with collections and connection state
runtime_context = {
    'collections': ['test', 'prod'],
    'indexed_collections': ['test'],
    'connected': True,
    'target_collection': 'test'
}

precond = PreconditionEvaluator(contract, profile, runtime_context)
adapter = MockAdapter(ResponseMode.SUCCESS)
oracles = [WriteReadConsistency(), FilterStrictness()]  # Stateless
executor = Executor(adapter, precond, oracles)  # Manages mock_state and result IDs
triage = Triage()

results = executor.execute_batch(cases)
triage_results = [triage.classify(c, r) for c, r in zip(cases, results)]

writer = EvidenceWriter()
run_dir = writer.create_run_dir('test')
writer.write_all(run_dir, {}, cases, results, triage_results)
print(f'Evidence written to {run_dir}')
"
```

---

## Summary

| Category | Files | Key Point |
|----------|-------|-----------|
| Preconditions | 1 | PreconditionEvaluator (contract-aware, runtime checks) |
| Evidence | 2 | writer.py, __init__.py |
| Oracles | 4 | base.py, write_read_consistency.py, filter_strictness.py, __init__.py |
| Pipeline | 2 | triage.py (upgraded), executor.py (oracle support) |
| Scripts | 1 | run_phase3.py (full flow with evidence) |
| Tests | 4 | test_preconditions, test_evidence_writer, test_oracles, e2e |
| Schemas | 1 | common.py (add check_type to GateTrace) |
| **Total New** | **14** | **Total Modified** | **5** | Methodological hardening |

---

## Acceptance Criteria

1. ✅ PreconditionEvaluator is contract-aware (uses CoreContract + DBProfile)
2. ✅ GateTrace.check_type distinguishes legality vs runtime checks
3. ✅ Runtime preconditions evaluated against runtime_context (not stubbed to True)
4. ✅ EvidenceWriter creates run-scoped directories with JSON artifacts (including cases.jsonl)
5. ✅ OracleBase interface defined with 2 concrete implementations
6. ✅ WriteReadConsistency consumes context.mock_state (stateless)
7. ✅ FilterStrictness validates ID subsets (not just counts)
8. ✅ Type-4 triggered by actual oracle failure (not mock placeholder)
9. ✅ Triage consumes oracle outputs in classification
10. ✅ No real database or LLM dependencies
11. ✅ All tests pass (including E2E)

---

## Risks / Design Tradeoffs

### Risk 1: PreconditionEvaluator complexity
**Tradeoff**: Contract-aware checks add complexity vs. Phase 2 GateStub
**Mitigation**: Keep mock simulation for runtime preconditions, no real checks yet

### Risk 2: Oracle state management
**Tradeoff**: WriteReadConsistency needs mock state to track writes
**Mitigation**: Simple in-memory dict per run, no persistence

### Risk 3: Evidence bloat
**Tradeoff**: Could create many files per run
**Mitigation**: Minimal JSON structure, no replay complexity

### Risk 4: Oracle execution order
**Tradeoff**: Oracles might depend on execution order
**Mitigation**: Phase 3 oracles are independent, no order dependencies

---

## Key Design Reminders

1. **precondition_pass is HARD constraint** for Type-3/4
2. **Abstract legality (contract) ≠ Runtime readiness (precondition)**
3. **Core contract (agnostic) ≠ DB profile (specific)**
4. **Type-4 from oracle failure, not mock placeholder**
5. **Evidence is run-scoped, not a complex replay system**
6. **YAGNI: minimal, research-oriented, not platform**
7. **GateTrace.check_type distinguishes legality vs runtime checks**
8. **Runtime preconditions evaluated against runtime_context, not stubbed**
9. **FilterStrictness validates ID subsets, not just counts**
10. **Oracles are stateless - executor manages context**

---

## Phase 3 Success Criteria

1. `scripts/run_phase3.py` runs successfully
2. Evidence directories created with correct structure (including cases.jsonl)
3. GateTrace entries include check_type field ("legality" or "runtime")
4. Runtime preconditions fail appropriately against runtime_context
5. Oracles validate and return OracleResult objects
6. FilterStrictness detects ID subset violations (not just count violations)
7. Triage correctly classifies Type-4 from oracle failures
8. All unit tests pass including E2E
9. No real DB or LLM dependencies
