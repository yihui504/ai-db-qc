# seekdb Integration Plan

> **Status**: Ready for Phase 3 implementation
> **Updated**: 2026-03-07
> **Timeline**: 4-6 weeks

## Overview

This plan details the minimal work required to add seekdb as a first-class AI-native database target, while keeping the architecture stable.

## Why seekdb: Key Differentiators

| Feature | Classic Vector DBs (Milvus/Qdrant) | seekdb (AI-Native) |
|---------|----------------------------------------|-------------------|
| Search Mode | Pure vector similarity | Hybrid (vector + keyword) |
| Data Model | Single-modal vectors | Multi-model (text, vector, image) |
| AI Pipeline | External to database | In-database embeddings/reranking |
| Query Complexity | Simple search | Multi-stage workflows |

**Research relevance**: seekdb tests the framework on **AI-native database complexity**, not just vector search.

---

## Phase 1: seekdb Adapter (Week 1-2)

### File: `adapters/seekdb_adapter.py`

**Minimal Implementation** (~400 lines):

```python
"""seekdb adapter for AI-native database testing."""

from __future__ import annotations

import requests
from typing import Any, Dict, Optional
from adapters.base import AdapterBase
from schemas.common import ObservedOutcome


class SeekDBAdapter(AdapterBase):
    """Adapter for seekdb AI-native search database."""

    def __init__(
        self,
        api_endpoint: str,
        api_key: str,
        collection: str,
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
        """Execute a request against seekdb."""
        operation = request.get("operation", "")
        params = request.get("params", {})

        try:
            if operation == "hybrid_search":
                return self._hybrid_search(params)
            elif operation == "insert":
                return self._insert(params)
            elif operation == "delete":
                return self._delete(params)
            elif operation == "create_schema":
                return self._create_schema(params)
            else:
                return self._error_response(
                    f"Unknown operation: {operation}",
                    "unsupported_operation"
                )
        except requests.exceptions.RequestException as e:
            return self._error_response(str(e), "network_error")
        except Exception as e:
            return self._error_response(f"Unexpected error: {e}", "internal_error")

    def _hybrid_search(self, params: Dict) -> Dict[str, Any]:
        """Execute hybrid search (vector + keyword)."""
        # Map generic params to seekdb API
        payload = {
            "collection": self.collection,
            "query": params.get("query_text", ""),
            "vector": params.get("query_vector", []),
            "hybrid_alpha": params.get("hybrid_alpha", 0.5),
            "limit": params.get("top_k", 10),
            "filters": params.get("filters", {})
        }

        response = self.session.post(
            f"{self.api_endpoint}/search/hybrid",
            json=payload,
            timeout=self.timeout
        )
        response.raise_for_status()

        data = response.json()
        return {
            "status": "success",
            "data": data.get("results", []),
            "operation": "hybrid_search"
        }

    def _insert(self, params: Dict) -> Dict[str, Any]:
        """Insert multi-model data."""
        payload = {
            "collection": self.collection,
            "documents": params.get("documents", [])
        }

        response = self.session.post(
            f"{self.api_endpoint}/documents",
            json=payload,
            timeout=self.timeout
        )
        response.raise_for_status()

        return {
            "status": "success",
            "data": response.json(),
            "operation": "insert"
        }

    def _delete(self, params: Dict) -> Dict[str, Any]:
        """Delete documents."""
        doc_ids = params.get("ids", [])

        response = self.session.delete(
            f"{self.api_endpoint}/documents",
            json={"ids": doc_ids},
            timeout=self.timeout
        )
        response.raise_for_status()

        return {
            "status": "success",
            "data": {"deleted": len(doc_ids)},
            "operation": "delete"
        }

    def _create_schema(self, params: Dict) -> Dict[str, Any]:
        """Create schema with multi-model fields."""
        schema_def = {
            "name": params.get("schema_name", self.collection),
            "fields": params.get("fields", [])
        }

        response = self.session.put(
            f"{self.api_endpoint}/schemas",
            json=schema_def,
            timeout=self.timeout
        )
        response.raise_for_status()

        return {
            "status": "success",
            "data": response.json(),
            "operation": "create_schema"
        }

    def _error_response(
        self,
        error_message: str,
        error_code: str
    ) -> Dict[str, Any]:
        """Build standardized error response."""
        return {
            "status": "error",
            "error": error_message,
            "error_code": error_code,
            "operation": "unknown"
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

    def get_runtime_snapshot(self) -> Dict[str, Any]:
        """Get current database state for precondition checking."""
        try:
            response = self.session.get(
                f"{self.api_endpoint}/collections/{self.collection}",
                timeout=5
            )
            response.raise_for_status()
            collection_info = response.json()

            return {
                "collections": [self.collection],
                "indexed_collections": [self.collection] if collection_info.get("indexed") else [],
                "loaded_collections": [self.collection] if collection_info.get("loaded") else [],
                "connected": True,
                "schema_fields": collection_info.get("fields", {}),
                "supported_features": collection_info.get("features", [])
            }
        except:
            return {
                "collections": [],
                "indexed_collections": [],
                "loaded_collections": [],
                "connected": False,
                "schema_fields": {},
                "supported_features": []
            }
```

