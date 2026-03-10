# Next Session: Real R3 Execution Plan

**Plan Date**: 2026-03-09
**Target**: Execute real R3 sequence/state-based campaign against live Milvus
**Prerequisites**: Milvus environment running, connection verified

---

## Overview

This document provides the exact step-by-step plan for executing the real R3 campaign. The R3 framework has been implemented and validated via mock dry-run. The next session must execute against real Milvus with full environment transparency.

**CRITICAL**: This is NOT a framework validation - this is the REAL database campaign.

---

## Pre-Execution Checklist

Before starting, verify:

- [ ] Milvus Docker container is running
- [ ] Milvus health endpoint responds
- [ ] pymilvus can connect to Milvus
- [ ] Working directory is correct: `C:\Users\11428\Desktop\ai-db-qc`
- [ ] Python environment has required dependencies
- [ ] Sufficient disk space for results (~100MB)

---

## Step 1: Start Milvus Environment

### Option A: Docker (Recommended)

```bash
# Pull latest Milvus image (if not already available)
docker pull milvusdb/milvus:latest

# Start Milvus container
docker run -d \
  --name milvus-standalone \
  -p 19530:19530 \
  -p 9091:9091 \
  -v /dev/shm/milvus:/dev/shm/milvus \
  milvusdb/milvus:latest

# Verify container is running
docker ps | grep milvus
```

**Expected Output**: Container listing showing milvus-standalone with status "Up"

### Option B: Native Installation

If Milvus is installed natively:

```bash
# Start Milvus service
sudo systemctl start milvus

# Verify service is running
sudo systemctl status milvus
```

**Expected Output**: Service status showing "active (running)"

---

## Step 2: Verify Container Status

```bash
docker ps | grep milvus
```

**Expected Output**:
```
CONTAINER ID   IMAGE                    STATUS          PORTS                      NAMES
abc123def456   milvusdb/milvus:latest   Up 2 minutes    0.0.0.0:19530->19530/tcp   milvus-standalone
```

**Troubleshooting**:
- If no output: Container not running - go back to Step 1
- If container exists but not "Up": `docker start milvus-standalone`

---

## Step 3: Verify Health Endpoint

```bash
curl http://localhost:19530/health
```

**Expected Output**: JSON response indicating healthy status

**Example**:
```json
{"status":"ok"}
```

**Troubleshooting**:
- If connection refused: Milvus not running - check Step 2
- If timeout: Milvus starting up - wait 30 seconds and retry

---

## Step 4: Verify pymilvus Connection

Create and run a quick verification script:

```bash
cd C:\Users\11428\Desktop\ai-db-qc

python -c "
from pymilvus import connections, utility
try:
    connections.connect('default', host='localhost', port='19530')
    print('✓ Connected to Milvus successfully')

    # List collections (should be empty or list existing)
    collections = utility.list_collections()
    print(f'✓ Collections found: {len(collections)}')

    # Get Milvus version info
    print('✓ Connection verified - ready for R3 execution')

except Exception as e:
    print(f'✗ Connection failed: {e}')
    exit(1)
finally:
    connections.disconnect('default')
"
```

**Expected Output**:
```
✓ Connected to Milvus successfully
✓ Collections found: 0
✓ Connection verified - ready for R3 execution
```

**Troubleshooting**:
- If connection fails: Check Milvus is running (Step 2)
- If import error: Install pymilvus: `pip install pymilvus`

---

## Step 5: Run R3 with Enforcement

### Execute Real R3 Campaign

```bash
cd C:\Users\11428\Desktop\ai-db-qc

python scripts/run_r3_sequence.py \
    --adapter milvus \
    --host localhost \
    --port 19530 \
    --require-real \
    --run-tag r3-real-execution \
    --output-dir results
```

**Flag Explanations**:
- `--adapter milvus`: Use real Milvus adapter
- `--host localhost`: Milvus host
- `--port 19530`: Milvus port
- `--require-real`: **CRITICAL** - Abort if Milvus connection fails (no silent fallback)
- `--run-tag`: Unique identifier for this run
- `--output-dir`: Directory for results

