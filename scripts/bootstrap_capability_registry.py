#!/usr/bin/env python3
"""Bootstrap capability registry from adapter code.

Priority: Scan execute() dispatch mapping first
Fallback: Scan _operation() methods
Filter: Exclude pure helper methods
"""

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Set


# Known helper methods to exclude (not operations)
HELPER_METHODS = {
    "_connect", "_format_output", "_parse_response", "_validate_params",
    "_build_schema", "_get_collection", "health_check", "close",
    "get_runtime_snapshot", "__init__"
}


class CapabilityScanner:
    """Scan adapter code to extract operations."""

    def __init__(self, adapter_path: Path):
        self.adapter_path = adapter_path

    def scan_execute_dispatch(self, content: str) -> Set[str]:
        """Extract operations from execute() method's if/elif chain.

        Priority method: Most adapters explicitly map operation names.
        """
        operations = set()

        # Find execute method body
        execute_match = re.search(
            r'def execute\(self[^)]*\):(.*?)(?=\n    def |\nclass |\Z)',
            content,
            re.DOTALL
        )

        if execute_match:
            execute_body = execute_match.group(1)
            # Find operation == "xxx" patterns
            op_patterns = [
                r'operation\s*==\s*["\'](\w+)["\']',
                r'elif\s+operation\s*==\s*["\'](\w+)["\']:',
                r'if\s+operation\s*==\s*["\'](\w+)["\']:',
            ]
            for pattern in op_patterns:
                matches = re.findall(pattern, execute_body)
                operations.update(matches)

        return operations

    def scan_private_methods(self, content: str) -> Set[str]:
        """Fallback: Extract from _operation() methods.

        Filters out known helper methods.
        """
        operations = set()

        # Find all _method definitions
        for match in re.finditer(r'def (_\w+)\(', content):
            method_name = match.group(1)
            if method_name not in HELPER_METHODS:
                operations.add(method_name.lstrip("_"))

        return operations

    def scan(self) -> List[Dict[str, Any]]:
        """Scan adapter file for operations.

        Returns:
            List of operation dicts
        """
        content = self.adapter_path.read_text()

        # Priority 1: Scan execute() dispatch
        operations = self.scan_execute_dispatch(content)

        # Priority 2: Fallback to _operation methods
        if not operations:
            operations = self.scan_private_methods(content)

        # Build operation list
        result = []
        for op_name in sorted(operations):
            result.append({
                "operation": op_name,
                "support_status": "unknown",
                "support_level": "static_only",
                "confidence": "low",
                "implementation_path": f"{self.adapter_path.stem}Adapter._{op_name if not op_name.startswith('_') else op_name}",
                "verification_path": None,
                "known_constraints": [],
                "evidence_source": "static_scan",
                "validated_in_campaigns": [],
                "notes": "TODO: Manual review required"
            })

        return result


def main():
    parser = argparse.ArgumentParser(description="Bootstrap capability registry")
    parser.add_argument("--adapter", required=True,
                        help="Adapter name (milvus, qdrant, seekdb, mock)")
    parser.add_argument("--output", default="capabilities", help="Output directory")
    args = parser.parse_args()

    adapter_files = {
        "milvus": "adapters/milvus_adapter.py",
        "qdrant": "adapters/qdrant_adapter.py",
        "seekdb": "adapters/seekdb_adapter.py",
        "mock": "adapters/mock.py"
    }

    if args.adapter not in adapter_files:
        print(f"Error: Unknown adapter '{args.adapter}'")
        print(f"Available: {', '.join(adapter_files.keys())}")
        return 1

    adapter_path = Path(adapter_files[args.adapter])
    if not adapter_path.exists():
        print(f"Error: Adapter file not found: {adapter_path}")
        return 1

    # Scan adapter
    scanner = CapabilityScanner(adapter_path)
    operations = scanner.scan()

    # Extract SDK version from imports
    content = adapter_path.read_text()
    sdk_version = "TODO"
    # Try to detect version from various patterns
    version_patterns = [
        r'pymilvus\s*==\s*([\d.]+)',
        r'from pymilvus import.*# v([\d.]+)',
        r'pymilvus version ([\d.]+)',
    ]
    for pattern in version_patterns:
        match = re.search(pattern, content)
        if match:
            sdk_version = f"pymilvus v{match.group(1)}"
            break

    # Build registry
    registry = {
        "adapter_name": f"{args.adapter}_adapter",
        "db_family": args.adapter.capitalize(),
        "sdk_version": sdk_version,
        "validated_db_version": "TODO",
        "last_updated": "2026-03-10",
        "operations": operations
    }

    # Write output
    output_path = Path(args.output) / f"{args.adapter}_capabilities.json"
    output_path.write_text(json.dumps(registry, indent=2))
    print(f"Generated: {output_path}")
    print(f"Found {len(operations)} operations")
    print("Please review and update:")
    print("  - sdk_version")
    print("  - validated_db_version")
    print("  - support_status (supported/unsupported/partially_supported)")
    print("  - confidence (high/medium/low)")
    print("  - known_constraints")
    print("  - validated_in_campaigns")
    print("  - notes")

    return 0


if __name__ == "__main__":
    exit(main())