**Key Implementation Notes**:
- Uses requests library (no SDK dependency)
- Maps generic operations to seekdb-specific API calls
- Standardizes error responses for triage
- Provides runtime snapshot for preconditions

---

## Phase 2: seekdb Contract & Profile (Week 2)

### File: `contracts/core/default_contract.yaml` (Add seekdb operations)

```yaml
# ... existing operations ...

  # seekdb-specific operations
  hybrid_search:
    operation_type: hybrid_search
    parameters:
      query_text:
        name: query_text
        type: str
        required: true
      query_vector:
        name: query_vector
        type: list
        required: false
      hybrid_alpha:
        name: hybrid_alpha
        type: float
        required: false
        min_value: 0.0
        max_value: 1.0
      top_k:
        name: top_k
        type: int
        required: true
        min_value: 1
      filters:
        name: filters
        type: dict
        required: false
    required_preconditions:
      - collection_exists
      - collection_loaded

  create_schema:
    operation_type: create_schema
    parameters:
      schema_name:
        name: schema_name
        type: str
        required: true
      fields:
        name: fields
        type: list
        required: true
    required_preconditions:
      - connection_active

  ai_embedding:
    operation_type: ai_embedding
    parameters:
      text:
        name: text
        type: str
        required: true
      model:
        name: model
        type: str
        required: false
    required_preconditions:
      - connection_active
      - ai_service_available
```

### File: `contracts/db_profiles/seekdb_profile.yaml`

```yaml
profile_name: seekdb_default
profile_version: "1.0.0"
description: Default profile for seekdb AI-native search database

supported_operations:
  - search
  - hybrid_search
  - insert
  - delete
  - create_schema
  - ai_embedding
  - ai_rerank

capabilities:
  hybrid_search: true
  multi_model: true
  ai_workflows: true
  filtering: true
  ranking: true

operation_specifics:
  hybrid_search:
    default_hybrid_alpha: 0.5
    supported_filters: ["keyword", "field", "range"]
    fusion_methods: ["linear", "rrf", "weighted"]

  multi_model:
    supported_types: ["text", "vector", "image"]
    cross_modal_reference: true
    cascade_behavior: "delete_propagates"
```

---

## Phase 3: seekdb-Specific Oracles (Week 3-4)

### Oracle 1: Hybrid Search Consistency

**File**: `oracles/hybrid_search_consistency.py`

