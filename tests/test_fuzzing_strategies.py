"""Unit tests for fuzzing strategies.

This module tests all 6 fuzzing strategies:
- RandomFuzzer
- BoundaryFuzzer
- ArithmeticFuzzer
- DictionaryFuzzer
- SplicingFuzzer
- CrossoverFuzzer

And the StrategySelector for orchestration.
"""

import unittest
from typing import Any, Dict, List

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from casegen.fuzzing.base import FuzzingStatus, FuzzingResult, CoverageInfo, FeedbackCollector
from casegen.fuzzing.random_fuzzer import RandomFuzzer
from casegen.fuzzing.boundary_fuzzer import BoundaryFuzzer
from casegen.fuzzing.arithmetic_fuzzer import ArithmeticFuzzer
from casegen.fuzzing.dictionary_fuzzer import DictionaryFuzzer
from casegen.fuzzing.splicing_fuzzer import SplicingFuzzer
from casegen.fuzzing.crossover_fuzzer import CrossoverFuzzer
from casegen.fuzzing.strategy_selector import StrategySelector, SelectionMode, create_selector


class TestRandomFuzzer(unittest.TestCase):
    """Tests for RandomFuzzer strategy."""
    
    def setUp(self):
        self.fuzzer = RandomFuzzer(seed=42)
        self.base_case = {
            "operation": "search",
            "params": {
                "top_k": 10,
                "metric": "L2",
                "vector": [0.1, 0.2, 0.3]
            }
        }
    
    def test_fuzz_generates_results(self):
        """Test that fuzz() generates fuzzing results."""
        results = self.fuzzer.fuzz(self.base_case)
        self.assertGreater(len(results), 0)
        self.assertTrue(all(isinstance(r, FuzzingResult) for r in results))
    
    def test_fuzz_mutates_params(self):
        """Test that fuzz() mutates parameters."""
        results = self.fuzzer.fuzz(self.base_case)
        
        # At least some results should have mutated params
        mutated = False
        for result in results:
            if result.test_case and result.status == FuzzingStatus.SUCCESS:
                if result.test_case.get("params") != self.base_case["params"]:
                    mutated = True
                    break
        self.assertTrue(mutated, "Expected at least one mutated parameter")
    
    def test_fuzz_preserves_structure(self):
        """Test that fuzz() preserves test case structure."""
        results = self.fuzzer.fuzz(self.base_case)
        
        for result in results:
            if result.test_case:
                self.assertIn("operation", result.test_case)
                self.assertIn("params", result.test_case)
    
    def test_generate_random_value_int(self):
        """Test random value generation for integers."""
        value = self.fuzzer._generate_random_value(42)
        self.assertIsInstance(value, int)
    
    def test_generate_random_value_float(self):
        """Test random value generation for floats."""
        value = self.fuzzer._generate_random_value(3.14)
        self.assertIsInstance(value, float)
    
    def test_generate_random_value_str(self):
        """Test random value generation for strings."""
        value = self.fuzzer._generate_random_value("test")
        self.assertIsInstance(value, str)
    
    def test_generate_random_value_list(self):
        """Test random value generation for lists."""
        value = self.fuzzer._generate_random_value([1, 2, 3])
        self.assertIsInstance(value, list)
    
    def test_empty_params(self):
        """Test handling of empty params."""
        empty_case = {"operation": "test", "params": {}}
        results = self.fuzzer.fuzz(empty_case)
        # Should handle gracefully
        self.assertIsInstance(results, list)


