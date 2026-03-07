# seekdb Integration: Minimal Two-Stage Plan

> **Status**: Revised for result-oriented progress
> **Updated**: 2026-03-07
> **Philosophy**: Maximize bug yield, minimize architecture expansion

## Overview

**Previous approach**: Large-scale expansion with multiple new oracles (4-6 weeks)
**Revised approach**: Two-stage minimal integration, S1 must prove value before S2

---

## Stage S1: Minimal seekdb Bring-Up (Week 1-2)

### Goal

**Get seekdb connected, run existing pipeline, produce first real bug candidates.**

### Success Criteria (Must Earn Right to S2)

1. **Connection**: seekdb adapter successfully executes operations
2. **Coverage**: Existing pipeline (triage, oracles) runs on seekdb
3. **Bug Yield**: At least **1 high-quality issue-ready real bug candidate** OR **at least 2 taxonomy-consistent, cross-database differential cases with clear evidence**
4. **Stability**: No crashes, clean evidence output

**If success criteria not met**: Re-evaluate approach before proceeding to S2.

### What S1 Does

#### 1. Minimal seekdb Adapter (~200 lines)

**File**: `adapters/seekdb_adapter.py`

```python
"""Minimal seekdb adapter for AI-native database testing."""

from __future__ import annotations

import requests
from typing import Any, Dict
from adapters.base import AdapterBase
from schemas.common import ObservedOutcome


class SeekDBAdapter(AdapterBase):
    """Minimal adapter for seekdb AI-native search database.

    Focus: Get basic operations working with minimal complexity.
    Reuses: existing triage, oracles, evidence pipeline.
    """

    def __init__(
        self,
        api_endpoint: str,
        api_key: str,
        collection: str = "default",
        timeout: int = 30
    ):
        self.api_endpoint = api_endpoint.rstrip("/")
        self.api_key = api_key
        self.collection = collection
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })

    def execute(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Execute request against seekdb.

        Maps generic operations to seekdb API calls.
        """
        operation = request.get("operation", "")
        params = request.get("params", {})

        try:
            if operation == "search":
                return self._search(params)
            elif operation == "insert":
                return self._insert(params)
            elif operation == "delete":
                return self._delete(params)
            elif operation == "create_collection":
                return self._create_collection(params)
            else:
                return self._error(f"Unknown operation: {operation}")
        except requests.RequestException as e:
            return self._error(f"Network error: {e}")
        except Exception as e:
            return self._error(f"Unexpected error: {e}")

    def _search(self, params: Dict) -> Dict[str, Any]:
        """Execute search operation."""
        # Map to seekdb's hybrid or vector search
        query_vector = params.get("vector")
        query_text = params.get("query_text", "")

        if query_vector and query_text:
            # Hybrid search
            payload = {
                "collection": self.collection,
                "query": query_text,
                "vector": query_vector,
                "limit": params.get("top_k", 10)
            }
            endpoint = "/search/hybrid"
        elif query_vector:
            # Pure vector search
            payload = {
                "collection": self.collection,
                "vector": query_vector,
                "limit": params.get("top_k", 10)
            }
            endpoint = "/search/vector"
        else:
            # Pure keyword search
            payload = {
                "collection": self.collection,
                "query": query_text,
                "limit": params.get("top_k", 10)
            }
            endpoint = "/search/keyword"

        response = self.session.post(
            f"{self.api_endpoint}{endpoint}",
            json=payload,
            timeout=self.timeout
        )

        if response.status_code == 200:
            data = response.json()
            return {
                "status": "success",
                "data": data.get("results", []),
                "operation": "search"
            }
        else:
            return self._error_from_response(response)

    def _insert(self, params: Dict) -> Dict[str, Any]:
        """Insert documents."""
        payload = {
            "collection": self.collection,
            "documents": params.get("documents", [])
        }

        response = self.session.post(
            f"{self.api_endpoint}/documents",
            json=payload,
            timeout=self.timeout
        )

        if response.status_code in [200, 201]:
            return {
                "status": "success",
                "data": response.json(),
                "operation": "insert"
            }
        else:
            return self._error_from_response(response)

    def _delete(self, params: Dict) -> Dict[str, Any]:
        """Delete documents."""
        response = self.session.delete(
            f"{self.api_endpoint}/documents",
            json={"ids": params.get("ids", [])},
            timeout=self.timeout
        )

        if response.status_code == 200:
            return {
                "status": "success",
                "data": {"deleted": len(params.get("ids", []))},
                "operation": "delete"
            }
        else:
            return self._error_from_response(response)

    def _create_collection(self, params: Dict) -> Dict[str, Any]:
        """Create collection."""
        payload = {
            "name": params.get("collection_name", self.collection),
            "dimension": params.get("dimension", 128)
        }

        response = self.session.put(
            f"{self.api_endpoint}/collections",
            json=payload,
            timeout=self.timeout
        )

        if response.status_code in [200, 201]:
            return {
                "status": "success",
                "data": response.json(),
                "operation": "create_collection"
            }
        else:
            return self._error_from_response(response)

    def _error(self, message: str) -> Dict[str, Any]:
        """Build error response."""
        return {
            "status": "error",
            "error": message,
            "operation": "unknown"
        }

    def _error_from_response(self, response) -> Dict[str, Any]:
        """Build error response from HTTP response."""
        try:
            error_data = response.json()
            error_msg = error_data.get("message", error_data.get("error", f"HTTP {response.status_code}"))
        except:
            error_msg = f"HTTP {response.status_code}: {response.text}"

        return {
            "status": "error",
            "error": error_msg,
            "operation": "unknown",
            "status_code": response.status_code
        }

    def health_check(self) -> bool:
        """Check if seekdb is accessible."""
        try:
            response = self.session.get(
                f"{self.api_endpoint}/health",
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
```

