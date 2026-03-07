# Phase 5 Design: Evaluation and Paper Packaging

> **Goal**: Move from system-building to real evaluation and paper packaging. Run small-scale, evidence-backed, real Milvus experiments and produce structured evaluation outputs, comparison/ablation results, representative case studies, and paper-ready materials.

## Experiment Matrix (6 runs)

| Run Tag | Adapter | Gate | Oracle | Triage | Purpose |
|---------|---------|------|--------|--------|---------|
| baseline_real_runA | milvus | on | on | diagnostic | Main baseline, run 1 |
| baseline_real_runB | milvus | on | on | diagnostic | Main baseline, run 2 (stability) |
| no_gate_real | milvus | off | on | diagnostic | Gate ablation |
| no_oracle_real | milvus | on | off | diagnostic | Oracle ablation |
| naive_triage_real | milvus | on | on | naive | Triage comparison |
| baseline_mock | mock | on | on | diagnostic | Mock vs real comparison |

**Scale**: Minimal - 6 runs total. Prioritize interpretability, artifact quality, and case-study value over volume.

## New Files

### Scripts
- `scripts/run_phase5_eval.py` - Main evaluation runner with variant flags

### Analysis Modules
- `analysis/summarize_runs.py` - Aggregate metrics across runs
- `analysis/build_tables.py` - Generate comparison tables
- `analysis/export_case_studies.py` - Export representative cases

### Config
- `configs/phase5_eval.yaml` - Run configuration (case template, default params)

### Documentation
- `docs/paper_outline.md` - Full paper skeleton
- `docs/experiments_phase5.md` - Experiment setup and reproducibility
- `docs/case_studies.md` - Paper-facing curated case studies
- `docs/limitations.md` - Methodology and evaluation limitations

## Modified Files
- `scripts/run_phase4.py` - Reuse as base for run_phase5_eval.py
- `pipeline/executor.py` - May need minor changes for no-oracle variant
- `pipeline/triage.py` - May need naive triage mode support

## Expected Analysis Outputs

### From summarize_runs.py
- `runs/phase5_summary.json` - Aggregated metrics
- `runs/phase5_summary.md` - Formatted summary

### From build_tables.py
- `runs/comparison_tables.md` - All tables in one markdown file
- `runs/table1_main_comparison.csv` - Main configuration comparison
- `runs/table2_gate_effect.csv` - Gate ablation
- `runs/table3_oracle_effect.csv` - Oracle ablation
- `runs/table4_triage_effect.csv` - Triage comparison
- `runs/table5_mock_vs_real.csv` - Mock vs real comparison

### From export_case_studies.py
- `runs/case_studies.md` - Auto-generated run-level case studies
- `runs/case_studies.json` - (optional) Machine-readable case studies

## Expected Documentation Outputs

### Paper Structure
- `docs/paper_outline.md` - Section-by-section outline with placeholders for contribution narrative

### Experiment Documentation
- `docs/experiments_phase5.md` - Full reproducibility info (setup, commands, artifacts)

### Case Study Documentation
- `docs/case_studies.md` - Paper-facing curated narratives with evidence links

### Limitations Documentation
- `docs/limitations.md` - Methodology and evaluation limitations

## Configuration Control (Command-line Flags)

**Flags for scripts/run_phase5_eval.py:**
- `--adapter {mock,milvus}` - Choose execution backend (default: milvus)
- `--no-gate` - Bypass precondition filtering for Type-3/4 (default: gate on)
- `--no-oracle` - Skip oracle execution (default: oracle on)
- `--naive-triage` - Use naive Type-2 classification (default: diagnostic-aware)
- `--run-tag TAG` - Tag for this run (e.g., baseline_real_runA)
- `--output-dir PATH` - Output directory (default: runs)

**Important:** `--no-gate` means "don't use precondition_pass as hard filter for Type-3/4", not "don't call evaluator". The PreconditionEvaluator still runs and produces GateTrace.

## Variant Definitions

### Naive Type-2 Classification
- **Naive**: illegal + failure → Type-2 (no diagnostic quality inspection)
- **Diagnostic-aware**: illegal + failure + poor diagnostics → Type-2

This isolates the diagnostic quality assessment effect.

### Gate Off
- PreconditionEvaluator still runs and produces GateTrace
- Type-3/4 can still be reported even if precondition_pass=true
- This isolates the gate's filtering effect

