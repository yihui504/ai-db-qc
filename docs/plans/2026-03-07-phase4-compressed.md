# Phase 4: Real Database Validation - Milvus Integration (Revised)

> **Upgrade Phase 3 mock skeleton to minimal real-database validation**

**Goal**: Runnable Milvus-based validation flow with evidence artifacts

**Architecture**: Single-target Milvus integration, adapter-owned runtime state, lightweight helper functions

**Tech Stack**: pymilvus v2.3.x, pytest, existing Phase 3 infrastructure

---

## Phase 4 Deliverables

### 1. MilvusAdapter
- Minimal Milvus adapter in `adapters/milvus_adapter.py`
- Implements: create_collection, insert, build_index, load, search, filtered_search
- Provides: `get_runtime_snapshot()` for PreconditionEvaluator
- Handles: connection management, error translation to ObservedOutcome

### 2. Runtime Snapshot Integration
- PreconditionEvaluator.load_runtime_snapshot() consumes real runtime snapshots
- Snapshot returned as simple dict (no separate EnvContext class)
- Separates adapter-owned state from precondition evaluation logic

### 3. Enhanced Oracles
- **WriteReadConsistency**: Extended to support count sanity + ID validation + optional content
- **FilterStrictness**: Lightweight pair execution helper in run script (no new PairExecutor class)
- Both oracles consume executor-managed context

### 4. Environment Fingerprinting
- Simple `Fingerprint` schema in existing schemas/evidence.py
- `capture_environment()` function in evidence/fingerprint.py
- EvidenceWriter includes fingerprint in run_metadata.json

### 5. Real Case Set
- 10-15 representative real cases in `casegen/templates/real_milvus_cases.yaml`
- Organized by category: legal+pass, illegal, legal-but-precondition-fail, oracle-evaluable

---

## File Checklist (8 new files, 5 modified)

### NEW FILES (8)

#### MilvusAdapter (1 file)
**`adapters/milvus_adapter.py`**
- `MilvusAdapter(AdapterBase)` class
- `__init__(connection_config: Dict)` - connects to Milvus
- `execute(request: Dict) -> Dict` - handles: create_collection, insert, build_index, load, search, filtered_search
- `get_runtime_snapshot() -> Dict` - returns dict with: collections, indexed_collections, loaded_collections, connected, memory_stats
- `health_check() -> bool` - connection verification
- `close()` - cleanup

#### Oracle Enhancements (1 file)
**`oracles/write_read_enhanced.py`** (or extend existing write_read_consistency.py)
- Helper functions for ID validation and optional content checks
- No new oracle class - extends existing WriteReadConsistency capabilities
- Functions: `validate_id_subset()`, `validate_content_match()`

#### Environment & Evidence (2 files)
**`evidence/fingerprint.py`**
- `Fingerprint` schema (pydantic BaseModel)
- `capture_environment(connection_config, adapter) -> Fingerprint` function
- Fields: os, python_version, pymilvus_version, milvus_version, hostname, timestamp, db_config

**`schemas/evidence.py`** (if not exists, or extend existing)
- Add `Fingerprint` model
- Add `RuntimeSnapshot` model (simple dict wrapper)

#### Real Case Set (1 file)
**`casegen/templates/real_milvus_cases.yaml`**
- 10-15 representative real cases
- Organized by category with comments:
  - `# Category: legal + precondition-pass`
  - `# Category: illegal`
  - `# Category: legal syntax but precondition-fail`
  - `# Category: oracle-evaluable legal cases`

#### Scripts (1 file)
**`scripts/run_phase4.py`**
- Main script for real Milvus execution
- Lightweight pair execution helper for FilterStrictness (no new class)
- Arguments: `--adapter {mock|milvus}`, `--host`, `--port`, `--output-dir`
- Captures fingerprint and writes evidence

#### Tests (3 files)
**`tests/unit/test_milvus_adapter.py`**
- Test MilvusAdapter operations (with mock pymilvus or real instance)
- Test get_runtime_snapshot returns correct structure
- Test error translation to ObservedOutcome

**`tests/integration/test_real_milvus_flow.py`**
- End-to-end: real Milvus with small case set
- Requires Milvus running (marked with @pytest.mark.integration)
- Validates full flow with real DB

