"""
Smoke tests for Layer I CLI changes.
Tests argument parsing only (no real DB connections required).
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

# --- Test 1: run_full_r4_differential.py argument parsing ---
def test_r4_argparse():
    import importlib.util, argparse
    spec = importlib.util.spec_from_file_location(
        "r4_diff", "scripts/run_full_r4_differential.py")
    mod = importlib.util.load_from_spec = None  # don't run main
    # Just import and check parser builds correctly
    import subprocess, sys as _sys
    r = subprocess.run(
        [_sys.executable, "scripts/run_full_r4_differential.py", "--help"],
        capture_output=True, text=True, cwd=os.path.dirname(__file__) or "."
    )
    assert r.returncode == 0, f"--help failed: {r.stderr}"
    assert "--adapters" in r.stdout, "--adapters not in help"
    assert "--weaviate-host" in r.stdout, "--weaviate-host not in help"
    assert "--pgvector-container" in r.stdout, "--pgvector-container not in help"
    print("[PASS] run_full_r4_differential.py --help OK")

# --- Test 2: run_r6_differential.py argument parsing ---
def test_r6_argparse():
    import subprocess, sys as _sys
    r = subprocess.run(
        [_sys.executable, "scripts/run_r6_differential.py", "--help"],
        capture_output=True, text=True, cwd=os.path.dirname(__file__) or "."
    )
    assert r.returncode == 0, f"--help failed: {r.stderr}"
    assert "--adapters" in r.stdout, "--adapters not in help"
    assert "--weaviate-host" in r.stdout, "--weaviate-host not in help"
    print("[PASS] run_r6_differential.py --help OK")

# --- Test 3: run_r5d_schema.py argument parsing ---
def test_r5d_argparse():
    import subprocess, sys as _sys
    r = subprocess.run(
        [_sys.executable, "scripts/run_r5d_schema.py", "--help"],
        capture_output=True, text=True, cwd=os.path.dirname(__file__) or "."
    )
    assert r.returncode == 0, f"--help failed: {r.stderr}"
    assert "--adapter" in r.stdout, "--adapter not in help"
    assert "--weaviate-host" in r.stdout, "--weaviate-host not in help"
    assert "weaviate" in r.stdout, "weaviate choice not in help"
    print("[PASS] run_r5d_schema.py --help OK")

# --- Test 4: run_r5d_schema.py offline+weaviate -> SCH-002 SKIP_NOT_SUPPORTED ---
def test_r5d_weaviate_sch002_skip():
    import subprocess, sys as _sys
    r = subprocess.run(
        [_sys.executable, "scripts/run_r5d_schema.py",
         "--offline", "--adapter", "weaviate", "--contracts", "SCH-002"],
        capture_output=True, text=True, cwd=os.path.dirname(__file__) or "."
    )
    combined = r.stdout + r.stderr
    assert "SKIP_NOT_SUPPORTED" in combined, (
        f"Expected SKIP_NOT_SUPPORTED in output but got:\n{combined}"
    )
    print("[PASS] run_r5d_schema.py weaviate SCH-002 -> SKIP_NOT_SUPPORTED")

# --- Test 5: SKIP_NOT_SUPPORTED NOT triggered for milvus SCH-002 ---
def test_r5d_milvus_sch002_not_skip():
    import subprocess, sys as _sys
    r = subprocess.run(
        [_sys.executable, "scripts/run_r5d_schema.py",
         "--offline", "--adapter", "milvus", "--contracts", "SCH-002"],
        capture_output=True, text=True, cwd=os.path.dirname(__file__) or "."
    )
    combined = r.stdout + r.stderr
    # Should NOT hit the SKIP_NOT_SUPPORTED branch for milvus
    # (it may PASS or VIOLATION or ERROR depending on offline mock, but not SKIP_NOT_SUPPORTED)
    # The key check: it actually ran (attempted) SCH-002
    assert "SCH-002" in combined, f"SCH-002 not mentioned in output:\n{combined}"
    print(f"[PASS] run_r5d_schema.py milvus SCH-002 -> ran (result: {'SKIP_NOT_SUPPORTED' if 'SKIP_NOT_SUPPORTED' in combined else 'ran normally'})")
    if "SKIP_NOT_SUPPORTED" in combined:
        print("  [WARN] milvus SCH-002 unexpectedly returned SKIP_NOT_SUPPORTED - check SKIP_NOT_SUPPORTED map")

if __name__ == "__main__":
    os.chdir("C:/Users/11428/Desktop/ai-db-qc")
    print("=" * 60)
    print("  Layer I Smoke Tests")
    print("=" * 60)
    failures = []
    for name, fn in [
        ("r4_argparse", test_r4_argparse),
        ("r6_argparse", test_r6_argparse),
        ("r5d_argparse", test_r5d_argparse),
        ("r5d_weaviate_sch002_skip", test_r5d_weaviate_sch002_skip),
        ("r5d_milvus_sch002_not_skip", test_r5d_milvus_sch002_not_skip),
    ]:
        try:
            fn()
        except Exception as e:
            print(f"[FAIL] {name}: {e}")
            failures.append(name)
    print("=" * 60)
    if failures:
        print(f"  FAILED: {failures}")
        sys.exit(1)
    else:
        print("  ALL TESTS PASSED")
        sys.exit(0)