**Expected Output**:

```
=== R3 Sequence/State-Based Campaign ===
Run ID: r3-sequence-r3-real-execution-YYYYMMDD-HHMMSS
Adapter: milvus
Templates: casegen/templates/r3_sequence_state.yaml

=== ENVIRONMENT SETUP ===
Target: Milvus at localhost:19530

Attempting connection to Milvus at localhost:19530...
✓ Successfully connected to Milvus
✓ Health check passed

=== ADAPTER STATUS ===
Adapter Type: milvus

Loading sequence templates...
Loaded 11 sequence templates

Executing sequence cases...
  Executing: seq-001 - Duplicate Delete Idempotency
    Status: success
  [... remaining cases ...]

Performing post-run review...
Cases reviewed: 11
...

=== Summary ===
Run ID: r3-sequence-r3-real-execution-YYYYMMDD-HHMMSS
Adapter Requested: milvus
Adapter Actual: milvus
Total cases: 11
...
```

**Critical Validation Points**:

1. **Must see**: "✓ Successfully connected to Milvus"
2. **Must see**: "Adapter Actual: milvus" (NOT "mock")
3. **Must NOT see**: "FALLBACK to mock adapter"
4. **Must see**: Real Milvus responses (not mock data)

---

## Step 6: Verify Metadata

After execution completes, verify the metadata file:

```bash
cd C:\Users\11428\Desktop\ai-db-qc

# Find the most recent run
LATEST_RUN=$(ls -t results/ | head -1)
echo "Latest run: $LATEST_RUN"

# Check metadata
cat "results/$LATEST_RUN/metadata.json" | grep -E "(adapter_requested|adapter_actual|is_real_database_run)"
```

**Expected Output**:
```json
"adapter_requested": "milvus",
"adapter_actual": "milvus",
"is_real_database_run": true
```

**Validation Checklist**:
- [ ] `adapter_requested` = "milvus"
- [ ] `adapter_actual` = "milvus"
- [ ] `is_real_database_run` = true
- [ ] `require_real_flag` = true

**If any of these are false**: Run was not a real database campaign - do not claim findings.

---

## Step 7: Run Post-Run Review

### Review Execution Results

```bash
cd C:\Users\11428\Desktop\ai-db-qc

# Read post-run review
LATEST_RUN=$(ls -t results/ | head -1)
cat "results/$LATEST_RUN/post_run_review.json"
```

### Key Review Questions

For each primary case (seq-001 through seq-006):

1. **Was the case validly exercised?**
   - Check `validly_exercised: true`
   - Verify all steps executed

2. **Did it test the intended state property?**
   - Check `state_property` description
   - Verify sequence matches design

3. **Was behavior masked by other issues?**
   - Check for unexpected errors in early steps
   - Verify state transitions occurred as expected

4. **Is the behavior a bug, documented, or observation?**
   - Check `classification` field
   - Verify `reasoning` is sound

### Classification Guidelines

| Classification | Criteria |
|----------------|----------|
| **issue_ready** | Clear anomaly vs. expected behavior, reproducible |
| **observation** | State property tested, no anomaly found |
| **calibration** | Known-good path or documented behavior verified |
| **exploratory** | Edge case documented, behavior uncertain |

### Minimum Success Criteria

**Minimum Success**: ≥1 of the following:
- Primary case classified as "issue_ready"
- All 6 primary cases validly exercised with observations

**Stretch Success**: ≥2 issue_ready findings

---

## Execution Verification Summary

After completing all steps, verify:

| Step | Verification | Status |
|------|---------------|--------|
| 1. Milvus running | `docker ps \| grep milvus` shows "Up" | [ ] |
| 2. Container status | Container listing shows milvus-standalone | [ ] |
| 3. Health endpoint | `curl` returns healthy status | [ ] |
| 4. pymilvus connection | Script prints "✓ Connected" | [ ] |
| 5. R3 execution | Output shows "Adapter Actual: milvus" | [ ] |
| 6. Metadata verification | `is_real_database_run: true` | [ ] |
| 7. Post-run review | All primary cases validly exercised | [ ] |

