# Minimal Configuration Model

**Date**: 2026-03-08
**Purpose**: Define configuration schemas for campaigns and case packs

---

## Configuration Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│                     CONFIGURATION LAYERS                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Connection Config (database connectivity)               │
│     ├─ type: milvus | seekdb                                │
│     ├─ host, port, credentials                              │
│     └─ Connection pool settings                             │
│                                                              │
│  2. Contract/Profile Config (expected behavior)             │
│     ├─ Database profile (which capabilities expected)       │
│     ├─ Contract (operation legality rules)                  │
│     └─ Parameter constraints                                │
│                                                              │
│  3. Oracle Config (correctness judgment)                    │
│     ├─ Which oracles to enable                              │
│     ├─ Oracle-specific settings                              │
│     └─ Severity thresholds                                  │
│                                                              │
│  4. Campaign Config (execution scenario)                    │
│     ├─ Case pack reference                                  │
│     ├─ Target databases                                     │
│     ├─ Execution options (parallel, timeout)                │
│     └─ Output specifications                                │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Schema 1: Case Pack

**Purpose**: Pre-instantiated test cases, ready to execute
**Format**: JSON
**Location**: `packs/*.json`

### Minimal Schema

```json
{
  "pack_meta": {
    "name": "Basic Operations Pack",
    "version": "1.0",
    "description": "Core vector database operations",
    "author": "ai-db-qa",
    "created": "2026-03-08"
  },
  "cases": [
    {
      "case_id": "create_collection_valid",
      "operation": "create_collection",
      "params": {
        "collection_name": "test_collection",
        "dimension": 128,
        "metric_type": "L2"
      },
      "rationale": "Valid collection creation should succeed"
    },
    {
      "case_id": "create_index_invalid_metric",
      "operation": "create_index",
      "params": {
        "collection_name": "test_collection",
        "metric_type": "INVALID_METRIC"
      },
      "expected_outcome": "failure",
      "rationale": "Invalid metric type should be rejected"
    }
  ]
}
```

### Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `pack_meta` | object | Yes | Metadata about the pack |
| `pack_meta.name` | string | Yes | Human-readable pack name |
| `pack_meta.version` | string | Yes | Version identifier |
| `pack_meta.description` | string | No | What this pack tests |
| `cases` | array | Yes | Test cases |
| `cases[*].case_id` | string | Yes | Unique case identifier |
| `cases[*].operation` | string | Yes | Operation name |
| `cases[*].params` | object | Yes | Operation parameters |
| `cases[*].expected_outcome` | string | No | "success" or "failure" (optional) |
| `cases[*].rationale` | string | Yes | Why this case exists |

---

## Schema 2: Campaign Configuration

**Purpose**: Complete testing scenario (cases + databases + outputs)
**Format**: YAML
**Location**: `campaigns/*.yaml`

### Variant A: Single-Database Validation

```yaml
# campaigns/milvus_validation.yaml
name: "Milvus Basic Validation"
version: "1.0"
description: "Validate Milvus against core test cases"

# Database configuration
databases:
  - type: milvus
    host: localhost
    port: 19530
    # Optional: credentials
    # username: null
    # password: null

# Test cases (pre-instantiated pack)
case_pack: packs/basic_ops_pack.json

# Expected behavior
contract:
  profile: contracts/db_profiles/milvus_profile.yaml

# Correctness judgment
oracles:
  - name: write_read_consistency
    config:
      validate_ids: true
  - name: filter_strictness
    config: {}
  - name: monotonicity
    config: {}

# Execution options
execution:
  parallel: false
  timeout_seconds: 30
  continue_on_failure: true

# Output specifications
outputs:
  - type: issue-report
    format: markdown
    file: BUG_REPORT.md

  - type: summary
    format: json
    file: summary.json

  - type: detailed
    format: jsonl
    file: execution_results.jsonl
```

### Variant B: Cross-Database Differential Comparison

```yaml
# campaigns/differential_comparison.yaml
name: "Milvus vs SeekDB Comparison"
version: "1.0"
description: "Compare behavior on shared test cases"
tag: "v4_comparison"

# Databases to compare
databases:
  - type: milvus
    host: localhost
    port: 19530
    alias: milvus

  - type: seekdb
    host: 127.0.0.1
    port: 2881
    alias: seekdb

# Shared test cases
case_pack: packs/differential_pack.json

# Expected behavior (generic or specific per-DB)
contract:
  profile: contracts/db_profiles/generic_profile.yaml
  # Or specify per-DB:
  # profiles:
  #   milvus: contracts/db_profiles/milvus_profile.yaml
  #   seekdb: contracts/db_profiles/seekdb_profile.yaml

# Correctness judgment
oracles:
  - name: write_read_consistency
    config:
      validate_ids: true
  - name: filter_strictness
    config: {}
  - name: monotonicity
    config: {}

# Execution options
execution:
  mode: differential  # Run on all DBs, then compare
  parallel: true      # Run databases in parallel
  timeout_seconds: 30
  continue_on_failure: true

# Output specifications (differential-specific)
outputs:
  - type: differential
    format: markdown
    file: differential_report.md

  - type: issue-report
    format: markdown
    file: BUG_REPORT.md

  - type: summary
    format: json
    file: summary.json
```

### Field Definitions