**`tests/unit/test_fingerprint.py`**
- Test environment capture
- Test fingerprint serialization

### MODIFIED FILES (5)

**`pipeline/preconditions.py`** (MODIFIED)
- Add `load_runtime_snapshot(snapshot: Dict) -> None` method
- Updates runtime_context from snapshot dict
- Keep contract/profile-based logic unchanged

**`oracles/write_read_consistency.py`** (MODIFIED)
- Add `validate_ids: bool = True` parameter (default True for Phase 4)
- Add `validate_content: bool = False` parameter (optional, off by default)
- Extend validate() to support ID subset validation (beyond count)
- Add content validation framework (can stay minimal for Phase 4)

**`oracles/filter_strictness.py`** (MODIFIED)
- Add docstring noting pair-aware usage requirement
- No code changes - relies on script-level pair execution

**`evidence/writer.py`** (MODIFIED)
- Add `write_fingerprint(run_dir, fingerprint)` method
- Include environment fingerprint in run_metadata.json
- Add `write_runtime_snapshots(run_dir, snapshots)` for snapshot history

**`schemas/result.py`** (MODIFIED)
- Add `snapshot_id: str = ""` field to ExecutionResult
- Do NOT add write_history (belongs to context, not result)

---

## Architecture Flow (Phase 4)

```
1. Connect to Milvus → MilvusAdapter
   ↓
2. Capture environment fingerprint
   ↓
3. Load runtime snapshot → PreconditionEvaluator.load_runtime_snapshot(adapter.get_runtime_snapshot())
   ↓
4. Load real cases → list[TestCase]
   ↓
5. For each case (or pair for FilterStrictness):
   a. PreconditionEvaluator.evaluate(case) → (precondition_pass, gate_trace)
   b. MilvusAdapter.execute(request) → raw_response
   c. Build ExecutionResult (with snapshot_id)
   d. Executor updates context (write_history, unfiltered_result_ids)
   e. Oracles.validate(case, result, context) → list[OracleResult]
   f. Triage.classify(case, result) → TriageResult
   ↓
6. EvidenceWriter.write_all(run_dir)
   - run_metadata.json (includes fingerprint)
   - cases.jsonl
   - execution_results.jsonl
   - runtime_snapshots.jsonl
   - triage_report.json
   - fingerprint.json
```

---

## MilvusAdapter Design

```python
from typing import Any, Dict
from adapters.base import AdapterBase
from pymilvus import Collection, connections, utility

class MilvusAdapter(AdapterBase):
    """Minimal Milvus adapter for real database validation."""

    def __init__(self, connection_config: Dict[str, Any]):
        self.host = connection_config.get("host", "localhost")
        self.port = connection_config.get("port", 19530)
        self.alias = connection_config.get("alias", "default")
        self._connect()

    def _connect(self):
        """Establish connection to Milvus."""
        connections.connect(alias=self.alias, host=self.host, port=self.port)

    def execute(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Milvus operation."""
        operation = request.get("operation")
        params = request.get("params", {})

        try:
            if operation == "create_collection":
                return self._create_collection(params)
            elif operation == "insert":
                return self._insert(params)
            elif operation == "build_index":
                return self._build_index(params)
            elif operation == "load":
                return self._load(params)
            elif operation == "search":
                return self._search(params)
            elif operation == "filtered_search":
                return self._filtered_search(params)
            else:
                return {"status": "error", "error": f"Unknown operation: {operation}"}
        except Exception as e:
            return {"status": "error", "error": str(e), "operation": operation}

    def get_runtime_snapshot(self) -> Dict[str, Any]:
        """Get runtime state for PreconditionEvaluator.

        Returns simple dict (no EnvContext class).
        """
        snapshot = {
            "collections": [],
            "indexed_collections": [],
            "loaded_collections": [],
            "connected": True,
            "memory_stats": {}
        }

        try:
            snapshot["collections"] = utility.list_collections(using=self.alias)
            for col_name in snapshot["collections"]:
                col = Collection(col_name, using=self.alias)
                if col.indexes:
                    snapshot["indexed_collections"].append(col_name)
                if col.loaded:
                    snapshot["loaded_collections"].append(col_name)
        except Exception:
            snapshot["connected"] = False

        return snapshot

    def health_check(self) -> bool:
        """Check if Milvus is responsive."""
        try:
            return utility.get_server_version(using=self.alias) is not None
        except Exception:
            return False

    def close(self):
        """Close connection."""
        try:
            connections.disconnect(self.alias)
        except Exception:
            pass
```