**ALL steps must pass for this to be a valid real R3 campaign.**

---

## Troubleshooting Guide

### Issue: "docker: command not found"

**Solution**: Docker not installed or not in PATH
- Install Docker Desktop for Windows
- Add Docker to system PATH
- Restart terminal

### Issue: "Connection refused" on curl

**Solution**: Milvus not running or wrong port
- Check `docker ps` - is Milvus container running?
- Check port mapping: `-p 19530:19530`
- Wait 30 seconds for Milvus to fully start

### Issue: "pymilvus import error"

**Solution**: pymilvus not installed

```bash
pip install pymilvus
```

### Issue: "Milvus connection failed" in script

**Solution**: Connection parameters incorrect or Milvus not ready
- Verify host: `localhost`
- Verify port: `19530`
- Check firewall settings
- Ensure Milvus is fully started (wait 30-60 seconds)

### Issue: Script says "FALLBACK to mock adapter"

**Solution**: `--require-real` flag not used or connection failed

**CRITICAL**: If you see this message, the run is NOT valid:
- Check that `--require-real` flag was used
- If connection fails with `--require-real`, script will abort
- Do NOT continue if fallback occurs

---

## Expected Results (Real R3)

### Success Indicators

1. **Environment**: All 7 verification steps pass
2. **Execution**: All 11 sequences execute
3. **Adapter**: Metadata shows `is_real_database_run: true`
4. **Cases**: All 6 primary cases validly exercised
5. **Findings**: ≥1 issue-ready OR all primary cases produce observations

### Evidence Files

After successful execution, expect:

```
results/r3-sequence-r3-real-execution-YYYYMMDD-HHMMSS/
├── metadata.json              # Run metadata (verify: is_real_database_run=true)
├── execution_results.json     # All step results with real Milvus responses
├── post_run_review.json       # Classification and review
└── [Additional evidence files]
```

---

## Post-Execution Actions

### 1. Verify Real Execution

```bash
# Quick check
grep "is_real_database_run" results/*/metadata.json | tail -1
```

**Expected**: `"is_real_database_run": true`

### 2. Document Findings

Create `docs/R3_REAL_EXECUTION_REPORT.md` with:
- Per-case outcomes
- Issue-ready candidates (if any)
- Observations and calibration results
- Minimum success criteria assessment

### 3. Update Status Documents

Update:
- `docs/NEXT_SESSION_START_HERE.md` - Mark R3 as complete
- `docs/R3_DECISION_STATUS.md` - Record real execution results

### 4. Archive Evidence

Ensure all result files are preserved:
- Copy to backup location if needed
- Verify file integrity
- Document run ID in checkpoint

---

## Critical Reminders

### DO NOT

- ❌ Run without `--require-real` flag
- ❌ Accept results if `adapter_actual: "mock"`
- ❌ Claim findings from mock execution
- ❌ Skip environment verification steps

### DO

- ✅ Verify Milvus is running before starting
- ✅ Use `--require-real` flag
- ✅ Check metadata shows `is_real_database_run: true`
- ✅ Review all primary cases for proper classification
- ✅ Only claim issue-ready findings from real Milvus behavior

---

## Session Success Criteria

The next session is successful when:

1. **Environment**: Milvus confirmed running (Steps 1-4 pass)
2. **Execution**: R3 runs with real Milvus (Step 5 passes)
3. **Verification**: Metadata confirms real database run (Step 6 passes)
4. **Review**: Post-run analysis completed (Step 7 passes)
5. **Documentation**: Real execution report created

**ALL criteria must be met for this to be a valid real R3 campaign.**

---

## Quick Reference Command

**Single command to execute real R3 (after Milvus is running)**:

```bash
cd C:\Users\11428\Desktop\ai-db-qc && \
python scripts/run_r3_sequence.py \
    --adapter milvus \
    --host localhost \
    --port 19530 \
    --require-real \
    --run-tag r3-real-execution \
    --output-dir results
```

---

**END OF NEXT SESSION EXECUTION PLAN**
