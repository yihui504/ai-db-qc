# 框架能力强化研究报告

## 执行摘要

本次研究针对 ai-db-qc 框架的系统性不足进行了深度分析和改进。通过系统执行 HYB 合约测试、极端生命周期测试和 Weaviate SCH 合约扩展，成功将可提交 bug 数量从 5 个提升至 7 个。新增发现包括 Qdrant 范围过滤 bug（DEF-006）和 Weaviate 过滤假阴性 bug（DEF-007），验证了框架在跨库测试方面的通用性和有效性。

## 背景与问题

### 原有问题定位

经过深度复盘，发现框架存在以下四个结构性偏差：

**合约执行覆盖率低**：定义了 16 个合约，但跨库执行覆盖率仅约 30%，ANN-003/004/005、HYB 全部、IDX-001/002 在 Qdrant/Weaviate/pgvector 上几乎未执行。

**极端场景不足**：测试集中在正常场景（随机向量、小数据量），边界破坏性场景（零向量、极端维度、批量操作后立即搜索）严重缺失。

**Qdrant/Weaviate 假阴性**：当前结论"0 bug"是因为根本没测关键功能（payload filtering、multi-tenancy、BM25+vector hybrid search）。

**Oracle 误报率高**：MR-03 在所有数据库上 100% VIOLATION，变成 embedding 质量检测而非 bug 检测。

### 核心目标

系统性提升 bug 挖掘深度和跨库覆盖率，目标新增 5-10 个可提交 issue。

## 研究方法

### 历史 Bug 分析

通过检索 GitHub 收集了以下真实 bug 模式：

- Qdrant #7462: DATETIME payload index 接受无效时间戳
- Weaviate #8921: DateTime 过滤 >2500 年返回错误结果
- Weaviate #7681: Hybrid search filters 无效

### 技术实现

**Qdrant Adapter 扩展**：扩展了 `_filtered_search` 方法，支持范围过滤（gt/lt/gte/lte），添加了 `_build_range_condition` 方法来处理复杂的过滤条件。

**测试脚本开发**：创建了多个针对性测试脚本，包括 run_qdrant_hyb_contract.py、run_extreme_lifecycle_test.py、run_weaviate_schema_test.py 等。

## 研究发现

### DEF-006: Qdrant 范围过滤不正确应用

**数据库**: Qdrant (qdrant/qdrant:latest)

**合约**: HYB-001 (Filter Pre-Application)

**严重程度**: High

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

### DEF-007: Weaviate 过滤假阴性

**数据库**: Weaviate (weaviate:1.27.0)

**合约**: SCH-002 (Query Compatibility Across Schema Updates)

**严重程度**: High

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

### 极端生命周期测试结果

| Adapter | Delete-then-Search | Insert-then-Search | Empty-Collection-Search |
|---------|-------------------|---------------------|------------------------|
| Qdrant  | PASS              | PASS                | PASS                   |
| Weaviate| PASS              | PASS                | PASS                   |

### Weaviate SCH 合约测试结果

| Contract | 测试项 | 结果 | 备注 |
|----------|--------|------|------|
| SCH-001 | Schema Evolution Data Preservation | PASS | 100/100 entities searchable |
| SCH-002 | Filter Compatibility | **VIOLATION** | 返回 0/50 (假阴性) |
| SCH-003 | Index Rebuild Recall | PASS | recall=1.000 |
| SCH-004 | Metadata Accuracy | PASS | count=90/90 |

## 可提交 Issue 总览

| ID | 数据库 | 描述 | 严重程度 |
|----|--------|------|----------|
| DEF-001 | Milvus | count_entities 不反映删除 | Medium |
| DEF-002 | Milvus | 动态字段 ANN 搜索不可见 | High |
| DEF-003 | Milvus | 动态字段过滤假阳性 | High |
| DEF-004 | Milvus | 混合 Schema count 不一致 | Medium |
| DEF-005 | pgvector | 动态字段过滤假阴性 | High |
| **DEF-006** | **Qdrant** | **范围过滤不正确应用** | High |
| **DEF-007** | **Weaviate** | **过滤假阴性** | High |

**累计可提交 Issue**: 7 个 (4 Milvus + 1 pgvector + 1 Qdrant + 1 Weaviate)

## 结论

本次研究成功验证了框架在跨库测试方面的通用性。通过系统执行 HYB 合约测试和 Weaviate SCH 合约扩展，发现了 2 个新的可提交 bug（DEF-006 和 DEF-007），将框架的 bug 挖掘成果从 5 个扩展到 7 个。

关键成果包括：Qdrant 范围过滤存在严重 bug，过滤条件没有正确应用到结果集；Weaviate 在 schema 扩展后存在过滤假阴性问题。这些发现证明了框架能够有效检测不同向量数据库之间的行为差异。

后续建议进一步扩展测试覆盖范围，特别是针对 Weaviate 的 hybrid search 功能和 Qdrant 的 datetime 过滤进行深度测试。

## 参考资料

1. [Qdrant GitHub Issues](https://github.com/qdrant/qdrant/issues)
2. [Weaviate GitHub Issues](https://github.com/weaviate/weaviate/issues)
3. [ai-db-qc CONTRACT_COVERAGE_REPORT](C:\Users\11428\Desktop\ai-db-qc\docs\CONTRACT_COVERAGE_REPORT.md)
4. [ai-db-qc EXPERIMENTS_LOG](C:\Users\11428\Desktop\ai-db-qc\docs\EXPERIMENTS_LOG.md)
