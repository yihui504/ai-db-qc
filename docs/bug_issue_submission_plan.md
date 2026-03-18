# Bug Issue 提交计划

**生成日期**: 2026-03-17
**框架**: ai-db-qc (Contract-Based Runtime Defect Detection)

---

## 已确认可提交的 Issue (4个)

### Issue 1: DEF-001 — count_entities 不反映删除操作直到压缩

**数据库**: Milvus v2.6.10
**合约**: R3B
**严重程度**: High
**标题建议**: `[Bug] count_entities / num_entities does not reflect deletions until compaction`

**复现步骤**:
1. 创建 collection，插入 M=1000 个 entities
2. 删除 N=100 个 entities: `collection.delete(expr="id in [id1, ..., idN]")`
3. 执行 `collection.flush()`
4. 读取 `collection.num_entities` → 返回 1000，期望 900

**影响**: 使用 num_entities 进行容量管理、计费计算的应用会收到错误数据。

---

### Issue 2: DEF-002 — 动态字段插入后 ANN 搜索不可见

**数据库**: Milvus v2.6.10
**合约**: SCH-001
**严重程度**: High
**标题建议**: `[Bug] enable_dynamic_field=True: entities inserted after dynamic schema extension invisible to ANN search`

**复现步骤**:
1. 创建 collection (enable_dynamic_field=True)，插入 N_base=200 个 entities
2. 扩展 schema，插入 N_tagged=300 个带新动态字段的 entities
3. 执行 flush 和 rebuild index
4. ANN search (top_k=300) → 仅返回 200 个，缺失 300 个 tagged entities

**影响**: 使用动态字段的应用会静默丢失召回率，无错误提示。

---

### Issue 3: DEF-003 — 动态字段过滤返回假阳性

**数据库**: Milvus v2.6.10
**合约**: SCH-002
**严重程度**: High
**标题建议**: `[Bug] filtered search with dynamic field predicates returns false positives for pre-extension entities`

**复现步骤**:
1. 创建 collection (enable_dynamic_field=True)，插入 200 个无 tag 的 entities
2. 扩展 schema，插入 300 个带 tag_value 字段的 entities
3. 执行 filtered search: `filter="tag_value > 0"`
4. 期望: 仅返回 300 个 tagged entities
5. 实际: 返回 100 个无 tag 的 entities (false positives, 50% 假阳性率)

**影响**: 依赖过滤向量搜索的应用会返回错误结果，无任何警告。

---

### Issue 4: DEF-004 — 混合 Schema 集合中 count-delete 不一致

**数据库**: Milvus v2.6.10
**合约**: SCH-004
**严重程度**: Medium
**标题建议**: `[Bug] count_entities incorrect after deletions in mixed-schema collections`

**复现步骤**:
1. 创建 collection (enable_dynamic_field=True)，插入 N_base=200 + N_tagged=300
2. 删除 N_deleted=50
3. 执行 flush
4. 读取 count_entities → 返回 500，期望 450 (=200+300-50)

**影响**: 监控和容量管理受影响，但查询结果仍然正确过滤。

---

## Qdrant/Weaviate/pgvector 扫描结果

| 测试类型 | Qdrant | Weaviate | pgvector |
|----------|--------|----------|----------|
| R8 数据漂移 | PASS | PASS | PASS |
| R7 并发压力 | PASS | PASS | PASS |
| MR-01 语义等价 | 100% PASS | 100% PASS | 100% PASS |
| MR-03 Hard Negative | 100% VIOLATION* | 100% VIOLATION* | 100% VIOLATION* |

*MR-03 VIOLATION 是 embedding 模型限制（all-MiniLM-L6-v2 无法区分 domain-specific hard negatives），非数据库 bug。

**结论**: 在当前测试场景下，Qdrant、Weaviate、pgvector 未发现可提交的 bug。Milvus 是唯一发现 4 个结构化缺陷的数据库。

---

## 提交优先级

