# Bug #18: Schema Atomicity Issue - Pgvector

## Metadata

| Field | Value |
|-------|-------|
| **Bug ID** | #18 |
| **Database** | Pgvector |
| **Database Version** | v0.7.0 on PostgreSQL 16 (Docker: pgvector/pgvector:pg16) |
| **Adapter** | `adapters/pgvector_adapter.py` |
| **Severity** | Medium |
| **Status** | Confirmed |
| **Reproduced** | Yes |
| **Date Discovered** | 2026-03-18 |

## Description

Schema operations in the Pgvector adapter are not atomic. When a `create_collection` or `drop_collection` operation fails midway, the database state becomes inconsistent with expected state, leaving partial or corrupted schema remnants.

## Impact

- **Data Integrity**: Partial schema states may cause subsequent operations to fail unpredictably
- **Testing Reliability**: Tests may fail intermittently due to inconsistent cleanup
- **Operational Complexity**: Manual intervention required to fix inconsistent states
- **Recovery Difficulty**: No built-in rollback mechanism for failed operations

## Reproduction Steps

```python
import psycopg2
from psycopg2 import sql

# 1. Connect to Pgvector database
conn = psycopg2.connect("postgresql://user:pass@localhost:5432/mydb")
cursor = conn.cursor()

# 2. Attempt to create collection with invalid configuration
# This simulates a failure mid-operation
try:
    # Start collection creation
    cursor.execute(sql.SQL("""
        CREATE TABLE {} (
            id SERIAL PRIMARY KEY,
            embedding vector(%s)
        )
    """).format(sql.Identifier('test_collection_invalid')), [999999])  # Invalid dimension
    
except psycopg2.Error as e:
    # Operation fails here
    print(f"Error: {e}")

# 3. Check if partial state exists
cursor.execute("""
    SELECT table_name FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_name = 'test_collection_invalid'
""")
result = cursor.fetchone()

# ISSUE: Partial table may still exist or be in corrupted state
if result:
    print("BUG: Partial schema remnants detected!")

cursor.close()
conn.close()
```

## Expected Behavior

- If a schema operation fails, the database should be in a consistent state
- Either the operation completes fully OR the database is rolled back to pre-operation state
- No partial or corrupted schema elements should remain

## Actual Behavior

- Failed schema operations leave partial remnants in the database
- Subsequent operations may fail due to inconsistent state
- Manual cleanup required to restore proper state

## Root Cause Analysis

The Pgvector adapter implements schema operations as multi-step PostgreSQL transactions:
1. Create table statements
2. Create index statements
3. Grant permissions
4. Update metadata

If any step fails, there is no transaction rollback mechanism to undo previous steps, leaving the database in an inconsistent state.

### Code Location

File: `adapters/pgvector_adapter.py`

Method: `create_collection()`, `drop_collection()`

## Evidence

### Test Case Output
```
Test: schema_atomicity_test
Result: FAILED
Details: Collection creation failure left partial table in database
Database state: INCONSISTENT
```

### Log Evidence
```
2026-03-18 10:45:23 [ERROR] Pgvector: Failed to create collection 'test_invalid'
2026-03-18 10:45:24 [WARNING] Pgvector: Partial table 'test_invalid' still exists
2026-03-18 10:45:25 [ERROR] Pgvector: Subsequent operations failing due to inconsistent state
```

## Related Issues