**Key Design Decisions**:
- Maps existing operations (search, insert, delete) to seekdb API
- Handles hybrid, vector, and keyword search transparently
- Minimal error handling—just extract error messages
- No seekdb-specific logic

#### 2. Minimal seekdb Profile (~80 lines)

**File**: `contracts/db_profiles/seekdb_profile.yaml`

```yaml
profile_name: seekdb_minimal
profile_version: "1.0.0"
description: Minimal profile for seekdb AI-native database

supported_operations:
  - search
  - insert
  - delete
  - create_collection

# Reuse existing core contract operations
# No seekdb-specific operation definitions needed for S1

capabilities:
  hybrid_search: true
  multi_model: true
  filtering: true

# Basic configuration
default_top_k: 10
default_dimension: 1536  # Common embedding dimension
max_batch_size: 100
```

**Key Design Decisions**:
- Reuses existing `default_contract.yaml` operations
- No new operation definitions
- Just capability flags and basic config

#### 3. Reuse Existing Framework Components

**No new oracles in S1**—reuse existing:
- `FilterStrictness` (works with any search results)
- `WriteReadConsistency` (works with any insert/delete)
- `Monotonicity` (works with any top_k search)

**No new test templates in S1**—reuse existing case families with minimal parameter mapping:
- `basic_templates.yaml` (generic cases)
- `real_milvus_cases.yaml` (parameter boundaries)
- `test_phase5_comprehensive.yaml` (diagnostic variation)

**Template reuse approach**: Reuse existing case families, with a thin parameter mapping layer where needed. Don't force Milvus-shaped parameters directly onto seekdb if they're incompatible—the adapter handles the mapping.

#### 4. High-Yield Case Families (S1 Focus)

**Family 1: Parameter Boundary / Constraint Handling**

Reuse existing templates with seekdb:
- Invalid `top_k` values (0, -1, 1000000)
- Invalid `dimension` values (-1, 99999)
- Invalid `metric_type` values
- Empty/null vectors
- Malformed filter expressions

**Expected findings**:
- **Type 1**: Invalid parameters accepted (seekdb validation weakness)
- **Type 2**: Invalid parameters rejected with poor diagnostics
- **Type 2.PF**: Contract-valid but precondition fails

**Why high-yield**: seekdb has different validation than Milvus—likely finds Type 1 bugs.

**Family 2: Diagnostic Quality**

