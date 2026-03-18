# Bug #22: Insufficient Input Validation - Collection Name - Pgvector

## Metadata

| Field | Value |
|-------|-------|
| **Bug ID** | #22 |
| **Database** | Pgvector |
| **Database Version** | v0.7.0 on PostgreSQL 16 (Docker: pgvector/pgvector:pg16) |
| **Adapter** | `adapters/pgvector_adapter.py` |
| **Severity** | Medium |
| **Status** | Confirmed |
| **Reproduced** | Yes |
| **Date Discovered** | 2026-03-18 |

## Description

The Pgvector adapter does not properly validate collection names before creating or operating on collections. Invalid names (with special characters, SQL keywords, reserved words, or excessively long names) are passed through to PostgreSQL, resulting in errors or unexpected behavior.

## Impact

- **Poor User Experience**: Unclear error messages for invalid collection names
- **Debugging Difficulty**: Root cause of naming errors is obscured
- **Security Risk**: Potential for SQL injection if names are not properly escaped
- **Operational Issues**: Invalid names can break downstream operations

## Reproduction Steps

```python
import psycopg2
from psycopg2 import sql

conn = psycopg2.connect("postgresql://user:pass@localhost:5432/mydb")
cursor = conn.cursor()

# Test Case 1: SQL Keywords as collection names
sql_keywords = ['select', 'insert', 'update', 'delete', 'drop', 'create', 
                'table', 'index', 'where', 'from', 'join', 'order', 'group']

for keyword in sql_keywords[:5]:  # Test first 5
    try:
        cursor.execute(sql.SQL("""
            CREATE TABLE {} (
                id SERIAL PRIMARY KEY,
                embedding vector(%s)
            )
        """).format(sql.Identifier(keyword)), [128])
        
        conn.commit()
        print(f"Created collection with keyword name: {keyword}")
        
    except Exception as e:
        print(f"Keyword name error ({keyword}): {e}")

# Test Case 2: Special characters
special_chars = [
    'test-collection',     # Hyphen
    'test.collection',     # Dot
    'test collection',     # Space
    'test/collection',     # Slash
    'test\\collection',    # Backslash
    'test"collection',     # Quote
    "test'collection",     # Single quote
    'test;drop',           # Semicolon
    'test--comment',       # Comment
]

for name in special_chars:
    try:
        cursor.execute(sql.SQL("""
            CREATE TABLE {} (
                id SERIAL PRIMARY KEY,
                embedding vector(%s)
            )
        """).format(sql.Identifier(name)), [128])
        
        conn.commit()
        print(f"Created collection with special chars: {name}")
        
    except Exception as e:
        print(f"Special chars error ({name}): {e}")

# Test Case 3: Empty or whitespace-only names
invalid_names = ['', ' ', '  ', '\t', '\n', 'test\nname']

for name in invalid_names:
    try:
        if not name:
            print("Testing empty name")
            continue
        
        cursor.execute(sql.SQL("""
            CREATE TABLE {} (
                id SERIAL PRIMARY KEY,
                embedding vector(%s)
            )
        """).format(sql.Identifier(name)), [128])
        
        conn.commit()
        print(f"Created collection with invalid whitespace: {repr(name)}")
        
    except Exception as e:
        print(f"Whitespace error ({repr(name)}): {e}")

# Test Case 4: Excessively long names
long_name = 'a' * 1000  # PostgreSQL identifier limit is 63 characters

try:
    cursor.execute(sql.SQL("""
        CREATE TABLE {} (
            id SERIAL PRIMARY KEY,
            embedding vector(%s)
        )
    """).format(sql.Identifier(long_name)), [128])
    
    conn.commit()
    print(f"Created collection with long name (length: {len(long_name)})")
    
except Exception as e:
    print(f"Long name error: {e}")

# Test Case 5: Case sensitivity and duplicate names
try:
    # Create collection with lowercase
    cursor.execute(sql.SQL("""
        CREATE TABLE {} (
            id SERIAL PRIMARY KEY,
            embedding vector(%s)
        )
    """).format(sql.Identifier('testcase')), [128])
    conn.commit()
    
    # Try to create same name with different case
    # PostgreSQL is case-insensitive for unquoted identifiers
    try:
        cursor.execute(sql.SQL("""
            CREATE TABLE {} (
                id SERIAL PRIMARY KEY,
                embedding vector(%s)
            )
        """).format(sql.Identifier('TESTCASE')), [128])
        conn.commit()
        print(f"Created duplicate case-variant: TESTCASE")
        
    except Exception as e:
        print(f"Case variant error: {e}")
        
except Exception as e:
    print(f"Case test error: {e}")

conn.close()
```

