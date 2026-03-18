"""Integration module for Fuzzing strategies.

This module integrates the 6 fuzzing strategies (Random, Boundary, Arithmetic,
Dictionary, Splicing, Crossover) into the existing ai-db-qc pipeline,
enabling feedback-driven test case generation.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from adapters.base import AdapterBase
from casegen.fuzzing.base import FuzzingResult, FuzzingStatus, CoverageInfo, FeedbackCollector
from casegen.fuzzing.random_fuzzer import RandomFuzzer
from casegen.fuzzing.boundary_fuzzer import BoundaryFuzzer
from casegen.fuzzing.arithmetic_fuzzer import ArithmeticFuzzer
from casegen.fuzzing.dictionary_fuzzer import DictionaryFuzzer
from casegen.fuzzing.splicing_fuzzer import SplicingFuzzer
from casegen.fuzzing.crossover_fuzzer import CrossoverFuzzer
from casegen.fuzzing.strategy_selector import StrategySelector, SelectionMode, create_selector
from pipeline.executor import Executor
from schemas.case import TestCase
from schemas.common import InputValidity, OperationType, ObservedOutcome
from schemas.result import ExecutionResult
from pipeline.triage import Triage


@dataclass
class FuzzingCampaignResult:
    """Result of a fuzzing campaign."""
    campaign_id: str
    total_generated: int
    total_executed: int
    bugs_found: int
    strategy_stats: Dict[str, Dict[str, Any]]
    results: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "total_generated": self.total_generated,
            "total_executed": self.total_executed,
            "bugs_found": self.bugs_found,
            "strategy_stats": self.strategy_stats,
            "results": self.results
        }


class FuzzingCampaignRunner:
    """Runner for fuzzing campaigns.
    
    Integrates all 6 fuzzing strategies with the existing pipeline
    infrastructure for comprehensive test case generation.
    """
    
    def __init__(
        self,
        adapter: AdapterBase,
        executor: Executor,
        triage: Triage,
        mode: str = "feedback_driven",
        seed: Optional[int] = None
    ):
        self.adapter = adapter
        self.executor = executor
        self.triage = triage
        self.selector = create_selector(mode=mode, seed=seed)
        self.feedback_collector = FeedbackCollector()
        
    def run_campaign(
        self,
        base_cases: List[TestCase],
        campaign_id: str = "fuzz-campaign-001",
        iterations_per_case: int = 10,
        max_total_cases: int = 100
    ) -> FuzzingCampaignResult:
        """Run a fuzzing campaign.
        
        Args:
            base_cases: Base test cases to fuzz
            campaign_id: Campaign identifier
            iterations_per_case: Fuzzing iterations per base case
            max_total_cases: Maximum total test cases to execute
            
        Returns:
            FuzzingCampaignResult with statistics and findings
        """
        print(f"\n  [Fuzzing Campaign] {campaign_id}")
        print(f"    Base cases: {len(base_cases)}")
        print(f"    Iterations/case: {iterations_per_case}")
        
        total_generated = 0
        total_executed = 0
        bugs_found = 0
        all_results = []
        
        for base_case in base_cases:
            if total_executed >= max_total_cases:
                break
            
            print(f"\n    Fuzzing case: {base_case.case_id}")
            
            # Convert TestCase to dict for fuzzing
            base_dict = self._test_case_to_dict(base_case)
            
            # Generate fuzzed cases
            fuzz_results = self.selector.execute_fuzzing(
                base_case=base_dict,
                num_iterations=iterations_per_case
            )
            
            total_generated += len(fuzz_results)
            
            # Execute fuzzed cases
            for fuzz_result in fuzz_results:
                if total_executed >= max_total_cases:
                    break
                
                if fuzz_result.status != FuzzingStatus.SUCCESS or not fuzz_result.test_case:
                    continue
                
                # Convert back to TestCase
                fuzzed_case = self._dict_to_test_case(
                    fuzz_result.test_case,
                    case_id=f"{base_case.case_id}_fuzz_{total_executed}"
                )
                
                # Execute
                execution_result = self.executor.execute_case(
                    fuzzed_case,
                    run_id=f"{campaign_id}_{total_executed}"
                )
                total_executed += 1
                
                # Record feedback
                self._record_feedback(fuzzed_case, execution_result, fuzz_result)
                
                # Check for bugs
                triage_result = self.triage.classify(fuzzed_case, execution_result)
                if triage_result:
                    bugs_found += 1
                    all_results.append({
                        "case_id": fuzzed_case.case_id,
                        "bug_type": triage_result.final_type.value,
                        "rationale": triage_result.rationale
                    })
                    print(f"      BUG: {triage_result.final_type.value} - {triage_result.rationale}")
        
        # Get final strategy stats
        strategy_stats = self.selector.get_strategy_stats()
        
        print(f"\n    Campaign Complete:")
        print(f"      Generated: {total_generated}")
        print(f"      Executed: {total_executed}")
        print(f"      Bugs found: {bugs_found}")
        
        return FuzzingCampaignResult(
            campaign_id=campaign_id,
            total_generated=total_generated,
            total_executed=total_executed,
            bugs_found=bugs_found,
            strategy_stats=strategy_stats,
            results=all_results
        )
    
    def run_targeted_fuzzing(
        self,
        base_case: TestCase,
        target_strategies: List[str],
        campaign_id: str = "targeted-fuzz-001",
        iterations: int = 50
    ) -> FuzzingCampaignResult:
        """Run targeted fuzzing with specific strategies.
        
        Args:
            base_case: Base test case to fuzz
            target_strategies: List of strategy names to use
            campaign_id: Campaign identifier
            iterations: Number of fuzzing iterations
            
        Returns:
            FuzzingCampaignResult
        """
        print(f"\n  [Targeted Fuzzing] {campaign_id}")
        print(f"    Strategies: {', '.join(target_strategies)}")
        print(f"    Iterations: {iterations}")
        
        total_generated = 0
        total_executed = 0
        bugs_found = 0
        all_results = []
        
        base_dict = self._test_case_to_dict(base_case)
        
        # Use specific strategies
        for strategy_name in target_strategies:
            if strategy_name not in self.selector.strategies:
                print(f"    Warning: Unknown strategy '{strategy_name}'")
                continue
            
            strategy = self.selector.strategies[strategy_name]
            
            print(f"\n    Running {strategy_name}...")
            
            fuzz_results = strategy.fuzz(base_dict)
            total_generated += len(fuzz_results)
            
            for fuzz_result in fuzz_results:
                if total_executed >= iterations:
                    break
                
                if fuzz_result.status != FuzzingStatus.SUCCESS or not fuzz_result.test_case:
                    continue
                
                fuzzed_case = self._dict_to_test_case(
                    fuzz_result.test_case,
                    case_id=f"{base_case.case_id}_{strategy_name}_{total_executed}"
                )
                
                execution_result = self.executor.execute_case(
                    fuzzed_case,
                    run_id=f"{campaign_id}_{total_executed}"
                )
                total_executed += 1
                
                self._record_feedback(fuzzed_case, execution_result, fuzz_result)
                
                triage_result = self.triage.classify(fuzzed_case, execution_result)
                if triage_result:
                    bugs_found += 1
                    all_results.append({
                        "case_id": fuzzed_case.case_id,
                        "strategy": strategy_name,
                        "bug_type": triage_result.final_type.value
                    })
        
        print(f"\n    Targeted Fuzzing Complete:")
        print(f"      Generated: {total_generated}")
        print(f"      Executed: {total_executed}")
        print(f"      Bugs found: {bugs_found}")
        
        return FuzzingCampaignResult(
            campaign_id=campaign_id,
            total_generated=total_generated,
            total_executed=total_executed,
            bugs_found=bugs_found,
            strategy_stats=self.selector.get_strategy_stats(),
            results=all_results
        )
    
    def _test_case_to_dict(self, case: TestCase) -> Dict[str, Any]:
        """Convert TestCase to dictionary for fuzzing."""
        return {
            "case_id": case.case_id,
            "operation": case.operation.value,
            "params": case.params,
            "expected_validity": case.expected_validity.value
        }
    
    def _dict_to_test_case(self, data: Dict[str, Any], case_id: str) -> TestCase:
        """Convert dictionary back to TestCase."""
        return TestCase(
            case_id=case_id,
            operation=OperationType(data.get("operation", "search")),
            params=data.get("params", {}),
            expected_validity=InputValidity(data.get("expected_validity", "legal"))
        )
    
    def _record_feedback(
        self,
        case: TestCase,
        execution_result: ExecutionResult,
        fuzz_result: FuzzingResult
    ) -> None:
        """Record execution feedback."""
        self.feedback_collector.record_execution(
            test_case=self._test_case_to_dict(case),
            result={
                "success": execution_result.observed_outcome == ObservedOutcome.SUCCESS,
                "error_type": execution_result.error_message
            },
            coverage=fuzz_result.metadata.get("coverage")
        )


class FuzzingStrategyFactory:
    """Factory for creating fuzzing strategies with custom configurations."""
    
    STRATEGY_MAP = {
        "random": RandomFuzzer,
        "boundary": BoundaryFuzzer,
        "arithmetic": ArithmeticFuzzer,
        "dictionary": DictionaryFuzzer,
        "splicing": SplicingFuzzer,
        "crossover": CrossoverFuzzer,
    }
    
    @classmethod
    def create_strategy(
        cls,
        name: str,
        max_iterations: int = 100,
        seed: Optional[int] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Create a fuzzing strategy.
        
        Args:
            name: Strategy name
            max_iterations: Maximum iterations
            seed: Random seed
            config: Additional configuration
            
        Returns:
            FuzzingStrategy instance
        """
        if name not in cls.STRATEGY_MAP:
            raise ValueError(f"Unknown strategy: {name}")
        
        strategy_class = cls.STRATEGY_MAP[name]
        strategy = strategy_class(max_iterations=max_iterations, seed=seed)
        
        # Apply custom config
        if config:
            for key, value in config.items():
                if hasattr(strategy, key):
                    setattr(strategy, key, value)
        
        return strategy
    
    @classmethod
    def create_all_strategies(
        cls,
        max_iterations: int = 100,
        seed: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create all available strategies.
        
        Args:
            max_iterations: Maximum iterations per strategy
            seed: Random seed
            
        Returns:
            Dictionary mapping strategy names to instances
        """
        return {
            name: cls.create_strategy(name, max_iterations, seed)
            for name in cls.STRATEGY_MAP.keys()
        }
    
    @classmethod
    def get_strategy_names(cls) -> List[str]:
        """Get list of available strategy names."""
        return list(cls.STRATEGY_MAP.keys())


def run_fuzzing_suite(
    adapter: AdapterBase,
    executor: Executor,
    triage: Triage,
    base_cases: List[TestCase],
    mode: str = "feedback_driven",
    iterations_per_case: int = 10,
    seed: Optional[int] = None
) -> FuzzingCampaignResult:
    """Run a complete fuzzing suite.
    
    Convenience function for running a full fuzzing campaign.
    
    Args:
        adapter: Database adapter
        executor: Test case executor
        triage: Triage classifier
        base_cases: Base test cases to fuzz
        mode: Selection mode (random, round_robin, feedback_driven, adaptive)
        iterations_per_case: Fuzzing iterations per base case
        seed: Random seed
        
    Returns:
        FuzzingCampaignResult
    """
    campaign_id = f"fuzz-suite-{int(time.time())}"
    
    runner = FuzzingCampaignRunner(
        adapter=adapter,
        executor=executor,
        triage=triage,
        mode=mode,
        seed=seed
    )
    
    print(f"\n{'='*60}")
    print(f"  Fuzzing Suite")
    print(f"  Mode: {mode}")
    print(f"  Campaign: {campaign_id}")
    print(f"{'='*60}")
    
    result = runner.run_campaign(
        base_cases=base_cases,
        campaign_id=campaign_id,
        iterations_per_case=iterations_per_case
    )
    
    print(f"\n{'='*60}")
    print(f"  Fuzzing Suite Summary")
    print(f"{'='*60}")
    print(f"  Total Generated: {result.total_generated}")
    print(f"  Total Executed: {result.total_executed}")
    print(f"  Bugs Found: {result.bugs_found}")
    
    if result.strategy_stats:
        print(f"\n  Strategy Statistics:")
        for name, stats in result.strategy_stats.items():
            success_rate = stats.get("success_rate", 0)
            attempts = stats.get("attempts", 0)
            print(f"    {name}: {attempts} attempts, {success_rate:.1%} success")
    
    print(f"{'='*60}\n")
    
    return result


# Export for use in other modules
__all__ = [
    "FuzzingCampaignRunner",
    "FuzzingCampaignResult",
    "FuzzingStrategyFactory",
    "run_fuzzing_suite",
]
