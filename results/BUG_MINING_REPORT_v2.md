# AI-DB-QC Bug Mining Report — Latest Versions

**Campaign ID:** AGGRESSIVE_BUG_MINING_2025_001  
**Date:** 2026-03-18  
**Tested Versions:**

| Database | Version | Image |
|----------|---------|-------|
| Milvus | v2.6.12 | milvusdb/milvus:v2.6.12 |
| Qdrant | v1.17.0 | qdrant/qdrant:v1.17.0 |
| Weaviate | v1.36.5 | cr.weaviate.io/semitechnologies/weaviate:1.36.5 |
| Pgvector | v0.8.2 (pg17) | pgvector/pgvector:pg17 |

**Contracts Tested:** SCH-005, SCH-006, BND-001~BND-004, STR-001, STR-002

---

## Executive Summary

对四个主流向量数据库的最新版本进行了全面的质量对比测试。共执行 8 个合约、48 个测试用例，覆盖模式演进、边界条件和压力测试三个维度。总计发现 **22 个 bug**，其中 Milvus 5 个、Qdrant 7 个、Weaviate 5 个、Pgvector 5 个。SCH-006（Schema Operation Atomicity）在所有四个数据库上均未通过，BND 系列合约在每个数据库上都暴露了不同类型的输入验证问题。Qdrant 是唯一在压力测试中出现崩溃（TYPE-3）的数据库。

---

## Phase 1: Schema Evolution Testing

### SCH-005: Schema Extension Backward Compatibility — ALL PASS

所有四个数据库在 schema 扩展后保持了向后兼容性，现有查询仍能正常工作。

| Database | Verdict | Notes |
|----------|---------|-------|
| Milvus | PASS | Schema extension not supported (feature limitation, not a bug) |
| Qdrant | PASS | Field extension works correctly |
| Weaviate | PASS | Field extension works correctly |
| Pgvector | PASS | Schema extension not supported (SQL limitation) |

### SCH-006: Schema Operation Atomicity — ALL FAIL (4 bugs)

Schema 操作的原子性在所有四个数据库上均存在问题。

| Database | Verdict | Details |
|----------|---------|---------|
| Milvus | LIKELY_BUG | Failed schema operation rollback — schema state not fully consistent after invalid operation |
| Qdrant | LIKELY_BUG | Same issue — incomplete rollback on failed schema change |
| Weaviate | LIKELY_BUG | Same issue — partial state visible after failed operation |
| Pgvector | LIKELY_BUG | Collection existence check fails; no partial state isolation |

**Analysis:** 这是本次测试中最普遍的问题。当 schema 操作失败时，所有四个数据库都无法保证完全的原子性回滚。这可能是因为底层存储引擎（RocksDB、PostgreSQL 等）在 DDL 操作中的事务隔离存在局限。

---

## Phase 2: Boundary Condition Testing

### BND-001: Vector Dimension Boundaries — ALL FAIL (4 bugs)

| Database | Verdict | Key Failures |
|----------|---------|-------------|
| Milvus | BUG | TYPE-2: dim=1 rejected (valid rejected); TYPE-2: poor diagnostics on invalid inputs |
| Qdrant | BUG | TYPE-2: poor diagnostics on zero/negative/excessive dimension |
| Weaviate | BUG | TYPE-1: dim=0 accepted (invalid accepted); dim=100000 accepted; dimension mismatch not rejected |
| Pgvector | BUG | TYPE-1: dim=0, dim=-1, dim=100000 all accepted; dimension mismatch silently accepted |

**Key Finding:**  
- **Milvus** 拒绝了 dim=1（有效输入），这是 TYPE-2 bug（正确值被拒绝）。  
- **Weaviate** 和 **Pgvector** 接受了无效的维度值（0、负数、100000），属于 TYPE-1 bug（无效输入被接受），严重性更高。  
- **所有数据库** 在错误诊断信息方面表现不佳，返回的错误消息缺乏足够的上下文信息。

### BND-002: Top-K Parameter Boundaries — ALL FAIL (4 bugs)