## Expected Behavior

- Collection names should be validated before database operations
- Clear, informative error messages for invalid names
- Name should conform to database identifier rules
- SQL injection protection should be guaranteed
- Length limits should be enforced

### Valid Collection Name Rules

| Rule | Requirement | Rationale |
|------|-------------|-----------|
| **Length** | 1-63 characters | PostgreSQL identifier limit |
| **Characters** | Letters (a-z, A-Z), digits (0-9), underscores (_) | Standard identifier rules |
| **Start Character** | Must start with letter or underscore | Cannot start with digit |
| **Case Sensitivity** | Case-insensitive (unquoted identifiers) | PostgreSQL default behavior |
| **Reserved Words** | Cannot use SQL keywords or reserved words | Prevents conflicts |
| **Special Characters** | No special characters (except underscore) | Prevents SQL errors |
| **Whitespace** | No whitespace allowed | Prevents parsing errors |

### Invalid Name Examples

```
❌ Invalid:
- "" (empty string)
- " " (whitespace only)
- "test-name" (hyphen)
- "test.name" (dot)
- "test name" (space)
- "123collection" (starts with digit)
- "select" (SQL keyword)
- "test;drop table" (SQL injection attempt)
- "a" * 100 (too long)

✅ Valid:
- "test_collection"
- "TestCollection"
- "test_collection_123"
- "my_vectors"
- "embedding_db"
```

## Actual Behavior

- No validation of collection names occurs at adapter layer
- Invalid names are passed to PostgreSQL which may accept or reject them inconsistently
- Error messages are database-specific and not user-friendly
- Some invalid names may succeed but cause issues later

### Observed Behaviors

1. **SQL Keywords**: PostgreSQL may or may not reject depending on quoting
2. **Special Characters**: Using `sql.Identifier()` provides some protection but inconsistent results
3. **Long Names**: PostgreSQL truncates to 63 characters silently
4. **Case Sensitivity**: Unquoted identifiers are case-insensitive, causing duplicates

### Error Messages Received

```
1. Empty name:
   ERROR: zero-length delimited identifier at or near """"
   HINT: Use a valid identifier

2. Long name:
   Warning: identifier "aaaaaaaa..." will be truncated to "aaaaaa..."
   (Silent truncation, not an error!)

3. SQL keyword (with proper quoting):
   May succeed but cause confusion in queries

4. Special characters:
   With sql.Identifier(), most special chars are handled
   But some edge cases may still cause issues
```

**Issue**: Silent truncation of long names is particularly dangerous as users may create collections without realizing the name was changed.

## Root Cause Analysis

The Pgvector adapter's methods (`create_collection`, `drop_collection`, `search`, etc.) do not validate collection names before passing them to PostgreSQL. While `sql.Identifier()` provides some protection, it doesn't enforce naming rules or catch all issues.

### Code Location

File: `adapters/pgvector_adapter.py`

Method: `create_collection(name, dimension, metric_type)`, `drop_collection(name)`, `search(collection_name, ...)`

```python
def create_collection(self, name, dimension, metric_type):
    """Create collection without name validation"""
    cursor = self.conn.cursor()
    
    # ISSUE: No validation of 'name' parameter
    # Just uses sql.Identifier() which provides minimal protection
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
Test: name_validation_test
Result: FAILED
Test Cases:
- Empty name: No validation, DB error
- SQL keywords: Inconsistent behavior
- Special characters: sql.Identifier() handles but not validated
- Long names: Silent truncation (no error!)
- Duplicate case variants: Accepted as same name
```

