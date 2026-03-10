"""Hybrid Test Generator for R5C Pilot.

Generates test cases for hybrid query contracts (filter + vector search).
"""

import math
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class HybridDataset:
    """Deterministic dataset for hybrid testing."""
    name: str
    entities: List[Dict[str, Any]]
    query_vector: List[float]
    filter_criteria: Dict[str, Any]
    top_k: int
    description: str


class HybridDatasetGenerator:
    """Generate deterministic datasets for hybrid query testing."""

    def __init__(self, dimension: int = 128):
        self.dimension = dimension

    def generate_dataset_1_vector_trap(self) -> HybridDataset:
        """Dataset 1: Vector Trap for HYB-001.

        Tests whether entities with wrong filter values are correctly excluded,
        even with similar vectors.
        """
        # Entity 1: red, exact match to query (all zeros)
        entity_1 = {
            'id': 1,
            'scalar_fields': {'color': 'red', 'status': 'active'},
            'vector': [0.0] * self.dimension
        }

        # Entity 2: blue, nearly identical vector (should be excluded!)
        vec_2 = [0.0001] * 5 + [0.0] * (self.dimension - 5)
        entity_2 = {
            'id': 2,
            'scalar_fields': {'color': 'blue', 'status': 'active'},
            'vector': vec_2
        }

        # Entities 3-15: red, with increasing distances
        entities = [entity_1, entity_2]
        for i in range(3, 16):
            vec = [(i - 1) * 0.1] * 4 + [0.0] * (self.dimension - 4)
            entity = {
                'id': i,
                'scalar_fields': {'color': 'red', 'status': 'active' if i % 2 == 0 else 'pending'},
                'vector': vec
            }
            entities.append(entity)

        return HybridDataset(
            name="dataset_1_vector_trap",
            entities=entities,
            query_vector=[0.0] * self.dimension,
            filter_criteria={'color': 'red'},
            top_k=10,
            description="15 entities: Entity 2 (blue) has nearly identical vector to query but must be excluded"
        )

    def generate_dataset_2_controlled_axis(self) -> HybridDataset:
        """Dataset 2: Controlled Axis for HYB-002.

        Fully deterministic distances - entities placed on x-axis.
        Distance to query = entity's x-coordinate.
        """
        entities = []
        for i in range(1, 13):
            # Distance = (i-1) * 0.15 for increasing distances
            x_coord = (i - 1) * 0.15
            vec = [x_coord] + [0.0] * (self.dimension - 1)

            # Alternate colors: red, red, blue, red, red, blue, ...
            color = 'red' if i not in [3, 6, 9, 12] else 'blue'

            entity = {
                'id': i,
                'scalar_fields': {'color': color, 'status': 'active'},
                'vector': vec
            }
            entities.append(entity)

        # Filtered subset (color='red'): {1, 2, 4, 5, 7, 8, 10, 11}
        # Filtered distances: [0.0, 0.15, 0.45, 0.6, 0.9, 1.05, 1.35, 1.5]

        return HybridDataset(
            name="dataset_2_controlled_axis",
            entities=entities,
            query_vector=[0.0] * self.dimension,
            filter_criteria={'color': 'red'},
            top_k=5,
            description="12 entities on x-axis: deterministic distances, alternating colors"
        )

    def generate_dataset_3_top_k_truncation(self) -> HybridDataset:
        """Dataset 3: Top-K Truncation for HYB-001.

        Tests whether system returns full filtered top-k when filtered
        subset is smaller than top_k parameter.
        """
        # Only 3 red entities, 12 blue entities
        entities = []

        # Red entities (filtered subset = only 3)
        for i in range(1, 4):
            vec = [(i - 1) * 0.1] + [0.0] * (self.dimension - 1)
            entity = {
                'id': i,
                'scalar_fields': {'color': 'red', 'status': 'active'},
                'vector': vec
            }
            entities.append(entity)

        # Blue entities (should be excluded)
        for i in range(4, 16):
            vec = [(i - 1) * 0.1] + [0.0] * (self.dimension - 1)
            entity = {
                'id': i,
                'scalar_fields': {'color': 'blue', 'status': 'active'},
                'vector': vec
            }
            entities.append(entity)

        return HybridDataset(
            name="dataset_3_top_k_truncation",
            entities=entities,
            query_vector=[0.0] * self.dimension,
            filter_criteria={'color': 'red'},
            top_k=10,  # Request 10, but only 3 red exist
            description="15 entities: only 3 red, top_k=10 - should return all 3 red entities"
        )

    def generate_dataset_4_impossible_filter(self) -> HybridDataset:
        """Dataset 4: Impossible Filter for HYB-003.

        Tests empty filter result handling.
        """
        entities = []
        for i in range(1, 11):
            vec = [i * 0.1] + [0.0] * (self.dimension - 1)
            entity = {
                'id': i,
                'scalar_fields': {'color': 'red', 'status': 'active'},
                'vector': vec
            }
            entities.append(entity)

        return HybridDataset(
            name="dataset_4_impossible_filter",
            entities=entities,
            query_vector=[0.5] * self.dimension,
            filter_criteria={'color': 'blue'},  # Impossible - no blue entities
            top_k=10,
            description="10 entities: all red, filter for blue - should return empty results"
        )

    def generate_all_datasets(self) -> Dict[str, HybridDataset]:
        """Generate all 4 deterministic datasets."""
        return {
            'dataset_1_vector_trap': self.generate_dataset_1_vector_trap(),
            'dataset_2_controlled_axis': self.generate_dataset_2_controlled_axis(),
            'dataset_3_top_k_truncation': self.generate_dataset_3_top_k_truncation(),
            'dataset_4_impossible_filter': self.generate_dataset_4_impossible_filter()
        }


