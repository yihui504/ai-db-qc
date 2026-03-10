"""Test case generator for SCH006B-001.

SCH-006b: Filter Semantics Verification
Goal: Determine if filter on dynamic scalar fields actually works

Experiment Design:
1. Create collection with dynamic scalar field (category)
2. Insert controlled data with explicit scalar values
3. FLUSH to ensure data visibility
4. Query WITHOUT filter - verify data exists (baseline)
5. Query WITH filter - verify filter semantics work
"""

from pathlib import Path
from typing import Dict, List, Any
import random


class Sch006b001Generator:
    """Generate test cases for SCH006B-001."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def _generate_test_vectors(self, n: int = 10, dim: int = 128) -> List[List[float]]:
        """Generate deterministic test vectors."""
        vectors = []
        for i in range(n):
            v = [random.random() for _ in range(dim)]
            vectors.append(v)
        return vectors

    def generate(self) -> List[Dict[str, Any]]:
        """Generate test cases for filter verification.

        Returns:
            List of test cases with controlled filter experiments
        """
        cases = []

        # Case 1: Basic filter with matching value
        cases.append({
            "case_id": "SCH006B-001",
            "contract_id": "SCH-006",
            "name": "Filter Semantics - Matching Value",
            "description": "Verify filter returns entities where scalar field matches filter value",
            "collection_name": "sch006b_filter_test",
            "dimension": 128,
            "field_types": [
                {"name": "id", "type": "INT64", "is_primary": True, "autoID": False},
                {"name": "vector", "type": "FLOAT_VECTOR", "params": {"dim": 128}},
                {"name": "category", "type": "VARCHAR", "params": {"max_length": 50}, "nullable": True}
            ],
            "insert_data": {
                "entities": [
                    # Category A entities (3)
                    {"id": 1, "vector": self._generate_test_vectors(1, 128)[0], "category": "alpha"},
                    {"id": 2, "vector": self._generate_test_vectors(1, 128)[0], "category": "alpha"},
                    {"id": 3, "vector": self._generate_test_vectors(1, 128)[0], "category": "alpha"},
                    # Category B entities (2)
                    {"id": 4, "vector": self._generate_test_vectors(1, 128)[0], "category": "beta"},
                    {"id": 5, "vector": self._generate_test_vectors(1, 128)[0], "category": "beta"},
                    # No category (1)
                    {"id": 6, "vector": self._generate_test_vectors(1, 128)[0], "category": None}
                ],
                "total_count": 6
            },
            "filter_test": {
                "filter_expression": 'category == "alpha"',
                "expected_min_count": 3,
                "expected_max_count": 3,
                "reasoning": "Exactly 3 entities have category='alpha'"
            },
            "verification_steps": [
                "flush_after_insert",
                "count_total_entities",  # Baseline: should be 6
                "query_with_filter"      # Test: should return 3
            ],
            "oracle_expectations": {
                "total_entity_count": 6,
                "filtered_entity_count": 3,
                "filter_field": "category",
                "filter_value": "alpha"
            }
        })

        # Case 2: Filter with non-matching value
        cases.append({
            "case_id": "SCH006B-002",
            "contract_id": "SCH-006",
            "name": "Filter Semantics - Non-Matching Value",
            "description": "Verify filter returns empty when no entities match",
            "collection_name": "sch006b_filter_test_nomatch",
            "dimension": 128,
            "field_types": [
                {"name": "id", "type": "INT64", "is_primary": True, "autoID": False},
                {"name": "vector", "type": "FLOAT_VECTOR", "params": {"dim": 128}},
                {"name": "category", "type": "VARCHAR", "params": {"max_length": 50}, "nullable": True}
            ],
            "insert_data": {
                "entities": [
                    {"id": 1, "vector": self._generate_test_vectors(1, 128)[0], "category": "alpha"},
                    {"id": 2, "vector": self._generate_test_vectors(1, 128)[0], "category": "beta"},
                ],
                "total_count": 2
            },
            "filter_test": {
                "filter_expression": 'category == "gamma"',
                "expected_min_count": 0,
                "expected_max_count": 0,
                "reasoning": "No entities have category='gamma'"
            },
            "verification_steps": [
                "flush_after_insert",
                "count_total_entities",
                "query_with_filter"
            ],
            "oracle_expectations": {
                "total_entity_count": 2,
                "filtered_entity_count": 0,
                "filter_field": "category",
                "filter_value": "gamma"
            }
        })

        # Case 3: Filter with numeric field (if supported)
        cases.append({
            "case_id": "SCH006B-003",
            "contract_id": "SCH-006",
            "name": "Filter Semantics - Numeric Field",
            "description": "Verify filter works on INT64 scalar field",
            "collection_name": "sch006b_filter_numeric",
            "dimension": 128,
            "field_types": [
                {"name": "id", "type": "INT64", "is_primary": True, "autoID": False},
                {"name": "vector", "type": "FLOAT_VECTOR", "params": {"dim": 128}},
                {"name": "priority", "type": "INT64", "nullable": True}
            ],
            "insert_data": {
                "entities": [
                    {"id": 1, "vector": self._generate_test_vectors(1, 128)[0], "priority": 1},
                    {"id": 2, "vector": self._generate_test_vectors(1, 128)[0], "priority": 5},
                    {"id": 3, "vector": self._generate_test_vectors(1, 128)[0], "priority": 10},
                ],
                "total_count": 3
            },
            "filter_test": {
                "filter_expression": "priority > 3",
                "expected_min_count": 2,
                "expected_max_count": 2,
                "reasoning": "2 entities have priority > 3 (5 and 10)"
            },
            "verification_steps": [
                "flush_after_insert",
                "count_total_entities",
                "query_with_filter"
            ],
            "oracle_expectations": {
                "total_entity_count": 3,
                "filtered_entity_count": 2,
                "filter_field": "priority",
                "filter_value": "> 3"
            }
        })

        return cases

    def save(self, cases: List[Dict[str, Any]], output_path: Path):
        """Save generated cases to file."""
        import json
        output_path.write_text(json.dumps(cases, indent=2))
