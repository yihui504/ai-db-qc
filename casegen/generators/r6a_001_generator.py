"""Test case generator for R6A-001.

R6A-001: Consistency / Visibility Campaign
Round 1 Core: CONS-001, CONS-002, CONS-003, CONS-005
Round 2 Extended: CONS-004, CONS-006
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
        """Generate 4 core test cases for round 1."""
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
                "insert_count_immediate": True,
                "flush_enables_storage_visibility": True
            }
        })

        # CONS-002: Storage-Visible vs Search-Visible Relationship
        cases.append({
            "case_id": "R6A-002",
            "contract_id": "CONS-002",
            "name": "Storage-Visible vs Search-Visible Relationship",
            "description": "flush enables storage_count; search visibility depends on load state",
            "collection_name": f"{self.collection_prefix}storage_vs_search",
            "dimension": 128,
            "num_entities": 5,
            "operation_sequence": [
                "create_collection",
                "insert",
                "flush",
                "check_storage_count",  # storage-visible
                "search_without_load",  # search not visible (unloaded)
                "load",
                "search_with_load"  # search visible (loaded)
            ],
            "expected_classification": "OBSERVATION",
            "oracle_strategy": "CONSERVATIVE",
            "evidence_needed": {
                "storage_count_post_flush": 5,
                "search_without_load": "0 or error",
                "search_with_load": 5
            },
            "oracle_expectations": {
                "flush_enables_storage_visibility": True,
                "search_requires_load": True
            },
            "scope_note": "Focus: storage-visible vs search-visible relationship. Load gate handled by CONS-003."
        })

        # CONS-003: Load/Release/Reload Gate on Search Visibility
        cases.append({
            "case_id": "R6A-003",
            "contract_id": "CONS-003",
            "name": "Load/Release/Reload Gate on Search Visibility",
            "description": "search requires loaded collection; unload blocks search; reload restores search",
            "collection_name": f"{self.collection_prefix}load_gate",
            "dimension": 128,
            "num_entities": 3,
            "operation_sequence": [
                "create_collection",
                "insert",
                "flush",
                "build_index",
                "load",
                "search_baseline",  # establish baseline
                "release",  # unload
                "verify_unloaded",  # confirm unloaded
                "search_unloaded",  # should fail (EXPECTED_FAILURE)
                "reload",
                "search_after_reload"  # should match baseline
            ],
            "expected_classification": "PASS",
            "oracle_strategy": "STRICT",
            "evidence_needed": {
                "search_unloaded": "EXPECTED_FAILURE or error",
                "search_after_reload": "results match baseline"
            },
            "oracle_expectations": {
                "load_gate_enforced": True,
                "reload_restores_search": True,
                "data_preserved": True
            },
            "scope_note": "Focus: load/release/reload gate. Flush/storage-visible handled by CONS-002."
        })

        # CONS-005: Release Preserves Storage Data
        cases.append({
            "case_id": "R6A-005",
            "contract_id": "CONS-005",
            "name": "Release Preserves Storage Data",
            "description": "release() preserves storage_count; reload restores search visibility",
            "collection_name": f"{self.collection_prefix}release_preserves",
            "dimension": 128,
            "num_entities": 5,
            "operation_sequence": [
                "create_collection",
                "insert",
                "flush",
                "build_index",
                "load",
                "record_storage_count_baseline",
                "search_baseline",
                "release",
                "check_storage_count_after_release",  # should be unchanged
                "reload",
                "search_after_reload"  # should match baseline
            ],
            "expected_classification": "PASS",
            "oracle_strategy": "STRICT",
            "evidence_needed": {
                "storage_count_unchanged_after_release": True,
                "search_after_reload_matches_baseline": True
            },
            "oracle_expectations": {
                "data_preserved_across_release": True,
                "reload_restores_search": True
            }
        })

        return cases

    def generate_round2(self) -> List[Dict[str, Any]]:
        """Generate 2 extended test cases for round 2."""
        cases = []

        # CONS-004: Insert-Search Timing Window Observation
        cases.append({
            "case_id": "R6A-004",
            "contract_id": "CONS-004",
            "name": "Insert-Search Timing Window Observation",
            "description": "observe insert-search visibility within tested wait window (no strong conclusion预设)",
            "collection_name": f"{self.collection_prefix}timing_window",
            "dimension": 128,
            "num_entities": 5,
            "operation_sequence": [
                "create_collection",
                "build_index",
                "load",
                "insert",
                "search_t0_immediate",
                "wait_1_second",
                "search_t1_after_wait",
                "flush",
                "search_after_flush_baseline"
            ],
            "expected_classification": "OBSERVATION",  # or EXPERIMENT_DESIGN_ISSUE
            "oracle_strategy": "CONSERVATIVE",
            "evidence_needed": {
                "search_t0_count": "document actual value",
                "search_t1_count": "document actual value",
                "search_after_flush_count": "baseline (expected 5)"
            },
            "oracle_expectations": {
                "note": "Do not preset strong conclusions. Document observed behavior."
            },
            "round": "round2_extended"
        })

        # CONS-006: Repeated Flush Stability
        cases.append({
            "case_id": "R6A-006",
            "contract_id": "CONS-006",
            "name": "Repeated Flush Stability",
            "description": "repeated flush should not introduce contradictory visibility regressions",
            "collection_name": f"{self.collection_prefix}flush_stability",
            "dimension": 128,
            "num_entities": 5,
            "operation_sequence": [
                "create_collection",
                "insert",
                "flush_first",
                "check_storage_state_before_second",
                "check_search_state_before_second",  # if loaded
                "flush_second",
                "check_storage_state_after_second",
                "check_search_state_after_second"  # if loaded
            ],
            "expected_classification": "OBSERVATION",
            "oracle_strategy": "CONSERVATIVE",
            "evidence_needed": {
                "storage_state_before": "document num_entities",
                "storage_state_after": "document num_entities",
                "search_state_before": "document search count (if loaded)",
                "search_state_after": "document search count (if loaded)"
            },
            "oracle_expectations": {
                "no_contradictory_regressions": "storage and search states should not regress"
            },
            "round": "round2_extended"
        })

        return cases

    def save(self, cases: List[Dict[str, Any]], output_path: Path):
        """Save generated cases to file."""
        import json
        output_path.write_text(json.dumps(cases, indent=2))
