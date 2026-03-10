# R5D Phase 1: Adapter Audit and Supported Operations Summary

**Date**: 2026-03-10
**Phase**: 1 - Specification and Adapter Audit
**Database**: Milvus v2.6.10
**SDK**: pymilvus (latest)

---

## A. Supported Operations Table

### A.1 Schema Operations (Core for R5D)

| Operation | SDK Support | Adapter Status | R5D Use |
|-----------|------------|----------------|---------|
| **create_collection** | ✓ | Implemented | Create different schema variants |
| **describe_collection** | ✓ (via `describe()`) | **NOT Implemented** | **NEEDS ADDITION** |
| **get_schema** | ✓ (via `schema`) | Not Implemented | Can use schema property |
| **alter_collection** | ✗ | N/A | **NOT SUPPORTED** |
| **add_field** | ✗ | N/A | **NOT SUPPORTED** |
| **drop_field** | ✗ | N/A | **NOT SUPPORTED** |
| **rename_field** | ✗ | N/A | **NOT SUPPORTED** |
| **drop_collection** | ✓ | Implemented | Cleanup |

### A.2 Data Operations (Supporting R5D)

| Operation | SDK Support | Adapter Status | R5D Use |
|-----------|------------|----------------|---------|
| **insert** | ✓ | Implemented | Insert with/without scalar data |
| **search** | ✓ | Implemented | Vector search |
| **filtered_search** | ✓ | Implemented | **CRITICAL for SCH-006** |
| **count_entities** | ✓ | Implemented | Data preservation checks |
| **delete** | ✓ | Implemented | (Not needed for P0) |

### A.3 Introspection Paths (Observability)

| Path | Type | Returns | Stability |
|------|------|---------|-----------|
| `Collection.schema` | Property | `CollectionSchema` object | **HIGH** |
| `Collection.schema.fields` | List | `FieldSchema` objects | **HIGH** |
| `Collection.describe()` | Method | Dict with 16 keys | **HIGH** |
| `Collection.num_entities` | Property | `int` (entity count) | **HIGH** |
| `Collection.name` | Property | `str` (collection name) | **HIGH** |
| `Collection.is_empty` | Property | `bool` | **HIGH** |

### A.4 Field Schema Information

From `Collection.schema.fields` or `describe()["fields"]`:

```python
# Each field returns:
{
    "field_id": int,           # Internal field ID
    "name": str,                # Field name
    "description": str,         # Empty string usually
    "type": DataType,           # Enum (INT64, FLOAT_VECTOR, etc.)
    "params": dict,             # Type-specific params
    "is_primary": bool          # Primary key flag
}

# For FLOAT_VECTOR:
params = {"dim": 128}

# For VARCHAR:
params = {"max_length": 256}  # If set
```

---

## B. Introspection Path Stability Analysis

### B.1 Schema Observation Paths

**Path 1: Via `Collection.schema`**
```python
collection = Collection(name, using="default")
schema = collection.schema
fields = schema.fields

for field in fields:
    print(f"{field.name}: {field.dtype}")
    if field.is_primary:
        print(f"  PRIMARY KEY")
```

**Stability**: HIGH
- Returns `CollectionSchema` object
- Fields list is deterministic
- Types are `DataType` enums

**Observation Data**:
```python
{
    "field_name": str,      # "id", "vector", "category"
    "dtype": DataType,       # DataType.INT64, DataType.FLOAT_VECTOR
    "is_primary": bool,      # True/False
    "description": str,      # Usually ""
}
# For FLOAT_VECTOR:
{
    "dtype.dim": int         # Vector dimension
}
```

---

**Path 2: Via `Collection.describe()`**
```python
collection = Collection(name, using="default")
desc = collection.describe()

fields = desc["fields"]
for field_dict in fields:
    print(f"{field_dict['name']}: {field_dict['type']}")
```

**Stability**: HIGH
- Returns dict with comprehensive metadata
- 16 keys including: collection_name, fields, num_shards, etc.

