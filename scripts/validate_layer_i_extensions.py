"""Layer I Extension Validation Script.

This script validates all Layer I extensions:
1. Cross-database ablation experiments
2. R4 lifecycle contract cross-database testing
3. R6 consistency contract cross-database testing
4. R5D schema evolution cross-database testing
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))


def validate_imports() -> Dict[str, Any]:
    """Validate that all required modules can be imported."""
    results = {
        "test": "import_validation",
        "passed": True,
        "modules": {}
    }
    
    modules_to_test = [
        ("oracles.differential", "DifferentialOracle"),
        ("oracles.differential", "R4LifecycleOracle"),
        ("oracles.differential", "R6ConsistencyOracle"),
        ("oracles.differential", "DifferenceCategory"),
        ("scripts.run_cross_db_ablation", "run_cross_db_ablation"),
        ("scripts.run_r4_cross_db", "run_r4_cross_db"),
        ("scripts.run_r6_cross_db", "run_r6_cross_db"),
        ("scripts.run_r5d_cross_db", "run_r5d_cross_db"),
    ]
    
    for module_name, item_name in modules_to_test:
        try:
            module = __import__(module_name, fromlist=[item_name])
            getattr(module, item_name)
            results["modules"][f"{module_name}.{item_name}"] = "OK"
        except Exception as e:
            results["modules"][f"{module_name}.{item_name}"] = f"FAILED: {e}"
            results["passed"] = False
    
    return results


def validate_file_structure() -> Dict[str, Any]:
    """Validate that all required files exist."""
    results = {
        "test": "file_structure_validation",
        "passed": True,
        "files": {}
    }
    
    required_files = [
        "oracles/differential.py",
        "scripts/run_cross_db_ablation.py",
        "scripts/run_r4_cross_db.py",
        "scripts/run_r6_cross_db.py",
        "scripts/run_r5d_cross_db.py",
    ]
    
    project_root = Path(__file__).parent.parent
    
    for file_path in required_files:
        full_path = project_root / file_path
        exists = full_path.exists()
        results["files"][file_path] = "OK" if exists else "MISSING"
        if not exists:
            results["passed"] = False
    
    return results


def validate_oracle_implementation() -> Dict[str, Any]:
    """Validate differential oracle implementation."""
    results = {
        "test": "oracle_implementation_validation",
        "passed": True,
        "checks": {}
    }
    
    try:
        from oracles.differential import (
            DifferentialOracle,
            R4LifecycleOracle,
            R6ConsistencyOracle,
            DifferenceCategory,
            DatabaseBehavior
        )
        
        # Check DifferentialOracle has required methods
        required_methods = ['validate', '_extract_behavior', '_classify_difference']
        for method in required_methods:
            has_method = hasattr(DifferentialOracle, method)
            results["checks"][f"DifferentialOracle.{method}"] = "OK" if has_method else "MISSING"
            if not has_method:
                results["passed"] = False
        
        # Check DifferenceCategory enum values
        expected_categories = [
            'CONSISTENT',
            'CONTRACT_VIOLATION',
            'ALLOWED_DIFFERENCE',
            'UNDEFINED_BEHAVIOR'
        ]
        for category in expected_categories:
            has_category = hasattr(DifferenceCategory, category)
            results["checks"][f"DifferenceCategory.{category}"] = "OK" if has_category else "MISSING"
            if not has_category:
                results["passed"] = False
        
        # Check specialized oracles inherit from DifferentialOracle
        r4_inherits = issubclass(R4LifecycleOracle, DifferentialOracle)
        r6_inherits = issubclass(R6ConsistencyOracle, DifferentialOracle)
        
        results["checks"]["R4LifecycleOracle inheritance"] = "OK" if r4_inherits else "FAILED"
        results["checks"]["R6ConsistencyOracle inheritance"] = "OK" if r6_inherits else "FAILED"
        
        if not r4_inherits or not r6_inherits:
            results["passed"] = False
        
        # Check DatabaseBehavior dataclass
        try:
            behavior = DatabaseBehavior(
                database="test",
                success=True,
                error_message=None,
                result_ids={1, 2, 3},
                result_count=3,
                response_data={"test": "data"}
            )
            results["checks"]["DatabaseBehavior instantiation"] = "OK"
        except Exception as e:
            results["checks"]["DatabaseBehavior instantiation"] = f"FAILED: {e}"
            results["passed"] = False
        
    except Exception as e:
        results["checks"]["import"] = f"FAILED: {e}"
        results["passed"] = False
    
    return results


def validate_script_interfaces() -> Dict[str, Any]:
    """Validate that all scripts have proper interfaces."""
    results = {
        "test": "script_interface_validation",
        "passed": True,
        "scripts": {}
    }
    
    scripts_to_check = [
        ("scripts.run_cross_db_ablation", "run_cross_db_ablation", ["databases", "templates", "run_tag"]),
        ("scripts.run_r4_cross_db", "run_r4_cross_db", ["databases", "run_tag"]),
        ("scripts.run_r6_cross_db", "run_r6_cross_db", ["databases", "run_tag"]),
        ("scripts.run_r5d_cross_db", "run_r5d_cross_db", ["databases", "run_tag"]),
    ]
    
    for module_name, func_name, required_params in scripts_to_check:
        try:
            module = __import__(module_name, fromlist=[func_name])
            func = getattr(module, func_name)
            
            # Check function signature
            import inspect
            sig = inspect.signature(func)
            params = list(sig.parameters.keys())
            
            missing_params = [p for p in required_params if p not in params]
            
            if missing_params:
                results["scripts"][f"{module_name}.{func_name}"] = f"MISSING_PARAMS: {missing_params}"
                results["passed"] = False
            else:
                results["scripts"][f"{module_name}.{func_name}"] = "OK"
                
        except Exception as e:
            results["scripts"][f"{module_name}.{func_name}"] = f"FAILED: {e}"
            results["passed"] = False
    
    return results


def validate_test_case_definitions() -> Dict[str, Any]:
    """Validate that test case definitions are properly structured."""
    results = {
        "test": "test_case_validation",
        "passed": True,
        "test_suites": {}
    }
    
    test_suites = [
        ("scripts.run_r4_cross_db", "R4_TEST_CASES", 8),
        ("scripts.run_r6_cross_db", "R6_TEST_CASES", 6),
        ("scripts.run_r5d_cross_db", "R5D_TEST_CASES", 5),
    ]
    
    for module_name, var_name, expected_count in test_suites:
        try:
            module = __import__(module_name, fromlist=[var_name])
            test_cases = getattr(module, var_name)
            
            # Check count
            actual_count = len(test_cases)
            count_ok = actual_count == expected_count
            
            # Check structure
            structure_ok = True
            for tc in test_cases:
                if not all(k in tc for k in ["case_id", "name", "description", "sequence"]):
                    structure_ok = False
                    break
            
            status = "OK" if (count_ok and structure_ok) else "ISSUES"
            issues = []
            if not count_ok:
                issues.append(f"count mismatch: expected {expected_count}, got {actual_count}")
            if not structure_ok:
                issues.append("structure issues")
            
            results["test_suites"][f"{module_name}.{var_name}"] = {
                "status": status,
                "count": actual_count,
                "issues": issues if issues else None
            }
            
            if not count_ok or not structure_ok:
                results["passed"] = False
                
        except Exception as e:
            results["test_suites"][f"{module_name}.{var_name}"] = {
                "status": "FAILED",
                "error": str(e)
            }
            results["passed"] = False
    
    return results


def run_mock_tests() -> Dict[str, Any]:
    """Run quick mock tests to verify basic functionality."""
    results = {
        "test": "mock_functionality_tests",
        "passed": True,
        "tests": {}
    }
    
    try:
        # Test DifferentialOracle instantiation
        from oracles.differential import DifferentialOracle, R4LifecycleOracle, R6ConsistencyOracle
        
        oracle = DifferentialOracle(["milvus", "qdrant"])
        results["tests"]["DifferentialOracle instantiation"] = "OK"
        
        r4_oracle = R4LifecycleOracle(["milvus", "qdrant", "weaviate", "pgvector"])
        results["tests"]["R4LifecycleOracle instantiation"] = "OK"
        
        r6_oracle = R6ConsistencyOracle(["milvus", "qdrant", "weaviate", "pgvector"])
        results["tests"]["R6ConsistencyOracle instantiation"] = "OK"
        
        # Test behavior extraction
        from schemas.result import ExecutionResult
        from schemas.common import ObservedOutcome
        
        mock_result = ExecutionResult(
            case_id="test_001",
            run_id="test_run",
            observed_outcome=ObservedOutcome.SUCCESS,
            response={"data": [{"id": 1}, {"id": 2}], "count": 2},
            error_message=None,
            oracle_results=[],
            precondition_pass=True
        )
        
        behavior = oracle._extract_behavior("test_db", mock_result)
        if behavior.database == "test_db" and behavior.result_count == 2:
            results["tests"]["Behavior extraction"] = "OK"
        else:
            results["tests"]["Behavior extraction"] = "FAILED: unexpected behavior values"
            results["passed"] = False
        
    except Exception as e:
        results["tests"]["mock_tests"] = f"FAILED: {e}"
        results["passed"] = False
    
    return results


def run_all_validations() -> Dict[str, Any]:
    """Run all validation tests."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    
    all_results = {
        "validation_run_id": f"layer-i-validation-{timestamp}",
        "timestamp": timestamp,
        "validations": [],
        "summary": {}
    }
    
    # Run all validation tests
    validations = [
        validate_imports(),
        validate_file_structure(),
        validate_oracle_implementation(),
        validate_script_interfaces(),
        validate_test_case_definitions(),
        run_mock_tests()
    ]
    
    all_results["validations"] = validations
    
    # Generate summary
    total_tests = len(validations)
    passed_tests = sum(1 for v in validations if v.get("passed", False))
    failed_tests = total_tests - passed_tests
    
    all_results["summary"] = {
        "total_tests": total_tests,
        "passed": passed_tests,
        "failed": failed_tests,
        "success_rate": passed_tests / total_tests if total_tests > 0 else 0
    }
    
    all_results["overall_passed"] = failed_tests == 0
    
    return all_results


def main():
    parser = argparse.ArgumentParser(
        description="Validate Layer I extensions"
    )
    parser.add_argument(
        "--output",
        help="Output file for validation results (JSON)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed results"
    )
    
    args = parser.parse_args()
    
    print("="*70)
    print("Layer I Extension Validation")
    print("="*70)
    print("")
    
    results = run_all_validations()
    
    # Print results
    if args.verbose:
        print(json.dumps(results, indent=2))
    else:
        print("Validation Results:")
        print("-"*70)
        for validation in results["validations"]:
            status = "PASS" if validation.get("passed") else "FAIL"
            print(f"  [{status}] {validation['test']}")
        print("-"*70)
    
    # Print summary
    summary = results["summary"]
    print("")
    print("Summary:")
    print(f"  Total tests: {summary['total_tests']}")
    print(f"  Passed: {summary['passed']}")
    print(f"  Failed: {summary['failed']}")
    print(f"  Success rate: {summary['success_rate']:.1%}")
    print("")
    
    if results["overall_passed"]:
        print("All validations PASSED")
    else:
        print("Some validations FAILED - see details above")
    
    # Write output if requested
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"")
        print(f"Results written to: {output_path}")
    
    return 0 if results["overall_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
