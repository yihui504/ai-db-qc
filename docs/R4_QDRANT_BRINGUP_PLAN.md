# R4.0: Qdrant Real-Environment Bring-Up Plan

**Plan Version**: 1.0
**Date**: 2026-03-09
**Phase**: R4.0 - Pre-Implementation Validation
**Status**: Plan - Ready for Execution

---

## Executive Summary

This plan defines the minimal steps to bring up a real Qdrant environment and validate core operations before implementing the full R4 differential testing framework.

**Purpose**: Verify Qdrant can serve as the second database for R4

**Success Criteria**: All 5 core operations (create, upsert, search, delete, drop) work against real Qdrant

---

## 1. Environment Setup

### 1.1 Qdrant Installation (Docker - Recommended)

**Option A: Docker (Recommended)**

```bash
# Pull and run Qdrant
docker run -d -p 6333:6333 -p 6334:6334 \
    --name qdrant \
    -v $(pwd)/qdrant_storage:/qdrant/storage \
    qdrant/qdrant
```

**Parameters**:
- `-p 6333:6333` - HTTP API port
- `-p 6334:6334` - gRPC API port
- `-v ...` - Persistent storage (optional but recommended)
- `--name qdrant` - Container name for easy management

**Verification**:
```bash
docker ps | grep qdrant
```

**Expected output**: Container running with ports mapped

---

**Option B: Qdrant Cloud (Alternative)**

1. Visit https://cloud.qdrant.io/
2. Create free tier account
3. Create cluster
4. Get API endpoint and API key
5. Use cloud URL instead of localhost

---

**Option C: Binary Installation**

```bash
# Download
curl -L https://github.com/qdrant/qdrant/releases/latest/download/qdrant-linux-x86_64.tar.gz | tar xz

# Run
./qdrant
```

---

### 1.2 Python Client Installation

```bash
# Install Qdrant Python client
pip install qdrant-client

# Verify installation
python -c "from qdrant_client import QdrantClient; print('Qdrant client installed')"
```

**Required version**: qdrant-client >= 1.7.0

**Dependencies**:
- `httpx` - HTTP client (usually installed with qdrant-client)
- `pydantic` - Data validation (usually installed with qdrant-client)

---

## 2. Health Check Procedures

### 2.1 Container Health Check

```bash
# Check if container is running
docker ps | grep qdrant

# Check container logs
docker logs qdrant --tail 20

# Check for specific health indicators
docker logs qdrant | grep "Qdrant is ready"
```

**Expected output**:
- Container status: "Up"
- Log message: "Qdrant is ready to accept connections"

---

### 2.2 HTTP Endpoint Check

```bash
# Check HTTP endpoint
curl http://localhost:6333/

# Expected output: Qdrant version info
# {"title":"qdrant","version":"x.y.z",...}

# Check collections endpoint
curl http://localhost:6333/collections

# Expected output: Empty collections list
# {"result":{"collections":[],...}}
```

---

### 2.3 Web UI (Optional but Useful)

**Access**: http://localhost:6333/dashboard

**Features**:
- Visual collection browser
- Query builder
- Performance metrics
- Cluster information

---

## 3. Connection Verification

### 3.1 Python Connection Test

```python
from qdrant_client import QdrantClient

# Connect to Qdrant
client = QdrantClient(url="http://localhost:6333")

# Verify connection
collections = client.get_collections()
print(f"Connected to Qdrant at localhost:6333")
print(f"Qdrant version: {client.get_cluster_info().status}")
print(f"Current collections: {len(collections.collections)}")
```

**Expected output**:
```
Connected to Qdrant at localhost:6333
Qdrant version: <status>
Current collections: 0
```

---

### 3.2 Connection Parameters

**For local Docker**:
```python
client = QdrantClient(
    url="http://localhost:6333",
    timeout=30.0
)
```

**For Qdrant Cloud**:
```python
client = QdrantClient(
    url="https://your-cluster.cloud.qdrant.io:6333",
    api_key="your-api-key-here",
    timeout=30.0
)
```

**For in-memory** (development only):
```python
client = QdrantClient(":memory:")
```

---

## 4. Core Operations to Validate

### 4.1 Operation Checklist

| Operation | Qdrant API | Purpose | Test Case |
|-----------|------------|---------|-----------|
| **create_collection** | `create_collection()` | Create vector collection | Smoke test |
| **upsert** | `upsert()` | Insert/update vectors | Smoke test |
| **search** | `search()` | Vector similarity search | Smoke test |
| **delete** | `delete()` | Delete by IDs | Smoke test |
| **drop_collection** | `delete_collection()` | Remove collection | Smoke test |

---

### 4.2 Expected Behavior for Each Operation

#### Create Collection

**Input**:
```python
client.create_collection(
    collection_name="test_smoke",
    vectors_config={
        "size": 128,
        "distance": "Cosine"
    }
)
```

**Expected**: Collection created successfully
**Failure Mode**: Exception with clear error message

---

#### Upsert

**Input**:
```python
from qdrant_client.models import PointStruct

client.upsert(
    collection_name="test_smoke",
    points=[
        PointStruct(
            id=1,
            vector=[0.1] * 128,
            payload={"color": "red"}
        ),
        PointStruct(
            id=2,
            vector=[0.9] * 128,
            payload={"color": "blue"}
        )
    ]
)
```

**Expected**: 2 points inserted
**Failure Mode**: Exception if collection doesn't exist

