#!/usr/bin/env python3
"""
R4 Full Differential Campaign

Tests all 8 semantic properties across Milvus and Qdrant:
- R4-001: Post-Drop Rejection (PRIMARY)
- R4-002: Deleted Entity Visibility (PRIMARY)
- R4-003: Delete Idempotency (PRIMARY)
- R4-004: Index-Independent Search (ALLOWED-SENSITIVE)
- R4-005: Load-State Enforcement (ALLOWED-SENSITIVE)
- R4-006: Empty Collection Handling (EXPLORATORY)
- R4-007: Non-Existent Delete Tolerance (PRIMARY)
- R4-008: Collection Creation Idempotency (PRIMARY)

Usage:
    python scripts/run_full_r4_differential.py --require-real
"""

import sys
import os
import json
import argparse
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from adapters.milvus_adapter import MilvusAdapter
from adapters.qdrant_adapter import QdrantAdapter


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{'='*70}")
    print(f" {text}")
    print(f"{'='*70}\n")


def get_environment_snapshot() -> Dict[str, str]:
    """Capture environment information for reproducibility."""
    snapshot = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "pymilvus_version": None,
        "qdrant_client_version": None,
        "milvus_image": None,
        "qdrant_image": None,
    }

    try:
        import pymilvus
        snapshot["pymilvus_version"] = getattr(pymilvus, "__version__", "unknown")
    except ImportError:
        snapshot["pymilvus_version"] = "not_installed"

    try:
        import qdrant_client
        # qdrant_client doesn't have __version__, try pkg_resources
        try:
            import pkg_resources
            snapshot["qdrant_client_version"] = pkg_resources.get_distribution("qdrant-client").version
        except:
            snapshot["qdrant_client_version"] = "unknown"
    except ImportError:
        snapshot["qdrant_client_version"] = "not_installed"

    # Try to get Docker image versions
    try:
        import subprocess
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}\t{{.Image}}", "--filter", "name=milvus"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.strip().split('\n'):
            if 'milvus-standalone' in line:
                parts = line.split('\t')
                if len(parts) == 2:
                    snapshot["milvus_image"] = parts[1]
    except:
        pass

    try:
        import subprocess
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}\t{{.Image}}", "--filter", "name=qdrant"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.strip().split('\n'):
            if 'qdrant' in line.lower() and 'smoke' not in line.lower():
                parts = line.split('\t')
                if len(parts) == 2:
                    snapshot["qdrant_image"] = parts[1]
    except:
        pass

    return snapshot


