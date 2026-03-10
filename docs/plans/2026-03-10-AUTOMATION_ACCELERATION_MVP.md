# Automation Acceleration MVP - Design Document

**Initiative**: AUTOMATION_ACCELERATION
**Date**: 2026-03-10
**Status**: DESIGN APPROVED
**Author**: Claude Code
**Version**: 1.0

---

## Problem Statement

**Core Pain Point**: Campaign bootstrapping is too manual and repetitive.

Every new campaign requires:
1. Manual capability audit of database/adapter operations
2. Manual review of existing contract families for reuse
3. Manual first-slice pruning
4. Manual generator/oracle/smoke/report skeleton creation
5. Manual historical results review to avoid redundant testing

**Primary Goal**: Reduce campaign startup cost through standardized, semi-automated bootstrapping.

**Success Criteria**: For a new direction (consistency/distributed/new DB), the system can quickly/minimally-human-answer:
- What can be tested?
- Which contracts to use?
- Which cases to run first?
- What results already exist (don't repeat)?

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    AUTOMATION_ACCELERATION MVP                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐            │
│  │     P1      │───▶│     P2      │───▶│     P3      │            │
│  │  Capability │    │   Contract  │    │  Campaign   │            │
│  │   Registry  │    │   Coverage  │    │  Bootstrap  │            │
│  └─────────────┘    └─────────────┘    └─────────────┘            │
│         │                   │                   │                  │
│         │                   │                   ▼                  │
│         │                   │           ┌─────────────┐            │
│         │                   │           │   P4 Results │            │
│         │                   │           │  Index/Diff │            │
│         │                   │           └─────────────┘            │
│         │                   │                   │                  │
│         ▼                   ▼                   ▼                  │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │                   Campaign Generator                         │  │
│  │  (Reads registries → Generates scaffolds → Tracks results)  │  │
│  └─────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Flow: New Campaign Workflow

```
1. User creates campaigns/{campaign_name}/config.yaml
2. scripts/bootstrap_campaign.py reads:
   - P1: capabilities/{db}_capabilities.json (what operations available?)
   - P2: contracts/CONTRACT_COVERAGE_INDEX.json (what contracts exist?)
3. Generator creates 8 scaffold artifacts in main repo structure
4. User implements + runs campaign
5. scripts/index_results.py scans results/ → RESULTS_INDEX.json
6. scripts/diff_results.py compares runs for regression detection
```

---

## Component 1: Capability Audit Registry (P1)

**Priority**: 1
**Goal**: Know what operations each database/adapter supports.

### File Structure
```
capabilities/
├── milvus_capabilities.json
├── qdrant_capabilities.json
├── seekdb_capabilities.json
└── mock_capabilities.json
scripts/
└── bootstrap_capability_registry.py
```

### Schema

```json
{
  "adapter_name": "milvus_adapter",
  "db_family": "Milvus",
  "sdk_version": "pymilvus v2.6.10",
  "validated_db_version": "v2.6.10",
  "last_updated": "2026-03-10",
  "operations": [
    {
      "operation": "create_collection",
      "support_status": "supported",
      "support_level": "campaign_validated",
      "confidence": "high",
      "implementation_path": "MilvusAdapter._create_collection",
      "verification_path": "run_r5d_smoke.py::R5D-001 create_collection",
      "known_constraints": [
        {
          "type": "schema_requirement",
          "value": "enable_dynamic_field=True required for scalar fields"
        }
      ],
      "evidence_source": "campaign",
      "validated_in_campaigns": ["R5D", "R5B"],
      "notes": "Core operation validated across multiple campaigns"
    }
  ]
}
```

### Field Definitions

| Field | Type | Values | Purpose |
|-------|------|--------|---------|
| adapter_name | string | - | Python class name |
| db_family | string | Milvus/Qdrant/SeekDB/Mock | Database family |
| sdk_version | string | - | SDK/adapter version |
| validated_db_version | string | - | DB version tested against |
| operation | string | - | Operation name |
| support_status | enum | supported/partially_supported/unsupported/unknown | Current support |
| support_level | enum | static_only/runtime_validated/campaign_validated | Evidence strength |
| confidence | enum | high/medium/low | Stability indicator |
| implementation_path | string | - | Code location in adapter |
| verification_path | string | - | Test case that verified support |
| known_constraints | array | [{type, value}, ...] | Structured limitations |
| evidence_source | enum | static_scan/runtime_test/campaign | Where evidence came from |
| validated_in_campaigns | array | ["R5D", "R5B"] | Campaigns that validated this |
| notes | string | - | Additional context |

### Implementation: `scripts/bootstrap_capability_registry.py`

**MVP Scope**:
- Scan: Milvus, Qdrant, SeekDB, Mock adapters
- Extract: ~20 core operations (create_collection, insert, search, build_index, load, release, drop_index, etc.)
- Output: 4 JSON drafts for manual tuning
- No runtime introspection (reserved for future drift detection)

---

## Component 2: Contract Coverage Map (P2)

**Priority**: 2
**Goal**: Know what contracts exist and their validation status.

### File Structure
```
contracts/
├── CONTRACT_COVERAGE_INDEX.json  # ← NEW (machine-readable)
├── VALIDATION_MATRIX.json        # ← NEW (cross-DB tracking)
├── ann/                          # Existing (immutable definitions)
├── hybrid/
├── index/
└── schema/
```

### Principle: Immutable Contracts + Dynamic Index

**Contract Definition Files** (immutable, stable):
- `contract_id`, `family`, `statement`, `scope`, `assumptions`, `oracle_hints`
- `stable_metadata`: maturity, intended_scope, validation_targets
- **NO**: latest classification, validated db/version, last campaign outcome

**Coverage Index** (dynamic, updated after runs):
- `coverage_status`: Overall validation conclusion
- `validation_level`: Evidence strength source
- `validated_in_campaigns`: Which campaigns tested this
- Case-level drill-down evidence

### Schema A: Contract Coverage Index

```json
{
  "last_updated": "2026-03-10",
  "total_contracts": 27,
  "summary": {
    "contract_counts_by_family": {
      "ANN": 5,
      "HYBRID": 3,
      "INDEX": 11,
      "SCHEMA": 6,
      "CONSISTENCY": 2
    },
    "coverage_counts_by_family": {
      "ANN": {"strongly_validated": 2, "partially_validated": 1, "unvalidated": 2},
      "HYBRID": {"observational_only": 2, "unvalidated": 1},
      "INDEX": {"strongly_validated": 8, "partially_validated": 2, "inconclusive": 1},
      "SCHEMA": {"strongly_validated": 2, "partially_validated": 2, "observational_only": 1, "inconclusive": 1}
    }
  },
  "contracts": [
    {
      "contract_id": "SCH-001",
      "family": "SCHEMA_EVOLUTION",
      "semantic_area": "data_integrity",
      "coverage_status": "strongly_validated",
      "validation_level": "campaign_validated",
      "validated_in_campaigns": ["R5D"],
      "result_file": "results/r5d_p0_20260310-140345.json",
      "case_evidence": [
        {
          "case_id": "R5D-002",
          "classification": "PASS"
        }
      ],
      "report_ref": "docs/reports/R5D_FINAL_SUMMARY.md",
      "db_matrix_ref": "VALIDATION_MATRIX.json",
      "framework_level_candidate": true,
      "notes": "Cross-collection isolation architecturally expected"
    }
  ]
}
```

### Schema B: Validation Matrix

```json
{
  "last_updated": "2026-03-10",
  "validations": [
    {
      "database_family": "Milvus",
      "db_version": "v2.6.10",
      "contract_id": "SCH-001",
      "status_scope": "case_level",
      "classification": "PASS",
      "case_id": "R5D-002",
      "result_file": "results/r5d_p0_20260310-140345.json",
      "report_ref": "docs/reports/R5D_FINAL_SUMMARY.md",
      "campaign": "R5D",
      "timestamp": "2026-03-10T14:03:45"
    }
  ]
}
```

### Field Definitions

| Field | Meaning |
|-------|---------|
| **coverage_status** | Overall validation conclusion: unvalidated/partially_validated/strongly_validated/observational_only/inconclusive |
| **validation_level** | Evidence strength source: static_only/runtime_validated/campaign_validated |
| **status_scope** | Granularity: case_level (single case) or contract_rollup (aggregated) |
| **framework_level_candidate** | Architecturally expected across DBs (not empirically cross-validated) |

### Two-Layer Granularity

- **Top Level**: Contract-level aggregation (coverage_status)
- **Drill-down**: Case-level evidence (case_evidence array with case_id, classification)

---

## Component 3: Campaign Bootstrap Scaffold (P3)

**Priority**: 3
**Goal**: Auto-generate campaign skeleton from YAML config.

### Input: YAML Config

```yaml
# campaigns/{campaign_name}/config.yaml
campaign_name: "consistency_cross_session"  # human-readable, directory name
campaign_id: "R6A-001"                      # stable identifier for indexes/diffs
target_db: "Milvus"
adapter: "milvus_adapter"
contract_families:
  - "CONSISTENCY"
  - "ANN"
goal: "Validate cross-session consistency properties"
mode: "REAL"

constraints:
  max_cases: 20
  runtime_budget: "1h"
  # MVP: simple list of operation names
  # Future: can upgrade to [{name: "create_collection", required: true, version_constraint: ">=2.6"}]
  required_operations:
    - "create_collection"
    - "insert"
    - "search"

preferences:
  # contract_families defines candidate scope
  # priority_contracts only influences ordering/focus within that scope
  priority_contracts:
    - "ANN-001"
    - "CONS-001"
  skip_contracts: []

input_registries:
  capability_registry: "capabilities/milvus_capabilities.json"
  contract_coverage: "contracts/CONTRACT_COVERAGE_INDEX.json"
  validation_matrix: "contracts/VALIDATION_MATRIX.json"
```

### Output: 8 Must-Have Artifacts

```
campaigns/{campaign_name}/
├── config.yaml                          # Input
└── bootstrap_manifest.json              # Machine-readable manifest

# Artifacts generated in MAIN repo structure:
docs/plans/{campaign_id}_PLAN.md
docs/reports/{campaign_id}_REPORT_TEMPLATE.md
docs/handoffs/{campaign_id}_HANDOFF_TEMPLATE.md
contracts/{family}/{campaign_id}_contracts.json
casegen/generators/{campaign_id}_generator.py
pipeline/oracles/{campaign_id}_oracle.py
scripts/run_{campaign_id}_smoke.py
```

### Schema: bootstrap_manifest.json

```json
{
  "campaign_name": "consistency_cross_session",
  "campaign_id": "R6A-001",
  "generated_at": "2026-03-10T15:00:00",
  "input_config": "campaigns/consistency_cross_session/config.yaml",
  "artifacts": [
    {"type": "plan", "path": "docs/plans/R6A-001_PLAN.md"},
    {"type": "contract_spec", "path": "contracts/consistency/R6A-001_contracts.json"},
    {"type": "generator", "path": "casegen/generators/r6a-001_generator.py"},
    {"type": "oracle", "path": "pipeline/oracles/r6a-001_oracle.py"},
    {"type": "smoke_runner", "path": "scripts/run_r6a-001_smoke.py"},
    {"type": "report_template", "path": "docs/reports/R6A-001_REPORT_TEMPLATE.md"},
    {"type": "handoff_template", "path": "docs/handoffs/R6A-001_HANDOFF_TEMPLATE.md"}
  ],
  "capability_registry_snapshot": {...},
  "contract_coverage_snapshot": {...}
}
```

### Implementation: `scripts/bootstrap_campaign.py`

**MVP Scope**:
- Generate skeleton files with TODO markers
- No auto-generated test cases (future enhancement)
- No interactive wizard
- Read from: config.yaml, capability registry, contract coverage index

---

## Component 4: Historical Results Index/Diff (P4)

**Priority**: 4
**Goal**: Make results indexable, comparable, traceable.

### File Structure
```
results/
├── RESULTS_INDEX.json        # ← NEW (machine-readable, source of truth)
├── RESULTS_INDEX.md          # ← NEW (optional generated view)
└── *.json                    # Existing result files
scripts/
├── index_results.py          # ← NEW
└── diff_results.py           # ← NEW
```

### Schema A: Results Index

```json
{
  "last_updated": "2026-03-10",
  "total_runs": 18,
  "summary": {
    "by_campaign": {
      "R5D": 6,
      "R5B": 12
    },
    "by_database_version": {
      "Milvus v2.6.10": 18
    }
  },
  "runs": [
    {
      "run_id": "r5d-p0-20260310-140340",
      "campaign": "R5D",
      "campaign_id": "R5D-001",
      "database_family": "Milvus",
      "db_version": "v2.6.10",
      "timestamp": "2026-03-10T14:03:40",
      "result_file": "results/r5d_p0_20260310-140345.json",
      "mode": "REAL",
      "classification_summary": {
        "total": 4,
        "by_classification": {
          "PASS": 3,
          "OBSERVATION": 1
        }
      },
      "linked_contracts": ["SCH-001", "SCH-002", "SCH-004", "SCH-008"],
      "case_count": 4,
      "report_ref": "docs/reports/R5D_P0_ROUND1_SUMMARY.md",
      "handoff_ref": null
    }
  ]
}
```

### Schema B: Diff Output

```json
{
  "diff_id": "r5d-p0-vs-r5d-p05",
  "comparison_scope": "run_to_run",
  "run1": "r5d-p0-20260310-140340",
  "run2": "r5d-p05-20260310-141433",
  "timestamp": "2026-03-10T15:00:00",
  "delta": {
    "cases_added": [
      {"case_id": "R5D-005", "contract_id": "SCH-005"}
    ],
    "cases_removed": [],
    "classification_changes": [
      {
        "case_id": "R5D-006",
        "contract_id": "SCH-006",
        "from": "unvalidated",
        "to": "inconclusive"
      }
    ],
    "new_observations": [
      {
        "case_id": "R5D-005",
        "observation": "Nullable field insert works; null value not observable"
      }
    ],
    "bug_candidates": {
      "introduced": [],
      "resolved": []
    },
    "contract_status_changes": [
      {
        "contract_id": "SCH-006",
        "from": "unvalidated",
        "to": "inconclusive",
        "reason": "Filter path accepted but semantics not validated"
      }
    ],
    "summary_delta": {
      "total": {"from": 4, "to": 6},
      "by_classification": {
        "PASS": {"from": 3, "to": 3},
        "OBSERVATION": {"from": 1, "to": 3}
      }
    }
  }
}
```

### Field Definitions

| Field | Meaning |
|-------|---------|
| **campaign** | Campaign family/stream (e.g., "R5D", "R5B") |
| **campaign_id** | Specific campaign instance (e.g., "R5D-001") |
| **run_id** | Individual execution run (e.g., "r5d-p0-20260310-140340") |
| **classification_changes** | Case-level / run-level classification changes |
| **contract_status_changes** | Contract coverage rollup changes |
| **comparison_scope** | "run_to_run" (MVP default), future: "baseline_vs_current" |

### Usage

```bash
# Index all results
python scripts/index_results.py

# Diff two runs
python scripts/diff_results.py r5d-p0-20260310-140340 r5d-p05-20260310-141433
```

**MVP Scope**:
- Scan results/ directory
- Parse JSON result files
- Generate index (JSON primary, MD optional)
- Explicit two-run comparison
- No automatic alerting (future enhancement)

---

## MVP Scope Summary

| Component | MVP Scope | Future Enhancements |
|-----------|-----------|---------------------|
| **P1** Capability Registry | 4 adapters, ~20 operations, static scan | Runtime introspection, drift detection |
| **P2** Contract Coverage | R5B/R5D/ANN/Hybrid contracts | Auto-update from results |
| **P3** Bootstrap | 8 skeleton artifacts, TODO markers | Auto-generate first-slice cases |
| **P4** Results Index/Diff | Manual indexing, explicit diff | Auto-alerting, regression detection |

---

## Implementation Plan

### Phase 1: Foundation (P1 + P2)
1. Create `capabilities/` directory structure
2. Implement `scripts/bootstrap_capability_registry.py`
3. Generate initial capability registries (Milvus, Qdrant, SeekDB, Mock)
4. Create `contracts/CONTRACT_COVERAGE_INDEX.json` from R5B/R5D results
5. Create `contracts/VALIDATION_MATRIX.json`

### Phase 2: Campaign Bootstrapping (P3)
1. Define YAML config schema
2. Implement `scripts/bootstrap_campaign.py`
3. Generate 8 skeleton artifacts with TODO markers
4. Create `bootstrap_manifest.json`

### Phase 3: Results Tracking (P4)
1. Implement `scripts/index_results.py`
2. Generate `RESULTS_INDEX.json` from existing results
3. Implement `scripts/diff_results.py`
4. Test diff between R5D P0 and P0.5 runs

---

## Success Criteria

**For a new campaign (e.g., R6A Consistency):**

1. **Before**: Manual audit of adapter code → Manual contract review → Manual skeleton creation
2. **After**: `bootstrap_campaign.py` → Read capability registry → Read contract coverage → Generate skeletons

**Time Saved**: Target 50-70% reduction in campaign startup time.

**Quality**: Generated skeletons are production-ready with TODO markers for custom logic.

---

## Constraints & Principles

1. **Machine-readable first**: JSON primary, MD optional
2. **MVP mindset**: Build just enough, iterate later
3. **Separation of concerns**: Contracts (stable) from validation status (dynamic)
4. **No interactive wizard**: Declarative YAML config
5. **Explicit over implicit**: Manual diff commands, not auto-alerting

---

## Appendix: Terminology

| Term | Definition |
|------|------------|
| **campaign** | Campaign family/stream (e.g., "R5D", "R5B") |
| **campaign_id** | Specific campaign instance (e.g., "R5D-001", "R6A-001") |
| **run_id** | Individual execution run (e.g., "r5d-p0-20260310-140340") |
| **coverage_status** | Overall validation conclusion (unvalidated → strongly_validated) |
| **validation_level** | Evidence strength (static → runtime → campaign) |
| **framework_level_candidate** | Architecturally expected, not empirically cross-validated |

---

**Document Version**: 1.0
**Status**: APPROVED - Ready for Implementation
**Next Step**: Create implementation plan via writing-plans skill
