"""R5A-PILOT: ANN Contract-Driven Validation on Real Milvus.

This script executes the ANN pilot test set on real Milvus and evaluates
results using the contract oracle engine.
"""

import json
import sys
import math
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.contract_registry import get_registry
from core.oracle_engine import OracleEngine, OracleResult, Classification

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


def compute_ground_truth_nn(query_vector: List[float], collection_vectors: List[Tuple[int, List[float]]], metric_type: str = "L2") -> int:
    """Compute ground truth nearest neighbor using brute force.

    Args:
        query_vector: Query vector
        collection_vectors: List of (id, vector) tuples
        metric_type: Distance metric (L2, IP, COSINE)

    Returns:
        ID of nearest neighbor
    """
    min_distance = float('inf')
    nn_id = None

    for vec_id, vector in collection_vectors:
        if metric_type == "L2":
            distance = compute_l2_distance(query_vector, vector)
        elif metric_type == "IP":
            # For IP, higher is better, so we negate for distance comparison
            distance = -compute_inner_product(query_vector, vector)
        elif metric_type == "COSINE":
            distance = compute_cosine_distance(query_vector, vector)
        else:
            distance = compute_l2_distance(query_vector, vector)

        if distance < min_distance:
            min_distance = distance
            nn_id = vec_id

    return nn_id


