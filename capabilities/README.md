# Capability Registry

Declarative capability declarations for each database adapter.

## Files

- `milvus_capabilities.json` - Milvus adapter capabilities
- `qdrant_capabilities.json` - Qdrant adapter capabilities
- `seekdb_capabilities.json` - SeekDB adapter capabilities
- `mock_capabilities.json` - Mock adapter capabilities

## Schema

See `docs/plans/2026-03-10-AUTOMATION_ACCELERATION_MVP.md` for full schema.

## Updating

Run `python scripts/bootstrap_capability_registry.py --adapter <name>` to regenerate from adapter code.
Manual review required for: support_status, confidence, known_constraints, notes.