---

## PreconditionEvaluator Enhancement

```python
# In pipeline/preconditions.py, add method:

def load_runtime_snapshot(self, snapshot: Dict[str, Any]) -> None:
    """Load runtime snapshot from adapter into runtime_context.

    Adapter owns the snapshot dict; PreconditionEvaluator consumes it.
    """
    self.runtime_context.update({
        "collections": snapshot.get("collections", []),
        "indexed_collections": snapshot.get("indexed_collections", []),
        "loaded_collections": snapshot.get("loaded_collections", []),
        "connected": snapshot.get("connected", False),
        "memory_stats": snapshot.get("memory_stats", {})
    })
```

---

## Enhanced WriteReadConsistency

```python
# Update oracles/write_read_consistency.py

class WriteReadConsistency(OracleBase):
    """Validate: written data can be read back.

    Phase 4: Supports count sanity + ID validation + optional content checks.
    """

    def __init__(
        self,
        validate_ids: bool = True,  # Phase 4 default: validate IDs
        validate_content: bool = False  # Optional: off by default
    ):
        self.validate_ids = validate_ids
        self.validate_content = validate_content

    def validate(
        self,
        case: TestCase,
        result: ExecutionResult,
        context: Dict[str, Any]
    ) -> OracleResult:
        """Validate write-read consistency."""
        write_history = context.get("write_history", [])

        if case.operation in [OperationType.SEARCH, OperationType.FILTERED_SEARCH]:
            collection = case.params.get("collection_name")

            # Collect written IDs from context (executor-managed)
            written_ids = set()
            for write_op in write_history:
                if write_op.get("collection_name") == collection:
                    written_ids.update(write_op.get("ids", []))

            if written_ids:
                result_ids = set()
                for item in result.response.get("data", []):
                    if "id" in item:
                        result_ids.add(item["id"])

                # Phase 4: ID validation (beyond count)
                if self.validate_ids and not result_ids.issubset(written_ids):
                    unexpected_ids = result_ids - written_ids
                    return OracleResult(
                        oracle_id="write_read_consistency",
                        passed=False,
                        metrics={"unexpected_ids": list(unexpected_ids)},
                        expected_relation="returned ⊆ written",
                        observed_relation=f"returned has IDs not in written: {unexpected_ids}",
                        explanation="Write-read consistency violated: unexpected IDs"
                    )

                # Optional content validation (future expansion)
                if self.validate_content:
                    # Basic content matching logic here
                    pass

        return OracleResult(
            oracle_id="write_read_consistency",
            passed=True,
            metrics={},
            explanation="Write-read consistency satisfied"
        )
```

---

## Environment Fingerprinting

```python
# evidence/fingerprint.py

import platform
import socket
from typing import Dict, Any
from datetime import datetime
from pydantic import BaseModel

class Fingerprint(BaseModel):
    """Environment fingerprint for reproducibility."""
    os: str
    python_version: str
    pymilvus_version: str
    milvus_version: str
    hostname: str
    timestamp: str
    db_config: Dict[str, Any]

def capture_environment(connection_config: Dict, adapter) -> Fingerprint:
    """Capture environment fingerprint."""
    import pymilvus
    from pymilvus import utility

    alias = connection_config.get("alias", "default")
    milvus_version = utility.get_server_version(using=alias)

    return Fingerprint(
        os=platform.platform(),
        python_version=platform.python_version(),
        pymilvus_version=pymilvus.__version__,
        milvus_version=milvus_version,
        hostname=socket.gethostname(),
        timestamp=datetime.now().isoformat(),
        db_config={
            "host": connection_config.get("host", "localhost"),
            "port": connection_config.get("port", 19530)
        }
    )
```