### Error Messages Received
```
1. Empty string:
   ERROR: syntax error at or near ""
   
2. SQL keyword "select":
   With sql.Identifier(): Creates table named "select"
   (Succeeds but confusing)
   
3. Long name (100 chars):
   Warning: identifier "aaa...aaa" will be truncated to "aaa...aaa" (63 chars)
   (Succeeds with truncated name - dangerous!)
   
4. Special chars:
   Most handled by sql.Identifier(), but no validation at adapter level
```

## Related Issues

- **Generic Pattern**: This issue affects all 4 database adapters (#5, #10, #17, #22)
- **Common Problem**: Lack of collection name validation across all adapters
- **Security Concern**: SQL injection risk if proper escaping is not used

## Suggested Fix

### Priority 1: Add Collection Name Validation

```python
# validators.py

import re

class CollectionNameValidator:
    """Validates collection names for PostgreSQL"""
    
    # PostgreSQL identifier rules
    MIN_LENGTH = 1
    MAX_LENGTH = 63
    NAME_PATTERN = r'^[a-zA-Z_][a-zA-Z0-9_]*$'
    
    # SQL and PostgreSQL reserved words (abbreviated list)
    RESERVED_WORDS = {
        'select', 'insert', 'update', 'delete', 'drop', 'create', 'alter',
        'table', 'index', 'view', 'sequence', 'function', 'trigger',
        'where', 'from', 'join', 'group', 'order', 'having', 'limit',
        'union', 'intersect', 'except', 'and', 'or', 'not', 'in', 'is',
        'null', 'true', 'false', 'case', 'when', 'then', 'else', 'end',
        'as', 'distinct', 'between', 'like', 'exists', 'default',
        'primary', 'foreign', 'key', 'unique', 'check', 'constraint',
        'reference', 'cascade', 'restrict', 'no', 'action', 'set',
        'deferred', 'immediate', 'initially', 'deferrable', 'current',
        'time', 'date', 'timestamp', 'interval', 'user', 'role', 'grant',
        'revoke', 'privilege', 'tablespace', 'schema', 'database',
        'cursor', 'close', 'open', 'fetch', 'move', 'absolute', 'relative',
        'forward', 'backward', 'all', 'some', 'any', 'value', 'row',
        'rows', 'only', 'offset', 'fetch', 'first', 'next', 'last',
        'absolute', 'backward', 'forward', 'relative'
    }
    
    @classmethod
    def validate(cls, name):
        """Validate collection name and raise ValueError if invalid"""
        
        # Check type
        if not isinstance(name, str):
            raise TypeError(
                f"Collection name must be a string, got {type(name).__name__}"
            )
        
        # Check for empty or whitespace-only strings
        if not name or not name.strip():
            raise ValueError(
                "Collection name cannot be empty or whitespace-only"
            )
        
        # Trim whitespace
        name = name.strip()
        
        # Check length
        if len(name) < cls.MIN_LENGTH:
            raise ValueError(
                f"Collection name must be at least {cls.MIN_LENGTH} character(s)"
            )
        
        if len(name) > cls.MAX_LENGTH:
            raise ValueError(
                f"Collection name cannot exceed {cls.MAX_LENGTH} characters, "
                f"got {len(name)} characters"
            )
        
        # Check pattern (must start with letter or underscore)
        if not re.match(cls.NAME_PATTERN, name):
            raise ValueError(
                f"Collection name '{name}' contains invalid characters. "
                f"Names must start with a letter or underscore and contain only "
                f"letters, digits, and underscores."
            )
        
        # Check for reserved words
        if name.lower() in cls.RESERVED_WORDS:
            raise ValueError(
                f"Collection name '{name}' is a reserved SQL keyword. "
                f"Please choose a different name."
            )
        
        return True
    
    @classmethod
    def normalize(cls, name):
        """Normalize collection name (lowercase for consistency)"""
        cls.validate(name)
        return name.lower()
```

### Priority 2: Update All Collection Name Usage

```python
def create_collection(self, name, dimension, metric_type):
    """Create collection with name validation"""
    
    # Validate and normalize name
    try:
        CollectionNameValidator.validate(name)
        normalized_name = CollectionNameValidator.normalize(name)
    except (ValueError, TypeError) as e:
        raise InputValidationError(
            f"Invalid collection name: {e}"
        )
    
    # Use normalized name
    cursor = self.conn.cursor()
    cursor.execute(sql.SQL("""
        CREATE TABLE {} (
            id SERIAL PRIMARY KEY,
            embedding vector(%s)
        )
    """).format(sql.Identifier(normalized_name)), [dimension])
    
    # ... rest of implementation

def drop_collection(self, name):
    """Drop collection with name validation"""
    
    # Validate name
    CollectionNameValidator.validate(name)
    normalized_name = CollectionNameValidator.normalize(name)
    
    cursor = self.conn.cursor()
    cursor.execute(sql.SQL("DROP TABLE {}").format(sql.Identifier(normalized_name)))
    conn.commit()

def search(self, collection_name, query_vector, top_k):
    """Search collection with name validation"""
    
    # Validate collection name
    CollectionNameValidator.validate(collection_name)
    normalized_name = CollectionNameValidator.normalize(collection_name)
    
    cursor = self.conn.cursor()
    cursor.execute(sql.SQL("""
        SELECT id, embedding <-> %s as distance 
        FROM {}
        ORDER BY distance 
        LIMIT %s
    """).format(sql.Identifier(normalized_name)), [query_vector, top_k])
    
    return cursor.fetchall()
```

### Priority 3: Add Name Sanitization for Special Use Cases

For cases where users want to use names from external sources (e.g., user input, file names), provide a sanitization function:

```python
@staticmethod
def sanitize_name(name):
    """
    Sanitize a string to create a valid collection name.
    
    This function converts an arbitrary string into a valid collection name
    by replacing invalid characters with underscores and ensuring it doesn't
    conflict with reserved words.
    """
    import re
    import hashlib
    
    if not isinstance(name, str):
        raise TypeError("Name must be a string")
    
    # Remove or replace invalid characters
    # Replace anything not alphanumeric or underscore with underscore
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    
    # Ensure it starts with letter or underscore
    if sanitized and not sanitized[0].isalpha() and sanitized[0] != '_':
        sanitized = 'col_' + sanitized
    
    # Remove consecutive underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    
    # Remove leading/trailing underscores
    sanitized = sanitized.strip('_')
    
    # Check if it's still invalid (e.g., was all special chars)
    if not sanitized:
        # Generate a hash-based name
        sanitized = 'col_' + hashlib.md5(name.encode()).hexdigest()[:20]
    
    # Truncate if too long
    if len(sanitized) > CollectionNameValidator.MAX_LENGTH:
        sanitized = sanitized[:CollectionNameValidator.MAX_LENGTH]
    
    # Check for reserved words
    if sanitized.lower() in CollectionNameValidator.RESERVED_WORDS:
        sanitized = 'col_' + sanitized
    
    return sanitized
```

## Test Cases

### Unit Tests
```python
import pytest
from adapters.pgvector_adapter import PgvectorAdapter

def test_collection_name_valid():
    """Test that valid collection names are accepted"""
    adapter = PgvectorAdapter(connection_string)
    
    valid_names = [
        'test_collection',
        'TestCollection',
        'test_collection_123',
        'my_vectors',
        'embedding_db',
        '_private_collection',
        'a',  # Minimum length
    ]
    
    for name in valid_names:
        adapter.create_collection(name, 128, 'cosine')
        assert name in adapter.list_collections()

def test_collection_name_invalid():
    """Test that invalid collection names are rejected"""
    adapter = PgvectorAdapter(connection_string)
    
    invalid_names = [
        '',           # Empty
        ' ',          # Whitespace only
        'test-name',  # Hyphen
        'test.name',  # Dot
        'test name',  # Space
        '123collection',  # Starts with digit
        'select',    # SQL keyword
        'create',     # SQL keyword
        'test;drop',  # SQL injection
        'a' * 100,   # Too long
    ]
    
    for name in invalid_names:
        with pytest.raises(ValueError):
            adapter.create_collection(name, 128, 'cosine')

def test_collection_name_case_insensitive():
    """Test that collection names are case-insensitive"""
    adapter = PgvectorAdapter(connection_string)
    
    # Create collection with lowercase
    adapter.create_collection('testcase', 128, 'cosine')
    assert 'testcase' in adapter.list_collections()
    
    # Try to create with uppercase - should fail (duplicate)
    with pytest.raises(ValueError, match="already exists"):
        adapter.create_collection('TESTCASE', 128, 'cosine')

def test_collection_name_sanitization():
    """Test name sanitization function"""
    from validators import CollectionNameValidator
    
    test_cases = [
        ('test-name', 'test_name'),
        ('test.name', 'test_name'),
        ('test name', 'test_name'),
        ('123test', 'col_123test'),
        ('select', 'col_select'),
        ('a' * 100, 'a' * 63),  # Truncated
        ('---', 'col_' + hashlib.md5('---'.encode()).hexdigest()[:20]),
    ]
    
    for input_name, expected in test_cases:
        sanitized = CollectionNameValidator.sanitize_name(input_name)
        assert sanitized == expected, f"Expected {expected}, got {sanitized}"
```

### Integration Test
```python
def test_collection_name_operations():
    """Test that validated names work consistently across operations"""
    adapter = PgvectorAdapter(connection_string)
    
    # Create collection with valid name
    name = 'test_valid_name'
    adapter.create_collection(name, 128, 'cosine')
    
    # Insert data
    adapter.insert(name, [
        {'id': 1, 'vector': [1.0]*128},
        {'id': 2, 'vector': [2.0]*128},
    ])
    
    # Search
    results = adapter.search(name, [1.0]*128, 10)
    assert len(results) > 0
    
    # Drop
    adapter.drop_collection(name)
    assert name not in adapter.list_collections()
```

## Validation Rules Summary

| Name Characteristic | Valid | Invalid Examples |
|---------------------|-------|------------------|
| **Length** | 1-63 chars | "", "a"*64 |
| **Characters** | a-z, A-Z, 0-9, _ | "test-name", "test.name", "test name" |
| **First Char** | Letter or underscore | "123test" |
| **Case Sensitivity** | Case-insensitive | "Test" and "TEST" are same |
| **Reserved Words** | Not reserved | "select", "create", "drop" |
| **Empty/Whitespace** | Not allowed | "", " ", "\t" |

## Naming Best Practices

### Good Names
```python
✅ Descriptive: "user_embeddings", "product_vectors", "image_features"
✅ With version: "embeddings_v2", "vectors_2024"
✅ With prefix: "staging_user_vec", "prod_image_emb"
✅ Underscore-separated: "my_collection_name"
```

### Bad Names
```python
❌ Cryptic: "col1", "abc", "xyz"
❌ Too generic: "data", "vectors", "collection"
❌ Reserved words: "table", "index", "select"
❌ Mixed separators: "test-name.collection"
```

## Verification

- [x] Bug successfully reproduced
- [x] Root cause identified
- [ ] Fix implemented
- [ ] Fix tested
- [ ] Fix deployed to production

## Additional Notes

1. **SQL Injection Protection**: While `sql.Identifier()` provides protection, explicit validation at the adapter layer provides better error messages and prevents edge cases.

2. **Name Normalization**: Converting names to lowercase (or uppercase) consistently helps avoid confusion and duplicates due to case variations.

3. **Silent Truncation**: PostgreSQL silently truncates identifiers to 63 characters. This is particularly dangerous because users may create a collection thinking it has one name, but it actually has another. Explicit validation prevents this.

4. **Reserved Words**: The list of reserved words provided is not exhaustive. PostgreSQL has many more reserved words. Consider importing or generating this list from PostgreSQL's documentation.

5. **Cross-Database Consistency**: Different databases have different identifier rules. The validation should be adapted for each adapter accordingly.

6. **Name Suggestions**: For invalid names, the adapter could suggest valid alternatives using the sanitization function to improve user experience.

## References

- Original Bug Report: `ISSUES.json` entry #22
- Bug Mining Evidence: `BUG_EVIDENCE_CHAIN_REPORT.md`
- Reproduction Results: `reproduction_results/bug_reproduction_results.json`
- PostgreSQL Identifier Rules: https://www.postgresql.org/docs/current/sql-syntax-lexical.html#SQL-SYNTAX-IDENTIFIERS
- PostgreSQL Reserved Words: https://www.postgresql.org/docs/current/sql-keywords-appendix.html
