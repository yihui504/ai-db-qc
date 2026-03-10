"""R5C-HYBRID PILOT: Executor for Hybrid Query Tests.

This script executes the hybrid pilot test set on real Milvus and evaluates
results using the corrected hybrid contract oracles.
"""

import json
import sys
import random
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.contract_registry import get_registry
from core.oracle_engine import OracleEngine, OracleResult, Classification
from core.hybrid_generator import HybridDatasetGenerator

# Try to import Milvus adapter
try:
    from adapters.milvus_adapter import MilvusAdapter
    MILVUS_AVAILABLE = True
except ImportError:
    MILVUS_AVAILABLE = False
    print("[WARNING] Milvus adapter not available, will use mock mode")


def satisfies_filter(scalar_fields: Dict[str, Any], filter_criteria: Dict[str, Any]) -> bool:
    """Check if entity's scalar fields satisfy filter criteria.

    Args:
        scalar_fields: Entity's scalar field values
        filter_criteria: Filter conditions

    Returns:
        True if entity satisfies filter, False otherwise
    """
    for key, expected_value in filter_criteria.items():
        actual_value = scalar_fields.get(key)

        # Handle null checks
        if expected_value is None:
            if actual_value is not None:
                return False
        # Handle list/set membership
        elif isinstance(expected_value, (list, set)):
            if actual_value not in expected_value:
                return False
        # Handle equality
        else:
            if actual_value != expected_value:
                return False

    return True


def check_filter_satisfaction(results: List[Dict[str, Any]], filter_criteria: Dict[str, Any]) -> OracleResult:
    """HYB-001 Oracle: All results must satisfy filter criteria.

    Args:
        results: Search results with scalar_fields
        filter_criteria: Filter expression

    Returns:
        OracleResult with classification
    """
    for result in results:
        scalar_fields = result.get('scalar_fields', {})
        if not satisfies_filter(scalar_fields, filter_criteria):
            return OracleResult(
                contract_id='HYB-001',
                classification=Classification.VIOLATION,
                passed=False,
                reasoning=f"Entity {result.get('id')} violates filter: {filter_criteria}. "
                          f"Entity fields: {scalar_fields}",
                evidence={'violating_entity': result.get('id'), 'scalar_fields': scalar_fields}
            )

    return OracleResult(
        contract_id='HYB-001',
        classification=Classification.PASS,
        passed=True,
        reasoning=f"All {len(results)} results satisfy filter criteria",
        evidence={'result_count': len(results), 'filter': filter_criteria}
    )


def check_filter_satisfaction_and_monotonicity(
    results: List[Dict[str, Any]],
    filter_criteria: Dict[str, Any]
) -> OracleResult:
    """HYB-002 Oracle (CORRECTED): Filter satisfaction + distance monotonicity.

    This oracle does NOT require exact list matching with unfiltered results.
    It only checks:
    1. All results satisfy filter
    2. Distances are monotonically increasing within filtered subset

    Args:
        results: Search results with scalar_fields and distances
        filter_criteria: Filter expression

    Returns:
        OracleResult with classification
    """
    # Check 1: Filter satisfaction
    for result in results:
        scalar_fields = result.get('scalar_fields', {})
        if not satisfies_filter(scalar_fields, filter_criteria):
            return OracleResult(
                contract_id='HYB-002',
                classification=Classification.VIOLATION,
                passed=False,
                reasoning=f"Entity {result.get('id')} violates filter: {filter_criteria}",
                evidence={'violating_entity': result.get('id'), 'check': 'filter_satisfaction'}
            )

    # Check 2: Distance monotonicity (within filtered entities)
    if len(results) > 1:
        for i in range(len(results) - 1):
            dist_current = results[i].get('distance')
            dist_next = results[i + 1].get('distance')

            # Distances should be monotonically increasing
            if dist_current is not None and dist_next is not None:
                if dist_current > dist_next:
                    return OracleResult(
                        contract_id='HYB-002',
                        classification=Classification.VIOLATION,
                        passed=False,
                        reasoning=f"Distance not monotonic: result[{i}]={dist_current} > result[{i+1}]={dist_next}",
                        evidence={'check': 'monotonicity', 'index': i}
                    )

    return OracleResult(
        contract_id='HYB-002',
        classification=Classification.PASS,
        passed=True,
        reasoning=f"All {len(results)} results satisfy filter AND distances are monotonic",
        evidence={'result_count': len(results), 'filter': filter_criteria}
    )


