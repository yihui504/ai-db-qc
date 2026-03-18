# Project Scope

## Mission Statement

Build a **minimal publishable prototype** of a contract-driven quality assurance system for AI databases, demonstrating that structured test case generation combined with structured correctness judgment can effectively discover and classify defects.

## Overall Project Scope

### Core Research Functions
1. **Structured Test Case Generation**
   - Rule-based generation from contracts
   - Contract-based mutation for boundary exploration
   - LLM-assisted suggestion (optional enhancement, Phase 2+)

2. **Structured Correctness Judgment**
   - Contract-based input validity checking
   - Precondition gate for runtime readiness
   - Semantic oracles for Type-4 detection
   - Triage pipeline for Type 1-4 classification
   - Confirm pipeline with rerun verification

### Target Systems
- **Primary**: Milvus (open-source vector database)
- **Secondary**: Any vector/hybrid retrieval database with adapter

### Initial Oracle Set
- Top-K monotonicity
- Filter strictness
- Write-read consistency

---

## Phase 1 Scope (Static Foundation)

### What Phase 1 DOES:
- ✅ Establish repository structure
- ✅ Write foundational documentation (THEORY.md, PROJECT_SCOPE.md, BUG_TAXONOMY.md)
- ✅ Implement core schemas with validation
- ✅ Implement contract/profile loading infrastructure
- ✅ Implement basic static validation
- ✅ Provide Milvus profile example
- ✅ Provide 10 basic case templates (valid, invalid, pseudo-valid)
- ✅ Establish unit test skeleton

### What Phase 1 Does NOT Do:
- ❌ Oracle implementation
- ❌ Real database execution
- ❌ Triage logic implementation
- ❌ Confirm pipeline implementation
- ❌ LLM integration
- ❌ Evidence writing (beyond schema definitions)
- ❌ Adapter execution

---

## Out of Scope (NON-GOALS)

### Platform Features NOT Included
- Distributed test execution
- Web UI or dashboard
- Multi-user support
- Persistent result database (beyond file-based evidence)
- Test suite management
- CI/CD integration

### Technical Scope NOT Included
- Full multi-database abstraction (beyond extensibility for Milvus)
- Complex DSL for test specification
- Performance optimization
- Load testing or stress testing
- Security testing

### Research Scope NOT Included
- Automatic oracle synthesis
- Test case prioritization
- Fault localization
- Automatic repair

---

## Success Criteria

### Phase 1 Success Criteria
1. ✅ Repository structure is complete and clean
2. ✅ Documentation clearly articulates the research contribution
3. ✅ All schemas are defined and can serialize/deserialize
4. ✅ Core contracts can be loaded
5. ✅ Milvus profile is defined and loadable
6. ✅ Case templates cover valid, invalid, and pseudo-valid cases
7. ✅ Unit tests validate schema and loading logic
8. ✅ `pytest tests/unit/ -v` passes

### Full System Success Criteria
1. Can generate test cases from contracts
2. Can execute cases against Milvus (or mock)
3. Can distinguish Type 1-4 defects with proper red-line enforcement
4. Can produce traceable evidence bundles
5. Can demonstrate findings on at least 3 benchmarks

---

## Design Principles

1. **Schema-First**: All module interactions use structured schemas
2. **LLM-Optional**: System works without LLM; LLM is enhancement only
3. **Evidence-Traceable**: Every conclusion traces to evidence
4. **YAGNI**: Minimal viable prototype, not platform
5. **Research-Oriented**: Design choices serve research clarity
