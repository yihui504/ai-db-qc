# Comparison Tables

## Table 1: Main Configuration Comparison

| Run | Total | Precond Pass | Failures | T1 | T2 | T2.PF | T3 | T4 | Non-bug | Oracle Fail |
|---|---|---|---|---|---|---|---|---|---|---|
| baseline_mock | 4 | 2 | 0 | 1 | 0 | 2 | 0 | 0 | 1 | 0 |
| baseline_real | 4 | 2 | 4 | 0 | 1 | 2 | 1 | 0 | 0 | 0 |
| naive_triage_real | 4 | 2 | 4 | 0 | 1 | 2 | 1 | 0 | 0 | 0 |
| no_gate_mock | 4 | 2 | 0 | 1 | 0 | 2 | 0 | 0 | 1 | 0 |
| no_gate_real | 4 | 2 | 4 | 0 | 1 | 2 | 1 | 0 | 0 | 0 |
| no_oracle_real | 4 | 2 | 4 | 0 | 1 | 2 | 1 | 0 | 0 | 0 |

## Table 2: Gate Effect Comparison
**Comparison:** baseline_real_runA vs no_gate_real

| Metric | baseline_real_runA | no_gate_real |
|---|---|---|
| precondition_fail_count | 2 | 2 |
| type3_count | 1 | 1 |
| type4_count | 0 | 0 |
| type2_precondition_failed_count | 2 | 2 |
| non_bug_count | 0 | 0 |

## Table 3: Oracle Effect Comparison
**Comparison:** baseline_real_runA vs no_oracle_real

| Metric | baseline_real | no_oracle_real |
|---|---|---|
| oracle_eval_count | 4 | 0 |
| oracle_fail_count | 0 | 0 |
| type4_count | 0 | 0 |
| non_bug_count | 0 | 0 |

## Table 4: Triage Effect Comparison
**Comparison:** baseline_real_runA vs naive_triage_real

| Metric | baseline_real | naive_triage_real |
|---|---|---|
| illegal_cases | 0 | 0 |
| observed_failure_count | 4 | 4 |
| type2_count | 1 | 1 |
| non_bug_count | 0 | 0 |
| type2_share_among_illegal_failures | 0.00% | 0.00% |

## Table 5: Mock vs Real Comparison
**Comparison:** baseline_mock vs baseline_real_runA

| Metric | baseline_mock | baseline_real_runA |
|---|---|---|
| total_cases | 4 | 4 |
| precondition_pass_count | 2 | 2 |
| observed_failure_count | 0 | 4 |
| type1_count | 1 | 0 |
| type2_count | 0 | 1 |
| type2_precondition_failed_count | 2 | 2 |
| type3_count | 0 | 1 |
| type4_count | 0 | 0 |
| non_bug_count | 1 | 0 |
