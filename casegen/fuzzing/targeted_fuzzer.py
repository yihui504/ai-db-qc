"""Targeted Fuzzer for specific contract testing.

This fuzzer focuses on specific contracts and parameters,
generating targeted test cases to find bugs in specific areas.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import random
import json
from dataclasses import dataclass

from .base import FuzzingStrategy, FuzzingResult, FuzzingStatus, generate_random_vector


@dataclass
class TargetConfig:
    """Configuration for targeted fuzzing.

    Attributes:
        contract_id: Target contract ID (e.g., "BND-001", "SCH-005")
        parameters: List of parameter names to fuzz
        mutation_types: Types of mutations to apply
        focus_areas: Specific areas to focus on
    """
    contract_id: str
    parameters: List[str]
    mutation_types: List[str]
    focus_areas: List[str]


class TargetedFuzzer(FuzzingStrategy):
    """Fuzzer that targets specific contracts and parameters.

    Unlike random fuzzing, this fuzzer focuses on specific contracts
    and parameters, generating mutations based on known vulnerability
    patterns.

    Mutation types:
    - boundary: Test boundary values (0, 1, -1, max, max+1)
    - type: Change parameter types (int -> string, etc.)
    - format: Change format (case, special chars, etc.)
    - sequence: Test sequences of operations
    - concurrent: Test concurrent operations
    """

    def __init__(
        self,
        target_config: TargetConfig,
        max_iterations: int = 500,
        seed: Optional[int] = None
    ):
        """Initialize targeted fuzzer.

        Args:
            target_config: Configuration for targeted fuzzing
            max_iterations: Maximum number of fuzzing iterations
            seed: Random seed for reproducibility
        """
        super().__init__(
            name=f"Targeted-{target_config.contract_id}",
            max_iterations=max_iterations,
            seed=seed
        )
        self.target_config = target_config

    def fuzz(
        self,
        base_case: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> List[FuzzingResult]:
        """Generate targeted fuzzed test cases.

        Args:
            base_case: Base test case to fuzz
            context: Additional context for fuzzing

        Returns:
            List of fuzzing results
        """
        results = []

        # Generate mutations based on mutation types
        for mutation_type in self.target_config.mutation_types:
            mutation_results = self._generate_mutations(
                base_case,
                mutation_type,
                context
            )
            results.extend(mutation_results)

        # Add boundary value tests
        if "boundary" in self.target_config.mutation_types:
            boundary_results = self._generate_boundary_tests(base_case, context)
            results.extend(boundary_results)

        # Add parameter-specific tests
        for param in self.target_config.parameters:
            param_results = self._generate_parameter_tests(
                base_case,
                param,
                context
            )
            results.extend(param_results)

        # Add to corpus
        for result in results:
            if result.test_case:
                self.add_to_corpus(result.test_case)

        return results

    def _generate_mutations(
        self,
        base_case: Dict[str, Any],
        mutation_type: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[FuzzingResult]:
        """Generate mutations based on type.

        Args:
            base_case: Base test case
            mutation_type: Type of mutation
            context: Additional context

        Returns:
            List of fuzzing results
        """
        results = []
        params = base_case.get("params", {})

        if mutation_type == "type":
            # Type mutations
            for param_name in params:
                for mutated in self._type_mutations(params[param_name]):
                    mutated_case = base_case.copy()
                    mutated_case["params"] = params.copy()
                    mutated_case["params"][param_name] = mutated

                    results.append(FuzzingResult(
                        status=FuzzingStatus.SUCCESS,
                        test_case=mutated_case,
                        seed=self.seed,
                        metadata={"mutation_type": "type", "param": param_name}
                    ))

        elif mutation_type == "format":
            # Format mutations
            for param_name in params:
                if isinstance(params[param_name], str):
                    for mutated in self._format_mutations(params[param_name]):
                        mutated_case = base_case.copy()
                        mutated_case["params"] = params.copy()
                        mutated_case["params"][param_name] = mutated

                        results.append(FuzzingResult(
                            status=FuzzingStatus.SUCCESS,
                            test_case=mutated_case,
                            seed=self.seed,
                            metadata={"mutation_type": "format", "param": param_name}
                        ))

        elif mutation_type == "sequence":
            # Sequence mutations
            results.extend(self._generate_sequence_mutations(base_case, context))

        elif mutation_type == "concurrent":
            # Concurrent mutations
            results.extend(self._generate_concurrent_mutations(base_case, context))

        return results

    def _generate_boundary_tests(
        self,
        base_case: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> List[FuzzingResult]:
        """Generate boundary value tests.

        Args:
            base_case: Base test case
            context: Additional context

        Returns:
            List of fuzzing results with boundary values
        """
        results = []
        params = base_case.get("params", {})

        # Boundary values for numeric parameters
        for param_name in params:
            value = params[param_name]

            if isinstance(value, int) or isinstance(value, float):
                # Numeric boundary tests
                boundary_values = [0, 1, -1, 2**31-1, 2**31, -2**31, 2**63-1]

                for boundary in boundary_values:
                    mutated_case = base_case.copy()
                    mutated_case["params"] = params.copy()
                    mutated_case["params"][param_name] = boundary

                    results.append(FuzzingResult(
                        status=FuzzingStatus.SUCCESS,
                        test_case=mutated_case,
                        seed=self.seed,
                        metadata={"mutation_type": "boundary", "param": param_name, "value": boundary}
                    ))

            elif isinstance(value, list):
                # List boundary tests
                boundary_lists = [[], [0], [0, 0], [0] * 10000]

                for boundary in boundary_lists:
                    mutated_case = base_case.copy()
                    mutated_case["params"] = params.copy()
                    mutated_case["params"][param_name] = boundary

                    results.append(FuzzingResult(
                        status=FuzzingStatus.SUCCESS,
                        test_case=mutated_case,
                        seed=self.seed,
                        metadata={"mutation_type": "boundary", "param": param_name, "value": len(boundary)}
                    ))

        return results

    def _generate_parameter_tests(
        self,
        base_case: Dict[str, Any],
        param_name: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[FuzzingResult]:
        """Generate parameter-specific tests.

        Args:
            base_case: Base test case
            param_name: Parameter to test
            context: Additional context

        Returns:
            List of fuzzing results for parameter
        """
        results = []
        params = base_case.get("params", {})

        if param_name not in params:
            return results

        value = params[param_name]

        # Contract-specific parameter tests
        if param_name == "dimension":
            # BND-001: Dimension boundary tests
            dimension_values = [0, 1, -1, 128, 256, 1024, 4096, 32768, 100000]
            for dim in dimension_values:
                mutated_case = base_case.copy()
                mutated_case["params"] = params.copy()
                mutated_case["params"]["dimension"] = dim

                results.append(FuzzingResult(
                    status=FuzzingStatus.SUCCESS,
                    test_case=mutated_case,
                    seed=self.seed,
                    metadata={"mutation_type": "parameter_specific", "param": "dimension", "value": dim}
                ))

        elif param_name == "top_k":
            # BND-002: Top-K boundary tests
            top_k_values = [0, 1, -1, 10, 100, 1000, 10000, 100000]
            for tk in top_k_values:
                mutated_case = base_case.copy()
                mutated_case["params"] = params.copy()
                mutated_case["params"]["top_k"] = tk

                results.append(FuzzingResult(
                    status=FuzzingStatus.SUCCESS,
                    test_case=mutated_case,
                    seed=self.seed,
                    metadata={"mutation_type": "parameter_specific", "param": "top_k", "value": tk}
                ))

        elif param_name == "metric_type":
            # BND-003: Metric type tests
            metric_values = ["L2", "IP", "COSINE", "l2", "ip", "cosine", "",
                            "INVALID", None, 123, "Euclidean", "Manhattan"]
            for mt in metric_values:
                mutated_case = base_case.copy()
                mutated_case["params"] = params.copy()
                mutated_case["params"]["metric_type"] = mt

                results.append(FuzzingResult(
                    status=FuzzingStatus.SUCCESS,
                    test_case=mutated_case,
                    seed=self.seed,
                    metadata={"mutation_type": "parameter_specific", "param": "metric_type", "value": mt}
                ))

        elif param_name == "collection_name":
            # BND-004: Collection name tests
            name_values = [
                "", "a", "ab", "abc",
                "test_collection", "test-collection", "test/collection",
                "123_invalid", "_invalid", "invalid name",
                "system", "System", "SYSTEM",
                "a" * 256, "x" * 1000
            ]
            for name in name_values:
                mutated_case = base_case.copy()
                mutated_case["params"] = params.copy()
                mutated_case["params"]["collection_name"] = name

                results.append(FuzzingResult(
                    status=FuzzingStatus.SUCCESS,
                    test_case=mutated_case,
                    seed=self.seed,
                    metadata={"mutation_type": "parameter_specific", "param": "collection_name", "value": name}
                ))

        elif param_name == "vector" or param_name == "vectors":
            # Vector boundary tests
            dimension = params.get("dimension", 128)

            # Wrong dimension
            wrong_dim_vec = generate_random_vector(dimension + 1, self.rng)
            mutated_case = base_case.copy()
            mutated_case["params"] = params.copy()
            if param_name == "vector":
                mutated_case["params"]["vector"] = wrong_dim_vec
            else:
                mutated_case["params"]["vectors"] = [wrong_dim_vec]

            results.append(FuzzingResult(
                status=FuzzingStatus.SUCCESS,
                test_case=mutated_case,
                seed=self.seed,
                metadata={"mutation_type": "parameter_specific", "param": param_name, "issue": "wrong_dimension"}
            ))

            # Empty vector
            mutated_case = base_case.copy()
            mutated_case["params"] = params.copy()
            if param_name == "vector":
                mutated_case["params"]["vector"] = []
            else:
                mutated_case["params"]["vectors"] = []

            results.append(FuzzingResult(
                status=FuzzingStatus.SUCCESS,
                test_case=mutated_case,
                seed=self.seed,
                metadata={"mutation_type": "parameter_specific", "param": param_name, "issue": "empty"}
            ))

            # Vector with NaN/Inf
            nan_vec = [float('nan')] * dimension
            mutated_case = base_case.copy()
            mutated_case["params"] = params.copy()
            if param_name == "vector":
                mutated_case["params"]["vector"] = nan_vec
            else:
                mutated_case["params"]["vectors"] = [nan_vec]

            results.append(FuzzingResult(
                status=FuzzingStatus.SUCCESS,
                test_case=mutated_case,
                seed=self.seed,
                metadata={"mutation_type": "parameter_specific", "param": param_name, "issue": "nan_values"}
            ))

        return results

    def _type_mutations(self, value: Any) -> List[Any]:
        """Generate type mutations for a value.

        Args:
            value: Original value

        Returns:
            List of mutated values with different types
        """
        mutations = []

        # Try common type mutations
        mutations.append(None)  # None
        mutations.append("")     # Empty string
        mutations.append([])     # Empty list
        mutations.append({})     # Empty dict

        if isinstance(value, (int, float)):
            mutations.append(str(value))    # int -> string
            mutations.append([value])       # int -> list
            mutations.append(False)        # int -> bool

        elif isinstance(value, str):
            try:
                mutations.append(int(value))     # string -> int
            except ValueError:
                pass
            mutations.append(123)             # string -> int
            mutations.append([value])         # string -> list

        elif isinstance(value, list):
            mutations.append(str(value))     # list -> string
            if value:
                mutations.append(value[0])   # list -> first element

        return mutations

    def _format_mutations(self, value: str) -> List[str]:
        """Generate format mutations for a string value.

        Args:
            value: Original string value

        Returns:
            List of mutated strings with different formats
        """
        mutations = []

        # Case variations
        mutations.append(value.upper())
        mutations.append(value.lower())
        mutations.append(value.swapcase())

        # Special characters
        mutations.append(f"{value} ")
        mutations.append(f" {value}")
        mutations.append(f"{value}\n")
        mutations.append(f"{value}\t")

        # SQL injection patterns
        mutations.append(f"{value}'; DROP TABLE--")
        mutations.append(f"{value}\" OR \"1\"=\"1")

        # Path traversal patterns
        mutations.append(f"{value}../..")
        mutations.append(f"{value}%2e%2e%2f")

        return mutations

    def _generate_sequence_mutations(
        self,
        base_case: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> List[FuzzingResult]:
        """Generate sequence mutations.

        Args:
            base_case: Base test case
            context: Additional context

        Returns:
            List of fuzzing results with sequence operations
        """
        results = []

        # Create sequences of operations
        sequences = [
            ["create_collection", "create_collection"],  # Duplicate create
            ["create_collection", "drop_collection", "drop_collection"],  # Double drop
            ["create_collection", "insert", "drop_collection", "search"],  # Search after drop
            ["create_collection", "build_index", "build_index"],  # Double index build
            ["create_collection", "insert", "search"],  # Search without index
            ["create_collection", "insert", "insert"],  # Duplicate insert with same IDs
        ]

        for sequence in sequences:
            mutated_case = base_case.copy()
            mutated_case["sequence"] = sequence

            results.append(FuzzingResult(
                status=FuzzingStatus.SUCCESS,
                test_case=mutated_case,
                seed=self.seed,
                metadata={"mutation_type": "sequence", "sequence": sequence}
            ))

        return results

    def _generate_concurrent_mutations(
        self,
        base_case: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> List[FuzzingResult]:
        """Generate concurrent mutations.

        Args:
            base_case: Base test case
            context: Additional context

        Returns:
            List of fuzzing results with concurrent operations
        """
        results = []

        # Concurrent operation patterns
        patterns = [
            {"name": "concurrent_insert", "threads": 10, "operation": "insert"},
            {"name": "concurrent_search", "threads": 10, "operation": "search"},
            {"name": "mixed_concurrent", "threads": 5, "operations": ["insert", "search", "delete"]},
        ]

        for pattern in patterns:
            mutated_case = base_case.copy()
            mutated_case["concurrent"] = pattern

            results.append(FuzzingResult(
                status=FuzzingStatus.SUCCESS,
                test_case=mutated_case,
                seed=self.seed,
                metadata={"mutation_type": "concurrent", "pattern": pattern["name"]}
            ))

        return results


# Factory functions for common target configurations

def create_boundary_fuzzer(contract_id: str, parameters: List[str]) -> TargetedFuzzer:
    """Create a fuzzer focused on boundary testing.

    Args:
        contract_id: Contract ID to target
        parameters: List of parameters to test

    Returns:
        Configured TargetedFuzzer
    """
    config = TargetConfig(
        contract_id=contract_id,
        parameters=parameters,
        mutation_types=["boundary", "type"],
        focus_areas=["validation"]
    )
    return TargetedFuzzer(config, max_iterations=500)


def create_schema_fuzzer(contract_id: str) -> TargetedFuzzer:
    """Create a fuzzer focused on schema evolution.

    Args:
        contract_id: Contract ID to target

    Returns:
        Configured TargetedFuzzer
    """
    config = TargetConfig(
        contract_id=contract_id,
        parameters=["collection_name", "dimension", "metric_type"],
        mutation_types=["sequence", "concurrent"],
        focus_areas=["atomicity", "compatibility"]
    )
    return TargetedFuzzer(config, max_iterations=300)


def create_stress_fuzzer(contract_id: str) -> TargetedFuzzer:
    """Create a fuzzer focused on stress testing.

    Args:
        contract_id: Contract ID to target

    Returns:
        Configured TargetedFuzzer
    """
    config = TargetConfig(
        contract_id=contract_id,
        parameters=["vectors", "top_k"],
        mutation_types=["boundary", "concurrent"],
        focus_areas=["throughput", "volume"]
    )
    return TargetedFuzzer(config, max_iterations=200)


__all__ = [
    'TargetedFuzzer',
    'TargetConfig',
    'create_boundary_fuzzer',
    'create_schema_fuzzer',
    'create_stress_fuzzer',
]
