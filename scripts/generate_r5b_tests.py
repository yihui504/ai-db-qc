"""R5B Lifecycle Test Generator.

Generates deterministic test cases from R5B lifecycle templates.
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

from casegen.generators.instantiator import load_templates, instantiate_template


def generate_test_data() -> Dict[str, Any]:
    """Generate deterministic test data vectors.

    Returns:
        Dict with vector data for template substitution
    """
    random.seed(42)  # Fixed seed for reproducibility

    # Generate 128D vectors
    vectors_128 = [[random.random() for _ in range(128)] for _ in range(100)]

    # Query vector
    query_vector_128 = vectors_128[0]

    return {
        "vectors_128": vectors_128,
        "query_vector_128": query_vector_128,
        "seed": 42
    }


def generate_test_cases(
    templates: List[Dict[str, Any]],
    test_data: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Generate test cases from templates.

    Args:
        templates: List of template definitions
        test_data: Test data for substitution

    Returns:
        List of generated test cases
    """
    test_cases = []

    for template in templates:
        template_id = template.get("template_id")

        # Generate unique collection name (Milvus only allows numbers, letters, underscores)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        # Replace hyphens with underscores for Milvus compatibility
        template_id_safe = template_id.replace("-", "_")
        collection_name = f"test_r5b_{template_id_safe}_{timestamp}"

        # Create substitutions
        substitutions = {
            "collection_name": collection_name,
            **test_data
        }

        # Create test case
        test_case = {
            "test_id": f"R5B-{template_id.upper()}",
            "template_id": template_id,
            "name": template.get("name", ""),
            "contract_id": template.get("contract_id", ""),
            "description": template.get("description", ""),
            "initial_state": template.get("initial_state", ""),
            "target_state": template.get("target_state", ""),
            "sequence": template.get("sequence", []),
            "oracle_expectation": template.get("oracle_expectation", {}),
            "priority": template.get("priority", "MEDIUM"),
            "substitutions": substitutions,
            "generated_at": datetime.now().isoformat()
        }

        # Add metadata
        if "entered_via" in template:
            test_case["entered_via"] = template["entered_via"]
        if "documented_behavior" in template:
            test_case["documented_behavior"] = template["documented_behavior"]

        test_cases.append(test_case)

    return test_cases


def save_test_cases(
    test_cases: List[Dict[str, Any]],
    output_path: str
) -> None:
    """Save test cases to JSON file.

    Args:
        test_cases: List of test cases
        output_path: Output file path
    """
    output = {
        "run_id": f"r5b-lifecycle-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "generated_at": datetime.now().isoformat(),
        "total_tests": len(test_cases),
        "campaign": "R5B_INDEX_LIFECYCLE",
        "version": "2.1",
        "description": "Index lifecycle state transition tests",
        "tests": test_cases,
        "test_data": {
            "seed": 42,
            "dimension": 128,
            "note": "Deterministic test data with fixed seed"
        }
    }

    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)


def main():
    """Main generation function."""
    print("=" * 70)
    print("R5B Lifecycle Test Generator")
    print("=" * 70)

    # Load templates
    template_path = "casegen/templates/r5b_lifecycle.yaml"
    print(f"\n[*] Loading templates from: {template_path}")

    try:
        templates = load_templates(template_path)
        print(f"[+] Loaded {len(templates)} templates")
    except Exception as e:
        print(f"[!] Failed to load templates: {e}")
        return 1

    # Generate test data
    print("\n[*] Generating test data (seed=42)...")
    test_data = generate_test_data()
    print(f"[+] Generated {len(test_data['vectors_128'])} vectors, dimension=128")

    # Generate test cases
    print("\n[*] Generating test cases...")
    test_cases = generate_test_cases(templates, test_data)
    print(f"[+] Generated {len(test_cases)} test cases")

    # List test cases
    print("\n[*] Test Cases:")
    for i, test in enumerate(test_cases, 1):
        print(f"    {i}. {test['test_id']}: {test['name']}")
        print(f"       {test['initial_state']} -> {test['target_state']}")
        print(f"       Contract: {test['contract_id']}, Priority: {test['priority']}")

    # Save test cases
    output_dir = Path("generated_tests")
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_path = output_dir / f"r5b_lifecycle_{timestamp}.json"

    save_test_cases(test_cases, str(output_path))
    print(f"\n[+] Saved test cases to: {output_path}")

    # Summary
    print("\n" + "=" * 70)
    print("Generation Summary")
    print("=" * 70)
    print(f"Total Tests: {len(test_cases)}")
    print(f"By Priority:")
    for priority in ["HIGH", "MEDIUM", "LOW"]:
        count = sum(1 for t in test_cases if t.get("priority") == priority)
        if count > 0:
            print(f"  {priority}: {count}")

    print(f"\nBy Contract:")
    contract_counts = {}
    for test in test_cases:
        contract = test.get("contract_id", "UNKNOWN")
        contract_counts[contract] = contract_counts.get(contract, 0) + 1
    for contract, count in sorted(contract_counts.items()):
        print(f"  {contract}: {count}")

    print(f"\nOutput: {output_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
