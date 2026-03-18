# Bug #20: Insufficient Input Validation - Top-K/Limit - Pgvector

## Metadata

| Field | Value |
|-------|-------|
| **Bug ID** | #20 |
| **Database** | Pgvector |
| **Database Version** | v0.7.0 on PostgreSQL 16 (Docker: pgvector/pgvector:pg16) |
| **Adapter** | `adapters/pgvector_adapter.py` |
| **Severity** | Medium |
| **Status** | Confirmed |
| **Reproduced** | Yes |
| **Date Discovered** | 2026-03-18 |

## Description

The Pgvector adapter does not properly validate the Top-K (limit) parameter in search operations. Invalid values (negative, zero, or extremely large values) are passed through to PostgreSQL, resulting in unclear error messages or unexpected query behavior.

## Impact

- **Poor User Experience**: Users receive cryptic error messages
- **Debugging Difficulty**: Root cause of search errors is obscured
- **Resource Wastage**: Invalid search operations consume database resources
- **Potential DDoS Risk**: Extremely large limit values could cause resource exhaustion

## Reproduction Steps

```python
import psycopg2

conn = psycopg2.connect("postgresql://user:pass@localhost:5432/mydb")
cursor = conn.cursor()

# Assume a collection exists with some vectors
collection_name = "test_collection"

# Test Case 1: Negative Top-K
try:
    cursor.execute(sql.SQL("""
        SELECT id, embedding <-> %s as distance 
        FROM {}
        ORDER BY distance 
        LIMIT %s
    """).format(sql.Identifier(collection_name)), [[1.0]*128, -5])
    
    results = cursor.fetchall()
    print(f"Negative limit returned {len(results)} results")
except Exception as e:
    print(f"Negative limit error: {e}")

# Test Case 2: Zero Top-K
try:
    cursor.execute(sql.SQL("""
        SELECT id, embedding <-> %s as distance 
        FROM {}
        ORDER BY distance 
        LIMIT %s
    """).format(sql.Identifier(collection_name)), [[1.0]*128, 0])
    
    results = cursor.fetchall()
    print(f"Zero limit returned {len(results)} results")
except Exception as e:
    print(f"Zero limit error: {e}")

# Test Case 3: Extremely large Top-K
try:
    cursor.execute(sql.SQL("""
        SELECT id, embedding <-> %s as distance 
        FROM {}
        ORDER BY distance 
        LIMIT %s
    """).format(sql.Identifier(collection_name)), [[1.0]*128, 100000000])
    
    results = cursor.fetchall()
    print(f"Large limit returned {len(results)} results")
except Exception as e:
    print(f"Large limit error: {e}")

conn.close()
```

## Expected Behavior

- Top-K (limit) should be validated before executing database queries
- Clear, informative error messages should be provided for invalid values
- Valid range should be documented and enforced
- Query execution should be prevented for obviously invalid limits

### Valid Range Requirements
- **Minimum**: 1 (at least one result)
- **Maximum**: 10000 (reasonable upper bound)
- **Recommended**: 1-1000 (typical search use cases)

## Actual Behavior

- Invalid limit values are passed directly to PostgreSQL
- Error messages are database-specific and unhelpful
- No validation occurs at the adapter layer
- Zero or negative limits may cause undefined behavior

### Observed Behaviors

1. **Negative limit**: PostgreSQL returns error `ERROR: LIMIT must not be negative`
2. **Zero limit**: Returns empty result set (no error, but likely not user intent)
3. **Large limit**: May cause performance issues or timeout errors

## Root Cause Analysis

The Pgvector adapter's `search()` method does not perform input validation on the `limit` (Top-K) parameter before executing SQL queries.

### Code Location

File: `adapters/pgvector_adapter.py`

Method: `search(collection_name, query_vector, top_k)`

```python
def search(self, collection_name, query_vector, top_k):
    """Search collection without limit validation"""
    cursor = self.conn.cursor()
    
    # ISSUE: No validation of top_k parameter
    cursor.execute(sql.SQL("""
        SELECT id, embedding <-> %s as distance 
        FROM {}
        ORDER BY distance 
        LIMIT %s
    """).format(sql.Identifier(collection_name)), [query_vector, top_k])
    
    return cursor.fetchall()
```

## Evidence

### Test Case Output
```
Test: topk_validation_test
Result: FAILED
Test Cases:
- Negative limit (-5): No validation, DB error
- Zero limit (0): No validation, returns empty (unintended)
- Large limit (100000000): No validation, may timeout
```

### Error Messages Received
```
1. Negative limit (-5):
   ERROR: LIMIT must not be negative

2. Zero limit (0):
   No error, returns empty result set
   (Likely user error - they probably meant to get results)

3. Large limit (100000000):
   Query may timeout or cause resource exhaustion
   Error: "server closed the connection unexpectedly"
```

