import subprocess, sys
r = subprocess.run(
    [sys.executable, "scripts/run_full_r4_differential.py",
     "--adapters", "mock", "--output-dir", "runs/r4_layer_i_smoke"],
    cwd="C:/Users/11428/Desktop/ai-db-qc",
    capture_output=True, text=True
)
print("=== STDOUT ===")
print(r.stdout[-4000:] if len(r.stdout) > 4000 else r.stdout)
print("=== STDERR ===")
print(r.stderr[-3000:] if len(r.stderr) > 3000 else r.stderr)
print("=== EXIT:", r.returncode, "===")
