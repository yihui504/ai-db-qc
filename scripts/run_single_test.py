"""Run a single database test."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.run_phase5_3_eval import (
    create_adapter_with_fallback,
    create_oracles,
    VariantFlags
)
from casegen.generators.instantiator import load_templates, instantiate_all
from contracts.core.loader import get_default_contract
from pipeline.preconditions import PreconditionEvaluator
from pipeline.executor import Executor
from pipeline.triage import Triage

def test_single_db(db_name):
    print(f"\nTesting {db_name}...")
    try:
        # Create adapter
        adapter, variant_flags, adapter_info = create_adapter_with_fallback(
            adapter_choice=db_name,
            host="localhost",
            port={"milvus": 19530, "qdrant": 6333, "weaviate": 8080, "pgvector": 5432}.get(db_name, 19530),
            require_real=True
        )
        
        if adapter is None:
            print(f"  Failed to create adapter for {db_name}")
            return False
            
        print(f"  Adapter created: {type(adapter).__name__}")
        
        # Load templates
        templates = load_templates("casegen/templates/experimental_triage.yaml")
        cases = instantiate_all(templates, num_samples=2)
        print(f"  Loaded {len(cases)} test cases")
        
        # Create oracles
        contract = get_default_contract()
        oracles = create_oracles(contract, adapter)
        print(f"  Created {len(oracles)} oracles")
        
        # Run a simple test
        variant_flags = VariantFlags()
        gate = PreconditionEvaluator(contract=contract, adapter=adapter)
        
        passed = 0
        for i, case in enumerate(cases[:3]):  # Test first 3 cases
            try:
                # Check preconditions
                gate_result = gate.evaluate(case)
                if not gate_result.passes:
                    continue
                    
                # Execute
                executor = Executor(adapter=adapter)
                exec_result = executor.execute(case)
                
                if exec_result.observed_outcome.value == "PASS":
                    passed += 1
                    
            except Exception as e:
                print(f"    Case {i} error: {e}")
                
        print(f"  Passed: {passed}/{min(3, len(cases))}")
        return True
        
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    databases = ["milvus", "qdrant", "weaviate", "pgvector"]
    
    print("="*60)
    print("Single Database Test")
    print("="*60)
    
    results = {}
    for db in databases:
        results[db] = test_single_db(db)
    
    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    for db, ok in results.items():
        status = "OK" if ok else "FAIL"
        print(f"{db}: {status}")
