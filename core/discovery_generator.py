"""R5A Discovery Phase: High-Yield ANN Test Generator.

This module expands contract-driven test generation with aggressive strategies
designed to reveal real bugs in vector database implementations.
"""

from __future__ import annotations

import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from itertools import product

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.contract_registry import Contract, get_registry
from core.contract_test_generator import TestCase
from core.dataset_generators import DatasetGenerator, GeneratedDataset


@dataclass
class DiscoveryTest:
    """A high-yield discovery test case."""

    test_id: str
    contract_id: str
    name: str
    description: str
    family: str
    strategy: str

    # Test sequence
    setup: List[Dict[str, Any]]
    steps: List[Dict[str, Any]]
    cleanup: List[Dict[str, Any]]

    # Expected outcome
    expected_outcome: str
    expected_result: Optional[Dict[str, Any]]

    # Oracle definition
    oracle: Dict[str, Any]

    # Discovery-specific metadata
    priority: str = "high"
    estimated_complexity: str = "medium"
    tags: List[str] = field(default_factory=list)

    # Dataset info
    dataset_type: str = "random"
    dataset_description: str = ""

    # Discovery metadata
    discovery_strategy: str = ""
    bug_yield_potential: str = "medium"  # low, medium, high

    def to_dict(self) -> Dict[str, Any]:
        """Convert discovery test to dictionary."""
        return {
            "test_id": self.test_id,
            "contract_id": self.contract_id,
            "name": self.name,
            "description": self.description,
            "family": self.family,
            "strategy": self.strategy,
            "setup": self.setup,
            "steps": self.steps,
            "cleanup": self.cleanup,
            "expected_outcome": self.expected_outcome,
            "expected_result": self.expected_result,
            "oracle": self.oracle,
            "priority": self.priority,
            "estimated_complexity": self.estimated_complexity,
            "tags": self.tags,
            "dataset_type": self.dataset_type,
            "dataset_description": self.dataset_description,
            "discovery_strategy": self.discovery_strategy,
            "bug_yield_potential": self.bug_yield_potential
        }


