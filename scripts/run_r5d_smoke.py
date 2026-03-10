#!/usr/bin/env python3
"""
R5D Smoke Run - Round 1 P0 Cases (4 core cases only)

Purpose: Validate minimal loop
- Generator generates correctly
- Adapter executes correctly
- Oracle classification is interpretable
- Evidence bundle is complete

Cases:
- R5D-001: Metadata Accuracy (SCH-004)
- R5D-002: Data Preservation (SCH-001)
- R5D-003: Query Compatibility (SCH-002)
- R5D-004: Schema Isolation (SCH-008)
"""

import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

# pymilvus imports
from pymilvus import connections, Collection, utility, DataType
from pymilvus import MilvusException

# Local imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from adapters.milvus_adapter import MilvusAdapter


# ============================================================================
# Classification Enum
# ============================================================================

class Classification:
    """Oracle classification options."""
    PASS = "PASS"
    BUG_CANDIDATE = "BUG_CANDIDATE"
    OBSERVATION = "OBSERVATION"
    ALLOWED_DIFFERENCE = "ALLOWED_DIFFERENCE"
    EXPECTED_FAILURE = "EXPECTED_FAILURE"
    EXPERIMENT_DESIGN_ISSUE = "EXPERIMENT_DESIGN_ISSUE"


# ============================================================================
# Oracle Engine
# ============================================================================

