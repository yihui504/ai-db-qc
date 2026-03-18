import subprocess, sys, os

r = subprocess.run(
    [sys.executable, "smoke_layer_i.py"],
    cwd="C:/Users/11428/Desktop/ai-db-qc",
    capture_output=True, text=True
)
print("STDOUT:")
print(r.stdout)
print("STDERR:")
print(r.stderr[-2000:] if len(r.stderr) > 2000 else r.stderr)
print("EXIT:", r.returncode)