class TestBoundaryFuzzer(unittest.TestCase):
    """Tests for BoundaryFuzzer strategy."""
    
    def setUp(self):
        self.fuzzer = BoundaryFuzzer(seed=42)
        self.base_case = {
            "operation": "search",
            "params": {
                "top_k": 10,
                "dim": 128,
                "name": "test_collection"
            }
        }
    
    def test_fuzz_generates_boundary_values(self):
        """Test that fuzz() generates boundary values."""
        results = self.fuzzer.fuzz(self.base_case)
        self.assertGreater(len(results), 0)
    
    def test_boundary_values_int(self):
        """Test boundary value generation for integers."""
        values = self.fuzzer._generate_boundary_values(10, {"min_value": 0, "max_value": 100})
        
        # Should include boundary values
        self.assertIn(0, values)   # min
        self.assertIn(-1, values)  # min-1
        self.assertIn(100, values) # max
        self.assertIn(101, values) # max+1
    
    def test_boundary_values_float(self):
        """Test boundary value generation for floats."""
        values = self.fuzzer._generate_boundary_values(0.5, {"min_value": 0.0, "max_value": 1.0})
        
        self.assertIn(0.0, values)
        self.assertIn(1.0, values)
        self.assertIn(float('inf'), values)
    
    def test_boundary_values_str(self):
        """Test boundary value generation for strings."""
        values = self.fuzzer._generate_boundary_values("test", {"max_length": 100})
        
        self.assertIn("", values)  # Empty
        self.assertIn("a", values)  # Single char
    
    def test_metadata_includes_boundary_info(self):
        """Test that metadata includes boundary information."""
        results = self.fuzzer.fuzz(self.base_case)
        
        for result in results:
            if result.status == FuzzingStatus.SUCCESS:
                self.assertIn("mutated_param", result.metadata)
                self.assertIn("boundary_value", result.metadata)


class TestArithmeticFuzzer(unittest.TestCase):
    """Tests for ArithmeticFuzzer strategy."""
    
    def setUp(self):
        self.fuzzer = ArithmeticFuzzer(seed=42)
        self.base_case = {
            "operation": "insert",
            "params": {
                "n_vectors": 100,
                "dim": 128,
                "batch_size": 10.0
            }
        }
    
    def test_fuzz_generates_arithmetic_mutations(self):
        """Test that fuzz() generates arithmetic mutations."""
        results = self.fuzzer.fuzz(self.base_case)
        self.assertGreater(len(results), 0)
    
    def test_arithmetic_values_int(self):
        """Test arithmetic value generation for integers."""
        values = self.fuzzer._generate_arithmetic_values(10)
        
        self.assertIn(11, values)  # +1
        self.assertIn(9, values)   # -1
        self.assertIn(20, values)  # *2
        self.assertIn(5, values)   # //2
        self.assertIn(-10, values) # negate
        self.assertIn(0, values)   # zero
    
    def test_arithmetic_values_float(self):
        """Test arithmetic value generation for floats."""
        values = self.fuzzer._generate_arithmetic_values(1.0)
        
        self.assertIn(2.0, values)  # *2
        self.assertIn(0.5, values)  # /2
        self.assertIn(0.0, values)  # zero
    
    def test_get_operation(self):
        """Test operation detection."""
        self.assertEqual(self.fuzzer._get_operation(10, 11), "+1")
        self.assertEqual(self.fuzzer._get_operation(10, 9), "-1")
        self.assertEqual(self.fuzzer._get_operation(10, 20), "×2")
        self.assertEqual(self.fuzzer._get_operation(10, 5), "÷2")
        self.assertEqual(self.fuzzer._get_operation(10, -10), "negate")
    
    def test_metadata_includes_operation(self):
        """Test that metadata includes operation info."""
        results = self.fuzzer.fuzz(self.base_case)
        
        for result in results:
            if result.status == FuzzingStatus.SUCCESS:
                self.assertIn("operation", result.metadata)


