"""Quick validation of new oracle imports."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from oracles.recall_quality import RecallQualityOracle
    from oracles.metamorphic import MetamorphicOracle, MetamorphicRelation
    from oracles.sequence_assertion import SequenceAssertionOracle
    print("All oracle imports: OK")
except Exception as e:
    print(f"Oracle import error: {e}")
    sys.exit(1)

try:
    from adapters.base import AdapterBase, OperationNotSupportedError
    from adapters.mock import MockAdapter
    adapter = MockAdapter()
    snapshot = adapter.get_runtime_snapshot()
    ops = adapter.supported_operations()
    print(f"Adapter abstraction: OK (operations: {len(ops)})")
except Exception as e:
    print(f"Adapter abstraction error: {e}")
    sys.exit(1)

print("\nQuick validation: ALL PASSED")
