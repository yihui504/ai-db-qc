"""Debug run_semantic_extended runner."""
import sys
sys.path.insert(0, ".")

from ai_db_qa.semantic_datagen import SemanticDataGenerator, SemanticTestDataset

# Generate dataset
gen = SemanticDataGenerator()
dataset = gen.generate(
    domain="finance",
    n_positives=10,
    n_negatives=5,
    n_hard_negatives=10,
    n_boundary=3,
)

print(f"Dataset pairs count: {len(dataset.pairs)}")
print(f"Positive pairs: {dataset.get_pairs_by_type('positive')}")
print(f"Negative pairs: {dataset.get_pairs_by_type('negative')}")
print(f"Hard negative pairs: {dataset.get_pairs_by_type('hard_negative')}")
