"""Contract Registry for AI-DB-QC Framework.

This module loads and manages contract definitions from JSON files,
providing access to contracts for test generation and oracle evaluation.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class Contract:
    """A contract specification loaded from JSON."""

    contract_id: str
    name: str
    family: str
    type: str
    statement: str
    rationale: str
    scope: Dict[str, Any]
    preconditions: List[str]
    postconditions: List[str]
    invariants: List[str]
    violation_criteria: Dict[str, Any]
    test_generation: Dict[str, Any]
    oracle: Dict[str, Any]
    metadata: Dict[str, Any]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Contract":
        """Create Contract from dictionary."""
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        """Convert Contract to dictionary."""
        return {
            "contract_id": self.contract_id,
            "name": self.name,
            "family": self.family,
            "type": self.type,
            "statement": self.statement,
            "rationale": self.rationale,
            "scope": self.scope,
            "preconditions": self.preconditions,
            "postconditions": self.postconditions,
            "invariants": self.invariants,
            "violation_criteria": self.violation_criteria,
            "test_generation": self.test_generation,
            "oracle": self.oracle,
            "metadata": self.metadata
        }


class ContractRegistry:
    """Registry for managing contract definitions."""

    def __init__(self, contracts_dir: Optional[str] = None):
        """Initialize contract registry.

        Args:
            contracts_dir: Path to contracts directory (default: contracts/)
        """
        if contracts_dir is None:
            # Default to contracts/ in project root
            # Get the absolute path to the contracts directory
            import os
            script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
            project_root = script_dir.parent
            contracts_dir = project_root / "contracts"

        self.contracts_dir = Path(contracts_dir)
        self._contracts: Dict[str, Contract] = {}
        self._contracts_by_family: Dict[str, List[str]] = {}

    def load_all(self) -> int:
        """Load all contract JSON files from the registry.

        Returns:
            Number of contracts loaded
        """
        count = 0

        # Walk through family directories
        for family_dir in self.contracts_dir.iterdir():
            if not family_dir.is_dir():
                continue

            family_name = family_dir.name

            # Load all JSON files in family directory
            for contract_file in family_dir.glob("*.json"):
                try:
                    contract = self._load_contract_file(contract_file)
                    self._contracts[contract.contract_id] = contract

                    # Index by family
                    if family_name not in self._contracts_by_family:
                        self._contracts_by_family[family_name] = []
                    self._contracts_by_family[family_name].append(contract.contract_id)

                    count += 1
                except Exception as e:
                    print(f"[WARN] Failed to load {contract_file}: {e}")

        return count

    def _load_contract_file(self, file_path: Path) -> Contract:
        """Load a single contract JSON file.

        Args:
            file_path: Path to contract JSON file

        Returns:
            Contract object
        """
        with open(file_path, 'r') as f:
            data = json.load(f)

        # Validate required fields
        required_fields = [
            "contract_id", "name", "family", "type",
            "statement", "rationale", "scope",
            "preconditions", "postconditions", "invariants",
            "violation_criteria", "test_generation", "oracle",
            "metadata"
        ]

        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

        return Contract.from_dict(data)

    def get_contract(self, contract_id: str) -> Optional[Contract]:
        """Get a contract by ID.

        Args:
            contract_id: Contract identifier

        Returns:
            Contract object or None if not found
        """
        return self._contracts.get(contract_id)

    def get_contracts_by_family(self, family: str) -> List[Contract]:
        """Get all contracts in a family.

        Args:
            family: Family name (ann, index, hybrid, schema)

        Returns:
            List of contracts in the family
        """
        contract_ids = self._contracts_by_family.get(family.lower(), [])
        return [self._contracts[cid] for cid in contract_ids]

    def get_all_contracts(self) -> List[Contract]:
        """Get all loaded contracts.

        Returns:
            List of all contracts
        """
        return list(self._contracts.values())

    def get_contracts_by_type(self, contract_type: str) -> List[Contract]:
        """Get all contracts of a specific type.

        Args:
            contract_type: Contract type (universal, database_specific)

        Returns:
            List of contracts of the specified type
        """
        return [
            c for c in self._contracts.values()
            if c.type == contract_type
        ]

    def get_contracts_by_complexity(self, complexity: str) -> List[Contract]:
        """Get all contracts by test complexity.

        Args:
            complexity: Test complexity (low, medium, high)

        Returns:
            List of contracts with specified complexity
        """
        return [
            c for c in self._contracts.values()
            if c.metadata.get("test_complexity") == complexity
        ]

    def validate_dependencies(self) -> List[str]:
        """Validate that all contract dependencies exist.

        Returns:
            List of missing dependency contract IDs
        """
        missing = []

        for contract in self.get_all_contracts():
            deps = contract.metadata.get("dependencies", [])
            for dep_id in deps:
                if dep_id not in self._contracts:
                    missing.append(f"{contract.contract_id} -> {dep_id}")

        return missing

    def get_statistics(self) -> Dict[str, Any]:
        """Get registry statistics.

        Returns:
            Dictionary with registry statistics
        """
        contracts = self.get_all_contracts()

        # Count by family
        by_family = {}
        for contract in contracts:
            family = contract.family
            by_family[family] = by_family.get(family, 0) + 1

        # Count by type
        by_type = {}
        for contract in contracts:
            ctype = contract.type
            by_type[ctype] = by_type.get(ctype, 0) + 1

        # Count by complexity
        by_complexity = {}
        for contract in contracts:
            complexity = contract.metadata.get("test_complexity", "unknown")
            by_complexity[complexity] = by_complexity.get(complexity, 0) + 1

        return {
            "total_contracts": len(contracts),
            "by_family": by_family,
            "by_type": by_type,
            "by_complexity": by_complexity,
            "families": list(self._contracts_by_family.keys())
        }

    def get_test_generation_summary(self) -> Dict[str, Any]:
        """Get summary of test generation strategies.

        Returns:
            Dictionary with test generation summary
        """
        strategies = {}

        for contract in self.get_all_contracts():
            strategy = contract.test_generation.get("strategy", "unknown")
            if strategy not in strategies:
                strategies[strategy] = []
            strategies[strategy].append(contract.contract_id)

        return {
            "strategies": strategies,
            "total_strategies": len(strategies)
        }


# Singleton instance
_registry_instance: Optional[ContractRegistry] = None


def get_registry(contracts_dir: Optional[str] = None) -> ContractRegistry:
    """Get the singleton contract registry instance.

    Args:
        contracts_dir: Path to contracts directory

    Returns:
        ContractRegistry instance
    """
    global _registry_instance

    if _registry_instance is None:
        _registry_instance = ContractRegistry(contracts_dir)
        _registry_instance.load_all()

    return _registry_instance


if __name__ == "__main__":
    # Test contract registry
    registry = get_registry()

    print(f"Loaded {len(registry.get_all_contracts())} contracts")

    stats = registry.get_statistics()
    print(f"\nBy Family: {stats['by_family']}")
    print(f"By Type: {stats['by_type']}")
    print(f"By Complexity: {stats['by_complexity']}")

    # Validate dependencies
    missing = registry.validate_dependencies()
    if missing:
        print(f"\nMissing dependencies: {missing}")
    else:
        print(f"\nAll dependencies satisfied")

    # Show all contracts
    print(f"\nAll Contracts:")
    for contract in registry.get_all_contracts():
        print(f"  {contract.contract_id}: {contract.name}")