---

## Lightweight Pair Execution (in run script)

```python
# In scripts/run_phase4.py - simple helper function, no new class

def execute_filtered_pair(
    executor: Executor,
    unfiltered_case: TestCase,
    filtered_case: TestCase,
    run_id: str
) -> tuple[ExecutionResult, ExecutionResult, Dict[str, Any]]:
    """Execute unfiltered → filtered pair for FilterStrictness.

    Lightweight helper - no PairExecutor class needed.
    Returns (unfiltered_result, filtered_result, context).
    """
    # Execute unfiltered first
    unfiltered_result = executor.execute_case(unfiltered_case, run_id)

    # Extract IDs from unfiltered result
    unfiltered_ids = [
        item.get("id")
        for item in unfiltered_result.response.get("data", [])
        if "id" in item
    ]

    # Build context with unfiltered IDs
    context = {
        "unfiltered_result_ids": unfiltered_ids,
        "mock_state": executor.mock_state,
        "write_history": executor.write_history
    }

    # Execute filtered
    filtered_result = executor.execute_case(filtered_case, run_id)

    return unfiltered_result, filtered_result, context
```

---

## Directory Layout (Run Output - Phase 4)

```
runs/
  run-001/
    run_metadata.json          # Includes fingerprint
    cases.jsonl                # TestCase snapshots
    execution_results.jsonl    # One JSON per ExecutionResult
    runtime_snapshots.jsonl    # Runtime snapshots (NEW)
    triage_report.json         # TriageResult[] (bugs only)
    fingerprint.json           # Environment fingerprint (NEW)
```

---

## Verification Commands

```bash
# Run with real Milvus
python scripts/run_phase4.py \
  --adapter milvus \
  --host localhost \
  --port 19530 \
  --output-dir runs/phase4-real

# Run with mock (Phase 3 compatibility)
python scripts/run_phase4.py \
  --adapter mock \
  --output-dir runs/phase4-mock

# Integration tests
pytest tests/integration/test_real_milvus_flow.py -v -m integration

# Unit tests
pytest tests/unit/test_milvus_adapter.py -v
pytest tests/unit/test_fingerprint.py -v
```

---

## Real Case Set Structure

```yaml
# casegen/templates/real_milvus_cases.yaml

cases:
  # Category: legal + precondition-pass
  - case_id: "real-001"
    operation: "create_collection"
    params:
      collection_name: "test_collection"
      dimension: 128
      metric_type: "L2"
    expected_validity: "legal"
    required_preconditions: []
    oracle_refs: []

  - case_id: "real-002"
    operation: "insert"
    params:
      collection_name: "test_collection"
      vectors: [[0.1] * 128, [0.2] * 128]]
    expected_validity: "legal"
    required_preconditions: ["collection_exists"]
    oracle_refs: ["write_read_consistency"]

  # Category: illegal
  - case_id: "real-003"
    operation: "create_collection"
    params:
      collection_name: "test_collection"
      dimension: -1  # Illegal: negative dimension
      metric_type: "L2"
    expected_validity: "illegal"
    required_preconditions: []
    oracle_refs: []

  - case_id: "real-004"
    operation: "search"
    params:
      collection_name: "test_collection"
      vector: [0.1] * 64  # Wrong dimension
      top_k: 10
    expected_validity: "illegal"
    required_preconditions: []
    oracle_refs: []

  # Category: legal syntax but precondition-fail
  - case_id: "real-005"
    operation: "insert"
    params:
      collection_name: "nonexistent_collection"
      vectors: [[0.1] * 128]
    expected_validity: "legal"
    required_preconditions: ["collection_exists"]  # Will fail
    oracle_refs: []

  - case_id: "real-006"
    operation: "search"
    params:
      collection_name: "test_collection"
      vector: [0.1] * 128
      top_k: 10
    expected_validity: "legal"
    required_preconditions: ["index_built", "index_loaded"]  # Will fail if no index
    oracle_refs: []

  # Category: oracle-evaluable legal cases
  - case_id: "real-007-unfiltered"
    operation: "search"
    params:
      collection_name: "test_collection"
      vector: [0.1] * 128
      top_k: 10
    expected_validity: "legal"
    required_preconditions: ["collection_exists", "index_built", "index_loaded"]
    oracle_refs: []
    pair_with: "real-007-filtered"

  - case_id: "real-007-filtered"
    operation: "filtered_search"
    params:
      collection_name: "test_collection"
      vector: [0.1] * 128
      top_k: 10
      filter: "field > 100"
    expected_validity: "legal"
    required_preconditions: ["collection_exists", "index_built", "index_loaded"]
    oracle_refs: ["filter_strictness"]
    pair_with: "real-007-unfiltered"
```