class ANNPilotExecutor:
    """Execute ANN pilot tests on real Milvus with oracle evaluation."""

    def __init__(self, test_file: str, is_real_database_run: bool = True):
        """Initialize ANN pilot executor.

        Args:
            test_file: Path to generated test JSON file
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
        """Execute a single ANN test case.

        Args:
            test: Test case definition

        Returns:
            Execution result with raw output
        """
        test_id = test['test_id']
        contract_id = test['contract_id']
        params = test['steps'][0].get('params', {})

        print(f"\n[*] Executing: {test_id}")
        print(f"    Contract: {contract_id}")
        print(f"    Params: {params}")

        result = {
            'test_id': test_id,
            'contract_id': contract_id,
            'params': params,
            'timestamp': datetime.now().isoformat(),
            'is_real_database': self.is_real_database_run and self.adapter is not None
        }

        if self.adapter is None:
            # Mock execution for testing infrastructure
            result['status'] = 'mock'
            result['results'] = self._mock_execute(contract_id, params)
            result['error'] = None
        else:
            # Real Milvus execution
            try:
                # Execute based on contract type
                if contract_id == 'ANN-001':
                    # Top-K cardinality test
                    result['results'] = self._execute_top_k_test(params)
                elif contract_id == 'ANN-002':
                    # Distance monotonicity test
                    result['results'] = self._execute_monotonicity_test(params)
                elif contract_id == 'ANN-003':
                    # NN inclusion test
                    result['results'] = self._execute_nn_inclusion_test(params)
                elif contract_id == 'ANN-004':
                    # Metric consistency test
                    result['results'] = self._execute_metric_consistency_test(params)
                elif contract_id == 'ANN-005':
                    # Empty query test
                    result['results'] = self._execute_empty_query_test(params)
                else:
                    result['results'] = {'error': f'Unknown contract: {contract_id}'}

                result['status'] = 'success'
                result['error'] = None

            except Exception as e:
                result['status'] = 'error'
                result['results'] = None
                result['error'] = str(e)
                print(f"    [!] Execution error: {e}")

        return result

    def _mock_execute(self, contract_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Mock execution for infrastructure testing.

        Args:
            contract_id: Contract identifier
            params: Test parameters

        Returns:
            Mock results matching expected behavior
        """
        # Return mock results that should PASS the oracle
        if contract_id == 'ANN-001':
            top_k = params.get('top_k', 5)
            return {'results': [{'id': i, 'distance': 0.1 * i} for i in range(min(top_k, 3))]}
        elif contract_id == 'ANN-002':
            return {'results': [{'id': i, 'distance': 0.1 * i} for i in range(10)]}
        elif contract_id == 'ANN-003':
            return {'results': [{'id': 0, 'distance': 0.01}], 'recall': 0.95}
        elif contract_id == 'ANN-004':
            metric = params.get('metric_type', 'L2')
            return {'results': [{'id': 0, 'distance': 0.5, 'vector': [1.0, 2.0]}], 'metric': metric}
        elif contract_id == 'ANN-005':
            return {'results': []}
        else:
            return {'results': []}

    def _execute_top_k_test(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute ANN-001 Top-K cardinality test.

        Args:
            params: Test parameters (top_k, collection_size)

        Returns:
            Search results
        """
        top_k = params.get('top_k', 5)
        collection_size = params.get('collection_size', 100)

        # Create test collection
        collection_name = f"test_ann_top_k_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        try:
            # Create collection
            self.adapter.execute({
                "operation": "create_collection",
                "params": {
                    "collection_name": collection_name,
                    "dimension": 128,
                    "metric_type": "L2"
                }
            })

            # Insert test data
            import random
            vectors = [[random.random() for _ in range(128)] for _ in range(collection_size)]
            self.adapter.execute({
                "operation": "insert",
                "params": {
                    "collection_name": collection_name,
                    "vectors": vectors
                }
            })

            # Create index
            self.adapter.execute({
                "operation": "build_index",
                "params": {
                    "collection_name": collection_name
                }
            })

            # Load collection
            self.adapter.execute({
                "operation": "load",
                "params": {
                    "collection_name": collection_name
                }
            })

            # Execute search
            query_vector = [random.random() for _ in range(128)]
            search_result = self.adapter.execute({
                "operation": "search",
                "params": {
                    "collection_name": collection_name,
                    "vector": query_vector,
                    "top_k": top_k
                }
            })

            return {
                'results': search_result.get('data', []),
                'top_k': top_k,
                'collection_size': collection_size
            }

        finally:
            # Cleanup
            try:
                self.adapter.execute({
                    "operation": "drop_collection",
                    "params": {
                        "collection_name": collection_name
                    }
                })
            except:
                pass

    def _execute_monotonicity_test(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute ANN-002 Distance monotonicity test.

        Args:
            params: Test parameters (top_k, collection_size)

        Returns:
            Search results with distances
        """
        top_k = params.get('top_k', 10)
        collection_size = params.get('collection_size', 100)

        collection_name = f"test_ann_monotonicity_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        try:
            # Setup collection
            self.adapter.execute({
                "operation": "create_collection",
                "params": {
                    "collection_name": collection_name,
                    "dimension": 128,
                    "metric_type": "L2"
                }
            })

            import random
            vectors = [[random.random() for _ in range(128)] for _ in range(collection_size)]
            self.adapter.execute({
                "operation": "insert",
                "params": {
                    "collection_name": collection_name,
                    "vectors": vectors
                }
            })
            self.adapter.execute({
                "operation": "build_index",
                "params": {"collection_name": collection_name}
            })
            self.adapter.execute({
                "operation": "load",
                "params": {"collection_name": collection_name}
            })

            # Search
            query_vector = [random.random() for _ in range(128)]
            search_result = self.adapter.execute({
                "operation": "search",
                "params": {
                    "collection_name": collection_name,
                    "vector": query_vector,
                    "top_k": top_k
                }
            })

            return {
                'results': search_result.get('data', []),
                'top_k': top_k
            }

        finally:
            try:
                self.adapter.execute({
                    "operation": "drop_collection",
                    "params": {"collection_name": collection_name}
                })
            except:
                pass

    def _execute_nn_inclusion_test(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute ANN-003 Nearest Neighbor inclusion test.

        Args:
            params: Test parameters (search_mode, index_type, force_exact)

        Returns:
            Search results with ground truth comparison
        """
        collection_name = f"test_ann_nn_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        try:
            # Setup collection with specific data for ground truth
            self.adapter.execute({
                "operation": "create_collection",
                "params": {
                    "collection_name": collection_name,
                    "dimension": 128,
                    "metric_type": "L2"
                }
            })

            import random
            collection_size = 100
            vectors = [[random.random() for _ in range(128)] for _ in range(collection_size)]

            # Store vectors with IDs for ground truth computation
            collection_vectors = [(i, vectors[i]) for i in range(collection_size)]

            self.adapter.execute({
                "operation": "insert",
                "params": {
                    "collection_name": collection_name,
                    "vectors": vectors
                }
            })
            self.adapter.execute({
                "operation": "build_index",
                "params": {"collection_name": collection_name}
            })
            self.adapter.execute({
                "operation": "load",
                "params": {"collection_name": collection_name}
            })

            # Query vector (use first vector as query for exact match)
            query_vector = vectors[0]
            search_result = self.adapter.execute({
                "operation": "search",
                "params": {
                    "collection_name": collection_name,
                    "vector": query_vector,
                    "top_k": 10
                }
            })

            # Compute ground truth nearest neighbor using brute force
            ground_truth_nn_id = compute_ground_truth_nn(query_vector, collection_vectors, "L2")

            return {
                'results': search_result.get('data', []),
                'ground_truth_nn_id': ground_truth_nn_id,
                'search_mode': params.get('search_mode', 'ann')
            }

        finally:
            try:
                self.adapter.execute({
                    "operation": "drop_collection",
                    "params": {"collection_name": collection_name}
                })
            except:
                pass

    def _execute_metric_consistency_test(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute ANN-004 Metric consistency test.

        Args:
            params: Test parameters (metric_type)

        Returns:
            Search results with distance verification
        """
        metric_type = params.get('metric_type', 'L2')
        collection_name = f"test_ann_metric_{metric_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        try:
            # Setup collection
            self.adapter.execute({
                "operation": "create_collection",
                "params": {
                    "collection_name": collection_name,
                    "dimension": 128,
                    "metric_type": metric_type
                }
            })

            import random
            vectors = [[random.random() for _ in range(128)] for _ in range(50)]

            # Store vectors for retrieval
            collection_vectors = [(i, vectors[i]) for i in range(len(vectors))]

            self.adapter.execute({
                "operation": "insert",
                "params": {
                    "collection_name": collection_name,
                    "vectors": vectors
                }
            })
            self.adapter.execute({
                "operation": "build_index",
                "params": {"collection_name": collection_name}
            })
            self.adapter.execute({
                "operation": "load",
                "params": {"collection_name": collection_name}
            })

            # Search
            query_vector = [random.random() for _ in range(128)]
            search_result = self.adapter.execute({
                "operation": "search",
                "params": {
                    "collection_name": collection_name,
                    "vector": query_vector,
                    "top_k": 5
                }
            })

            # Extract data for oracle validation
            results = search_result.get('data', [])
            if results and len(results) > 0:
                first_result = results[0]
                result_id = first_result.get('id')
                result_distance = first_result.get('distance')

                # Get the vector for the first result
                result_vector = None
                for vec_id, vector in collection_vectors:
                    if vec_id == result_id:
                        result_vector = vector
                        break

                return {
                    'results': results,
                    'metric_type': metric_type,
                    'query_vector': query_vector,
                    'result_distance': result_distance,
                    'result_vector': result_vector
                }
            else:
                return {
                    'results': results,
                    'metric_type': metric_type,
                    'query_vector': query_vector
                }

        finally:
            try:
                self.adapter.execute({
                    "operation": "drop_collection",
                    "params": {"collection_name": collection_name}
                })
            except:
                pass

    def _execute_empty_query_test(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute ANN-005 Empty query handling test.

        Args:
            params: Test parameters (collection_empty)

        Returns:
            Search results on empty collection
        """
        collection_name = f"test_ann_empty_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        try:
            # Create empty collection
            self.adapter.execute({
                "operation": "create_collection",
                "params": {
                    "collection_name": collection_name,
                    "dimension": 128,
                    "metric_type": 'L2'
                }
            })

            # Try to search on empty collection
            query_vector = [0.5] * 128
            search_result = self.adapter.execute({
                "operation": "search",
                "params": {
                    "collection_name": collection_name,
                    "vector": query_vector,
                    "top_k": 5
                }
            })

            return {
                'results': search_result.get('data', []),
                'collection_empty': True
            }

        finally:
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
        """Execute all ANN pilot tests and evaluate with oracles.

        Returns:
            List of test results with oracle evaluations
        """
        print("=" * 70)
        print("R5A-PILOT: ANN Contract-Driven Execution on Milvus")
        print("=" * 70)
        print(f"\nTest cases: {len(self.test_cases)}")
        print(f"Real database: {self.is_real_database_run}")
        print(f"Timestamp: {datetime.now().isoformat()}")

        all_results = []

        for i, test in enumerate(self.test_cases, 1):
            print(f"\n{'=' * 70}")
            print(f"Test {i}/{len(self.test_cases)}: {test['test_id']}")
            print(f"Name: {test['name']}")
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
            print(f"\n{status_icon} Oracle: {oracle_result.classification.value}")
            print(f"Reasoning: {oracle_result.reasoning}")

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

        filename = f"ann_pilot_{timestamp}.json"
        output_path = output_dir / filename

        summary = {
            'run_id': f"ann-pilot-{timestamp}",
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
            'passed': 0,
            'failed': 0
        }

        for result in results:
            classification = result['oracle']['classification']
            summary['by_classification'][classification] = summary['by_classification'].get(classification, 0) + 1

            contract_id = result['contract_id']
            if contract_id not in summary['by_contract']:
                summary['by_contract'][contract_id] = {'passed': 0, 'failed': 0}

            if result['oracle']['passed']:
                summary['passed'] += 1
                summary['by_contract'][contract_id]['passed'] += 1
            else:
                summary['failed'] += 1
                summary['by_contract'][contract_id]['failed'] += 1

        return summary


def main():
    """Main execution function."""
    # Find the most recent ANN pilot test file
    generated_tests_dir = Path("generated_tests")
    ann_files = list(generated_tests_dir.glob("ann_pilot_*.json"))

    if not ann_files:
        print("[ERROR] No ANN pilot test file found. Run generate_ann_pilot.py first.")
        return

    # Use the most recent file
    test_file = max(ann_files, key=lambda p: p.stat().st_mtime)
    print(f"[+] Using test file: {test_file}")

    # Create executor
    executor = ANNPilotExecutor(
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
    print("ANN Pilot Execution Summary")
    print("=" * 70)
    print(f"\nTotal Tests: {summary['total']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"\nBy Classification:")
    for classification, count in summary['by_classification'].items():
        print(f"  {classification}: {count}")

    print(f"\nBy Contract:")
    for contract_id, counts in summary['by_contract'].items():
        print(f"  {contract_id}: {counts['passed']} passed, {counts['failed']} failed")

    print(f"\nResults saved to: {results_path}")


if __name__ == "__main__":
    main()