class DiscoveryTestGenerator:
    """Generate high-yield discovery tests from ANN contracts."""

    def __init__(self, output_dir: Optional[str] = None):
        """Initialize discovery test generator.

        Args:
            output_dir: Directory for generated tests (default: generated_tests/)
        """
        if output_dir is None:
            project_root = Path(__file__).parent.parent
            output_dir = project_root / "generated_tests"

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        self.registry = get_registry()
        self.dataset_generator = DatasetGenerator(dimension=128)

        # Discovery strategies
        self.strategies = [
            "combinatorial_params",
            "degenerate_vectors",
            "duplicate_datasets",
            "extreme_values",
            "size_edge_cases",
            "cross_metric",
            "index_stress",
            "dataset_variety"
        ]

    def generate_discovery_set(self, target_size: int = 50) -> List[DiscoveryTest]:
        """Generate a comprehensive ANN discovery test set.

        Args:
            target_size: Target number of tests to generate

        Returns:
            List of discovery test cases
        """
        print(f"[*] Generating ANN Discovery Test Set (target: {target_size} tests)")

        all_tests = []

        # Get ANN contracts
        ann_contracts = self.registry.get_contracts_by_family("ANN")

        # Generate tests by strategy
        strategy_allocation = self._allocate_strategies(target_size, len(ann_contracts))

        for strategy, count in strategy_allocation.items():
            print(f"[*] Strategy: {strategy} -> {count} tests")
            tests = self._generate_by_strategy(strategy, ann_contracts, count)
            all_tests.extend(tests)

        # Shuffle to mix strategies
        random.shuffle(all_tests)

        # Assign sequential IDs
        for i, test in enumerate(all_tests, 1):
            test.test_id = f"ann_discovery_{i:03d}"

        print(f"[+] Generated {len(all_tests)} discovery tests")

        return all_tests

    def _allocate_strategies(self, target_size: int, num_contracts: int) -> Dict[str, int]:
        """Allocate test counts to strategies.

        Args:
            target_size: Target total number of tests
            num_contracts: Number of ANN contracts

        Returns:
            Dictionary mapping strategy names to test counts
        """
        # Allocate tests to strategies
        allocation = {}

        # Core strategies get more tests
        allocation["dataset_variety"] = target_size // 4  # 25%
        allocation["combinatorial_params"] = target_size // 5  # 20%
        allocation["degenerate_vectors"] = target_size // 5  # 20%
        allocation["extreme_values"] = target_size // 6  # ~17%
        allocation["size_edge_cases"] = target_size // 8  # ~12%
        allocation["cross_metric"] = max(2, target_size // 10)  # ~10%
        allocation["index_stress"] = max(2, target_size // 12)  # ~8%
        allocation["duplicate_datasets"] = max(2, target_size // 15)  # ~7%

        # Adjust to hit target
        total = sum(allocation.values())
        if total < target_size:
            # Add remainder to dataset_variety
            allocation["dataset_variety"] += (target_size - total)
        elif total > target_size:
            # Reduce from largest allocation
            largest = max(allocation, key=allocation.get)
            allocation[largest] -= (total - target_size)

        return allocation

    def _generate_by_strategy(
        self,
        strategy: str,
        contracts: List[Contract],
        count: int
    ) -> List[DiscoveryTest]:
        """Generate tests using a specific strategy.

        Args:
            strategy: Discovery strategy name
            contracts: ANN contracts
            count: Number of tests to generate

        Returns:
            List of discovery test cases
        """
        tests = []

        if strategy == "dataset_variety":
            tests = self._generate_dataset_variety_tests(contracts, count)
        elif strategy == "combinatorial_params":
            tests = self._generate_combinatorial_tests(contracts, count)
        elif strategy == "degenerate_vectors":
            tests = self._generate_degenerate_tests(contracts, count)
        elif strategy == "extreme_values":
            tests = self._generate_extreme_value_tests(contracts, count)
        elif strategy == "size_edge_cases":
            tests = self._generate_size_edge_case_tests(contracts, count)
        elif strategy == "cross_metric":
            tests = self._generate_cross_metric_tests(contracts, count)
        elif strategy == "index_stress":
            tests = self._generate_index_stress_tests(contracts, count)
        elif strategy == "duplicate_datasets":
            tests = self._generate_duplicate_tests(contracts, count)

        return tests

    def _generate_dataset_variety_tests(
        self,
        contracts: List[Contract],
        count: int
    ) -> List[DiscoveryTest]:
        """Generate tests using varied dataset types.

        Tests different dataset characteristics to reveal behavior
        variations across data distributions.
        """
        tests = []

        # Dataset types to test
        dataset_types = [
            ("identical", "identical_vectors"),
            ("clustered", "clustered_vectors"),
            ("sparse", "sparse_vectors"),
            ("random", "random_vectors"),
        ]

        # Distribute tests across contracts and dataset types
        for contract in contracts:
            tests_per_contract = count // len(contracts)

            for i in range(tests_per_contract):
                dataset_type_name, dataset_method = dataset_types[i % len(dataset_types)]

                # Generate dataset
                if dataset_method == "identical_vectors":
                    dataset = self.dataset_generator.generate_identical_vectors(count=100)
                elif dataset_method == "clustered_vectors":
                    dataset = self.dataset_generator.generate_clustered_vectors(count=100, clusters=5)
                elif dataset_method == "sparse_vectors":
                    dataset = self.dataset_generator.generate_sparse_vectors(count=100, sparsity=0.9)
                else:  # random_vectors
                    dataset = self.dataset_generator.generate_random_vectors(count=100, seed=42+i)

                # Create test
                test = self._create_dataset_test(
                    contract=contract,
                    dataset=dataset,
                    variant=f"{dataset_type_name}_{i+1}"
                )
                tests.append(test)

        return tests

    def _generate_combinatorial_tests(
        self,
        contracts: List[Contract],
        count: int
    ) -> List[DiscoveryTest]:
        """Generate tests with combinatorial parameter combinations.

        Tests various combinations of parameters to reveal edge cases
        at parameter boundaries.
        """
        tests = []

        # Parameter combinations to test
        top_k_values = [0, 1, 10, 100, 1000]
        collection_sizes = [1, 10, 100, 1000]
        metric_types = ["L2", "IP", "COSINE"]

        # Generate combinations
        combinations = list(product(
            [c for c in contracts if c.contract_id == "ANN-001"],  # Top-K contract
            top_k_values[:3],  # Limit to avoid too many tests
            collection_sizes[:3],
            metric_types[:2]
        ))

        for i, (contract, top_k, collection_size, metric_type) in enumerate(combinations[:count]):
            test = DiscoveryTest(
                test_id="temp",
                contract_id=contract.contract_id,
                name=f"{contract.name} - Combo: top_k={top_k}, size={collection_size}, metric={metric_type}",
                description=f"Combinatorial parameter test for {contract.name}",
                family=contract.family,
                strategy="combinatorial",
                setup=self._create_setup(collection_size, metric_type),
                steps=self._create_search_step(top_k),
                cleanup=self._create_cleanup(),
                expected_outcome="at most top_k results",
                expected_result=None,
                oracle=contract.oracle,
                priority="high",
                estimated_complexity="medium",
                tags=["combinatorial", "boundary", contract.family],
                dataset_type="random",
                dataset_description=f"Random vectors, size={collection_size}",
                discovery_strategy="combinatorial_params",
                bug_yield_potential="high"
            )
            tests.append(test)

        return tests

    def _generate_degenerate_tests(
        self,
        contracts: List[Contract],
        count: int
    ) -> List[DiscoveryTest]:
        """Generate tests with degenerate/vector edge cases.

        Tests unusual vector patterns that might reveal implementation
        issues or numerical instabilities.
        """
        tests = []

        degenerate_patterns = [
            ("all_zeros", [0.0] * 128),
            ("all_ones", [1.0] * 128),
            ("alternating", [0.0 if i % 2 == 0 else 1.0 for i in range(128)]),
            ("single_nonzero", [0.0] * 127 + [1.0]),
            ("negative_values", [-1.0 if i % 2 == 0 else 1.0 for i in range(128)]),
        ]

        for contract in contracts[:2]:  # Focus on main contracts
            tests_per_contract = count // 2

            for i in range(tests_per_contract):
                pattern_name, pattern_vector = degenerate_patterns[i % len(degenerate_patterns)]

                # Create dataset with pattern
                dataset = GeneratedDataset(
                    vectors=[pattern_vector] * 100,
                    metadata={"type": "degenerate", "pattern": pattern_name},
                    description=f"Degenerate dataset: {pattern_name}"
                )

                test = self._create_dataset_test(
                    contract=contract,
                    dataset=dataset,
                    variant=f"degenerate_{pattern_name}_{i+1}"
                )
                test.discovery_strategy = "degenerate_vectors"
                test.bug_yield_potential = "high"
                tests.append(test)

        return tests

    def _generate_extreme_value_tests(
        self,
        contracts: List[Contract],
        count: int
    ) -> List[DiscoveryTest]:
        """Generate tests with extreme floating-point values.

        Tests numerical stability and handling of edge cases.
        """
        tests = []

        for contract in contracts[:2]:
            # Generate extreme value dataset
            dataset = self.dataset_generator.generate_extreme_vectors(count=100)

            for i in range(count // 2):
                test = self._create_dataset_test(
                    contract=contract,
                    dataset=dataset,
                    variant=f"extreme_{i+1}"
                )
                test.discovery_strategy = "extreme_values"
                test.bug_yield_potential = "high"
                tests.append(test)

        return tests

    def _generate_size_edge_case_tests(
        self,
        contracts: List[Contract],
        count: int
    ) -> List[DiscoveryTest]:
        """Generate tests at collection size boundaries.

        Tests behavior with empty, single-vector, and very small collections.
        """
        tests = []

        edge_datasets = self.dataset_generator.generate_size_edge_cases()

        for contract in contracts[:2]:
            for dataset in edge_datasets:
                test = self._create_dataset_test(
                    contract=contract,
                    dataset=dataset,
                    variant=f"size_edge_{dataset.metadata['edge_case']}"
                )
                test.discovery_strategy = "size_edge_cases"
                test.bug_yield_potential = "medium"
                tests.append(test)

        return tests[:count]

    def _generate_cross_metric_tests(
        self,
        contracts: List[Contract],
        count: int
    ) -> List[DiscoveryTest]:
        """Generate tests with metric type mismatches.

        Tests behavior when index metric differs from search metric,
        which can reveal inconsistent behavior.
        """
        tests = []

        # Focus on metric consistency contract
        metric_contract = next(c for c in contracts if c.contract_id == "ANN-004")

        metric_scenarios = [
            ("index_L2_search_L2", "L2", "L2"),
            ("index_L2_search_IP", "L2", "IP"),
            ("index_IP_search_IP", "IP", "IP"),
            ("index_COSINE_search_COSINE", "COSINE", "COSINE"),
        ]

        for i, (scenario, index_metric, search_metric) in enumerate(metric_scenarios[:count]):
            dataset = self.dataset_generator.generate_random_vectors(count=50, seed=i)

            test = DiscoveryTest(
                test_id="temp",
                contract_id=metric_contract.contract_id,
                name=f"Cross-metric test: {scenario}",
                description=f"Test with index_metric={index_metric}, search_metric={search_metric}",
                family=metric_contract.family,
                strategy="cross_metric",
                setup=self._create_setup(len(dataset.vectors), index_metric),
                steps=self._create_search_step(10, search_metric),
                cleanup=self._create_cleanup(),
                expected_outcome="consistent metric behavior",
                expected_result=None,
                oracle=metric_contract.oracle,
                priority="high",
                estimated_complexity="medium",
                tags=["cross_metric", "consistency", metric_contract.family],
                dataset_type="random",
                dataset_description=dataset.description,
                discovery_strategy="cross_metric",
                bug_yield_potential="high"
            )
            tests.append(test)

        return tests

    def _generate_index_stress_tests(
        self,
        contracts: List[Contract],
        count: int
    ) -> List[DiscoveryTest]:
        """Generate tests stressing index parameters.

        Tests various index configurations to reveal issues with
        different index types and parameters.
        """
        tests = []

        # Index parameter combinations
        index_configs = [
            ("IVF_FLAT_nlist_128", {"index_type": "IVF_FLAT", "nlist": 128}),
            ("IVF_FLAT_nlist_1024", {"index_type": "IVF_FLAT", "nlist": 1024}),
            ("HNSW_M_16", {"index_type": "HNSW", "M": 16}),
            ("HNSW_M_32", {"index_type": "HNSW", "M": 32}),
        ]

        for contract in contracts[:2]:
            for i, (config_name, index_params) in enumerate(index_configs[:count//2]):
                dataset = self.dataset_generator.generate_random_vectors(count=200, seed=i)

                test = DiscoveryTest(
                    test_id="temp",
                    contract_id=contract.contract_id,
                    name=f"Index stress test: {config_name}",
                    description=f"Test with index configuration: {config_name}",
                    family=contract.family,
                    strategy="index_stress",
                    setup=self._create_setup(len(dataset.vectors), "L2", index_params),
                    steps=self._create_search_step(10),
                    cleanup=self._create_cleanup(),
                    expected_outcome="correct search results",
                    expected_result=None,
                    oracle=contract.oracle,
                    priority="high",
                    estimated_complexity="high",
                    tags=["index_stress", "performance", contract.family],
                    dataset_type="random",
                    dataset_description=dataset.description,
                    discovery_strategy="index_stress",
                    bug_yield_potential="medium"
                )
                tests.append(test)

        return tests

    def _generate_duplicate_tests(
        self,
        contracts: List[Contract],
        count: int
    ) -> List[DiscoveryTest]:
        """Generate tests with duplicate vectors.

        Tests tie-breaking behavior and result consistency.
        """
        tests = []

        for contract in contracts[:2]:
            dataset = self.dataset_generator.generate_duplicate_vectors(
                count=100,
                duplication_rate=0.3
            )

            for i in range(count // 2):
                test = self._create_dataset_test(
                    contract=contract,
                    dataset=dataset,
                    variant=f"duplicates_{i+1}"
                )
                test.discovery_strategy = "duplicate_datasets"
                test.bug_yield_potential = "medium"
                test.tags.append("tie_breaking")
                tests.append(test)

        return tests

    def _create_dataset_test(
        self,
        contract: Contract,
        dataset: GeneratedDataset,
        variant: str
    ) -> DiscoveryTest:
        """Create a discovery test from a contract and dataset.

        Args:
            contract: Contract specification
            dataset: Generated dataset
            variant: Test variant identifier

        Returns:
            Discovery test case
        """
        # Determine top_k based on dataset size
        dataset_size = len(dataset.vectors)
        if dataset_size == 0:
            top_k = 0
        elif dataset_size == 1:
            top_k = 1
        else:
            top_k = min(10, dataset_size)

        metric_type = "L2"  # Default metric

        return DiscoveryTest(
            test_id="temp",
            contract_id=contract.contract_id,
            name=f"{contract.name} - Discovery: {variant}",
            description=f"Discovery test for {contract.name} with {dataset.description}",
            family=contract.family,
            strategy="discovery",
            setup=self._create_setup(dataset_size, metric_type),
            steps=self._create_search_step(top_k),
            cleanup=self._create_cleanup(),
            expected_outcome="contract-compliant behavior",
            expected_result=None,
            oracle=contract.oracle,
            priority="high",
            estimated_complexity="medium",
            tags=["discovery", "high_yield", contract.family, dataset.metadata["type"]],
            dataset_type=dataset.metadata["type"],
            dataset_description=dataset.description,
            discovery_strategy="dataset_variety",
            bug_yield_potential="medium"
        )

    def _create_setup(
        self,
        collection_size: int,
        metric_type: str = "L2",
        index_params: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """Create setup steps for test.

        Args:
            collection_size: Number of vectors in collection
            metric_type: Distance metric type
            index_params: Index parameters

        Returns:
            List of setup operations
        """
        setup = [
            {"operation": "create_collection", "params": {
                "dimension": 128,
                "metric_type": metric_type
            }},
            {"operation": "insert_vectors", "params": {
                "count": collection_size,
                "dataset_type": "generated"
            }}
        ]

        if index_params:
            setup.append({"operation": "create_index", "params": index_params})
        else:
            setup.append({"operation": "create_index", "params": {
                "index_type": "IVF_FLAT",
                "nlist": 128
            }})

        setup.append({"operation": "load_collection", "params": {}})

        return setup

    def _create_search_step(self, top_k: int, metric_type: str = "L2") -> List[Dict[str, Any]]:
        """Create search step for test.

        Args:
            top_k: Number of results to return
            metric_type: Distance metric type

        Returns:
            List of search operations
        """
        return [{
            "operation": "search",
            "params": {
                "top_k": top_k,
                "metric_type": metric_type
            },
            "description": f"Execute search with top_k={top_k}"
        }]

    def _create_cleanup(self) -> List[Dict[str, Any]]:
        """Create cleanup steps for test.

        Returns:
            List of cleanup operations
        """
        return [
            {"operation": "drop_collection", "description": "Drop test collection"},
            {"operation": "cleanup_test_data", "description": "Cleanup test data"}
        ]

    def save_tests(self, tests: List[DiscoveryTest]) -> str:
        """Save discovery tests to file.

        Args:
            tests: List of discovery test cases

        Returns:
            Path to saved test file
        """
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"ann_discovery_{timestamp}.json"
        output_path = self.output_dir / filename

        test_data = {
            "suite_name": "ann_discovery",
            "generated_at": datetime.now().isoformat(),
            "total_tests": len(tests),
            "contracts_covered": list(set(t.contract_id for t in tests)),
            "strategies_used": list(set(t.discovery_strategy for t in tests)),
            "tests": [t.to_dict() for t in tests]
        }

        import json
        with open(output_path, 'w') as f:
            json.dump(test_data, f, indent=2)

        return str(output_path)


if __name__ == "__main__":
    # Generate ANN discovery test set
    generator = DiscoveryTestGenerator()

    print("=" * 70)
    print("R5A-DISCOVERY: High-Yield ANN Test Generation")
    print("=" * 70)

    # Generate discovery set
    discovery_tests = generator.generate_discovery_set(target_size=50)

    # Save tests
    output_path = generator.save_tests(discovery_tests)
    print(f"\n[Saved] Discovery tests: {output_path}")

    # Print summary
    print("\n" + "=" * 70)
    print("Discovery Test Summary")
    print("=" * 70)

    by_strategy = {}
    by_contract = {}
    by_potential = {}

    for test in discovery_tests:
        strategy = test.discovery_strategy
        by_strategy[strategy] = by_strategy.get(strategy, 0) + 1

        contract = test.contract_id
        by_contract[contract] = by_contract.get(contract, 0) + 1

        potential = test.bug_yield_potential
        by_potential[potential] = by_potential.get(potential, 0) + 1

    print(f"\nBy Discovery Strategy:")
    for strategy, count in by_strategy.items():
        print(f"  {strategy}: {count}")

    print(f"\nBy Contract:")
    for contract, count in by_contract.items():
        print(f"  {contract}: {count}")

    print(f"\nBy Bug Yield Potential:")
    for potential, count in by_potential.items():
        print(f"  {potential}: {count}")

    print(f"\n[Total] {len(discovery_tests)} discovery tests generated")