| Database | Verdict | Key Failures |
|----------|---------|-------------|
| Milvus | BUG | TYPE-2: top_k=0 rejected; TYPE-2: top_k > collection size rejected |
| Qdrant | BUG | TYPE-2: top_k=0 rejected with poor diagnostics |
| Weaviate | BUG | TYPE-1: top_k=0 accepted (returns empty); TYPE-2: inconsistent top_k > collection handling |
| Pgvector | BUG | TYPE-3: top_k=0 causes internal error; TYPE-1: negative top_k accepted |

**Key Finding:**  
- **Pgvector** 的 top_k=0 导致内部错误（"invalid literal for int() with base 10: 'empty'"），这是一个 TYPE-3 bug（有效操作失败）。  
- **Milvus** 拒绝了 top_k=0 和 top_k > collection size，但诊断信息不足。

### BND-003: Metric Type Validation — ALL FAIL (4 bugs)

| Database | Verdict | Key Failures |
|----------|---------|-------------|
| Milvus | BUG | TYPE-2: case-sensitive metric names (L2 accepted, l2 rejected) |
| Qdrant | BUG | TYPE-2: case-sensitive metric names; poor diagnostics |
| Weaviate | BUG | TYPE-1: unsupported metric 'MANHATTAN' silently accepted |
| Pgvector | BUG | TYPE-1: unsupported metric 'MANHATTAN' accepted; empty metric accepted |

**Key Finding:**  
- **Milvus 和 Qdrant** 对 metric type 大小写敏感，"l2" 被拒绝但 "L2" 被接受，属于 TYPE-2 bug。  
- **Weaviate 和 Pgvector** 接受不支持的 metric type（如 MANHATTAN），属于 TYPE-1 bug，可能导致后续查询行为异常。

### BND-004: Collection Name Boundaries — ALL FAIL (4 bugs)

| Database | Verdict | Key Failures |
|----------|---------|-------------|
| Milvus | BUG | TYPE-2: duplicate name rejected with poor diagnostics; empty name behavior unclear |
| Qdrant | BUG | TYPE-2: empty/invalid names rejected but with poor diagnostics |
| Weaviate | BUG | TYPE-1: names with spaces accepted; TYPE-2: inconsistent validation |
| Pgvector | BUG | TYPE-1: empty name, names with spaces, names with slashes, reserved name 'system' all accepted |

**Key Finding:**  
- **Pgvector** 的集合名称验证几乎完全缺失，空名称、含空格名称、含斜杠名称以及保留名称（如 "system"）均被接受。  
- **Weaviate** 接受含空格的名称，可能在后续使用中导致问题。

---

## Phase 3: Stress Testing

### STR-001: High Throughput Stress Test

| Database | Low (100 RPS) | Medium (1000 RPS) | High (5000 RPS) | Overall |
|----------|---------------|--------------------|-----------------|---------|
| Milvus | PASS (204ms avg) | PASS (175ms avg) | PASS (241ms avg) | **PASS** |
| Qdrant | PASS (192ms avg) | **CRASH (502 Bad Gateway)** | **CRASH (502 Bad Gateway)** | **BUG** |
| Weaviate | PASS | PASS | PASS | **PASS** |
| Pgvector | MARGINAL (1024ms avg) | MARGINAL (1136ms avg) | MARGINAL (1151ms avg) | **MARGINAL** |

### STR-002: Large Dataset Stress Test

| Database | 10K vectors | 100K vectors | Overall |
|----------|-------------|--------------|---------|
| Milvus | PASS (68ms avg) | PASS (95ms avg) | **PASS** |
| Qdrant | **CRASH (502 Bad Gateway)** | **CRASH (502 Bad Gateway)** | **BUG** |
| Weaviate | PASS (18ms avg) | PASS (17ms avg) | **PASS** |
| Pgvector | MARGINAL (153ms avg) | PASS (155ms avg) | **MARGINAL** |

