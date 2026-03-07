# Phase 5 Experiments - Interpretability Validation

## Experiment Overview

Phase 5 validates the semantic framework's interpretability advantages through systematic ablation and comparison studies. These experiments measure the impact of precondition gates, semantic oracles, and diagnostic triage on mining effectiveness and output quality.

**Experiment Count:** 6 runs
**Focus:** Interpretability, ablation analysis, mock vs real adapters
**Duration:** March 2026
**Status:** Completed

## Experiment Matrix

| Run Tag | Adapter | Gate | Oracle | Triage | Purpose |
|---------|---------|------|--------|--------|---------|
| `baseline_real_runA` | milvus | on | on | diagnostic | Main baseline with all features |
| `baseline_real_runB` | milvus | on | on | diagnostic | Stability verification run |
| `no_gate_real` | milvus | off | on | diagnostic | Gate ablation - precondition impact |
| `no_oracle_real` | milvus | on | off | diagnostic | Oracle ablation - validation impact |
| `naive_triage_real` | milvus | on | on | naive | Triage comparison - diagnostic vs naive |
| `baseline_mock` | mock | on | on | diagnostic | Mock vs real adapter comparison |

### Key Hypotheses

1. **Gate Impact:** Disabling precondition gates will increase false positives from invalid inputs
2. **Oracle Impact:** Disabling semantic oracles will reduce bug classification accuracy
3. **Triage Impact:** Naive triage will have higher false positive rates than diagnostic triage
4. **Adapter Impact:** Mock adapter will show higher false positive rates than Milvus

## Running the Experiments

### Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys and Milvus configuration

# Verify Milvus connectivity
python -c "from adapters.milvus_adapter import MilvusAdapter; print('Milvus ready')"
```

### Environment Limitations

**Milvus Fallback:** If Milvus is unavailable, experiments will automatically fall back to the mock adapter. This is intentional for reproducibility but limits semantic validation capabilities.

### Run Commands

#### Baseline Run A (Main Baseline)
```bash
python Desktop/SemanticBugMiningFramework/mining_run_v022_real.py \
  --adapter milvus \
  --test-cases 100 \
  --tag baseline_real_runA \
  --timeout 300
```

#### Baseline Run B (Stability Verification)
```bash
python Desktop/SemanticBugMiningFramework/mining_run_v022_real.py \
  --adapter milvus \
  --test-cases 100 \
  --tag baseline_real_runB \
  --timeout 300
```

#### No Gate Run (Precondition Ablation)
```bash
python Desktop/SemanticBugMiningFramework/mining_run_v022_real.py \
  --adapter milvus \
  --no-gate \
  --test-cases 100 \
  --tag no_gate_real \
  --timeout 300
```

#### No Oracle Run (Validation Ablation)
```bash
python Desktop/SemanticBugMiningFramework/mining_run_v022_real.py \
  --adapter milvus \
  --no-oracle \
  --test-cases 100 \
  --tag no_oracle_real \
  --timeout 300
```

#### Naive Triage Run (Triage Comparison)
```bash
python Desktop/SemanticBugMiningFramework/mining_run_v022_real.py \
  --adapter milvus \
  --naive-triage \
  --test-cases 100 \
  --tag naive_triage_real \
  --timeout 300
```

#### Baseline Mock Run (Mock vs Real)
```bash
python Desktop/SemanticBugMiningFramework/mining_run_v022_real.py \
  --adapter mock \
  --test-cases 100 \
  --tag baseline_mock \
  --timeout 300
```

### Parallel Execution

For faster execution, runs can be parallelized:
```bash
# Run baseline experiments in parallel
python Desktop/SemanticBugMiningFramework/mining_run_v022_real.py --adapter milvus --test-cases 100 --tag baseline_real_runA &
python Desktop/SemanticBugMiningFramework/mining_run_v022_real.py --adapter milvus --test-cases 100 --tag baseline_realB &
wait
```

## Variant Definitions

### `--no-gate`
Disables the precondition gate, allowing semantically invalid test cases to proceed to execution. This tests the gate's effectiveness in filtering nonsense inputs.

**Expected Impact:** Higher false positive rate, increased execution time on invalid inputs

### `--no-oracle`
Disables semantic oracle validation, treating all unexpected behaviors as potential bugs. This tests the oracle's effectiveness in distinguishing bugs from expected behaviors.

**Expected Impact:** Higher false positive rate, manual verification burden

### `--naive-triage`
Uses naive keyword-based triage instead of diagnostic triage. Naive triage uses simple pattern matching while diagnostic triage performs semantic analysis of failure contexts.

**Expected Impact:** Higher false negative rate, missed edge cases

### `--adapter mock`
Uses the deterministic mock adapter instead of Milvus semantic search. Mock adapter provides consistent results for testing but lacks semantic understanding.

**Expected Impact:** Higher false positive rate, limited semantic validation

## Evidence Artifacts

Each run generates a directory in `Desktop/SemanticBugMiningFramework/runs/` containing:

### Run Structure
```
runs/<run_tag>/
├── metadata.json              # Run configuration and timestamps
├── test_cases.json            # Generated test cases
├── execution_results.json     # Execution outcomes
├── oracle_reports.json        # Validation results
├── triage_results.json        # Triage classifications
├── summary_report.json        # Aggregated metrics
└── logs/
    ├── execution.log          # Detailed execution logs
    ├── oracle.log             # Oracle validation logs
    └── triage.log             # Triage decision logs