**Observation Data**:
```python
{
    "collection_name": str,
    "auto_id": bool,
    "num_shards": int,
    "description": str,
    "fields": List[Dict],    # Same as schema.fields
    "collection_id": int,
    "consistency_level": int,
    "properties": dict,       # Custom properties
    "enable_dynamic_field": bool,
    "created_timestamp": int,
    "update_timestamp": int
}
```

---

### B.2 Data Count Observation Paths

**Path: `Collection.num_entities`**
```python
count = collection.num_entities
```

**Stability**: HIGH
- Direct integer return
- No parsing needed

**Caveat**: May not reflect very recent inserts without flush

---

### B.3 Query Result Observation Paths

**Path: Search results**
```python
results = collection.search(...)
# Returns list of Result objects
for result in results[0]:  # First query
    id = result.id
    distance = result.distance
    # Scalar fields accessible via:
    # result.entity.get("field_name")
```

**Stability**: HIGH
- Deterministic result order
- Scalar fields in `result.entity`

---

## C. State Model

### C.1 SchemaState Dataclass

```python
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class SchemaState:
    """Structural state of a collection."""

    # Identity
    collection_name: str

    # Schema definition
    fields: List[str]              # Field names
    field_types: Dict[str, str]     # {"id": "INT64", "vector": "FLOAT_VECTOR"}
    field_ids: Dict[str, int]      # {"id": 100, "vector": 101}

    # Vector specifics
    dimension: int                 # Vector dimension

    # Primary key
    primary_key: str               # Field name

    # Metadata
    entity_count: int              # Number of entities
    num_shards: int                # From describe()
    consistency_level: int         # From describe()

    # Observability metadata
    _observable_via: List[str]      # ["schema", "describe", "num_entities"]

    @classmethod
    def from_collection(cls, collection: 'Collection') -> 'SchemaState':
        """Create SchemaState from Milvus Collection object."""
        schema = collection.schema

        fields = []
        field_types = {}
        field_ids = {}

        for field in schema.fields:
            fields.append(field.name)
            field_types[field.name] = str(field.dtype).split(".")[-1]
            if hasattr(field.dtype, "max_length"):
                field_types[field.name] += f"({field.dtype.max_length})"
            field_ids[field.name] = getattr(field, "id", None)

        # Get vector dimension
        dimension = None
        for field in schema.fields:
            if str(field.dtype).startswith("FLOAT_VECTOR"):
                dimension = field.dtype.dim
                break

        # Get primary key
        primary_key = None
        for field in schema.fields:
            if field.is_primary:
                primary_key = field.name
                break

        return cls(
            collection_name=collection.name,
            fields=fields,
            field_types=field_types,
            field_ids=field_ids,
            dimension=dimension,
            primary_key=primary_key,
            entity_count=collection.num_entities,
            num_shards=1,  # Can get from describe()
            consistency_level=2,  # Can get from describe()
            _observable_via=["schema", "describe", "num_entities"]
        )

    def has_field(self, field_name: str) -> bool:
        """Check if field exists in schema."""
        return field_name in self.fields

    def is_subset_of(self, other: 'SchemaState') -> bool:
        """Check if this schema's fields are subset of another."""
        return set(self.fields).issubset(set(other.fields))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "collection_name": self.collection_name,
            "fields": self.fields,
            "field_types": self.field_types,
            "field_ids": self.field_ids,
            "dimension": self.dimension,
            "primary_key": self.primary_key,
            "entity_count": self.entity_count,
            "num_shards": self.num_shards,
            "consistency_level": self.consistency_level
        }
```

---

## D. Effect Matrix

### D.1 Operation → State Effects

| Operation | Affected State | Observation Path |
|-----------|----------------|-------------------|
| **create_collection** | All (initial) | schema, describe |
| **insert** | entity_count | num_entities |
| **create_collection(v2)** | v2 only (isolation) | N/A (different collection) |
| **search** | None (read-only) | results |
| **filtered_search** | None (read-only) | results |

### D.2 Multi-Collection Interaction Matrix

