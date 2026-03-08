# Product Transition: From Research Framework to Usable Tool

**Date**: 2026-03-07
**Current State**: Research framework complete, transitioning to product

---

## At a Glance

### What We Built (Research Framework)

| Component | Status | File Location |
|-----------|--------|---------------|
| Test Execution Pipeline | ✅ Complete | `pipeline/executor.py`, `pipeline/preconditions.py` |
| Oracle System | ✅ Complete | `oracles/` (3 oracles) |
| Triage System | ✅ Complete | `pipeline/triage.py` |
| Database Adapters | ✅ Complete | `adapters/milvus_adapter.py`, `adapters/seekdb_adapter.py` |
| Contract System | ✅ Complete | `contracts/core/`, `contracts/db_profiles/` |
| Template System | ✅ Working | `casegen/generators/instantiator.py` |
| Differential Analysis | ✅ Complete | `scripts/analyze_differential_results.py` |

### What We Need (Product)

| Component | Status | Gap |
|-----------|--------|-----|
| CLI Interface | ❌ Missing | Single entry point |
| Template Library | ⚠️ Partial | 18 cases → 50+ cases needed |
| Automatic Reporting | ⚠️ Partial | Unified report generation |
| Documentation | ❌ Missing | User-facing guides |
| Installation | ❌ Missing | pip package setup |

---

## Three Integrated Capabilities

### Capability 1: Test-Case Generation ✅ (Template-Based)

**Current Implementation**:
- `casegen/generators/instantiator.py` - Template instantiation
- `casegen/templates/*.yaml` - 18 working templates
- Manual template authoring

**User Experience**:
```bash
# Current: Direct Python
python -m casegen.generators.instantiator template.yaml output.json

# Target: CLI
ai-db-qa generate -t template.yaml -o output.json
```

**Status**: ✅ Core works, needs CLI wrapper

---

### Capability 2: Correctness Judgment / Evidence-Backed Triage ✅ (Complete)

**Current Implementation**:
- `pipeline/executor.py` - Test execution
- `pipeline/preconditions.py` - Legality + runtime checks
- `oracles/` - 3 oracles (FilterStrictness, WriteReadConsistency, Monotonicity)
- `pipeline/triage.py` - Diagnostic/Naive triage modes
- Evidence collection: `oracle_results`, `gate_trace`

**Validation**:
- ✅ v3 Phase 1: 0% noise (excellent triage)
- ✅ v3 Phase 2: 0% noise (excellent triage)
- ✅ Differential v3: 3 genuine differences, 0 false positives

**User Experience**:
```bash
# Wrapped in CLI
ai-db-qa run -a milvus -c cases.json -o results/
```

**Status**: ✅ Complete and production-ready

---

### Capability 3: Result Organization / Reporting / Differential Analysis ⚠️ (Partial)

**Current Implementation**:
- `scripts/analyze_differential_results.py` - Differential analysis
- Scattered output formats (JSONL, JSON, Markdown)
- Manual report generation

**Output Types**:
- `execution_results.jsonl` - Per-case results
- `triage_results.json` - Classification
- `differential_report.md` - Cross-database comparison
- `docs/issues/*.md` - Issue reports (manual)

**Status**: ⚠️ Core works, needs unification

---

## Minimum Product Form (MVP)

### Entry Point: Unified CLI

```bash
$ ai-db-qa --help
AI Database QA Tool - Test databases, judge correctness, generate reports

Commands:
  generate  Generate test cases from templates
  run       Execute test campaigns
  report    Generate reports from results
  survey    Survey database capabilities
  version   Show version information
```

### User Workflow

```bash
# 1. Generate test cases (or use pre-built templates)
ai-db-qa generate -t templates/basic_ops.yaml -o cases/basic_ops.json

# 2. Run campaign
ai-db-qa run -a milvus -c cases/basic_ops.json -o results/milvus_basic -t run1

# 3. Generate report
ai-db-qa report -i results/milvus_basic -t bugs -o reports/milvus_bugs/

# 4. Differential comparison
ai-db-qa run --diff milvus,seekdb -c cases/shared.yaml -o results/comparison -t diff1
ai-db-qa report -i results/comparison -t differential -o reports/diff1.md
```

### Outputs

| Output | Format | Content |
|--------|--------|---------|
| **Results** | JSONL | Per-case execution with evidence |
| **Bugs** | Markdown | Issue-ready bug reports |
| **Differential** | Markdown | Cross-database comparison tables |
| **Summary** | JSON/MD | Statistics, pass/fail rates |

---

## What's Strong ✅

### 1. Core Pipeline is Production-Ready

- Precondition checking (legality + runtime)
- Oracle-based correctness verification
- Evidence collection and storage
- Triage classification (filters noise effectively)

**Evidence**: v3 achieved 0% noise pollution

### 2. Database Integration Works