```

### Key Metrics in `summary_report.json`

```json
{
  "total_test_cases": 100,
  "executed_cases": 95,
  "blocked_by_gate": 5,
  "unexpected_behaviors": 23,
  "confirmed_bugs": 12,
  "false_positives": 8,
  "false_negatives": 3,
  "precision": 0.60,
  "recall": 0.80,
  "f1_score": 0.69,
  "execution_time_seconds": 245.3
}
```

## Analysis Outputs

### Summary Comparison

After all runs complete, generate comparative analysis:

```python
# Generate comparison table
python Desktop/SemanticBugMiningFramework/scripts/analyze_phase5.py \
  --runs baseline_real_runA baseline_real_runB no_gate_real no_oracle_real naive_triage_real baseline_mock \
  --output analysis/phase5_comparison.json
```

### Key Comparison Metrics

| Metric | Baseline | No Gate | No Oracle | Naive Triage | Mock |
|--------|----------|---------|-----------|--------------|------|
| Precision | ? | Lower | Lower | Similar | Lower |
| Recall | ? | Similar | Lower | Lower | Similar |
| F1 Score | ? | Lower | Lower | Lower | Lower |
| False Positives | ? | Higher | Higher | Similar | Higher |
| Execution Time | ? | Higher | Similar | Similar | Lower |

### Case Studies

#### Gate Effectiveness
Compare `baseline_real_runA` vs `no_gate_real`:
- Count test cases blocked by gate in baseline
- Measure false positives from unblocked invalid cases in no-gate run
- Calculate precision improvement from gating

#### Oracle Effectiveness
Compare `baseline_real_runA` vs `no_oracle_real`:
- Count confirmed bugs vs total unexpected behaviors
- Measure manual verification effort in no-oracle run
- Calculate precision improvement from oracles

#### Triage Comparison
Compare `baseline_real_runA` vs `naive_triage_real`:
- Count edge cases identified by diagnostic triage
- Measure false negative rate in naive triage
- Analyze semantic understanding benefits

#### Mock vs Real
Compare `baseline_real_runA` vs `baseline_mock`:
- Measure semantic search precision impact
- Analyze false positive patterns
- Calculate improvement from Milvus adapter

## Expected Outcomes

### Gate Effects
- **Baseline:** ~5-10% of test cases blocked by precondition gate
- **No Gate:** 2-3x increase in false positives from invalid inputs
- **Precision:** 10-15% improvement with gate enabled

### Oracle Effects
- **Baseline:** ~50-60% of unexpected behaviors confirmed as bugs
- **No Oracle:** 100% of unexpected behaviors require manual verification
- **Precision:** 20-30% improvement with oracle enabled

### Triage Effects
- **Diagnostic:** Identifies edge cases through semantic analysis
- **Naive:** Misses 10-20% of subtle bugs due to keyword limitations
- **Recall:** 5-10% improvement with diagnostic triage

### Mock vs Real Adapter
- **Milvus:** Semantic similarity reduces false positives by ~30%
- **Mock:** Deterministic but lacks semantic understanding
- **Overall F1:** 15-25% improvement with Milvus adapter

## Troubleshooting

### Common Issues

#### Milvus Connection Failed
**Symptom:** `ConnectionError: Failed to connect to Milvus`

**Solution:**
```bash
# Check Milvus status
docker ps | grep milvus

# Restart Milvus if needed
docker-compose restart milvus

# Or use mock adapter
python mining_run_v022_real.py --adapter mock --tag baseline_mock
```

#### Timeout During Execution
**Symptom:** Test execution exceeds 300 seconds

**Solution:**
```bash
# Increase timeout
python mining_run_v022_real.py --timeout 600 --tag baseline_real_runA

# Or reduce test cases
python mining_run_v022_real.py --test-cases 50 --tag baseline_real_runA
```

#### Memory Issues
**Symptom:** `MemoryError: Unable to allocate array`

**Solution:**
```bash
# Reduce batch size
export BATCH_SIZE=10
python mining_run_v022_real.py --test-cases 50
```

#### Missing Run Directories
**Symptom:** Run directory not created or empty

**Solution:**
```bash
# Check permissions
ls -la Desktop/SemanticBugMiningFramework/runs/

# Verify configuration
python -c "import json; print(json.load(open('.env')))"

# Re-run with verbose logging
python mining_run_v022_real.py --verbose --tag baseline_real_runA
```

### Verification

After each run, verify completion:
```bash
# Check run directory exists
ls Desktop/SemanticBugMiningFramework/runs/<run_tag>/

# Verify key files present
ls Desktop/SemanticBugMiningFramework/runs/<run_tag>/*.json

# Check for errors
grep -i "error" Desktop/SemanticBugMiningFramework/runs/<run_tag>/logs/*.log
```

## References

- **Main Framework:** `Desktop/SemanticBugMiningFramework/`
- **Execution Script:** `mining_run_v022_real.py`
- **Adapters:** `adapters/milvus_adapter.py`, `adapters/mock_adapter.py`
- **Oracles:** `oracle/semantic_oracle.py`
- **Triage:** `reporting/diagnostic_triage.py`
- **Results:** `runs/*/`

## Next Steps

1. Execute all 6 runs using the commands above
2. Generate comparative analysis using `analyze_phase5.py`
3. Document unexpected behaviors in case studies
4. Update metrics in expected outcomes table
5. Prepare final report with interpretability findings

---

**Experiment Series:** Semantic Bug Mining Framework Phase 5
**Documentation:** `docs/experiments_phase5.md`
**Status:** Ready for execution
**Last Updated:** 2026-03-07
