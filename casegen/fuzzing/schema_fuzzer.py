"""Schema Fuzzer for schema evolution testing.

This fuzzer specializes in testing schema evolution contracts (SCH-005, SCH-006),
focusing on atomicity, backward compatibility, and data preservation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import random
import json

from .base import FuzzingStrategy, FuzzingResult, FuzzingStatus, generate_random_vector


class SchemaFuzzer(FuzzingStrategy):
    """Fuzzer specialized for schema evolution testing.

    Focus areas:
    - Atomicity: Schema operations are all-or-nothing
    - Backward compatibility: Schema changes don't break existing queries
    - Data preservation: Schema changes don't corrupt or lose data
    - Concurrent schema operations: Multiple schema changes at once

    Mutation types:
    - field_addition: Add new fields to schema
    - field_removal: Remove fields from schema
    - field_modification: Change field types or constraints
    - concurrent_operations: Multiple schema operations concurrently
    - invalid_operations: Invalid or malformed schema changes
    - state_transitions: Schema changes during various states (empty, with data, with index)
    """

    def __init__(
        self,
        max_iterations: int = 300,
        seed: Optional[int] = None
    ):
        """Initialize schema fuzzer.

        Args:
            max_iterations: Maximum number of fuzzing iterations
            seed: Random seed for reproducibility
        """
        super().__init__(
            name="SchemaFuzzer",
            max_iterations=max_iterations,
            seed=seed
        )

        # Schema field types to test
        self.field_types = [
            {"name": "text_field", "type": "text"},
            {"name": "int_field", "type": "integer"},
            {"name": "float_field", "type": "float"},
            {"name": "bool_field", "type": "boolean"},
            {"name": "keyword_field", "type": "keyword"},
            {"name": "date_field", "type": "date"},
        ]

    def fuzz(
        self,
        base_case: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> List[FuzzingResult]:
        """Generate schema fuzzed test cases.

        Args:
            base_case: Base test case to fuzz
            context: Additional context for fuzzing

        Returns:
            List of fuzzing results
        """
        results = []

        # Generate schema evolution test cases
        results.extend(self._generate_field_addition_tests(base_case, context))
        results.extend(self._generate_atomicity_tests(base_case, context))
        results.extend(self._generate_backward_compatibility_tests(base_case, context))
        results.extend(self._generate_concurrent_schema_tests(base_case, context))
        results.extend(self._generate_invalid_schema_tests(base_case, context))
        results.extend(self._generate_state_transition_tests(base_case, context))

        # Add to corpus
        for result in results:
            if result.test_case:
                self.add_to_corpus(result.test_case)

        return results

    def _generate_field_addition_tests(
        self,
        base_case: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> List[FuzzingResult]:
        """Generate tests for adding fields to schema.

        Focus: SCH-005 - Backward Compatibility
        """
        results = []

        # Test adding different types of fields
        for field_type in self.field_types:
            test_case = base_case.copy()
            test_case["schema_evolution"] = {
                "action": "add_field",
                "field": field_type,
                "precondition": "collection_exists",
                "verify": [
                    "existing_data_accessible",
                    "existing_queries_work",
                    "data_integrity_preserved"
                ]
            }

            results.append(FuzzingResult(
                status=FuzzingStatus.SUCCESS,
                test_case=test_case,
                seed=self.seed,
                metadata={
                    "focus": "backward_compatibility",
                    "mutation": "field_addition",
                    "field_type": field_type["type"]
                }
            ))

        # Test adding multiple fields at once
        multi_fields = self.field_types[:3]
        test_case = base_case.copy()
        test_case["schema_evolution"] = {
            "action": "add_multiple_fields",
            "fields": multi_fields,
            "precondition": "collection_exists",
            "verify": [
                "all_fields_added",
                "existing_data_accessible",
                "existing_queries_work"
            ]
        }

        results.append(FuzzingResult(
            status=FuzzingStatus.SUCCESS,
            test_case=test_case,
            seed=self.seed,
            metadata={
                "focus": "backward_compatibility",
                "mutation": "field_addition",
                "count": len(multi_fields)
            }
        ))

        return results

    def _generate_atomicity_tests(
        self,
        base_case: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> List[FuzzingResult]:
        """Generate tests for schema operation atomicity.

        Focus: SCH-006 - Schema Atomicity
        """
        results = []

        # Test failed schema operation rollback
        invalid_changes = [
            {"action": "add_field", "field": {"name": "", "type": "text"}},  # Empty name
            {"action": "add_field", "field": {"name": "a" * 300, "type": "text"}},  # Too long
            {"action": "drop_field", "field_name": "nonexistent_field"},  # Nonexistent field
            {"action": "modify_field", "field": {"name": "nonexistent", "new_type": "integer"}},
            {"action": "invalid_action", "params": {}},  # Invalid action
        ]

        for invalid_change in invalid_changes:
            test_case = base_case.copy()
            test_case["schema_evolution"] = {
                "action": "invalid_operation",
                "change": invalid_change,
                "precondition": "collection_exists",
                "expected": "rejected",
                "verify": [
                    "original_schema_intact",
                    "all_data_accessible",
                    "no_partial_changes"
                ]
            }

            results.append(FuzzingResult(
                status=FuzzingStatus.SUCCESS,
                test_case=test_case,
                seed=self.seed,
                metadata={
                    "focus": "atomicity",
                    "mutation": "failed_rollback",
                    "action": invalid_change["action"]
                }
            ))

        # Test concurrent schema operations
        concurrent_operations = [
            ["add_field", "add_field"],
            ["add_field", "drop_field"],
            ["modify_field", "drop_field"],
            ["add_field", "add_field", "add_field"],
        ]

        for operations in concurrent_operations:
            test_case = base_case.copy()
            test_case["schema_evolution"] = {
                "action": "concurrent_operations",
                "operations": operations,
                "precondition": "collection_exists",
                "expected": "one_success_or_all_fail",
                "verify": [
                    "schema_consistent",
                    "no_corruption",
                    "clear_error_if_failed"
                ]
            }

            results.append(FuzzingResult(
                status=FuzzingStatus.SUCCESS,
                test_case=test_case,
                seed=self.seed,
                metadata={
                    "focus": "atomicity",
                    "mutation": "concurrent_operations",
                    "count": len(operations)
                }
            ))

        return results

    def _generate_backward_compatibility_tests(
        self,
        base_case: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> List[FuzzingResult]:
        """Generate tests for backward compatibility.

        Focus: SCH-005 - Queries still work after schema changes
        """
        results = []

        # Test different query types after schema change
        query_types = ["search", "filtered_search", "hybrid_search"]

        for query_type in query_types:
            test_case = base_case.copy()
            test_case["schema_evolution"] = {
                "action": "add_field",
                "field": {"name": "new_field", "type": "text"},
                "precondition": "collection_exists",
                "post_test": {
                    "operation": query_type,
                    "verify": [
                        "query_succeeds",
                        "results_returned",
                        "result_format_consistent"
                    ]
                }
            }

            results.append(FuzzingResult(
                status=FuzzingStatus.SUCCESS,
                test_case=test_case,
                seed=self.seed,
                metadata={
                    "focus": "backward_compatibility",
                    "mutation": "query_after_change",
                    "query_type": query_type
                }
            ))

        # Test filtered search with new field
        test_case = base_case.copy()
        test_case["schema_evolution"] = {
            "action": "add_field",
            "field": {"name": "category", "type": "keyword"},
            "precondition": "collection_exists",
            "post_test": {
                "operation": "filtered_search",
                "filter": {"field": "category", "value": "test"},
                "verify": [
                    "query_succeeds",
                    "results_filtered_correctly"
                ]
            }
        }

        results.append(FuzzingResult(
            status=FuzzingStatus.SUCCESS,
            test_case=test_case,
            seed=self.seed,
            metadata={
                "focus": "backward_compatibility",
                "mutation": "filtered_search_new_field"
            }
        ))

        return results

    def _generate_concurrent_schema_tests(
        self,
        base_case: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> List[FuzzingResult]:
        """Generate tests for concurrent schema and data operations.

        Focus: SCH-006 - Schema changes during active operations
        """
        results = []

        # Schema change during insert operations
        test_case = base_case.copy()
        test_case["concurrent_test"] = {
            "schema_operation": {
                "action": "add_field",
                "field": {"name": "new_field", "type": "integer"}
            },
            "data_operations": [
                {"operation": "insert", "count": 100},
                {"operation": "search", "count": 50}
            ],
            "verify": [
                "no_crashes",
                "data_consistent",
                "schema_change_atomic"
            ]
        }

        results.append(FuzzingResult(
            status=FuzzingStatus.SUCCESS,
            test_case=test_case,
            seed=self.seed,
            metadata={
                "focus": "concurrent_operations",
                "mutation": "schema_during_insert_search"
            }
        ))

        # Schema change during search operations
        test_case = base_case.copy()
        test_case["concurrent_test"] = {
            "schema_operation": {
                "action": "add_field",
                "field": {"name": "metadata", "type": "text"}
            },
            "data_operations": [
                {"operation": "search", "count": 200}
            ],
            "verify": [
                "no_crashes",
                "all_searches_complete",
                "results_consistent"
            ]
        }

        results.append(FuzzingResult(
            status=FuzzingStatus.SUCCESS,
            test_case=test_case,
            seed=self.seed,
            metadata={
                "focus": "concurrent_operations",
                "mutation": "schema_during_search"
            }
        ))

        # Multiple concurrent schema operations
        test_case = base_case.copy()
        test_case["concurrent_test"] = {
            "schema_operations": [
                {"action": "add_field", "field": {"name": "f1", "type": "integer"}},
                {"action": "add_field", "field": {"name": "f2", "type": "text"}},
                {"action": "add_field", "field": {"name": "f3", "type": "boolean"}},
            ],
            "verify": [
                "at_most_one_succeeds",
                "schema_consistent",
                "no_partial_changes"
            ]
        }

        results.append(FuzzingResult(
            status=FuzzingStatus.SUCCESS,
            test_case=test_case,
            seed=self.seed,
            metadata={
                "focus": "concurrent_operations",
                "mutation": "multiple_schema_ops"
            }
        ))

        return results

    def _generate_invalid_schema_tests(
        self,
        base_case: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> List[FuzzingResult]:
        """Generate tests with invalid schema operations.

        Focus: SCH-006 - Invalid operations are properly rejected
        """
        results = []

        # Invalid field names
        invalid_names = [
            "",
            " ",
            "123_invalid",
            "_invalid",
            "invalid/name",
            "invalid.name",
            "invalid name",
            "a" * 300,
            "name-with-dashes",
        ]

        for name in invalid_names:
            test_case = base_case.copy()
            test_case["schema_evolution"] = {
                "action": "add_field",
                "field": {"name": name, "type": "text"},
                "expected": "rejected",
                "verify": [
                    "operation_rejected",
                    "good_error_message",
                    "schema_unchanged"
                ]
            }

            results.append(FuzzingResult(
                status=FuzzingStatus.SUCCESS,
                test_case=test_case,
                seed=self.seed,
                metadata={
                    "focus": "invalid_operations",
                    "mutation": "invalid_field_name",
                    "name": name[:50] + "..." if len(name) > 50 else name
                }
            ))

        # Invalid field types
        invalid_types = [
            {"name": "field1", "type": ""},  # Empty type
            {"name": "field2", "type": "invalid_type"},  # Invalid type
            {"name": "field3", "type": None},  # None type
            {"name": "field4", "type": 123},  # Integer instead of string
        ]

        for field_def in invalid_types:
            test_case = base_case.copy()
            test_case["schema_evolution"] = {
                "action": "add_field",
                "field": field_def,
                "expected": "rejected",
                "verify": [
                    "operation_rejected",
                    "good_error_message",
                    "schema_unchanged"
                ]
            }

            results.append(FuzzingResult(
                status=FuzzingStatus.SUCCESS,
                test_case=test_case,
                seed=self.seed,
                metadata={
                    "focus": "invalid_operations",
                    "mutation": "invalid_field_type",
                    "field_type": str(field_def.get("type"))
                }
            ))

        return results

    def _generate_state_transition_tests(
        self,
        base_case: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> List[FuzzingResult]:
        """Generate tests for schema changes in different states.

        Focus: SCH-005 and SCH-006 - Schema changes in various collection states
        """
        results = []

        # State transitions
        states = [
            {"name": "empty_collection", "has_data": False, "has_index": False},
            {"name": "collection_with_data", "has_data": True, "has_index": False},
            {"name": "collection_with_index", "has_data": True, "has_index": True},
        ]

        for state in states:
            test_case = base_case.copy()
            test_case["schema_evolution"] = {
                "action": "add_field",
                "field": {"name": "state_field", "type": "text"},
                "state": state,
                "verify": [
                    "operation_succeeds_or_appropriate_rejection",
                    "state_consistent",
                    "data_preserved"
                ]
            }

            results.append(FuzzingResult(
                status=FuzzingStatus.SUCCESS,
                test_case=test_case,
                seed=self.seed,
                metadata={
                    "focus": "state_transition",
                    "mutation": "schema_in_state",
                    "state": state["name"]
                }
            ))

        # Schema change during data insert
        test_case = base_case.copy()
        test_case["schema_evolution"] = {
            "action": "add_field",
            "field": {"name": "dynamic_field", "type": "integer"},
            "timing": "during_insert",
            "verify": [
                "atomicity_preserved",
                "data_consistent",
                "schema_final_state_correct"
            ]
        }

        results.append(FuzzingResult(
            status=FuzzingStatus.SUCCESS,
            test_case=test_case,
            seed=self.seed,
            metadata={
                "focus": "state_transition",
                "mutation": "schema_during_insert"
            }
        ))

        # Schema change during index operations
        test_case = base_case.copy()
        test_case["schema_evolution"] = {
            "action": "add_field",
            "field": {"name": "index_field", "type": "text"},
            "timing": "during_index_build",
            "verify": [
                "atomicity_preserved",
                "index_consistent",
                "no_corruption"
            ]
        }

        results.append(FuzzingResult(
            status=FuzzingStatus.SUCCESS,
            test_case=test_case,
            seed=self.seed,
            metadata={
                "focus": "state_transition",
                "mutation": "schema_during_index"
            }
        ))

        return results


def create_schema_evolution_fuzzer() -> SchemaFuzzer:
    """Create a schema evolution fuzzer.

    Returns:
        Configured SchemaFuzzer for schema evolution testing
    """
    return SchemaFuzzer(max_iterations=300)


def create_backward_compatibility_fuzzer() -> SchemaFuzzer:
    """Create a fuzzer focused on backward compatibility.

    Returns:
        Configured SchemaFuzzer focused on SCH-005
    """
    fuzzer = SchemaFuzzer(max_iterations=200)
    # Override fuzz method to focus on backward compatibility
    original_fuzz = fuzzer.fuzz

    def focused_fuzz(base_case, context=None):
        # Only generate backward compatibility tests
        return fuzzer._generate_backward_compatibility_tests(base_case, context)

    fuzzer.fuzz = focused_fuzz
    return fuzzer


def create_atomicity_fuzzer() -> SchemaFuzzer:
    """Create a fuzzer focused on atomicity.

    Returns:
        Configured SchemaFuzzer focused on SCH-006
    """
    fuzzer = SchemaFuzzer(max_iterations=200)
    # Override fuzz method to focus on atomicity
    original_fuzz = fuzzer.fuzz

    def focused_fuzz(base_case, context=None):
        # Only generate atomicity tests
        return fuzzer._generate_atomicity_tests(base_case, context)

    fuzzer.fuzz = focused_fuzz
    return fuzzer


__all__ = [
    'SchemaFuzzer',
    'create_schema_evolution_fuzzer',
    'create_backward_compatibility_fuzzer',
    'create_atomicity_fuzzer',
]