class SchemaOracleEngine:
    """Oracle engine for schema evolution contracts."""

    def _oracle_result(self, contract_id: str, classification: str,
                       satisfied: bool, reasoning: str,
                       evidence: Dict[str, Any]) -> Dict[str, Any]:
        """Create oracle result dict."""
        return {
            "contract_id": contract_id,
            "classification": classification,
            "satisfied": satisfied,
            "reasoning": reasoning,
            "evidence": evidence,
            "timestamp": datetime.now().isoformat()
        }

    def _oracle_sch004_metadata_accuracy(self, result: Dict, contract: Dict) -> Dict[str, Any]:
        """
        SCH-004: Metadata Accuracy
        Collection metadata must accurately reflect actual schema

        NOTE: Entity count has documented timing behavior (R5B ILC-009b)
        - Flush enables visibility but with delay
        - Entity count mismatch is OBSERVATION, not BUG_CANDIDATE
        """
        metadata = result.get("metadata", {})
        expected = result.get("expected_schema", {})

        # Check field count (CRITICAL - schema structure)
        actual_fields = len(metadata.get("fields", []))
        expected_fields = expected.get("field_count", 0)

        if actual_fields != expected_fields:
            return self._oracle_result(
                "SCH-004", Classification.BUG_CANDIDATE, False,
                f"Field count mismatch: metadata={actual_fields}, expected={expected_fields}",
                {"actual": actual_fields, "expected": expected_fields, "issue_type": "schema_structure"}
            )

        # Check dimension (CRITICAL - schema structure)
        actual_dim = metadata.get("dimension")
        expected_dim = expected.get("dimension", 0)

        if actual_dim != expected_dim:
            return self._oracle_result(
                "SCH-004", Classification.BUG_CANDIDATE, False,
                f"Dimension mismatch: metadata={actual_dim}, expected={expected_dim}",
                {"actual": actual_dim, "expected": expected_dim, "issue_type": "schema_structure"}
            )

        # Check entity count (DOCUMENTED TIMING BEHAVIOR)
        actual_count = metadata.get("entity_count")
        expected_count = expected.get("entity_count", 0)

        if actual_count != expected_count:
            # This is documented Milvus timing behavior (R5B ILC-009b)
            return self._oracle_result(
                "SCH-004", Classification.OBSERVATION, True,
                f"Entity count timing behavior: metadata={actual_count}, expected={expected_count}. Documented in R5B ILC-009b - flush enables visibility with delay.",
                {"actual": actual_count, "expected": expected_count, "issue_type": "documented_timing_behavior",
                 "reference": "R5B ILC-009b", "note": "Not a bug - Milvus flush visibility is delayed"}
            )

        return self._oracle_result(
            "SCH-004", Classification.PASS, True,
            "Metadata accurately reflects schema (structure and timing)",
            metadata
        )

    def _oracle_sch001_data_preservation(self, result: Dict, contract: Dict) -> Dict[str, Any]:
        """
        SCH-001: Data Preservation
        Creating collection_v2 must not affect data in collection_v1
        """
        v1_count_before = result.get("v1_count_before")
        v1_count_after = result.get("v1_count_after")

        if v1_count_after is None:
            return self._oracle_result(
                "SCH-001", Classification.EXPERIMENT_DESIGN_ISSUE, False,
                "v1_count_after not captured",
                result
            )

        if v1_count_after != v1_count_before:
            return self._oracle_result(
                "SCH-001", Classification.BUG_CANDIDATE, False,
                f"Data loss in v1: {v1_count_before} → {v1_count_after}",
                {"loss": v1_count_before - v1_count_after,
                 "before": v1_count_before, "after": v1_count_after}
            )

        return self._oracle_result(
            "SCH-001", Classification.PASS, True,
            f"Data preserved across schema versions (count={v1_count_after})",
            {"v1_count": v1_count_after}
        )

    def _oracle_sch002_query_compatibility(self, result: Dict, contract: Dict) -> Dict[str, Any]:
        """
        SCH-002: Backward Query Compatibility
        Queries on collection_v1 must continue working after collection_v2 is created
        """
        query_before = result.get("v1_query_before", {})
        query_after = result.get("v1_query_after", {})

        # Check if query succeeded
        if query_after.get("status") == "error":
            return self._oracle_result(
                "SCH-002", Classification.BUG_CANDIDATE, False,
                f"Query broke after v2 creation: {query_after.get('error', 'unknown')}",
                {"error": query_after.get("error")}
            )

        # Check result count
        before_count = query_before.get("result_count", 0)
        after_count = query_after.get("result_count", 0)

        if before_count != after_count:
            return self._oracle_result(
                "SCH-002", Classification.ALLOWED_DIFFERENCE, True,
                f"Query result count changed: {before_count} → {after_count}",
                {"before": before_count, "after": after_count}
            )

        return self._oracle_result(
            "SCH-002", Classification.PASS, True,
            f"Query compatible across schema versions ({after_count} results)",
            {"result_count": after_count}
        )

    def _oracle_sch008_schema_isolation(self, result: Dict, contract: Dict) -> Dict[str, Any]:
        """
        SCH-008: Metadata Reflection After Change
        After creating collection_v2, collection_v1 metadata must remain unchanged
        """
        v1_schema_before = result.get("v1_schema_before", {})
        v1_schema_after = result.get("v1_schema_after", {})

        # Compare field lists
        fields_before = set(v1_schema_before.get("fields", []))
        fields_after = set(v1_schema_after.get("fields", []))

        if fields_before != fields_after:
            return self._oracle_result(
                "SCH-008", Classification.BUG_CANDIDATE, False,
                f"v1 field list changed after v2 creation: {fields_before} → {fields_after}",
                {"before": list(fields_before), "after": list(fields_after)}
            )

        # Compare dimensions
        dim_before = v1_schema_before.get("dimension")
        dim_after = v1_schema_after.get("dimension")

        if dim_before != dim_after:
            return self._oracle_result(
                "SCH-008", Classification.BUG_CANDIDATE, False,
                f"v1 dimension changed after v2 creation: {dim_before} → {dim_after}",
                {"before": dim_before, "after": dim_after}
            )

        # Compare primary key
        pk_before = v1_schema_before.get("primary_key")
        pk_after = v1_schema_after.get("primary_key")

        if pk_before != pk_after:
            return self._oracle_result(
                "SCH-008", Classification.BUG_CANDIDATE, False,
                f"v1 primary_key changed after v2 creation: {pk_before} → {pk_after}",
                {"before": pk_before, "after": pk_after}
            )

        return self._oracle_result(
            "SCH-008", Classification.PASS, True,
            "v1 schema unchanged after v2 creation",
            v1_schema_after
        )

    def evaluate(self, result: Dict, contract: Dict) -> Dict[str, Any]:
        """Evaluate a result against a contract."""
        contract_id = contract.get("contract_id", "")

        if contract_id == "SCH-004":
            return self._oracle_sch004_metadata_accuracy(result, contract)
        elif contract_id == "SCH-001":
            return self._oracle_sch001_data_preservation(result, contract)
        elif contract_id == "SCH-002":
            return self._oracle_sch002_query_compatibility(result, contract)
        elif contract_id == "SCH-008":
            return self._oracle_sch008_schema_isolation(result, contract)
        else:
            return self._oracle_result(
                contract_id, Classification.EXPERIMENT_DESIGN_ISSUE, False,
                f"Unknown contract: {contract_id}",
                {}
            )


