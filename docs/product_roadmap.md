# AI Database QA Tool - Product-Oriented Planning View

**Date**: 2026-03-07
**Status**: Prototype consolidation and productization phase
**Objective**: Transform research framework into usable QA tool prototype

---

## 1. Current System → Original Proposal Mapping

### Original Proposal Components

| # | Component | Description |
|---|-----------|-------------|
| 1 | Technical Survey | Catalog AI database capabilities, operations, constraints |
| 2 | Test Generation | LLM-driven generation of diverse test cases |
| 3 | Correctness Judgment | Evidence-backed triage with oracle verification |
| 4 | QA Tool Output | Actionable reports, differential analysis, bug reports |

### Current Implementation Mapping

#### Component 1: Technical Survey ✅ STRONG

**Implemented As**:
- `contracts/core/` - Database capability contracts
- `contracts/db_profiles/` - seekdb and Milvus profiles
- `adapters/` - Database adapters (MilvusAdapter, SeekDBAdapter)
- `get_runtime_snapshot()` - Capability discovery

**Coverage**:
- ✅ Operation discovery (search, insert, create_collection, etc.)
- ✅ Parameter constraints (dimension limits, metric types)
- ✅ Runtime state (collections, indexes, loaded state)
- ✅ Multi-database support (Milvus, seekdb)

**Product Strength**: **Core survey infrastructure is solid**

---

#### Component 2: Test Generation ✅ PARTIAL

**Implemented As**:
- `casegen/generators/instantiator.py` - Template instantiation
- `casegen/templates/*.yaml` - Template-based case packs
- Manual template creation (not LLM-driven yet)

**Current Limitations**:
- ❌ Template-based, not LLM-driven
- ❌ Requires manual template authoring
- ❌ No automatic case generation from contracts
- ❌ Limited to hand-written templates

**Product Gap**: **LLM-driven generation is the missing piece**

---

#### Component 3: Correctness Judgment ✅ STRONG

**Implemented As**:
- `pipeline/executor.py` - Test execution engine
- `pipeline/preconditions.py` - PreconditionEvaluator (gate)
- `oracles/` - Oracle suite (FilterStrictness, WriteReadConsistency, Monotonicity)
- `pipeline/triage.py` - Triage with naive/diagnostic modes
- `schemas/common.py` - ObservedOutcome taxonomy

**Coverage**:
- ✅ Precondition checking (legality + runtime)
- ✅ Oracle-based correctness verification
- ✅ Triage classification (bug types)
- ✅ Evidence collection (oracle_results, gate_trace)

**Product Strength**: **Correctness judgment pipeline is complete and working**

---

#### Component 4: QA Tool Output ✅ PARTIAL