- **Generic Pattern**: This issue affects all 4 database adapters (#1, #6, #13, #18)
- **Common Root Cause**: Lack of atomic transaction handling in schema operations
- **Cross-Database Consistency**: All adapters need similar fixes

## Suggested Fix

### Priority 1: Transaction Wrapping

```python
def create_collection(self, name, dimension, metric_type):
    """Create collection with proper transaction handling"""
    conn = self.get_connection()
    
    try:
        # Start transaction
        with conn:
            # All schema operations within single transaction
            cursor = conn.cursor()
            cursor.execute(sql.SQL("""
                CREATE TABLE {} (
                    id SERIAL PRIMARY KEY,
                    embedding vector(%s)
                )
            """).format(sql.Identifier(name)), [dimension])
            
            cursor.execute(sql.SQL("""
                CREATE INDEX {}_idx ON {} 
                USING ivfflat (embedding vector_cosine_ops)
            """).format(sql.Identifier(name), sql.Identifier(name)))
            
            # Grant permissions
            cursor.execute(sql.SQL("GRANT ALL ON TABLE {} TO PUBLIC").format(sql.Identifier(name)))
            cursor.execute(sql.SQL("GRANT ALL ON SEQUENCE {}_id_seq TO PUBLIC").format(sql.Identifier(name)))
            
            # All operations complete successfully
            conn.commit()
            
    except psycopg2.Error as e:
        # Transaction rollback is automatic with context manager
        conn.rollback()
        raise SchemaOperationError(f"Failed to create collection {name}: {e}")
```

### Priority 2: State Validation

Add validation after schema operations to ensure consistency:

```python
def validate_schema_state(self, expected_collections):
    """Validate that schema is in expected state"""
    cursor = self.conn.cursor()
    cursor.execute("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public'
    """)
    actual_collections = {row[0] for row in cursor.fetchall()}
    
    if actual_collections != expected_collections:
        raise SchemaInconsistencyError(
            f"Schema state inconsistent. Expected: {expected_collections}, "
            f"Actual: {actual_collections}"
        )
```

### Priority 3: Cleanup Mechanism

Implement cleanup for failed operations:

```python
def cleanup_failed_operation(self, operation_type, name):
    """Clean up remnants of failed schema operation"""
    cursor = self.conn.cursor()
    
    if operation_type == "create_collection":
        # Drop any partial tables
        cursor.execute(sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(sql.Identifier(name)))
        cursor.execute(sql.SQL("DROP INDEX IF EXISTS {}_idx CASCADE").format(sql.Identifier(name)))
    
    elif operation_type == "drop_collection":
        # Recreate dropped table if operation failed after drop
        # (This is more complex and may require recreation logic)
        pass
```

## Test Cases

### Unit Test
```python
def test_schema_atomicity_pgvector():
    """Test that failed schema operations don't leave partial state"""
    adapter = PgvectorAdapter(connection_string)
    
    # Create collection with invalid dimension (should fail)
    invalid_dimension = 999999
    
    with pytest.raises(SchemaOperationError):
        adapter.create_collection('test_atomic', invalid_dimension, 'cosine')
    
    # Verify no partial state exists
    collections = adapter.list_collections()
    assert 'test_atomic' not in collections
```

### Integration Test
```python
def test_schema_rollback_after_failure():
    """Test complete rollback after multi-step operation failure"""
    adapter = PgvectorAdapter(connection_string)
    
    # Attempt operation that will fail mid-process
    with pytest.raises(SchemaOperationError):
        # This simulates a failure after table creation but before indexing
        adapter.create_collection_with_delayed_failure('test_rollback', 128, 'cosine')
    
    # Verify database is in clean state
    cursor = adapter.conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM information_schema.tables 
        WHERE table_name = 'test_rollback'
    """)
    count = cursor.fetchone()[0]
    assert count == 0, "Partial table should not exist"
```

## Verification

- [x] Bug successfully reproduced
- [x] Root cause identified
- [ ] Fix implemented
- [ ] Fix tested
- [ ] Fix deployed to production

## Additional Notes

This is a critical data integrity issue that affects all schema operations in the Pgvector adapter. The fix requires careful transaction management and thorough testing to ensure:

1. All operations are properly wrapped in transactions
2. Rollback happens automatically on failure
3. No partial state can exist after any operation
4. Performance impact of transaction wrapping is acceptable

The fix should be applied consistently across all schema operation methods: `create_collection`, `drop_collection`, and any other schema-modifying operations.

## References

- Original Bug Report: `ISSUES.json` entry #18
- Bug Mining Evidence: `BUG_EVIDENCE_CHAIN_REPORT.md`
- Reproduction Results: `reproduction_results/bug_reproduction_results.json`