class TestDictionaryFuzzer(unittest.TestCase):
    """Tests for DictionaryFuzzer strategy."""
    
    def setUp(self):
        self.fuzzer = DictionaryFuzzer(seed=42)
        self.base_case = {
            "operation": "search",
            "params": {
                "metric": "L2",
                "top_k": 10
            }
        }
    
    def test_add_to_dictionary(self):
        """Test adding values to dictionary."""
        self.fuzzer.add_to_dictionary("metric", "L2")
        self.fuzzer.add_to_dictionary("metric", "IP")
        
        self.assertIn("metric", self.fuzzer.value_dictionary)
        self.assertIn("L2", self.fuzzer.value_dictionary["metric"])
        self.assertIn("IP", self.fuzzer.value_dictionary["metric"])
    
    def test_add_to_dictionary_avoids_duplicates(self):
        """Test that dictionary avoids duplicates."""
        self.fuzzer.add_to_dictionary("metric", "L2")
        self.fuzzer.add_to_dictionary("metric", "L2")  # Duplicate
        
        self.assertEqual(len(self.fuzzer.value_dictionary["metric"]), 1)
    
    def test_load_dictionary(self):
        """Test loading a dictionary."""
        dictionary = {
            "metric": ["L2", "IP", "COSINE"],
            "top_k": [5, 10, 50]
        }
        self.fuzzer.load_dictionary(dictionary)
        
        self.assertEqual(self.fuzzer.value_dictionary["metric"], ["L2", "IP", "COSINE"])
    
    def test_fuzz_uses_dictionary_values(self):
        """Test that fuzz() uses dictionary values."""
        # Pre-populate dictionary
        self.fuzzer.add_to_dictionary("metric", "IP")
        self.fuzzer.add_to_dictionary("metric", "COSINE")
        
        results = self.fuzzer.fuzz(self.base_case)
        self.assertGreater(len(results), 0)
    
    def test_get_dictionary_stats(self):
        """Test dictionary statistics."""
        self.fuzzer.add_to_dictionary("metric", "L2")
        self.fuzzer.add_to_dictionary("metric", "IP")
        self.fuzzer.add_to_dictionary("top_k", 10)
        
        stats = self.fuzzer.get_dictionary_stats()
        self.assertEqual(stats["metric"], 2)
        self.assertEqual(stats["top_k"], 1)


class TestSplicingFuzzer(unittest.TestCase):
    """Tests for SplicingFuzzer strategy."""
    
    def setUp(self):
        self.fuzzer = SplicingFuzzer(seed=42)
        self.base_case = {
            "case_id": "case1",
            "operation": "search",
            "params": {
                "top_k": 10,
                "metric": "L2"
            }
        }
    
    def test_add_fragment(self):
        """Test adding fragments to pool."""
        fragment = {"case_id": "frag1", "params": {"dim": 128}}
        self.fuzzer.add_fragment(fragment)
        
        self.assertEqual(len(self.fuzzer.fragment_pool), 1)
    
    def test_fuzz_requires_multiple_fragments(self):
        """Test that fuzz() requires at least 2 fragments."""
        results = self.fuzzer.fuzz(self.base_case)
        
        # Should return skipped result
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, FuzzingStatus.SKIPPED)
    
    def test_fuzz_with_fragments(self):
        """Test fuzzing with multiple fragments."""
        # Add fragments
        self.fuzzer.add_fragment({
            "case_id": "frag1",
            "params": {"top_k": 5, "metric": "IP"}
        })
        self.fuzzer.add_fragment({
            "case_id": "frag2",
            "params": {"dim": 256, "nlist": 128}
        })
        
        results = self.fuzzer.fuzz(self.base_case)
        self.assertGreater(len(results), 0)
    
    def test_splice_cases(self):
        """Test case splicing."""
        case1 = {
            "case_id": "case1",
            "params": {"a": 1, "b": 2, "c": 3}
        }
        case2 = {
            "case_id": "case2",
            "params": {"b": 20, "c": 30, "d": 40}
        }
        
        spliced = self.fuzzer._splice_cases(case1, case2)
        
        self.assertIn("_spliced", spliced)
        self.assertIn("params", spliced)


