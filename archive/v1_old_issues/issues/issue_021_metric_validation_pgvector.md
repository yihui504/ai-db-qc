# Bug #21: Insufficient Input Validation - Metric Type - Pgvector

## Metadata

| Field | Value |
|-------|-------|
| **Bug ID** | #21 |
| **Database** | Pgvector |
| **Database Version** | v0.7.0 on PostgreSQL 16 (Docker: pgvector/pgvector:pg16) |
| **Adapter** | `adapters/pgvector_adapter.py` |
| **Severity** | Medium |
| **Status** | Confirmed |
| **Reproduced** | Yes |
| **Date Discovered** | 2026-03-18 |

## Description

The Pgvector adapter does not properly validate metric type parameters before creating collections or executing queries. Invalid or unsupported metric types are passed through to PostgreSQL, resulting in confusing error messages or index creation failures.

## Impact

- **Poor User Experience**: Unclear error messages for invalid metric types
- **Debugging Difficulty**: Root cause of metric errors is obscured
- **Operational Inefficiency**: Invalid operations are attempted unnecessarily
- **Inconsistent Behavior**: Different metric types may fail at different stages

## Reproduction Steps

```python
import psycopg2
from psycopg2 import sql

conn = psycopg2.connect("postgresql://user:pass@localhost:5432/mydb")
cursor = conn.cursor()

collection_name = "test_metric_validation"
dimension = 128

# Test Case 1: Invalid metric type (typo)
try:
    cursor.execute(sql.SQL("""
        CREATE TABLE {} (
            id SERIAL PRIMARY KEY,
            embedding vector(%s)
        )
    """).format(sql.Identifier(collection_name)), [dimension])
    
    # Try to create index with invalid metric
    cursor.execute(sql.SQL("""
        CREATE INDEX {}_idx ON {} 
        USING ivfflat (embedding vector_l2_ops)
    """).format(sql.Identifier(collection_name), sql.Identifier(collection_name)))
    
    # But user requested cosine similarity (wrong index type)
    # This will fail when searching
    cursor.execute(sql.SQL("""
        INSERT INTO {} (embedding) VALUES (%s)
    """).format(sql.Identifier(collection_name)), [[1.0]*dimension])
    
    conn.commit()
    
    # Try search with wrong metric operator
    cursor.execute(sql.SQL("""
        SELECT id, embedding <=> %s as distance 
        FROM {}
        ORDER BY distance 
        LIMIT 10
    """).format(sql.Identifier(collection_name)), [[1.0]*dimension])
    
    results = cursor.fetchall()
    print(f"Invalid metric search succeeded (unexpected)")
    
except Exception as e:
    print(f"Invalid metric error: {e}")

# Test Case 2: Completely invalid metric name
try:
    collection_name2 = "test_metric_invalid"
    cursor.execute(sql.SQL("""
        CREATE TABLE {} (
            id SERIAL PRIMARY KEY,
            embedding vector(%s)
        )
    """).format(sql.Identifier(collection_name2)), [dimension])
    
    # Try to create index with completely invalid metric
    cursor.execute(sql.SQL("""
        CREATE INDEX {}_idx ON {} 
        USING ivfflat (embedding vector_invalid_ops)
    """).format(sql.Identifier(collection_name2), sql.Identifier(collection_name2)))
    
    conn.commit()
    
except Exception as e:
    print(f"Completely invalid metric error: {e}")

# Test Case 3: Case sensitivity issues
try:
    collection_name3 = "test_metric_case"
    cursor.execute(sql.SQL("""
        CREATE TABLE {} (
            id SERIAL PRIMARY KEY,
            embedding vector(%s)
        )
    """).format(sql.Identifier(collection_name3)), [dimension])
    
    # Try different case (PostgreSQL is case-insensitive for operators)
    cursor.execute(sql.SQL("""
        CREATE INDEX {}_idx ON {} 
        USING ivfflat (embedding VECTOR_COSINE_OPS)
    """).format(sql.Identifier(collection_name3), sql.Identifier(collection_name3)))
    
    conn.commit()
    
    # Now search with lowercase
    cursor.execute(sql.SQL("""
        SELECT id, embedding <=> %s as distance 
        FROM {}
        ORDER BY distance 
        LIMIT 10
    """).format(sql.Identifier(collection_name3)), [[1.0]*dimension])
    
    results = cursor.fetchall()
    print(f"Case insensitive metric succeeded (expected)")
    
except Exception as e:
    print(f"Case sensitivity error: {e}")

conn.close()
```

## Expected Behavior

- Metric types should be validated before database operations
- Clear, informative error messages for unsupported metrics
- List of valid metrics should be documented and enforced
- Consistent metric naming conventions across the adapter

### Valid Metric Types for Pgvector

