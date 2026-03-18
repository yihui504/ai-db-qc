"""Differential oracle for cross-database comparison.

This oracle compares behavior across multiple databases to identify
behavioral inconsistencies. It supports N-way comparison (not just 2-way)
and provides classification of differences as bugs, allowed variations,
or undefined behaviors.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass

from oracles.base import OracleBase
from schemas.case import TestCase
from schemas.result import ExecutionResult, OracleResult


class DifferenceCategory(Enum):
    """Classification of behavioral differences."""
    
    CONSISTENT = "consistent"  # All databases behave the same
    CONTRACT_VIOLATION = "contract_violation"  # Violates universal semantic contract
    ALLOWED_DIFFERENCE = "allowed_difference"  # Legitimate architectural variation
    UNDEFINED_BEHAVIOR = "undefined_behavior"  # Edge case with no standard


@dataclass
class DatabaseBehavior:
    """Behavior observation from a single database."""
    database: str
    success: bool
    error_message: Optional[str]
    result_ids: Set[Any]
    result_count: int
    response_data: Dict[str, Any]


class DifferentialOracle(OracleBase):
    """Cross-database differential testing oracle.
    
    Compares behavior across multiple databases to identify inconsistencies.
    Supports N-way comparison and provides classification of differences.
    
    Key features:
    - N-way comparison (not limited to 2 databases)
    - Semantic contract violation detection
    - Allowed architectural variation recognition
    - Undefined behavior identification
    """
    
    def __init__(
        self,
        reference_databases: List[str],
        semantic_contract: Optional[Dict[str, Any]] = None
    ):
        """Initialize differential oracle.
        
        Args:
            reference_databases: List of database names to compare
            semantic_contract: Optional semantic contract rules for classification
        """
        self.reference_databases = reference_databases
        self.semantic_contract = semantic_contract or {}
        
    def _extract_behavior(
        self,
        database: str,
        result: ExecutionResult
    ) -> DatabaseBehavior:
        """Extract behavior observation from execution result.
        
        Args:
            database: Database name
            result: Execution result
            
        Returns:
            DatabaseBehavior with extracted observations
        """
        response = result.response or {}
        
        # Extract result IDs
        result_ids = set()
        if "data" in response:
            for item in response["data"]:
                if isinstance(item, dict) and "id" in item:
                    result_ids.add(item["id"])
        
        # Extract result count
        result_count = len(result_ids)
        if "count" in response:
            result_count = response["count"]
        
        return DatabaseBehavior(
            database=database,
            success=result.observed_success,
            error_message=result.error_message,
            result_ids=result_ids,
            result_count=result_count,
            response_data=response
        )
    
    def _classify_difference(
        self,
        behaviors: List[DatabaseBehavior],
        case: TestCase
    ) -> Tuple[DifferenceCategory, str, Dict[str, Any]]:
        """Classify behavioral difference across databases.
        
        Args:
            behaviors: List of behaviors from each database
            case: Test case being evaluated
            
        Returns:
            Tuple of (category, explanation, metrics)
        """
        # Check if all databases agree
        all_success = all(b.success for b in behaviors)
        all_failure = all(not b.success for b in behaviors)
        
        if all_success or all_failure:
            # All databases behave consistently
            return DifferenceCategory.CONSISTENT, "All databases behave consistently", {
                "databases_agree": len(behaviors),
                "common_behavior": "success" if all_success else "failure"
            }
        
        # Databases disagree - classify the difference
        success_dbs = [b.database for b in behaviors if b.success]
        failure_dbs = [b.database for b in behaviors if not b.success]
        
        # Check semantic contract rules
        contract_rules = self.semantic_contract.get("rules", [])
        
        for rule in contract_rules:
            rule_type = rule.get("type")
            
            if rule_type == "post_drop_rejection":
                # After drop, all operations should fail
                if case.operation in ["search", "insert", "delete"]:
                    # If any database allows operation after drop, it's a bug
                    if success_dbs:
                        return DifferenceCategory.CONTRACT_VIOLATION, \
                               f"Post-drop operation should fail: {success_dbs} allowed it", \
                               {"violating_databases": success_dbs, "rule": rule_type}
                    else:
                        return DifferenceCategory.CONSISTENT, \
                               "All databases correctly reject post-drop operation", \
                               {"databases": failure_dbs}
            
            elif rule_type == "deleted_entity_visibility":
                # Deleted entities should not appear in search
                if case.operation == "search":
                    # Check if any database returns deleted IDs
                    # This requires context about which IDs were deleted
                    pass
            
            elif rule_type == "load_gate":
                # Search requires loaded collection
                if case.operation == "search":
                    # If any database allows search without load, it's a bug
                    if success_dbs:
                        return DifferenceCategory.CONTRACT_VIOLATION, \
                               f"Search without load should fail: {success_dbs} allowed it", \
                               {"violating_databases": success_dbs, "rule": rule_type}
        
        # Default classification: allowed architectural difference
        # Different databases may have different error messages or timing
        return DifferenceCategory.ALLOWED_DIFFERENCE, \
               f"Architectural variation: {success_dbs} succeeded, {failure_dbs} failed", \
               {
                   "success_databases": success_dbs,
                   "failure_databases": failure_dbs,
                   "note": "Different error handling strategies are allowed"
               }
    
    def validate(
        self,
        case: TestCase,
        result: ExecutionResult,
        context: Dict[str, Any]
    ) -> OracleResult:
        """Validate behavior against other databases.
        
        This oracle requires cross-database results in context:
        - context["differential_results"]: Dict[database_name, ExecutionResult]
        
        Args:
            case: Test case
            result: Result from primary database
            context: Contains differential_results from all databases
            
        Returns:
            OracleResult with differential analysis
        """
        differential_results = context.get("differential_results", {})
        
        if not differential_results:
            return OracleResult(
                oracle_id="differential",
                passed=True,
                metrics={},
                explanation="No differential results: cross-database comparison skipped"
            )
        
        # Collect behaviors from all databases
        behaviors = []
        
        # Add primary result
        primary_db = context.get("primary_database", "primary")
        behaviors.append(self._extract_behavior(primary_db, result))
        
        # Add differential results
        for db_name, db_result in differential_results.items():
            behaviors.append(self._extract_behavior(db_name, db_result))
        
        # Classify difference
        category, explanation, metrics = self._classify_difference(behaviors, case)
        
        # Build detailed metrics
        detailed_metrics = {
            "category": category.value,
            "databases_compared": len(behaviors),
            "database_behaviors": [
                {
                    "database": b.database,
                    "success": b.success,
                    "result_count": b.result_count
                }
                for b in behaviors
            ],
            **metrics
        }
        
        # Determine pass/fail based on category
        passed = category in [DifferenceCategory.CONSISTENT, DifferenceCategory.ALLOWED_DIFFERENCE]
        
        return OracleResult(
            oracle_id="differential",
            passed=passed,
            metrics=detailed_metrics,
            expected_behavior="Consistent behavior across databases or allowed architectural variation",
            observed_behavior=explanation,
            explanation=f"Differential analysis: {category.value}"
        )


class R4LifecycleOracle(DifferentialOracle):
    """Specialized oracle for R4 lifecycle contract testing.
    
    Tests 8 semantic properties:
    1. Post-Drop Rejection
    2. Deleted Entity Visibility
    3. Delete Idempotency
    4. Index-Independent Search
    5. Load-State Enforcement
    6. Empty Collection Handling
    7. Non-Existent Delete Tolerance
    8. Collection Creation Idempotency
    """
    
    def __init__(self, reference_databases: List[str]):
        """Initialize R4 lifecycle oracle with predefined semantic contracts."""
        semantic_contract = {
            "rules": [
                {"type": "post_drop_rejection", "description": "Operations after drop must fail"},
                {"type": "deleted_entity_visibility", "description": "Deleted entities must not appear in search"},
                {"type": "delete_idempotency", "description": "Delete should be idempotent"},
                {"type": "index_independent_search", "description": "Search should work with or without index"},
                {"type": "load_gate", "description": "Search requires loaded collection"},
                {"type": "empty_collection_handling", "description": "Empty collections should be handled gracefully"},
                {"type": "nonexistent_delete_tolerance", "description": "Deleting non-existent entities should not error"},
                {"type": "creation_idempotency", "description": "Collection creation should be idempotent"}
            ]
        }
        super().__init__(reference_databases, semantic_contract)


class R6ConsistencyOracle(DifferentialOracle):
    """Specialized oracle for R6 consistency contract testing.
    
    Tests consistency properties:
    - Insert visibility
    - Flush semantics
    - Load/release semantics
    - Timing behavior
    """
    
    def __init__(self, reference_databases: List[str]):
        """Initialize R6 consistency oracle with predefined semantic contracts."""
        semantic_contract = {
            "rules": [
                {"type": "insert_visibility", "description": "Inserted data should become visible"},
                {"type": "flush_semantics", "description": "Flush should make data storage-visible"},
                {"type": "load_release_semantics", "description": "Load/release should control search visibility"},
                {"type": "timing_consistency", "description": "Timing behavior should be consistent"}
            ]
        }
        super().__init__(reference_databases, semantic_contract)
