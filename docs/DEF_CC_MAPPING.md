# DEF Bug 到 CC 分类体系映射文档

**生成日期**: 2026-03-17  
**框架**: ai-db-qc (Contract-Based Runtime Defect Detection)  
**参考**: CC (AI数据库Bug挖掘框架) v1.1 Bug分类体系

---

## CC 四类 Bug 分类体系速查

| 类型 | 名称 | 判定条件 | 严重性 |
|------|------|----------|--------|
| **Type-1** | 非法操作成功 | `is_legal_input=False` 且 `status=SUCCESS` | HIGH |
| **Type-2** | 错误不可诊断 | `is_legal_input=False` 且 `status=FAILURE` 且 `!has_root_cause_slots` | MEDIUM |
| **Type-3** | 合法操作失败 | `is_legal_input=True` 且 `precondition_pass=True` 且 `status=FAILURE` | HIGH |
| **Type-4** | 语义违背 | `is_legal_input=True` 且 `precondition_pass=True` 且 `oracle_passed=False` | MEDIUM |

---

## ai-db-qc 7个DEF映射详情

### DEF-001: count_entities 不反映删除操作直到压缩

| 属性 | 值 |
|------|-----|
| **数据库** | Milvus v2.6.10 |
| **合约** | R3B |
| **严重程度** | High |
| **CC分类** | **Type-4 (语义违背)** |

**映射理由**:
- ✅ 输入合法: `delete()` 和 `count_entities()` 调用参数符合规范
- ✅ 前置条件满足: collection存在、数据已插入、flush已执行
- ✅ 操作成功: `delete()` 返回成功，`count_entities()` 返回成功
- ❌ Oracle未通过: `count_entities` 返回值未反映删除操作（期望900，实际1000）

**判定Checklist**:
- [x] 输入参数符合官方文档规范
- [x] 前置条件（collection存在、flush完成）已满足
- [x] 操作返回成功状态
- [x] 结果不符合语义预期（count未反映删除）

---

### DEF-002: 动态字段插入后 ANN 搜索不可见

| 属性 | 值 |
|------|-----|
| **数据库** | Milvus v2.6.10 |
| **合约** | SCH-001 |
| **严重程度** | High |
| **CC分类** | **Type-4 (语义违背)** |

**映射理由**:
- ✅ 输入合法: `insert()` 参数符合动态字段schema规范
- ✅ 前置条件满足: collection存在、enable_dynamic_field=True、index已构建
- ✅ 操作成功: `insert()` 返回成功，`search()` 返回成功
- ❌ Oracle未通过: ANN search未返回动态字段扩展后的entities（期望500，实际200）

**判定Checklist**:
- [x] 输入参数符合官方文档规范
- [x] 前置条件（动态字段启用、index构建）已满足
- [x] 操作返回成功状态
- [x] 结果不符合语义预期（动态字段entities不可见）

---

### DEF-003: 动态字段过滤返回假阳性

| 属性 | 值 |
|------|-----|
| **数据库** | Milvus v2.6.10 |
| **合约** | SCH-002 |
| **严重程度** | High |
| **CC分类** | **Type-4 (语义违背)** |

**映射理由**:
- ✅ 输入合法: `filtered_search()` 参数符合过滤表达式语法
- ✅ 前置条件满足: collection存在、动态字段已扩展、数据已插入
- ✅ 操作成功: `filtered_search()` 返回成功
- ❌ Oracle未通过: 返回了无tag的entities作为假阳性（假阳性率50%）

**判定Checklist**:
- [x] 输入参数符合官方文档规范
- [x] 前置条件（schema扩展、数据存在）已满足
- [x] 操作返回成功状态
- [x] 结果不符合语义预期（过滤条件未正确应用）

---

### DEF-004: 混合 Schema 集合中 count-delete 不一致

| 属性 | 值 |
|------|-----|
| **数据库** | Milvus v2.6.10 |
| **合约** | SCH-004 |
| **严重程度** | Medium |
| **CC分类** | **Type-4 (语义违背)** |

**映射理由**:
- ✅ 输入合法: `delete()` 和 `count_entities()` 参数符合规范
- ✅ 前置条件满足: collection存在、混合schema数据已插入
- ✅ 操作成功: `delete()` 返回成功，`count_entities()` 返回成功
- ❌ Oracle未通过: count未反映删除后的正确数量（期望450，实际500）

**判定Checklist**:
- [x] 输入参数符合官方文档规范
- [x] 前置条件（混合schema、数据存在）已满足
- [x] 操作返回成功状态
- [x] 结果不符合语义预期（count未正确计算）

---

### DEF-005: pgvector 动态字段过滤假阴性

| 属性 | 值 |
|------|-----|
| **数据库** | pgvector (pg16) |
| **合约** | SCH-002 |
| **严重程度** | High |
| **CC分类** | **Type-4 (语义违背)** |