- Milvus adapter: Fully functional
- seekdb adapter: Fully functional
- Multi-database: Differential comparison validated

**Evidence**: v3 Phase 1 + Phase 2 executed successfully

### 3. Differential Analysis is Powerful

- Finds genuine behavioral differences
- Identifies architectural differences
- Produces publication-quality comparisons

**Evidence**: 3 paper-worthy cases, 3 issue-ready bugs

### 4. Template System is Flexible

- YAML-based template language
- Parameter substitution
- Easy to extend

**Evidence**: 18 templates covering multiple operation types

---

## What's Weak ⚠️

### 1. No Single Entry Point

**Current**: Multiple scripts, must understand framework
**Need**: Single `ai-db-qa` CLI

**Impact**: High barrier to entry

### 2. Limited Template Coverage

**Current**: 18 templates
**Need**: 50+ templates for comprehensive coverage

**Impact**: Can't test all operations without manual template writing

### 3. Manual Report Assembly

**Current**: Scattered outputs, manual post-processing
**Need**: Unified report generation

**Impact**: Time-consuming to produce publication-ready output

### 4. No User Documentation

**Current**: Research-focused documentation
**Need**: User guides, tutorials, examples

**Impact**: Users can't get started without reading source code

---

## Productization Plan

### Phase 1: CLI Unification (Week 1)

**Goal**: Make it usable without reading source code

**Deliverables**:
1. `ai-db-qa` CLI package with 5 commands
2. `--help` for all commands
3. README.md with quick start

**Success Criterion**: User can run end-to-end campaign in 10 minutes

### Phase 2: Template Library Expansion (Weeks 2-4)

**Goal**: Comprehensive test coverage

**Deliverables**:
1. Template audit (coverage analysis)
2. Fill operation gaps (delete, update, hybrid_search)
3. Add regression tests for v3 findings
4. Reach 50+ templates

**Success Criterion**: All major operations covered

### Phase 3: Report Automation (Week 5)

**Goal**: One-command report generation

**Deliverables**:
1. Unified `ai-db-qa report` command
2. Report templates (bugs, differential, summary)
3. Publication-ready formatting

**Success Criterion**: Generate publication report with single command

---

## Continued Real Bug Mining (Product Mode)

### Shift in Mindset

**Before (Research Mode)**:
- Run campaign → Analyze methodology → Design next experiment
- Output: Research papers

**After (Production Mode)**:
- Run campaign → Generate reports → File issues → Expand templates
- Output: Bug reports + improved templates

### Concrete Plan: Campaign v4

**Focus**: Real bug discovery + template expansion

**Week 1** (Post-CLI):
1. Use new CLI to run v3 cases
2. Verify CLI produces same results
3. Document v3 findings as issue reports

**Week 2-3**:
1. Generate 30+ new templates
2. Cover operations: delete, update, hybrid_search, batch operations
3. Add regression tests for v3 bugs

**Week 4**:
1. Run v4 campaign with expanded templates
2. Automatic issue report generation
3. File real bugs to database maintainers

**Measurable Output**:
- Issue reports filed
- Templates added to library
- Real bugs discovered and documented

---

## Immediate Next Step

### This Week: Build CLI

**Task**: Create `ai-db_qa/` package with 5 commands

**Files to Create**:
1. `ai_db_qa/__init__.py` - Package
2. `ai_db_qa/cli.py` - Main entry point
3. `ai_db_qa/commands/generate.py` - Wrap instantiator
4. `ai_db_qa/commands/run.py` - Wrap executor
5. `ai_db_qa/commands/report.py` - Wrap analyzer
6. `ai_db_qa/commands/survey.py` - Wrap get_runtime_snapshot
7. `ai_db_qa/commands/version.py` - Version info
8. `README.md` - User documentation

**Estimated Time**: 3-5 days

**Entry to Production**: Single install command
```bash
pip install -e .
```

---

## Summary

### Transition Approach

**DO**:
- ✅ Wrap existing components in CLI
- ✅ Expand template library systematically
- ✅ Focus on real bug discovery
- ✅ Make tool externally usable

**DON'T**:
- ❌ Redesign core pipeline
- ❌ Add new research directions
- ❌ Expand before consolidating

### Product Vision

**AI Database QA Tool** that:
1. Generates or runs test cases
2. Judges correctness with evidence
3. Produces actionable reports
4. Compares databases automatically

### Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| CLI commands | 0 | 5 |
| Templates | 18 | 50 |
| Real bugs filed | 0 | 5+ |
| Time to first report | Days | Hours |

---

## Conclusion

**Current State**: Research framework complete, ready for productization

**Product Gap**: No single entry point, limited templates, manual reporting

**Solution**: CLI unification (Week 1) → Template expansion (Weeks 2-4)

**Key Insight**: We have a working system, not a prototype. The task is **exposure** and **integration**, not rebuilding.

**Next Action**: Build `ai-db-qa` CLI package this week.
