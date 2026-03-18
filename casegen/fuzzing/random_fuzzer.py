"""Random fuzzing strategy - completely random parameter replacement."""

from typing import Any, Dict, List, Optional
from casegen.fuzzing.base import FuzzingStrategy, FuzzingResult, FuzzingStatus


class RandomFuzzer(FuzzingStrategy):
    """Generate fuzzed test cases by completely random parameter replacement.
    
    This strategy randomly replaces parameter values with random values
    of the same or different types to explore unexpected behavior.
    """
    
    def __init__(self, max_iterations: int = 100, seed: Optional[int] = None):
        super().__init__("RandomFuzzer", max_iterations, seed)
        
    def fuzz(
        self,
        base_case: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> List[FuzzingResult]:
        """Generate fuzzed test cases by random parameter mutation.
        
        Args:
            base_case: Base test case to fuzz
            context: Additional context (may include valid_values, ranges, etc.)
            
        Returns:
            List of fuzzing results
        """
        results = []
        
        for i in range(min(self.max_iterations, 10)):  # Limit for practical use
            import time
            start_time = time.time()
            
            try:
                # Create a deep copy of base case
                import copy
                fuzzed_case = copy.deepcopy(base_case)
                
                # Randomly select a parameter to mutate
                params = fuzzed_case.get("params", {})
                if not params:
                    continue
                    
                param_keys = list(params.keys())
                if not param_keys:
                    continue
                    
                # Select random parameter(s) to mutate
                n_mutations = self.rng.randint(1, min(3, len(param_keys)))
                keys_to_mutate = self.rng.sample(param_keys, n_mutations)
                
                for key in keys_to_mutate:
                    original_value = params[key]
                    params[key] = self._generate_random_value(original_value)
                
                generation_time = (time.time() - start_time) * 1000
                
                results.append(FuzzingResult(
                    status=FuzzingStatus.SUCCESS,
                    test_case=fuzzed_case,
                    seed=self.seed,
                    generation_time_ms=generation_time,
                    metadata={
                        "strategy": "random",
                        "mutated_params": keys_to_mutate
                    }
                ))
                
                self.add_to_corpus(fuzzed_case)
                
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
    
    def _generate_random_value(self, original: Any) -> Any:
        """Generate a random value based on original value type."""
        if isinstance(original, int):
            # Mix of small, medium, large, and edge case integers
            choices = [
                self.rng.randint(-1000, 1000),  # Normal range
                self.rng.randint(-2**31, 2**31),  # Full int32 range
                0, 1, -1,  # Edge cases
                2**16, 2**31, -2**31,  # Boundary values
            ]
            return self.rng.choice(choices)
            
        elif isinstance(original, float):
            choices = [
                self.rng.random(),
                self.rng.gauss(0, 1),
                0.0, -0.0, float('inf'), float('-inf'),
                1e-10, 1e10, -1e10,
            ]
            return self.rng.choice(choices)
            
        elif isinstance(original, str):
            # Random string mutations
            mutations = [
                "",  # Empty
                "a" * self.rng.randint(1, 1000),  # Long string
                "\x00" * self.rng.randint(1, 10),  # Null bytes
                "' OR '1'='1",  # SQL injection attempt
                "<script>alert(1)</script>",  # XSS attempt
                "\n\r\t",  # Whitespace
                original[::-1] if len(original) > 1 else "",  # Reversed
            ]
            return self.rng.choice(mutations)
            
        elif isinstance(original, list):
            # Mutate list elements
            if not original:
                return [self.rng.random() for _ in range(self.rng.randint(1, 10))]
            
            mutated = original.copy()
            if self.rng.random() < 0.5 and mutated:
                # Remove random element
                mutated.pop(self.rng.randint(0, len(mutated) - 1))
            else:
                # Add random element
                if isinstance(original[0], (int, float)):
                    mutated.append(self.rng.randint(0, 1000))
                else:
                    mutated.append("random_element")
            return mutated
            
        else:
            # For other types, return random choice from common values
            return self.rng.choice([None, True, False, 0, "", []])