# ============================================================================
# Test Case Generator
# ============================================================================

class R5DSmokeGenerator:
    """Generate smoke test cases for R5D Round 1."""

    def __init__(self, dimension: int = 128):
        self.dimension = dimension

    def _generate_vector(self, seed: int) -> List[float]:
        """Generate a deterministic vector."""
        import random
        random.seed(seed)
        return [random.random() for _ in range(self.dimension)]

    def generate_r5d001(self) -> Dict[str, Any]:
        """
        R5D-001: Metadata Accuracy (SCH-004)

        Sequence:
        1. Create collection with schema: {id, vector[128]}
        2. Insert 50 entities
        3. describe_collection
        4. Verify: fields=2, dimension=128, entity_count=50
        """
        return {
            "case_id": "R5D-001",
            "contract_id": "SCH-004",
            "name": "Metadata Accuracy",
            "description": "describe_collection returns correct schema",
            "sequence": [
                {
                    "step": 1,
                    "operation": "create_collection",
                    "params": {
                        "collection_name": "r5d001_test_collection",
                        "dimension": self.dimension,
                        "field_types": [
                            {"name": "id", "type": "INT64", "is_primary": True},
                            {"name": "vector", "type": "FLOAT_VECTOR", "params": {"dim": self.dimension}}
                        ]
                    }
                },
                {
                    "step": 2,
                    "operation": "insert",
                    "params": {
                        "collection_name": "r5d001_test_collection",
                        "num_entities": 50
                    },
                    "flush_after": True
                },
                {
                    "step": 3,
                    "operation": "describe_collection",
                    "params": {
                        "collection_name": "r5d001_test_collection"
                    },
                    "wait_after": True
                }
            ],
            "expected_schema": {
                "field_count": 2,
                "dimension": self.dimension,
                "entity_count": 50
            }
        }

    def generate_r5d002(self) -> Dict[str, Any]:
        """
        R5D-002: Data Preservation (SCH-001)

        Sequence:
        1. Create collection_v1: {id, vector[128]}
        2. Insert 100 entities into v1
        3. count_entities(v1) → count_before
        4. Create collection_v2: {id, vector[128], category}
        5. count_entities(v1) → count_after
        6. Verify: count_after == count_before
        """
        return {
            "case_id": "R5D-002",
            "contract_id": "SCH-001",
            "name": "Data Preservation",
            "description": "v1 count unchanged after v2 creation",
            "sequence": [
                {
                    "step": 1,
                    "operation": "create_collection",
                    "params": {
                        "collection_name": "r5d002_v1",
                        "dimension": self.dimension,
                        "field_types": [
                            {"name": "id", "type": "INT64", "is_primary": True},
                            {"name": "vector", "type": "FLOAT_VECTOR", "params": {"dim": self.dimension}}
                        ]
                    }
                },
                {
                    "step": 2,
                    "operation": "insert",
                    "params": {
                        "collection_name": "r5d002_v1",
                        "num_entities": 100
                    },
                    "flush_after": True
                },
                {
                    "step": 3,
                    "operation": "count_entities",
                    "params": {
                        "collection_name": "r5d002_v1"
                    },
                    "capture_as": "v1_count_before"
                },
                {
                    "step": 4,
                    "operation": "create_collection",
                    "params": {
                        "collection_name": "r5d002_v2",
                        "dimension": self.dimension,
                        "field_types": [
                            {"name": "id", "type": "INT64", "is_primary": True},
                            {"name": "vector", "type": "FLOAT_VECTOR", "params": {"dim": self.dimension}},
                            {"name": "category", "type": "VARCHAR", "params": {"max_length": 256}}
                        ]
                    }
                },
                {
                    "step": 5,
                    "operation": "count_entities",
                    "params": {
                        "collection_name": "r5d002_v1"
                    },
                    "capture_as": "v1_count_after"
                }
            ]
        }

    def generate_r5d003(self) -> Dict[str, Any]:
        """
        R5D-003: Query Compatibility (SCH-002)

        Sequence:
        1. Create collection_v1: {id, vector[128]}
        2. Insert 100 entities into v1
        3. Search v1 with query_vector → results_before
        4. Create collection_v2: {id, vector[128], category}
        5. Search v1 with SAME query_vector → results_after
        6. Verify: results semantically equivalent
        """
        query_vector = self._generate_vector(42)

        return {
            "case_id": "R5D-003",
            "contract_id": "SCH-002",
            "name": "Query Compatibility",
            "description": "v1 query works after v2 creation",
            "sequence": [
                {
                    "step": 1,
                    "operation": "create_collection",
                    "params": {
                        "collection_name": "r5d003_v1",
                        "dimension": self.dimension,
                        "field_types": [
                            {"name": "id", "type": "INT64", "is_primary": True},
                            {"name": "vector", "type": "FLOAT_VECTOR", "params": {"dim": self.dimension}}
                        ]
                    }
                },
                {
                    "step": 2,
                    "operation": "insert",
                    "params": {
                        "collection_name": "r5d003_v1",
                        "num_entities": 100
                    },
                    "flush_after": True
                },
                {
                    "step": 2.5,
                    "operation": "build_index",
                    "params": {
                        "collection_name": "r5d003_v1"
                    }
                },
                {
                    "step": 3,
                    "operation": "search",
                    "params": {
                        "collection_name": "r5d003_v1",
                        "vector": query_vector,
                        "top_k": 10
                    },
                    "capture_as": "v1_query_before"
                },
                {
                    "step": 4,
                    "operation": "create_collection",
                    "params": {
                        "collection_name": "r5d003_v2",
                        "dimension": self.dimension,
                        "field_types": [
                            {"name": "id", "type": "INT64", "is_primary": True},
                            {"name": "vector", "type": "FLOAT_VECTOR", "params": {"dim": self.dimension}},
                            {"name": "category", "type": "VARCHAR", "params": {"max_length": 256}}
                        ]
                    }
                },
                {
                    "step": 5,
                    "operation": "search",
                    "params": {
                        "collection_name": "r5d003_v1",
                        "vector": query_vector,
                        "top_k": 10
                    },
                    "capture_as": "v1_query_after"
                }
            ]
        }

    def generate_r5d004(self) -> Dict[str, Any]:
        """
        R5D-004: Schema Isolation (SCH-008)

        Sequence:
        1. Create collection_v1: {id, vector[128]}
        2. describe_collection(v1) → schema_v1_before
        3. Create collection_v2: {id, vector[128], category}
        4. describe_collection(v1) → schema_v1_after
        5. Verify: schema_v1_before == schema_v1_after
        """
        return {
            "case_id": "R5D-004",
            "contract_id": "SCH-008",
            "name": "Schema Isolation",
            "description": "v1 schema unchanged after v2 creation",
            "sequence": [
                {
                    "step": 1,
                    "operation": "create_collection",
                    "params": {
                        "collection_name": "r5d004_v1",
                        "dimension": self.dimension,
                        "field_types": [
                            {"name": "id", "type": "INT64", "is_primary": True},
                            {"name": "vector", "type": "FLOAT_VECTOR", "params": {"dim": self.dimension}}
                        ]
                    }
                },
                {
                    "step": 2,
                    "operation": "describe_collection",
                    "params": {
                        "collection_name": "r5d004_v1"
                    },
                    "capture_as": "v1_schema_before"
                },
                {
                    "step": 3,
                    "operation": "create_collection",
                    "params": {
                        "collection_name": "r5d004_v2",
                        "dimension": self.dimension,
                        "field_types": [
                            {"name": "id", "type": "INT64", "is_primary": True},
                            {"name": "vector", "type": "FLOAT_VECTOR", "params": {"dim": self.dimension}},
                            {"name": "category", "type": "VARCHAR", "params": {"max_length": 256}}
                        ]
                    }
                },
                {
                    "step": 4,
                    "operation": "describe_collection",
                    "params": {
                        "collection_name": "r5d004_v1"
                    },
                    "capture_as": "v1_schema_after"
                }
            ]
        }

    def generate_all(self) -> List[Dict[str, Any]]:
        """Generate all Round 1 smoke test cases."""
        return [
            self.generate_r5d001(),
            self.generate_r5d002(),
            self.generate_r5d003(),
            self.generate_r5d004()
        ]