```python
"""Hybrid search consistency oracle for seekdb."""

from __future__ import annotations
from typing import Any, Dict
from oracles.base import OracleBase
from schemas.case import TestCase
from schemas.result import ExecutionResult, OracleResult


class HybridSearchConsistency(OracleBase):
    """Validate hybrid search fusion properties.

    Checks that hybrid search results are consistent with:
    1. Pure vector search ranking
    2. Pure keyword search ranking
    3. Monotonicity of hybrid_alpha parameter
    """

    def __init__(self, vector_adapter, keyword_adapter):
        """Initialize with adapters for pure mode comparison."""
        self.vector_adapter = vector_adapter
        self.keyword_adapter = keyword_adapter
        self._pure_vector_results = {}
        self._pure_keyword_results = {}

    def validate(
        self,
        case: TestCase,
        result: ExecutionResult,
        context: Dict[str, Any]
    ) -> OracleResult:
        """Validate hybrid search consistency."""
        operation = case.operation

        # Store results for comparison
        if operation.value == "search":
            # Pure mode results stored for later comparison
            if case.params.get("search_mode") == "vector":
                self._pure_vector_results[case.case_id] = self._extract_ids(result)
            elif case.params.get("search_mode") == "keyword":
                self._pure_keyword_results[case.case_id] = self._extract_ids(result)
            return OracleResult(oracle_id="hybrid_search_consistency", passed=True)

        if operation.value != "hybrid_search":
            return OracleResult(oracle_id="hybrid_search_consistency", passed=True, explanation="N/A")

        # Check 1: Mode coverage (hybrid should include results from both pure modes)
        hybrid_ids = set(self._extract_ids(result))
        vector_ids = set(context.get("pure_vector_ids", []))
        keyword_ids = set(context.get("pure_keyword_ids", []))

        # Violation: Hybrid results don't include high-scoring vector results
        if vector_ids and not hybrid_ids.issubset(vector_ids.union(keyword_ids)):
            unexpected_ids = hybrid_ids - vector_ids - keyword_ids
            return OracleResult(
                oracle_id="hybrid_search_consistency",
                passed=False,
                metrics={"unexpected_ids": list(unexpected_ids)},
                expected_relation="hybrid ⊆ vector ∪ keyword",
                observed_relation=f"hybrid has IDs not in pure modes: {list(unexpected_ids)}",
                explanation="Hybrid search produced results not present in either pure mode"
            )

        # Check 2: Fusion monotonicity (same result shouldn't have worse score than pure modes)
        hybrid_scores = self._extract_scores(result)
        fusion_violations = self._check_fusion_monotonicity(hybrid_scores, context)

        if fusion_violations:
            return OracleResult(
                oracle_id="hybrid_search_consistency",
                passed=False,
                metrics={"violations": fusion_violations},
                expected_relation="score_hybrid >= max(score_vector, score_keyword)",
                observed_relation="Some results have worse hybrid score",
                explanation="Hybrid fusion violates monotonicity property"
            )

        return OracleResult(
            oracle_id="hybrid_search_consistency",
            passed=True,
            explanation="Hybrid search is consistent with pure modes"
        )

    def _extract_ids(self, result: ExecutionResult) -> list:
        """Extract result IDs."""
        return [item.get("id") for item in result.response.get("data", []) if "id" in item]

    def _extract_scores(self, result: ExecutionResult) -> dict:
        """Extract result scores."""
        scores = {}
        for item in result.response.get("data", []):
            if "id" in item and "score" in item:
                scores[item["id"]] = item["score"]
        return scores

    def _check_fusion_monotonicity(self, hybrid_scores: dict, context: dict) -> list:
        """Check if fusion violates monotonicity."""
        violations = []
        vector_scores = context.get("pure_vector_scores", {})
        keyword_scores = context.get("pure_keyword_scores", {})

        for doc_id, hybrid_score in hybrid_scores.items():
            vector_score = vector_scores.get(doc_id, 0)
            keyword_score = keyword_scores.get(doc_id, 0)
            max_pure_score = max(vector_score, keyword_score)

            if hybrid_score < max_pure_score - 0.01:  # Allow small floating-point differences
                violations.append({
                    "doc_id": doc_id,
                    "hybrid_score": hybrid_score,
                    "vector_score": vector_score,
                    "keyword_score": keyword_score,
                    "max_pure_score": max_pure_score
                })

        return violations
```

### Oracle 2: Multi-Model Consistency

**File**: `oracles/multimodel_consistency.py`