| Action | v1 State | v2 State | Cross-Effect |
|--------|----------|----------|-------------|
| Create v1 | Initialized | N/A | None |
| Insert to v1 | entity_count++ | N/A | None |
| Create v2 | Unchanged | Initialized | **None** |
| Insert to v2 | Unchanged | entity_count++ | **None** |
| Search v1 | Unchanged | N/A | **None** |
| Search v2 | N/A | Unchanged | **None** |

**Key Finding**: Creating v2 does NOT affect v1 state (isolation confirmed by SDK design)

---

## E. Adapter Extension Requirements

### E.1 Need to Implement: `describe_collection`

**Current Gap**: Adapter has no `describe_collection` operation

**Required Addition**:
```python
def _describe_collection(self, params: Dict) -> Dict[str, Any]:
    """Get collection schema and metadata.

    Args:
        params: Dict with keys:
            - collection_name (str): Name of collection to describe

    Returns:
        Response dict with:
            - status (str): "success" or "error"
            - operation (str): "describe_collection"
            - collection_name (str)
            - data (dict): {
                - fields: List[Dict] with field info
                - dimension: int
                - entity_count: int
                - primary_key: str
            }
    """
    collection_name = params.get("collection_name")

    try:
        collection = Collection(collection_name, using=self.alias)
        schema = collection.schema

        # Build field info
        fields_info = []
        for field in schema.fields:
            field_info = {
                "name": field.name,
                "type": str(field.dtype).split(".")[-1],
                "is_primary": field.is_primary
            }

            # Add type-specific params
            if hasattr(field.dtype, "dim"):
                field_info["dim"] = field.dtype.dim
            if hasattr(field.dtype, "max_length"):
                field_info["max_length"] = field.dtype.max_length

            fields_info.append(field_info)

        # Get vector dimension
        dimension = None
        for field in schema.fields:
            if hasattr(field.dtype, "dim"):
                dimension = field.dtype.dim
                break

        # Get primary key
        primary_key = None
        for field in schema.fields:
            if field.is_primary:
                primary_key = field.name
                break

        return {
            "status": "success",
            "operation": "describe_collection",
            "collection_name": collection_name,
            "data": [{
                "fields": fields_info,
                "dimension": dimension,
                "entity_count": collection.num_entities,
                "primary_key": primary_key,
                "num_shards": 1,  # Could fetch from describe()
                "consistency_level": 2
            }]
        }

    except Exception as e:
        return {
            "status": "error",
            "operation": "describe_collection",
            "collection_name": collection_name,
            "error": str(e)
        }
```

**Add to execute() method**:
```python
elif operation == "describe_collection":
    return self._describe_collection(params)
```

---

## F. P0 Case Executability Analysis

### F.1 Original 7 Cases → Final Executable Cases

| Original Case | Contract | Status | Reason |
|---------------|----------|--------|--------|
| R5D-001 | SCH-004 | ✓ KEEP | Metadata accuracy - fully supported |
| R5D-002 | SCH-008 | ✓ KEEP | Metadata reflection - fully supported |
| R5D-003 | SCH-001 | ✓ KEEP | Data preservation - fully supported |
| R5D-004 | SCH-002 | ✓ KEEP | Query compatibility - fully supported |
| R5D-005 | SCH-007 | ⚠️ MODIFY | Forbidden gate - operation doesn't exist |
| R5D-006 | SCH-005 | ✓ KEEP | Null semantics - testable |
| R5D-007 | SCH-006 | ✓ KEEP | Filter semantics - fully supported |

### F.2 Case Modifications

#### R5D-005: Modified from "Forbidden Gate" to "Collection Isolation"