---

#### Search

**Input**:
```python
results = client.search(
    collection_name="test_smoke",
    query_vector=[0.1] * 128,
    limit=5
)
```

**Expected**: List of results, top match should be point ID=1
**Failure Mode**: Exception or empty results

---

#### Delete

**Input**:
```python
client.delete(
    collection_name="test_smoke",
    points_selector=[1]
)
```

**Expected**: Point ID=1 deleted
**Failure Mode**: Exception if collection doesn't exist

---

#### Drop Collection

**Input**:
```python
client.delete_collection(collection_name="test_smoke")
```

**Expected**: Collection removed
**Failure Mode**: Exception if collection doesn't exist

---

## 5. Smoke Script Specification

### 5.1 Script Requirements

**File**: `scripts/smoke_test_qdrant.py`

**Requirements**:
1. Accept optional URL parameter (default: localhost:6333)
2. Execute all 5 core operations in sequence
3. Report success/failure for each operation
4. Clean up (delete test collection) at end
5. Exit with appropriate status code

---

### 5.2 Script Structure

```python
#!/usr/bin/env python3
"""
Qdrant Smoke Test - Real Environment Validation

Validates core Qdrant operations:
1. create_collection
2. upsert
3. search
4. delete (by ID)
5. delete_collection
"""

import sys
from qdrant_client import QdrantClient, models

# Configuration
COLLECTION_NAME = "test_smoke_r4"
VECTOR_DIM = 128
VECTOR_SIZE = 128

def main():
    # 1. Connect
    # 2. create_collection
    # 3. upsert
    # 4. search
    # 5. delete
    # 6. search (verify deletion)
    # 7. delete_collection

if __name__ == "__main__":
    sys.exit(main())
```

---

### 5.3 Expected Output Format

```
=== Qdrant Smoke Test ===
Target: http://localhost:6333

[1/6] Connection... OK
[2/6] Create collection... OK
[3/6] Upsert points... OK (inserted 2 points)
[4/6] Search... OK (found 2 results)
[5/6] Delete point... OK (deleted 1 point)
[6/6] Verify deletion... OK (1 result remaining)
[7/6] Drop collection... OK

=== All Tests Passed ===
Qdrant is ready for R4 implementation.
```

---

## 6. Troubleshooting

### 6.1 Connection Issues

**Symptom**: `ConnectionError` or timeout

**Checks**:
1. Is Qdrant container running? `docker ps`
2. Is port 6333 exposed? `docker port qdrant`
3. Is firewall blocking localhost:6333?
4. Try curl: `curl http://localhost:6333/`

---

### 6.2 Collection Already Exists

**Symptom**: Exception on `create_collection`

**Solution 1**: Delete existing collection
```python
client.delete_collection(collection_name="test_smoke")
```

**Solution 2**: Check existence first
```python
from qdrant_client import models
client.create_collection(
    collection_name="test_smoke",
    vectors_config=models.VectorParams(size=128, distance=models.Distance.COSINE),
    # Add this to skip if exists (not recommended for testing)
)
```

---

### 6.3 Import Errors

**Symptom**: `ModuleNotFoundError: No module named 'qdrant_client'`

**Solution**:
```bash
pip install qdrant-client
```

---

## 7. Validation Criteria

### 7.1 Success Criteria

**All of the following must pass**:

| Check | Requirement |
|-------|-------------|
| Container running | Docker container "Up" |
| HTTP endpoint responds | `curl http://localhost:6333/` returns JSON |
| Python connection | `client.get_collections()` succeeds |
| create_collection | Collection created without error |
| upsert | Points inserted successfully |
| search | Results returned (non-empty) |
| delete | Point removed from collection |
| delete_collection | Collection removed |

---

### 7.2 Failure Modes

**Hard Failures** (must fix before proceeding):
- Container won't start
- Connection fails
- Any core operation fails with exception

**Soft Failures** (document and proceed):
- Different error message format (adapt adapter)
- Unexpected but workable behavior

---

## 8. Next Steps After Smoke Test

### 8.1 If Smoke Test Passes

1. Document results in `docs/R4_QDRANT_SMOKE_RESULTS.md`
2. Proceed to R4 Phase 1: Qdrant adapter implementation
3. Start with basic adapter supporting 5 core operations

---

### 8.2 If Smoke Test Fails

1. Document failure mode
2. Troubleshoot per Section 6
3. Re-run smoke test
4. If persistent failure, reassess Qdrant as second database choice

---

## 9. Environment Cleanup

### 9.1 Stop Qdrant

```bash
# Stop container
docker stop qdrant

# Remove container (optional)
docker rm qdrant

# Remove volume (optional - wipes data)
docker volume rm qdrant_storage
```

---

### 9.2 Restart Qdrant

```bash
# Start existing container
docker start qdrant

# Or recreate if removed
docker run -d -p 6333:6333 --name qdrant qdrant/qdrant
```

---

## 10. Metadata

- **Plan**: R4.0 Qdrant Bring-Up Plan
- **Version**: 1.0
- **Date**: 2026-03-09
- **Purpose**: Pre-implementation validation for R4
- **Prerequisites**: Docker, Python 3.8+, pip
- **Estimated Time**: 30-60 minutes
- **Status**: Ready for Execution

---

**END OF R4.0 QDRANT BRING-UP PLAN**

**Next Step**: Execute smoke test script against real Qdrant instance.
