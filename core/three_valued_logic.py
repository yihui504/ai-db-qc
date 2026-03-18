"""Three-valued logic system for semantic testing.

This module implements Kleene's three-valued logic (K3) with values:
- TRUE: Definitively true
- FALSE: Definitively false  
- UNKNOWN: Unknown/uncertain (neither true nor false)

Used for handling uncertain test results and partial information in oracle validation.
"""

from __future__ import annotations

from enum import Enum, auto
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass


class TriValue(Enum):
    """Three-valued logic enumeration.
    
    Values:
        TRUE: The proposition is definitely true
        FALSE: The proposition is definitely false
        UNKNOWN: The truth value is unknown or uncertain
    """
    TRUE = 1
    FALSE = 0
    UNKNOWN = -1
    
    def __bool__(self) -> bool:
        """Convert to boolean (UNKNOWN raises exception)."""
        if self == TriValue.TRUE:
            return True
        elif self == TriValue.FALSE:
            return False
        else:
            raise ValueError("Cannot convert UNKNOWN to boolean")
    
    def __str__(self) -> str:
        return self.name
    
    def __repr__(self) -> str:
        return f"TriValue.{self.name}"
    
    @classmethod
    def from_bool(cls, value: bool) -> TriValue:
        """Create TriValue from boolean."""
        return cls.TRUE if value else cls.FALSE
    
    @classmethod
    def from_optional(cls, value: Optional[bool]) -> TriValue:
        """Create TriValue from optional boolean."""
        if value is None:
            return cls.UNKNOWN
        return cls.TRUE if value else cls.FALSE


class TriLogic:
    """Three-valued logic operations (Kleene's strong logic)."""
    
    @staticmethod
    def and_(a: TriValue, b: TriValue) -> TriValue:
        """Logical AND operation.
        
        Truth table:
            T & T = T
            T & F = F
            T & U = U
            F & * = F
            U & F = F
            U & U = U
        """
        if a == TriValue.FALSE or b == TriValue.FALSE:
            return TriValue.FALSE
        if a == TriValue.TRUE and b == TriValue.TRUE:
            return TriValue.TRUE
        return TriValue.UNKNOWN
    
    @staticmethod
    def or_(a: TriValue, b: TriValue) -> TriValue:
        """Logical OR operation.
        
        Truth table:
            T | * = T
            F | T = T
            F | F = F
            F | U = U
            U | T = T
            U | U = U
        """
        if a == TriValue.TRUE or b == TriValue.TRUE:
            return TriValue.TRUE
        if a == TriValue.FALSE and b == TriValue.FALSE:
            return TriValue.FALSE
        return TriValue.UNKNOWN
    
    @staticmethod
    def not_(a: TriValue) -> TriValue:
        """Logical NOT operation.
        
        Truth table:
            !T = F
            !F = T
            !U = U
        """
        if a == TriValue.TRUE:
            return TriValue.FALSE
        elif a == TriValue.FALSE:
            return TriValue.TRUE
        return TriValue.UNKNOWN
    
    @staticmethod
    def implies(a: TriValue, b: TriValue) -> TriValue:
        """Logical implication (a -> b).
        
        Equivalent to: !a | b
        """
        return TriLogic.or_(TriLogic.not_(a), b)
    
    @staticmethod
    def eq(a: TriValue, b: TriValue) -> TriValue:
        """Logical equivalence (a <-> b).
        
        Equivalent to: (a -> b) & (b -> a)
        """
        return TriLogic.and_(
            TriLogic.implies(a, b),
            TriLogic.implies(b, a)
        )
    
    @staticmethod
    def all_(values: List[TriValue]) -> TriValue:
        """Logical AND over a list of values."""
        result = TriValue.TRUE
        for v in values:
            result = TriLogic.and_(result, v)
            if result == TriValue.FALSE:
                break
        return result
    
    @staticmethod
    def any_(values: List[TriValue]) -> TriValue:
        """Logical OR over a list of values."""
        result = TriValue.FALSE
        for v in values:
            result = TriLogic.or_(result, v)
            if result == TriValue.TRUE:
                break
        return result