```python
"""Multi-model consistency oracle for seekdb."""

from __future__ import annotations
from typing import Any, Dict
from oracles.base import OracleBase
from schemas.case import TestCase
from schemas.result import ExecutionResult, OracleResult


class MultiModelConsistency(OracleBase):
    """Validate multi-model referential integrity.

    Checks that:
    1. Cross-modal references are maintained
    2. Delete operations cascade correctly
    3. No orphaned multi-model references
    """

    def __init__(self):
        self._multi_model_index = {}  # Track entities across models

    def validate(
        self,
        case: TestCase,
        result: ExecutionResult,
        context: Dict[str, Any]
    ) -> OracleResult:
        """Validate multi-model consistency."""
        operation = case.operation

        # Track insert operations
        if operation.value == "insert":
            return self._validate_insert(case, result, context)

        # Track delete operations
        if operation.value == "delete":
            return self._validate_delete(case, result, context)

        # Validate search operations
        if operation.value in ["search", "hybrid_search"]:
            return self._validate_search(case, result, context)

        return OracleResult(oracle_id="multimodel_consistency", passed=True, explanation="N/A")

    def _validate_insert(
        self,
        case: TestCase,
        result: ExecutionResult,
        context: Dict[str, Any]
    ) -> OracleResult:
        """Validate multi-model insert maintains consistency."""
        if result.observed_outcome.value != "success":
            return OracleResult(oracle_id="multimodel_consistency", passed=True, explanation="Insert failed")

        # Track inserted documents
        documents = case.params.get("documents", [])
        for doc in documents:
            doc_id = doc.get("id")
            if doc_id:
                self._multi_model_index[doc_id] = {
                    "text": doc.get("text") is not None,
                    "vector": doc.get("vector") is not None,
                    "image": doc.get("image") is not None
                }

        return OracleResult(
            oracle_id="multimodel_consistency",
            passed=True,
            explanation=f"Inserted {len(documents)} multi-model documents"
        )

    def _validate_delete(
        self,
        case: TestCase,
        result: ExecutionResult,
        context: Dict[str, Any]
    ) -> OracleResult:
        """Validate multi-model delete cascades correctly."""
        doc_ids = case.params.get("ids", [])

        # Check for orphaned references after delete
        for doc_id in doc_ids:
            if doc_id in self._multi_model_index:
                # Verify deletion is complete across all models
                # (In real implementation, would query each model separately)
                del self._multi_model_index[doc_id]

        return OracleResult(
            oracle_id="multimodel_consistency",
            passed=True,
            explanation=f"Deleted {len(doc_ids)} documents"
        )

    def _validate_search(
        self,
        case: TestCase,
        result: ExecutionResult,
        context: Dict[str, Any]
    ) -> OracleResult:
        """Validate search results don't reference deleted entities."""
        result_ids = [item.get("id") for item in result.response.get("data", [])]

        # Check for orphaned references
        orphaned = [id_ for id_ in result_ids if id_ not in self._multi_model_index]

        if orphaned:
            return OracleResult(
                oracle_id="multimodel_consistency",
                passed=False,
                metrics={"orphaned_ids": orphaned},
                expected_relation="All result IDs exist in multi-model index",
                observed_relation=f"Results reference deleted entities: {orphaned}",
                explanation="Search returned references to deleted multi-model entities"
            )

        return OracleResult(
            oracle_id="multimodel_consistency",
            passed=True,
            explanation="Search results are consistent with multi-model index"
        )
```

---

## Phase 4: seekdb Test Templates (Week 4-5)

### Template 1: Hybrid Search Cases

**File**: `casegen/templates/seekdb_hybrid_search.yaml`

