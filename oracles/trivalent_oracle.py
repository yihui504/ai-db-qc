"""Trivalent oracle implementation using three-valued logic.

This oracle extends the base oracle system with support for UNKNOWN results,
allowing for more nuanced validation when test outcomes are uncertain.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from oracles.base import OracleBase
from core.three_valued_logic import (
    TriValue, TriLogic, TrivalentResult, TrivalentOracleMixin,
    true_result, false_result, unknown_result
)
from schemas.case import TestCase
from schemas.result import ExecutionResult, OracleResult


class TrivalentOracle(OracleBase, TrivalentOracleMixin):
    """Oracle that returns trivalent (three-valued) results.
    
    Unlike traditional oracles that only return PASS/FAIL, this oracle
    can return UNKNOWN when the test outcome is uncertain or cannot be
    definitively determined.
    
    Use cases:
    - Non-deterministic operations (timing-dependent)
    - Partial information scenarios
    - Ambiguous specification interpretations
    - Resource-dependent behaviors
    """
    
    def __init__(
        self,
        name: str = "TrivalentOracle",
        unknown_threshold: float = 0.3,
        on_unknown: str = "conservative"
    ):
        """Initialize trivalent oracle.
        
        Args:
            name: Oracle name
            unknown_threshold: Confidence threshold below which to return UNKNOWN
            on_unknown: Strategy for converting UNKNOWN to boolean:
                - "conservative": Treat UNKNOWN as False
                - "optimistic": Treat UNKNOWN as True
        """
        self.name = name
        self.unknown_threshold = unknown_threshold
        self.on_unknown = on_unknown
    
    def validate(
        self,
        case: TestCase,
        result: ExecutionResult,
        context: Dict[str, Any]
    ) -> OracleResult:
        """Validate execution result using trivalent logic.
        
        Args:
            case: Original test case
            result: Execution result
            context: Additional validation context
            
        Returns:
            OracleResult with trivalent interpretation
        """
        # Perform trivalent validation
        trivalent_result = self._validate_trivalent(case, result, context)
        
        # Convert to standard OracleResult
        passed = self.require_definite(trivalent_result, on_unknown=self.on_unknown)
        
        # Build metrics
        metrics = {
            "trivalent_value": trivalent_result.value.name,
            "confidence": trivalent_result.confidence,
            "is_definite": trivalent_result.is_definite(),
        }
        
        # Add evidence to metrics
        if trivalent_result.evidence:
            metrics["evidence"] = trivalent_result.evidence
        
        return OracleResult(
            passed=passed,
            oracle_name=self.name,
            explanation=trivalent_result.explanation,
            metrics=metrics
        )
    
    def _validate_trivalent(
        self,
        case: TestCase,
        result: ExecutionResult,
        context: Dict[str, Any]
    ) -> TrivalentResult:
        """Perform trivalent validation (to be overridden by subclasses).
        
        Args:
            case: Original test case
            result: Execution result
            context: Additional validation context
            
        Returns:
            TrivalentResult
        """
        # Default implementation: check if operation succeeded
        if result.observed_success:
            return true_result("Operation completed successfully")
        else:
            # Check if failure is expected
            expected_failure = context.get("expected_failure", False)
            if expected_failure:
                return true_result("Expected failure occurred")
            else:
                return false_result(f"Unexpected failure: {result.error_message}")


class TimingAwareOracle(TrivalentOracle):
    """Oracle for timing-dependent operations.
    
    Returns UNKNOWN when timing conditions make results non-deterministic.
    """
    
    def __init__(self, timing_window_ms: float = 1000, **kwargs):
        """Initialize timing-aware oracle.
        
        Args:
            timing_window_ms: Time window in milliseconds for considering
                results as timing-dependent
        """
        super().__init__(name="TimingAwareOracle", **kwargs)
        self.timing_window_ms = timing_window_ms
    
    def _validate_trivalent(
        self,
        case: TestCase,
        result: ExecutionResult,
        context: Dict[str, Any]
    ) -> TrivalentResult:
        """Validate with timing awareness.
        
        If the operation is within the timing window of a state change,
        return UNKNOWN as results may vary based on timing.
        """
        operation = case.operation
        time_since_state_change = context.get("time_since_state_change_ms", float('inf'))
        
        # Check for timing-sensitive operations
        timing_sensitive_ops = ["search", "count", "query"]
        
        if operation in timing_sensitive_ops and time_since_state_change < self.timing_window_ms:
            return unknown_result(
                explanation=f"Operation {operation} within timing window "
                           f"({time_since_state_change}ms < {self.timing_window_ms}ms)",
                confidence=0.5,
                evidence={
                    "timing_window_ms": self.timing_window_ms,
                    "time_since_change_ms": time_since_state_change,
                    "operation": operation
                }
            )
        
        # Otherwise, use standard validation
        return super()._validate_trivalent(case, result, context)


class ResourceDependentOracle(TrivalentOracle):
    """Oracle for resource-dependent operations.
    
    Returns UNKNOWN when resource constraints may affect results.
    """
    
    def __init__(self, **kwargs):
        super().__init__(name="ResourceDependentOracle", **kwargs)
    
    def _validate_trivalent(
        self,
        case: TestCase,
        result: ExecutionResult,
        context: Dict[str, Any]
    ) -> TrivalentResult:
        """Validate with resource awareness.
        
        If resource constraints are detected, return UNKNOWN as
        results may be affected by resource availability.
        """
        # Check for resource-related error patterns
        resource_errors = [
            "memory", "disk", "quota", "limit exceeded",
            "resource", "capacity", "insufficient"
        ]
        
        error_message = (result.error_message or "").lower()
        
        if any(pattern in error_message for pattern in resource_errors):
            return unknown_result(
                explanation=f"Resource constraint detected: {result.error_message}",
                confidence=0.7,
                evidence={
                    "error_message": result.error_message,
                    "resource_error": True
                }
            )
        
        # Check for resource warnings in context
        resource_warning = context.get("resource_warning", False)
        if resource_warning:
            return unknown_result(
                explanation="Resource warning in context",
                confidence=0.6,
                evidence={"resource_warning": resource_warning}
            )
        
        return super()._validate_trivalent(case, result, context)


class ConsensusOracle(TrivalentOracle):
    """Oracle that requires consensus from multiple databases.
    
    Returns UNKNOWN when databases disagree and no clear majority exists.
    """
    
    def __init__(
        self,
        databases: List[str],
        consensus_threshold: float = 0.6,
        **kwargs
    ):
        """Initialize consensus oracle.
        
        Args:
            databases: List of database names to compare
            consensus_threshold: Minimum fraction of databases that must agree
        """
        super().__init__(name="ConsensusOracle", **kwargs)
        self.databases = databases
        self.consensus_threshold = consensus_threshold
    
    def _validate_trivalent(
        self,
        case: TestCase,
        result: ExecutionResult,
        context: Dict[str, Any]
    ) -> TrivalentResult:
        """Validate based on cross-database consensus.
        
        Compares results across multiple databases and returns:
        - TRUE if consensus exists for success
        - FALSE if consensus exists for failure
        - UNKNOWN if no clear consensus
        """
        # Get results from all databases
        db_results = context.get("database_results", {})
        
        if not db_results:
            return unknown_result(
                explanation="No database results available for consensus",
                confidence=0.0
            )
        
        # Count successes and failures
        successes = sum(1 for r in db_results.values() if r.get("success", False))
        failures = len(db_results) - successes
        total = len(db_results)
        
        success_ratio = successes / total
        failure_ratio = failures / total
        
        # Check for consensus
        if success_ratio >= self.consensus_threshold:
            return true_result(
                explanation=f"Consensus for success: {successes}/{total} databases",
                evidence={
                    "successes": successes,
                    "failures": failures,
                    "total": total,
                    "ratio": success_ratio
                }
            )
        elif failure_ratio >= self.consensus_threshold:
            return false_result(
                explanation=f"Consensus for failure: {failures}/{total} databases",
                evidence={
                    "successes": successes,
                    "failures": failures,
                    "total": total,
                    "ratio": failure_ratio
                }
            )
        else:
            # No clear consensus
            return unknown_result(
                explanation=f"No consensus: {successes} success, {failures} failure out of {total}",
                confidence=max(success_ratio, failure_ratio),
                evidence={
                    "successes": successes,
                    "failures": failures,
                    "total": total,
                    "success_ratio": success_ratio,
                    "failure_ratio": failure_ratio
                }
            )


class CompositeTrivalentOracle(TrivalentOracle):
    """Composite oracle that combines multiple trivalent oracles.
    
    Uses trivalent logic to combine results from multiple oracles.
    """
    
    def __init__(
        self,
        oracles: List[TrivalentOracle],
        combination_mode: str = "all",
        **kwargs
    ):
        """Initialize composite oracle.
        
        Args:
            oracles: List of trivalent oracles to combine
            combination_mode: How to combine results:
                - "all": All must pass (AND logic)
                - "any": At least one must pass (OR logic)
                - "majority": Majority must pass
        """
        super().__init__(name="CompositeTrivalentOracle", **kwargs)
        self.oracles = oracles
        self.combination_mode = combination_mode
    
    def _validate_trivalent(
        self,
        case: TestCase,
        result: ExecutionResult,
        context: Dict[str, Any]
    ) -> TrivalentResult:
        """Validate by combining multiple oracles.
        
        Runs all child oracles and combines their results using
        trivalent logic based on the combination mode.
        """
        results = []
        
        for oracle in self.oracles:
            trivalent_result = oracle._validate_trivalent(case, result, context)
            results.append(trivalent_result)
        
        # Combine based on mode
        if self.combination_mode == "all":
            return self.combine_results(results)
        elif self.combination_mode == "any":
            values = [r.value for r in results]
            combined_value = TriLogic.any_(values)
            
            # Find first TRUE or last FALSE result for explanation
            explanation_result = None
            for r in results:
                if r.value == TriValue.TRUE:
                    explanation_result = r
                    break
            if explanation_result is None and results:
                explanation_result = results[-1]
            
            return TrivalentResult(
                value=combined_value,
                explanation=explanation_result.explanation if explanation_result else "",
                evidence={"combined_results": len(results)}
            )
        elif self.combination_mode == "majority":
            true_count = sum(1 for r in results if r.value == TriValue.TRUE)
            false_count = sum(1 for r in results if r.value == TriValue.FALSE)
            unknown_count = sum(1 for r in results if r.value == TriValue.UNKNOWN)
            total = len(results)
            
            if true_count > total / 2:
                return true_result(
                    f"Majority ({true_count}/{total}) agree on TRUE",
                    evidence={"true_count": true_count, "false_count": false_count, "unknown_count": unknown_count}
                )
            elif false_count > total / 2:
                return false_result(
                    f"Majority ({false_count}/{total}) agree on FALSE",
                    evidence={"true_count": true_count, "false_count": false_count, "unknown_count": unknown_count}
                )
            else:
                return unknown_result(
                    f"No majority: {true_count} TRUE, {false_count} FALSE, {unknown_count} UNKNOWN",
                    confidence=0.5,
                    evidence={"true_count": true_count, "false_count": false_count, "unknown_count": unknown_count}
                )
        else:
            return unknown_result(f"Unknown combination mode: {self.combination_mode}")


# Factory function for creating common oracle configurations
def create_trivalent_oracle_set() -> Dict[str, TrivalentOracle]:
    """Create a standard set of trivalent oracles.
    
    Returns:
        Dictionary of oracle name -> oracle instance
    """
    return {
        "basic": TrivalentOracle(),
        "timing_aware": TimingAwareOracle(),
        "resource_dependent": ResourceDependentOracle(),
        "consensus": ConsensusOracle(databases=["milvus", "qdrant", "weaviate", "pgvector"]),
    }


__all__ = [
    'TrivalentOracle',
    'TimingAwareOracle',
    'ResourceDependentOracle',
    'ConsensusOracle',
    'CompositeTrivalentOracle',
    'create_trivalent_oracle_set',
]