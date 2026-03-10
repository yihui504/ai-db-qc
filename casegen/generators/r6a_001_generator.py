"""Test case generator for R6A-001.

R6A-001: Consistency / Visibility Campaign
Tests: insert visibility, flush effects, load state, timing windows, release, idempotence
"""

import random
from pathlib import Path
from typing import Dict, List, Any


class R6a001Generator:
    """Generate test cases for R6A-001."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.collection_prefix = "r6a_consistency_"

    def _generate_test_vectors(self, n: int = 10, dim: int = 128) -> List[List[float]]:
        """Generate deterministic test vectors."""
        random.seed(42)  # Fixed seed for reproducibility
        vectors = []
        for i in range(n):
            v = [random.random() for _ in range(dim)]
            vectors.append(v)
        return vectors

    def generate(self) -> List[Dict[str, Any]]:
        """Generate 6 test cases for consistency/visibility validation."""
        cases = []

        # CONS-001: Insert Return vs Storage Visibility
        cases.append({
            "case_id": "R6A-001",
            "contract_id": "CONS-001",
            "name": "Insert Return vs Storage Visibility",
            "description": "insert() returns immediately, but storage_count visibility requires flush",
            "collection_name": f"{self.collection_prefix}insert_visibility",
            "dimension": 128,
            "num_entities": 5,
            "operation_sequence": [
                "create_collection",
                "insert",
                "check_insert_count",
                "check_num_entities_pre_flush",
                "flush",
                "check_num_entities_post_flush"
            ],
            "expected_classification": "OBSERVATION",
            "oracle_strategy": "CONSERVATIVE",
            "evidence_needed": {
                "insert_count": 5,
                "num_entities_pre_flush": "deterministic (0 or 5)",
                "num_entities_post_flush": 5
            },
            "oracle_expectations": {
                "insert_count_should_equal": 5,
                "flush_enables_storage_visibility": True
            }
        })

        # CONS-002: Flush Effect on Storage vs Search Visibility
        cases.append({
            "case_id": "R6A-002",
            "contract_id": "CONS-002",
            "name": "Flush Effect on Storage vs Search Visibility",
            "description": "flush enables storage_count, but search requires index update",
            "collection_name": f"{self.collection_prefix}flush_visibility",
            "dimension": 128,
            "num_entities": 5,
            "operation_sequence": [
                "create_collection",
                "insert",
                "flush",
                "check_num_entities",
                "search_without_load",
                "load",
                "search_with_load"
            ],
            "expected_classification": "OBSERVATION",
            "oracle_strategy": "CONSERVATIVE",
            "evidence_needed": {
                "num_entities_post_flush": 5,
                "search_without_load": "0 or error",
                "search_with_load": 5
            },
            "oracle_expectations": {
                "flush_enables_storage_visibility": True,
                "index_update_required_for_search": True
            }
        })

        # CONS-003: Load State Effect on Search Visibility
        cases.append({
            "case_id": "R6A-003",
            "contract_id": "CONS-003",
            "name": "Load State Effect on Search Visibility",
            "description": "search requires loaded collection; unloaded returns EXPECTED_FAILURE",
            "collection_name": f"{self.collection_prefix}load_visibility",
            "dimension": 128,
            "num_entities": 3,
            "operation_sequence": [
                "create_collection",
                "insert",
                "flush",
                "build_index",
                "load",
                "search_baseline",
                "release",
                "verify_unloaded",
                "search_unloaded",
                "reload",
                "search_after_reload"
            ],
            "expected_classification": "PASS",
            "oracle_strategy": "STRICT",
            "evidence_needed": {
                "search_unloaded": "EXPECTED_FAILURE or error",
                "search_after_reload": "results match baseline"
            },
            "oracle_expectations": {
                "load_gate_enforced": True,
                "reload_restores_search": True
            }
        })

        # CONS-004: Insert-Search Timing Window
        cases.append({
            "case_id": "R6A-004",
            "contract_id": "CONS-004",
            "name": "Insert-Search Timing Window",
            "description": "insert → search without flush has deterministic (non-flush) behavior",
            "collection_name": f"{self.collection_prefix}timing_window",
            "dimension": 128,
            "num_entities": 5,
            "operation_sequence": [
                "create_collection",
                "build_index",
                "load",
                "insert",
                "search_immediate",
                "wait_1_second",
                "search_after_wait",
                "flush",
                "search_after_flush"
            ],
            "expected_classification": "OBSERVATION",
            "oracle_strategy": "CONSERVATIVE",
            "evidence_needed": {
                "search_immediate": 0,
                "search_after_wait": 0,
                "search_after_flush": 5
            },
            "oracle_expectations": {
                "wait_without_flush_doesnt_enable_search": True,
                "flush_required_for_search_visibility": True
            }
        })

        # CONS-005: Release Preserves Storage Data
        cases.append({
            "case_id": "R6A-005",
            "contract_id": "CONS-005",
            "name": "Release Preserves Storage Data",
            "description": "release() preserves storage_count; reload restores search visibility",
            "collection_name": f"{self.collection_prefix}release_consistency",
            "dimension": 128,
            "num_entities": 5,
            "operation_sequence": [
                "create_collection",
                "insert",
                "flush",
                "build_index",
                "load",
                "record_num_entities_loaded",
                "search_baseline",
                "release",
                "check_num_entities_after_release",
                "reload",
                "search_after_reload"
            ],
            "expected_classification": "PASS",
            "oracle_strategy": "STRICT",
            "evidence_needed": {
                "num_entities_unchanged_after_release": True,
                "search_after_reload_matches_baseline": True
            },
            "oracle_expectations": {
                "data_preserved_across_release": True,
                "reload_restores_search": True
            }
        })

        # CONS-006: Flush Idempotence
        cases.append({
            "case_id": "R6A-006",
            "contract_id": "CONS-006",
            "name": "Flush Idempotence",
            "description": "multiple flush calls are idempotent (no side effects)",
            "collection_name": f"{self.collection_prefix}flush_idempotence",
            "dimension": 128,
            "num_entities": 5,
            "operation_sequence": [
                "create_collection",
                "insert",
                "flush_first",
                "check_num_entities",
                "flush_second",
                "check_num_entities_unchanged"
            ],
            "expected_classification": "OBSERVATION",
            "oracle_strategy": "CONSERVATIVE",
            "evidence_needed": {
                "num_entities_after_first_flush": 5,
                "num_entities_after_second_flush": 5
            },
            "oracle_expectations": {
                "flush_is_idempotent": True
            }
        })

        return cases

    def save(self, cases: List[Dict[str, Any]], output_path: Path):
        """Save generated cases to file."""
        import json
        output_path.write_text(json.dumps(cases, indent=2))
