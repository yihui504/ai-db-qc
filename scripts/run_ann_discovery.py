"""R5A-DISCOVERY: High-Yield ANN Test Executor.

This script executes the ANN discovery test set on real Milvus and evaluates
results using the contract oracle engine, focusing on bug discovery capability.
"""

import json
import sys
import random
import math
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.contract_registry import get_registry
from core.oracle_engine import OracleEngine, OracleResult, Classification
from core.dataset_generators import DatasetGenerator

# Try to import Milvus adapter
try:
    from adapters.milvus_adapter import MilvusAdapter
    MILVUS_AVAILABLE = True
except ImportError:
    MILVUS_AVAILABLE = False
    print("[WARNING] Milvus adapter not available, will use mock mode")


# Utility functions for ground truth computation
def compute_l2_distance(v1: List[float], v2: List[float]) -> float:
    """Compute L2 (Euclidean) distance between vectors."""
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(v1, v2)))


def compute_inner_product(v1: List[float], v2: List[float]) -> float:
    """Compute inner product between vectors."""
    return sum(a * b for a, b in zip(v1, v2))


def compute_cosine_distance(v1: List[float], v2: List[float]) -> float:
    """Compute cosine distance (1 - cosine similarity)."""
    dot_product = compute_inner_product(v1, v2)
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(a * a for a in v2))

    if norm1 == 0 or norm2 == 0:
        return 0.0

    cosine_similarity = dot_product / (norm1 * norm2)
    return 1.0 - cosine_similarity


def compute_ground_truth_nn(query_vector: List[float], collection_vectors: List[tuple], metric_type: str = "L2") -> int:
    """Compute ground truth nearest neighbor using brute force."""
    min_distance = float('inf')
    nn_id = None

    for vec_id, vector in collection_vectors:
        if metric_type == "L2":
            distance = compute_l2_distance(query_vector, vector)
        elif metric_type == "IP":
            distance = -compute_inner_product(query_vector, vector)
        elif metric_type == "COSINE":
            distance = compute_cosine_distance(query_vector, vector)
        else:
            distance = compute_l2_distance(query_vector, vector)

        if distance < min_distance:
            min_distance = distance
            nn_id = vec_id

    return nn_id


