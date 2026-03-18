"""Boundary value fuzzing strategy - test min-1, min, max, max+1."""

from typing import Any, Dict, List, Optional
from casegen.fuzzing.base import FuzzingStrategy, FuzzingResult, FuzzingStatus


class BoundaryFuzzer(FuzzingStrategy):
    """Generate fuzzed test cases using boundary value analysis.
    
    This strategy tests boundary conditions: min-1, min, max, max+1
    for numeric parameters, and empty/single/max-length for strings.
    """
    
    def __init__(self, max_iterations: int = 100, seed: Optional[int] = None):
        super().__init__("BoundaryFuzzer", max_iterations, seed)
        
    def fuzz(
        self,
        base_case: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> List[FuzzingResult]:
        """Generate fuzzed test cases with boundary values.
        
        Args:
            base_case: Base test case to fuzz
            context: May include 'constraints' with min_value, max_value, etc.
            
        Returns:
            List of fuzzing results
        """
        results = []
        import time
        import copy
        
        params = base_case.get("params", {})
        constraints = context.get("constraints", {}) if context else {}
        
        for param_name, original_value in params.items():
            param_constraints = constraints.get(param_name, {})
            
            # Generate boundary values for this parameter
            boundary_values = self._generate_boundary_values(
                original_value, param_constraints
            )
            
            for boundary_value in boundary_values:
                start_time = time.time()
                
                try:
                    fuzzed_case = copy.deepcopy(base_case)
                    fuzzed_case["params"][param_name] = boundary_value
                    
                    generation_time = (time.time() - start_time) * 1000
                    
                    results.append(FuzzingResult(
                        status=FuzzingStatus.SUCCESS,
                        test_case=fuzzed_case,
                        seed=self.seed,
                        generation_time_ms=generation_time,
                        metadata={
                            "strategy": "boundary",
                            "mutated_param": param_name,
                            "original_value": original_value,
                            "boundary_value": boundary_value
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
    
    def _generate_boundary_values(
        self,
        original: Any,
        constraints: Dict[str, Any]
    ) -> List[Any]:
        """Generate boundary values based on type and constraints."""
        
        if isinstance(original, int):
            min_val = constraints.get("min_value", 0)
            max_val = constraints.get("max_value", 1000)
            
            return [
                min_val - 1,  # Just below minimum
                min_val,      # At minimum
                min_val + 1,  # Just above minimum
                max_val - 1,  # Just below maximum
                max_val,      # At maximum
                max_val + 1,  # Just above maximum
                0,            # Zero
                -1,           # Negative
            ]
            
        elif isinstance(original, float):
            min_val = constraints.get("min_value", 0.0)
            max_val = constraints.get("max_value", 1.0)
            
            return [
                min_val - 0.1,
                min_val,
                min_val + 0.1,
                max_val - 0.1,
                max_val,
                max_val + 0.1,
                0.0,
                -0.1,
                float('inf'),
                float('-inf'),
            ]
            
        elif isinstance(original, str):
            max_length = constraints.get("max_length", 65535)
            
            return [
                "",                           # Empty string
                "a",                          # Single character
                "a" * 100,                    # Medium length
                "a" * max_length,             # At max length
                "a" * (max_length + 1),       # Just over max length
                "\x00",                       # Null character
                " " * 10,                     # Whitespace only
            ]
            
        elif isinstance(original, list):
            max_items = constraints.get("max_items", 1000)
            
            return [
                [],                           # Empty list
                [original[0]] if original else [1],  # Single item
                original[:10] if len(original) > 10 else original,  # Small list
                original[:max_items] if len(original) > max_items else original,  # At max
            ]
            
        else:
            return [original]  # No boundary values for other types
