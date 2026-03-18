import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

print("Testing imports...")

try:
    from oracles.differential import DifferentialOracle
    print("DifferentialOracle: OK")
except Exception as e:
    print(f"DifferentialOracle: FAILED - {e}")

try:
    from oracles.differential import R4LifecycleOracle
    print("R4LifecycleOracle: OK")
except Exception as e:
    print(f"R4LifecycleOracle: FAILED - {e}")

try:
    from oracles.differential import R6ConsistencyOracle
    print("R6ConsistencyOracle: OK")
except Exception as e:
    print(f"R6ConsistencyOracle: FAILED - {e}")

print("\nAll imports completed!")