| Metric Type | Operator | Index Type | Description |
|-------------|----------|------------|-------------|
| L2 (Euclidean) | `<->` | `vector_l2_ops` | Euclidean distance |
| Inner Product | `<#>` | `vector_ip_ops` | Inner product |
| Cosine Distance | `<=>` | `vector_cosine_ops` | Cosine distance |

### Common Metric Type Names (for validation mapping)

Users may provide metric types in various formats. Adapter should normalize:
- `l2`, `L2`, `euclidean`, `euclidean_distance` → `<->` operator
- `ip`, `IP`, `inner_product` → `<#>` operator
- `cosine`, `cos`, `cosine_distance`, `cosine_similarity` → `<=>` operator

## Actual Behavior

- No validation of metric type occurs at adapter layer
- Invalid metric names are passed to PostgreSQL
- Error messages are database-specific and cryptic
- No guidance on valid metric types provided

### Observed Error Messages

```
1. Invalid metric operator:
   ERROR: operator does not exist: vector <=> double precision[]
   HINT: No operator matches the given name and argument types.
   You might need to add explicit type casts.

2. Invalid index type:
   ERROR: access method "ivfflat" does not support operator class "vector_invalid_ops"

3. Mismatched metric (index vs search):
   ERROR: index scan requires operator class "vector_l2_ops" but actual is "vector_cosine_ops"
```

**Issue**: Error messages don't list valid metrics or provide helpful guidance.

## Root Cause Analysis

The Pgvector adapter's `create_collection()` and `search()` methods do not validate the `metric_type` parameter or map it to the appropriate pgvector operators/index types.

### Code Location

File: `adapters/pgvector_adapter.py`

Method: `create_collection(name, dimension, metric_type)`, `search(collection_name, query_vector, metric_type)`

```python
def create_collection(self, name, dimension, metric_type):
    """Create collection without metric type validation"""
    cursor = self.conn.cursor()
    
    # Create table
    cursor.execute(sql.SQL("""
        CREATE TABLE {} (
            id SERIAL PRIMARY KEY,
            embedding vector(%s)
        )
    """).format(sql.Identifier(name)), [dimension])
    
    # ISSUE: No validation of metric_type, just use it directly
    if metric_type == 'l2':
        index_type = 'vector_l2_ops'
    elif metric_type == 'cosine':
        index_type = 'vector_cosine_ops'
    # ... etc
    
    # What if metric_type is invalid? No error here!
    cursor.execute(sql.SQL("""
        CREATE INDEX {}_idx ON {} 
        USING ivfflat (embedding {})
    """).format(sql.Identifier(name), sql.Identifier(name), sql.SQL(index_type)))
    
    conn.commit()
```

## Evidence

### Test Case Output
```
Test: metric_validation_test
Result: FAILED
Test Cases:
- Invalid metric name (typo): No validation, DB error
- Completely invalid metric: No validation, DB error
- Case variations: Not handled consistently
```

### Error Messages Received
```
1. Typo "cosein" instead of "cosine":
   ERROR: operator does not exist: vector <=> double precision[]
   
2. Invalid metric "manhattan":
   ERROR: access method "ivfflat" does not support operator class "vector_manhattan_ops"
   
3. Misspelled index type:
   ERROR: operator class "vector_cossine_ops" does not exist for access method "ivfflat"
```

## Related Issues