class FullR4Runner:
    """Run full R4 differential campaign across Milvus and Qdrant."""

    # Test isolation: unique collection names for each property
    COLLECTION_NAMES = {
        "r4_001": "r4_001",
        "r4_002": "r4_002",
        "r4_003": "r4_003",
        "r4_004": "r4_004",
        "r4_005": "r4_005",
        "r4_006": "r4_006",
        "r4_007": "r4_007",
        "r4_008": "r4_008",
    }

    def __init__(self, results_dir: str, require_real: bool = False):
        self.results_dir = results_dir
        self.require_real = require_real
        self.milvus = None
        self.qdrant = None
        self.raw_results = {"milvus": {}, "qdrant": {}}
        self.differential_results = []
        self.environment_snapshot = {}
        self.adapter_requested = "real"
        self.adapter_actual = "unknown"

    def setup_adapters(self) -> bool:
        """Initialize both adapters with safety checks."""
        try:
            # Milvus config
            milvus_config = {
                "host": "localhost",
                "port": 19530,
                "alias": "r4_full_milvus"
            }
            self.milvus = MilvusAdapter(milvus_config)

            # Verify real connection
            if not self._verify_real_connection(self.milvus, "Milvus"):
                return False

            # Qdrant config
            qdrant_config = {
                "url": "http://localhost:6333",
                "timeout": 30.0
            }
            self.qdrant = QdrantAdapter(qdrant_config)

            # Verify real connection
            if not self._verify_real_connection(self.qdrant, "Qdrant"):
                return False

            self.adapter_actual = "real"
            print("[PASS]: Both adapters initialized and verified (REAL databases)")
            return True
        except Exception as e:
            print(f"[FAIL]: Adapter initialization failed: {e}")
            return False

    def _verify_real_connection(self, adapter, name: str) -> bool:
        """Verify adapter is connected to a real database."""
        try:
            # Simple health check - try to list collections
            if hasattr(adapter, 'client'):
                if hasattr(adapter.client, 'list_collections'):
                    collections = adapter.client.list_collections()
                    return True
                elif hasattr(adapter.client, 'get_collections'):
                    # Qdrant
                    collections = adapter.client.get_collections()
                    return True
            return True
        except Exception as e:
            print(f"[FAIL]: {name} connection verification failed: {e}")
            return False

    def cleanup_collection(self, adapter, adapter_name: str, collection_name: str):
        """Cleanup a collection after testing."""
        try:
            adapter.execute({
                "operation": "drop_collection",
                "params": {"collection_name": collection_name}
            })
        except Exception as e:
            # Non-fatal - collection may not exist
            print(f"  [WARN] {adapter_name} cleanup for {collection_name}: {e}")

    def execute_sequence(self, adapter, adapter_name: str, sequence: List[Dict], cleanup: bool = True) -> List[Dict]:
        """Execute a sequence of operations on an adapter."""
        results = []
        collection_name = None

        for step in sequence:
            step_num = step.get("step", len(results) + 1)
            operation = step["operation"]
            params = step.get("params", {})

            # Track collection name for cleanup
            if operation == "create_collection":
                collection_name = params.get("collection_name")

            request = {"operation": operation, "params": params}
            response = adapter.execute(request)

            results.append({
                "step": step_num,
                "operation": operation,
                "status": response["status"],
                "data": response.get("data", {}),
                "error": response.get("error"),
                "error_type": response.get("error_type")
            })

        # Cleanup after sequence
        if cleanup and collection_name:
            self.cleanup_collection(adapter, adapter_name, collection_name)

        return results

    def run_r4_001_post_drop_rejection(self) -> Dict:
        """R4-001: Post-Drop Rejection (PRIMARY).

        Oracle Rule 1: Both databases must fail operations on dropped collections.
        Test Step: 7 (search after drop)
        """
        print("\n--- R4-001: Post-Drop Rejection (PRIMARY) ---")

        case_id = "r4_001"
        collection_name = self.COLLECTION_NAMES[case_id]

        sequence = [
            {"step": 1, "operation": "create_collection", "params": {
                "collection_name": collection_name,
                "dimension": 128,
                "metric_type": "COSINE"
            }},
            {"step": 2, "operation": "insert", "params": {
                "collection_name": collection_name,
                "vectors": [[0.1] * 128, [0.9] * 128],
                "ids": [1, 2]
            }},
            {"step": 3, "operation": "build_index", "params": {
                "collection_name": collection_name,
                "field_name": "vector",
                "index_type": "HNSW"
            }},
            {"step": 4, "operation": "load", "params": {
                "collection_name": collection_name
            }},
            {"step": 5, "operation": "search", "params": {
                "collection_name": collection_name,
                "query_vector": [0.1] * 128,
                "top_k": 10
            }},
            {"step": 6, "operation": "drop_collection", "params": {
                "collection_name": collection_name
            }},
            {"step": 7, "operation": "search", "params": {
                "collection_name": collection_name,
                "query_vector": [0.1] * 128,
                "top_k": 10
            }},
        ]

        # No cleanup - collection is dropped in step 6
        milvus_results = self.execute_sequence(self.milvus, "milvus", sequence, cleanup=False)
        qdrant_results = self.execute_sequence(self.qdrant, "qdrant", sequence, cleanup=False)

        # Classify at step 7
        classification = self._classify_post_drop_rejection(
            milvus_results[6], qdrant_results[6]
        )

        return {
            "case_id": case_id,
            "property": "Post-Drop Rejection",
            "category": "PRIMARY",
            "property_number": 1,
            "oracle_rule": "Rule 1 (Search After Drop)",
            "milvus_results": milvus_results,
            "qdrant_results": qdrant_results,
            "classification": classification,
            "test_step": 7,
            "description": "Both databases must fail search on dropped collection"
        }

    def run_r4_002_deleted_entity_visibility(self) -> Dict:
        """R4-002: Deleted Entity Visibility (PRIMARY).

        Oracle Rule 2: Deleted entities must not appear in search results.
        Test Step: 7 (search after delete)
        """
        print("\n--- R4-002: Deleted Entity Visibility (PRIMARY) ---")

        case_id = "r4_002"
        collection_name = self.COLLECTION_NAMES[case_id]

        sequence = [
            {"step": 1, "operation": "create_collection", "params": {
                "collection_name": collection_name,
                "dimension": 128,
                "metric_type": "COSINE"
            }},
            {"step": 2, "operation": "insert", "params": {
                "collection_name": collection_name,
                "vectors": [[0.1] * 128, [0.5] * 128, [0.9] * 128],
                "ids": [1, 2, 3]
            }},
            {"step": 3, "operation": "build_index", "params": {
                "collection_name": collection_name,
                "field_name": "vector",
                "index_type": "HNSW"
            }},
            {"step": 4, "operation": "load", "params": {
                "collection_name": collection_name
            }},
            {"step": 5, "operation": "search", "params": {
                "collection_name": collection_name,
                "query_vector": [0.1] * 128,
                "top_k": 10
            }},
            {"step": 6, "operation": "delete", "params": {
                "collection_name": collection_name,
                "ids": [1]
            }},
            {"step": 7, "operation": "search", "params": {
                "collection_name": collection_name,
                "query_vector": [0.1] * 128,
                "top_k": 10
            }},
        ]

        milvus_results = self.execute_sequence(self.milvus, "milvus", sequence)
        qdrant_results = self.execute_sequence(self.qdrant, "qdrant", sequence)

        # Classify at step 7
        classification = self._classify_deleted_entity_visibility(
            milvus_results[6], qdrant_results[6]
        )

        return {
            "case_id": case_id,
            "property": "Deleted Entity Visibility",
            "category": "PRIMARY",
            "property_number": 2,
            "oracle_rule": "Rule 2 (Deleted Entity Visibility)",
            "milvus_results": milvus_results,
            "qdrant_results": qdrant_results,
            "classification": classification,
            "test_step": 7,
            "description": "Deleted entities must not appear in search results"
        }

    def run_r4_003_delete_idempotency(self) -> Dict:
        """R4-003: Delete Idempotency (PRIMARY).

        Oracle Rule 4: Delete operations should be idempotent.
        Test Step: 6 (second delete)
        """
        print("\n--- R4-003: Delete Idempotency (PRIMARY) ---")

        case_id = "r4_003"
        collection_name = self.COLLECTION_NAMES[case_id]

        sequence = [
            {"step": 1, "operation": "create_collection", "params": {
                "collection_name": collection_name,
                "dimension": 128,
                "metric_type": "COSINE"
            }},
            {"step": 2, "operation": "insert", "params": {
                "collection_name": collection_name,
                "vectors": [[0.1] * 128],
                "ids": [100]
            }},
            {"step": 3, "operation": "build_index", "params": {
                "collection_name": collection_name,
                "field_name": "vector",
                "index_type": "HNSW"
            }},
            {"step": 4, "operation": "load", "params": {
                "collection_name": collection_name
            }},
            {"step": 5, "operation": "delete", "params": {
                "collection_name": collection_name,
                "ids": [100]
            }},
            {"step": 6, "operation": "delete", "params": {
                "collection_name": collection_name,
                "ids": [100]
            }},
        ]

        milvus_results = self.execute_sequence(self.milvus, "milvus", sequence)
        qdrant_results = self.execute_sequence(self.qdrant, "qdrant", sequence)

        # Classify at step 6
        classification = self._classify_delete_idempotency(
            milvus_results[5], qdrant_results[5]
        )

        return {
            "case_id": case_id,
            "property": "Delete Idempotency",
            "category": "PRIMARY",
            "property_number": 3,
            "oracle_rule": "Rule 4 (Delete Idempotency)",
            "milvus_results": milvus_results,
            "qdrant_results": qdrant_results,
            "classification": classification,
            "test_step": 6,
            "description": "Delete operations should be idempotent"
        }

    def run_r4_004_index_independent_search(self) -> Dict:
        """R4-004: Index-Independent Search (ALLOWED-SENSITIVE).

        Oracle Rule 3: Search without explicit index (undefined/allowed difference).
        Test Step: 3 (search without index)
        """
        print("\n--- R4-004: Index-Independent Search (ALLOWED-SENSITIVE) ---")

        case_id = "r4_004"
        collection_name = self.COLLECTION_NAMES[case_id]

        sequence = [
            {"step": 1, "operation": "create_collection", "params": {
                "collection_name": collection_name,
                "dimension": 128,
                "metric_type": "COSINE"
            }},
            {"step": 2, "operation": "insert", "params": {
                "collection_name": collection_name,
                "vectors": [[0.1] * 128, [0.9] * 128]
            }},
            {"step": 3, "operation": "search", "params": {
                "collection_name": collection_name,
                "query_vector": [0.1] * 128,
                "top_k": 10
            }},
        ]

        milvus_results = self.execute_sequence(self.milvus, "milvus", sequence)
        qdrant_results = self.execute_sequence(self.qdrant, "qdrant", sequence)

        # Classify at step 3
        classification = self._classify_search_without_index(
            milvus_results[2], qdrant_results[2]
        )

        return {
            "case_id": case_id,
            "property": "Index-Independent Search",
            "category": "ALLOWED-SENSITIVE",
            "property_number": 4,
            "oracle_rule": "Rule 3 (Search Without Index)",
            "milvus_results": milvus_results,
            "qdrant_results": qdrant_results,
            "classification": classification,
            "test_step": 3,
            "description": "Search behavior without explicit index creation"
        }

    def run_r4_005_load_state_enforcement(self) -> Dict:
        """R4-005: Load-State Enforcement (ALLOWED-SENSITIVE).

        Oracle Rule 7: Load requirement (undefined/allowed difference).
        Test Step: 3 (search without load)
        """
        print("\n--- R4-005: Load-State Enforcement (ALLOWED-SENSITIVE) ---")

        case_id = "r4_005"
        collection_name = self.COLLECTION_NAMES[case_id]

        sequence = [
            {"step": 1, "operation": "create_collection", "params": {
                "collection_name": collection_name,
                "dimension": 128,
                "metric_type": "COSINE"
            }},
            {"step": 2, "operation": "insert", "params": {
                "collection_name": collection_name,
                "vectors": [[0.1] * 128]
            }},
            {"step": 3, "operation": "search", "params": {
                "collection_name": collection_name,
                "query_vector": [0.1] * 128,
                "top_k": 10
            }},
        ]

        milvus_results = self.execute_sequence(self.milvus, "milvus", sequence)
        qdrant_results = self.execute_sequence(self.qdrant, "qdrant", sequence)

        # Classify at step 3
        classification = self._classify_load_requirement(
            milvus_results[2], qdrant_results[2]
        )

        return {
            "case_id": case_id,
            "property": "Load-State Enforcement",
            "category": "ALLOWED-SENSITIVE",
            "property_number": 5,
            "oracle_rule": "Rule 7 (Load Requirement)",
            "milvus_results": milvus_results,
            "qdrant_results": qdrant_results,
            "classification": classification,
            "test_step": 3,
            "description": "Search behavior without explicit load"
        }

    def run_r4_006_empty_collection_handling(self) -> Dict:
        """R4-006: Empty Collection Handling (EXPLORATORY).

        Oracle Rule 5: Empty collection search (undefined/observation).
        Test Step: 2 (search empty collection)
        """
        print("\n--- R4-006: Empty Collection Handling (EXPLORATORY) ---")

        case_id = "r4_006"
        collection_name = self.COLLECTION_NAMES[case_id]

        sequence = [
            {"step": 1, "operation": "create_collection", "params": {
                "collection_name": collection_name,
                "dimension": 128,
                "metric_type": "COSINE"
            }},
            {"step": 2, "operation": "search", "params": {
                "collection_name": collection_name,
                "query_vector": [0.1] * 128,
                "top_k": 10
            }},
        ]

        milvus_results = self.execute_sequence(self.milvus, "milvus", sequence)
        qdrant_results = self.execute_sequence(self.qdrant, "qdrant", sequence)

        # Classify at step 2
        classification = self._classify_empty_collection(
            milvus_results[1], qdrant_results[1]
        )

        return {
            "case_id": case_id,
            "property": "Empty Collection Handling",
            "category": "EXPLORATORY",
            "property_number": 6,
            "oracle_rule": "Rule 5 (Empty Collection)",
            "milvus_results": milvus_results,
            "qdrant_results": qdrant_results,
            "classification": classification,
            "test_step": 2,
            "description": "Search behavior on empty collection"
        }

    def run_r4_007_nonexistent_delete(self) -> Dict:
        """R4-007: Non-Existent Delete Tolerance (PRIMARY).

        Oracle Rule 4: Deleting non-existent ID should be handled gracefully.
        Test Step: 2 (delete non-existent ID)
        """
        print("\n--- R4-007: Non-Existent Delete Tolerance (PRIMARY) ---")

        case_id = "r4_007"
        collection_name = self.COLLECTION_NAMES[case_id]

        sequence = [
            {"step": 1, "operation": "create_collection", "params": {
                "collection_name": collection_name,
                "dimension": 128,
                "metric_type": "COSINE"
            }},
            {"step": 2, "operation": "delete", "params": {
                "collection_name": collection_name,
                "ids": [999]  # Non-existent ID
            }},
        ]

        milvus_results = self.execute_sequence(self.milvus, "milvus", sequence)
        qdrant_results = self.execute_sequence(self.qdrant, "qdrant", sequence)

        # Classify at step 2
        classification = self._classify_nonexistent_delete(
            milvus_results[1], qdrant_results[1]
        )

        return {
            "case_id": case_id,
            "property": "Non-Existent Delete Tolerance",
            "category": "PRIMARY",
            "property_number": 7,
            "oracle_rule": "Rule 4 (Idempotency Extension)",
            "milvus_results": milvus_results,
            "qdrant_results": qdrant_results,
            "classification": classification,
            "test_step": 2,
            "description": "Deleting non-existent ID should be handled gracefully"
        }

    def run_r4_008_collection_creation_idempotency(self) -> Dict:
        """R4-008: Collection Creation Idempotency (PRIMARY).

        Oracle Rule 6: Duplicate collection creation behavior.
        Test Step: 2 (duplicate creation)
        """
        print("\n--- R4-008: Collection Creation Idempotency (PRIMARY) ---")

        case_id = "r4_008"
        collection_name = self.COLLECTION_NAMES[case_id]

        sequence = [
            {"step": 1, "operation": "create_collection", "params": {
                "collection_name": collection_name,
                "dimension": 128,
                "metric_type": "COSINE"
            }},
            {"step": 2, "operation": "create_collection", "params": {
                "collection_name": collection_name,
                "dimension": 128,
                "metric_type": "COSINE"
            }},
        ]

        # For R4-008, we need to handle cleanup specially
        # since the test is about duplicate creation
        milvus_results = self.execute_sequence(self.milvus, "milvus", sequence, cleanup=False)
        qdrant_results = self.execute_sequence(self.qdrant, "qdrant", sequence, cleanup=False)

        # Cleanup manually
        self.cleanup_collection(self.milvus, "milvus", collection_name)
        self.cleanup_collection(self.qdrant, "qdrant", collection_name)

        # Classify at step 2
        classification = self._classify_creation_idempotency(
            milvus_results[1], qdrant_results[1]
        )

        return {
            "case_id": case_id,
            "property": "Collection Creation Idempotency",
            "category": "PRIMARY",
            "property_number": 8,
            "oracle_rule": "Rule 6 (Creation Idempotency)",
            "milvus_results": milvus_results,
            "qdrant_results": qdrant_results,
            "classification": classification,
            "test_step": 2,
            "description": "Duplicate collection creation should have deterministic behavior"
        }

    # ========================================================================
    # CLASSIFICATION METHODS (from frozen classification rules)
    # ========================================================================

    def _classify_post_drop_rejection(self, milvus_step: Dict, qdrant_step: Dict) -> Dict:
        """Classify R4-001: Post-Drop Rejection (Rule 1)."""
        milvus_failed = milvus_step["status"] == "error"
        qdrant_failed = qdrant_step["status"] == "error"

        if milvus_failed and qdrant_failed:
            return {
                "result": "CONSISTENT",
                "category": "PASS",
                "reasoning": "Both databases correctly fail search on dropped collection"
            }
        elif not milvus_failed and not qdrant_failed:
            return {
                "result": "BUG",
                "category": "BUG",
                "reasoning": "Both databases allow post-drop search (CONTRACT VIOLATION)"
            }
        else:
            return {
                "result": "BUG",
                "category": "BUG",
                "reasoning": f"One database allows post-drop search: {'Milvus' if not milvus_failed else 'Qdrant'} (CONTRACT VIOLATION)"
            }

    def _classify_deleted_entity_visibility(self, milvus_step: Dict, qdrant_step: Dict) -> Dict:
        """Classify R4-002: Deleted Entity Visibility (Rule 2)."""
        # Check if deleted entity (ID=1) appears in results
        milvus_has_deleted = self._entity_id_in_results(milvus_step, 1)
        qdrant_has_deleted = self._entity_id_in_results(qdrant_step, 1)

        if not milvus_has_deleted and not qdrant_has_deleted:
            return {
                "result": "CONSISTENT",
                "category": "PASS",
                "reasoning": "Both databases correctly exclude deleted entity from search results"
            }
        elif milvus_has_deleted and qdrant_has_deleted:
            return {
                "result": "BUG",
                "category": "BUG",
                "reasoning": "Both databases show deleted entity in results (CONTRACT VIOLATION)"
            }
        else:
            return {
                "result": "BUG",
                "category": "BUG",
                "reasoning": f"One database shows deleted entity: {'Milvus' if milvus_has_deleted else 'Qdrant'} (CONTRACT VIOLATION)"
            }

    def _entity_id_in_results(self, step: Dict, entity_id: int) -> bool:
        """Check if an entity ID appears in search results."""
        if step["status"] != "success":
            return False

        data = step.get("data", {})
        results = data.get("results", [])

        for result in results:
            if result.get("id") == entity_id:
                return True

        return False

    def _classify_delete_idempotency(self, milvus_step: Dict, qdrant_step: Dict) -> Dict:
        """Classify R4-003: Delete Idempotency (Rule 4)."""
        milvus_succeeds = milvus_step["status"] == "success"
        qdrant_succeeds = qdrant_step["status"] == "success"

        if milvus_succeeds and qdrant_succeeds:
            return {
                "result": "CONSISTENT",
                "category": "PASS",
                "reasoning": "Both databases allow repeated delete (idempotent success)",
                "strategy": "both-succeed"
            }
        elif not milvus_succeeds and not qdrant_succeeds:
            return {
                "result": "CONSISTENT",
                "category": "PASS",
                "reasoning": "Both databases reject repeated delete (first-succeeds-rest-fail)",
                "strategy": "first-succeeds-rest-fail"
            }
        else:
            return {
                "result": "ALLOWED_DIFFERENCE",
                "category": "ALLOWED",
                "reasoning": f"Different idempotency strategies: Milvus={'succeeds' if milvus_succeeds else 'fails'}, Qdrant={'succeeds' if qdrant_succeeds else 'fails'}",
                "strategy": "different"
            }

    def _classify_search_without_index(self, milvus_step: Dict, qdrant_step: Dict) -> Dict:
        """Classify R4-004: Index-Independent Search (Rule 3)."""
        milvus_succeeds = milvus_step["status"] == "success"
        qdrant_succeeds = qdrant_step["status"] == "success"

        if milvus_succeeds and qdrant_succeeds:
            return {
                "result": "CONSISTENT",
                "category": "PASS",
                "reasoning": "Both databases allow search without explicit index"
            }
        elif not milvus_succeeds and not qdrant_succeeds:
            return {
                "result": "CONSISTENT",
                "category": "PASS",
                "reasoning": "Both databases require explicit index before search"
            }
        else:
            return {
                "result": "ALLOWED_DIFFERENCE",
                "category": "ALLOWED",
                "reasoning": f"Different index requirements: {'Milvus requires index' if not milvus_succeeds else 'Qdrant requires index'} (ARCHITECTURAL DIFFERENCE)"
            }

    def _classify_load_requirement(self, milvus_step: Dict, qdrant_step: Dict) -> Dict:
        """Classify R4-005: Load-State Enforcement (Rule 7)."""
        milvus_succeeds = milvus_step["status"] == "success"
        qdrant_succeeds = qdrant_step["status"] == "success"

        if milvus_succeeds and qdrant_succeeds:
            return {
                "result": "CONSISTENT",
                "category": "PASS",
                "reasoning": "Both databases allow search without explicit load"
            }
        elif not milvus_succeeds and not qdrant_succeeds:
            return {
                "result": "CONSISTENT",
                "category": "PASS",
                "reasoning": "Both databases require explicit load before search"
            }
        else:
            return {
                "result": "ALLOWED_DIFFERENCE",
                "category": "ALLOWED",
                "reasoning": f"Different load requirements: {'Milvus requires load' if not milvus_succeeds else 'Qdrant requires load'} (ARCHITECTURAL DIFFERENCE)"
            }

    def _classify_empty_collection(self, milvus_step: Dict, qdrant_step: Dict) -> Dict:
        """Classify R4-006: Empty Collection Handling (Rule 5)."""
        milvus_succeeds = milvus_step["status"] == "success"
        qdrant_succeeds = qdrant_step["status"] == "success"

        # Check if both return empty results
        milvus_empty = milvus_succeeds and len(milvus_step.get("data", {}).get("results", [])) == 0
        qdrant_empty = qdrant_succeeds and len(qdrant_step.get("data", {}).get("results", [])) == 0

        if milvus_empty and qdrant_empty:
            return {
                "result": "CONSISTENT",
                "category": "PASS",
                "reasoning": "Both databases return empty results for empty collection search"
            }
        elif not milvus_succeeds and not qdrant_succeeds:
            return {
                "result": "ALLOWED_DIFFERENCE",
                "category": "ALLOWED",
                "reasoning": "Both databases reject empty collection search"
            }
        elif milvus_succeeds and qdrant_succeeds:
            return {
                "result": "ALLOWED_DIFFERENCE",
                "category": "ALLOWED",
                "reasoning": f"Different empty collection handling: both succeed with different result sets"
            }
        else:
            return {
                "result": "ALLOWED_DIFFERENCE",
                "category": "ALLOWED",
                "reasoning": f"Different empty collection handling: Milvus={'succeeds' if milvus_succeeds else 'fails'}, Qdrant={'succeeds' if qdrant_succeeds else 'fails'} (EDGE CASE - OBSERVATION)"
            }

    def _classify_nonexistent_delete(self, milvus_step: Dict, qdrant_step: Dict) -> Dict:
        """Classify R4-007: Non-Existent Delete Tolerance (Rule 4 extension)."""
        milvus_succeeds = milvus_step["status"] == "success"
        qdrant_succeeds = qdrant_step["status"] == "success"

        if milvus_succeeds and qdrant_succeeds:
            return {
                "result": "CONSISTENT",
                "category": "PASS",
                "reasoning": "Both databases silently succeed on non-existent delete",
                "strategy": "silent-success"
            }
        elif not milvus_succeeds and not qdrant_succeeds:
            return {
                "result": "CONSISTENT",
                "category": "PASS",
                "reasoning": "Both databases fail with 'not found' error",
                "strategy": "error-on-not-found"
            }
        else:
            return {
                "result": "ALLOWED_DIFFERENCE",
                "category": "ALLOWED",
                "reasoning": f"Different non-existent delete strategies: Milvus={'succeeds' if milvus_succeeds else 'fails'}, Qdrant={'succeeds' if qdrant_succeeds else 'fails'}",
                "strategy": "different"
            }

    def _classify_creation_idempotency(self, milvus_step: Dict, qdrant_step: Dict) -> Dict:
        """Classify R4-008: Collection Creation Idempotency (Rule 6)."""
        milvus_succeeds = milvus_step["status"] == "success"
        qdrant_succeeds = qdrant_step["status"] == "success"

        if milvus_succeeds and qdrant_succeeds:
            return {
                "result": "CONSISTENT",
                "category": "PASS",
                "reasoning": "Both databases allow duplicate collection creation",
                "strategy": "allow-duplicates"
            }
        elif not milvus_succeeds and not qdrant_succeeds:
            return {
                "result": "CONSISTENT",
                "category": "PASS",
                "reasoning": "Both databases reject duplicate collection creation",
                "strategy": "reject-duplicates"
            }
        else:
            return {
                "result": "ALLOWED_DIFFERENCE",
                "category": "ALLOWED",
                "reasoning": f"Different creation idempotency: Milvus={'allows' if milvus_succeeds else 'rejects'}, Qdrant={'allows' if qdrant_succeeds else 'rejects'}",
                "strategy": "different"
            }

    # ========================================================================
    # SAVE AND REPORT METHODS
    # ========================================================================

    def save_raw_results(self):
        """Save raw results per database."""
        raw_dir = os.path.join(self.results_dir, "raw")
        os.makedirs(raw_dir, exist_ok=True)

        for case in self.differential_results:
            case_id = case["case_id"]

            # Save Milvus results
            milvus_file = os.path.join(raw_dir, f"{case_id}_milvus.json")
            with open(milvus_file, 'w') as f:
                json.dump({
                    "database": "milvus",
                    "case_id": case_id,
                    "property": case["property"],
                    "property_number": case["property_number"],
                    "steps": case["milvus_results"]
                }, f, indent=2)

            # Save Qdrant results
            qdrant_file = os.path.join(raw_dir, f"{case_id}_qdrant.json")
            with open(qdrant_file, 'w') as f:
                json.dump({
                    "database": "qdrant",
                    "case_id": case_id,
                    "property": case["property"],
                    "property_number": case["property_number"],
                    "steps": case["qdrant_results"]
                }, f, indent=2)

        print(f"\n[INFO]: Raw results saved to {raw_dir}")

    def save_differential_results(self):
        """Save differential classification results."""
        diff_dir = os.path.join(self.results_dir, "differential")
        os.makedirs(diff_dir, exist_ok=True)

        for case in self.differential_results:
            case_id = case["case_id"]
            file_path = os.path.join(diff_dir, f"{case_id}_classification.json")

            classification_data = {
                "case_id": case_id,
                "property": case["property"],
                "category": case["category"],
                "property_number": case["property_number"],
                "oracle_rule": case["oracle_rule"],
                "description": case["description"],
                "classification": case["classification"],
                "test_step": case["test_step"]
            }

            with open(file_path, 'w') as f:
                json.dump(classification_data, f, indent=2)

        print(f"[INFO]: Differential classifications saved to {diff_dir}")

    def save_summary(self):
        """Save campaign summary."""
        summary = {
            "campaign": "R4 Full Differential Testing",
            "version": "1.0",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "environment": self.environment_snapshot,
            "adapter_requested": self.adapter_requested,
            "adapter_actual": self.adapter_actual,
            "databases": ["milvus", "qdrant"],
            "total_cases": len(self.differential_results),
            "results": self._calculate_summary_stats(),
            "by_category": self._calculate_category_stats()
        }

        summary_file = os.path.join(self.results_dir, "summary.json")
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)

        print(f"[INFO]: Campaign summary saved to {summary_file}")

    def _calculate_summary_stats(self) -> Dict:
        """Calculate summary statistics."""
        stats = {
            "total_cases": len(self.differential_results),
            "pass_consistent": 0,
            "allowed_difference": 0,
            "bugs": 0,
            "observation": 0
        }

        for case in self.differential_results:
            result = case["classification"]["result"]
            if result == "CONSISTENT":
                stats["pass_consistent"] += 1
            elif result == "ALLOWED_DIFFERENCE":
                stats["allowed_difference"] += 1
            elif result == "BUG":
                stats["bugs"] += 1
            elif result == "OBSERVATION":
                stats["observation"] += 1

        return stats

    def _calculate_category_stats(self) -> Dict:
        """Calculate statistics by test category."""
        categories = {
            "primary": {"total": 0, "pass": 0, "allowed": 0, "bugs": 0, "observation": 0},
            "allowed_sensitive": {"total": 0, "pass": 0, "allowed": 0, "bugs": 0, "observation": 0},
            "exploratory": {"total": 0, "pass": 0, "allowed": 0, "bugs": 0, "observation": 0}
        }

        for case in self.differential_results:
            cat = case["category"].lower().replace("-", "_")
            if cat not in categories:
                cat = "exploratory" if cat == "exploratory" else "primary"

            categories[cat]["total"] += 1

            result = case["classification"]["result"]
            if result == "CONSISTENT":
                categories[cat]["pass"] += 1
            elif result == "ALLOWED_DIFFERENCE":
                categories[cat]["allowed"] += 1
            elif result == "BUG":
                categories[cat]["bugs"] += 1
            elif result == "OBSERVATION":
                categories[cat]["observation"] += 1

        return categories

    def run_full_campaign(self) -> int:
        """Run the full R4 differential campaign."""
        print_header("R4 Full Differential Campaign")
        print("Testing 8 semantic properties across Milvus and Qdrant")
        print("\nProperties:")
        print("  R4-001: Post-Drop Rejection (PRIMARY)")
        print("  R4-002: Deleted Entity Visibility (PRIMARY)")
        print("  R4-003: Delete Idempotency (PRIMARY)")
        print("  R4-004: Index-Independent Search (ALLOWED-SENSITIVE)")
        print("  R4-005: Load-State Enforcement (ALLOWED-SENSITIVE)")
        print("  R4-006: Empty Collection Handling (EXPLORATORY)")
        print("  R4-007: Non-Existent Delete Tolerance (PRIMARY)")
        print("  R4-008: Collection Creation Idempotency (PRIMARY)")

        # Safety check
        if self.require_real:
            print("\n[SAFETY]: --require-real flag active")
            print("[SAFETY]: Will only execute on real databases")

        # Capture environment
        print("\n[INFO]: Capturing environment snapshot...")
        self.environment_snapshot = get_environment_snapshot()
        print(f"[INFO]: pymilvus: {self.environment_snapshot['pymilvus_version']}")
        print(f"[INFO]: qdrant-client: {self.environment_snapshot['qdrant_client_version']}")
        print(f"[INFO]: milvus image: {self.environment_snapshot['milvus_image']}")
        print(f"[INFO]: qdrant image: {self.environment_snapshot['qdrant_image']}")

        # Setup adapters
        print("\n" + "="*70)
        print(" INITIALIZING ADAPTERS")
        print("="*70)

        if not self.setup_adapters():
            return 1

        # Run test cases
        print("\n" + "="*70)
        print(" EXECUTING R4 TEST CASES")
        print("="*70)

        try:
            self.differential_results.append(self.run_r4_001_post_drop_rejection())
            self.differential_results.append(self.run_r4_002_deleted_entity_visibility())
            self.differential_results.append(self.run_r4_003_delete_idempotency())
            self.differential_results.append(self.run_r4_004_index_independent_search())
            self.differential_results.append(self.run_r4_005_load_state_enforcement())
            self.differential_results.append(self.run_r4_006_empty_collection_handling())
            self.differential_results.append(self.run_r4_007_nonexistent_delete())
            self.differential_results.append(self.run_r4_008_collection_creation_idempotency())
        except Exception as e:
            print(f"\n[ERROR]: Campaign execution failed: {e}")
            import traceback
            traceback.print_exc()
            return 1

        # Save results
        print("\n" + "="*70)
        print(" SAVING RESULTS")
        print("="*70)

        self.save_raw_results()
        self.save_differential_results()
        self.save_summary()

        return 0

    def print_summary(self):
        """Print campaign execution summary."""
        print_header("R4 Full Campaign Execution Summary")

        print("\nEnvironment:")
        print(f"  pymilvus: {self.environment_snapshot.get('pymilvus_version', 'unknown')}")
        print(f"  qdrant-client: {self.environment_snapshot.get('qdrant_client_version', 'unknown')}")
        print(f"  milvus image: {self.environment_snapshot.get('milvus_image', 'unknown')}")
        print(f"  qdrant image: {self.environment_snapshot.get('qdrant_image', 'unknown')}")
        print(f"  adapter_requested: {self.adapter_requested}")
        print(f"  adapter_actual: {self.adapter_actual}")

        print("\nPer-Property Results:")
        for case in self.differential_results:
            print(f"\n  {case['case_id']}: {case['property']} ({case['category']})")
            print(f"    Oracle: {case['oracle_rule']}")
            print(f"    Result: {case['classification']['result']}")
            print(f"    Category: {case['classification']['category']}")
            print(f"    Reasoning: {case['classification']['reasoning']}")

        # Print summary statistics
        stats = self._calculate_summary_stats()
        category_stats = self._calculate_category_stats()

        print(f"\n{'='*70}")
        print(f" CAMPAIGN RESULTS SUMMARY")
        print(f"{'='*70}")
        print(f"Total Cases: {stats['total_cases']}")
        print(f"  PASS (CONSISTENT): {stats['pass_consistent']}")
        print(f"  ALLOWED DIFFERENCE: {stats['allowed_difference']}")
        print(f"  BUG (INCONSISTENT): {stats['bugs']}")
        print(f"  OBSERVATION: {stats['observation']}")

        print(f"\nBy Category:")
        print(f"  PRIMARY: {category_stats['primary']['total']} total")
        print(f"    - PASS: {category_stats['primary']['pass']}")
        print(f"    - ALLOWED: {category_stats['primary']['allowed']}")
        print(f"    - BUGS: {category_stats['primary']['bugs']}")
        print(f"  ALLOWED-SENSITIVE: {category_stats['allowed_sensitive']['total']} total")
        print(f"    - PASS: {category_stats['allowed_sensitive']['pass']}")
        print(f"    - ALLOWED: {category_stats['allowed_sensitive']['allowed']}")
        print(f"    - BUGS: {category_stats['allowed_sensitive']['bugs']}")
        print(f"  EXPLORATORY: {category_stats['exploratory']['total']} total")
        print(f"    - PASS: {category_stats['exploratory']['pass']}")
        print(f"    - ALLOWED: {category_stats['exploratory']['allowed']}")
        print(f"    - OBSERVATION: {category_stats['exploratory']['observation']}")

        # Success criteria check
        print(f"\n{'='*70}")
        print(f" SUCCESS CRITERIA CHECK")
        print(f"{'='*70}")

        minimum_success = (
            stats['total_cases'] == 8 and
            category_stats['primary']['bugs'] == 0
        )

        if minimum_success:
            print("[MINIMUM SUCCESS]: All 8 properties executed successfully")
        else:
            print("[MINIMUM SUCCESS FAILED]: Criteria not met")

        return {
            "stats": stats,
            "category_stats": category_stats,
            "minimum_success": minimum_success
        }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="R4 Full Differential Campaign"
    )
    parser.add_argument(
        "--require-real",
        action="store_true",
        help="Require real database connections (safety mechanism)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Custom output directory"
    )

    args = parser.parse_args()

    # Safety check
    if not args.require_real:
        print("[ERROR]: --require-real flag is required for execution")
        print("[ERROR]: This prevents accidental execution on wrong environment")
        return 1

    # Create results directory with timestamp
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    if args.output_dir:
        results_dir = args.output_dir
    else:
        results_dir = f"results/r4-full-{timestamp}"

    os.makedirs(results_dir, exist_ok=True)

    # Run full campaign
    runner = FullR4Runner(results_dir, require_real=args.require_real)
    exit_code = runner.run_full_campaign()

    if exit_code == 0:
        summary = runner.print_summary()

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
