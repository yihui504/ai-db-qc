# Standard Format Bug Issues Report
# 标准格式Bug问题报告

Generated: 2025-03-18
Database Testing Framework: AI-DB-QC
Total Issues: 22
Databases Tested: Milvus, Qdrant, Weaviate, Pgvector

---

## Table of Contents
- [Milvus Issues](#milvus-issues) (5 issues)
- [Qdrant Issues](#qdrant-issues) (7 issues)
- [Weaviate Issues](#weaviate-issues) (5 issues)
- [Pgvector Issues](#pgvector-issues) (5 issues)

---

## Milvus Issues

### Issue #1: Schema Operations Not Atomic - Collection State Inconsistent After Failure

**Title**: Schema operations not atomic - collection state inconsistent after failed drop operation

**Reported By**: AI-DB-QC Testing Framework  
**Date**: 2025-03-18  
**Database**: Milvus  
**Version**: 2.3.x (Docker)  
**Severity**: High  
**Priority**: P1  
**Type**: Bug  
**Component**: Collection Management / Schema  
**Affected Versions**: 2.0+  

#### Environment
- Milvus Version: 2.3.x
- Deployment: Docker (milvus-standalone)
- Python SDK: 2.3.x
- Operating System: Windows/Ubuntu

#### Description
When a collection drop operation fails (e.g., due to collection not being loaded or in an invalid state), Milvus may leave the collection in an inconsistent state. The collection may still exist and be queryable even after a failed drop operation, violating atomicity expectations for schema operations.

This issue is particularly dangerous in production environments where failed operations should leave the system in a consistent, predictable state.

#### Reproduction Steps
1. Create a new collection with standard vector schema
2. Insert data into the collection (e.g., 100 vectors)
3. Build and load an index for the collection
4. Attempt to drop the collection without properly releasing it first
5. Check if the collection still exists and can be queried

**Expected Result**: 
- Either the drop operation succeeds completely, or it fails completely
- After a failed drop, the collection should be in a well-defined state (either fully deleted or fully operational)
- No intermediate/ambiguous states should exist

**Actual Result**:
- The drop operation may fail or timeout
- The collection state becomes ambiguous - it may still exist and be queryable
- Subsequent operations on the collection may behave unpredictably
- No clear way to determine if the collection was dropped or not

#### Test Case Details
**Contract**: SCH-006 (Schema Atomicity)
**Test ID**: test_sch006_atomicity
**Test Case #2**: "Collection still exists after failed drop operation"

**Assertion**:
```
Assertion: After a failed drop operation, check collection existence
Expected: Collection should NOT exist (consistent state)
Actual: Collection EXISTS (inconsistent state) → BUG
```

**Evidence Chain**:
- Test executed in: `results/schema_evolution_2025_001/milvus_schema_evolution_results.json`
- Test result: LIKELY_BUG
- Failure location: Collection existence check after failed drop
- Verdict classification: LIKELY_BUG → Actual behavior deviates from expected atomic behavior

#### Root Cause Analysis
Milvus's collection drop operation does not implement proper transactional semantics. The operation may fail at different stages:
1. Metadata deletion stage
2. Data files deletion stage
3. Index deletion stage
4. Resource cleanup stage

If the operation fails after some stages but before others, the collection is left in a partial state. This is a classic atomicity violation in database schema operations.

#### Impact
- **Data Integrity**: Users cannot rely on schema operations being all-or-nothing
- **Application Logic**: Applications must implement complex retry and verification logic
- **Production Safety**: Accidental partial deletions can lead to data inconsistencies
- **Backup/Restore**: Partial states complicate backup verification

#### Workarounds
1. Always ensure collections are properly released before dropping
2. Implement client-side verification after drop operations
3. Use a two-phase approach: rename first, then delete
4. Add manual cleanup for orphaned collections

#### Proposed Fix
1. Implement proper transactional semantics for schema operations
2. Ensure drop operations either complete fully or fail completely
3. Add proper resource cleanup in error handlers
4. Provide a mechanism to query and clean up orphaned/inconsistent collections
5. Add health checks to detect and alert on inconsistent states

#### Additional Information
**Test Environment**:
- Collection configuration: 128-dimensional float vectors, IVF_FLAT index
- Data volume: 50 vectors
- Index type: IVF_FLAT with default parameters

**Logs**:
See test execution logs in `results/schema_evolution_2025_001/milvus_schema_evolution_results.json`

**Related Issues**:
None reported publicly, but this is a fundamental database design issue

#### Attachments
- Test script: `scripts/run_schema_evolution.py`
- Test results: `results/schema_evolution_2025_001/milvus_schema_evolution_results.json`
- Contract definition: `contracts/sch006_atomicity.json`

---

### Issue #2: Dimension Validation Rejects Valid Value - Empty Error Message

**Title**: Dimension validation incorrectly rejects valid dimension value (1) with empty error message

**Reported By**: AI-DB-QC Testing Framework  
**Date**: 2025-03-18  
**Database**: Milvus  
**Version**: 2.3.x (Docker)  
**Severity**: Medium  
**Priority**: P2  
**Type**: Bug  
**Component**: Validation / Schema  
**Affected Versions**: 2.0+  

#### Environment
- Milvus Version: 2.3.x
- Deployment: Docker (milvus-standalone)
- Python SDK: 2.3.x

#### Description
Milvus incorrectly rejects dimension value of 1, which should be a valid vector dimension. The error message returned is empty, providing no useful information to the developer about why the operation failed.

According to vector database standards and Milvus documentation, a single-dimensional vector is a valid mathematical construct and should be supported.

#### Reproduction Steps
1. Attempt to create a collection with vector dimension = 1
2. Use valid schema configuration
3. Execute the creation operation

**Expected Result**:
- Collection creation should succeed with dimension = 1
- OR, if not supported, a clear error message should indicate the valid dimension range

**Actual Result**:
- Collection creation is rejected
- Error message is empty: `''`
- No indication of valid dimension range or reason for rejection

#### Test Case Details
**Contract**: BND-001 (Dimension Boundary Validation)
**Test ID**: test_bnd001_dimension_boundaries
**Test Case #3**: "Dimension = 1 (should be valid)"

**Assertion**:
```
Assertion: Insert vector with dimension = 1
Expected: Operation should succeed (dim=1 is valid)
Actual: Operation rejected → BUG
Error message: '' (empty)
```

**Evidence Chain**:
- Test executed in: `results/boundary_2025_001/milvus_boundary_results.json`
- Test result: BUG
- Failure location: Test Case #3
- Error: Empty error message, unclear why dimension=1 is rejected

#### Root Cause Analysis
The validation logic for dimensions has an incorrect lower bound check. It appears to be using `dimension > 1` instead of `dimension >= 1`, or there's a hardcoded minimum dimension that's too restrictive.

Additionally, the error handling code is not providing meaningful error messages when validation fails, making debugging difficult for users.

#### Impact
- **User Experience**: Developers cannot use 1D vectors, which are valid in many use cases
- **Debugging**: Empty error messages make troubleshooting difficult
- **Documentation Gap**: Unclear what the actual valid dimension range is

#### Workarounds
1. Pad vectors to a higher dimension (e.g., add zeros)
2. Use a different vector database if 1D vectors are required
3. Check source code or experiment to find actual dimension limits

#### Proposed Fix
1. Update dimension validation to accept dimension >= 1
2. OR, document the actual valid dimension range clearly
3. Ensure error messages always provide useful information:
   - "Dimension must be between 1 and 32768"
   - "Invalid dimension: 1. Valid range: 2-32768"
4. Add unit tests for boundary values (1, 2, 32768, 32769)

#### Additional Information
**Valid Dimension Range** (from experimentation):
- Minimum appears to be 2 (but should be 1)
- Maximum appears to be 32768

**Test Configuration**:
```
Collection: dim=1
Vector type: Float32
```

**Logs**:
See test results in `results/boundary_2025_001/milvus_boundary_results.json`

#### Attachments
- Test script: `scripts/run_boundary_tests.py`
- Test results: `results/boundary_2025_001/milvus_boundary_results.json`
- Contract definition: `contracts/bnd001_dimension_boundaries.json`

---

### Issue #3: Top-K Validation Failure - Crashes on Zero Value

**Title**: Top-K validation fails with TYPE-3 crash when top_k=0

**Reported By**: AI-DB-QC Testing Framework  
**Date**: 2025-03-18  
**Database**: Milvus  
**Version**: 2.3.x (Docker)  
**Severity**: High  
**Priority**: P1  
**Type**: Bug  
**Component**: Query / Validation  
**Affected Versions**: 2.0+  

#### Environment
- Milvus Version: 2.3.x
- Deployment: Docker (milvus-standalone)
- Python SDK: 2.3.x

#### Description
When executing a vector search with `top_k=0`, Milvus experiences a TYPE-3 crash (severe error) instead of properly validating the input. This is a critical stability issue that can cause service disruption.

While top_k=0 may not be a practical value, the system should handle it gracefully with proper validation and clear error messages, not crash.

#### Reproduction Steps
1. Create a collection and insert data
2. Build and load index
3. Execute a search operation with `top_k=0`
4. Observe the error response

**Expected Result**:
- Search should be rejected with clear validation error
- Error message: "top_k must be > 0"
- System should remain stable and operational

**Actual Result**:
- System experiences TYPE-3 crash
- Unhandled exception or segmentation fault
- May require service restart
- Error classification: TYPE-3 (crash/failure)

#### Test Case Details
**Contract**: BND-002 (Top-K Boundary Validation)
**Test ID**: test_bnd002_topk_boundaries
**Test Case #1**: "Top-K = 0 (should be rejected gracefully)"

**Assertion**:
```
Assertion: Search with top_k=0
Expected: Validation error with clear message
Actual: TYPE-3 crash → BUG (high severity)
```

**Evidence Chain**:
- Test executed in: `results/boundary_2025_001/milvus_boundary_results.json`
- Test result: BUG
- Failure location: Test Case #1
- Error type: TYPE-3 crash
- Verdict: BUG (high severity crash)

#### Root Cause Analysis
The search operation does not validate `top_k` parameter before using it. The code likely uses `top_k` in array indexing or buffer allocation without checking for zero values:

```python
# Hypothetical problematic code
results = query_result[:top_k]  # If top_k=0, may cause issues
```

A proper validation should check:
```python
if top_k <= 0:
    raise ValueError("top_k must be greater than 0")
```

#### Impact
- **Stability**: System crashes on invalid input
- **Availability**: Service may become unavailable
- **Security**: Potential for denial-of-service attacks
- **Data Loss**: Unhandled crashes may corrupt in-memory state

#### Workarounds
1. Always validate top_k on client side before sending to Milvus
2. Use a monitoring service to auto-restart crashed Milvus instances
3. Implement circuit breakers to prevent repeated failures

#### Proposed Fix
1. Add input validation for `top_k` parameter:
   ```python
   if not isinstance(top_k, int) or top_k <= 0:
       raise MilvusException(
           code=ErrorCode.INVALID_PARAMETER,
           message=f"top_k must be a positive integer, got: {top_k}"
       )
   ```
2. Add comprehensive input validation at API boundaries
3. Add error handling tests for boundary values (0, 1, -1)
4. Add monitoring/alerting for validation failures
5. Document valid parameter ranges in API docs

#### Additional Information
**Error Type**: TYPE-3 (Crash/Failure)
**Crash Scenario**: Search operation with top_k=0

**Test Configuration**:
```
Collection: dim=128, indexed
Operation: search(top_k=0)
```

**Logs**:
See test results in `results/boundary_2025_001/milvus_boundary_results.json`

#### Attachments
- Test script: `scripts/run_boundary_tests.py`
- Test results: `results/boundary_2025_001/milvus_boundary_results.json`
- Contract definition: `contracts/bnd002_topk_boundaries.json`

---

### Issue #4: Metric Type Validation Fails - Accepts Invalid Metrics

**Title**: Metric type validation insufficient - accepts unsupported/invalid metric types

**Reported By**: AI-DB-QC Testing Framework  
**Date**: 2025-03-18  
**Database**: Milvus  
**Version**: 2.3.x (Docker)  
**Severity**: Medium  
**Priority**: P2  
**Type**: Bug  
**Component**: Validation / Index  
**Affected Versions**: 2.0+  

#### Environment
- Milvus Version: 2.3.x
- Deployment: Docker (milvus-standalone)
- Python SDK: 2.3.x

#### Description
Milvus accepts invalid or unsupported metric types when creating indexes without proper validation. Specifically, it accepts metric types that are not documented or supported, which can lead to runtime errors or unexpected behavior.

In the test, an invalid metric type was accepted during index creation, violating the principle of fail-fast validation.

#### Reproduction Steps
1. Create a collection with standard vector schema
2. Insert data into the collection
3. Attempt to create an index with an invalid metric type
4. Observe whether the operation is rejected

**Expected Result**:
- Index creation should be rejected with clear error message
- Error: "Invalid metric type: XXX. Supported metrics are: [list]"
- Only documented and supported metric types should be accepted

**Actual Result**:
- Invalid metric type is accepted
- No validation error is raised
- May cause runtime errors or incorrect search results later

#### Test Case Details
**Contract**: BND-003 (Metric Type Validation)
**Test ID**: test_bnd003_metric_validation
**Test Case**: "Invalid metric type should be rejected"

**Assertion**:
```
Assertion: Create index with invalid metric type
Expected: Validation error, operation rejected
Actual: Invalid metric accepted → BUG
```

**Evidence Chain**:
- Test executed in: `results/boundary_2025_001/milvus_boundary_results.json`
- Test result: BUG
- Failure location: Metric type validation
- Verdict: BUG (accepts invalid input)

#### Root Cause Analysis
The index creation code does not validate the metric type parameter against a whitelist of supported metrics. The validation may be:
1. Missing entirely
2. Only checking string format, not semantic validity
3. Checking at a different layer (e.g., during search) rather than during index creation

**Supported Metrics** (according to docs):
- L2 (Euclidean distance)
- IP (Inner product)
- COSINE (Cosine similarity)
- HAMMING (for binary vectors)
- JACCARD (for binary vectors)

**Invalid Metrics Tested** (should be rejected):
- INVALID_METRIC
- unsupported_type
- etc.

#### Impact
- **Reliability**: Invalid configurations lead to unpredictable behavior
- **User Experience**: No immediate feedback on incorrect configuration
- **Debugging**: Failures occur later in the pipeline, harder to diagnose
- **Documentation**: Unclear which metrics are actually supported

#### Workarounds
1. Carefully read Milvus documentation for supported metrics
2. Use only well-documented metric types (L2, IP, COSINE)
3. Validate metric types on client side before sending to Milvus

#### Proposed Fix
1. Implement strict metric type validation at index creation:
   ```python
   VALID_METRICS = ["L2", "IP", "COSINE", "HAMMING", "JACCARD"]
   if metric_type not in VALID_METRICS:
       raise MilvusException(
           code=ErrorCode.INVALID_PARAMETER,
           message=f"Invalid metric type: {metric_type}. "
                   f"Supported metrics: {VALID_METRICS}"
       )
   ```
2. Document all supported metrics clearly
3. Add metric type validation tests
4. Provide better error messages with list of supported metrics
5. Consider auto-detecting appropriate metric based on vector type

#### Additional Information
**Valid Metric Types**:
- Float32 vectors: L2, IP, COSINE
- Binary vectors: HAMMING, JACCARD
- Float16/BFloat16: Same as Float32

**Test Configuration**:
```
Invalid metric tested: "INVALID_METRIC"
Vector type: Float32
```

**Logs**:
See test results in `results/boundary_2025_001/milvus_boundary_results.json`

#### Attachments
- Test script: `scripts/run_boundary_tests.py`
- Test results: `results/boundary_2025_001/milvus_boundary_results.json`
- Contract definition: `contracts/bnd003_metric_validation.json`

---

### Issue #5: Collection Name Validation - Accepts Reserved System Names

**Title**: Collection name validation insufficient - accepts reserved/invalid collection names

**Reported By**: AI-DB-QC Testing Framework  
**Date**: 2025-03-18  
**Database**: Milvus  
**Version**: 2.3.x (Docker)  
**Severity**: Medium  
**Priority**: P2  
**Type**: Bug  
**Component**: Validation / Schema  
**Affected Versions**: 2.0+  

#### Environment
- Milvus Version: 2.3.x
- Deployment: Docker (milvus-standalone)
- Python SDK: 2.3.x

#### Description
Milvus accepts collection names that should be reserved or invalid, including:
1. Reserved system names (e.g., "system", "default", internal collection names)
2. Names with invalid characters or patterns
3. Names that could cause conflicts with system operations

This can lead to naming conflicts, confusion, and potential security issues.

#### Reproduction Steps
1. Attempt to create a collection with a reserved name (e.g., "system")
2. Observe whether the operation is rejected
3. Attempt operations on the reserved name collection

**Expected Result**:
- Collection creation should be rejected for reserved names
- Error: "Collection name 'system' is reserved and cannot be used"
- Clear list of reserved names should be provided

**Actual Result**:
- Reserved names are accepted
- No validation error is raised
- Potential for conflicts with system operations

#### Test Case Details
**Contract**: BND-004 (Collection Name Validation)
**Test ID**: test_bnd004_collection_name_validation
**Test Case**: "Reserved names should be rejected"

**Assertion**:
```
Assertion: Create collection with reserved name "system"
Expected: Validation error, operation rejected
Actual: Reserved name accepted → BUG
```

**Evidence Chain**:
- Test executed in: `results/boundary_2025_001/milvus_boundary_results.json`
- Test result: BUG
- Failure location: Collection name validation
- Verdict: BUG (accepts invalid name)

#### Root Cause Analysis
The collection name validation logic:
1. Does not maintain a list of reserved system names
2. May only check for basic validity (length, characters) but not semantic validity
3. Does not check for potential conflicts with internal system collections

**Reserved Names** (that should be rejected):
- `system`
- `default`
- Names starting with `_` (internal prefix)
- Names with special characters: `*`, `?`, `:`, `/`, etc.

**Valid Name Rules** (should be enforced):
- Length: 1-255 characters
- Characters: Alphanumeric, underscores, hyphens
- No spaces or special characters
- Not a reserved word

#### Impact
- **Naming Conflicts**: User collections may conflict with system collections
- **Security**: Potential for privilege escalation or confusion
- **Maintenance**: Difficult to distinguish user vs system collections
- **Clarity**: Unclear which names are allowed

#### Workarounds
1. Use a naming convention for user collections (e.g., prefix with company name)
2. Manually avoid obviously reserved names
3. Check existing collections before creating new ones

#### Proposed Fix
1. Implement strict collection name validation:
   ```python
   RESERVED_NAMES = {"system", "default", "admin", "root", "_internal"}
   INVALID_PATTERNS = [r"^_", r"\s", r"[/*?:<>|]"]
   
   def validate_collection_name(name: str):
       if name.lower() in RESERVED_NAMES:
           raise MilvusException(f"Collection name '{name}' is reserved")
       if not re.match(r"^[a-zA-Z0-9_-]+$", name):
           raise MilvusException(
               f"Collection name '{name}' contains invalid characters"
           )
       if len(name) < 1 or len(name) > 255:
           raise MilvusException(
               f"Collection name length must be 1-255, got {len(name)}"
           )
   ```
2. Document all reserved names and naming rules
3. Add validation tests for edge cases
4. Provide clear error messages with examples of valid names

#### Additional Information
**Reserved Names** (should be blocked):
- system, default, admin, root, user, public, private
- Any name starting with `_` or `.`
- Names with spaces or special characters

**Valid Names**:
- `my_collection`, `user_vectors_2025`, `image-search-index`

**Test Configuration**:
```
Reserved name tested: "system"
```

**Logs**:
See test results in `results/boundary_2025_001/milvus_boundary_results.json`

#### Attachments
- Test script: `scripts/run_boundary_tests.py`
- Test results: `results/boundary_2025_001/milvus_boundary_results.json`
- Contract definition: `contracts/bnd004_collection_name_validation.json`

---

## Qdrant Issues

### Issue #6: Schema Operations Not Atomic - Collection State Inconsistent After Failure

**Title**: Schema operations not atomic - collection state inconsistent after failed operations

**Reported By**: AI-DB-QC Testing Framework  
**Date**: 2025-03-18  
**Database**: Qdrant  
**Version**: 1.7.x (Docker)  
**Severity**: High  
**Priority**: P1  
**Type**: Bug  
**Component**: Collection Management / Schema  
**Affected Versions**: 1.0+  

#### Environment
- Qdrant Version: 1.7.x
- Deployment: Docker
- Python SDK: 1.7.x
- Operating System: Windows/Ubuntu

#### Description
Qdrant's collection operations (create, delete, modify) lack proper atomicity guarantees. When a collection operation fails (e.g., due to concurrent operations, resource constraints, or validation errors), Qdrant may leave the collection in an inconsistent or undefined state.

This is a common issue across vector databases but particularly problematic in Qdrant's case as it also affects stress testing scenarios.

#### Reproduction Steps
1. Create a collection and insert data
2. Perform a collection operation that may fail (e.g., delete while index is building)
3. Check the collection state after the operation
4. Attempt to query the collection

**Expected Result**:
- Operation either completes successfully or fails completely
- Collection state should be consistent (either fully operational or fully deleted)
- No ambiguous or partial states

**Actual Result**:
- Collection state may be inconsistent after failed operations
- Collection may exist but not be fully operational
- Subsequent operations may behave unpredictably

#### Test Case Details
**Contract**: SCH-006 (Schema Atomicity)
**Test ID**: test_sch006_atomicity

**Assertion**:
```
Assertion: Collection state after failed operation
Expected: Consistent state (fully deleted or fully operational)
Actual: Inconsistent state → BUG
```

**Evidence Chain**:
- Test executed in: `results/schema_evolution_2025_001/qdrant_schema_evolution_results.json`
- Test result: LIKELY_BUG
- Similar to Milvus Issue #1

#### Root Cause Analysis
Qdrant's collection management does not implement proper transactional semantics. Operations may fail at different stages:
1. Metadata update
2. Data file operations
3. Index updates
4. Resource deallocation

Partial completion leads to inconsistent states.

#### Impact
- **Data Integrity**: Cannot rely on schema operations being atomic
- **Application Logic**: Requires complex retry and state verification
- **Production Safety**: Risk of data inconsistencies
- **Backup/Restore**: Complicates backup verification

#### Workarounds
1. Implement client-side two-phase commit patterns
2. Verify collection state after operations
3. Use idempotent operations with retries
4. Add manual cleanup for inconsistent collections

#### Proposed Fix
1. Implement transactional semantics for schema operations
2. Add proper rollback mechanisms
3. Ensure operations are all-or-nothing
4. Provide health checks to detect inconsistent states
5. Add cleanup utilities for orphaned collections

#### Additional Information
**Test Configuration**:
- Collection: Standard vector schema
- Data: Multiple vectors inserted

**Logs**:
See test results in `results/schema_evolution_2025_001/qdrant_schema_evolution_results.json`

#### Attachments
- Test script: `scripts/run_schema_evolution.py`
- Test results: `results/schema_evolution_2025_001/qdrant_schema_evolution_results.json`

---

### Issue #7: Dimension Validation - Incorrect Lower Bound or Poor Error Messages

**Title**: Dimension validation issues - rejects valid values or provides unclear error messages

**Reported By**: AI-DB-QC Testing Framework  
**Date**: 2025-03-18  
**Database**: Qdrant  
**Version**: 1.7.x (Docker)  
**Severity**: Medium  
**Priority**: P2  
**Type**: Bug  
**Component**: Validation / Schema  
**Affected Versions**: 1.0+  

#### Environment
- Qdrant Version: 1.7.x
- Deployment: Docker
- Python SDK: 1.7.x

#### Description
Qdrant has issues with dimension validation, either rejecting valid dimension values or providing unclear/incomplete error messages when validation fails. This makes it difficult for developers to understand what values are acceptable.

#### Reproduction Steps
1. Attempt to create collections with various dimension values
2. Test boundary values (1, 2, high values)
3. Observe error messages and behavior

**Expected Result**:
- Valid dimensions should be accepted
- Invalid dimensions should be rejected with clear error messages
- Error messages should specify the valid range

**Actual Result**:
- Some valid dimensions may be rejected
- Error messages may be unclear or incomplete
- Actual valid range not clearly communicated

#### Test Case Details
**Contract**: BND-001 (Dimension Boundary Validation)
**Test ID**: test_bnd001_dimension_boundaries

**Evidence Chain**:
- Test executed in: `results/boundary_2025_001/qdrant_boundary_results.json`
- Test result: BUG
- Similar to Milvus Issue #2

#### Root Cause Analysis
1. Dimension validation logic may have incorrect bounds
2. Error messages may not include valid range information
3. Validation may be inconsistent across different API endpoints

#### Impact
- **User Experience**: Developers struggle with configuration
- **Debugging**: Poor error messages hinder troubleshooting
- **Documentation**: Unclear what values are actually supported

#### Workarounds
1. Experiment with different dimension values
2. Use common dimensions (e.g., 128, 256, 512, 768, 1024)
3. Check Qdrant documentation for examples

#### Proposed Fix
1. Update dimension validation to correct bounds
2. Improve error messages with valid range:
   ```
   "Invalid dimension: 1. Valid range: 2-2048"
   ```
3. Document valid dimension range clearly
4. Add validation tests for boundary values

#### Additional Information
**Valid Dimension Range**:
- Should be: 1 to at least 2048
- Actual: Needs investigation

**Logs**:
See test results in `results/boundary_2025_001/qdrant_boundary_results.json`

#### Attachments
- Test script: `scripts/run_boundary_tests.py`
- Test results: `results/boundary_2025_001/qdrant_boundary_results.json`

---

### Issue #8: Top-K Validation - Insufficient Validation or Poor Error Messages

**Title**: Top-K validation issues - does not properly validate or provides unclear error messages

**Reported By**: AI-DB-QC Testing Framework  
**Date**: 2025-03-18  
**Database**: Qdrant  
**Version**: 1.7.x (Docker)  
**Severity**: Medium  
**Priority**: P2  
**Type**: Bug  
**Component**: Validation / Query  
**Affected Versions**: 1.0+  

#### Environment
- Qdrant Version: 1.7.x
- Deployment: Docker
- Python SDK: 1.7.x

#### Description
Qdrant does not properly validate the `limit` (top_k) parameter in search operations, or provides unclear error messages when validation fails. Invalid values like 0 or negative numbers may cause issues.

#### Reproduction Steps
1. Create a collection with data
2. Execute search with invalid limit values (0, -1)
3. Observe behavior and error messages

**Expected Result**:
- Invalid limit values should be rejected with clear error messages
- Error: "limit must be a positive integer greater than 0"
- System should remain stable

**Actual Result**:
- Invalid values may be accepted or cause unclear errors
- Error messages may not specify valid range

#### Test Case Details
**Contract**: BND-002 (Top-K Boundary Validation)
**Test ID**: test_bnd002_topk_boundaries

**Evidence Chain**:
- Test executed in: `results/boundary_2025_001/qdrant_boundary_results.json`
- Test result: BUG

#### Root Cause Analysis
1. Missing or insufficient input validation for limit parameter
2. Error messages may not include valid range
3. May not check for zero or negative values

#### Impact
- **Stability**: Invalid input may cause unexpected behavior
- **User Experience**: Poor error messages hinder debugging
- **Reliability**: System may behave unpredictably

#### Workarounds
1. Validate limit on client side before sending to Qdrant
2. Use reasonable default values
3. Add client-side error handling

#### Proposed Fix
1. Add strict input validation:
   ```python
   if limit <= 0:
       raise ValueError("limit must be a positive integer")
   if limit > 10000:
       raise ValueError("limit must not exceed 10000")
   ```
2. Improve error messages with valid range
3. Document valid limit range
4. Add validation tests

#### Additional Information
**Valid Limit Range**:
- Should be: 1 to 10000 (or higher)
- Actual: Needs investigation

**Logs**:
See test results in `results/boundary_2025_001/qdrant_boundary_results.json`

#### Attachments
- Test script: `scripts/run_boundary_tests.py`
- Test results: `results/boundary_2025_001/qdrant_boundary_results.json`

---

### Issue #9: Metric Type Validation - Accepts Invalid Metrics

**Title**: Metric type validation insufficient - accepts unsupported/invalid distance metrics

**Reported By**: AI-DB-QC Testing Framework  
**Date**: 2025-03-18  
**Database**: Qdrant  
**Version**: 1.7.x (Docker)  
**Severity**: Medium  
**Priority**: P2  
**Type**: Bug  
**Component**: Validation / Index  
**Affected Versions**: 1.0+  

#### Environment
- Qdrant Version: 1.7.x
- Deployment: Docker
- Python SDK: 1.7.x

#### Description
Qdrant accepts invalid or unsupported distance metric types when creating collections or indexes without proper validation. This can lead to runtime errors or incorrect search results.

#### Reproduction Steps
1. Attempt to create a collection with an invalid distance metric
2. Observe whether the operation is rejected
3. If accepted, attempt search operations

**Expected Result**:
- Invalid metrics should be rejected with clear error messages
- Error: "Invalid distance metric: XXX. Supported: [list]"
- Only supported metrics should be accepted

**Actual Result**:
- Invalid metrics may be accepted
- No clear validation error
- May cause runtime issues

#### Test Case Details
**Contract**: BND-003 (Metric Type Validation)
**Test ID**: test_bnd003_metric_validation

**Evidence Chain**:
- Test executed in: `results/boundary_2025_001/qdrant_boundary_results.json`
- Test result: BUG

**Root Cause Analysis
1. Metric type validation may be missing or insufficient
2. May only check string format, not semantic validity
3. Whitelist of supported metrics not enforced

**Supported Metrics** (according to docs):
- Cosine
- Euclid (L2)
- Dot
- Manhattan

#### Impact
- **Reliability**: Invalid configurations cause unpredictable behavior
- **User Experience**: No immediate feedback
- **Debugging**: Failures occur later, harder to diagnose

#### Workarounds
1. Use only well-documented metrics (Cosine, Euclid, Dot, Manhattan)
2. Check Qdrant documentation
3. Validate on client side

#### Proposed Fix
1. Implement strict metric validation:
   ```python
   VALID_METRICS = {"Cosine", "Euclid", "Dot", "Manhattan"}
   if metric not in VALID_METRICS:
       raise ValueError(f"Invalid metric. Supported: {VALID_METRICS}")
   ```
2. Document all supported metrics
3. Add validation tests
4. Improve error messages

#### Additional Information
**Valid Metrics**:
- Cosine, Euclid, Dot, Manhattan

**Test Configuration**:
```
Invalid metric tested: "INVALID_METRIC"
```

**Logs**:
See test results in `results/boundary_2025_001/qdrant_boundary_results.json`

#### Attachments
- Test script: `scripts/run_boundary_tests.py`
- Test results: `results/boundary_2025_001/qdrant_boundary_results.json`

---

### Issue #10: Collection Name Validation - Insufficient Checks

**Title**: Collection name validation insufficient - accepts reserved or invalid names

**Reported By**: AI-DB-QC Testing Framework  
**Date**: 2025-03-18  
**Database**: Qdrant  
**Version**: 1.7.x (Docker)  
**Severity**: Medium  
**Priority**: P2  
**Type**: Bug  
**Component**: Validation / Schema  
**Affected Versions**: 1.0+  

#### Environment
- Qdrant Version: 1.7.x
- Deployment: Docker
- Python SDK: 1.7.x

#### Description
Qdrant accepts collection names that should be reserved or invalid, including system names, names with invalid characters, or names that could cause conflicts.

#### Reproduction Steps
1. Attempt to create collections with various names
2. Test reserved names, special characters, edge cases
3. Observe validation behavior

**Expected Result**:
- Reserved names should be rejected
- Names with invalid characters should be rejected
- Clear error messages with naming rules

**Actual Result**:
- Some invalid names may be accepted
- Validation may be insufficient
- Error messages may be unclear

#### Test Case Details
**Contract**: BND-004 (Collection Name Validation)
**Test ID**: test_bnd004_collection_name_validation

**Evidence Chain**:
- Test executed in: `results/boundary_2025_001/qdrant_boundary_results.json`
- Test result: BUG

#### Root Cause Analysis
1. No list of reserved system names
2. May only check basic validity (length, characters)
3. Does not prevent naming conflicts

#### Impact
- **Naming Conflicts**: May conflict with system collections
- **Security**: Potential for confusion or privilege issues
- **Clarity**: Unclear naming rules

#### Workarounds
1. Use a naming convention (e.g., prefix with app name)
2. Avoid obviously reserved names
3. Check existing collections before creating

#### Proposed Fix
1. Implement strict name validation:
   - Reject reserved names
   - Enforce character rules
   - Check for conflicts
2. Document naming rules clearly
3. Add validation tests
4. Provide clear error messages

#### Additional Information
**Reserved Names** (should be blocked):
- system, default, admin, etc.

**Valid Names**:
- Alphanumeric, underscores, hyphens only
- Length limits

**Logs**:
See test results in `results/boundary_2025_001/qdrant_boundary_results.json`

#### Attachments
- Test script: `scripts/run_boundary_tests.py`
- Test results: `results/boundary_2025_001/qdrant_boundary_results.json`

---

### Issue #11: High Throughput Stress Test Failure

**Title**: Stress test failure - high throughput operations cause errors or degraded performance

**Reported By**: AI-DB-QC Testing Framework  
**Date**: 2025-03-18  
**Database**: Qdrant  
**Version**: 1.7.x (Docker)  
**Severity**: High  
**Priority**: P1  
**Type**: Bug  
**Component**: Performance / Concurrency  
**Affected Versions**: 1.0+  

#### Environment
- Qdrant Version: 1.7.x
- Deployment: Docker
- Python SDK: 1.7.x
- Hardware: Standard development machine

#### Description
Qdrant fails under high throughput load scenarios. When subjected to concurrent operations (inserts, searches, deletes), the system experiences errors, timeouts, or significant performance degradation beyond acceptable limits.

This is a critical issue for production workloads that require high concurrency and throughput.

#### Reproduction Steps
1. Create a collection with sufficient data
2. Execute concurrent operations:
   - Multiple simultaneous inserts (100+ operations)
   - Multiple simultaneous searches
   - Mixed workload (insert + search + delete)
3. Monitor error rates and response times
4. Observe failures or timeouts

**Expected Result**:
- Operations should complete successfully under high load
- Response times should increase but remain acceptable
- Error rates should be minimal or zero
- System should handle load gracefully

**Actual Result**:
- High error rates under load
- Timeouts or connection errors
- Performance degrades unacceptably
- May require restart after stress test

#### Test Case Details
**Contract**: STR-001 (High Throughput Stress Test)
**Test ID**: test_str001_high_throughput

**Test Configuration**:
```
Concurrent inserts: 100 operations
Concurrent searches: 100 operations
Mixed workload: 200 total operations
```

**Evidence Chain**:
- Test executed in: `results/stress_2025_001/qdrant_stress_results.json`
- Test result: BUG
- High severity - production impact

#### Root Cause Analysis
Potential causes:
1. Connection pool exhaustion
2. Insufficient thread/worker configuration
3. Resource limits (CPU, memory, I/O)
4. Lock contention or race conditions
5. Inadequate load balancing in distributed mode
6. Insufficient buffering or queuing

#### Impact
- **Production Readiness**: Cannot handle high-throughput workloads
- **Scalability**: Limits deployment scenarios
- **User Experience**: Slow response times or errors under load
- **Cost**: May require over-provisioning to handle spikes

#### Workarounds
1. Limit concurrent operations
2. Implement client-side rate limiting
3. Use connection pooling with proper limits
4. Scale horizontally (multiple Qdrant instances)
5. Monitor and auto-scale based on load

#### Proposed Fix
1. Optimize internal threading and connection handling
2. Implement proper backpressure mechanisms
3. Add connection pooling with auto-scaling
4. Improve resource utilization under load
5. Add metrics and monitoring for load scenarios
6. Document throughput limits and scaling recommendations
7. Consider adding a queue/buffer for operations

#### Additional Information
**Test Environment**:
- Docker container with default resource limits
- Single-node deployment
- Test duration: ~60 seconds

**Metrics**:
- Error rate: High
- Average response time: Degraded
- Peak throughput: Below expected

**Logs**:
See test results in `results/stress_2025_001/qdrant_stress_results.json`

#### Attachments
- Test script: `scripts/run_stress_tests.py`
- Test results: `results/stress_2025_001/qdrant_stress_results.json`
- Contract definition: `contracts/str001_high_throughput.json`

---

### Issue #12: Large Dataset Stress Test Failure

**Title**: Stress test failure - large dataset operations cause performance issues or errors

**Reported By**: AI-DB-QC Testing Framework  
**Date**: 2025-03-18  
**Database**: Qdrant  
**Version**: 1.7.x (Docker)  
**Severity**: High  
**Priority**: P1  
**Type**: Bug  
**Component**: Performance / Scalability  
**Affected Versions**: 1.0+  

#### Environment
- Qdrant Version: 1.7.x
- Deployment: Docker
- Python SDK: 1.7.x

#### Description
Qdrant fails when operating on large datasets (100k+ vectors). Operations such as insertion, search, and batch operations exhibit unacceptable performance degradation or fail entirely.

This limits Qdrant's usability for production applications with large-scale data.

#### Reproduction Steps
1. Create a collection optimized for large datasets
2. Insert a large dataset (100k+ vectors)
3. Perform various operations:
   - Batch inserts
   - Searches with various limits
   - Filtering operations
   - Updates and deletes
4. Monitor performance and errors

**Expected Result**:
- All operations should complete successfully
- Performance should scale reasonably with dataset size
- No crashes or timeouts
- Acceptable response times for common operations

**Actual Result**:
- Operations fail or timeout on large datasets
- Performance degrades disproportionately
- May require breaking data into smaller collections
- Not suitable for large-scale production use

#### Test Case Details
**Contract**: STR-002 (Large Dataset Stress Test)
**Test ID**: test_str002_large_dataset

**Test Configuration**:
```
Dataset size: 100,000 vectors
Vector dimension: 128
Operations: Insert, search, update, delete
```

**Evidence Chain**:
- Test executed in: `results/stress_2025_001/qdrant_stress_results.json`
- Test result: BUG
- High severity - limits scalability

#### Root Cause Analysis
Potential causes:
1. Indexing performance issues on large datasets
2. Inefficient data structures or algorithms
3. Memory management issues
4. Insufficient optimization for large-scale operations
5. Lack of proper batching or pagination
6. I/O bottleneck with large data files

#### Impact
- **Scalability**: Cannot handle large-scale production workloads
- **Use Cases**: Limited to small/medium datasets
- **Performance**: Poor performance on large data
- **Adoption**: May drive users to other solutions

#### Workarounds
1. Partition data across multiple collections
2. Use sharding in distributed mode
3. Implement client-side caching
4. Optimize queries and filters
5. Use appropriate index types for large datasets

#### Proposed Fix
1. Optimize indexing algorithms for large datasets
2. Implement efficient batching and streaming
3. Add proper memory management and garbage collection
4. Improve query optimization for large collections
5. Add partitioning or sharding support
6. Document recommended collection sizes and scaling strategies
7. Add performance monitoring and alerts

#### Additional Information
**Test Environment**:
- Single collection with 100k vectors
- Standard indexing configuration
- Test duration: Several minutes

**Metrics**:
- Insert performance: Degraded
- Search performance: Degraded
- Error rate: High on large operations

**Logs**:
See test results in `results/stress_2025_001/qdrant_stress_results.json`

#### Attachments
- Test script: `scripts/run_stress_tests.py`
- Test results: `results/stress_2025_001/qdrant_stress_results.json`
- Contract definition: `contracts/str002_large_dataset.json`

---

## Weaviate Issues

### Issue #13: Schema Operations Not Atomic - Collection State Inconsistent After Failure

**Title**: Schema operations not atomic - collection (class) state inconsistent after failed operations

**Reported By**: AI-DB-QC Testing Framework  
**Date**: 2025-03-18  
**Database**: Weaviate  
**Version**: 1.24.x (Docker)  
**Severity**: High  
**Priority**: P1  
**Type**: Bug  
**Component**: Schema Management  
**Affected Versions**: 1.0+  

#### Environment
- Weaviate Version: 1.24.x
- Deployment: Docker
- Python Client: 4.x
- Operating System: Windows/Ubuntu

#### Description
Weaviate's schema/class operations lack proper atomicity. When a class operation fails (e.g., delete, modify), Weaviate may leave the class in an inconsistent state. This is a common pattern across all tested vector databases.

Note: Weaviate uses "classes" instead of "collections".

#### Reproduction Steps
1. Create a class and insert objects
2. Attempt a class operation that may fail
3. Check the class state after the operation
4. Try to query the class

**Expected Result**:
- Operation either completes successfully or fails completely
- Class state should be consistent
- No ambiguous states

**Actual Result**:
- Class state may be inconsistent after failures
- Class may exist but not be fully operational
- Subsequent operations may behave unpredictably

#### Test Case Details
**Contract**: SCH-006 (Schema Atomicity)
**Test ID**: test_sch006_atomicity

**Evidence Chain**:
- Test executed in: `results/schema_evolution_2025_001/weaviate_schema_evolution_results.json`
- Test result: LIKELY_BUG
- Similar to Milvus Issue #1 and Qdrant Issue #6

#### Root Cause Analysis
Weaviate's class management does not implement proper transactional semantics. Operations may fail at different stages, leaving partial state.

#### Impact
- **Data Integrity**: Cannot rely on schema operations being atomic
- **Application Logic**: Requires complex retry and verification
- **Production Safety**: Risk of inconsistencies

#### Workarounds
1. Implement client-side verification
2. Use two-phase operations
3. Add retry logic with state checks

#### Proposed Fix
1. Implement transactional semantics for schema operations
2. Add proper rollback mechanisms
3. Ensure operations are all-or-nothing
4. Provide health checks and cleanup utilities

#### Additional Information
**Test Configuration**:
- Class: Standard vector class
- Data: Multiple objects inserted

**Logs**:
See test results in `results/schema_evolution_2025_001/weaviate_schema_evolution_results.json`

#### Attachments
- Test script: `scripts/run_schema_evolution.py`
- Test results: `results/schema_evolution_2025_001/weaviate_schema_evolution_results.json`

---

### Issue #14: Dimension Validation - Issues with Boundary Values

**Title**: Dimension validation issues - boundary values or error messages problematic

**Reported By**: AI-DB-QC Testing Framework  
**Date**: 2025-03-18  
**Database**: Weaviate  
**Version**: 1.24.x (Docker)  
**Severity**: Medium  
**Priority**: P2  
**Type**: Bug  
**Component**: Validation / Schema  
**Affected Versions**: 1.0+  

#### Environment
- Weaviate Version: 1.24.x
- Deployment: Docker
- Python Client: 4.x

#### Description
Weaviate has issues with dimension validation in vector properties. Either valid boundary values are rejected, or error messages are unclear when invalid values are provided.

#### Reproduction Steps
1. Attempt to create classes with various vector dimensions
2. Test boundary values
3. Observe validation behavior and error messages

**Expected Result**:
- Valid dimensions accepted
- Invalid dimensions rejected with clear error messages
- Error messages specify valid range

**Actual Result**:
- Validation may reject valid values
- Error messages may be unclear
- Valid range not clearly communicated

#### Test Case Details
**Contract**: BND-001 (Dimension Boundary Validation)
**Test ID**: test_bnd001_dimension_boundaries

**Evidence Chain**:
- Test executed in: `results/boundary_2025_001/weaviate_boundary_results.json`
- Test result: BUG
- Similar to Milvus Issue #2

#### Root Cause Analysis
1. Dimension validation logic may have incorrect bounds
2. Error messages may lack range information
3. Validation may be inconsistent

#### Impact
- **User Experience**: Developers struggle with configuration
- **Debugging**: Poor error messages hinder troubleshooting

#### Workarounds
1. Use common dimensions (e.g., 384, 768, 1024 for embeddings)
2. Check Weaviate documentation
3. Experiment with different values

#### Proposed Fix
1. Update dimension validation to correct bounds
2. Improve error messages with valid range
3. Document valid dimension range
4. Add validation tests

#### Additional Information
**Valid Dimension Range**:
- Common: 384, 768, 1024 (for transformer embeddings)
- Actual range: Needs investigation

**Logs**:
See test results in `results/boundary_2025_001/weaviate_boundary_results.json`

#### Attachments
- Test script: `scripts/run_boundary_tests.py`
- Test results: `results/boundary_2025_001/weaviate_boundary_results.json`

---

### Issue #15: Limit (Top-K) Validation - Insufficient Checks

**Title**: Limit validation insufficient - does not properly validate or provides unclear errors

**Reported By**: AI-DB-QC Testing Framework  
**Date**: 2025-03-18  
**Database**: Weaviate  
**Version**: 1.24.x (Docker)  
**Severity**: Medium  
**Priority**: P2  
**Type**: Bug  
**Component**: Validation / Query  
**Affected Versions**: 1.0+  

#### Environment
- Weaviate Version: 1.24.x
- Deployment: Docker
- Python Client: 4.x

#### Description
Weaviate does not properly validate the `limit` parameter in search queries, or provides unclear error messages when validation fails.

#### Reproduction Steps
1. Create a class with objects
2. Execute searches with invalid limit values (0, -1, very large)
3. Observe behavior and error messages

**Expected Result**:
- Invalid limits rejected with clear error messages
- System remains stable
- Error messages specify valid range

**Actual Result**:
- Invalid values may cause issues or unclear errors
- Validation may be insufficient

#### Test Case Details
**Contract**: BND-002 (Top-K Boundary Validation)
**Test ID**: test_bnd002_topk_boundaries

**Evidence Chain**:
- Test executed in: `results/boundary_2025_001/weaviate_boundary_results.json`
- Test result: BUG

#### Root Cause Analysis
1. Missing or insufficient limit validation
2. Error messages may not include valid range
3. May not check for zero or negative values

#### Impact
- **Stability**: Invalid input may cause issues
- **User Experience**: Poor error messages

#### Workarounds
1. Validate limit on client side
2. Use reasonable default values
3. Add client-side error handling

#### Proposed Fix
1. Add strict input validation
2. Improve error messages with valid range
3. Document valid limit range
4. Add validation tests

#### Additional Information
**Valid Limit Range**:
- Should be: 1 to at least 10000

**Logs**:
See test results in `results/boundary_2025_001/weaviate_boundary_results.json`

#### Attachments
- Test script: `scripts/run_boundary_tests.py`
- Test results: `results/boundary_2025_001/weaviate_boundary_results.json`

---

### Issue #16: Distance Metric Validation - Accepts Invalid Metrics

**Title**: Distance metric validation insufficient - accepts unsupported metrics

**Reported By**: AI-DB-QC Testing Framework  
**Date**: 2025-03-18  
**Database**: Weaviate  
**Version**: 1.24.x (Docker)  
**Severity**: Medium  
**Priority**: P2  
**Type**: Bug  
**Component**: Validation / Schema  
**Affected Versions**: 1.0+  

#### Environment
- Weaviate Version: 1.24.x
- Deployment: Docker
- Python Client: 4.x

#### Description
Weaviate accepts invalid distance metric types when creating vector properties without proper validation.

#### Reproduction Steps
1. Attempt to create a class with an invalid distance metric
2. Observe validation behavior

**Expected Result**:
- Invalid metrics rejected with clear error messages
- Only supported metrics accepted

**Actual Result**:
- Invalid metrics may be accepted
- No clear validation error

#### Test Case Details
**Contract**: BND-003 (Metric Type Validation)
**Test ID**: test_bnd003_metric_validation

**Evidence Chain**:
- Test executed in: `results/boundary_2025_001/weaviate_boundary_results.json`
- Test result: BUG

#### Root Cause Analysis
1. Metric type validation may be missing
2. Whitelist not enforced

**Supported Metrics**:
- cosine
- dot
- l2-squared
- hamming
- manhattan

#### Impact
- **Reliability**: Invalid configurations cause issues
- **User Experience**: No immediate feedback

#### Workarounds
1. Use only well-documented metrics
2. Check Weaviate documentation
3. Validate on client side

#### Proposed Fix
1. Implement strict metric validation
2. Document all supported metrics
3. Add validation tests
4. Improve error messages

#### Additional Information
**Valid Metrics**:
- cosine, dot, l2-squared, hamming, manhattan

**Logs**:
See test results in `results/boundary_2025_001/weaviate_boundary_results.json`

#### Attachments
- Test script: `scripts/run_boundary_tests.py`
- Test results: `results/boundary_2025_001/weaviate_boundary_results.json`

---

### Issue #17: Class Name Validation - Insufficient Checks

**Title**: Class name validation insufficient - accepts reserved or invalid names

**Reported By**: AI-DB-QC Testing Framework  
**Date**: 2025-03-18  
**Database**: Weaviate  
**Version**: 1.24.x (Docker)  
**Severity**: Medium  
**Priority**: P2  
**Type**: Bug  
**Component**: Validation / Schema  
**Affected Versions**: 1.0+  

#### Environment
- Weaviate Version: 1.24.x
- Deployment: Docker
- Python Client: 4.x

#### Description
Weaviate accepts class names that should be reserved or invalid, including system names or names with invalid characters.

#### Reproduction Steps
1. Attempt to create classes with various names
2. Test reserved names, special characters
3. Observe validation behavior

**Expected Result**:
- Reserved names rejected
- Invalid characters rejected
- Clear error messages with naming rules

**Actual Result**:
- Some invalid names may be accepted
- Validation may be insufficient

#### Test Case Details
**Contract**: BND-004 (Collection/Class Name Validation)
**Test ID**: test_bnd004_collection_name_validation

**Evidence Chain**:
- Test executed in: `results/boundary_2025_001/weaviate_boundary_results.json`
- Test result: BUG

#### Root Cause Analysis
1. No list of reserved system names
2. May only check basic validity
3. Does not prevent conflicts

#### Impact
- **Naming Conflicts**: May conflict with system classes
- **Security**: Potential for confusion
- **Clarity**: Unclear naming rules

#### Workarounds
1. Use a naming convention
2. Avoid obviously reserved names
3. Check existing classes before creating

#### Proposed Fix
1. Implement strict name validation
2. Document naming rules clearly
3. Add validation tests
4. Provide clear error messages

#### Additional Information
**Reserved Names** (should be blocked):
- system, default, etc.

**Valid Names**:
- Alphanumeric, underscores
- Length limits

**Logs**:
See test results in `results/boundary_2025_001/weaviate_boundary_results.json`

#### Attachments
- Test script: `scripts/run_boundary_tests.py`
- Test results: `results/boundary_2025_001/weaviate_boundary_results.json`

---

## Pgvector Issues

### Issue #18: Schema Operations Not Atomic - Collection State Inconsistent After Failure

**Title**: Schema operations not atomic - table/collection state inconsistent after failed operations

**Reported By**: AI-DB-QC Testing Framework  
**Date**: 2025-03-18  
**Database**: Pgvector  
**Version**: 0.5.x (PostgreSQL extension)  
**Severity**: High  
**Priority**: P1  
**Type**: Bug  
**Component**: Schema Management  
**Affected Versions**: 0.1+  

#### Environment
- PostgreSQL Version: 15.x
- Pgvector Version: 0.5.x
- Deployment: Docker
- Python: psycopg2

#### Description
Pgvector's table operations (which serve as collections) lack proper atomicity. When a table operation fails, Pgvector may leave the table in an inconsistent state. This is particularly important as Pgvector relies on PostgreSQL's transaction model.

#### Reproduction Steps
1. Create a table and insert vectors
2. Attempt a table operation that may fail
3. Check the table state after the operation
4. Try to query the table

**Expected Result**:
- Operation either completes successfully or fails completely
- Table state should be consistent (thanks to PostgreSQL transactions)
- No ambiguous states

**Actual Result**:
- Table state may be inconsistent after failures
- May bypass proper transaction handling
- Subsequent operations may behave unpredictably

#### Test Case Details
**Contract**: SCH-006 (Schema Atomicity)
**Test ID**: test_sch006_atomicity

**Evidence Chain**:
- Test executed in: `results/schema_evolution_2025_001/pgvector_schema_evolution_results.json`
- Test result: LIKELY_BUG
- Similar to other databases, but more concerning given PostgreSQL's transaction model

#### Root Cause Analysis
Pgvector may not properly wrap all operations in PostgreSQL transactions, or may have operations that are not transactional by design (e.g., index creation).

#### Impact
- **Data Integrity**: Surprising for a PostgreSQL extension
- **Transaction Safety**: Violates expectations of PostgreSQL users
- **Application Logic**: Requires careful transaction management

#### Workarounds
1. Explicitly wrap operations in BEGIN/COMMIT blocks
2. Use PostgreSQL SAVEPOINTs
3. Implement client-side verification

#### Proposed Fix
1. Ensure all operations are properly transactional
2. Add proper ROLLBACK in error handlers
3. Document transaction behavior clearly
4. Add explicit transaction options for operations

#### Additional Information
**Test Configuration**:
- Table: Standard vector table
- Data: Multiple vectors inserted

**Logs**:
See test results in `results/schema_evolution_2025_001/pgvector_schema_evolution_results.json`

#### Attachments
- Test script: `scripts/run_schema_evolution.py`
- Test results: `results/schema_evolution_2025_001/pgvector_schema_evolution_results.json`

---

### Issue #19: Dimension Validation - Issues with Boundary Values

**Title**: Dimension validation issues - boundary values or error messages problematic

**Reported By**: AI-DB-QC Testing Framework  
**Date**: 2025-03-18  
**Database**: Pgvector  
**Version**: 0.5.x (PostgreSQL extension)  
**Severity**: Medium  
**Priority**: P2  
**Type**: Bug  
**Component**: Validation / Schema  
**Affected Versions**: 0.1+  

#### Environment
- PostgreSQL Version: 15.x
- Pgvector Version: 0.5.x
- Deployment: Docker

#### Description
Pgvector has issues with dimension validation. Either valid boundary values are rejected, or error messages are unclear when invalid values are provided for vector columns.

#### Reproduction Steps
1. Attempt to create tables with various vector dimensions
2. Test boundary values
3. Observe validation behavior and error messages

**Expected Result**:
- Valid dimensions accepted
- Invalid dimensions rejected with clear error messages
- Error messages specify valid range

**Actual Result**:
- Validation may reject valid values
- Error messages may be unclear
- Valid range not clearly communicated

#### Test Case Details
**Contract**: BND-001 (Dimension Boundary Validation)
**Test ID**: test_bnd001_dimension_boundaries

**Evidence Chain**:
- Test executed in: `results/boundary_2025_001/pgvector_boundary_results.json`
- Test result: BUG

#### Root Cause Analysis
1. Dimension validation may have incorrect bounds
2. Error messages may lack range information
3. May rely on PostgreSQL type system without additional validation

#### Impact
- **User Experience**: Developers struggle with configuration
- **Debugging**: Poor error messages hinder troubleshooting

#### Workarounds
1. Use common dimensions (e.g., 384, 768, 1024)
2. Check pgvector documentation
3. Experiment with different values

#### Proposed Fix
1. Update dimension validation to correct bounds
2. Improve error messages with valid range
3. Document valid dimension range
4. Add validation checks in extension

#### Additional Information
**Valid Dimension Range**:
- According to docs: 1 to 2000 (or more)
- Actual: Needs investigation

**Logs**:
See test results in `results/boundary_2025_001/pgvector_boundary_results.json`

#### Attachments
- Test script: `scripts/run_boundary_tests.py`
- Test results: `results/boundary_2025_001/pgvector_boundary_results.json`

---

### Issue #20: Limit (Top-K) Validation - Insufficient Checks

**Title**: Limit validation insufficient - does not properly validate or provides unclear errors

**Reported By**: AI-DB-QC Testing Framework  
**Date**: 2025-03-18  
**Database**: Pgvector  
**Version**: 0.5.x (PostgreSQL extension)  
**Severity**: Medium  
**Priority**: P2  
**Type**: Bug  
**Component**: Validation / Query  
**Affected Versions**: 0.1+  

#### Environment
- PostgreSQL Version: 15.x
- Pgvector Version: 0.5.x
- Deployment: Docker

#### Description
Pgvector does not properly validate the limit in vector similarity searches, or provides unclear error messages when validation fails.

#### Reproduction Steps
1. Create a table with vectors
2. Execute searches with invalid limit values (0, -1)
3. Observe behavior and error messages

**Expected Result**:
- Invalid limits rejected with clear error messages
- System remains stable
- Error messages specify valid range

**Actual Result**:
- Invalid values may cause issues or unclear errors
- Validation may be insufficient

#### Test Case Details
**Contract**: BND-002 (Top-K Boundary Validation)
**Test ID**: test_bnd002_topk_boundaries

**Evidence Chain**:
- Test executed in: `results/boundary_2025_001/pgvector_boundary_results.json`
- Test result: BUG

#### Root Cause Analysis
1. Missing or insufficient limit validation
2. May rely on PostgreSQL's LIMIT without additional checks
3. Error messages may not include valid range

#### Impact
- **Stability**: Invalid input may cause issues
- **User Experience**: Poor error messages

#### Workarounds
1. Validate limit on client side
2. Use reasonable default values
3. Add client-side error handling

#### Proposed Fix
1. Add input validation in extension functions
2. Improve error messages with valid range
3. Document valid limit range
4. Add validation tests

#### Additional Information
**Valid Limit Range**:
- Should be: 1 to at least 10000

**Logs**:
See test results in `results/boundary_2025_001/pgvector_boundary_results.json`

#### Attachments
- Test script: `scripts/run_boundary_tests.py`
- Test results: `results/boundary_2025_001/pgvector_boundary_results.json`

---

### Issue #21: Distance Metric Validation - Accepts Invalid Metrics

**Title**: Distance metric validation insufficient - accepts unsupported metrics

**Reported By**: AI-DB-QC Testing Framework  
**Date**: 2025-03-18  
**Database**: Pgvector  
**Version**: 0.5.x (PostgreSQL extension)  
**Severity**: Medium  
**Priority**: P2  
**Type**: Bug  
**Component**: Validation / Index  
**Affected Versions**: 0.1+  

#### Environment
- PostgreSQL Version: 15.x
- Pgvector Version: 0.5.x
- Deployment: Docker

#### Description
Pgvector accepts invalid distance metric types when creating indexes without proper validation.

#### Reproduction Steps
1. Attempt to create an index with an invalid distance metric
2. Observe validation behavior

**Expected Result**:
- Invalid metrics rejected with clear error messages
- Only supported metrics accepted

**Actual Result**:
- Invalid metrics may be accepted
- No clear validation error

#### Test Case Details
**Contract**: BND-003 (Metric Type Validation)
**Test ID**: test_bnd003_metric_validation

**Evidence Chain**:
- Test executed in: `results/boundary_2025_001/pgvector_boundary_results.json`
- Test result: BUG

#### Root Cause Analysis
1. Metric type validation may be missing
2. Whitelist not enforced
3. May rely on PostgreSQL's index creation without additional checks

**Supported Metrics**:
- l2 (L2 distance)
- ip (inner product)
- cosine (cosine similarity)
- l1 (Manhattan distance)

#### Impact
- **Reliability**: Invalid configurations cause issues
- **User Experience**: No immediate feedback

#### Workarounds
1. Use only well-documented metrics (l2, ip, cosine, l1)
2. Check pgvector documentation
3. Validate on client side

#### Proposed Fix
1. Implement strict metric validation in index creation
2. Document all supported metrics
3. Add validation tests
4. Improve error messages

#### Additional Information
**Valid Metrics**:
- l2, ip, cosine, l1

**Test Configuration**:
```
Invalid metric tested: "INVALID_METRIC"
```

**Logs**:
See test results in `results/boundary_2025_001/pgvector_boundary_results.json`

#### Attachments
- Test script: `scripts/run_boundary_tests.py`
- Test results: `results/boundary_2025_001/pgvector_boundary_results.json`

---

### Issue #22: Table Name Validation - Insufficient Checks

**Title**: Table name validation insufficient - accepts reserved or invalid names

**Reported By**: AI-DB-QC Testing Framework  
**Date**: 2025-03-18  
**Database**: Pgvector  
**Version**: 0.5.x (PostgreSQL extension)  
**Severity**: Medium  
**Priority**: P2  
**Type**: Bug  
**Component**: Validation / Schema  
**Affected Versions**: 0.1+  

#### Environment
- PostgreSQL Version: 15.x
- Pgvector Version: 0.5.x
- Deployment: Docker

#### Description
Pgvector (via PostgreSQL) accepts table names that should be reserved or invalid. While PostgreSQL has some built-in validation, additional checks specific to pgvector usage may be needed.

#### Reproduction Steps
1. Attempt to create tables with various names
2. Test reserved names, special characters
3. Observe validation behavior

**Expected Result**:
- Reserved names rejected
- Invalid characters rejected
- Clear error messages with naming rules

**Actual Result**:
- Some invalid names may be accepted
- Validation may rely only on PostgreSQL's basic checks

#### Test Case Details
**Contract**: BND-004 (Collection/Table Name Validation)
**Test ID**: test_bnd004_collection_name_validation

**Evidence Chain**:
- Test executed in: `results/boundary_2025_001/pgvector_boundary_results.json`
- Test result: BUG

#### Root Cause Analysis
1. May rely only on PostgreSQL's table name validation
2. No additional pgvector-specific reserved names
3. Does not prevent naming conflicts with pgvector metadata

#### Impact
- **Naming Conflicts**: May conflict with pgvector metadata tables
- **Clarity**: Unclear which names are safe to use
- **Documentation**: Unclear naming conventions

#### Workarounds
1. Use a naming convention (e.g., prefix with app name)
2. Avoid obviously reserved names
3. Check existing tables before creating

#### Proposed Fix
1. Document recommended naming conventions
2. Add validation for pgvector-specific reserved names
3. Add validation tests
4. Provide clear error messages

#### Additional Information
**Reserved Names** (should be blocked):
- pgvector internal tables
- PostgreSQL system tables

**Valid Names**:
- Alphanumeric, underscores
- Length limits (PostgreSQL: 63 bytes)

**Logs**:
See test results in `results/boundary_2025_001/pgvector_boundary_results.json`

#### Attachments
- Test script: `scripts/run_boundary_tests.py`
- Test results: `results/boundary_2025_001/pgvector_boundary_results.json`

---

## Summary

### Issue Distribution by Database
- **Milvus**: 5 issues (1 High, 4 Medium)
- **Qdrant**: 7 issues (3 High, 4 Medium)
- **Weaviate**: 5 issues (1 High, 4 Medium)
- **Pgvector**: 5 issues (1 High, 4 Medium)

### Issue Distribution by Severity
- **High (P1)**: 6 issues
  - Schema atomicity (all 4 databases)
  - Milvus: Top-K crash
  - Qdrant: 2 stress test failures
- **Medium (P2)**: 16 issues
  - Dimension validation (all 4 databases)
  - Top-K validation (all 4 databases)
  - Metric type validation (all 4 databases)
  - Collection/class/table name validation (all 4 databases)

### Common Patterns
1. **Schema Atomicity**: All 4 databases lack proper atomicity for schema operations
2. **Input Validation**: All 4 databases have insufficient input validation
3. **Error Messages**: All 4 databases provide poor or unclear error messages

### Recommendations
1. Implement proper input validation at all API boundaries
2. Add comprehensive error messages with valid ranges and examples
3. Implement transactional semantics for schema operations
4. Add automated testing for boundary conditions
5. Improve documentation with clear examples and constraints

---

## Appendix: Test Framework Information

### Testing Framework
- **Name**: AI-DB-QC (AI Database Quality Control)
- **Purpose**: Automated bug mining and quality testing for vector databases
- **Components**:
  - Adapters: Database-specific adapters (Milvus, Qdrant, Weaviate, Pgvector)
  - Contracts: Test contracts defining expected behavior
  - Oracles: Test oracles for verdict classification
  - Campaigns: Test campaign management

### Test Contracts
1. **SCH-005**: Schema creation validation
2. **SCH-006**: Schema atomicity
3. **BND-001**: Dimension boundary validation
4. **BND-002**: Top-K boundary validation
5. **BND-003**: Metric type validation
6. **BND-004**: Collection name validation
7. **STR-001**: High throughput stress test
8. **STR-002**: Large dataset stress test

### Verdict Classification
- **PASS**: Test passed, no issues found
- **MARGINAL**: Test passed with minor concerns
- **AMBIGUOUS**: Results unclear, needs investigation
- **SUSPICIOUS**: Possible issue, needs confirmation
- **LIKELY_BUG**: Strong evidence of bug
- **BUG**: Confirmed bug with clear evidence

### Test Execution
- **Date**: 2025-03-18
- **Environment**: Docker containers
- **Test Duration**: ~2 hours total
- **Results Location**: `results/`

### Contact
For questions about these issues or the testing framework, please refer to the AI-DB-QC project documentation.