class DiscoveryTestExecutor:
    """Execute high-yield discovery tests on real Milvus."""

    def __init__(self, test_file: str, is_real_database_run: bool = True):
        """Initialize discovery test executor.

        Args:
            test_file: Path to generated discovery test JSON file
            is_real_database_run: Whether to use real Milvus (True) or mock (False)
        """
        self.test_file = Path(test_file)
        self.is_real_database_run = is_real_database_run

        # Load test cases
        with open(self.test_file, 'r') as f:
            test_data = json.load(f)
            self.test_cases = test_data['tests']

        # Initialize registry and oracle engine
        self.registry = get_registry()
        self.oracle_engine = OracleEngine()
        self.dataset_generator = DatasetGenerator(dimension=128)

        # Initialize adapter
        if is_real_database_run and MILVUS_AVAILABLE:
            try:
                self.adapter = MilvusAdapter(connection_config={
                    "host": "localhost",
                    "port": 19530,
                    "alias": "default"
                })
                # Test connection
                if self.adapter.health_check():
                    print("[+] Using REAL Milvus database")
                else:
                    print("[!] Milvus health check failed, using mock execution")
                    self.adapter = None
            except Exception as e:
                print(f"[!] Milvus connection failed: {e}, using mock execution")
                self.adapter = None
        else:
            self.adapter = None
            if is_real_database_run:
                print("[!] Milvus adapter not available, using mock execution")
            else:
                print("[+] Using MOCK execution mode")

        self.results = []

    def execute_test(self, test: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single discovery test case.

        Args:
            test: Test case definition

        Returns:
            Execution result with raw output
        """
        test_id = test['test_id']
        contract_id = test['contract_id']
        dataset_type = test['dataset_type']

        print(f"\n[*] Executing: {test_id}")
        print(f"    Contract: {contract_id}")
        print(f"    Strategy: {test['discovery_strategy']}")
        print(f"    Dataset: {dataset_type}")
        print(f"    Bug Yield: {test['bug_yield_potential']}")

        result = {
            'test_id': test_id,
            'contract_id': contract_id,
            'strategy': test['discovery_strategy'],
            'dataset_type': dataset_type,
            'bug_yield_potential': test['bug_yield_potential'],
            'timestamp': datetime.now().isoformat(),
            'is_real_database': self.is_real_database_run and self.adapter is not None
        }

        if self.adapter is None:
            # Mock execution for infrastructure testing
            result['status'] = 'mock'
            result['results'] = self._mock_execute(test)
            result['error'] = None
        else:
            # Real Milvus execution
            try:
                result['results'] = self._execute_with_dataset(test)
                result['status'] = 'success'
                result['error'] = None
            except Exception as e:
                result['status'] = 'error'
                result['results'] = None
                result['error'] = str(e)
                print(f"    [!] Execution error: {e}")

        return result

    def _mock_execute(self, test: Dict[str, Any]) -> Dict[str, Any]:
        """Mock execution for infrastructure testing."""
        # Return mock results that should typically PASS
        return {
            'results': [
                {'id': i, 'distance': 0.1 * i, 'score': 0.1 * i}
                for i in range(min(10, 5))
            ],
            'top_k': 10
        }

    def _execute_with_dataset(self, test: Dict[str, Any]) -> Dict[str, Any]:
        """Execute test with appropriate dataset generation.

        Args:
            test: Test case definition

        Returns:
            Search results with metadata
        """
        contract_id = test['contract_id']
        dataset_type = test['dataset_type']

        # Generate dataset based on type
        if dataset_type == "identical":
            dataset = self.dataset_generator.generate_identical_vectors(count=100)
        elif dataset_type == "clustered":
            dataset = self.dataset_generator.generate_clustered_vectors(count=100, clusters=5)
        elif dataset_type == "sparse":
            dataset = self.dataset_generator.generate_sparse_vectors(count=100, sparsity=0.9)
        elif dataset_type == "extreme":
            dataset = self.dataset_generator.generate_extreme_vectors(count=100)
        elif dataset_type == "duplicates":
            dataset = self.dataset_generator.generate_duplicate_vectors(count=100, duplication_rate=0.3)
        elif dataset_type == "edge_case":
            # Use size edge cases
            edge_datasets = self.dataset_generator.generate_size_edge_cases()
            # Pick the appropriate one based on test description
            if "empty" in test['name']:
                dataset = edge_datasets[0]
            elif "single" in test['name']:
                dataset = edge_datasets[1]
            elif "two" in test['name']:
                dataset = edge_datasets[2]
            else:
                dataset = edge_datasets[3]  # small
        elif dataset_type == "degenerate":
            # Generate degenerate dataset based on test name
            if "all_zeros" in test['name']:
                pattern = [0.0] * 128
            elif "all_ones" in test['name']:
                pattern = [1.0] * 128
            elif "alternating" in test['name']:
                pattern = [0.0 if i % 2 == 0 else 1.0 for i in range(128)]
            elif "single_nonzero" in test['name']:
                pattern = [0.0] * 127 + [1.0]
            else:  # negative_values
                pattern = [-1.0 if i % 2 == 0 else 1.0 for i in range(128)]

            dataset = type('Dataset', (), {
                'vectors': [pattern] * 100,
                'metadata': {'type': 'degenerate'},
                'description': f"Degenerate dataset: {test['name'].split('_')[-1]}"
            })()
        else:  # random or default
            dataset = self.dataset_generator.generate_random_vectors(count=100, seed=42)

        # Get test parameters
        steps = test['steps'][0]
        top_k = steps['params'].get('top_k', 10)
        metric_type = steps['params'].get('metric_type', 'L2')

        # Execute on Milvus
        collection_name = f"test_discovery_{datetime.now().strftime('%Y%m%d%H%M%S')}_{random.randint(1000, 9999)}"

        try:
            # Create collection
            self.adapter.execute({
                "operation": "create_collection",
                "params": {
                    "collection_name": collection_name,
                    "dimension": 128,
                    "metric_type": metric_type
                }
            })

            # Insert vectors
            if len(dataset.vectors) > 0:
                self.adapter.execute({
                    "operation": "insert",
                    "params": {
                        "collection_name": collection_name,
                        "vectors": dataset.vectors
                    }
                })

                # Create index
                self.adapter.execute({
                    "operation": "build_index",
                    "params": {"collection_name": collection_name}
                })

                # Load collection
                self.adapter.execute({
                    "operation": "load",
                    "params": {"collection_name": collection_name}
                })

                # Generate query vector
                if len(dataset.vectors) > 0:
                    # Use first vector as query for more interesting results
                    query_vector = dataset.vectors[0]
                else:
                    query_vector = [0.5] * 128

                # Execute search
                search_result = self.adapter.execute({
                    "operation": "search",
                    "params": {
                        "collection_name": collection_name,
                        "vector": query_vector,
                        "top_k": top_k
                    }
                })

                results = search_result.get('data', [])

                # Enhance results with ground truth for NN inclusion tests
                if contract_id == "ANN-003" and len(dataset.vectors) > 0:
                    collection_vectors = [(i, dataset.vectors[i]) for i in range(len(dataset.vectors))]
                    ground_truth_nn = compute_ground_truth_nn(query_vector, collection_vectors, metric_type)

                    return {
                        'results': results,
                        'top_k': top_k,
                        'ground_truth_nn_id': ground_truth_nn,
                        'dataset_description': dataset.description,
                        'dataset_type': dataset_type
                    }

                return {
                    'results': results,
                    'top_k': top_k,
                    'dataset_description': dataset.description,
                    'dataset_type': dataset_type
                }
            else:
                # Empty collection
                query_vector = [0.5] * 128
                try:
                    search_result = self.adapter.execute({
                        "operation": "search",
                        "params": {
                            "collection_name": collection_name,
                            "vector": query_vector,
                            "top_k": top_k
                        }
                    })
                    results = search_result.get('data', [])
                except:
                    results = []

                return {
                    'results': results,
                    'top_k': top_k,
                    'dataset_description': dataset.description,
                    'dataset_type': dataset_type,
                    'collection_empty': True
                }

        finally:
            # Cleanup
            try:
                self.adapter.execute({
                    "operation": "drop_collection",
                    "params": {"collection_name": collection_name}
                })
            except:
                pass

    def evaluate_oracle(self, execution_result: Dict[str, Any]) -> OracleResult:
        """Evaluate execution result against contract oracle.

        Args:
            execution_result: Result from test execution

        Returns:
            Oracle evaluation result
        """
        contract_id = execution_result['contract_id']

        # Get contract definition
        contract = self.registry.get_contract(contract_id)

        if contract is None:
            return OracleResult(
                contract_id=contract_id,
                classification=Classification.OBSERVATION,
                passed=False,
                reasoning=f"Contract {contract_id} not found in registry",
                evidence=execution_result
            )

        # Evaluate using oracle engine
        return self.oracle_engine.evaluate(
            contract_id=contract_id,
            execution_result=execution_result,
            contract_definition=contract.to_dict()
        )

    def run_all_tests(self) -> List[Dict[str, Any]]:
        """Execute all discovery tests and evaluate with oracles.

        Returns:
            List of test results with oracle evaluations
        """
        print("=" * 70)
        print("R5A-DISCOVERY: High-Yield ANN Test Execution on Milvus")
        print("=" * 70)
        print(f"\nTest cases: {len(self.test_cases)}")
        print(f"Real database: {self.is_real_database_run}")
        print(f"Timestamp: {datetime.now().isoformat()}")

        all_results = []

        for i, test in enumerate(self.test_cases, 1):
            print(f"\n{'=' * 70}")
            print(f"Test {i}/{len(self.test_cases)}: {test['test_id']}")
            print(f"Name: {test['name']}")
            print(f"Strategy: {test['discovery_strategy']}")
            print('=' * 70)

            # Execute test
            execution_result = self.execute_test(test)

            # Evaluate with oracle
            oracle_result = self.evaluate_oracle(execution_result)

            # Combine results
            test_result = {
                'test_id': test['test_id'],
                'contract_id': test['contract_id'],
                'name': test['name'],
                'discovery_strategy': test['discovery_strategy'],
                'bug_yield_potential': test['bug_yield_potential'],
                'dataset_type': test['dataset_type'],
                'dataset_description': test['dataset_description'],
                'execution': execution_result,
                'oracle': {
                    'classification': oracle_result.classification.value,
                    'passed': oracle_result.passed,
                    'reasoning': oracle_result.reasoning,
                    'evidence': oracle_result.evidence
                },
                'timestamp': datetime.now().isoformat()
            }

            all_results.append(test_result)

            # Print result
            status_icon = "[PASS]" if oracle_result.passed else "[FAIL]"
            classification = oracle_result.classification.value
            print(f"\n{status_icon} Oracle: {classification}")
            print(f"Reasoning: {oracle_result.reasoning}")

            # Flag interesting findings
            if classification == "VIOLATION":
                print(f"    [!!!] POTENTIAL BUG DISCOVERED")
            elif classification == "ALLOWED_DIFFERENCE":
                print(f"    [*] ALLOWED DIFFERENCE (implementation variance)")

        return all_results

    def save_results(self, results: List[Dict[str, Any]]) -> str:
        """Save test results to file.

        Args:
            results: Test results with oracle evaluations

        Returns:
            Path to saved results file
        """
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        output_dir = Path("results")
        output_dir.mkdir(exist_ok=True)

        filename = f"ann_discovery_{timestamp}.json"
        output_path = output_dir / filename

        summary = {
            'run_id': f"ann-discovery-{timestamp}",
            'timestamp': datetime.now().isoformat(),
            'total_tests': len(results),
            'is_real_database': self.is_real_database_run,
            'results': results,
            'summary': self._generate_summary(results)
        }

        with open(output_path, 'w') as f:
            json.dump(summary, f, indent=2)

        print(f"\n[Saved] Results: {output_path}")
        return str(output_path)

    def _generate_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary statistics from results.

        Args:
            results: Test results

        Returns:
            Summary statistics
        """
        summary = {
            'total': len(results),
            'by_classification': {},
            'by_contract': {},
            'by_strategy': {},
            'by_potential': {},
            'issue_candidates': [],
            'passed': 0,
            'failed': 0
        }

        for result in results:
            classification = result['oracle']['classification']
            summary['by_classification'][classification] = summary['by_classification'].get(classification, 0) + 1

            contract_id = result['contract_id']
            if contract_id not in summary['by_contract']:
                summary['by_contract'][contract_id] = {'passed': 0, 'failed': 0, 'total': 0}

            summary['by_contract'][contract_id]['total'] += 1

            strategy = result['discovery_strategy']
            if strategy not in summary['by_strategy']:
                summary['by_strategy'][strategy] = {}

            if classification not in summary['by_strategy'][strategy]:
                summary['by_strategy'][strategy][classification] = 0
            summary['by_strategy'][strategy][classification] += 1

            potential = result['bug_yield_potential']
            if potential not in summary['by_potential']:
                summary['by_potential'][potential] = {}

            if classification not in summary['by_potential'][potential]:
                summary['by_potential'][potential][classification] = 0
            summary['by_potential'][potential][classification] += 1

            if result['oracle']['passed']:
                summary['passed'] += 1
                summary['by_contract'][contract_id]['passed'] += 1
            else:
                summary['failed'] += 1
                summary['by_contract'][contract_id]['failed'] += 1

                # Track potential issues
                if classification == "VIOLATION":
                    summary['issue_candidates'].append({
                        'test_id': result['test_id'],
                        'contract_id': contract_id,
                        'strategy': strategy,
                        'classification': classification,
                        'reasoning': result['oracle']['reasoning']
                    })

        return summary


def main():
    """Main execution function."""
    # Find the most recent ANN discovery test file
    generated_tests_dir = Path("generated_tests")
    discovery_files = list(generated_tests_dir.glob("ann_discovery_*.json"))

    if not discovery_files:
        print("[ERROR] No ANN discovery test file found. Run discovery_generator first.")
        return

    # Use the most recent file
    test_file = max(discovery_files, key=lambda p: p.stat().st_mtime)
    print(f"[+] Using discovery test file: {test_file}")

    # Create executor
    executor = DiscoveryTestExecutor(
        test_file=str(test_file),
        is_real_database_run=True  # Use real Milvus
    )

    # Run all tests
    results = executor.run_all_tests()

    # Save results
    results_path = executor.save_results(results)

    # Print summary
    summary = executor._generate_summary(results)
    print("\n" + "=" * 70)
    print("ANN Discovery Execution Summary")
    print("=" * 70)
    print(f"\nTotal Tests: {summary['total']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")

    print(f"\nBy Classification:")
    for classification, count in summary['by_classification'].items():
        print(f"  {classification}: {count}")

    if summary['issue_candidates']:
        print(f"\n[!!!] POTENTIAL BUGS DISCOVERED: {len(summary['issue_candidates'])}")
        for issue in summary['issue_candidates']:
            print(f"  - {issue['test_id']}: {issue['reasoning']}")
    else:
        print(f"\n[INFO] No contract violations found")

    print(f"\nBy Strategy:")
    for strategy, classifications in summary['by_strategy'].items():
        print(f"  {strategy}:")
        for classification, count in classifications.items():
            print(f"    {classification}: {count}")

    print(f"\nBy Bug Yield Potential:")
    for potential, classifications in summary['by_potential'].items():
        print(f"  {potential}:")
        for classification, count in classifications.items():
            print(f"    {classification}: {count}")

    print(f"\nResults saved to: {results_path}")


if __name__ == "__main__":
    main()