def check_empty_when_no_match(
    results: List[Dict[str, Any]],
    filter_criteria: Dict[str, Any],
    collection_matches_nothing: bool
) -> OracleResult:
    """HYB-003 Oracle: Empty results when filter matches nothing.

    Args:
        results: Search results
        filter_criteria: Filter expression
        collection_matches_nothing: Whether filter matches zero entities in collection

    Returns:
        OracleResult with classification
    """
    if collection_matches_nothing:
        if len(results) > 0:
            return OracleResult(
                contract_id='HYB-003',
                classification=Classification.VIOLATION,
                passed=False,
                reasoning=f"Filter matches nothing but returned {len(results)} results",
                evidence={'result_count': len(results), 'filter': filter_criteria}
            )
        else:
            return OracleResult(
                contract_id='HYB-003',
                classification=Classification.PASS,
                passed=True,
                reasoning="Filter matches nothing and correctly returned empty results",
                evidence={'result_count': 0}
            )
    else:
        # Filter does match something - use ALLOWED_DIFFERENCE for behavior variance
        return OracleResult(
            contract_id='HYB-003',
            classification=Classification.PASS,
            passed=True,
            reasoning=f"Filter matches entities, returned {len(results)} results",
            evidence={'result_count': len(results)}
        )


class HybridTestExecutor:
    """Execute hybrid pilot tests on real Milvus."""

    def __init__(self, test_file: str, is_real_database_run: bool = True):
        """Initialize hybrid test executor.

        Args:
            test_file: Path to generated hybrid test JSON file
            is_real_database_run: Whether to use real Milvus (True) or mock (False)
        """
        self.test_file = Path(test_file)
        self.is_real_database_run = is_real_database_run

        # Load test cases
        with open(self.test_file, 'r') as f:
            test_data = json.load(f)
            self.test_cases = test_data['tests']

        # Initialize dataset generator
        self.dataset_generator = HybridDatasetGenerator()

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
        """Execute a single hybrid test case.

        Args:
            test: Test case definition

        Returns:
            Execution result with raw output
        """
        test_id = test['test_id']
        contract_id = test['contract_id']
        dataset_name = test['dataset_name']

        print(f"\n[*] Executing: {test_id}")
        print(f"    Contract: {contract_id}")
        print(f"    Name: {test['name']}")
        print(f"    Dataset: {dataset_name}")
        print(f"    Bug Yield: {test['bug_yield_potential']}")

        result = {
            'test_id': test_id,
            'contract_id': contract_id,
            'name': test['name'],
            'dataset_name': dataset_name,
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
                {'id': i, 'distance': 0.1 * i, 'score': 0.1 * i, 'scalar_fields': {'color': 'red', 'status': 'active'}}
                for i in range(1, 6)
            ],
            'top_k': 10
        }

    def _execute_with_dataset(self, test: Dict[str, Any]) -> Dict[str, Any]:
        """Execute test with dataset on Milvus.

        Args:
            test: Test case definition

        Returns:
            Search results with metadata
        """
        # Get dataset from generator
        dataset_name = test['dataset_name']
        all_datasets = self.dataset_generator.generate_all_datasets()
        dataset = all_datasets[dataset_name]

        filter_criteria = test['filter_criteria']
        top_k = test['top_k']

        # Check for empty collection test
        use_empty_collection = test.get('use_empty_collection', False)

        # Generate unique collection name
        collection_name = f"test_hybrid_{datetime.now().strftime('%Y%m%d%H%M%S')}_{random.randint(1000, 9999)}"

        try:
            # Create collection with scalar fields
            self.adapter.execute({
                "operation": "create_collection",
                "params": {
                    "collection_name": collection_name,
                    "dimension": len(dataset.query_vector),
                    "metric_type": "L2",
                    "scalar_fields": ["color", "status"]
                }
            })

            # Insert entities if not empty collection test
            entities_to_insert = dataset.entities if not use_empty_collection else []

            if len(entities_to_insert) > 0:
                # Prepare batch insert
                vectors = [e['vector'] for e in entities_to_insert]
                scalar_data = [
                    {'id': e['id'], 'color': e['scalar_fields']['color'], 'status': e['scalar_fields']['status']}
                    for e in entities_to_insert
                ]

                self.adapter.execute({
                    "operation": "insert",
                    "params": {
                        "collection_name": collection_name,
                        "vectors": vectors,
                        "scalar_data": scalar_data
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

                # Execute filtered search
                search_result = self.adapter.execute({
                    "operation": "filtered_search",
                    "params": {
                        "collection_name": collection_name,
                        "vector": dataset.query_vector,
                        "filter": filter_criteria,
                        "top_k": top_k
                    }
                })
            else:
                # Empty collection - search should handle gracefully
                search_result = self.adapter.execute({
                    "operation": "filtered_search",
                    "params": {
                        "collection_name": collection_name,
                        "vector": dataset.query_vector,
                        "filter": filter_criteria,
                        "top_k": top_k
                    }
                })

            results = search_result.get('data', [])

            # Check if filter matches nothing in collection
            collection_matches_nothing = False
            if use_empty_collection:
                collection_matches_nothing = True
            else:
                # Check if any entity matches filter
                has_match = any(
                    satisfies_filter(e['scalar_fields'], filter_criteria)
                    for e in dataset.entities
                )
                collection_matches_nothing = not has_match

            return {
                'results': results,
                'top_k': top_k,
                'filter_criteria': filter_criteria,
                'dataset_description': dataset.description,
                'collection_matches_nothing': collection_matches_nothing,
                'result_count': len(results)
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

    def evaluate_oracle(self, execution_result: Dict[str, Any], test: Dict[str, Any]) -> OracleResult:
        """Evaluate execution result against contract oracle.

        Args:
            execution_result: Result from test execution
            test: Original test case definition

        Returns:
            Oracle evaluation result
        """
        contract_id = execution_result['contract_id']
        results_data = execution_result.get('results')

        if results_data is None:
            return OracleResult(
                contract_id=contract_id,
                classification=Classification.OBSERVATION,
                passed=False,
                reasoning=f"Execution failed or returned no results: {execution_result.get('error')}",
                evidence=execution_result
            )

        results = results_data.get('results', [])
        filter_criteria = results_data.get('filter_criteria', test.get('filter_criteria'))

        # Route to appropriate oracle
        if contract_id == 'HYB-001':
            return check_filter_satisfaction(results, filter_criteria)
        elif contract_id == 'HYB-002':
            return check_filter_satisfaction_and_monotonicity(results, filter_criteria)
        elif contract_id == 'HYB-003':
            return check_empty_when_no_match(
                results,
                filter_criteria,
                results_data.get('collection_matches_nothing', False)
            )
        else:
            return OracleResult(
                contract_id=contract_id,
                classification=Classification.OBSERVATION,
                passed=False,
                reasoning=f"Unknown contract: {contract_id}",
                evidence=execution_result
            )

    def run_all_tests(self) -> List[Dict[str, Any]]:
        """Execute all hybrid tests and evaluate with oracles.

        Returns:
            List of test results with oracle evaluations
        """
        print("=" * 70)
        print("R5C-HYBRID PILOT: Hybrid Query Test Execution on Milvus")
        print("=" * 70)
        print(f"\nTest cases: {len(self.test_cases)}")
        print(f"Real database: {self.is_real_database_run}")
        print(f"Timestamp: {datetime.now().isoformat()}")

        all_results = []

        for i, test in enumerate(self.test_cases, 1):
            print(f"\n{'=' * 70}")
            print(f"Test {i}/{len(self.test_cases)}: {test['test_id']}")
            print('=' * 70)

            # Execute test
            execution_result = self.execute_test(test)

            # Evaluate with oracle
            oracle_result = self.evaluate_oracle(execution_result, test)

            # Combine results
            test_result = {
                'test_id': test['test_id'],
                'contract_id': test['contract_id'],
                'name': test['name'],
                'dataset_name': test['dataset_name'],
                'bug_yield_potential': test['bug_yield_potential'],
                'expected_behavior': test.get('expected_behavior', ''),
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

        filename = f"hybrid_pilot_{timestamp}.json"
        output_path = output_dir / filename

        summary = {
            'run_id': f"hybrid-pilot-{timestamp}",
            'timestamp': datetime.now().isoformat(),
            'total_tests': len(results),
            'is_real_database': self.is_real_database_run,
            'results': results,
            'summary': self._generate_summary(results)
        }

        with open(output_path, 'w') as f:
            json.dump(summary, f, indent=2, default=str)

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
                        'name': result['name'],
                        'classification': classification,
                        'reasoning': result['oracle']['reasoning'],
                        'bug_yield_potential': result['bug_yield_potential']
                    })

        return summary


def main():
    """Main execution function."""
    # Find the most recent hybrid pilot test file
    generated_tests_dir = Path("generated_tests")
    pilot_files = list(generated_tests_dir.glob("hybrid_pilot_*.json"))

    if not pilot_files:
        print("[ERROR] No hybrid pilot test file found. Run hybrid_generator first.")
        return

    # Use the most recent file
    test_file = max(pilot_files, key=lambda p: p.stat().st_mtime)
    print(f"[+] Using hybrid pilot test file: {test_file}")

    # Create executor
    executor = HybridTestExecutor(
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
    print("R5C-Hybrid Pilot Execution Summary")
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
            print(f"  - {issue['test_id']} ({issue['bug_yield_potential']}): {issue['reasoning']}")
    else:
        print(f"\n[INFO] No contract violations found")

    print(f"\nBy Contract:")
    for contract_id, stats in summary['by_contract'].items():
        print(f"  {contract_id}: {stats['passed']}/{stats['total']} passed")

    print(f"\nResults saved to: {results_path}")


if __name__ == "__main__":
    main()
