# Differential Campaign Implementation Checklist

> **Goal**: Run same 30 cases on Milvus + seekdb, produce differential comparison

---

## Task List (4 tasks)

1. **Create shared case pack** - 30 cases (10 per bucket)
2. **Build differential runner** - Execute on both DBs
3. **Build differential analyzer** - Assign comparison labels
4. **Execute and verify** - Run campaign, generate reports

---

## File List (3 new files)

| File | Purpose | Lines |
|------|---------|-------|
| `casegen/templates/differential_shared_pack.yaml` | Shared 30 cases | ~300 |
| `scripts/run_differential_campaign.py` | Dual-DB runner | ~250 |
| `scripts/analyze_differential_results.py` | Labeling + output | ~300 |

**Total**: ~850 new lines (not 1162)

---

## Acceptance Criteria

- [ ] 30 cases in shared pack (10 per bucket)
- [ ] Runner executes same cases on both databases
- [ ] Analyzer assigns explicit comparison labels per case
- [ ] Output: aggregate table + differential case list (JSON + Markdown)
- [ ] At least 2 differential cases identified

---

## Output Artifacts

| Artifact | Format | Location |
|----------|--------|----------|
| Execution results | JSONL per DB | `runs/differential-<tag>-<ts>/seekdb/`, `/milvus/` |
| Differential report | JSON | `runs/.../differential_report.json` |
| Differential report | Markdown | `runs/.../differential_report.md` |
| Differential case list | Embedded in report | Key deliverable |

---

## Comparison Labels (8)

```
same_behavior              - Identical outcomes
seekdb_stricter            - seekdb rejected, Milvus accepted
milvus_stricter            - Milvus rejected, seekdb accepted
seekdb_poorer_diagnostic   - Both rejected, seekdb error worse
milvus_poorer_diagnostic   - Both rejected, Milvus error worse
seekdb_precond_sensitive   - seekdb precond fail, Milvus didn't
milvus_precond_sensitive   - Milvus precond fail, seekdb didn't
outcome_difference         - Other outcome differences
```

---

## Key Risks

| Risk | Mitigation |
|------|------------|
| Milvus not available | `--skip-milvus` flag for seekdb-only |
| Milvus adapter missing | Create minimal adapter or skip Milvus |
| Case parameter mismatch | Adapter parameter mapping layer |
| Empty differential results | Expected - still valid comparison |

---

## Execution Order

```
1. Create shared pack → 2. Build runner → 3. Build analyzer → 4. Test seekdb-only → 5. Full run (if Milvus available)
```

---

## Success Definition

**Campaign success**: Same 30 cases run on both databases, differential report produced with explicit labels, at least 2 behavioral differences identified and documented.

**NOT a new subsystem**: Reuses existing framework (triage, oracles, evidence). Only adds case pack + runner + analyzer.