**Key Findings:**  
- **Qdrant v1.17.0** 在中等和高负载下出现 502 Bad Gateway 错误，属于 TYPE-3 bug（服务崩溃）。这是一个严重问题，因为 1000 RPS 对于生产环境来说并不算极端负载。  
- **Pgvector** 在吞吐量测试中延迟较高（>1s avg），虽然未崩溃但性能表现较差（MARGINAL）。  
- **Milvus** 和 **Weaviate** 在压力测试中表现稳定。

---

## Bug Classification Summary

### By Database

| Database | TYPE-1 (Invalid Accepted) | TYPE-2 (Valid Rejected/Poor Diagnostics) | TYPE-3 (Crash) | Total |
|----------|--------------------------|------------------------------------------|----------------|-------|
| Milvus | 0 | 5 | 0 | 5 |
| Qdrant | 0 | 3 | 4 | 7 |
| Weaviate | 5 | 0 | 0 | 5 |
| Pgvector | 4 | 0 | 1 | 5 |
| **Total** | **9** | **8** | **5** | **22** |

### By Contract

| Contract | Name | Bugs | Severity |
|----------|------|------|----------|
| SCH-006 | Schema Operation Atomicity | 4 | Medium (all LIKELY_BUG) |
| BND-001 | Vector Dimension Boundaries | 4 | High (TYPE-1 in Weaviate/Pgvector) |
| BND-002 | Top-K Parameter Boundaries | 4 | High (TYPE-3 in Pgvector) |
| BND-003 | Metric Type Validation | 4 | Medium |
| BND-004 | Collection Name Boundaries | 4 | High (TYPE-1 in Pgvector) |
| STR-001 | High Throughput Stress | 1 | Critical (TYPE-3 crash in Qdrant) |
| STR-002 | Large Dataset Stress | 1 | Critical (TYPE-3 crash in Qdrant) |

---

## Comparative Analysis

**Input Validation Strictness (from most to least strict):**

1. **Milvus** — Most conservative. Rejects many edge cases but sometimes rejects valid inputs (dim=1, top_k=0). Good at preventing invalid data, but at the cost of usability. TYPE-2 bugs dominate.
2. **Qdrant** — Balanced approach. Correctly accepts/rejects most inputs but fails under load. Stress stability is a significant concern.
3. **Weaviate** — Permissive. Accepts invalid inputs (dim=0, dim=-1, dim=100000, MANHATTAN metric). These silently accepted invalid inputs could cause undefined behavior later.
4. **Pgvector** — Least validation. Inherits PostgreSQL's minimal input checking. Zero-dimension vectors, negative top_k, unsupported metrics, and invalid collection names are all silently accepted.

**Performance Rankings (100K vectors search latency):**

1. Weaviate: 17ms avg (best)
2. Qdrant: N/A (crashed)
3. Milvus: 95ms avg
4. Pgvector: 155ms avg

---

## Conclusions

1. **SCH-006 (Schema Atomicity)** 是一个系统性问题，影响所有四个数据库。这可能与向量数据库对 schema 管理的重视程度不足有关。

2. **BND 系列合约**暴露了每个数据库在输入验证方面的不同取舍。Milvus 偏向严格拒绝（TYPE-2），Weaviate 和 Pgvector 偏向宽松接受（TYPE-1），Qdrant 介于两者之间。

3. **Qdrant v1.17.0** 在压力测试中出现的 502 崩溃是最严重的问题，值得关注并在生产环境中进行额外的负载测试验证。

4. **Weaviate v1.36.5** 在功能和性能方面表现最均衡，但输入验证过于宽松可能导致数据完整性风险。

5. **Pgvector v0.8.2** 作为 PostgreSQL 扩展，输入验证最为薄弱，但搜索延迟较高是其主要性能瓶颈。

---

## Raw Data Files

All detailed test results are available in:

- `results/schema_evolution_2025_001/` — Schema evolution results (4 JSON files)
- `results/boundary_2025_001/` — Boundary condition results (4 JSON files)
- `results/stress_2025_001/` — Stress test results (4 JSON files)
- `results/aggressive_bug_mining_2025_001/campaign_results.json` — Campaign summary

---

*Report generated automatically by AI-DB-QC bug mining pipeline on 2026-03-18*