### Oracle Off
- Oracle execution is skipped
- Type-4 is not produced from oracle logic
- Other triage types remain functional

## Core Metrics

### Raw Metrics (per run)
1. total_cases
2. total_executed
3. illegal_cases
4. legal_cases
5. precondition_pass_count
6. precondition_fail_count
7. observed_success_count
8. observed_failure_count
9. triage counts:
   - type1_count
   - type2_count
   - type2_precondition_failed_count
   - type3_count
   - type4_count
   - non_bug_count
10. oracle_fail_count
11. oracle_eval_count

### Derived Metrics
1. precondition_pass_rate
2. type2_share_among_illegal_failures
3. type4_share_among_oracle_evaluable_cases
4. non_bug_share
5. gate_filtered_share (= precondition_fail_count / total_cases)

## Required Tables

### Table 1: Main Configuration Comparison
Rows: All 6 run configurations
Columns: total_cases, precondition_pass_count, observed_failure_count, type1_count, type2_count, type2_precondition_failed_count, type3_count, type4_count, non_bug_count, oracle_fail_count

### Table 2: Gate Effect
Compare: baseline_real vs no_gate_real
Focus: precondition_fail_count, type3_count, type4_count, type2_precondition_failed_count, non_bug_count

### Table 3: Oracle Effect
Compare: baseline_real vs no_oracle_real
Focus: oracle_eval_count, oracle_fail_count, type4_count, non_bug_count

### Table 4: Triage Effect
Compare: baseline_real vs naive_triage_real
Focus: illegal_cases, observed_failure_count (illegal), type2_count, non_bug_count, type2_share_among_illegal_failures

### Table 5: Mock vs Real (Optional)
Compare: baseline_mock vs baseline_real
Focus: total_cases, precondition_pass_count, observed_failure_count, type1_count, type2_count, type3_count, type4_count

## Case Studies

### Auto-Generated (runs/case_studies.md)
- At least one representative example per bug type:
  - Type-1
  - Type-2
  - Type-2.PreconditionFailed
  - Type-3
  - Type-4
  - Non-bug / correct rejection

Each includes: run_id, case_id, operation, expected_validity, precondition result, observed outcome, triage result, oracle result, evidence references, short interpretation

### Paper-Facing Curated (docs/case_studies.md)
- Research-facing narratives
- Qualitative interpretation
- Links to evidence artifacts
- Publication-ready language

## Acceptance Criteria

1. **All 6 runs are attempted** - If real Milvus is unavailable, record explicitly as environment limitation
2. **Analysis scripts produce** all expected outputs without errors
3. **Comparison tables show** clear ablation effects (gate, oracle, triage)
4. **Case studies include** at least one example per bug type
5. **Paper docs are publication-oriented** (not internal engineering notes)
6. **No new major infrastructure** - Phase 5 remains minimal and analyzable
7. **All outputs derive from evidence artifacts** - not ad hoc logs

## Key Risks / Tradeoffs

| Risk | Mitigation |
|------|------------|
| Real Milvus connection fails | Use mock as fallback; document limitation explicitly |
| Case set too small for meaningful ablation | Focus on qualitative interpretation, not statistics |
| Naive triage implementation complexity | Keep as simple flag-controlled variant, minimal code changes |
| Table/summary format changes during iteration | Use modular scripts, easy to adjust output format |
| Over-engineering experiment management | Enforce command-line flag approach, no config framework |
| Paper narrative doesn't emerge from results | Design docs around contribution narrative from start |

**Tradeoff**: Scale vs interpretability - Choosing minimal 6-run scale means no statistical significance claims possible. This is acceptable; Phase 5 is about proof-of-concept and case-study value, not benchmarking.

## Implementation Constraints

1. **Type-3 and Type-4 absolutely require precondition_pass=true** in the full method
2. **Adapter must not decide final bug type** - triage remains separate
3. **Summaries and tables must derive from evidence artifacts** - not ad hoc logs
4. **Phase 5 must remain small, analyzable, and publishable**
5. **Do not expand platform complexity**

## Strict Non-Goals

- No second real database
- No multi-database expansion
- No UI/dashboard
- No large benchmark platform
- No complex confirm system
- No LLM generation expansion
- No new major oracle family
