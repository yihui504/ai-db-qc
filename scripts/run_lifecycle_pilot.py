"""R5B Index Lifecycle Pilot Executor.

Executes index lifecycle state transition tests on Milvus and evaluates
results using lifecycle contract oracles.
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

from core.oracle_engine import OracleEngine, OracleResult, Classification

# Try to import Milvus adapter
try:
    from adapters.milvus_adapter import MilvusAdapter
    MILVUS_AVAILABLE = True
except ImportError:
    MILVUS_AVAILABLE = False
    print("[WARNING] Milvus adapter not available, will use mock mode")


class LifecyclePilotExecutor:
    """Execute R5B lifecycle pilot tests on Milvus."""

    def __init__(self, test_file: str, is_real_database_run: bool = True):
        """Initialize lifecycle pilot executor.

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

        # Initialize oracle engine
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
        """Execute a single lifecycle test case.

        Args:
            test: Test case definition

        Returns:
            Execution result with step-by-step outcomes
        """
        test_id = test['test_id']
        contract_id = test['contract_id']
        sequence = test.get('sequence', [])

        print(f"\n[*] Executing: {test_id}")
        print(f"    Contract: {contract_id}")
        print(f"    Name: {test['name']}")
        print(f"    State: {test.get('initial_state', '?')} -> {test.get('target_state', '?')}")

        result = {
            'test_id': test_id,
            'contract_id': contract_id,
            'name': test['name'],
            'initial_state': test.get('initial_state', ''),
            'target_state': test.get('target_state', ''),
            'timestamp': datetime.now().isoformat(),
            'is_real_database': self.is_real_database_run and self.adapter is not None,
            'steps': []
        }

        # Collection name for cleanup
        collection_name = None

        if self.adapter is None:
            # Mock execution
            result['status'] = 'mock'
            result['steps'] = self._mock_execute_sequence(test)
            result['error'] = None
        else:
            # Real Milvus execution
            try:
                step_results = self._execute_sequence(test, sequence)
                result['steps'] = step_results
                result['status'] = 'success'
                result['error'] = None

                # Get collection name for cleanup
                if step_results:
                    collection_name = step_results[0].get('collection_name')

            except Exception as e:
                result['status'] = 'error'
                result['steps'] = []
                result['error'] = str(e)
                print(f"    [!] Execution error: {e}")

        # Cleanup
        if collection_name and self.adapter:
            try:
                self.adapter.execute({
                    "operation": "drop_collection",
                    "params": {"collection_name": collection_name}
                })
            except:
                pass

        return result

    def _execute_sequence(
        self,
        test: Dict[str, Any],
        sequence: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Execute a sequence of operations.

        Args:
            test: Test case definition
            sequence: List of operation steps

        Returns:
            List of step results
        """
        step_results = []

        # Get substitutions
        substitutions = test.get('substitutions', {})

        for step in sequence:
            operation = step.get('operation')
            param_template = step.get('param_template', {})
            store_as = step.get('store_as')

            # Apply substitutions
            params = self._apply_substitutions(param_template, substitutions)

            # Execute operation
            try:
                op_result = self.adapter.execute({
                    "operation": operation,
                    "params": params
                })

                step_result = {
                    "step": step.get('step'),
                    "operation": operation,
                    "params": params,
                    "result": op_result,
                    "status": op_result.get("status", "unknown")
                }

                # Store result label if specified
                if store_as:
                    step_result["store_as"] = store_as

            except Exception as e:
                step_result = {
                    "step": step.get('step'),
                    "operation": operation,
                    "params": params,
                    "result": {"error": str(e)},
                    "status": "error"
                }

            step_results.append(step_result)

            # Store results for oracle evaluation
            if 'result' not in step_result:
                result = {}
            else:
                result = step_result

        return step_results

    def _apply_substitutions(
        self,
        param_template: Dict[str, Any],
        substitutions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply substitutions to parameter template.

        Args:
            param_template: Parameter template with placeholders
            substitutions: Substitution values

        Returns:
            Parameters with substitutions applied
        """
        import copy
        params = copy.deepcopy(param_template)

        for key, value in params.items():
            if isinstance(value, str) and value.startswith("{") and value.endswith("}"):
                placeholder = value[1:-1]
                if placeholder in substitutions:
                    params[key] = substitutions[placeholder]

        return params

    def _mock_execute_sequence(
        self,
        test: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Mock execution for infrastructure testing.

        Args:
            test: Test case definition

        Returns:
            List of mock step results
        """
        sequence = test.get('sequence', [])
        step_results = []

        for step in sequence:
            operation = step.get('operation')
            store_as = step.get('store_as')

            # Mock results based on operation
            if operation == "get_load_state":
                mock_result = {
                    "load_state": "NotLoad",
                    "index_metadata_exists": operation in ["build_index", "load"],
                    "data": [{"load_state": "NotLoad"}]
                }
            elif operation == "search":
                mock_result = {
                    "data": [{"id": i, "distance": 0.1 * i} for i in range(5)],
                    "status": "success"
                }
            elif operation == "count_entities":
                mock_result = {
                    "storage_count": 100,
                    "load_state": "Loaded",
                    "status": "success"
                }
            else:
                mock_result = {"status": "success", "data": []}

            step_result = {
                "step": step.get('step'),
                "operation": operation,
                "result": mock_result,
                "status": "mock"
            }

            # Store result label if specified
            if store_as:
                step_result["store_as"] = store_as

            step_results.append(step_result)

        return step_results

    def evaluate_oracle(
        self,
        execution_result: Dict[str, Any],
        test: Dict[str, Any]
    ) -> OracleResult:
        """Evaluate execution result against lifecycle contract oracle.

        Args:
            execution_result: Result from test execution
            test: Original test case definition

        Returns:
            Oracle evaluation result
        """
        contract_id = execution_result['contract_id']

        # Extract step results into oracle-friendly format
        steps = execution_result.get('steps', [])
        oracle_data = {}

        for step in steps:
            store_as = step.get('store_as')
            result = step.get('result', {})

            if store_as:
                oracle_data[store_as] = result

        # Evaluate using oracle engine
        return self.oracle_engine.evaluate(
            contract_id=contract_id,
            execution_result=oracle_data,
            contract_definition=None
        )

    def run_all_tests(self) -> List[Dict[str, Any]]:
        """Execute all lifecycle tests and evaluate with oracles.

        Returns:
            List of test results with oracle evaluations
        """
        print("=" * 70)
        print("R5B Index Lifecycle Pilot Execution")
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
                'initial_state': test.get('initial_state', ''),
                'target_state': test.get('target_state', ''),
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

        filename = f"r5b_lifecycle_{timestamp}.json"
        output_path = output_dir / filename

        summary = {
            'run_id': f"r5b-lifecycle-{timestamp}",
            'timestamp': datetime.now().isoformat(),
            'total_tests': len(results),
            'is_real_database': self.is_real_database_run,
            'campaign': 'R5B_INDEX_LIFECYCLE',
            'version': '2.1',
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
            'by_state_transition': {},
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

            # Track state transitions
            transition = f"{result.get('initial_state', '?')} -> {result.get('target_state', '?')}"
            if transition not in summary['by_state_transition']:
                summary['by_state_transition'][transition] = {'passed': 0, 'failed': 0, 'total': 0}
            summary['by_state_transition'][transition]['total'] += 1

            if result['oracle']['passed']:
                summary['passed'] += 1
                summary['by_contract'][contract_id]['passed'] += 1
                summary['by_state_transition'][transition]['passed'] += 1
            else:
                summary['failed'] += 1
                summary['by_contract'][contract_id]['failed'] += 1
                summary['by_state_transition'][transition]['failed'] += 1

        return summary


def main():
    """Main execution function."""
    # Find the most recent R5B lifecycle test file
    generated_tests_dir = Path("generated_tests")
    pilot_files = list(generated_tests_dir.glob("r5b_lifecycle_*.json"))

    if not pilot_files:
        print("[ERROR] No R5B lifecycle test file found. Run generate_r5b_tests.py first.")
        return 1

    # Use the most recent file
    test_file = max(pilot_files, key=lambda p: p.stat().st_mtime)
    print(f"[+] Using R5B lifecycle test file: {test_file}")

    # Create executor
    executor = LifecyclePilotExecutor(
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
    print("R5B Lifecycle Pilot Execution Summary")
    print("=" * 70)
    print(f"\nTotal Tests: {summary['total']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")

    print(f"\nBy Classification:")
    for classification, count in summary['by_classification'].items():
        print(f"  {classification}: {count}")

    print(f"\nBy State Transition:")
    for transition, stats in summary['by_state_transition'].items():
        print(f"  {transition}: {stats['passed']}/{stats['total']} passed")

    print(f"\nBy Contract:")
    for contract_id, stats in summary['by_contract'].items():
        print(f"  {contract_id}: {stats['passed']}/{stats['total']} passed")

    print(f"\nResults saved to: {results_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