```yaml
templates:
  # Pure vector search baseline
  - template_id: "seekdb-pure-vector"
    operation: "search"
    param_template:
      search_mode: "vector"
      query_text: "machine learning"
      query_vector: "<generate_test_vector>"
      top_k: 10
    expected_validity: "legal"
    required_preconditions: ["collection_exists", "collection_loaded"]
    oracle_refs: ["hybrid_search_consistency"]
    pair_with: "seekdb-pure-keyword"

  # Pure keyword search baseline
  - template_id: "seekdb-pure-keyword"
    operation: "search"
    param_template:
      search_mode: "keyword"
      query_text: "machine learning"
      top_k: 10
    expected_validity: "legal"
    required_preconditions: ["collection_exists", "collection_loaded"]
    oracle_refs: ["hybrid_search_consistency"]
    pair_with: "seekdb-pure-vector"

  # Hybrid search with default fusion
  - template_id: "seekdb-hybrid-default"
    operation: "hybrid_search"
    param_template:
      query_text: "machine learning"
      query_vector: "<generate_test_vector>"
      hybrid_alpha: 0.5
      top_k: 10
    expected_validity: "legal"
    required_preconditions: ["collection_exists", "collection_loaded"]
    oracle_refs: ["hybrid_search_consistency"]
    rationale: "Hybrid search should be consistent with pure modes"

  # Type-4: Hybrid search with extreme fusion
  - template_id: "seekdb-hybrid-vector-dominant"
    operation: "hybrid_search"
    param_template:
      query_text: "machine learning"
      query_vector: "<generate_test_vector>"
      hybrid_alpha: 0.95  # Heavily favors vector
      top_k: 10
    expected_validity: "legal"
    required_preconditions: ["collection_exists", "collection_loaded"]
    oracle_refs: ["hybrid_search_consistency"]
    pair_with: "seekdb-hybrid-keyword-dominant"
    rationale: "Vector-dominant fusion should still include keyword matches"

  # Type-4: Hybrid search with keyword dominance
  - template_id: "seekdb-hybrid-keyword-dominant"
    operation: "hybrid_search"
    param_template:
      query_text: "machine learning"
      query_vector: "<generate_test_vector>"
      hybrid_alpha: 0.05  # Heavily favors keyword
      top_k: 10
    expected_validity: "legal"
    required_preconditions: ["collection_exists", "collection_loaded"]
    oracle_refs: ["hybrid_search_consistency"]
    pair_with: "seekdb-hybrid-vector-dominant"
    rationale: "Keyword-dominant fusion should still include vector matches"

  # Type-1: Hybrid search with invalid alpha
  - template_id: "seekdb-hybrid-invalid-alpha"
    operation: "hybrid_search"
    param_template:
      query_text: "test"
      query_vector: "<generate_test_vector>"
      hybrid_alpha: 1.5  # Invalid: > 1.0
      top_k: 10
    expected_validity: "illegal"
    required_preconditions: ["collection_exists", "collection_loaded"]
    oracle_refs: []
    rationale: "Hybrid alpha outside [0,1] range should fail"
```

### Template 2: Multi-Model Cases

**File**: `casegen/templates/seekdb_multimodel.yaml`

```yaml
templates:
  # Multi-model insert: text only
  - template_id: "seekdb-insert-text"
    operation: "insert"
    param_template:
      documents:
        - id: "doc1"
          text: "Machine learning is a subset of AI"
    expected_validity: "legal"
    required_preconditions: ["collection_exists"]
    oracle_refs: ["multimodel_consistency"]

  # Multi-model insert: vector only
  - template_id: "seekdb-insert-vector"
    operation: "insert"
    param_template:
      documents:
        - id: "doc1"
          vector: "<generate_test_vector>"
    expected_validity: "legal"
    required_preconditions: ["collection_exists"]
    oracle_refs: ["multimodel_consistency"]

  # Multi-model insert: text + vector
  - template_id: "seekdb-insert-multimodel"
    operation: "insert"
    param_template:
      documents:
        - id: "doc1"
          text: "Machine learning is a subset of AI"
          vector: "<generate_test_vector>"
    expected_validity: "legal"
    required_preconditions: ["collection_exists"]
    oracle_refs: ["multimodel_consistency"]

  # Type-4: Multi-model reference violation
  - template_id: "seekdb-delete-text-reference-vector"
    operation: "delete"
    param_template:
      ids: ["doc1"]
    expected_validity: "legal"
    required_preconditions: ["collection_exists"]
    oracle_refs: ["multimodel_consistency"]
    setup_operations:
      - operation: "insert"
        documents:
          - id: "doc1"
            text: "Test document"
            vector: "<generate_test_vector>"
    rationale: "Deleting text should invalidate vector reference"

  # Type-2: Invalid multi-model insert
  - template_id: "seekdb-insert-missing-required-field"
    operation: "insert"
    param_template:
      documents:
        - id: "doc1"
          # Missing required field (e.g., text for text collection)
    expected_validity: "illegal"
    required_preconditions: ["collection_exists"]
    oracle_refs: []
    rationale: "Multi-model schema requires at least one field type"
```

