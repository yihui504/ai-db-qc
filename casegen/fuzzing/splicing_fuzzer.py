"""Splicing fuzzing strategy - combine fragments from multiple test cases."""

from typing import Any, Dict, List, Optional
from casegen.fuzzing.base import FuzzingStrategy, FuzzingResult, FuzzingStatus


class SplicingFuzzer(FuzzingStrategy):
    """Generate fuzzed test cases by splicing fragments from multiple cases.
    
    This strategy takes parameters from different test cases and combines
    them to create new hybrid test cases.
    """
    
    def __init__(self, max_iterations: int = 100, seed: Optional[int] = None):
        super().__init__("SplicingFuzzer", max_iterations, seed)
        self.fragment_pool: List[Dict[str, Any]] = []
        
    def add_fragment(self, fragment: Dict[str, Any]):
        """Add a test case fragment to the pool.
        
        Args:
            fragment: A test case or partial test case
        """
        self.fragment_pool.append(fragment)
        
    def fuzz(
        self,
        base_case: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> List[FuzzingResult]:
        """Generate fuzzed test cases by splicing fragments.
        
        Args:
            base_case: Base test case to fuzz
            context: May include 'fragments' list of additional cases
            
        Returns:
            List of fuzzing results
        """
        results = []
        import time
        import copy
        
        # Add base case to fragment pool
        self.add_fragment(copy.deepcopy(base_case))
        
        # Add context fragments if provided
        if context and "fragments" in context:
            for fragment in context["fragments"]:
                self.add_fragment(fragment)
        
        # Need at least 2 fragments to splice
        if len(self.fragment_pool) < 2:
            return [FuzzingResult(
                status=FuzzingStatus.SKIPPED,
                test_case=None,
                seed=self.seed,
                generation_time_ms=0.0,
                metadata={"reason": "insufficient_fragments"}
            )]
        
        # Generate spliced cases
        num_splices = min(self.max_iterations, len(self.fragment_pool) - 1)
        
        for i in range(num_splices):
            start_time = time.time()
            
            try:
                # Select two different fragments to splice
                idx1, idx2 = self.rng.sample(range(len(self.fragment_pool)), 2)
                frag1 = self.fragment_pool[idx1]
                frag2 = self.fragment_pool[idx2]
                
                # Create spliced case
                spliced_case = self._splice_cases(frag1, frag2)
                
                generation_time = (time.time() - start_time) * 1000
                
                results.append(FuzzingResult(
                    status=FuzzingStatus.SUCCESS,
                    test_case=spliced_case,
                    seed=self.seed,
                    generation_time_ms=generation_time,
                    metadata={
                        "strategy": "splicing",
                        "source_fragments": [idx1, idx2]
                    }
                ))
                
                self.add_to_corpus(spliced_case)
                
            except Exception as e:
                generation_time = (time.time() - start_time) * 1000
                results.append(FuzzingResult(
                    status=FuzzingStatus.FAILED,
                    test_case=None,
                    seed=self.seed,
                    generation_time_ms=generation_time,
                    metadata={"error": str(e)}
                ))
        
        return results
    
    def _splice_cases(
        self,
        case1: Dict[str, Any],
        case2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Splice two test cases together.
        
        Args:
            case1: First test case
            case2: Second test case
            
        Returns:
            Spliced test case
        """
        import copy
        
        # Start with a copy of case1
        spliced = copy.deepcopy(case1)
        
        # Get params from both cases
        params1 = case1.get("params", {})
        params2 = case2.get("params", {})
        
        if not params1 or not params2:
            return spliced
        
        # Select random subset of params from case2 to splice in
        params2_keys = list(params2.keys())
        num_to_splice = self.rng.randint(1, max(1, len(params2_keys)))
        keys_to_splice = self.rng.sample(params2_keys, num_to_splice)
        
        # Splice selected params
        for key in keys_to_splice:
            if key in params2:
                spliced["params"][key] = copy.deepcopy(params2[key])
        
        # Mark as spliced
        spliced["_spliced"] = True
        spliced["_source_cases"] = [case1.get("case_id", "unknown"), case2.get("case_id", "unknown")]
        
        return spliced
