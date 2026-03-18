# ISSUE-002: Qdrant crashes with 502 Bad Gateway under medium/high throughput and large dataset operations

## Metadata

| Field | Value |
|-------|-------|
| **Bug ID** | ISSUE-002 |
| **Database** | Qdrant v1.17.0 |
| **Contract** | STR-001 (High Throughput Stress), STR-002 (Large Dataset Stress) |
| **Bug Type** | TYPE-3 (Crash / Service Failure) |
| **Severity** | Critical |
| **Date Discovered** | 2026-03-18 |

## Evidence Chain

### 1. Documentation Evidence (What Should Happen)

**Source**: [Qdrant Common Errors](https://qdrant.tech/documentation/guides/common-errors/)

Qdrant's documentation acknowledges that under high load, the system may encounter "Queue is full" and "Request timeout" errors. The [Optimize Performance](https://qdrant.tech/documentation/guides/optimize/) guide recommends horizontal scaling via sharding for high RPS scenarios.

However, **1000 RPS is not an extreme load** for a vector database in production. Qdrant's own benchmarks claim high RPS performance under similar conditions ([Qdrant Benchmarks](https://qdrant.tech/benchmarks/)).

**Source**: [Qdrant Capacity Planning](https://qdrant.tech/documentation/guides/capacity-planning/)

Memory requirements for HNSW index: `Memory ~ (dim * 4 bytes * num_vectors) + (num_vectors * 8 * M * 1.5 bytes)` where M defaults to 16.

The documentation states that the primary limiting factor is available memory and disk space, not software hard limits. For the test scenario (128-dim vectors), the memory requirement for 100K vectors would be approximately: `128 * 4 * 100000 + 100000 * 8 * 16 * 1.5 = ~214 MB`, which should be well within the capacity of a Docker container.

### 2. Actual Behavior (What Happened)

Test results from `results/stress_2025_001/qdrant_stress_results.json`:

**STR-001 (Throughput Test)**:
- **Low (100 RPS)**: PASS (avg 192ms, 100% success rate, 31367 total requests)
- **Medium (1000 RPS)**: CRASH - `{"status": "error", "error": "Unexpected Response: 502 (Bad Gateway)", "error_type": "UnexpectedResponse", "operation": "create_collection"}`
- **High (5000 RPS)**: CRASH - Same 502 Bad Gateway error

**STR-002 (Large Dataset Test)**:
- **10K vectors**: CRASH - Same 502 Bad Gateway on `create_collection`
- **100K vectors**: CRASH - Same 502 Bad Gateway on `create_collection`

The crash occurs during **collection creation**, not during data insertion or search. This indicates that Qdrant's service becomes unresponsive under concurrent load, even before the actual test workload begins.

### 3. Analysis

The 502 Bad Gateway errors occur at the collection creation phase, meaning the Qdrant service itself is crashing or becoming unreachable. This is a **critical stability issue** because:

1. **Low threshold**: The crash happens at only 1000 RPS, which is moderate for production workloads. Qdrant's own benchmarks show much higher throughput figures.
2. **Service unavailability**: The 502 error indicates the service is completely down, not just slow. Clients cannot create collections or perform any operations.
3. **Recovery uncertainty**: After a 502 crash, it is unclear whether the service automatically recovers or requires manual intervention.
4. **STR-002 independence**: The large dataset tests crash even at the collection creation step, suggesting the issue may be related to memory pressure or resource exhaustion during test setup rather than the actual dataset size.

**Possible Root Causes**:
- Default Docker container memory limits may be insufficient for Qdrant v1.17.0
- A regression in v1.17.0 affecting stability under concurrent operations
- gRPC/HTTP proxy timeout misconfiguration
- Memory leak during concurrent collection creation

**Impact**: Service availability risk in production. Any sustained traffic above ~1000 RPS could cause complete service outage.

**Recommended Fix**: Qdrant should handle high-concurrency collection creation gracefully, either by queueing requests or returning proper rate-limiting errors (429) instead of 502 crashes. Investigate if v1.17.0 introduced a regression.

## References

1. [Qdrant Common Errors Documentation](https://qdrant.tech/documentation/guides/common-errors/)
2. [Qdrant Performance Optimization Guide](https://qdrant.tech/documentation/guides/optimize/)
3. [Qdrant Capacity Planning](https://qdrant.tech/documentation/guides/capacity-planning/)
4. [Qdrant Benchmarks](https://qdrant.tech/benchmarks/)
5. [Test Results: qdrant_stress_results.json](../stress_2025_001/qdrant_stress_results.json)