Reuse existing diagnostic variation:
- Good diagnostic: "Parameter 'dimension' must be positive"
- Poor diagnostic: "Invalid parameter", "Operation failed"
- Edge cases: Empty vectors, null queries, malformed filters

**Expected findings**:
- **Triage differentiation**: Diagnostic mode excludes good-diagnostic cases, naive includes them
- **Database comparison**: seekdb vs Milvus diagnostic quality differences

**Why high-yield**: Shows differential results across databases.

**Family 3: Precondition / State Handling**

Reuse existing precondition cases:
- Search on non-existent collection
- Insert without schema creation
- Delete non-existent documents
- Search before index built
- Empty collection searches

**Expected findings**:
- **Type 2.PF**: Precondition fails with poor diagnostics
- **Type 2**: State errors without clear explanation
- **Database comparison**: seekdb vs Milvus precondition strictness

**Why high-yield**: seekdb has different state management—likely finds Type 2.PF bugs.

### S1 File Count

| File | Lines | Purpose |
|------|-------|---------|
| `adapters/seekdb_adapter.py` | ~200 | Minimal adapter |
| `contracts/db_profiles/seekdb_profile.yaml` | ~80 | Minimal profile |
| **Total NEW** | **~280** | **S1 only** |

### S1 Timeline

| Week | Tasks |
|------|-------|
| 1 | Adapter implementation, basic testing |
| 2 | Profile setup, first bug-mining runs |

### S1 Bug-Mining Campaign

**Script**: `scripts/run_seekdb_s1.py`

```python
"""Run Stage S1 bug-mining campaign on seekdb."""

from adapters.seekdb_adapter import SeekDBAdapter
from contracts.core.loader import get_default_contract
from contracts.db_profiles.loader import load_profile
from casegen.generators.instantiator import load_templates, instantiate_all
from pipeline.preconditions import PreconditionEvaluator
from pipeline.executor import Executor
from pipeline.triage import Triage
from evidence.writer import EvidenceWriter
from oracles.write_read_consistency import WriteReadConsistency
from oracles.filter_strictness import FilterStrictness
from oracles.monotonicity import Monotonicity

def run_seekdb_s1():
    # Configuration
    config = {
        "api_endpoint": os.getenv("SEEKDB_API_ENDPOINT"),
        "api_key": os.getenv("SEEKDB_API_KEY"),
        "collection": "test_collection"
    }

    # Initialize
    adapter = SeekDBAdapter(**config)
    contract = get_default_contract()
    profile = load_profile("contracts/db_profiles/seekdb_profile.yaml")
    runtime_context = {
        "collections": ["test_collection"],
        "indexed_collections": [],
        "loaded_collections": [],
        "connected": True
    }

    precond = PreconditionEvaluator(contract, profile, runtime_context)
    oracles = [WriteReadConsistency(), FilterStrictness(), Monotonicity()]
    executor = Executor(adapter, precond, oracles)
    triage = Triage()
    writer = EvidenceWriter()

    # Load existing templates (reuse!)
    templates = load_templates("casegen/templates/basic_templates.yaml")
    templates.extend(load_templates("casegen/templates/real_milvus_cases.yaml"))

    cases = instantiate_all(templates, {"collection": "test_collection"})

    # Execute
    results = []
    for case in cases:
        try:
            result = executor.execute_case(case, run_id="seekdb_s1")
            results.append(result)
        except Exception as e:
            print(f"Case {case.case_id} failed: {e}")
            continue

    # Classify
    triage_results = []
    for case in cases:
        result = next((r for r in results if r.case_id == case.case_id), None)
        if result:
            triage_result = triage.classify(case, result, naive=False)
            triage_results.append(triage_result)

    # Write evidence
    run_dir = writer.create_run_dir("seekdb_s1")
    writer.write_all(run_dir, {}, cases, results, triage_results)

    # Report
    bug_count = sum(1 for t in triage_results if t is not None)
    print(f"S1 Campaign: {bug_count} bugs found from {len(cases)} cases")

    return bug_count > 0
```

**Campaign variations**:
1. `seekdb_s1_diag` - Diagnostic mode
2. `seekdb_s1_naive` - Naive mode
3. Compare with Milvus results for differential analysis