class HybridTestGenerator:
    """Generate hybrid query test cases from contracts."""

    def __init__(self):
        self.dataset_generator = HybridDatasetGenerator()
        self.datasets = self.dataset_generator.generate_all_datasets()

    def generate_hyb001_tests(self) -> List[Dict[str, Any]]:
        """Generate HYB-001: Filter Pre-Application tests (6 tests)."""
        tests = []

        # Test 1: exclusion_basic
        tests.append({
            'test_id': 'hyb-001_exclusion_001',
            'contract_id': 'HYB-001',
            'name': 'Filter Exclusion - Basic',
            'dataset_name': 'dataset_1_vector_trap',
            'filter_criteria': {'color': 'red'},
            'top_k': 10,
            'expected_behavior': 'All results must have color=red, no blue entities',
            'oracle_check': 'all_results_satisfy_filter',
            'bug_yield_potential': 'CRITICAL'
        })

        # Test 2: exclusion_similarity_trap
        tests.append({
            'test_id': 'hyb-001_exclusion_002',
            'contract_id': 'HYB-001',
            'name': 'Filter Exclusion - Similarity Trap',
            'dataset_name': 'dataset_1_vector_trap',
            'filter_criteria': {'color': 'red'},
            'top_k': 10,
            'expected_behavior': 'Entity 2 (blue) with near-identical vector must be excluded',
            'oracle_check': 'all_results_satisfy_filter',
            'bug_yield_potential': 'CRITICAL'
        })

        # Test 3: exclusion_multiple_filters
        tests.append({
            'test_id': 'hyb-001_exclusion_003',
            'contract_id': 'HYB-001',
            'name': 'Filter Exclusion - Multiple Conditions',
            'dataset_name': 'dataset_1_vector_trap',
            'filter_criteria': {'color': 'red', 'status': 'active'},
            'top_k': 10,
            'expected_behavior': 'All results must have color=red AND status=active',
            'oracle_check': 'all_results_satisfy_filter',
            'bug_yield_potential': 'CRITICAL'
        })

        # Test 4: exclusion_set_membership
        tests.append({
            'test_id': 'hyb-001_exclusion_004',
            'contract_id': 'HYB-001',
            'name': 'Filter Exclusion - Set Membership',
            'dataset_name': 'dataset_1_vector_trap',
            'filter_criteria': {'color': ['red', 'green']},  # Only red exists
            'top_k': 10,
            'expected_behavior': 'All results must have color IN [red, green]',
            'oracle_check': 'all_results_satisfy_filter',
            'bug_yield_potential': 'HIGH'
        })

        # Test 5: exclusion_null_filter
        tests.append({
            'test_id': 'hyb-001_exclusion_005',
            'contract_id': 'HYB-001',
            'name': 'Filter Exclusion - Null Handling',
            'dataset_name': 'dataset_1_vector_trap',
            'filter_criteria': {'status': None},  # No nulls exist
            'top_k': 10,
            'expected_behavior': 'Results must have status=NULL (should be empty or handle gracefully)',
            'oracle_check': 'all_results_satisfy_filter',
            'bug_yield_potential': 'MEDIUM'
        })

        # Test 6: truncation_full_filtered_topk
        tests.append({
            'test_id': 'hyb-001_truncation_001',
            'contract_id': 'HYB-001',
            'name': 'Top-K Truncation - Full Filtered Subset',
            'dataset_name': 'dataset_3_top_k_truncation',
            'filter_criteria': {'color': 'red'},
            'top_k': 10,  # Only 3 red exist
            'expected_behavior': 'Return all 3 red entities (not 10 with 7 blue)',
            'oracle_check': 'all_results_satisfy_filter',
            'bug_yield_potential': 'CRITICAL'
        })

        return tests

    def generate_hyb002_tests(self) -> List[Dict[str, Any]]:
        """Generate HYB-002: Filter-Result Consistency tests (4 tests)."""
        tests = []

        # Test 1: consistency_filter_satisfaction
        tests.append({
            'test_id': 'hyb-002_consistency_001',
            'contract_id': 'HYB-002',
            'name': 'Consistency - Filter Satisfaction',
            'dataset_name': 'dataset_2_controlled_axis',
            'filter_criteria': {'color': 'red'},
            'top_k': 5,
            'expected_behavior': 'All results satisfy color=red',
            'oracle_check': 'filter_satisfaction_and_monotonicity',
            'bug_yield_potential': 'HIGH'
        })

        # Test 2: consistency_distance_monotonicity
        tests.append({
            'test_id': 'hyb-002_consistency_002',
            'contract_id': 'HYB-002',
            'name': 'Consistency - Distance Monotonicity',
            'dataset_name': 'dataset_2_controlled_axis',
            'filter_criteria': {'color': 'red'},
            'top_k': 5,
            'expected_behavior': 'Distances are monotonically increasing within filtered entities',
            'oracle_check': 'filter_satisfaction_and_monotonicity',
            'bug_yield_potential': 'HIGH'
        })

        # Test 3: consistency_different_topk
        tests.append({
            'test_id': 'hyb-002_consistency_003',
            'contract_id': 'HYB-002',
            'name': 'Consistency - Different Top-K Values',
            'dataset_name': 'dataset_2_controlled_axis',
            'filter_criteria': {'color': 'red'},
            'top_k': 3,
            'expected_behavior': 'Filter satisfaction and monotonicity with top_k=3',
            'oracle_check': 'filter_satisfaction_and_monotonicity',
            'bug_yield_potential': 'MEDIUM'
        })

        # Test 4: consistency_exact_reference
        tests.append({
            'test_id': 'hyb-002_consistency_004',
            'contract_id': 'HYB-002',
            'name': 'Consistency - Exact Reference Comparison',
            'dataset_name': 'dataset_2_controlled_axis',
            'filter_criteria': {'color': 'red'},
            'top_k': 5,
            'expected_behavior': 'Compare with exact ground truth (ALLOWED_DIFFERENCE for ANN)',
            'oracle_check': 'filter_satisfaction_and_monotonicity',
            'bug_yield_potential': 'MEDIUM'
        })

        return tests

    def generate_hyb003_tests(self) -> List[Dict[str, Any]]:
        """Generate HYB-003: Empty Filter Result Handling tests (4 tests)."""
        tests = []

        # Test 1: empty_impossible_filter
        tests.append({
            'test_id': 'hyb-003_empty_001',
            'contract_id': 'HYB-003',
            'name': 'Empty Filter - Impossible Condition',
            'dataset_name': 'dataset_4_impossible_filter',
            'filter_criteria': {'color': 'blue'},
            'top_k': 10,
            'expected_behavior': 'Empty results (all entities are red)',
            'oracle_check': 'empty_when_no_match',
            'bug_yield_potential': 'MEDIUM'
        })

        # Test 2: empty_collection
        tests.append({
            'test_id': 'hyb-003_empty_002',
            'contract_id': 'HYB-003',
            'name': 'Empty Filter - Empty Collection',
            'dataset_name': 'dataset_4_impossible_filter',
            'filter_criteria': {'color': 'red'},
            'top_k': 10,
            'use_empty_collection': True,
            'expected_behavior': 'Empty results (collection is empty)',
            'oracle_check': 'empty_when_no_match',
            'bug_yield_potential': 'MEDIUM'
        })

        # Test 3: empty_null_filter
        tests.append({
            'test_id': 'hyb-003_empty_003',
            'contract_id': 'HYB-003',
            'name': 'Empty Filter - Null Field Filter',
            'dataset_name': 'dataset_4_impossible_filter',
            'filter_criteria': {'nonexistent_field': 'value'},
            'top_k': 10,
            'expected_behavior': 'Empty results or consistent error handling',
            'oracle_check': 'empty_when_no_match',
            'bug_yield_potential': 'LOW'
        })

        # Test 4: empty_contradictory
        tests.append({
            'test_id': 'hyb-003_empty_004',
            'contract_id': 'HYB-003',
            'name': 'Empty Filter - Contradictory Condition',
            'dataset_name': 'dataset_4_impossible_filter',
            'filter_criteria': {'color': 'red', 'color': 'blue'},  # Contradictory
            'top_k': 10,
            'expected_behavior': 'Empty results or consistent error handling',
            'oracle_check': 'empty_when_no_match',
            'bug_yield_potential': 'LOW'
        })

        return tests

    def generate_all_tests(self) -> List[Dict[str, Any]]:
        """Generate all 14 hybrid test cases."""
        all_tests = []
        all_tests.extend(self.generate_hyb001_tests())
        all_tests.extend(self.generate_hyb002_tests())
        all_tests.extend(self.generate_hyb003_tests())

        # Don't embed dataset object - it will be regenerated by executor
        # Just keep dataset_name reference

        return all_tests


def main():
    """Generate and save hybrid test cases."""
    import json
    from pathlib import Path
    from datetime import datetime

    generator = HybridTestGenerator()
    tests = generator.generate_all_tests()

    # Prepare output
    output = {
        'run_id': f'hybrid-pilot-{datetime.now().strftime("%Y%m%d-%H%M%S")}',
        'timestamp': datetime.now().isoformat(),
        'total_tests': len(tests),
        'tests': tests
    }

    # Save to file
    output_dir = Path("generated_tests")
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"hybrid_pilot_{timestamp}.json"
    output_path = output_dir / filename

    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2, default=str)

    print(f"[+] Generated {len(tests)} hybrid test cases")
    print(f"[+] Saved to: {output_path}")

    # Print summary
    print("\nTest Summary:")
    print(f"  HYB-001 (Filter Pre-Application): {len(generator.generate_hyb001_tests())} tests")
    print(f"  HYB-002 (Filter-Result Consistency): {len(generator.generate_hyb002_tests())} tests")
    print(f"  HYB-003 (Empty Filter Handling): {len(generator.generate_hyb003_tests())} tests")
    print(f"  TOTAL: {len(tests)} tests")


if __name__ == "__main__":
    main()