---

## Phase 5: seekdb Bug-Mining Campaign (Week 5-6)

### Campaign Structure

```python
# scripts/run_seekdb_campaign.py

"""Run seekdb bug-mining campaign."""

from adapters.seekdb_adapter import SeekDBAdapter
from oracles.hybrid_search_consistency import HybridSearchConsistency
from oracles.multimodel_consistency import MultiModelConsistency

def run_seekdb_campaign():
    # Configuration
    config = {
        "api_endpoint": "https://api.seekdb.com",
        "api_key": os.getenv("SEEKDB_API_KEY"),
        "collection": "test_collection"
    }

    # Initialize adapter
    adapter = SeekDBAdapter(**config)

    # Initialize oracles
    oracles = [
        HybridSearchConsistency(vector_adapter=adapter, keyword_adapter=adapter),
        MultiModelConsistency()
    ]

    # Load seekdb-specific templates
    templates = load_templates("casegen/templates/seekdb_*.yaml")

    # Run campaign
    results = []
    for template_group in templates:
        cases = instantiate_all(template_group, config)
        for case in cases:
            result = execute_case(case, adapter, oracles)
            results.append(result)

    # Analyze results
    bug_counts = analyze_bug_counts(results)
    print(f"seekdb campaign complete: {bug_counts}")
```

### Expected Outcomes

**Hybrid Search Cases**:
- Type-4 violations: Fusion monotonicity violations
- Type-4 violations: Mode coverage gaps (hybrid misses pure mode results)
- Type-2 violations: Poor diagnostics for fusion parameter errors

**Multi-Model Cases**:
- Type-4 violations: Orphaned cross-modal references
- Type-4 violations: Cascade failures (delete text but vector remains)
- Type-2 violations: "Invalid multi-model operation" without specificity

---

## Summary

### Implementation Effort

| Component | Lines | Time |
|-----------|-------|------|
| seekdb Adapter | ~400 | 1-2 weeks |
| Contract/Profile | ~100 | 0.5 weeks |
| Hybrid Search Oracle | ~200 | 1 week |
| Multi-Model Oracle | ~150 | 1 week |
| Test Templates | ~400 | 1-1.5 weeks |
| Campaign & Analysis | ~200 | 0.5-1 weeks |
| **Total** | **~1450** | **4-6 weeks** |

### Architecture Impact

**No changes to existing code**:
- MilvusAdapter unchanged
- Existing oracles unchanged
- Triage pipeline unchanged
- Evidence writing unchanged

**Pure additions**:
- `adapters/seekdb_adapter.py`
- `oracles/hybrid_search_consistency.py`
- `oracles/multimodel_consistency.py`
- `contracts/db_profiles/seekdb_profile.yaml`
- `casegen/templates/seekdb_*.yaml`

### Research Value

After seekdb integration, the paper can claim:

1. **Cross-Paradigm Coverage**:
   - Classic vector databases: Milvus, Qdrant
   - AI-native database: seekdb

2. **Unique Bug Types**:
   - Hybrid search fusion violations (seekdb-specific)
   - Multi-model cascade failures (seekdb-specific)
   - AI workflow state errors (seekdb-specific)

3. **Framework Generality**:
   - Adapts to different database architectures
   - Handles AI-native complexity
   - Oracle system extends to new semantic properties

4. **Forward-Looking Relevance**:
   - AI-native databases are the future trend
   - Demonstrates framework applicability beyond vector search