class TestCrossoverFuzzer(unittest.TestCase):
    """Tests for CrossoverFuzzer strategy."""
    
    def setUp(self):
        self.fuzzer = CrossoverFuzzer(seed=42)
        self.base_case = {
            "case_id": "parent1",
            "operation": "search",
            "params": {
                "top_k": 10,
                "metric": "L2",
                "dim": 128
            }
        }
    
    def test_add_parent(self):
        """Test adding parents to pool."""
        parent = {"case_id": "p1", "params": {"top_k": 5}}
        self.fuzzer.add_parent(parent)
        
        self.assertEqual(len(self.fuzzer.parent_pool), 1)
    
    def test_fuzz_requires_multiple_parents(self):
        """Test that fuzz() requires at least 2 parents."""
        results = self.fuzzer.fuzz(self.base_case)
        
        # Should return skipped result
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, FuzzingStatus.SKIPPED)
    
    def test_fuzz_with_parents(self):
        """Test fuzzing with multiple parents."""
        # Add parents
        self.fuzzer.add_parent({
            "case_id": "parent2",
            "params": {"top_k": 20, "metric": "IP", "dim": 256}
        })
        
        results = self.fuzzer.fuzz(self.base_case)
        self.assertGreater(len(results), 0)
    
    def test_crossover(self):
        """Test crossover operation."""
        parent1 = {
            "case_id": "p1",
            "params": {"a": 1, "b": 2, "c": 3}
        }
        parent2 = {
            "case_id": "p2",
            "params": {"a": 10, "b": 20, "c": 30}
        }
        
        offspring = self.fuzzer._crossover(parent1, parent2)
        
        self.assertIn("_crossover", offspring)
        self.assertIn("_crossover_point", offspring)
        self.assertIn("params", offspring)
    
    def test_uniform_crossover(self):
        """Test uniform crossover operation."""
        parent1 = {
            "case_id": "p1",
            "params": {"a": 1, "b": 2}
        }
        parent2 = {
            "case_id": "p2",
            "params": {"a": 10, "b": 20}
        }
        
        offspring = self.fuzzer._uniform_crossover(parent1, parent2)
        
        self.assertIn("_uniform_crossover", offspring)
        self.assertIn("params", offspring)


class TestStrategySelector(unittest.TestCase):
    """Tests for StrategySelector."""
    
    def setUp(self):
        self.selector = StrategySelector(mode=SelectionMode.RANDOM, seed=42)
    
    def test_initialization(self):
        """Test selector initialization."""
        self.assertEqual(self.selector.mode, SelectionMode.RANDOM)
        self.assertEqual(len(self.selector.strategies), 6)  # All 6 strategies
    
    def test_select_random(self):
        """Test random strategy selection."""
        strategy = self.selector._select_random()
        self.assertIsNotNone(strategy)
    
    def test_select_round_robin(self):
        """Test round-robin strategy selection."""
        selector = StrategySelector(mode=SelectionMode.ROUND_ROBIN, seed=42)
        
        strategy1 = selector._select_round_robin()
        strategy2 = selector._select_round_robin()
        
        # Should cycle through strategies
        self.assertIsNotNone(strategy1)
        self.assertIsNotNone(strategy2)
    
    def test_execute_fuzzing(self):
        """Test executing fuzzing with selector."""
        base_case = {
            "operation": "search",
            "params": {"top_k": 10, "metric": "L2"}
        }
        
        results = self.selector.execute_fuzzing(base_case, num_iterations=5)
        self.assertGreater(len(results), 0)
    
    def test_get_strategy_stats(self):
        """Test getting strategy statistics."""
        base_case = {
            "operation": "search",
            "params": {"top_k": 10}
        }
        
        # Execute some fuzzing
        self.selector.execute_fuzzing(base_case, num_iterations=3)
        
        stats = self.selector.get_strategy_stats()
        self.assertIn("random", stats)
        self.assertIn("boundary", stats)
        self.assertIn("attempts", stats["random"])
        self.assertIn("successes", stats["random"])
    
    def test_reset(self):
        """Test resetting selector state."""
        base_case = {"operation": "test", "params": {}}
        self.selector.execute_fuzzing(base_case, num_iterations=2)
        
        self.selector.reset()
        
        # Stats should be reset
        stats = self.selector.get_strategy_stats()
        for name in stats:
            self.assertEqual(stats[name]["attempts"], 0)


