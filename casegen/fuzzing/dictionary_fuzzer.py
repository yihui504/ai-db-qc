"""Dictionary fuzzing strategy - replace with historically valid values."""

from typing import Any, Dict, List, Optional
from casegen.fuzzing.base import FuzzingStrategy, FuzzingResult, FuzzingStatus


class DictionaryFuzzer(FuzzingStrategy):
    """Generate fuzzed test cases using historically valid values.
    
    This strategy maintains a dictionary of historically valid values
    for each parameter and uses them for substitution during fuzzing.
    """
    
    def __init__(self, max_iterations: int = 100, seed: Optional[int] = None):
        super().__init__("DictionaryFuzzer", max_iterations, seed)
        self.value_dictionary: Dict[str, List[Any]] = {}
        
    def add_to_dictionary(self, param_name: str, value: Any):
        """Add a value to the dictionary for a parameter.
        
        Args:
            param_name: Name of the parameter
            value: Valid value observed
        """
        if param_name not in self.value_dictionary:
            self.value_dictionary[param_name] = []
        
        # Avoid duplicates
        if value not in self.value_dictionary[param_name]:
            self.value_dictionary[param_name].append(value)
    
    def load_dictionary(self, dictionary: Dict[str, List[Any]]):
        """Load a pre-built dictionary.
        
        Args:
            dictionary: Dictionary mapping parameter names to valid values
        """
        self.value_dictionary.update(dictionary)
        
    def fuzz(
        self,
        base_case: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> List[FuzzingResult]:
        """Generate fuzzed test cases using dictionary values.
        
        Args:
            base_case: Base test case to fuzz
            context: May include 'dictionary' with valid values
            
        Returns:
            List of fuzzing results
        """
        results = []
        import time
        import copy
        
        params = base_case.get("params", {})
        
        # Merge context dictionary if provided
        if context and "dictionary" in context:
            self.load_dictionary(context["dictionary"])
        
        # Also learn from base_case values
        for param_name, value in params.items():
            self.add_to_dictionary(param_name, value)
        
        # Generate fuzzed cases by substituting dictionary values
        for param_name in params.keys():
            if param_name not in self.value_dictionary:
                continue
                
            valid_values = self.value_dictionary[param_name]
            
            # Sample a subset of dictionary values
            sample_size = min(5, len(valid_values))
            sampled_values = self.rng.sample(valid_values, sample_size)
            
            for dict_value in sampled_values:
                start_time = time.time()
                
                try:
                    fuzzed_case = copy.deepcopy(base_case)
                    fuzzed_case["params"][param_name] = dict_value
                    
                    generation_time = (time.time() - start_time) * 1000
                    
                    results.append(FuzzingResult(
                        status=FuzzingStatus.SUCCESS,
                        test_case=fuzzed_case,
                        seed=self.seed,
                        generation_time_ms=generation_time,
                        metadata={
                            "strategy": "dictionary",
                            "mutated_param": param_name,
                            "dictionary_value": dict_value
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
    
    def get_dictionary_stats(self) -> Dict[str, int]:
        """Get statistics about the current dictionary.
        
        Returns:
            Dictionary with parameter names and value counts
        """
        return {
            param: len(values)
            for param, values in self.value_dictionary.items()
        }
