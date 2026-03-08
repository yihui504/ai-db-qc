# Next Session Start Here

**Last Updated**: 2026-03-08
**Current Phase**: Planning Complete → Ready for Implementation

---

## 1. Current Project Status

**What we have**: A working research framework for AI database QA with:
- ✅ Test execution pipeline (executor, preconditions, oracles, triage)
- ✅ Database adapters (Milvus, seekdb)
- ✅ 18 working test templates (v3 Phase 1 + 2)
- ✅ Differential comparison validated (3 genuine bugs found, 0% noise)
- ✅ All core components production-ready

**What we need**: Productization through exposure and integration:
- ⏸️ Unified CLI entry point
- ⏸️ Workflow wrappers around existing components
- ⏸️ Case packs and campaigns (artifact organization)
- ⏸️ User-facing documentation

**Key insight**: The product is the same system, exposed better. NOT a rebuild.

---

## 2. Current Phase Goal

**Create a usable QA tool prototype** with three integrated capabilities:
1. Test-case generation (template instantiation → case packs)
2. Correctness judgment with evidence-backed triage (already working)
3. Result organization, reporting, and differential analysis (already working)

**Approach**: Wrap existing workflows in minimal CLI. No new architecture.

---

## 3. Required Reading Order

Read in this order before starting implementation:

1. **`docs/ready_for_implementation_summary.md`** (5 min)
   - Overview of what's defined
   - Implementation checklist
   - Key design decisions

2. **`docs/product_workflow_first_plan_refined.md`** (15 min)
   - Three primary workflows (validate, compare, export)
   - Artifact hierarchy (templates → packs → campaigns)
   - Configuration model embedded in workflows

3. **`docs/minimal_config_model.md`** (10 min)
   - Schemas for Case Pack, Campaign, Contract/Profile
   - Configuration loading priority

4. **`docs/cli_workflow_description_refined.md`** (15 min)
   - Implementation-ready CLI code
   - Workflow wrapper implementations
   - File structure and LOC estimates

**Total reading time**: ~45 minutes

---

## 4. Explicitly Out of Scope for Implementation

**DO NOT implement these in the first milestone**:

- ❌ LLM-driven test generation (template-based is sufficient)
- ❌ Web UI or GUI (CLI is appropriate)
- ❌ New research directions or experiments
- ❌ Additional oracles beyond the existing 3
- ❌ Template count metrics (focus on operation family coverage instead)
- ❌ Complex configuration (validation schemas, custom oracles)
- ❌ Advanced features (caching, parallel execution, progress bars)

**Focus ONLY on**:
- ✅ Three CLI commands wrapping existing workflows
- ✅ Case pack and campaign file support
- ✅ Basic configuration loading
- ✅ Documentation (README, quick start)

---

## 5. First Implementation Milestone Boundary

**Milestone**: "Usable Validation Tool"

**Objective**: User can complete end-to-end validation workflow and generate issue-ready or paper-ready outputs within 1 hour

**Deliverables**:

1. **CLI Package** (`ai_db_qa/`)
   - `__main__.py` - Entry point with 3 commands
   - `workflows/validate.py` - Wrap executor pipeline
   - `workflows/compare.py` - Wrap differential scripts
   - `workflows/export.py` - Wrap result formatting

2. **Working Example** (using existing v3 templates)
   ```bash
   # Generate case pack
   python -m ai_db_qa generate \
     --template casegen/templates/differential_v3_phase1.yaml \
     --output packs/v3_phase1_pack.json

   # Validate database
   python -m ai_db_qa validate --db milvus --pack packs/v3_phase1_pack.json

   # Compare databases
   python -m ai_db_qa compare --databases milvus,seekdb --pack packs/v3_phase1_pack.json --tag v4

   # Export results
   python -m ai_db_qa export --input results/v4-phase1/ --type issue-report
   ```

3. **Documentation**
   - README.md with quick start
   - Three scenario examples
   - Output format descriptions

**Success Criteria**:
- ✅ User can run full workflow without reading source code
- ✅ Generated reports are issue-ready or paper-ready
- ✅ Total time: <1 hour for end-to-end workflow (install → results)
- ✅ No breaking changes to existing components

**Exit Condition**: CLI produces same outputs as existing scripts when tested against v3 results.

---

## Implementation Files to Create

```
ai_db_qa/
├── __init__.py              # Package init (~5 lines)
├── __main__.py              # CLI entry point (~150 lines)
└── workflows/
    ├── __init__.py
    ├── validate.py          # Single-DB workflow (~150 lines)
    ├── compare.py           # Differential workflow (~100 lines)
    └── export.py            # Export workflow (~200 lines)
```

**Total**: ~600 lines of code, wrapping existing components.

**Estimated time**: 3-5 days

---

## Before You Start Implementation

1. ✅ Read all 4 planning documents in order
2. ✅ Confirm CLI approach (3 commands: validate, compare, export)
3. ✅ Confirm configuration model (packs + campaigns)
4. ✅ Review existing components to understand what you're wrapping

Then begin with package structure.

---

**Planning complete. Ready to implement.**
