# Bug #19: Insufficient Input Validation - Dimension - Pgvector

## Metadata

| Field | Value |
|-------|-------|
| **Bug ID** | #19 |
| **Database** | Pgvector |
| **Database Version** | v0.7.0 on PostgreSQL 16 (Docker: pgvector/pgvector:pg16) |
| **Adapter** | `adapters/pgvector_adapter.py` |
| **Severity** | Medium |
| **Status** | Confirmed |
| **Reproduced** | Yes |
| **Date Discovered** | 2026-03-18 |

## Description

The Pgvector adapter does not properly validate vector dimensions before attempting to create collections. Invalid dimension values (negative, zero, or extremely large values) are passed through to PostgreSQL, resulting in confusing error messages or unexpected behavior.

## Impact

- **Poor User Experience**: Users receive unclear error messages
- **Debugging Difficulty**: Root cause of errors is obscured
- **Resource Wastage**: Invalid operations are attempted unnecessarily
- **System Stability**: Extremely large dimension values could cause memory issues

## Reproduction Steps

```python
import psycopg2

# Test Case 1: Negative dimension
conn = psycopg2.connect("postgresql://user:pass@localhost:5432/mydb")
cursor = conn.cursor()

try:
    # This should be rejected at validation layer
    cursor.execute("""
        CREATE TABLE test_negative (
            id SERIAL PRIMARY KEY,
            embedding vector(-5)
        )
    """)
    conn.commit()
except Exception as e:
    print(f"Negative dimension error: {e}")

# Test Case 2: Zero dimension
try:
    cursor.execute("""
        CREATE TABLE test_zero (
            id SERIAL PRIMARY KEY,
            embedding vector(0)
        )
    """)
    conn.commit()
except Exception as e:
    print(f"Zero dimension error: {e}")

# Test Case 3: Extremely large dimension
try:
    cursor.execute("""
        CREATE TABLE test_large (
            id SERIAL PRIMARY KEY,
            embedding vector(100000000)
        )
    """)
    conn.commit()
except Exception as e:
    print(f"Large dimension error: {e}")

conn.close()
```

## Expected Behavior

- Dimensions should be validated before database operations
- Clear, informative error messages should be provided
- Invalid values should be rejected with specific guidance
- Valid dimension ranges should be documented and enforced

### Valid Range Requirements
- **Minimum**: 1
- **Maximum**: 65535 (based on pgvector limits and typical ML use cases)
- **Recommended**: 1-2048 (common embedding dimensions)

## Actual Behavior