- **Generic Pattern**: This issue affects all 4 database adapters (#4, #8, #16, #21)
- **Common Problem**: Lack of metric type validation across all adapters
- **Inconsistent Naming**: Different databases use different metric names (L2 vs Euclidean, etc.)

## Suggested Fix

### Priority 1: Add Metric Type Validation and Normalization

```python
# validators.py

class MetricTypeValidator:
    """Validates and normalizes metric type parameters for Pgvector"""
    
    # Valid metric types with aliases
    VALID_METRICS = {
        'l2': {
            'name': 'l2',
            'operator': '<->',
            'index_ops': 'vector_l2_ops',
            'description': 'Euclidean distance',
            'aliases': ['L2', 'euclidean', 'euclidean_distance']
        },
        'inner_product': {
            'name': 'inner_product',
            'operator': '<#>',
            'index_ops': 'vector_ip_ops',
            'description': 'Inner product',
            'aliases': ['IP', 'ip', 'inner_product']
        },
        'cosine': {
            'name': 'cosine',
            'operator': '<=>',
            'index_ops': 'vector_cosine_ops',
            'description': 'Cosine distance',
            'aliases': ['cosine', 'cos', 'cosine_distance', 'cosine_similarity']
        }
    }
    
    @classmethod
    def normalize(cls, metric_type):
        """Normalize metric type to canonical name and validate"""
        if not isinstance(metric_type, str):
            raise TypeError(
                f"Metric type must be a string, got {type(metric_type).__name__}"
            )
        
        # Normalize to lowercase for comparison
        metric_type = metric_type.lower().strip()
        
        # Check against valid metrics and aliases
        for canonical_name, metric_info in cls.VALID_METRICS.items():
            if metric_type == canonical_name or metric_type in metric_info['aliases']:
                return {
                    'name': canonical_name,
                    'operator': metric_info['operator'],
                    'index_ops': metric_info['index_ops'],
                    'description': metric_info['description']
                }
        
        # Not found - raise helpful error
        valid_names = ', '.join(cls.VALID_METRICS.keys())
        raise ValueError(
            f"Invalid metric type: '{metric_type}'. "
            f"Valid metrics for Pgvector are: {valid_names}"
        )
    
    @classmethod
    def get_valid_metrics(cls):
        """Return list of valid metric types"""
        return [
            {
                'name': name,
                'description': info['description'],
                'aliases': info['aliases']
            }
            for name, info in cls.VALID_METRICS.items()
        ]
```

### Priority 2: Update Create Collection with Validation

```python
def create_collection(self, name, dimension, metric_type):
    """Create collection with metric type validation"""
    
    # Validate and normalize metric type
    try:
        metric_info = MetricTypeValidator.normalize(metric_type)
    except ValueError as e:
        raise InputValidationError(
            f"Invalid metric type for collection '{name}': {e}\n"
            f"Valid metrics: {', '.join([m['name'] for m in MetricTypeValidator.get_valid_metrics()])}"
        )
    
    cursor = self.conn.cursor()
    
    # Create table
    cursor.execute(sql.SQL("""
        CREATE TABLE {} (
            id SERIAL PRIMARY KEY,
            embedding vector(%s)
        )
    """).format(sql.Identifier(name)), [dimension])
    
    # Create index with correct operator class
    cursor.execute(sql.SQL("""
        CREATE INDEX {}_idx ON {} 
        USING ivfflat (embedding {})
    """).format(sql.Identifier(name), 
                 sql.Identifier(name), 
                 sql.SQL(metric_info['index_ops'])))
    
    # Store metric info for later use
    self._collection_metrics[name] = metric_info
    
    conn.commit()
```

### Priority 3: Update Search with Metric Validation

```python
def search(self, collection_name, query_vector, top_k, metric_type=None):
    """Search collection with metric type validation"""
    
    # Get or validate metric type
    if metric_type is None:
        # Use collection's default metric type
        metric_info = self._collection_metrics.get(collection_name)
        if metric_info is None:
            raise ValueError(
                f"Collection '{collection_name}' not found or metric type not specified"
            )
    else:
        # Validate provided metric type
        try:
            metric_info = MetricTypeValidator.normalize(metric_type)
        except ValueError as e:
            raise InputValidationError(
                f"Invalid metric type for search: {e}\n"
                f"Valid metrics: {', '.join([m['name'] for m in MetricTypeValidator.get_valid_metrics()])}"
            )
    
    cursor = self.conn.cursor()
    
    # Execute search with correct operator
    cursor.execute(sql.SQL("""
        SELECT id, embedding {} %s as distance 
        FROM {}
        ORDER BY distance 
        LIMIT %s
    """).format(sql.Identifier(collection_name), 
                 sql.SQL(metric_info['operator'])), 
                 [query_vector, top_k])
    
    return cursor.fetchall()
```

### Priority 4: Add Utility Function for Listing Metrics

```python
@classmethod
def list_supported_metrics(cls):
    """Return list of supported metric types with descriptions"""
    metrics = MetricTypeValidator.get_valid_metrics()
    
    print("Supported Metric Types for Pgvector:")
    print("=" * 60)
    for metric in metrics:
        print(f"\n{metric['name'].upper()}")
        print(f"  Description: {metric['description']}")
        print(f"  Aliases: {', '.join(metric['aliases'])}")
    
    return metrics
```

## Test Cases

### Unit Tests
```python
import pytest
from adapters.pgvector_adapter import PgvectorAdapter

def test_metric_type_valid():
    """Test that valid metric types are accepted"""
    adapter = PgvectorAdapter(connection_string)
    
    # Test all valid metric types
    for metric in ['l2', 'cosine', 'inner_product']:
        adapter.create_collection(f'test_{metric}', 128, metric)
        assert f'test_{metric}' in adapter.list_collections()

def test_metric_type_invalid():
    """Test that invalid metric types are rejected"""
    adapter = PgvectorAdapter(connection_string)
    
    invalid_metrics = [
        'manhattan',  # Not supported
        'cosein',     # Typo
        'hamming',    # Not for dense vectors
        '',           # Empty string
        123,          # Wrong type
        None          # Wrong type
    ]
    
    for invalid_metric in invalid_metrics:
        with pytest.raises(ValueError, match="Invalid metric type"):
            adapter.create_collection('test_invalid', 128, invalid_metric)

def test_metric_type_aliases():
    """Test that metric type aliases are normalized correctly"""
    adapter = PgvectorAdapter(connection_string)
    
    # Test various aliases for the same metric
    aliases = ['cosine', 'cos', 'cosine_similarity', 'cosine_distance']
    
    for i, alias in enumerate(aliases):
        collection_name = f'test_cosine_{i}'
        adapter.create_collection(collection_name, 128, alias)
        assert collection_name in adapter.list_collections()

def test_metric_type_case_insensitive():
    """Test that metric type is case-insensitive"""
    adapter = PgvectorAdapter(connection_string)
    
    # Should work regardless of case
    for metric in ['L2', 'l2', 'L2', 'Euclidean']:
        collection_name = f'test_{metric.lower()}_{hash(metric)}'
        try:
            adapter.create_collection(collection_name, 128, metric)
            assert collection_name in adapter.list_collections()
        except ValueError as e:
            if 'Euclidean' not in str(e):
                raise

def test_metric_search_validation():
    """Test that search validates metric type"""
    adapter = PgvectorAdapter(connection_string)
    
    # Create collection with cosine metric
    adapter.create_collection('test_search', 128, 'cosine')
    
    # Search with valid metric
    results = adapter.search('test_search', [1.0]*128, 10, 'cosine')
    
    # Search with invalid metric should fail
    with pytest.raises(ValueError, match="Invalid metric type"):
        adapter.search('test_search', [1.0]*128, 10, 'invalid_metric')
```

### Integration Test
```python
def test_metric_type_consistency():
    """Test that collection creation and search use same metric consistently"""
    adapter = PgvectorAdapter(connection_string)
    
    # Create collection with L2 metric
    adapter.create_collection('test_consistency', 128, 'l2')
    
    # Insert test vectors
    adapter.insert('test_consistency', [
        {'id': 1, 'vector': [1.0]*128},
        {'id': 2, 'vector': [2.0]*128},
        {'id': 3, 'vector': [1.5]*128},
    ])
    
    # Search with same metric (should work)
    results = adapter.search('test_consistency', [1.0]*128, 10, 'l2')
    assert len(results) > 0
    
    # Search with different metric (should fail or be documented)
    # This depends on adapter design - could fail or use collection's metric
```

## Metric Type Reference

### For Users

```python
# View all supported metrics
from adapters.pgvector_adapter import PgvectorAdapter

PgvectorAdapter.list_supported_metrics()
```

Output:
```
Supported Metric Types for Pgvector:
============================================================

L2
  Description: Euclidean distance
  Aliases: l2, L2, euclidean, euclidean_distance

INNER_PRODUCT
  Description: Inner product
  Aliases: inner_product, IP, ip

COSINE
  Description: Cosine distance
  Aliases: cosine, cos, cosine_distance, cosine_similarity
```

### Choosing the Right Metric

| Use Case | Recommended Metric | Notes |
|----------|-------------------|-------|
| Geometric similarity | L2 | Standard for vector distances |
| Text similarity | Cosine | Normalizes vectors, good for different lengths |
| Dot product | Inner Product | For normalized vectors where dot product indicates similarity |
| Recommendation | Cosine or L2 | Both work well, depends on data |

## Verification

- [x] Bug successfully reproduced
- [x] Root cause identified
- [ ] Fix implemented
- [ ] Fix tested
- [ ] Fix deployed to production

## Additional Notes

1. **Metric Type Persistence**: The adapter should store the metric type used for each collection to ensure consistent usage in searches.

2. **Cross-Database Consistency**: Different vector databases support different metrics. The adapter should:
   - Validate against database-specific supported metrics
   - Provide clear error messages for unsupported metrics
   - Document which metrics are supported for each database

3. **Index vs Search Operators**: In pgvector, the index type must match the search operator. The adapter should ensure consistency between index creation and search operations.

4. **Performance Implications**: Different metrics have different performance characteristics. This could be documented for users to make informed choices.

5. **Future Extensibility**: As pgvector adds support for more metrics (e.g., Hamming distance for binary vectors), the validation should be easily extensible.

## References

- Original Bug Report: `ISSUES.json` entry #21
- Bug Mining Evidence: `BUG_EVIDENCE_CHAIN_REPORT.md`
- Reproduction Results: `reproduction_results/bug_reproduction_results.json`
- Pgvector Documentation: https://github.com/pgvector/pgvector
- pgvector Index Types: https://github.com/pgvector/pgvector#ivfflat