---

## Summary

| Category | Files | Key Point |
|----------|-------|-----------|
| MilvusAdapter | 1 | milvus_adapter.py (no milvus_client.py) |
| Oracle Helpers | 1 | write_read_enhanced.py (helper functions, no new oracle class) |
| Evidence | 2 | fingerprint.py, schemas/evidence.py (no env_context.py) |
| Real Cases | 1 | real_milvus_cases.yaml (categorized) |
| Scripts | 1 | run_phase4.py (with lightweight pair helper) |
| Tests | 3 | milvus_adapter, integration, fingerprint |
| **Total New** | **8** | **Total Modified** | **5** | Minimal real DB validation |

---

## Acceptance Criteria

1. ✅ MilvusAdapter implements 8 operations (no milvus_client.py separation)
2. ✅ PreconditionEvaluator.load_runtime_snapshot() takes simple dict (no EnvContext class)
3. ✅ FilterStrictness works with lightweight pair helper in script (no PairExecutor class)
4. ✅ WriteReadConsistency supports count + ID + optional content (single file)
5. ✅ Environment fingerprint captured and stored (simple schema, no env_context.py)
6. ✅ Real case set categorized by type (4 categories)
7. ✅ Executor manages write_history in context (not in ExecutionResult)
8. ✅ Type-3/4 still require precondition_pass=true
9. ✅ All tests pass (unit + integration)
10. ✅ No second database, no platform expansion

---

## Risks / Design Tradeoffs

### Risk 1: Milvus connection lifecycle
**Tradeoff**: Adapter owns connection, needs explicit cleanup
**Mitigation**: Provide close() method, document usage pattern

### Risk 2: FilterStrictness pair ordering
**Tradeoff**: Script-level pair execution vs dedicated class
**Mitigation**: Clear documentation in run script, simple helper function

### Risk 3: WriteReadConsistency complexity
**Tradeoff**: Adding ID/content validation may grow complex
**Mitigation**: Keep content validation optional/off, clear feature flags

### Risk 4: Runtime snapshot freshness
**Tradeoff**: Snapshot may become stale during long runs
**Mitigation**: Document snapshot refresh strategy, call load_runtime_snapshot() as needed

### Risk 5: Integration test dependency
**Tradeoff**: Real Milvus required for integration tests
**Mitigation**: Use pytest marks, keep unit tests independent

---

## Key Design Reminders

1. **No new core components** - extend existing, don't add PairExecutor or EnvContext classes
2. **Single oracle path** - strengthen write_read_consistency.py, don't add content_consistency.py
3. **Context, not result** - write_history belongs to executor context, not ExecutionResult
4. **Lightweight helpers** - pair execution as simple function in script
5. **Simple schemas** - use basic dicts or existing evidence schemas
6. **Categorized cases** - organize by type in YAML with comments
7. **Minimal over comprehensive** - 10-15 real cases, focused validation
8. **Publishable, not platform** - research prototype, not production system

---

## Phase 4 Success Criteria

1. `scripts/run_phase4.py --adapter milvus` runs successfully with real Milvus
2. MilvusAdapter handles all operations in single file
3. PreconditionEvaluator consumes simple dict snapshot
4. Lightweight pair helper executes FilterStrictness pairs
5. WriteReadConsistency validates IDs (single file, count+ID+optional content)
6. Environment fingerprint captured and stored
7. Real case set categorized (4 types, 10-15 cases)
8. Integration tests pass with real Milvus
9. Evidence includes fingerprint and runtime snapshots
10. Phase 3 mock flow still works
11. No second database, no platform expansion