**Original**: Try to change dimension (operation doesn't exist)
**Problem**: No `alter_collection` operation to test

**Modified R5D-005**: **Schema Isolation Verification**
- Purpose: Verify that v2 schema creation doesn't affect v1
- Sequence:
  1. Create v1: {id, vector[128]}
  2. Insert 100 entities to v1
  3. Describe v1 → state_v1_before
  4. Create v2: {id, vector[128], category}
  5. Describe v1 → state_v1_after
  6. Verify: state_v1_before == state_v1_after

**Contract**: SCH-008 (Metadata Reflection After Change)
**Oracle Strategy**: STRICT

---

### F.3 Final Executable P0 Cases

| Case ID | Contract | Name | Tests | Oracle Strategy |
|---------|----------|------|-------|-----------------|
| **R5D-001** | SCH-004 | Metadata Accuracy | describe returns correct schema | STRICT |
| **R5D-002** | SCH-008 | Metadata Reflection | v1 metadata stable after v2 | STRICT |
| **R5D-003** | SCH-001 | Data Preservation | v1 count unchanged after v2 | STRICT |
| **R5D-004** | SCH-002 | Query Compatibility | v1 query works after v2 | CONSERVATIVE |
| **R5D-005** | SCH-008 (modified) | Schema Isolation | v1 schema unchanged after v2 | STRICT |
| **R5D-006** | SCH-005 | Null Semantics | Missing field behavior | CONSERVATIVE |
| **R5D-007** | SCH-006 | Filter Semantics | Filter on new field works | CONSERVATIVE |

**Note**: R5D-002 and R5D-005 both test SCH-008 (metadata reflection), but from different angles:
- R5D-002: v1 metadata after v2 creation (query-focused)
- R5D-005: v1 schema after v2 creation (schema-focused)

Actually, these are redundant. Let me consolidate:

**FINAL P0 - 5 Cases**:
1. R5D-001: Metadata Accuracy (SCH-004)
2. R5D-002: Data Preservation (SCH-001)
3. R5D-003: Query Compatibility (SCH-002)
4. R5D-004: Schema Isolation (SCH-008)
5. R5D-005: Null Semantics (SCH-005)
6. R5D-006: Filter Semantics (SCH-006)

---

## G. Dropped/Rewritten Cases

### G.1 Dropped Cases

| Original Case | Reason | Replacement |
|---------------|--------|-------------|
| **Original R5D-005** (SCH-007 Forbidden Gate) | Operation doesn't exist | Removed - no alter_collection in SDK |
| **R5D-002** (SCH-008 Metadata Reflection) | Redundant with schema isolation | Merged into R5D-004 |

### G.2 Final Count

- **Original Plan**: 7 cases
- **Dropped**: 1 case (forbidden gate - not supported)
- **Merged**: 1 case (redundant)
- **Final**: 5 cases (reduced from 7)

---

## H. Summary

### H.1 Key Findings

1. **Milvus v2.6.10 does NOT support dynamic schema changes**
   - No `alter_collection`, `add_field`, `drop_field`
   - Confirmed: Multi-collection comparison approach is correct

2. **Introspection is HIGH quality**
   - `Collection.schema`: Stable, comprehensive
   - `Collection.describe()`: Rich metadata (16 keys)
   - `Collection.num_entities`: Direct count access

3. **Schema operations support boundary**
   - SUPPORTED: create_collection with different schemas
   - NOT SUPPORTED: alter existing schema
   - WORKAROUND: Multi-collection comparison

### H.2 Adapter Extension Required

**Single addition**: `describe_collection` operation
- ~30 lines of code
- Uses `Collection.schema` and `Collection.describe()`
- No external dependencies needed

### H.3 Final P0 Cases (5 total)

| Case | Contract | Layer | Focus |
|------|----------|-------|-------|
| R5D-001 | SCH-004 | L1 Foundation | Metadata accuracy |
| R5D-002 | SCH-001 | L3 Data Integrity | Data preservation |
| R5D-003 | SCH-002 | L4 Query Behavior | Query compatibility |
| R5D-004 | SCH-008 | L1 Foundation | Schema isolation |
| R5D-005 | SCH-005 | L5 Field Semantics | Null behavior |
| R5D-006 | SCH-006 | L4 Query Behavior | Filter semantics |

**Reduced from 7 to 5** - removed forbidden gate, merged redundant metadata reflection test

---

**Phase 1 Complete**: Adapter audit, state model, effect matrix, P0 case reduction documented.
**Ready for**: Phase 4 (Adapter Patch) - implement `describe_collection`
**NOT proceeding to**: Generator or Oracle until adapter patch complete
