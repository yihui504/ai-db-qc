"""Arithmetic fuzzing strategy - apply arithmetic mutations (±1, ×2, ÷2)."""

from typing import Any, Dict, List, Optional
from casegen.fuzzing.base import FuzzingStrategy, FuzzingResult, FuzzingStatus


class ArithmeticFuzzer(FuzzingStrategy):
    """Generate fuzzed test cases using arithmetic mutations.
    
    This strategy applies arithmetic operations to numeric values:
    - Addition/Subtraction: ±1, ±10, ±100
    - Multiplication: ×2, ×10, ×0.5
    - Division: ÷2, ÷10
    """
    
    def __init__(self, max_iterations: int = 100, seed: Optional[int] = None):
        super().__init__("ArithmeticFuzzer", max_iterations, seed)
        
    def fuzz(
        self,
        base_case: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> List[FuzzingResult]:
        """Generate fuzzed test cases with arithmetic mutations.
        
        Args:
            base_case: Base test case to fuzz
            context: Additional context
            
        Returns:
            List of fuzzing results
        """
        results = []
        import time
        import copy
        
        params = base_case.get("params", {})
        
        for param_name, original_value in params.items():
            # Only apply arithmetic mutations to numeric values
            if not isinstance(original_value, (int, float)):
                continue
                
            arithmetic_values = self._generate_arithmetic_values(original_value)
            
            for new_value in arithmetic_values:
                start_time = time.time()
                
                try:
                    fuzzed_case = copy.deepcopy(base_case)
                    fuzzed_case["params"][param_name] = new_value
                    
                    generation_time = (time.time() - start_time) * 1000
                    
                    results.append(FuzzingResult(
                        status=FuzzingStatus.SUCCESS,
                        test_case=fuzzed_case,
                        seed=self.seed,
                        generation_time_ms=generation_time,
                        metadata={
                            "strategy": "arithmetic",
                            "mutated_param": param_name,
                            "original_value": original_value,
                            "new_value": new_value,
                            "operation": self._get_operation(original_value, new_value)
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
    
    def _generate_arithmetic_values(self, original: Any) -> List[Any]:
        """Generate arithmetic mutations of the original value."""
        
        if isinstance(original, int):
            return [
                original + 1,      # Increment
                original - 1,      # Decrement
                original + 10,     # Add 10
                original - 10,     # Subtract 10
                original + 100,    # Add 100
                original - 100,    # Subtract 100
                original * 2,      # Double
                original * 10,     # Multiply by 10
                original // 2,     # Halve (integer division)
                original // 10,    # Divide by 10
                -original,         # Negate
                original ** 2,     # Square
                0,                 # Zero
                1,                 # One
            ]
            
        elif isinstance(original, float):
            return [
                original + 0.1,
                original - 0.1,
                original + 1.0,
                original - 1.0,
                original * 2.0,
                original * 10.0,
                original / 2.0,
                original / 10.0,
                original * 0.5,    # Half
                original * 1.5,    # One and a half
                -original,
                original ** 2,
                0.0,
                1.0,
            ]
            
        else:
            return [original]
    
    def _get_operation(self, original: Any, new_value: Any) -> str:
        """Determine which arithmetic operation was applied."""
        
        if isinstance(original, (int, float)) and isinstance(new_value, (int, float)):
            if new_value == original + 1:
                return "+1"
            elif new_value == original - 1:
                return "-1"
            elif new_value == original + 10:
                return "+10"
            elif new_value == original - 10:
                return "-10"
            elif new_value == original * 2:
                return "×2"
            elif new_value == original / 2:
                return "÷2"
            elif new_value == -original:
                return "negate"
            elif new_value == 0:
                return "zero"
            else:
                return "other"
        
        return "unknown"