| Section | Field | Type | Required | Description |
|---------|------|------|----------|-------------|
| **Root** | `name` | string | Yes | Human-readable campaign name |
| | `version` | string | Yes | Version identifier |
| | `description` | string | No | What this campaign tests |
| | `tag` | string | No | Run identifier for comparisons |
| **databases** | `type` | string | Yes | "milvus" or "seekdb" |
| | `host` | string | No | Hostname (default: localhost) |
| | `port` | integer | No | Port number |
| | `alias` | string | No | Short name for reports |
| **case_pack** | `case_pack` | string | Yes | Path to case pack JSON |
| **contract** | `profile` | string | No | Path to contract/profile YAML |
| | `profiles` | object | No | Per-DB profile mappings |
| **oracles** | `name` | string | Yes | Oracle class name |
| | `config` | object | No | Oracle-specific settings |
| **execution** | `mode` | string | No | "validation" or "differential" |
| | `parallel` | boolean | No | Execute in parallel |
| | `timeout_seconds` | integer | No | Per-case timeout |
| | `continue_on_failure` | boolean | No | Stop on first failure? |
| **outputs** | `type` | string | Yes | Output type |
| | `format` | string | Yes | Output format |
| | `file` | string | Yes | Output filename |

---

## Schema 3: Contract/Profile

**Purpose**: Define expected database behavior
**Format**: YAML
**Location**: `contracts/db_profiles/*.yaml`

### Minimal Schema

```yaml
# contracts/db_profiles/milvus_profile.yaml
database:
  type: milvus
  version: "2.4+"

# Supported operations
operations:
  - create_collection
  - drop_collection
  - insert
  - search
  - create_index

# Parameter constraints
constraints:
  create_collection:
    dimension:
      min: 2
      max: 32768
      default: 128
    metric_type:
      allowed: ["L2", "IP", "COSINE", "HAMMING", "JACCARD"]
      default: "L2"

  create_index:
    index_type:
      allowed: ["IVF_FLAT", "IVF_SQ8", "IVF_PQ", "HNSW"]
      default: "IVF_FLAT"
    metric_type:
      allowed: ["L2", "IP", "COSINE"]

# Expected error messages (for diagnostic quality)
error_messages:
  invalid_dimension:
    expected_pattern: "invalid dimension"
    should_include_param: true
  invalid_metric_type:
    expected_pattern: "invalid metric type"
    should_include_param: true
```

---

## Configuration Loading Strategy

### Priority Order (highest to lowest)

1. **CLI flags** - Override everything
   ```bash
   python -m ai_db_qa validate --db milvus --host remote.host
   ```

2. **Campaign file** - Complete configuration
   ```yaml
   databases:
     - type: milvus
       host: localhost  # Used if no CLI flag
   ```

3. **Default profiles** - Fallback values
   ```python
   # contracts/db_profiles/milvus_profile.yaml
   default_port: 19530
   ```

### Resolution Example

```python
# User runs:
python -m ai_db_qa validate --campaign campaigns/milvus.yaml --host remote.host

# Resolution:
# - host: "remote.host" (CLI flag overrides campaign)
# - port: 19530 (from campaign, no CLI override)
# - type: "milvus" (from campaign)
# - case_pack: "packs/basic_ops.json" (from campaign)
```

---

## Configuration Validation

### Validation Rules

1. **Required fields present**
   - Campaign: `databases`, `case_pack`
   - Case pack: `cases`
   - Profile: `database.type`

2. **Valid values**
   - `databases[*].type` ∈ {milvus, seekdb}
   - `outputs[*].type` ∈ {issue-report, summary, differential}
   - `outputs[*].format` ∈ {markdown, json, jsonl}

3. **File existence**
   - `case_pack` file must exist
   - `contract.profile` file must exist (if specified)

4. **Logical consistency**
   - Differential campaigns need ≥2 databases
   - `differential` output type only valid for compare workflow

---

## Example: Complete Campaign Set

### File Structure

```
campaigns/
├── milvus_validation.yaml       # Single-DB validation
├── seekdb_validation.yaml       # Single-DB validation
└── differential_comparison.yaml # Cross-DB comparison

packs/
├── basic_ops_pack.json          # Core operations
├── boundary_pack.json           # Parameter limits
└── differential_pack.json       # Shared comparison cases

contracts/
└── db_profiles/
    ├── milvus_profile.yaml      # Milvus expectations
    ├── seekdb_profile.yaml      # SeekDB expectations
    └── generic_profile.yaml     # Generic expectations
```

### Usage

```bash
# Validate Milvus
python -m ai_db_qa validate --campaign campaigns/milvus_validation.yaml

# Validate SeekDB
python -m ai_db_qa validate --campaign campaigns/seekdb_validation.yaml

# Compare both
python -m ai_db_qa compare --campaign campaigns/differential_comparison.yaml

# Export results
python -m ai_db_qa export \
  --input results/differential_v4_comparison_20260308_120000/ \
  --type issue-report \
  --output bugs.md
```

---

## Summary

### Configuration Artifacts

| Artifact | Format | Purpose | Authoring Level |
|----------|--------|---------|-----------------|
| **Raw Template** | YAML | Test case patterns | Expert |
| **Case Pack** | JSON | Ready-to-execute cases | Intermediate |
| **Campaign** | YAML | Complete scenario | End-user |
| **Contract/Profile** | YAML | Expected behavior | Expert |

### Key Design Principles

1. **Case packs over templates**: End-users consume packs, not templates
2. **Campaigns for reproducibility**: Single file = reproducible run
3. **CLI overrides for flexibility**: Quick tests without editing files
4. **Sensible defaults**: Minimize required configuration
5. **Validation at load time**: Fail fast, clear errors
