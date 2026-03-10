"""Generate ANN pilot test set for contract-driven validation."""

from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.contract_registry import get_registry
from core.contract_test_generator import ContractTestGenerator

def main():
    print("=" * 70)
    print("R5A-PILOT: ANN Contract-Driven Test Generation")
    print("=" * 70)

    # Initialize registry and generator
    registry = get_registry()
    generator = ContractTestGenerator()

    # Get ANN contracts
    ann_contracts = registry.get_contracts_by_family("ANN")

    print(f"\n[*] ANN Contracts Found: {len(ann_contracts)}")
    print("-" * 70)

    for contract in ann_contracts:
        print(f"\n{contract.contract_id}: {contract.name}")
        print(f"  Strategy: {contract.test_generation.get('strategy', 'legal')}")
        print(f"  Oracle: {contract.oracle.get('check', 'N/A')}")
        print(f"  Cases: {len(contract.test_generation.get('cases', []))}")

    # Generate ANN tests
    print("\n" + "=" * 70)
    print("Generating ANN Test Cases...")
    print("=" * 70)

    ann_tests = []
    for contract in ann_contracts:
        contract_tests = generator.generate_for_contract(contract)
        ann_tests.extend(contract_tests)

    print(f"\n[+] Generated {len(ann_tests)} ANN test cases")

    # Group by contract
    print("\n" + "=" * 70)
    print("Test Cases by Contract")
    print("=" * 70)

    for contract in ann_contracts:
        contract_tests = [t for t in ann_tests if t.contract_id == contract.contract_id]
        print(f"\n{contract.contract_id}: {len(contract_tests)} tests")
        for test in contract_tests:
            print(f"  - {test.test_id}: {test.name}")
            print(f"    Strategy: {test.strategy}, Priority: {test.priority}")

    # Save ANN pilot tests
    output_path = generator.save_tests(ann_tests, "ann_pilot")
    print(f"\n[Saved] Output: {output_path}")

    # Summary statistics
    print("\n" + "=" * 70)
    print("ANN Pilot Summary")
    print("=" * 70)

    by_strategy = {}
    by_priority = {}

    for test in ann_tests:
        by_strategy[test.strategy] = by_strategy.get(test.strategy, 0) + 1
        by_priority[test.priority] = by_priority.get(test.priority, 0) + 1

    print(f"\nBy Strategy:")
    for strategy, count in by_strategy.items():
        print(f"  {strategy}: {count}")

    print(f"\nBy Priority:")
    for priority, count in by_priority.items():
        print(f"  {priority}: {count}")

    print(f"\n[Total] {len(ann_tests)} test cases from {len(ann_contracts)} contracts")

    return output_path, ann_tests

if __name__ == "__main__":
    main()
