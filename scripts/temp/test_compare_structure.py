"""Test compare workflow structure without requiring actual databases."""

import sys
import json
import tempfile
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Test 1: Verify imports work
print("Test 1: Verifying imports...")
try:
    from ai_db_qa.workflows.compare import (
        run_compare,
        _load_compare_config,
        _analyze_differential,
        _interpret_label,
        _save_differential_artifacts
    )
    print("✓ All compare workflow functions imported successfully")
except ImportError as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

# Test 2: Verify enhanced analyze_differential_results.py exports
print("\nTest 2: Verifying enhanced analyze_differential_results.py...")
try:
    from scripts.analyze_differential_results import (
        compare_outcomes,
        label_differences,
        identify_stricter_database
    )
    print("✓ New differential functions available")
except ImportError as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

# Test 3: Verify _interpret_label function
print("\nTest 3: Testing _interpret_label function...")
db_names = ['milvus', 'seekdb']

# Test db1_stricter (milvus stricter)
result = _interpret_label('db1_stricter', db_names)
expected = "Milvus rejects, Seekdb accepts (stricter)"
assert result == expected, f"Expected '{expected}', got '{result}'"
print(f"✓ db1_stricter interpretation: {result}")

# Test db2_stricter (seekdb stricter)
result = _interpret_label('db2_stricter', db_names)
expected = "Seekdb rejects, Milvus accepts (stricter)"
assert result == expected, f"Expected '{expected}', got '{result}'"
print(f"✓ db2_stricter interpretation: {result}")

# Test oracle_difference
result = _interpret_label('oracle_difference', db_names)
expected = "Different oracle results"
assert result == expected, f"Expected '{expected}', got '{result}'"
print(f"✓ oracle_difference interpretation: {result}")

# Test 4: Verify label_differences function
print("\nTest 4: Testing label_differences function...")

# Create mock result objects
class MockOutcome:
    def __init__(self, value):
        self.value = value

class MockTriageResult:
    def __init__(self, final_type):
        self.final_type = final_type

class MockResult:
    def __init__(self, outcome, triage_result=None):
        self.observed_outcome = MockOutcome(outcome)
        self.triage_result = triage_result

class MockCase:
    def __init__(self, case_id):
        self.case_id = case_id

# Test both success
result1 = MockResult("success")
result2 = MockResult("success")
case = MockCase("test_1")
label = label_differences(result1, result2, case)
assert label == "no_difference", f"Expected 'no_difference', got '{label}'"
print("✓ Both success: no_difference")

# Test one success, one failure (db1 stricter)
result1 = MockResult("failure")
result2 = MockResult("success")
label = label_differences(result1, result2, case)
assert label == "db1_stricter", f"Expected 'db1_stricter', got '{label}'"
print("✓ One success, one failure: db1_stricter")

# Test both failure with different oracle results
triage1 = MockTriageResult("type-1")
triage2 = MockTriageResult("type-2")
result1 = MockResult("failure", triage1)
result2 = MockResult("failure", triage2)
label = label_differences(result1, result2, case)
assert label == "oracle_difference", f"Expected 'oracle_difference', got '{label}'"
print("✓ Both failure, different oracles: oracle_difference")

# Test 5: Verify identify_stricter_database function
print("\nTest 5: Testing identify_stricter_database function...")

result = identify_stricter_database(5, 3)
assert result == "milvus", f"Expected 'milvus', got '{result}'"
print(f"✓ Milvus stricter (5 vs 3): {result}")

result = identify_stricter_database(2, 7)
assert result == "seekdb", f"Expected 'seekdb', got '{result}'"
print(f"✓ Seekdb stricter (2 vs 7): {result}")

result = identify_stricter_database(4, 4)
assert result == "none", f"Expected 'none', got '{result}'"
print(f"✓ Equal strictness (4 vs 4): {result}")

# Test 6: Verify _save_differential_artifacts creates correct files
print("\nTest 6: Testing differential artifact saving...")
with tempfile.TemporaryDirectory() as tmpdir:
    output_dir = Path(tmpdir)

    details = {
        'total_cases': 10,
        'genuine_difference_count': 2,
        'stricter_db': 'milvus',
        'genuine_differences': [
            {
                'case_id': 'test_1',
                'difference_type': 'db1_stricter',
                'milvus_outcome': 'failure',
                'seekdb_outcome': 'success',
                'interpretation': 'Milvus rejects, Seekdb accepts (stricter)'
            }
        ],
        'milvus_strict_count': 5,
        'seekdb_strict_count': 3
    }

    config = {
        'databases': [
            {'type': 'milvus', 'host': 'localhost', 'port': 19530},
            {'type': 'seekdb', 'host': 'localhost', 'port': 2881}
        ],
        '_campaign_path': 'test_campaign.yaml'
    }

    _save_differential_artifacts(details, output_dir, "test", "20260308_120000", config, ["MilvusAdapter", "SeekDBAdapter"])

    # Verify files exist
    assert (output_dir / "differential_details.json").exists(), "differential_details.json not created"
    assert (output_dir / "differential_report.md").exists(), "differential_report.md not created"
    assert (output_dir / "comparison_metadata.json").exists(), "comparison_metadata.json not created"

    # Verify JSON content
    with open(output_dir / "differential_details.json", "r") as f:
        saved_details = json.load(f)
    assert saved_details['total_cases'] == 10, "Total cases mismatch"
    assert saved_details['genuine_difference_count'] == 2, "Difference count mismatch"

    # Verify metadata content
    with open(output_dir / "comparison_metadata.json", "r") as f:
        metadata = json.load(f)
    assert metadata['workflow_type'] == "compare", "Workflow type mismatch"
    assert metadata['tool_version'] == "0.1.0", "Tool version mismatch"

    print("✓ All 3 differential artifacts created successfully")
    print(f"  - differential_details.json ({saved_details['total_cases']} cases, {saved_details['genuine_difference_count']} differences)")
    print(f"  - differential_report.md")
    print(f"  - comparison_metadata.json ({metadata['workflow_type']} workflow)")

print("\n" + "="*60)
print("All structure tests passed! ✓")
print("="*60)
print("\nThe compare workflow implementation is structurally sound.")
print("Full end-to-end testing requires running databases (milvus + seekdb).")