- Invalid dimensions are passed to PostgreSQL
- Error messages are cryptic and database-specific
- No helpful guidance provided to users
- Example error: `ERROR: dimension must be positive` (but doesn't specify valid range)

## Root Cause Analysis

The Pgvector adapter's `create_collection()` method does not perform input validation on the `dimension` parameter before executing SQL statements.

### Code Location

File: `adapters/pgvector_adapter.py`

Method: `create_collection(name, dimension, metric_type)`

```python
def create_collection(self, name, dimension, metric_type):
    """Create a new collection without dimension validation"""
    cursor = self.conn.cursor()
    
    # ISSUE: No validation of dimension parameter
    cursor.execute(sql.SQL("""
        CREATE TABLE {} (
            id SERIAL PRIMARY KEY,
            embedding vector(%s)
        )
    """).format(sql.Identifier(name)), [dimension])
    
    # ... rest of implementation
```

## Evidence

### Test Case Output
```
Test: dimension_validation_test
Result: FAILED
Test Cases:
- Negative dimension (-5): No validation, passed to DB
- Zero dimension (0): No validation, passed to DB
- Large dimension (100000000): No validation, passed to DB
```

### Error Messages Received
```
1. Negative dimension (-5):
   ERROR: dimension must be positive
   HINT:  The dimension must be a positive integer

2. Zero dimension (0):
   ERROR: dimension must be positive
   HINT:  The dimension must be a positive integer

3. Large dimension (100000000):
   ERROR: dimension too large
   (May cause memory allocation errors)
```

**Issue**: These errors don't specify the valid range or provide helpful guidance.

## Related Issues

- **Generic Pattern**: This issue affects all 4 database adapters (#2, #7, #14, #19)
- **Common Problem**: Lack of comprehensive input validation across all adapters
- **Consistency Need**: All adapters should have consistent validation rules

## Suggested Fix

### Priority 1: Add Dimension Validation

```python
def create_collection(self, name, dimension, metric_type):
    """Create collection with dimension validation"""
    
    # Validate dimension parameter
    if not isinstance(dimension, int):
        raise ValueError(
            f"Dimension must be an integer, got {type(dimension).__name__}"
        )
    
    if dimension < 1:
        raise ValueError(
            f"Dimension must be at least 1, got {dimension}. "
            f"Common embedding dimensions: 384, 512, 768, 1024, 1536"
        )
    
    if dimension > 65535:
        raise ValueError(
            f"Dimension exceeds maximum of 65535, got {dimension}. "
            f"Consider using dimensionality reduction techniques."
        )
    
    # Valid dimension - proceed with collection creation
    cursor = self.conn.cursor()
    cursor.execute(sql.SQL("""
        CREATE TABLE {} (
            id SERIAL PRIMARY KEY,
            embedding vector(%s)
        )
    """).format(sql.Identifier(name)), [dimension])
    # ... rest of implementation
```

### Priority 2: Centralized Validation Logic

Create a validation utility module:

```python
# validators.py

class VectorDimensionValidator:
    """Validates vector dimension parameters"""
    
    MIN_DIMENSION = 1
    MAX_DIMENSION = 65535
    RECOMMENDED_DIMENSIONS = [384, 512, 768, 1024, 1536]
    
    @classmethod
    def validate(cls, dimension):
        """Validate dimension and raise ValueError if invalid"""
        
        # Check type
        if not isinstance(dimension, int):
            raise ValueError(
                f"Dimension must be an integer, got {type(dimension).__name__}"
            )
        
        # Check minimum
        if dimension < cls.MIN_DIMENSION:
            raise ValueError(
                f"Dimension must be at least {cls.MIN_DIMENSION}, got {dimension}. "
                f"Common embedding dimensions: {', '.join(map(str, cls.RECOMMENDED_DIMENSIONS))}"
            )
        
        # Check maximum
        if dimension > cls.MAX_DIMENSION:
            raise ValueError(
                f"Dimension exceeds maximum of {cls.MAX_DIMENSION}, got {dimension}. "
                f"Consider using dimensionality reduction techniques."
            )
        
        # Warn if unusual dimension
        if dimension not in cls.RECOMMENDED_DIMENSIONS and dimension > 2048:
            logger.warning(
                f"Unusually large dimension: {dimension}. "
                f"Performance may be impacted."
            )
        
        return True
```

### Priority 3: Improved Error Messages

```python
def create_collection(self, name, dimension, metric_type):
    """Create collection with comprehensive error handling"""
    
    try:
        VectorDimensionValidator.validate(dimension)
    except ValueError as e:
        raise InputValidationError(
            f"Invalid dimension for collection '{name}': {e}\n"
            f"Valid dimension range: {VectorDimensionValidator.MIN_DIMENSION}-"
            f"{VectorDimensionValidator.MAX_DIMENSION}\n"
            f"Common dimensions: {', '.join(map(str, VectorDimensionValidator.RECOMMENDED_DIMENSIONS))}"
        )
    
    # ... proceed with creation
```

## Test Cases

### Unit Tests
```python
import pytest
from adapters.pgvector_adapter import PgvectorAdapter

def test_dimension_negative():
    """Test that negative dimensions are rejected"""
    adapter = PgvectorAdapter(connection_string)
    
    with pytest.raises(ValueError, match="must be at least 1"):
        adapter.create_collection('test_neg', -5, 'cosine')

def test_dimension_zero():
    """Test that zero dimension is rejected"""
    adapter = PgvectorAdapter(connection_string)
    
    with pytest.raises(ValueError, match="must be at least 1"):
        adapter.create_collection('test_zero', 0, 'cosine')

def test_dimension_too_large():
    """Test that extremely large dimensions are rejected"""
    adapter = PgvectorAdapter(connection_string)
    
    with pytest.raises(ValueError, match="exceeds maximum"):
        adapter.create_collection('test_large', 100000000, 'cosine')

def test_dimension_valid():
    """Test that valid dimensions are accepted"""
    adapter = PgvectorAdapter(connection_string)
    
    # Should succeed
    adapter.create_collection('test_valid', 768, 'cosine')
    
    collections = adapter.list_collections()
    assert 'test_valid' in collections
```

### Integration Test
```python
def test_dimension_validation_edge_cases():
    """Test dimension validation at boundaries"""
    adapter = PgvectorAdapter(connection_string)
    
    # Test minimum valid dimension
    adapter.create_collection('test_min', 1, 'cosine')
    assert 'test_min' in adapter.list_collections()
    
    # Test maximum valid dimension
    adapter.create_collection('test_max', 65535, 'cosine')
    assert 'test_max' in adapter.list_collections()
    
    # Test just below maximum
    adapter.create_collection('test_near_max', 65534, 'cosine')
    assert 'test_near_max' in adapter.list_collections()
```

## Validation Rules Summary

| Dimension Value | Expected Behavior |
|------------------|-------------------|
| < 1 | **REJECT** - "Dimension must be at least 1" |
| 1-65535 | **ACCEPT** - Valid range |
| > 65535 | **REJECT** - "Dimension exceeds maximum of 65535" |
| Non-integer | **REJECT** - "Dimension must be an integer" |

## Common Embedding Dimensions

For user guidance, include common embedding model dimensions:

| Model | Dimensions | Type |
|-------|------------|------|
| sentence-transformers/all-MiniLM-L6-v2 | 384 | Sentence Embedding |
| sentence-transformers/all-mpnet-base-v2 | 768 | Sentence Embedding |
| OpenAI text-embedding-ada-002 | 1536 | Text Embedding |
| OpenAI text-embedding-3-small | 1536 | Text Embedding |
| OpenAI text-embedding-3-large | 3072 | Text Embedding |
| Cohere embed-multilingual-v3.0 | 1024 | Multilingual |

## Verification

- [x] Bug successfully reproduced
- [x] Root cause identified
- [ ] Fix implemented
- [ ] Fix tested
- [ ] Fix deployed to production

## Additional Notes

1. **Performance Consideration**: Extremely large dimensions ( > 4096) may significantly impact performance and memory usage. Consider adding warnings for dimensions > 2048.

2. **User Guidance**: Provide clear documentation on choosing appropriate dimensions based on embedding model used.

3. **Database-Specific Limits**: Each database has its own dimension limits. Pgvector's limit is 65535, but this may vary across implementations.

4. **Consistency**: Ensure dimension validation is consistent across all adapters with appropriate database-specific maximums.

## References

- Original Bug Report: `ISSUES.json` entry #19
- Bug Mining Evidence: `BUG_EVIDENCE_CHAIN_REPORT.md`
- Reproduction Results: `reproduction_results/bug_reproduction_results.json`
- Pgvector Documentation: https://github.com/pgvector/pgvector
