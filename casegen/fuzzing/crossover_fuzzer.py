"""Crossover fuzzing strategy - exchange parameter segments between cases."""

from typing import Any, Dict, List, Optional, Tuple
from casegen.fuzzing.base import FuzzingStrategy, FuzzingResult, FuzzingStatus


class CrossoverFuzzer(FuzzingStrategy):
    """Generate fuzzed test cases using crossover between multiple cases.
    
    This strategy exchanges parameter segments between two or more parent
    test cases to create offspring with mixed characteristics.
    """
    
    def __init__(self, max_iterations: int = 100, seed: Optional[int] = None):
        super().__init__("CrossoverFuzzer", max_iterations, seed)
        self.parent_pool: List[Dict[str, Any]] = []
        
    def add_parent(self, parent: Dict[str, Any]):
        """Add a parent test case to the pool.
        
        Args:
            parent: A test case to use as parent
        """
        import copy
        self.parent_pool.append(copy.deepcopy(parent))
        
    def fuzz(
        self,
        base_case: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> List[FuzzingResult]:
        """Generate fuzzed test cases using crossover.
        
        Args:
            base_case: Base test case to fuzz
            context: May include 'parents' list of additional cases
            
        Returns:
            List of fuzzing results
        """
        results = []
        import time
        import copy
        
        # Add base case to parent pool
        self.add_parent(base_case)
        
        # Add context parents if provided
        if context and "parents" in context:
            for parent in context["parents"]:
                self.add_parent(parent)
        
        # Need at least 2 parents for crossover
        if len(self.parent_pool) < 2:
            return [FuzzingResult(
                status=FuzzingStatus.SKIPPED,
                test_case=None,
                seed=self.seed,
                generation_time_ms=0.0,
                metadata={"reason": "insufficient_parents"}
            )]
        
        # Generate crossover offspring
        num_offspring = min(self.max_iterations, 10)
        
        for i in range(num_offspring):
            start_time = time.time()
            
            try:
                # Select two parents
                parent1, parent2 = self._select_parents()
                
                # Perform crossover
                offspring = self._crossover(parent1, parent2)
                
                generation_time = (time.time() - start_time) * 1000
                
                results.append(FuzzingResult(
                    status=FuzzingStatus.SUCCESS,
                    test_case=offspring,
                    seed=self.seed,
                    generation_time_ms=generation_time,
                    metadata={
                        "strategy": "crossover",
                        "parent_ids": [
                            parent1.get("case_id", "unknown"),
                            parent2.get("case_id", "unknown")
                        ]
                    }
                ))
                
                self.add_to_corpus(offspring)
                
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
    
    def _select_parents(self) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Select two distinct parents from the pool.
        
        Returns:
            Tuple of two parent test cases
        """
        idx1, idx2 = self.rng.sample(range(len(self.parent_pool)), 2)
        return self.parent_pool[idx1], self.parent_pool[idx2]
    
    def _crossover(
        self,
        parent1: Dict[str, Any],
        parent2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform crossover between two parents.
        
        Args:
            parent1: First parent
            parent2: Second parent
            
        Returns:
            Offspring test case
        """
        import copy
        
        # Start with copy of parent1
        offspring = copy.deepcopy(parent1)
        
        # Get params from both parents
        params1 = parent1.get("params", {})
        params2 = parent2.get("params", {})
        
        if not params1 or not params2:
            return offspring
        
        # Get all unique param keys
        all_keys = set(params1.keys()) | set(params2.keys())
        
        if not all_keys:
            return offspring
        
        # Single-point crossover: split params at random point
        keys_list = sorted(list(all_keys))
        crossover_point = self.rng.randint(1, len(keys_list))
        
        # Take first half from parent1 (already in offspring)
        # Take second half from parent2
        for i in range(crossover_point, len(keys_list)):
            key = keys_list[i]
            if key in params2:
                offspring["params"][key] = copy.deepcopy(params2[key])
        
        # Mark as crossover offspring
        offspring["_crossover"] = True
        offspring["_crossover_point"] = crossover_point
        
        return offspring
    
    def _uniform_crossover(
        self,
        parent1: Dict[str, Any],
        parent2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform uniform crossover (each param chosen independently).
        
        Args:
            parent1: First parent
            parent2: Second parent
            
        Returns:
            Offspring test case
        """
        import copy
        
        offspring = {"params": {}}
        
        params1 = parent1.get("params", {})
        params2 = parent2.get("params", {})
        
        # Get all unique param keys
        all_keys = set(params1.keys()) | set(params2.keys())
        
        for key in all_keys:
            # 50% chance to take from either parent
            if self.rng.random() < 0.5 and key in params1:
                offspring["params"][key] = copy.deepcopy(params1[key])
            elif key in params2:
                offspring["params"][key] = copy.deepcopy(params2[key])
            elif key in params1:
                offspring["params"][key] = copy.deepcopy(params1[key])
        
        offspring["_uniform_crossover"] = True
        
        return offspring