@dataclass
class TrivalentResult:
    """Result of a trivalent oracle validation.
    
    Attributes:
        value: The trivalent result (TRUE/FALSE/UNKNOWN)
        confidence: Confidence level (0.0-1.0) for UNKNOWN results
        explanation: Human-readable explanation
        evidence: Supporting evidence for the result
        metadata: Additional metadata
    """
    value: TriValue
    confidence: float = 1.0
    explanation: str = ""
    evidence: Dict[str, Any] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.evidence is None:
            self.evidence = {}
        if self.metadata is None:
            self.metadata = {}
        # Clamp confidence to [0, 1]
        self.confidence = max(0.0, min(1.0, self.confidence))
    
    def is_definite(self) -> bool:
        """Check if result is definite (TRUE or FALSE)."""
        return self.value in (TriValue.TRUE, TriValue.FALSE)
    
    def is_true(self) -> bool:
        """Check if result is TRUE."""
        return self.value == TriValue.TRUE
    
    def is_false(self) -> bool:
        """Check if result is FALSE."""
        return self.value == TriValue.FALSE
    
    def is_unknown(self) -> bool:
        """Check if result is UNKNOWN."""
        return self.value == TriValue.UNKNOWN
    
    def to_bool(self, default: bool = False) -> bool:
        """Convert to boolean, using default for UNKNOWN."""
        if self.value == TriValue.TRUE:
            return True
        elif self.value == TriValue.FALSE:
            return False
        return default
    
    @classmethod
    def true(cls, explanation: str = "", **kwargs) -> TrivalentResult:
        """Create a TRUE result."""
        return cls(TriValue.TRUE, explanation=explanation, **kwargs)
    
    @classmethod
    def false(cls, explanation: str = "", **kwargs) -> TrivalentResult:
        """Create a FALSE result."""
        return cls(TriValue.FALSE, explanation=explanation, **kwargs)
    
    @classmethod
    def unknown(cls, explanation: str = "", confidence: float = 0.5, **kwargs) -> TrivalentResult:
        """Create an UNKNOWN result."""
        return cls(TriValue.UNKNOWN, confidence=confidence, explanation=explanation, **kwargs)


class TrivalentOracleMixin:
    """Mixin class for oracles that support trivalent logic.
    
    Provides utility methods for handling UNKNOWN results and
    combining multiple trivalent results.
    """
    
    def combine_results(self, results: List[TrivalentResult]) -> TrivalentResult:
        """Combine multiple trivalent results using AND logic.
        
        Args:
            results: List of trivalent results
            
        Returns:
            Combined result
        """
        if not results:
            return TrivalentResult.true("No results to combine")
        
        # Combine values using trivalent AND
        values = [r.value for r in results]
        combined_value = TriLogic.all_(values)
        
        # Combine explanations
        explanations = [r.explanation for r in results if r.explanation]
        combined_explanation = "; ".join(explanations) if explanations else ""
        
        # Combine evidence
        combined_evidence = {}
        for r in results:
            combined_evidence.update(r.evidence)
        
        # Average confidence for UNKNOWN results
        unknown_results = [r for r in results if r.value == TriValue.UNKNOWN]
        avg_confidence = sum(r.confidence for r in unknown_results) / len(unknown_results) if unknown_results else 1.0
        
        return TrivalentResult(
            value=combined_value,
            confidence=avg_confidence,
            explanation=combined_explanation,
            evidence=combined_evidence
        )
    
    def require_definite(self, result: TrivalentResult, 
                         on_unknown: str = "conservative") -> bool:
        """Convert trivalent result to boolean, handling UNKNOWN.
        
        Args:
            result: Trivalent result to convert
            on_unknown: Strategy for handling UNKNOWN:
                - "conservative": Treat UNKNOWN as False (safe)
                - "optimistic": Treat UNKNOWN as True (risky)
                - "raise": Raise exception for UNKNOWN
                
        Returns:
            Boolean result
            
        Raises:
            ValueError: If on_unknown="raise" and result is UNKNOWN
        """
        if result.value == TriValue.TRUE:
            return True
        elif result.value == TriValue.FALSE:
            return False
        else:  # UNKNOWN
            if on_unknown == "conservative":
                return False
            elif on_unknown == "optimistic":
                return True
            else:  # raise
                raise ValueError(f"Cannot convert UNKNOWN result to boolean: {result.explanation}")


# Convenience functions for creating results
def true_result(explanation: str = "", **kwargs) -> TrivalentResult:
    """Create a TRUE result."""
    return TrivalentResult.true(explanation, **kwargs)


def false_result(explanation: str = "", **kwargs) -> TrivalentResult:
    """Create a FALSE result."""
    return TrivalentResult.false(explanation, **kwargs)


def unknown_result(explanation: str = "", confidence: float = 0.5, **kwargs) -> TrivalentResult:
    """Create an UNKNOWN result."""
    return TrivalentResult.unknown(explanation, confidence, **kwargs)


# Export all public symbols
__all__ = [
    'TriValue',
    'TriLogic',
    'TrivalentResult',
    'TrivalentOracleMixin',
    'true_result',
    'false_result',
    'unknown_result',
]