class TestFeedbackCollector(unittest.TestCase):
    """Tests for FeedbackCollector."""
    
    def setUp(self):
        self.collector = FeedbackCollector()
    
    def test_record_execution(self):
        """Test recording execution results."""
        test_case = {"operation": "search", "params": {"top_k": 10}}
        result = {"success": True}
        
        self.collector.record_execution(test_case, result)
        
        self.assertEqual(len(self.collector.execution_history), 1)
    
    def test_get_error_hotspots(self):
        """Test getting error hotspots."""
        # Record some errors
        for _ in range(5):
            self.collector.record_execution(
                {"operation": "search"},
                {"success": False, "error_type": "timeout"}
            )
        for _ in range(3):
            self.collector.record_execution(
                {"operation": "insert"},
                {"success": False, "error_type": "validation"}
            )
        
        hotspots = self.collector.get_error_hotspots(top_n=2)
        self.assertEqual(len(hotspots), 2)
        self.assertEqual(hotspots[0][0], "timeout")  # Most frequent
    
    def test_get_coverage_trend(self):
        """Test coverage trend analysis."""
        # Record with improving coverage
        for i in range(15):
            coverage = CoverageInfo(
                branches_hit=set(range(i)),
                total_branches=20
            )
            self.collector.record_execution(
                {"operation": "test"},
                {"success": True},
                coverage
            )
        
        trend = self.collector.get_coverage_trend()
        self.assertIn(trend, ["improving", "stable", "stagnant"])
    
    def test_suggest_focus_areas(self):
        """Test focus area suggestions."""
        # Record some errors
        self.collector.record_execution(
            {"operation": "search", "params": {"x": 1}},
            {"success": False, "error_type": "range_error"}
        )
        
        suggestions = self.collector.suggest_focus_areas()
        self.assertIsInstance(suggestions, list)


class TestCoverageInfo(unittest.TestCase):
    """Tests for CoverageInfo dataclass."""
    
    def test_branch_coverage(self):
        """Test branch coverage calculation."""
        info = CoverageInfo(
            branches_hit={1, 2, 3},
            total_branches=10
        )
        self.assertEqual(info.branch_coverage, 0.3)
    
    def test_line_coverage(self):
        """Test line coverage calculation."""
        info = CoverageInfo(
            lines_hit={1, 2, 3, 4, 5},
            total_lines=20
        )
        self.assertEqual(info.line_coverage, 0.25)
    
    def test_merge(self):
        """Test merging coverage info."""
        info1 = CoverageInfo(
            branches_hit={1, 2},
            lines_hit={1, 2},
            total_branches=10,
            total_lines=20
        )
        info2 = CoverageInfo(
            branches_hit={2, 3},
            lines_hit={2, 3},
            total_branches=10,
            total_lines=20
        )
        
        merged = info1.merge(info2)
        self.assertEqual(merged.branches_hit, {1, 2, 3})
        self.assertEqual(merged.lines_hit, {1, 2, 3})


class TestIntegration(unittest.TestCase):
    """Integration tests for the fuzzing system."""
    
    def test_all_strategies_with_same_input(self):
        """Test all strategies with the same input."""
        base_case = {
            "case_id": "test_case",
            "operation": "search",
            "params": {
                "top_k": 10,
                "metric": "L2",
                "dim": 128,
                "nprobe": 16
            }
        }
        
        strategies = [
            RandomFuzzer(seed=42),
            BoundaryFuzzer(seed=42),
            ArithmeticFuzzer(seed=42),
            DictionaryFuzzer(seed=42),
        ]
        
        for strategy in strategies:
            results = strategy.fuzz(base_case)
            self.assertGreater(len(results), 0, f"{strategy.name} should generate results")
    
    def test_strategy_selector_modes(self):
        """Test all strategy selector modes."""
        base_case = {
            "operation": "search",
            "params": {"top_k": 10}
        }
        
        modes = ["random", "round_robin", "feedback_driven", "adaptive"]
        
        for mode in modes:
            selector = create_selector(mode=mode, seed=42)
            results = selector.execute_fuzzing(base_case, num_iterations=3)
            self.assertIsInstance(results, list)


def create_test_suite():
    """Create a test suite with all tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestRandomFuzzer,
        TestBoundaryFuzzer,
        TestArithmeticFuzzer,
        TestDictionaryFuzzer,
        TestSplicingFuzzer,
        TestCrossoverFuzzer,
        TestStrategySelector,
        TestFeedbackCollector,
        TestCoverageInfo,
        TestIntegration,
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    return suite


if __name__ == "__main__":
    # Run all tests
    runner = unittest.TextTestRunner(verbosity=2)
    suite = create_test_suite()
    result = runner.run(suite)
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