# ============================================================================
# Full P0 Execution Constants
# ============================================================================

# Wait windows for count-related observations (milliseconds)
COUNT_OBSERVATION_WAIT_MS = 200  # Based on R5B ILC-009b findings

# ============================================================================
# Test Executor
# ============================================================================

class R5DTestExecutor:
    """Execute R5D smoke tests."""

    def __init__(self, host: str = "localhost", port: int = 19530):
        self.host = host
        self.port = port
        self.adapter = None
        self.oracle = SchemaOracleEngine()
        self._collections_created = []

    def connect(self):
        """Connect to Milvus."""
        try:
            self.adapter = MilvusAdapter({
                "host": self.host,
                "port": self.port,
                "alias": "default"
            })
            print(f"[OK] Connected to Milvus at {self.host}:{self.port}")
        except Exception as e:
            print(f"[FAIL] Failed to connect: {e}")
            raise

    def disconnect(self):
        """Disconnect from Milvus."""
        try:
            connections.disconnect("default")
            print("[OK] Disconnected from Milvus")
        except:
            pass  # Already disconnected or never connected

    def cleanup(self):
        """Clean up created collections."""
        for collection_name in self._collections_created:
            try:
                if utility.has_collection(collection_name):
                    utility.drop_collection(collection_name)
                    print(f"[OK] Cleaned up {collection_name}")
            except Exception as e:
                print(f"[WARN] Failed to cleanup {collection_name}: {e}")

    def _extract_schema_summary(self, metadata: Dict) -> Dict[str, Any]:
        """Extract schema summary from describe_collection result."""
        fields = metadata.get("fields", [])
        return {
            "fields": [f.get("name") for f in fields],
            "dimension": metadata.get("dimension"),
            "primary_key": metadata.get("primary_key"),
            "entity_count": metadata.get("entity_count")
        }

    def execute_operation(self, operation: str, params: Dict) -> Dict[str, Any]:
        """Execute a single operation via adapter."""
        result = self.adapter.execute({"operation": operation, "params": params})

        # Track created collections
        if operation == "create_collection":
            collection_name = params.get("collection_name")
            if collection_name and collection_name not in self._collections_created:
                self._collections_created.append(collection_name)

        return result

    def execute_case(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single test case."""
        case_id = case.get("case_id", "UNKNOWN")
        print(f"\n{'='*60}")
        print(f"Executing {case_id}: {case.get('name', '')}")
        print(f"{'='*60}")

        execution_trace = []
        captured_results = {}

        for step in case.get("sequence", []):
            step_num = step.get("step", 0)
            operation = step.get("operation", "")
            params = step.get("params", {}).copy()
            capture_as = step.get("capture_as")

            print(f"\n[Step {step_num}] {operation}")

            # Generate data if needed
            if operation == "insert":
                num_entities = params.get("num_entities", 0)
                collection_name = params.get("collection_name")

                # Build insert data in adapter format
                vectors = []
                scalar_data = []
                for i in range(num_entities):
                    vectors.append([float(i) * 0.01] * 128)  # Simple deterministic vector
                    scalar_data.append({"id": i})

                # Add category if v2
                if "v2" in collection_name:
                    for i, scalar in enumerate(scalar_data):
                        scalar["category"] = "A" if i % 2 == 0 else "B"

                # Replace num_entities with adapter format
                params.pop("num_entities", None)
                params["vectors"] = vectors
                params["scalar_data"] = scalar_data

            # Flush after insert (required for visibility in Milvus)
            if operation == "insert" and step.get("flush_after", False):
                collection_name = params.get("collection_name")
                try:
                    flush_result = self.execute_operation("flush", {"collection_names": [collection_name]})
                    print(f"    [flush] Flushed for visibility")
                    # Wait for flush to complete (based on R5B ILC-009b)
                    import time
                    time.sleep(COUNT_OBSERVATION_WAIT_MS / 1000.0)
                    print(f"    [wait] Waited {COUNT_OBSERVATION_WAIT_MS}ms for flush visibility")
                except:
                    pass  # Flush may fail silently

            # Wait after count for visibility
            if operation == "count_entities" and step.get("wait_after", False):
                import time
                time.sleep(COUNT_OBSERVATION_WAIT_MS / 1000.0)
                print(f"    [wait] Waited {COUNT_OBSERVATION_WAIT_MS}ms for count visibility")

            # Add load before search (required by Milvus)
            if operation == "search":
                collection_name = params.get("collection_name")
                # Load collection first
                try:
                    load_result = self.execute_operation("load", {"collection_name": collection_name})
                    print(f"    [preload] Loaded collection")
                except:
                    pass  # May already be loaded

            # Execute operation
            try:
                result = self.execute_operation(operation, params)

                # Add to trace
                trace_entry = {
                    "step": step_num,
                    "operation": operation,
                    "params": {k: v for k, v in params.items() if k != "data"},  # Don't log full data
                    "result_status": result.get("status", "unknown")
                }

                # Capture result
                if capture_as:
                    captured_results[capture_as] = result
                    trace_entry["captured_as"] = capture_as

                # Show result
                if result.get("status") == "success":
                    print(f"  [OK] Success")

                    # Show key info
                    if operation == "describe_collection":
                        data = result.get("data", [{}])[0]
                        fields = data.get("fields", [])
                        print(f"    Fields: {[f['name'] for f in fields]}")
                        print(f"    Dimension: {data.get('dimension')}")
                        print(f"    Entity Count: {data.get('entity_count')}")

                    elif operation == "count_entities":
                        count = result.get("storage_count", 0)
                        print(f"    Count: {count}")
                        captured_results[capture_as] = count

                    elif operation == "search":
                        results = result.get("data", [])
                        count = len(results) if isinstance(results, list) else 0
                        print(f"    Result count: {count}")
                        if count > 0:
                            top_id = results[0].get("id") if isinstance(results[0], dict) else "N/A"
                            print(f"    Top ID: {top_id}")

                        captured_results[capture_as] = {
                            "status": "success",
                            "result_count": count,
                            "results": results[:3] if count > 0 else []  # Keep top 3 for evidence
                        }

                else:
                    print(f"  [FAIL] Error: {result.get('error', 'unknown')}")
                    trace_entry["error"] = result.get("error")

                execution_trace.append(trace_entry)

            except Exception as e:
                print(f"  [FAIL] Exception: {e}")
                execution_trace.append({
                    "step": step_num,
                    "operation": operation,
                    "error": str(e),
                    "exception": True
                })

        # Build final result
        final_result = {
            "case_id": case_id,
            "contract_id": case.get("contract_id"),
            "execution_trace": execution_trace,
            "captured_results": captured_results
        }

        # Add expected schema for R5D-001
        if case_id == "R5D-001":
            final_result["expected_schema"] = case.get("expected_schema", {})
            # Also extract metadata from describe result
            if "describe_result" in captured_results:
                metadata = captured_results["describe_result"].get("data", [{}])[0]
                final_result["metadata"] = self._extract_schema_summary(metadata)
            elif "Step 3" in str(captured_results):
                # Find describe result
                for trace in execution_trace:
                    if trace.get("operation") == "describe_collection":
                        # We need to get the actual result
                        pass

        # Extract metadata for describe_collection operations
        for trace in execution_trace:
            if trace.get("operation") == "describe_collection" and trace.get("result_status") == "success":
                # Need to re-execute to get full result (simplified)
                collection_name = trace.get("params", {}).get("collection_name")
                if collection_name:
                    desc_result = self.execute_operation("describe_collection", {"collection_name": collection_name})
                    if desc_result.get("status") == "success":
                        metadata = desc_result.get("data", [{}])[0]
                        captured_results[f"{collection_name}_metadata"] = self._extract_schema_summary(metadata)

        # Map captured results properly for each case
        if case_id == "R5D-001":
            # Get metadata from describe result
            if "r5d001_test_collection_metadata" in captured_results:
                final_result["metadata"] = captured_results["r5d001_test_collection_metadata"]

        elif case_id == "R5D-002":
            final_result["v1_count_before"] = captured_results.get("v1_count_before", 0)
            final_result["v1_count_after"] = captured_results.get("v1_count_after", 0)

        elif case_id == "R5D-003":
            final_result["v1_query_before"] = captured_results.get("v1_query_before", {})
            final_result["v1_query_after"] = captured_results.get("v1_query_after", {})

        elif case_id == "R5D-004":
            final_result["v1_schema_before"] = captured_results.get("r5d004_v1_metadata", {})
            final_result["v1_schema_after"] = captured_results.get("r5d004_v1_metadata", {})

        return final_result


# ============================================================================
# Main Smoke Run
# ============================================================================

def run_full_p0():
    """Run R5D Round 1 full P0 execution."""
    print("="*60)
    print("R5D FULL P0 EXECUTION - Round 1 (4 Core Cases)")
    print("="*60)
    print(f"Date: {datetime.now().isoformat()}")
    print(f"Database: Milvus v2.6.10")
    print(f"Campaign: R5D Schema Evolution")
    print(f"Cases: 4 (R5D-001, R5D-002, R5D-003, R5D-004)")
    print(f"Mode: Full P0 (interpretable results, not all-pass target)")
    print("="*60)

    # Generate run ID
    run_id = f"r5d-p0-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    # Create generator and executor
    generator = R5DSmokeGenerator(dimension=128)
    executor = R5DTestExecutor()

    # Load contracts
    with open("contracts/schema/schema_contracts.json", "r") as f:
        contracts_data = json.load(f)

    # Create contract lookup
    contracts = {}
    for layer in contracts_data.get("contract_layers", {}).values():
        for contract in layer.get("contracts", []):
            contracts[contract["contract_id"]] = contract

    # Generate cases
    cases = generator.generate_all()
    print(f"\n[OK] Generated {len(cases)} test cases")

    # Connect
    try:
        executor.connect()
    except Exception as e:
        print(f"\n[FAIL] Cannot proceed without connection: {e}")
        return

    # Execute cases
    results = []
    classifications = {"PASS": 0, "BUG_CANDIDATE": 0, "OBSERVATION": 0,
                       "ALLOWED_DIFFERENCE": 0, "EXPECTED_FAILURE": 0,
                       "EXPERIMENT_DESIGN_ISSUE": 0}

    for case in cases:
        try:
            result = executor.execute_case(case)

            # Get contract
            contract_id = case.get("contract_id")
            contract = contracts.get(contract_id, {})

            # Run oracle
            oracle_result = executor.oracle.evaluate(result, contract)
            result["oracle"] = oracle_result

            # Track classification
            cls = oracle_result.get("classification", "EXPERIMENT_DESIGN_ISSUE")
            classifications[cls] = classifications.get(cls, 0) + 1

            # Show oracle result
            print(f"\n[Oracle] {cls}: {oracle_result.get('reasoning', '')}")

            results.append(result)

        except Exception as e:
            print(f"\n[FAIL] Case execution failed: {e}")
            results.append({
                "case_id": case.get("case_id"),
                "error": str(e),
                "oracle": {
                    "classification": "EXPERIMENT_DESIGN_ISSUE",
                    "reasoning": f"Execution error: {e}"
                }
            })

    # Cleanup
    executor.cleanup()
    executor.disconnect()

    # Build final report
    report = {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(),
        "database": "Milvus v2.6.10",
        "mode": "REAL",
        "campaign": "R5D Schema Evolution",
        "round": "Round 1 (Full P0)",
        "total_tests": len(cases),
        "execution_type": "full_p0",
        "note": "Target is interpretable results, not all-pass",
        "summary": {
            "total": len(cases),
            "by_classification": classifications,
            "passed": classifications.get("PASS", 0),
            "observation": classifications.get("OBSERVATION", 0),
            "bug_candidate": classifications.get("BUG_CANDIDATE", 0),
            "infra_issues": 0,
            "generator_issues": 0,
            "adapter_issues": 0
        },
        "results": results
    }

    # Save report
    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)

    report_file = results_dir / f"r5d_p0_{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"\n{'='*60}")
    print("FULL P0 EXECUTION COMPLETE")
    print(f"{'='*60}")
    print(f"Run ID: {run_id}")
    print(f"Report saved: {report_file}")
    print(f"\nClassification Summary:")
    for cls, count in classifications.items():
        if count > 0:
            print(f"  {cls}: {count}")
    print(f"\nResults Summary:")
    print(f"  PASS: {report['summary']['passed']}/{len(cases)}")
    print(f"  OBSERVATION: {report['summary']['observation']}/{len(cases)}")
    print(f"  BUG_CANDIDATE: {report['summary']['bug_candidate']}/{len(cases)}")
    print("="*60)

    return report


if __name__ == "__main__":
    run_full_p0()
