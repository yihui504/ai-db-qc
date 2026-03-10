"""Contract Test Generator for AI-DB-QC Framework.

This module generates test cases from contract definitions, expanding
parameter ranges and attaching oracle definitions.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from .contract_registry import Contract, get_registry


@dataclass
class TestCase:
    """A generated test case from a contract."""

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

    # Metadata
    priority: str = "medium"
    estimated_complexity: str = "medium"
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert test case to dictionary."""
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
            "tags": self.tags
        }


class ContractTestGenerator:
    """Generate test cases from contract definitions."""

    def __init__(self, output_dir: Optional[str] = None):
        """Initialize test generator.

        Args:
            output_dir: Directory for generated tests (default: generated_tests/)
        """
        if output_dir is None:
            project_root = Path(__file__).parent.parent
            output_dir = project_root / "generated_tests"

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        self.registry = get_registry()

    def generate_all(self) -> List[TestCase]:
        """Generate test cases for all loaded contracts.

        Returns:
            List of generated test cases
        """
        all_tests = []

        for contract in self.registry.get_all_contracts():
            tests = self.generate_for_contract(contract)
            all_tests.extend(tests)

        return all_tests

    def generate_for_contract(self, contract: Contract) -> List[TestCase]:
        """Generate test cases for a single contract.

        Args:
            contract: Contract to generate tests for

        Returns:
            List of generated test cases
        """
        strategy = contract.test_generation.get("strategy", "legal")

        if strategy == "boundary":
            return self._generate_boundary_tests(contract)
        elif strategy == "illegal":
            return self._generate_illegal_tests(contract)
        elif strategy == "sequence":
            return self._generate_sequence_tests(contract)
        elif strategy == "combinatorial":
            return self._generate_combinatorial_tests(contract)
        else:  # "legal" or default
            return self._generate_legal_tests(contract)

    def _generate_legal_tests(self, contract: Contract) -> List[TestCase]:
        """Generate legal input tests from contract.

        Args:
            contract: Contract specification

        Returns:
            List of test cases
        """
        tests = []
        cases = contract.test_generation.get("cases", [])

        for idx, case in enumerate(cases):
            test = TestCase(
                test_id=f"{contract.contract_id.lower()}_legal_{idx+1:03d}",
                contract_id=contract.contract_id,
                name=f"{contract.name} - Legal: {case.get('name', f'Case {idx+1}')}",
                description=f"Legal input test for {contract.name}",
                family=contract.family,
                strategy="legal",
                setup=self._generate_setup_from_case(case),
                steps=self._generate_steps_from_case(case),
                cleanup=self._generate_cleanup(),
                expected_outcome=case.get("expected", "success"),
                expected_result=case.get("verification"),
                oracle=contract.oracle,
                priority=self._get_priority(contract),
                estimated_complexity=contract.metadata.get("test_complexity", "medium"),
                tags=["legal", contract.family]
            )
            tests.append(test)

        return tests

    def _generate_boundary_tests(self, contract: Contract) -> List[TestCase]:
        """Generate boundary condition tests from contract.

        Args:
            contract: Contract specification

        Returns:
            List of test cases
        """
        tests = []
        cases = contract.test_generation.get("cases", [])

        for idx, case in enumerate(cases):
            test = TestCase(
                test_id=f"{contract.contract_id.lower()}_boundary_{idx+1:03d}",
                contract_id=contract.contract_id,
                name=f"{contract.name} - Boundary: {case.get('name', f'Case {idx+1}')}",
                description=f"Boundary condition test for {contract.name}",
                family=contract.family,
                strategy="boundary",
                setup=self._generate_setup_from_case(case),
                steps=self._generate_steps_from_case(case),
                cleanup=self._generate_cleanup(),
                expected_outcome=case.get("expected", "success"),
                expected_result=case.get("verification"),
                oracle=contract.oracle,
                priority="high",  # Boundary tests are high priority
                estimated_complexity="low",
                tags=["boundary", contract.family]
            )
            tests.append(test)

        return tests

    def _generate_illegal_tests(self, contract: Contract) -> List[TestCase]:
        """Generate illegal input tests from contract.

        Args:
            contract: Contract specification

        Returns:
            List of test cases
        """
        tests = []
        cases = contract.test_generation.get("cases", [])

        for idx, case in enumerate(cases):
            test = TestCase(
                test_id=f"{contract.contract_id.lower()}_illegal_{idx+1:03d}",
                contract_id=contract.contract_id,
                name=f"{contract.name} - Illegal: {case.get('name', f'Case {idx+1}')}",
                description=f"Illegal input test for {contract.name}",
                family=contract.family,
                strategy="illegal",
                setup=self._generate_setup_from_case(case),
                steps=self._generate_steps_from_case(case),
                cleanup=self._generate_cleanup(),
                expected_outcome=case.get("expected", "error"),
                expected_result=case.get("verification"),
                oracle=contract.oracle,
                priority="high",  # Illegal tests are high priority
                estimated_complexity="low",
                tags=["illegal", contract.family, "validation"]
            )
            tests.append(test)

        return tests

    def _generate_sequence_tests(self, contract: Contract) -> List[TestCase]:
        """Generate sequence tests from contract.

        Args:
            contract: Contract specification

        Returns:
            List of test cases
        """
        tests = []
        cases = contract.test_generation.get("cases", [])

        for idx, case in enumerate(cases):
            sequence = case.get("sequence", [])

            test = TestCase(
                test_id=f"{contract.contract_id.lower()}_seq_{idx+1:03d}",
                contract_id=contract.contract_id,
                name=f"{contract.name} - Sequence: {case.get('name', f'Case {idx+1}')}",
                description=f"Sequence test for {contract.name}",
                family=contract.family,
                strategy="sequence",
                setup=[],  # Setup is part of sequence
                steps=self._generate_steps_from_sequence(sequence),
                cleanup=self._generate_cleanup(),
                expected_outcome=case.get("expected", "success"),
                expected_result=case.get("verification"),
                oracle=contract.oracle,
                priority="medium",
                estimated_complexity=contract.metadata.get("test_complexity", "medium"),
                tags=["sequence", contract.family]
            )
            tests.append(test)

        return tests

    def _generate_combinatorial_tests(self, contract: Contract) -> List[TestCase]:
        """Generate combinatorial tests from contract.

        Args:
            contract: Contract specification

        Returns:
            List of test cases
        """
        tests = []
        cases = contract.test_generation.get("cases", [])

        for idx, case in enumerate(cases):
            test = TestCase(
                test_id=f"{contract.contract_id.lower()}_combo_{idx+1:03d}",
                contract_id=contract.contract_id,
                name=f"{contract.name} - Combinatorial: {case.get('name', f'Case {idx+1}')}",
                description=f"Combinatorial test for {contract.name}",
                family=contract.family,
                strategy="combinatorial",
                setup=self._generate_setup_from_case(case),
                steps=self._generate_steps_from_case(case),
                cleanup=self._generate_cleanup(),
                expected_outcome=case.get("expected", "success"),
                expected_result=case.get("verification"),
                oracle=contract.oracle,
                priority="medium",
                estimated_complexity="medium",
                tags=["combinatorial", contract.family]
            )
            tests.append(test)

        return tests

    def _generate_setup_from_case(self, case: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate setup steps from test case definition.

        Args:
            case: Test case definition

        Returns:
            List of setup operations
        """
        setup = case.get("setup", [])
        return [
            {"operation": step, "description": f"Setup: {step}"}
            for step in setup
        ]

    def _generate_steps_from_case(self, case: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate test steps from test case definition.

        Args:
            case: Test case definition

        Returns:
            List of test operations
        """
        params = case.get("params", {})

        # Generate steps based on contract family
        return [
            {
                "operation": "execute_test",
                "params": params,
                "description": f"Execute with params: {params}"
            }
        ]

    def _generate_steps_from_sequence(self, sequence: List[str]) -> List[Dict[str, Any]]:
        """Generate test steps from sequence definition.

        Args:
            sequence: List of operation descriptions

        Returns:
            List of test operations
        """
        steps = []

        for idx, step_desc in enumerate(sequence):
            steps.append({
                "step": idx + 1,
                "operation": step_desc,
                "description": f"Step {idx + 1}: {step_desc}"
            })

        return steps

    def _generate_cleanup(self) -> List[Dict[str, Any]]:
        """Generate cleanup steps.

        Returns:
            List of cleanup operations
        """
        return [
            {"operation": "cleanup_test_data", "description": "Cleanup test data"}
        ]

    def _get_priority(self, contract: Contract) -> str:
        """Get test priority from contract.

        Args:
            contract: Contract specification

        Returns:
            Priority level (high, medium, low)
        """
        severity = contract.violation_criteria.get("severity", "medium")

        if severity == "critical":
            return "high"
        elif severity == "high":
            return "high"
        elif severity == "medium":
            return "medium"
        else:
            return "low"

    def save_tests(self, tests: List[TestCase], suite_name: str) -> str:
        """Save generated tests to file.

        Args:
            tests: List of test cases
            suite_name: Name of the test suite

        Returns:
            Path to saved test file
        """
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"{suite_name}_{timestamp}.json"
        output_path = self.output_dir / filename

        test_data = {
            "suite_name": suite_name,
            "generated_at": datetime.now().isoformat(),
            "total_tests": len(tests),
            "contracts_covered": list(set(t.contract_id for t in tests)),
            "tests": [t.to_dict() for t in tests]
        }

        with open(output_path, 'w') as f:
            json.dump(test_data, f, indent=2)

        return str(output_path)

    def generate_by_family(self, family: str) -> List[TestCase]:
        """Generate tests for all contracts in a family.

        Args:
            family: Contract family name (ann, index, hybrid, schema)

        Returns:
            List of generated test cases
        """
        contracts = self.registry.get_contracts_by_family(family)
        tests = []

        for contract in contracts:
            contract_tests = self.generate_for_contract(contract)
            tests.extend(contract_tests)

        return tests

    def generate_by_type(self, contract_type: str) -> List[TestCase]:
        """Generate tests for all contracts of a type.

        Args:
            contract_type: Contract type (universal, database_specific)

        Returns:
            List of generated test cases
        """
        contracts = self.registry.get_contracts_by_type(contract_type)
        tests = []

        for contract in contracts:
            contract_tests = self.generate_for_contract(contract)
            tests.extend(contract_tests)

        return tests


if __name__ == "__main__":
    # Test contract test generator
    generator = ContractTestGenerator()

    print("Generating test cases from contracts...")
    all_tests = generator.generate_all()

    print(f"\nGenerated {len(all_tests)} test cases")

    # Save all tests
    output_path = generator.save_tests(all_tests, "all_contracts")
    print(f"Saved to: {output_path}")

    # Show summary by family
    registry = generator.registry
    stats = registry.get_statistics()

    print(f"\nTests by Family:")
    for family in stats["families"]:
        family_tests = generator.generate_by_family(family)
        print(f"  {family}: {len(family_tests)} tests")
