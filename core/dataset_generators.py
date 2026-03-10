"""Dataset Generators for High-Yield Test Generation.

This module provides dataset generators that create test vectors designed
to reveal edge cases and bugs in vector database implementations.
"""

from __future__ import annotations

import random
import math
from typing import List, Tuple, Any
from dataclasses import dataclass


@dataclass
class GeneratedDataset:
    """A generated dataset for testing."""
    vectors: List[List[float]]
    metadata: dict[str, Any]
    description: str


class DatasetGenerator:
    """Generate test datasets designed to reveal edge cases and bugs."""

    def __init__(self, dimension: int = 128):
        """Initialize dataset generator.

        Args:
            dimension: Vector dimensionality
        """
        self.dimension = dimension

    def generate_identical_vectors(self, count: int = 100) -> GeneratedDataset:
        """Generate dataset with all identical vectors.

        This tests whether the database handles duplicate vectors correctly,
        including tie-breaking behavior and result stability.

        Args:
            count: Number of vectors to generate

        Returns:
            Dataset with identical vectors
        """
        # All vectors are the same
        base_vector = [0.5] * self.dimension
        vectors = [base_vector.copy() for _ in range(count)]

        return GeneratedDataset(
            vectors=vectors,
            metadata={
                "type": "identical",
                "count": count,
                "dimension": self.dimension,
                "unique_vectors": 1
            },
            description=f"Dataset with {count} identical vectors (tests tie-breaking)"
        )

    def generate_random_vectors(self, count: int = 100, seed: int = None) -> GeneratedDataset:
        """Generate dataset with random vectors.

        Args:
            count: Number of vectors to generate
            seed: Random seed for reproducibility

        Returns:
            Dataset with random vectors
        """
        if seed is not None:
            random.seed(seed)

        vectors = [[random.random() for _ in range(self.dimension)] for _ in range(count)]

        return GeneratedDataset(
            vectors=vectors,
            metadata={
                "type": "random",
                "count": count,
                "dimension": self.dimension,
                "seed": seed
            },
            description=f"Dataset with {count} random vectors (seed={seed})"
        )

    def generate_clustered_vectors(self, count: int = 100, clusters: int = 5) -> GeneratedDataset:
        """Generate dataset with clustered vectors.

        Creates distinct clusters of vectors to test how the database
        handles local vs global search patterns.

        Args:
            count: Total number of vectors
            clusters: Number of clusters to create

        Returns:
            Dataset with clustered vectors
        """
        vectors = []
        vectors_per_cluster = count // clusters

        for cluster_idx in range(clusters):
            # Create a cluster center
            cluster_center = [cluster_idx * 0.2] * self.dimension

            # Add vectors around the cluster center
            for _ in range(vectors_per_cluster):
                # Add small random noise to center
                noise = [random.uniform(-0.02, 0.02) for _ in range(self.dimension)]
                vector = [c + n for c, n in zip(cluster_center, noise)]
                vectors.append(vector)

        # Handle remainder
        remainder = count - len(vectors)
        if remainder > 0:
            cluster_center = [clusters * 0.2] * self.dimension
            for _ in range(remainder):
                noise = [random.uniform(-0.02, 0.02) for _ in range(self.dimension)]
                vector = [c + n for c, n in zip(cluster_center, noise)]
                vectors.append(vector)

        return GeneratedDataset(
            vectors=vectors,
            metadata={
                "type": "clustered",
                "count": count,
                "dimension": self.dimension,
                "clusters": clusters
            },
            description=f"Dataset with {count} vectors in {clusters} clusters (tests local vs global search)"
        )

    def generate_sparse_vectors(self, count: int = 100, sparsity: float = 0.9) -> GeneratedDataset:
        """Generate dataset with sparse vectors (mostly zeros).

        Tests how the database handles sparse data, which can reveal
        numerical precision issues.

        Args:
            count: Number of vectors to generate
            sparsity: Fraction of elements that should be zero (0-1)

        Returns:
            Dataset with sparse vectors
        """
        vectors = []
        for _ in range(count):
            vector = []
            for _ in range(self.dimension):
                if random.random() < sparsity:
                    vector.append(0.0)
                else:
                    vector.append(random.random())
            vectors.append(vector)

        return GeneratedDataset(
            vectors=vectors,
            metadata={
                "type": "sparse",
                "count": count,
                "dimension": self.dimension,
                "sparsity": sparsity
            },
            description=f"Dataset with {count} sparse vectors (sparsity={sparsity})"
        )

    def generate_extreme_vectors(self, count: int = 100) -> GeneratedDataset:
        """Generate dataset with extreme floating-point values.

        Tests numerical stability and handling of edge cases like:
        - Very large values
        - Very small values
        - Mixed magnitudes
        - NaN and infinity handling

        Args:
            count: Number of vectors to generate

        Returns:
            Dataset with extreme values
        """
        vectors = []

        # Mix of different extreme patterns
        patterns = [
            "very_large",      # Values near float max
            "very_small",      # Values near float min
            "mixed_magnitude", # Mix of large and small
            "alternating",     # Alternating large/small values
            "zeros_ones",      # Only 0.0 and 1.0
        ]

        vectors_per_pattern = count // len(patterns)

        for pattern in patterns:
            for _ in range(vectors_per_pattern):
                if pattern == "very_large":
                    vector = [random.uniform(1e30, 1e38) * random.choice([-1, 1]) for _ in range(self.dimension)]
                elif pattern == "very_small":
                    vector = [random.uniform(1e-38, 1e-30) * random.choice([-1, 1]) for _ in range(self.dimension)]
                elif pattern == "mixed_magnitude":
                    vector = [
                        random.choice([
                            random.uniform(1e-38, 1e-30),
                            random.uniform(1e30, 1e38),
                            random.random()
                        ]) for _ in range(self.dimension)
                    ]
                elif pattern == "alternating":
                    vector = []
                    for i in range(self.dimension):
                        if i % 2 == 0:
                            vector.append(random.uniform(1e30, 1e38))
                        else:
                            vector.append(random.uniform(1e-38, 1e-30))
                else:  # zeros_ones
                    vector = [random.choice([0.0, 1.0]) for _ in range(self.dimension)]

                vectors.append(vector)

        # Handle remainder
        remainder = count - len(vectors)
        if remainder > 0:
            for _ in range(remainder):
                vector = [random.uniform(1e30, 1e38) * random.choice([-1, 1]) for _ in range(self.dimension)]
                vectors.append(vector)

        return GeneratedDataset(
            vectors=vectors,
            metadata={
                "type": "extreme",
                "count": count,
                "dimension": self.dimension,
                "patterns": patterns
            },
            description=f"Dataset with {count} vectors containing extreme floating-point values"
        )

    def generate_duplicate_vectors(self, count: int = 100, duplication_rate: float = 0.3) -> GeneratedDataset:
        """Generate dataset with strategic duplicate vectors.

        Tests tie-breaking behavior and result consistency when multiple
        vectors have identical distances to the query.

        Args:
            count: Total number of vectors (including duplicates)
            duplication_rate: Fraction of vectors that should be duplicates

        Returns:
            Dataset with strategic duplicates
        """
        # Generate base unique vectors
        unique_count = int(count * (1 - duplication_rate))
        unique_vectors = [[random.random() for _ in range(self.dimension)] for _ in range(unique_count)]

        # Create duplicates
        vectors = list(unique_vectors)
        duplicate_count = count - unique_count

        for _ in range(duplicate_count):
            # Randomly select a vector to duplicate
            base_vector = random.choice(unique_vectors)
            vectors.append(base_vector.copy())

        # Shuffle to mix duplicates throughout
        random.shuffle(vectors)

        return GeneratedDataset(
            vectors=vectors,
            metadata={
                "type": "duplicates",
                "count": count,
                "dimension": self.dimension,
                "unique_vectors": unique_count,
                "duplicate_count": duplicate_count,
                "duplication_rate": duplication_rate
            },
            description=f"Dataset with {count} vectors ({duplicate_count} duplicates, tests tie-breaking)"
        )

    def generate_high_dimensional(self, count: int = 100, dimension: int = 2048) -> GeneratedDataset:
        """Generate high-dimensional dataset.

        Tests how the database handles high-dimensional vectors, which can
        reveal curse of dimensionality issues.

        Args:
            count: Number of vectors to generate
            dimension: Vector dimensionality

        Returns:
            High-dimensional dataset
        """
        vectors = [[random.random() for _ in range(dimension)] for _ in range(count)]

        return GeneratedDataset(
            vectors=vectors,
            metadata={
                "type": "high_dimensional",
                "count": count,
                "dimension": dimension
            },
            description=f"Dataset with {count} high-dimensional vectors (dim={dimension})"
        )

    def generate_size_edge_cases(self) -> List[GeneratedDataset]:
        """Generate datasets at size boundaries.

        Tests behavior at collection size limits:
        - Empty collection
        - Single vector
        - Two vectors
        - Very large collection

        Returns:
            List of edge case datasets
        """
        datasets = []

        # Empty collection
        datasets.append(GeneratedDataset(
            vectors=[],
            metadata={"type": "edge_case", "edge_case": "empty", "count": 0},
            description="Empty collection (edge case)"
        ))

        # Single vector
        datasets.append(GeneratedDataset(
            vectors=[[random.random() for _ in range(self.dimension)]],
            metadata={"type": "edge_case", "edge_case": "single", "count": 1},
            description="Single vector collection (edge case)"
        ))

        # Two vectors
        datasets.append(GeneratedDataset(
            vectors=[[random.random() for _ in range(self.dimension)] for _ in range(2)],
            metadata={"type": "edge_case", "edge_case": "two", "count": 2},
            description="Two vector collection (edge case)"
        ))

        # Small collection
        datasets.append(GeneratedDataset(
            vectors=[[random.random() for _ in range(self.dimension)] for _ in range(10)],
            metadata={"type": "edge_case", "edge_case": "small", "count": 10},
            description="Small collection (10 vectors)"
        ))

        return datasets
