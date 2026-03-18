"""Base classes for fuzzing strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import random
import hashlib
import json


class FuzzingStatus(Enum):
    """Status of a fuzzing operation."""
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


@dataclass
class FuzzingResult:
    """Result of a fuzzing operation.
    
    Attributes:
        status: Operation status
        test_case: Generated test case
        seed: Random seed used
        generation_time_ms: Time taken to generate
        metadata: Additional metadata
    """
    status: FuzzingStatus
    test_case: Optional[Dict[str, Any]] = None
    seed: Optional[int] = None
    generation_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CoverageInfo:
    """Coverage information for feedback-driven fuzzing.
    
    Attributes:
        branches_hit: Set of branch IDs hit
        lines_hit: Set of line numbers hit
        functions_called: Set of function names called
        total_branches: Total number of branches
        total_lines: Total number of lines
    """
    branches_hit: set = field(default_factory=set)
    lines_hit: set = field(default_factory=set)
    functions_called: set = field(default_factory=set)
    total_branches: int = 0
    total_lines: int = 0
    
    @property
    def branch_coverage(self) -> float:
        """Calculate branch coverage percentage."""
        if self.total_branches == 0:
            return 0.0
        return len(self.branches_hit) / self.total_branches
    
    @property
    def line_coverage(self) -> float:
        """Calculate line coverage percentage."""
        if self.total_lines == 0:
            return 0.0
        return len(self.lines_hit) / self.total_lines
    
    def merge(self, other: CoverageInfo) -> CoverageInfo:
        """Merge coverage from another CoverageInfo."""
        return CoverageInfo(
            branches_hit=self.branches_hit | other.branches_hit,
            lines_hit=self.lines_hit | other.lines_hit,
            functions_called=self.functions_called | other.functions_called,
            total_branches=max(self.total_branches, other.total_branches),
            total_lines=max(self.total_lines, other.total_lines),
        )


class FuzzingStrategy(ABC):
    """Base class for fuzzing strategies.
    
    All fuzzing strategies should inherit from this class and
    implement the fuzz() method.
    """
    
    def __init__(
        self,
        name: str,
        max_iterations: int = 1000,
        seed: Optional[int] = None
    ):
        """Initialize fuzzing strategy.
        
        Args:
            name: Strategy name
            max_iterations: Maximum number of fuzzing iterations
            seed: Random seed for reproducibility
        """
        self.name = name
        self.max_iterations = max_iterations
        self.seed = seed
        self.rng = random.Random(seed)
        self.iteration_count = 0
        self.corpus: List[Dict[str, Any]] = []
        self.coverage_history: List[CoverageInfo] = []
    
    @abstractmethod
    def fuzz(
        self,
        base_case: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> List[FuzzingResult]:
        """Generate fuzzed test cases.
        
        Args:
            base_case: Base test case to fuzz
            context: Additional context for fuzzing
            
        Returns:
            List of fuzzing results
        """
        pass
    
    def reset(self):
        """Reset fuzzing state."""
        self.iteration_count = 0
        self.corpus = []
        self.coverage_history = []
        if self.seed is not None:
            self.rng = random.Random(self.seed)
    
    def add_to_corpus(self, test_case: Dict[str, Any]):
        """Add a test case to the corpus."""
        # Avoid duplicates
        case_hash = self._hash_test_case(test_case)
        if not any(self._hash_test_case(c) == case_hash for c in self.corpus):
            self.corpus.append(test_case)
    
    def _hash_test_case(self, test_case: Dict[str, Any]) -> str:
        """Generate hash for a test case."""
        # Normalize and hash
        normalized = json.dumps(test_case, sort_keys=True, default=str)
        return hashlib.md5(normalized.encode()).hexdigest()[:16]
    
    def get_corpus_size(self) -> int:
        """Get current corpus size."""
        return len(self.corpus)
    
    def select_from_corpus(self) -> Optional[Dict[str, Any]]:
        """Select a random test case from corpus."""
        if not self.corpus:
            return None
        return self.rng.choice(self.corpus)


class SeedPool:
    """Pool of seeds for fuzzing.
    
    Manages interesting seeds for mutation-based fuzzing.
    """
    
    def __init__(self, max_size: int = 1000):
        """Initialize seed pool.
        
        Args:
            max_size: Maximum number of seeds to keep
        """
        self.max_size = max_size
        self.seeds: List[Dict[str, Any]] = []
        self.seed_scores: Dict[str, float] = {}
    
    def add_seed(
        self,
        seed: Dict[str, Any],
        score: float = 0.0,
        coverage: Optional[CoverageInfo] = None
    ):
        """Add a seed to the pool.
        
        Args:
            seed: Seed test case
            score: Interestingness score
            coverage: Coverage information
        """
        seed_hash = self._hash_seed(seed)
        
        # Update score if seed already exists
        if seed_hash in self.seed_scores:
            self.seed_scores[seed_hash] = max(self.seed_scores[seed_hash], score)
            return
        
        # Add new seed
        if len(self.seeds) >= self.max_size:
            # Remove lowest scored seed
            min_hash = min(self.seed_scores, key=self.seed_scores.get)
            self.seeds = [s for s in self.seeds if self._hash_seed(s) != min_hash]
            del self.seed_scores[min_hash]
        
        self.seeds.append(seed)
        self.seed_scores[seed_hash] = score
    
    def select_seed(self, rng: random.Random) -> Optional[Dict[str, Any]]:
        """Select a seed from the pool.
        
        Uses weighted random selection based on scores.
        """
        if not self.seeds:
            return None
        
        # Weight by score (higher score = more likely)
        weights = [self.seed_scores.get(self._hash_seed(s), 1.0) for s in self.seeds]
        total = sum(weights)
        if total == 0:
            return rng.choice(self.seeds)
        
        # Weighted random selection
        r = rng.uniform(0, total)
        cumulative = 0
        for seed, weight in zip(self.seeds, weights):
            cumulative += weight
            if r <= cumulative:
                return seed
        
        return self.seeds[-1]
    
    def _hash_seed(self, seed: Dict[str, Any]) -> str:
        """Generate hash for a seed."""
        normalized = json.dumps(seed, sort_keys=True, default=str)
        return hashlib.md5(normalized.encode()).hexdigest()[:16]
    
    def get_size(self) -> int:
        """Get current pool size."""
        return len(self.seeds)


class FeedbackCollector:
    """Collects and analyzes feedback from test execution.
    
    Used for feedback-driven fuzzing to guide test generation.
    """
    
    def __init__(self):
        """Initialize feedback collector."""
        self.execution_history: List[Dict[str, Any]] = []
        self.error_patterns: Dict[str, int] = {}
        self.success_patterns: Dict[str, int] = {}
        self.coverage_progress: List[float] = []
    
    def record_execution(
        self,
        test_case: Dict[str, Any],
        result: Dict[str, Any],
        coverage: Optional[CoverageInfo] = None
    ):
        """Record test execution result.
        
        Args:
            test_case: Executed test case
            result: Execution result
            coverage: Coverage information
        """
        record = {
            "test_case": test_case,
            "result": result,
            "coverage": coverage,
        }
        self.execution_history.append(record)
        
        # Update patterns
        success = result.get("success", False)
        pattern = self._extract_pattern(test_case)
        
        if success:
            self.success_patterns[pattern] = self.success_patterns.get(pattern, 0) + 1
        else:
            error_type = result.get("error_type", "unknown")
            self.error_patterns[error_type] = self.error_patterns.get(error_type, 0) + 1
        
        # Update coverage progress
        if coverage:
            self.coverage_progress.append(coverage.branch_coverage)
    
    def _extract_pattern(self, test_case: Dict[str, Any]) -> str:
        """Extract pattern from test case for analysis."""
        # Simple pattern: operation type + parameter types
        operation = test_case.get("operation", "unknown")
        params = test_case.get("params", {})
        param_types = [type(v).__name__ for v in params.values()]
        return f"{operation}:{','.join(param_types)}"
    
    def get_error_hotspots(self, top_n: int = 5) -> List[Tuple[str, int]]:
        """Get most common error patterns.
        
        Returns:
            List of (error_type, count) tuples
        """
        sorted_errors = sorted(
            self.error_patterns.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_errors[:top_n]
    
    def get_coverage_trend(self) -> str:
        """Analyze coverage trend.
        
        Returns:
            "improving", "stable", or "stagnant"
        """
        if len(self.coverage_progress) < 10:
            return "insufficient_data"
        
        recent = self.coverage_progress[-10:]
        if recent[-1] > recent[0] * 1.05:
            return "improving"
        elif recent[-1] > recent[0] * 0.95:
            return "stable"
        else:
            return "stagnant"
    
    def suggest_focus_areas(self) -> List[str]:
        """Suggest areas to focus fuzzing on.
        
        Returns:
            List of suggested operation types or patterns
        """
        suggestions = []
        
        # Focus on error hotspots
        hotspots = self.get_error_hotspots(3)
        for error_type, _ in hotspots:
            suggestions.append(f"error_type:{error_type}")
        
        # Focus on underrepresented success patterns
        if self.success_patterns:
            min_pattern = min(self.success_patterns, key=self.success_patterns.get)
            suggestions.append(f"underrepresented:{min_pattern}")
        
        return suggestions


# Utility functions
def generate_random_vector(dim: int, rng: Optional[random.Random] = None) -> List[float]:
    """Generate a random vector.
    
    Args:
        dim: Vector dimension
        rng: Random number generator
        
    Returns:
        Random vector
    """
    if rng is None:
        rng = random.Random()
    return [rng.random() for _ in range(dim)]


def generate_gaussian_vector(dim: int, mu: float = 0, sigma: float = 1,
                             rng: Optional[random.Random] = None) -> List[float]:
    """Generate a vector with Gaussian distributed values.
    
    Args:
        dim: Vector dimension
        mu: Mean
        sigma: Standard deviation
        rng: Random number generator
        
    Returns:
        Gaussian vector
    """
    if rng is None:
        rng = random.Random()
    return [rng.gauss(mu, sigma) for _ in range(dim)]


def mutate_vector(vector: List[float], mutation_rate: float = 0.1,
                  rng: Optional[random.Random] = None) -> List[float]:
    """Mutate a vector.
    
    Args:
        vector: Original vector
        mutation_rate: Probability of mutating each element
        rng: Random number generator
        
    Returns:
        Mutated vector
    """
    if rng is None:
        rng = random.Random()
    
    mutated = []
    for v in vector:
        if rng.random() < mutation_rate:
            # Add Gaussian noise
            mutated.append(v + rng.gauss(0, 0.1))
        else:
            mutated.append(v)
    
    return mutated


__all__ = [
    'FuzzingStatus',
    'FuzzingResult',
    'CoverageInfo',
    'FuzzingStrategy',
    'SeedPool',
    'FeedbackCollector',
    'generate_random_vector',
    'generate_gaussian_vector',
    'mutate_vector',
]