"""Fuzzing module for test case generation.

This module provides various fuzzing strategies for generating
diverse test cases to improve bug detection coverage.
"""

from casegen.fuzzing.base import (
    FuzzingStrategy, 
    FuzzingResult, 
    FuzzingStatus,
    CoverageInfo,
    FeedbackCollector
)
from casegen.fuzzing.random_fuzzer import RandomFuzzer
from casegen.fuzzing.boundary_fuzzer import BoundaryFuzzer
from casegen.fuzzing.arithmetic_fuzzer import ArithmeticFuzzer
from casegen.fuzzing.dictionary_fuzzer import DictionaryFuzzer
from casegen.fuzzing.splicing_fuzzer import SplicingFuzzer
from casegen.fuzzing.crossover_fuzzer import CrossoverFuzzer
from casegen.fuzzing.strategy_selector import (
    StrategySelector,
    SelectionMode,
    create_selector
)

__all__ = [
    # Base
    'FuzzingStrategy',
    'FuzzingResult',
    'FuzzingStatus',
    'CoverageInfo',
    'FeedbackCollector',
    # Fuzzers
    'RandomFuzzer',
    'BoundaryFuzzer',
    'ArithmeticFuzzer',
    'DictionaryFuzzer',
    'SplicingFuzzer',
    'CrossoverFuzzer',
    # Strategy Selector
    'StrategySelector',
    'SelectionMode',
    'create_selector',
]