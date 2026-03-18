"""Strategy selector for choosing and orchestrating fuzzing strategies."""

from typing import Any, Dict, List, Optional, Type
from enum import Enum
import random

from casegen.fuzzing.base import FuzzingStrategy, FuzzingResult, FeedbackCollector
from casegen.fuzzing.random_fuzzer import RandomFuzzer
from casegen.fuzzing.boundary_fuzzer import BoundaryFuzzer
from casegen.fuzzing.arithmetic_fuzzer import ArithmeticFuzzer
from casegen.fuzzing.dictionary_fuzzer import DictionaryFuzzer
from casegen.fuzzing.splicing_fuzzer import SplicingFuzzer
from casegen.fuzzing.crossover_fuzzer import CrossoverFuzzer


class SelectionMode(Enum):
    """Strategy selection modes."""
    RANDOM = "random"
    ROUND_ROBIN = "round_robin"
    FEEDBACK_DRIVEN = "feedback_driven"
    ADAPTIVE = "adaptive"


class StrategySelector:
    """Selects and orchestrates fuzzing strategies.
    
    Supports multiple selection modes:
    - RANDOM: Randomly select strategy each iteration
    - ROUND_ROBIN: Cycle through strategies in order
    - FEEDBACK_DRIVEN: Use feedback to guide strategy selection
    - ADAPTIVE: Dynamically adjust based on success rates
    """
    
    # Registry of available strategies
    STRATEGY_REGISTRY: Dict[str, Type[FuzzingStrategy]] = {
        "random": RandomFuzzer,
        "boundary": BoundaryFuzzer,
        "arithmetic": ArithmeticFuzzer,
        "dictionary": DictionaryFuzzer,
        "splicing": SplicingFuzzer,
        "crossover": CrossoverFuzzer,
    }
    
    def __init__(
        self,
        mode: SelectionMode = SelectionMode.FEEDBACK_DRIVEN,
        seed: Optional[int] = None
    ):
        """Initialize strategy selector.
        
        Args:
            mode: Strategy selection mode
            seed: Random seed for reproducibility
        """
        self.mode = mode
        self.seed = seed
        self.rng = random.Random(seed)
        
        # Strategy instances
        self.strategies: Dict[str, FuzzingStrategy] = {}
        
        # Selection state
        self._round_robin_index = 0
        self._strategy_scores: Dict[str, float] = {}
        self._strategy_attempts: Dict[str, int] = {}
        self._strategy_successes: Dict[str, int] = {}
        
        # Feedback collector
        self.feedback_collector = FeedbackCollector()
        
        # Initialize all strategies
        self._initialize_strategies()
    
    def _initialize_strategies(self):
        """Initialize all registered strategy instances."""
        for name, strategy_class in self.STRATEGY_REGISTRY.items():
            self.strategies[name] = strategy_class(seed=self.seed)
            self._strategy_scores[name] = 1.0  # Initial score
            self._strategy_attempts[name] = 0
            self._strategy_successes[name] = 0
    
    def select_strategy(self) -> FuzzingStrategy:
        """Select a fuzzing strategy based on current mode.
        
        Returns:
            Selected strategy instance
        """
        if self.mode == SelectionMode.RANDOM:
            return self._select_random()
        elif self.mode == SelectionMode.ROUND_ROBIN:
            return self._select_round_robin()
        elif self.mode == SelectionMode.FEEDBACK_DRIVEN:
            return self._select_feedback_driven()
        elif self.mode == SelectionMode.ADAPTIVE:
            return self._select_adaptive()
        else:
            return self._select_random()
    
    def _select_random(self) -> FuzzingStrategy:
        """Randomly select a strategy."""
        strategy_name = self.rng.choice(list(self.strategies.keys()))
        return self.strategies[strategy_name]
    
    def _select_round_robin(self) -> FuzzingStrategy:
        """Select strategy in round-robin order."""
        strategy_names = list(self.strategies.keys())
        strategy_name = strategy_names[self._round_robin_index % len(strategy_names)]
        self._round_robin_index += 1
        return self.strategies[strategy_name]
    
    def _select_feedback_driven(self) -> FuzzingStrategy:
        """Select strategy based on feedback."""
        # Get focus areas from feedback collector
        focus_areas = self.feedback_collector.suggest_focus_areas()
        
        # Map focus areas to strategies (simplified mapping)
        area_strategy_map = {
            "error_type:param_validation": "boundary",
            "error_type:range_error": "arithmetic",
            "underrepresented:search": "random",
        }
        
        # Try to match focus area to strategy
        for area in focus_areas:
            if area in area_strategy_map:
                strategy_name = area_strategy_map[area]
                if strategy_name in self.strategies:
                    return self.strategies[strategy_name]
        
        # Fall back to weighted random based on scores
        return self._select_weighted_random()
    
    def _select_adaptive(self) -> FuzzingStrategy:
        """Select strategy based on adaptive success rates."""
        # Calculate success rates
        success_rates = {}
        for name in self.strategies.keys():
            attempts = self._strategy_attempts[name]
            successes = self._strategy_successes[name]
            if attempts > 0:
                success_rates[name] = successes / attempts
            else:
                success_rates[name] = 0.5  # Default for untried strategies
        
        # Select strategy with highest success rate (with exploration)
        if self.rng.random() < 0.2:  # 20% exploration
            return self._select_random()
        else:
            # Exploitation: pick best strategy
            best_strategy = max(success_rates, key=success_rates.get)
            return self.strategies[best_strategy]
    
    def _select_weighted_random(self) -> FuzzingStrategy:
        """Select strategy using weighted random based on scores."""
        strategy_names = list(self.strategies.keys())
        weights = [self._strategy_scores[name] for name in strategy_names]
        
        total_weight = sum(weights)
        if total_weight == 0:
            return self._select_random()
        
        # Weighted random selection
        r = self.rng.uniform(0, total_weight)
        cumulative = 0
        for name, weight in zip(strategy_names, weights):
            cumulative += weight
            if r <= cumulative:
                return self.strategies[name]
        
        return self.strategies[strategy_names[-1]]
    
    def execute_fuzzing(
        self,
        base_case: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        num_iterations: int = 10
    ) -> List[FuzzingResult]:
        """Execute fuzzing using selected strategies.
        
        Args:
            base_case: Base test case to fuzz
            context: Additional context
            num_iterations: Number of fuzzing iterations
            
        Returns:
            List of all fuzzing results
        """
        all_results = []
        
        for i in range(num_iterations):
            # Select strategy
            strategy = self.select_strategy()
            strategy_name = self._get_strategy_name(strategy)
            
            # Update attempts
            self._strategy_attempts[strategy_name] += 1
            
            # Execute fuzzing
            results = strategy.fuzz(base_case, context)
            all_results.extend(results)
            
            # Update feedback and scores
            self._update_scores(strategy_name, results)
            
            # Record in feedback collector
            for result in results:
                self.feedback_collector.record_execution(
                    test_case=result.test_case or {},
                    result={
                        "success": result.status.value == "success",
                        "error_type": result.metadata.get("error")
                    }
                )
        
        return all_results
    
    def _get_strategy_name(self, strategy: FuzzingStrategy) -> str:
        """Get the registered name of a strategy."""
        for name, strat in self.strategies.items():
            if strat == strategy:
                return name
        return "unknown"
    
    def _update_scores(self, strategy_name: str, results: List[FuzzingResult]):
        """Update strategy scores based on results."""
        if not results:
            return
        
        # Count successes
        successes = sum(1 for r in results if r.status.value == "success")
        self._strategy_successes[strategy_name] += successes
        
        # Update score (exponential moving average)
        success_rate = successes / len(results)
        old_score = self._strategy_scores[strategy_name]
        new_score = 0.7 * old_score + 0.3 * success_rate * 10
        self._strategy_scores[strategy_name] = max(0.1, new_score)
    
    def get_strategy_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all strategies.
        
        Returns:
            Dictionary with strategy statistics
        """
        stats = {}
        for name in self.strategies.keys():
            attempts = self._strategy_attempts[name]
            successes = self._strategy_successes[name]
            stats[name] = {
                "attempts": attempts,
                "successes": successes,
                "success_rate": successes / attempts if attempts > 0 else 0,
                "score": self._strategy_scores[name]
            }
        return stats
    
    def reset(self):
        """Reset all strategies and statistics."""
        for strategy in self.strategies.values():
            strategy.reset()
        
        self._round_robin_index = 0
        for name in self._strategy_scores:
            self._strategy_scores[name] = 1.0
            self._strategy_attempts[name] = 0
            self._strategy_successes[name] = 0
        
        self.feedback_collector = FeedbackCollector()


def create_selector(
    mode: str = "feedback_driven",
    seed: Optional[int] = None
) -> StrategySelector:
    """Factory function to create a strategy selector.
    
    Args:
        mode: Selection mode (random, round_robin, feedback_driven, adaptive)
        seed: Random seed
        
    Returns:
        Configured StrategySelector instance
    """
    mode_map = {
        "random": SelectionMode.RANDOM,
        "round_robin": SelectionMode.ROUND_ROBIN,
        "feedback_driven": SelectionMode.FEEDBACK_DRIVEN,
        "adaptive": SelectionMode.ADAPTIVE,
    }
    
    selection_mode = mode_map.get(mode, SelectionMode.FEEDBACK_DRIVEN)
    return StrategySelector(mode=selection_mode, seed=seed)
