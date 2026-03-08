# Current System → User Task Mapping

**Date**: 2026-03-07
**Purpose**: Show exactly how existing components enable user tasks

---

## Task 1: "Test Milvus for Bugs"

### User Intent

"I want to test the Milvus vector database to find bugs or unexpected behavior."

### Current System Mapping

```
USER TASK                                    CURRENT SYSTEM COMPONENT
┌─────────────────────────────────────────────────────────┐
│ 1. Connect to Milvus database                                  │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│ adapters/milvus_adapter.py                                   │
│ • MilvusAdapter(connection_config)                          │
│ • connect()                                                   │
│ • health_check()                                              │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ 2. Define what to test                                        │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│ casegen/templates/differential_v3_phase1.yaml              │
│ • 6 capability-boundary test cases                         │
│ • Each case has: operation, param_template, rationale     │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ 3. Execute tests and check correctness                       │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│ pipeline/executor.py                                         │
│ • execute_case(case, run_id)                                │
│   - Calls adapter.execute(request)                            │
│   - Returns ExecutionResult                                 │
│                                                             │
│ pipeline/preconditions.py                                   │
│ • PreconditionEvaluator(contract, profile, context)        │
│ • load_runtime_snapshot()                                   │
│ • check_preconditions() → gate_trace                       │
│                                                             │
│ oracles/                                                     │
│ • WriteReadConsistency.validate()                            │
│ • FilterStrictness.validate()                                │
│ • Monotonicity.validate()                                   │
│ → oracle_results                                              │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ 4. Classify outcomes (bug vs non-bug)                       │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│ pipeline/triage.py                                          │
│ • Triage.classify(case, result, naive=False)               │
│ • Returns TriageResult with:                                 │
│   - bug_type (Type-1, Type-2, Type-2.PF, Type-3, Type-4)     │
│   - severity (critical, high, medium, low)                    │
│   - classification (bug, non_bug, unknown)                   │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ 5. Save results                                              │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│ JSONL output (execution_results.jsonl)                     │
│ • Per-case results with:                                   │
│   - case_id, observed_outcome                                │
│   - request, response                                       │
│   - gate_trace, oracle_results                              │
└─────────────────────────────────────────────────────────┘
```

### What's Missing: CLI Wrapper

**Gap**: User needs to write Python script or run multiple scripts manually

**Solution**: Single CLI command
```bash
python -m ai_db_qa validate --db milvus --templates templates/ops.yaml
```

**Implementation**: Wrap above workflow in single entry point

---

## Task 2: "Compare Milvus and seekdb Behavior"

### User Intent

"I want to know how Milvus and seekdb differ in their behavior."

### Current System Mapping

```
USER TASK                                    CURRENT SYSTEM COMPONENT
┌─────────────────────────────────────────────────────────┐
│ 1. Connect to both databases                                    │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│ adapters/milvus_adapter.py                                   │
│ adapters/seekdb_adapter.py                                  │
│ • Parallel connections to both                               │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ 2. Define SHARED test cases                                 │
│ (Same tests run on both databases)                          │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│ casegen/templates/differential_v3_phase1.yaml              │
│ • 6 capability-boundary test cases                         │
│ • Designed to work on BOTH databases                        │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ 3. Run same tests on both databases                          │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│ scripts/run_differential_campaign.py                          │
│ • Setup: create test collection, insert data, build index  │
│ • Loop through cases:                                         │
│   - Run on Milvus adapter                                    │
│   - Run on seekdb adapter                                   │
│ • Collect results separately                                 │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ 4. Compare results per case                                   │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│ scripts/analyze_differential_results.py                      │
│ • Load results from both databases                          │
│ • Compare per case:                                         │
│   - Same outcome → same_behavior                            │
│   - Different outcomes → classify difference                 │
│     • milvus_stricter, seekdb_stricter                        │
│     • Diagnostic quality differences                         │
│ • Aggregate into comparison table                             │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ 5. Generate comparison report                                 │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│ differential_report.md                                         │
│ • Aggregate table (label counts)                             │
│ • Differential case list (per-case comparison)               │
│ • All cases comparison table                                 │
└─────────────────────────────────────────────────────────┘
```

### What's Missing: CLI Wrapper

**Gap**: User needs to:
1. Understand run_differential_campaign.py script
2. Understand analyze_differential_results.py script
3. Manually run both in correct order

**Solution**: Single CLI command
```bash
python -m ai_db_qa compare --databases milvus,seekdb --templates templates/shared.yaml --tag comparison1
```

**Implementation**: Wrap both scripts in unified workflow

---

## Task 3: "Generate Issue Reports for Bugs Found"

### User Intent

"I found bugs in my testing. I want to generate issue reports I can file to the database maintainers."

### Current System Mapping