**Implemented As**:
- `scripts/analyze_differential_results.py` - Differential analysis
- JSONL output (execution_results.jsonl)
- JSON summary (metadata.json, triage_results.json)
- Markdown reports (differential_report.md)
- Issue reports (docs/issues/*.md)

**Current Limitations**:
- ⚠️ Multiple output formats (not unified)
- ⚠️ Requires manual post-processing for publication
- ⚠️ No user-facing CLI entry point
- ⚠️ No configurable report templates

**Product Gap**: **Need unified reporting interface and CLI entry point**

---

## 2. Product Readiness Assessment

### Strengths (Ready for Product Use)

| Component | Readiness | Evidence |
|-----------|-----------|----------|
| **Core Pipeline** | ✅ Production-ready | End-to-end execution working (Differential v3 success) |
| **Adapters** | ✅ Production-ready | Milvus, seekdb adapters robust |
| **Oracles** | ✅ Production-ready | FilterStrictness, WriteReadConsistency, Monotonicity validated |
| **Preconditions** | ✅ Production-ready | Legality + runtime checking working |
| **Triage** | ✅ Production-ready | Diagnostic mode successfully filters noise |
| **Contracts** | ✅ Production-ready | Capability profiles functional |

### Weaknesses (Need Product Work)

| Component | Gap | Impact |
|-----------|-----|--------|
| **Test Generation** | Template-based, not LLM-driven | Manual template authoring required |
| **CLI Interface** | Multiple scripts, no unified entry point | Poor UX |
| **Reporting** | Scattered outputs, not unified | Manual aggregation needed |
| **Configuration** | Hardcoded in scripts | Not user-configurable |
| **Documentation** | Research-focused, not user-facing | Learning curve |

---

## 3. Minimum Product Form (MVP)

### Product Definition

**AI Database QA Tool**: Command-line tool that automatically tests AI databases, judges correctness, and generates actionable reports.

**Target Users**:
1. AI database developers (test their own systems)
2. AI database users (validate vendor claims)
3. Researchers (compare database behaviors)

### MVP Modules

#### Module A: Test Generator (productize existing)

**Current**: `casegen/generators/instantiator.py`
**Product Form**: CLI command `ai-db-qa generate`

```bash
# Generate test cases from template
ai-db-qa generate \
  --template templates/basic_operations.yaml \
  --output cases/generated_pack.json \
  --overrides dimension=128,metric_type=L2

# Generate with LLM assistance (future)
ai-db-qa generate \
  --contract contracts/db_profiles/milvus_profile.yaml \
  --llm \
  --coverage boundary,diagnostic \
  --output cases/llm_generated.json
```

**Status**: ✅ Usable now (template-based), ⚠️ Needs LLM integration

---

#### Module B: Test Runner (productize existing)

**Current**: `pipeline/executor.py` + `scripts/run_differential_campaign.py`
**Product Form**: CLI command `ai-db-qa run`

```bash
# Run single database test
ai-db-qa run \
  --adapter milvus \
  --cases cases/basic_operations.json \
  --output results/milvus_run.json

# Run differential comparison
ai-db-qa run \
  --diff milvus,seekdb \
  --cases cases/shared_pack.json \
  --output results/comparison/
```

**Status**: ✅ Core ready, needs CLI wrapping

---

#### Module C: Report Generator (unify existing)

**Current**: `scripts/analyze_differential_results.py` + scattered formats
**Product Form**: CLI command `ai-db-qa report`

```bash
# Generate bug report
ai-db-qa report \
  --input results/milvus_run.json \
  --template bug_report \
  --output reports/bugs/

# Generate differential comparison
ai-db-qa report \
  --input results/milvus/,results/seekdb/ \
  --template differential \
  --output reports/comparison/

# Generate summary statistics
ai-db-qa report \
  --input results/ \
  --template summary \
  --output reports/summary.md
```

**Status**: ⚠️ Needs unification of existing scripts

---

#### Module D: Technical Survey (expose existing)

**Current**: `adapters/*.py` get_runtime_snapshot()
**Product Form**: CLI command `ai-db-qa survey`

```bash
# Survey database capabilities
ai-db-qa survey \
  --adapter milvus \
  --output surveys/milvus_capabilities.json

# Compare capabilities
ai-db-qa survey \
  --diff milvus,seekdb \
  --output surveys/capability_comparison.md
```

**Status**: ✅ Core ready, needs CLI exposure

---

### User Inputs

| Input Type | Format | Example |
|------------|--------|---------|
| **Database Connection** | Config/CLI flags | `--adapter milvus --endpoint localhost:19530` |
| **Test Cases** | Template file or JSON | `--templates templates/basic.yaml` |
| **Contract** | YAML profile | `--contract contracts/db_profiles/milvus.yaml` |
| **Report Type** | Template selection | `--template differential` |
| **Output Format** | File/dir selection | `--output results/` |

### User Outputs

| Output Type | Format | Content |
|------------|--------|---------|
| **Execution Results** | JSONL | Per-case results with oracle evidence |
| **Bug Reports** | Markdown | Issue-ready bug writeups |
| **Differential Analysis** | Markdown | Cross-database comparison tables |
| **Summary Statistics** | JSON/Markdown | Counts, pass/fail rates, noise metrics |

### Entry Points

**Single Unified CLI**:
```bash
# Primary interface
ai-db-qa <command> [options]

# Commands:
#   generate  - Generate test cases
#   run       - Execute tests
#   report    - Generate reports
#   survey    - Capability discovery
#   version   - Tool and database version info
```

---

## 4. Continued Real Bug Mining Strategy

### Shift from "Research Mode" to "Production Mode"

**Research Mode** (what we were doing):
- Run campaigns → Analyze results → Design next experiments
- Focus on methodology improvement
- Target: Paper publication

**Production Mode** (what we should do):
- Generate useful reports → File issues → Improve product
- Focus on actionable output for users
- Target: Usable tool + real bug discovery

### Product-Oriented Mining Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                    PRODUCTION PIPELINE                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. GENERATE                                                 │
│     ai-db-qa generate --template <pack> --output cases/     │
│     ↓                                                       │
│  2. RUN                                                      │
│     ai-db-qa run --adapter milvus,seekdb --cases <pack>    │
│     ↓                                                       │
│  3. REPORT                                                   │
│     ai-db-qa report --input results/ --template differential │
│     ↓                                                       │
│  4. ISSUE (Manual/Review)                                   │
│     Review generated issues, file to database maintainers    │
│     ↓                                                       │
│  5. ITERATE                                                  │
│     Expand templates based on findings                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### How to Continue Mining Without Losing Product Focus

#### Principle: Every Campaign Produces Usable Output

**Before** (Research Mode):
```
Run campaign → Analyze → Write plan → Run more campaigns
Output: Research papers, methodology insights
```

**After** (Production Mode):
```
Run campaign → Generate reports → File issues → Expand templates
Output: Bug reports, differential comparisons, better templates
```

#### Concrete Strategy

1. **Productize Each Campaign**
   - Every run produces a published issue report
   - Every comparison produces a differential analysis
   - Every finding updates the template library

2. **Expand Template Library Systematically**
   - After v3: Add templates for new operations (delete, update, hybrid_search)
   - After findings: Add regression templates for discovered bugs
   - Continuously: Improve template coverage based on blind spots

3. **Report Generation is First-Class Output**
   - Differential v3 produced 3 issue reports (already filed)
   - Future campaigns should produce same automatically
   - Reports are the product, not just intermediate artifacts

4. **User Feedback Drives Template Development**
   - If user wants to test X: Add template for X
   - If user reports bug in database: Add regression test
   - If user compares databases: Add differential template

---

## 5. Product Development Roadmap

### Phase 1: CLI Unification (Immediate - Week 1)

**Goal**: Single entry point for all capabilities

**Tasks**:
1. Create `ai-db-qa` main CLI
2. Wrap existing scripts into CLI commands
3. Unify output formats
4. Basic help/version commands

**Deliverable**: Working CLI with 4 commands (generate, run, report, survey)

---

### Phase 2: Template Library Expansion (Week 2-4)

**Goal**: Comprehensive test case coverage

**Strategy**: Product-driven expansion
- After v3 findings: Add templates for discovered edge cases
- User requests: Add templates for high-value operations
- Systematic coverage: Fill operation matrix

**Template Coverage Target**:
```
Current: 18 templates (v3 Phase 1 + 2)
Target: 50 templates covering all major operations
```

---

### Phase 3: LLM Integration (Future - Month 2+)

**Goal**: Automated test generation from contracts

**Approach**:
1. Use LLM to read contract/profile
2. Generate candidate test cases
3. Validate against existing templates
4. Human-in-the-loop curation

**Status**: ⚠️ DEFER - Template-based approach is working well

---

### Phase 4: Product Hardening (Ongoing)

**Goal**: Production-ready tool

**Tasks**:
1. Error handling and recovery
2. Configuration file support
3. Progress bars and status output
4. Comprehensive documentation
5. Installation scripts

---

## 6. Immediate Next Steps

### This Week: CLI Unification

**Deliverable**: Working `ai-db-qa` CLI

```bash
# Create main CLI entry point
ai-db-qa/
├── __main__.py          # Entry point
├── cli.py               # CLI commands
├── commands/             # Command implementations
│   ├── generate.py       # Wrap instantiator
│   ├── run.py            # Wrap executor
│   ├── report.py         # Wrap analyzers
│   └── survey.py         # Wrap get_runtime_snapshot
└── templates/            # Existing templates
```

### Next 2 Weeks: Template Library Expansion

**Deliverable**: 50 comprehensive templates

**Priority**:
1. Fill operation gaps (delete, update, hybrid_search)
2. Add boundary cases for known limits (dimension, top_k)
3. Add regression tests for discovered bugs
4. Add differential comparison cases

### Continued Mining: Campaign v4

**Focus**: Real bug discovery + product improvement

**Plan**:
1. Generate comprehensive template pack (50 cases)
2. Run on Milvus + seekdb
3. Generate issue reports automatically
4. File real bugs to database maintainers
5. Use findings to expand templates further

---

## 7. Product Metrics

### Success Metrics (Product Perspective)

| Metric | Current | Target | How to Measure |
|--------|---------|--------|----------------|
| **CLI Usability** | Scattered scripts | Single unified CLI | Can user run end-to-end? |
| **Template Coverage** | 18 cases | 50 cases | Operation matrix completeness |
| **Report Quality** | Manual generation | Automatic reports | Publication-ready output? |
| **Real Bugs Found** | 3 (v3) | 10+ | Issues filed to vendors |
| **Time to Value** | Days | Hours | From install to first report |

### User Journey

**Current** (Research tool):
1. Understand framework → Write templates → Run scripts → Analyze results manually
2. Time to first useful output: ~1 day
3. Requires reading source code

**Target** (Product tool):
1. Install tool → Run pre-built templates → Get reports automatically
2. Time to first useful output: ~10 minutes
3. Documentation-driven

---

## 8. Summary: Product Vision

### What We Have (Strong Foundation)

✅ **Core Pipeline**: Complete correctness judgment system
✅ **Adapters**: Working Milvus and seekdb integration
✅ **Oracles**: Evidence-backed verification
✅ **Triage**: Noise-filtering classification
✅ **Templates**: 18 working test cases
✅ **Differential**: Cross-database comparison validated

### What We Need (Productization)

⚠️ **CLI**: Single entry point
⚠️ **Templates**: Systematic expansion to 50+ cases
⚠️ **Reports**: Unified automatic generation
⚠️ **Documentation**: User-facing guides
⚠️ **LLM**: Automated test generation (future)

### Product Strategy

**Do NOT**:
- ❌ Redesign the architecture
- ❌ Add new research directions
- ❌ Expand framework before productizing

**DO**:
- ✅ Wrap existing components in CLI
- ✅ Expand template library systematically
- ✅ Generate reports automatically
- ✅ Focus on real bug discovery
- ✅ Make tool usable by external users

---

## 9. Consolidation Plan

### Immediate: This Week

1. **Create CLI wrapper** (`ai-db-qa` package)
2. **Unify reporting** (single `ai-db-qa report` command)
3. **Document existing capabilities** (user guide)

### Short-term: Next 2-4 Weeks

4. **Expand template library** to 50 cases
5. **Run production campaign** (v4)
6. **File real bugs** from findings
7. **Iterate based on results**

### Long-term: Next 1-3 Months

8. **Hard for production** (error handling, config, docs)
9. **Gather user feedback** from real usage
10. **Plan LLM integration** based on template gaps

---

## Conclusion

**Current State**: Strong research framework, ready for productization

**Product Opportunity**: AI database QA tool that:
- Generates or runs test cases
- Judges correctness with evidence
- Produces actionable reports
- Compares databases automatically

**Next Step**: Build CLI wrapper and demonstrate end-to-end user journey

**Not Next Step**: More research, more architecture, more methodology

The shift is from **"research framework"** to **"usable tool"**.