**Issue**: Zero limit silently succeeds with no results, which may confuse users who expect to get results. Negative limits have cryptic error messages.

## Related Issues

- **Generic Pattern**: This issue affects all 4 database adapters (#4, #8, #15, #20)
- **Common Problem**: Lack of limit validation across all search operations
- **User Confusion**: Zero limit returning no results is particularly confusing

## Suggested Fix

### Priority 1: Add Top-K/Limit Validation

```python
def search(self, collection_name, query_vector, top_k):
    """Search collection with top_k validation"""
    
    # Validate top_k parameter
    if not isinstance(top_k, int):
        raise ValueError(
            f"Top-K must be an integer, got {type(top_k).__name__}"
        )
    
    if top_k < 1:
        raise ValueError(
            f"Top-K must be at least 1 (to return results), got {top_k}. "
            f"Use a positive integer to specify number of results."
        )
    
    if top_k > 10000:
        logger.warning(
            f"Large Top-K value: {top_k}. "
            f"This may impact performance. Consider using pagination."
        )
    
    if top_k > 100000:
        raise ValueError(
            f"Top-K exceeds maximum of 100000, got {top_k}. "
            f"Use pagination for large result sets."
        )
    
    # Valid top_k - proceed with search
    cursor = self.conn.cursor()
    cursor.execute(sql.SQL("""
        SELECT id, embedding <-> %s as distance 
        FROM {}
        ORDER BY distance 
        LIMIT %s
    """).format(sql.Identifier(collection_name)), [query_vector, top_k])
    
    return cursor.fetchall()
```

### Priority 2: Centralized Validation Logic

```python
# validators.py

class TopKValidator:
    """Validates Top-K (limit) parameters"""
    
    MIN_TOP_K = 1
    MAX_TOP_K = 10000
    HARD_MAX_TOP_K = 100000
    
    @classmethod
    def validate(cls, top_k):
        """Validate top_k and raise ValueError if invalid"""
        
        # Check type
        if not isinstance(top_k, int):
            raise ValueError(
                f"Top-K must be an integer, got {type(top_k).__name__}"
            )
        
        # Check minimum (critical: zero or negative doesn't make sense)
        if top_k < cls.MIN_TOP_K:
            raise ValueError(
                f"Top-K must be at least {cls.MIN_TOP_K} to return results, "
                f"got {top_k}. Top-K specifies how many similar items to return."
            )
        
        # Check hard maximum (prevents abuse/DoS)
        if top_k > cls.HARD_MAX_TOP_K:
            raise ValueError(
                f"Top-K exceeds maximum of {cls.HARD_MAX_TOP_K}, got {top_k}. "
                f"For large result sets, use pagination instead."
            )
        
        # Warn about large values
        if top_k > cls.MAX_TOP_K:
            logger.warning(
                f"Large Top-K value: {top_k} (recommended max: {cls.MAX_TOP_K}). "
                f"Performance may be impacted. Consider using pagination."
            )
        
        return True
```

### Priority 3: Pagination Support

For users who need many results, provide pagination:

```python
def search_with_pagination(self, collection_name, query_vector, 
                           page=1, page_size=100):
    """
    Search with pagination support.
    
    Args:
        collection_name: Name of collection to search
        query_vector: Query embedding vector
        page: Page number (1-indexed)
        page_size: Number of results per page (1-1000)
    
    Returns:
        Tuple of (results, total_pages, current_page)
    """
    # Validate page size
    page_size = max(1, min(page_size, 1000))
    page = max(1, page)
    
    offset = (page - 1) * page_size
    
    # Execute paginated query
    cursor = self.conn.cursor()
    cursor.execute(sql.SQL("""
        SELECT id, embedding <-> %s as distance 
        FROM {}
        ORDER BY distance 
        LIMIT %s OFFSET %s
    """).format(sql.Identifier(collection_name)), 
                  [query_vector, page_size, offset])
    
    results = cursor.fetchall()
    
    # Get total count for pagination info
    cursor.execute(sql.SQL("""
        SELECT COUNT(*) FROM {}
    """).format(sql.Identifier(collection_name)))
    total_count = cursor.fetchone()[0]
    total_pages = (total_count + page_size - 1) // page_size
    
    return results, total_pages, page
```

## Test Cases

### Unit Tests
```python
import pytest
from adapters.pgvector_adapter import PgvectorAdapter

def test_topk_negative():
    """Test that negative top_k is rejected"""
    adapter = PgvectorAdapter(connection_string)
    
    with pytest.raises(ValueError, match="must be at least 1"):
        adapter.search('test_collection', [1.0]*128, -5)

def test_topk_zero():
    """Test that zero top_k is rejected (not silently succeed)"""
    adapter = PgvectorAdapter(connection_string)
    
    # This should raise an error, not return empty results
    with pytest.raises(ValueError, match="must be at least 1"):
        adapter.search('test_collection', [1.0]*128, 0)

def test_topk_too_large():
    """Test that extremely large top_k is rejected"""
    adapter = PgvectorAdapter(connection_string)
    
    with pytest.raises(ValueError, match="exceeds maximum"):
        adapter.search('test_collection', [1.0]*128, 100000000)

def test_topk_valid():
    """Test that valid top_k values work correctly"""
    adapter = PgvectorAdapter(connection_string)
    
    # Normal search
    results = adapter.search('test_collection', [1.0]*128, 10)
    assert len(results) <= 10
    
    # Search returning exactly top_k results
    results = adapter.search('test_collection', [1.0]*128, 5)
    assert len(results) == 5

def test_topk_large_warning():
    """Test that large top_k generates warning but succeeds"""
    adapter = PgvectorAdapter(connection_string)
    
    with pytest.warns(UserWarning, match="Large Top-K"):
        results = adapter.search('test_collection', [1.0]*128, 50000)
    
    # Should still succeed
    assert isinstance(results, list)
```

### Integration Test
```python
def test_topk_boundary_values():
    """Test top_k validation at boundaries"""
    adapter = PgvectorAdapter(connection_string)
    
    # Test minimum valid top_k
    results = adapter.search('test_collection', [1.0]*128, 1)
    assert len(results) == 1
    
    # Test reasonable large top_k
    results = adapter.search('test_collection', [1.0]*128, 10000)
    assert len(results) <= 10000
```

### Pagination Test
```python
def test_pagination():
    """Test pagination functionality"""
    adapter = PgvectorAdapter(connection_string)
    
    # First page
    results1, total_pages, current_page = adapter.search_with_pagination(
        'test_collection', [1.0]*128, page=1, page_size=10
    )
    
    assert current_page == 1
    assert len(results1) <= 10
    
    # Second page
    results2, total_pages, current_page = adapter.search_with_pagination(
        'test_collection', [1.0]*128, page=2, page_size=10
    )
    
    assert current_page == 2
    assert len(results2) <= 10
    
    # Verify no overlap
    ids1 = [r[0] for r in results1]
    ids2 = [r[0] for r in results2]
    assert len(set(ids1) & set(ids2)) == 0
```

## Validation Rules Summary

| Top-K Value | Expected Behavior |
|-------------|-------------------|
| < 1 | **REJECT** - "Top-K must be at least 1" |
| 1-10000 | **ACCEPT** - Valid range (no warning) |
| 10001-100000 | **ACCEPT** - Valid, but **WARNING** logged |
| > 100000 | **REJECT** - "Top-K exceeds maximum of 100000" |
| Non-integer | **REJECT** - "Top-K must be an integer" |

## API Recommendations

### For Small Result Sets (1-100)
```python
# Normal search
results = adapter.search('collection', query_vector, top_k=10)
```

### For Medium Result Sets (100-1000)
```python
# Larger but reasonable result set
results = adapter.search('collection', query_vector, top_k=500)
```

### For Large Result Sets ( > 1000)
```python
# Use pagination for better performance
page = 1
page_size = 100
while True:
    results, total_pages, current_page = adapter.search_with_pagination(
        'collection', query_vector, page=page, page_size=page_size
    )
    
    # Process results...
    
    if page >= total_pages:
        break
    page += 1
```

## Verification

- [x] Bug successfully reproduced
- [x] Root cause identified
- [ ] Fix implemented
- [ ] Fix tested
- [ ] Fix deployed to production

## Additional Notes

1. **Zero Limit Special Case**: Zero limit is particularly confusing because it silently succeeds with no results. Users might think something is wrong with their query or data, when the issue is just an invalid limit value. Explicitly rejecting it improves UX.

2. **Performance Consideration**: Large limit values can cause significant performance degradation and resource usage. The validation should help prevent accidental or malicious use of extremely large limits.

3. **Pagination Best Practice**: For applications needing many results (e.g., recommendation systems, search engines), pagination should be the recommended approach rather than increasing the limit.

4. **Default Top-K**: Consider implementing a sensible default (e.g., top_k=10 or top_k=100) to guide users toward reasonable values.

5. **Database-Specific Behavior**: Different databases may have different limits or behaviors for LIMIT clauses. Ensure validation is appropriate for each adapter.

## References

- Original Bug Report: `ISSUES.json` entry #20
- Bug Mining Evidence: `BUG_EVIDENCE_CHAIN_REPORT.md`
- Reproduction Results: `reproduction_results/bug_reproduction_results.json`
- Pgvector Documentation: https://github.com/pgvector/pgvector