```
USER TASK                                    CURRENT SYSTEM COMPONENT
┌─────────────────────────────────────────────────────────┐
│ 1. Load test results                                           │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│ runs/differential-v3-phase1-fixed/milvus/execution_results.jsonl│
│ • Contains per-case results with:                             │
│   - observed_outcome (success/failure)                       │
│   - gate_trace (precondition checks)                           │
│   - oracle_results (evidence)                                │
│   - triage_result (classification)                           │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ 2. Filter for bug candidates                                   │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│ Manual filtering (currently):                                  │
│ • Look for Type-1 (illegal succeeded)                         │
│ • Look for Type-2 (poor diagnostic)                          │
│ • Look for Type-2.PF (precondition failed)                   │
│   OR Use diagnostic mode (filters automatically)               │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ 3. Write issue report                                          │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│ docs/issues/issue_001_invalid_metric_type.md               │
│ docs/issues/issue_002_invalid_index_type.md                │
│ docs/issues/issue_003_poor_topk_diagnostic.md               │
│ • Currently written manually                                 │
│ • Structure:                                                 │
│   - Summary                                                  │
│   - Steps to reproduce                                      │
│   - Expected vs Actual                                      │
│   - Impact analysis                                         │
│   - Recommendations                                        │
└─────────────────────────────────────────────────────────┘
```

### What's Missing: Automated Export

**Gap**: Manual filtering and Markdown writing

**Solution**: Export command
```bash
python -m ai_db_qa export --results runs/v3-phase1/ --type issue-report --output issues.md
```

**Implementation**: Automate filtering + formatting

---

## Current System Coverage

### ✅ Fully Implemented (Ready to Wrap)

| Component | File | Purpose | Status |
|-----------|------|---------|--------|
| **Adapter Layer** | `adapters/milvus_adapter.py` | DB connection | ✅ Working |
| **Test Execution** | `pipeline/executor.py` | Run tests | ✅ Working |
| **Preconditions** | `pipeline/preconditions.py` | Validate input/state | ✅ Working |
| **Oracles** | `oracles/` | Verify correctness | ✅ 3 oracles |
| **Triage** | `pipeline/triage.py` | Classify bugs | ✅ Working |
| **Templates** | `casegen/templates/*.yaml` | Test definitions | ✅ 18 cases |
| **Differential Runner** | `scripts/run_differential_campaign.py` | Multi-DB execution | ✅ Working |
| **Differential Analyzer** | `scripts/analyze_differential_results.py` | Compare results | ✅ Working |
| **Result Storage** | `runs/*/execution_results.jsonl` | Evidence storage | ✅ Working |

### ⚠️ Partially Implemented (Needs Integration)

| Component | Current State | Gap |
|-----------|--------------|-----|
| **Result Export** | Manual report writing | Need automation |
| **CLI Entry** | Multiple scripts | Need unification |
| **Documentation** | Research-focused | Need user guides |

### ❌ Not Implemented (Future Work)

| Component | Description | Priority |
|-----------|-------------|----------|
| **LLM Generation** | Auto-generate tests from contracts | Low (templates work) |
| **Report Templates** | Standardized report formats | Medium |
| **Web UI** | Browser-based interface | Low (CLI is fine) |

---

## Minimum Viable Product: What Users Need

### User Journey 1: Bug Hunter

```bash
# 1. Install
pip install ai-db-qa

# 2. Validate database (finds bugs)
ai-db_qa validate --db milvus --templates templates/comprehensive.yaml

# 3. View bugs
cat results/milvus_validation_20260307/BUG_REPORT.md

# 4. (Optional) Report issues
# File the generated bug reports to database maintainers
```

### User Journey 2: Comparison Researcher

```bash
# 1. Install
pip install ai-db-qa

# 2. Compare databases
ai-db_qa compare --databases milvus,seekdb --templates templates/shared.yaml

# 3. View comparison
cat results/comparison_20260307/differential_report.md

# 4. Export for paper
ai-db_qa export --results results/comparison_20260307/ --type paper-cases
```

### User Journey 3: Quality Engineer

```bash
# 1. Install
pip install ai-db-qa

# 2. Run validation regularly (CI/CD)
ai-db_qa validate --db milvus --templates templates/regression.yaml --output ci-results/

# 3. Check for new bugs
ai-db_qa export --results ci-results/ --type issue-report

# 4. Add new regression tests if bugs found
# Edit templates/regression.yaml based on findings
```

---

## First Milestone Components

### What We Build

**File**: `ai_db_qa/` (new package)

```
ai_db_qa/
├── __main__.py              # Entry point
├── workflows/                 # Workflow wrappers
│   ├── validate.py           # Wrap executor pipeline
│   ├── compare.py            # Wrap differential scripts
│   └── export.py             # Export formatters
└── export/                    # Export templates
    ├── issue_report.py      # Issue report formatter
    ├── paper_cases.py        # Paper case formatter
    └── summary.py            # Summary formatter
```

### What We Don't Build (Yet)

- ❌ New research directions
- ❌ Additional oracles (3 is enough)
- ❌ LLM integration (templates work fine)
- ❌ Web UI (CLI is sufficient)
- ❌ Template count metric (focus on coverage instead)

---

## Summary: Product = Exposure + Integration

### What We Have

All core components exist and work:
- Test execution ✅
- Correctness judgment ✅
- Triage classification ✅
- Differential analysis ✅
- Template system ✅

### What We Need

Only **exposure and integration**:
1. Wrap workflows in CLI commands
2. Automate report generation
3. Document how to use it

### What We Don't Need

- ❌ New architecture
- ❌ New research
- ❌ New components
- ❌ Template count goals

**The product is the same system, exposed better.**