### S1 Success Criteria (Must Meet Before S2)

1. ✅ **Connection**: seekdb adapter executes operations successfully
2. ✅ **Coverage**: All existing oracles work on seekdb results
3. ✅ **Bug Yield**: ≥ 1 high-quality issue-ready real bug candidate OR ≥ 2 taxonomy-consistent, cross-database differential cases with clear evidence
4. ✅ **Evidence Quality**: Clean triage reports, consistent with taxonomy

**If S1 fails**: Debug and retry before considering S2.

---

## Stage S2: seekdb-Specific Semantic Extension (Week 3+)

### Condition

**S2 ONLY proceeds if S1 meets all success criteria.**

### Goal

**Add seekdb-specific semantic validation that exploits AI-native features.**

### What S2 Does

#### 1. Hybrid Search Oracle (~200 lines)

**File**: `oracles/hybrid_search_consistency.py`

Detects:
- Fusion monotonicity violations (hybrid score < max(vector, keyword))
- Mode coverage gaps (hybrid misses pure mode results)
- Inconsistent fusion across different `hybrid_alpha` values

#### 2. Multi-Model Consistency Oracle (~150 lines)

**File**: `oracles/multimodel_consistency.py`

Detects:
- Orphaned cross-modal references (text deleted, vector remains)
- Schema constraint violations
- Cascade failures

#### 3. seekdb-Specific Templates (~400 lines)

**Files**:
- `casegen/templates/seekdb_hybrid.yaml` - Hybrid search cases
- `casegen/templates/seekdb_multimodel.yaml` - Multi-model cases

### S2 Timeline

| Week | Tasks |
|------|-------|
| 3 | Hybrid search oracle + templates |
| 4 | Multi-model oracle + templates |
| 5+ | Bug-mining campaigns with new oracles |

### S2 Success Criteria

1. **Oracle Effectiveness**: New oracles detect violations
2. **Unique Bugs**: seekdb-specific bugs not found in S1
3. **Differential Value**: Results show AI-native vs classic vector DB differences

---

## Comparison: Previous vs Revised Plan

| Aspect | Previous Plan | Revised Plan |
|--------|---------------|--------------|
| **Timeline** | 4-6 weeks | 1-2 weeks (S1) + 3+ weeks (S2) |
| **New Code** | ~1450 lines | ~280 lines (S1) |
| **New Oracles** | 2 new oracles | 0 new (S1), 2 new (S2) |
| **New Templates** | 4 template files | 0 new (S1), reuse existing |
| **Architecture** | Stable | Stable (no changes) |
| **Focus** | Build subsystem | **Find bugs** |

---

## S1 First Actions

### Immediate Next Steps

1. **Create minimal adapter**: `adapters/seekdb_adapter.py`
2. **Create minimal profile**: `contracts/db_profiles/seekdb_profile.yaml`
3. **Connect to real seekdb instance**: Verify adapter works against real seekdb
4. **Run S1 campaign**: Reuse existing templates and oracles
5. **Evaluate success criteria**: Decide whether S2 is warranted

### Decision Point

**After S1 completes, decide**:
- ✅ **S2 warranted**: If ≥1 high-quality issue-ready bug OR ≥2 taxonomy-consistent cross-database differential cases
- ❌ **S2 postponed**: If S1 shows seekdb integration is too complex
- ❌ **S2 redesigned**: If S1 reveals different high-yield opportunities

---

## Summary

**Stage S1** (1-2 weeks):
- Minimal seekdb adapter (~200 lines)
- Minimal seekdb profile (~80 lines)
- **No new oracles**
- **No new templates** (reuse existing)
- Reuse existing framework components
- Focus: parameter boundaries, diagnostic quality, preconditions
- **Goal**: Get seekdb connected, produce first bug candidates

**Stage S2** (3+ weeks, ONLY if S1 succeeds):
- Hybrid search consistency oracle
- Multi-model consistency oracle
- seekdb-specific templates
- **Goal**: Exploit AI-native features for unique findings

**Philosophy**: Result-oriented progress, not architecture expansion. S1 must prove value before S2.
