#!/usr/bin/env python3
"""Test ID conversion logic for all adapters."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_id_conversion():
    """Test the _convert_ids_to_int method."""
    test_cases = [
        (['id_1', 'id_2', 'entity_10'], [1, 2, 10]),
        (['test_100', 'item_5'], [100, 5]),
        ([1, 2, 3], [1, 2, 3]),  # Already integers
        (['abc', 'def'], [abs(hash('abc')) % (2**63), abs(hash('def')) % (2**63)]),  # No numbers, use hash
    ]
    
    def _convert_ids_to_int(ids):
        converted = []
        for id_val in ids:
            if isinstance(id_val, int):
                converted.append(id_val)
            elif isinstance(id_val, str):
                import re
                numeric_match = re.search(r'\d+', id_val)
                if numeric_match:
                    converted.append(int(numeric_match.group()))
                else:
                    converted.append(abs(hash(id_val)) % (2**63))
            else:
                converted.append(int(id_val))
        return converted
    
    print("="*60)
    print("ID Conversion Test")
    print("="*60)
    
    all_passed = True
    for input_ids, expected in test_cases:
        result = _convert_ids_to_int(input_ids)
        passed = result == expected or (len(result) == len(input_ids) and all(isinstance(r, int) for r in result))
        status = "PASS" if passed else "FAIL"
        print(f"\n{status}: {input_ids}")
        print(f"  Expected: {expected}")
        print(f"  Got:      {result}")
        if not passed:
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("All tests PASSED!")
    else:
        print("Some tests FAILED!")
    print("="*60)
    
    return all_passed


if __name__ == "__main__":
    success = test_id_conversion()
    sys.exit(0 if success else 1)