1. **立即提交**: DEF-001 (R3B count_entities) — 最明确，最易复现
2. **高优先级**: DEF-002, DEF-003 (动态字段) — 影响严重
3. **中优先级**: DEF-004 (混合 schema count) — 较低实际影响

---

---

## 新发现：pgvector SCH-002 Filter Bug (2026-03-17)

### DEF-005: pgvector 动态字段过滤假阴性

**数据库**: pgvector (pgvector/pgvector:pg16)
**合约**: SCH-002
**严重程度**: High
**标题建议**: `[Bug] pgvector filtered search returns 0 results for dynamically added columns`

**复现步骤**:
1. 创建表，插入 200 个无额外字段的基础 entities
2. ALTER TABLE ADD COLUMN，插入 100 个带新字段的 tagged entities
3. 执行 filtered search: `WHERE new_column > 0`
4. 期望: 返回 100 个 tagged entities
5. 实际: 返回 0 个 entities (假阴性)

**定量证据**:
```
n_base=200, n_tagged=100
Expected: 80-100 tagged entities match filter
Actual: 0 entities returned
False negative rate: 100%
```

**根因分析**: pgvector 在动态添加列后，新列的过滤条件无法正确匹配已插入的数据。这可能是 PostgreSQL 的表结构变更与向量索引的同步问题。

---

## 新发现：Qdrant Range Filter Bug (2026-03-17)

### DEF-006: Qdrant 范围过滤不正确应用

**数据库**: Qdrant (qdrant/qdrant:latest)
**合约**: HYB-001 (Filter Pre-Application)
**严重程度**: High
**标题建议**: `[Bug] Qdrant range filter (gt/lt/gte/lte) does not correctly filter results`

**复现步骤**:
1. 创建 collection，插入 3 个向量，payload 包含 score 字段 (10, 50, 90)
2. 执行 filtered_search with filter: `{"score": {"gt": 50}}`
3. 期望: 仅返回 score > 50 的结果 (id with score=90)
4. 实际: 返回了 score=50 和 score=90 两个结果

**定量证据**:
```
Filter: score > 50
Expected: [score=90]
Actual: [score=50, score=90]  ← score=50 不应返回

Filter: 30 <= score <= 80
Expected: [score=50]
Actual: [score=90]  ← score=90 不应返回
```

**根因分析**: Qdrant 的 Range filter (gt/lt/gte/lte) 没有正确应用到过滤阶段，可能在向量评分之后才应用，或者条件解析有问题。

---

## 新发现：Weaviate SCH-002 Filter Bug (2026-03-17)

### DEF-007: Weaviate 过滤假阴性

**数据库**: Weaviate (weaviate:1.27.0)
**合约**: SCH-002 (Query Compatibility Across Schema Updates)
**严重程度**: High
**标题建议**: `[Bug] Weaviate filtered search returns empty results for newly added property`

**复现步骤**:
1. 创建 collection，插入 50 个不带 category 字段的向量
2. 再插入 50 个带 category="premium" 字段的向量
3. 执行 filtered_search with filter: `{"category": "premium"}`
4. 期望: 返回 50 个结果
5. 实际: 返回 0 个结果

**定量证据**:
```
Schema: initial (50 entities) + extended (50 entities with category)
Filter: category == "premium"
Expected: 50 entities
Actual: 0 entities ← 过滤假阴性
```

**根因分析**: Weaviate 在 schema 扩展后，新添加的属性过滤返回空结果。这可能是 schema 缓存问题或属性索引未正确更新。

---

## 附录: 测试环境

- Milvus: `milvusdb/milvus:v2.6.10` (Docker)
- Qdrant: `qdrant/qdrant:latest` (Docker)
- Weaviate: `semitechnologies/weaviate:1.27.0` (Docker)
- pgvector: `pgvector/pgvector:pg16` (Docker)
- Embedding: sentence-transformers (all-MiniLM-L6-v2, dim=384)