**映射理由**:
- ✅ 输入合法: `ALTER TABLE` 和 `filtered_search` 参数符合SQL规范
- ✅ 前置条件满足: 表存在、新列已添加、数据已插入
- ✅ 操作成功: `ALTER TABLE` 成功，`filtered_search` 返回成功
- ❌ Oracle未通过: 过滤搜索返回0结果，期望返回100个tagged entities（假阴性率100%）

**判定Checklist**:
- [x] 输入参数符合官方文档规范
- [x] 前置条件（表结构、列存在）已满足
- [x] 操作返回成功状态
- [x] 结果不符合语义预期（过滤未匹配到有效数据）

---

### DEF-006: Qdrant 范围过滤不正确应用

| 属性 | 值 |
|------|-----|
| **数据库** | Qdrant (latest) |
| **合约** | HYB-001 |
| **严重程度** | High |
| **CC分类** | **Type-4 (语义违背)** |

**映射理由**:
- ✅ 输入合法: `filtered_search` 参数符合Qdrant过滤语法
- ✅ 前置条件满足: collection存在、payload数据已插入
- ✅ 操作成功: `filtered_search` 返回成功
- ❌ Oracle未通过: Range filter (gt/lt/gte/lte) 未正确应用，返回了不符合条件的结果

**判定Checklist**:
- [x] 输入参数符合官方文档规范
- [x] 前置条件（collection、payload数据）已满足
- [x] 操作返回成功状态
- [x] 结果不符合语义预期（范围条件未正确过滤）

---

### DEF-007: Weaviate 过滤假阴性

| 属性 | 值 |
|------|-----|
| **数据库** | Weaviate (1.27.0) |
| **合约** | SCH-002 |
| **严重程度** | High |
| **CC分类** | **Type-4 (语义违背)** |

**映射理由**:
- ✅ 输入合法: `filtered_search` 参数符合Weaviate GraphQL语法
- ✅ 前置条件满足: collection存在、schema已扩展、数据已插入
- ✅ 操作成功: `filtered_search` 返回成功
- ❌ Oracle未通过: 新添加属性的过滤返回空结果，期望返回50个entities

**判定Checklist**:
- [x] 输入参数符合官方文档规范
- [x] 前置条件（schema扩展、数据存在）已满足
- [x] 操作返回成功状态
- [x] 结果不符合语义预期（新属性过滤失效）

---

## 映射汇总表

| DEF ID | 数据库 | 合约 | 严重程度 | CC分类 | 核心问题 |
|--------|--------|------|----------|--------|----------|
| DEF-001 | Milvus | R3B | High | **Type-4** | count未反映删除 |
| DEF-002 | Milvus | SCH-001 | High | **Type-4** | 动态字段不可见 |
| DEF-003 | Milvus | SCH-002 | High | **Type-4** | 过滤假阳性 |
| DEF-004 | Milvus | SCH-004 | Medium | **Type-4** | 混合schema count错误 |
| DEF-005 | pgvector | SCH-002 | High | **Type-4** | 过滤假阴性 |
| DEF-006 | Qdrant | HYB-001 | High | **Type-4** | 范围过滤失效 |
| DEF-007 | Weaviate | SCH-002 | High | **Type-4** | 过滤假阴性 |

---

## 关键观察

### 1. 全为Type-4
所有7个DEF均映射为 **Type-4 (语义违背)**，这是因为：
- 所有测试用例的输入都符合官方文档规范
- 所有前置条件都已满足
- 所有操作都返回成功状态
- 但结果不符合预期的语义约定

### 2. 无Type-1/2/3
当前发现的Bug中**未发现**以下类型：
- **Type-1**: 未发现"非法操作成功"的情况
- **Type-2**: 未发现"错误不可诊断"的情况（错误信息相对清晰）
- **Type-3**: 未发现"合法操作失败"的情况（操作都成功执行）

### 3. 扩展方向
为完善CC分类覆盖，后续测试应关注：
- **Type-1**: 边界值测试（如负维度、超大top_k）
- **Type-2**: 错误信息质量测试（故意提供非法参数观察错误提示）
- **Type-3**: 压力测试下的稳定性（高并发下合法操作是否可能失败）

---

## 红线约束检查

根据CC框架的红线约束，所有DEF映射均满足：

| 红线 | 内容 | 检查状态 |
|------|------|----------|
| **R1** | 禁止把DB特定参数写回contract | ✅ 通过 |
| **R2** | 禁止放松门禁或oracle标准 | ✅ 通过 |
| **R3** | 禁止报告口径不一致 | ✅ 通过 |
| **R4** | Type-4必须precondition_pass=true | ✅ 通过 |
| **R5** | 证据来源必须是官方文档 | ✅ 通过 |

---

## 参考文档

- [CC项目GitHub主页](https://github.com/yihui504/CC)
- [CC项目README.md](https://github.com/yihui504/CC/blob/main/README.md)
- [CC项目架构文档](https://github.com/yihui504/CC/blob/main/docs/architecture.md)
- [CC项目标准工作流程](https://github.com/yihui504/CC/blob/main/docs/STANDARD_WORKFLOW.md)
- [ai-db-qc Bug提交计划](./bug_issue_submission_plan.md)
