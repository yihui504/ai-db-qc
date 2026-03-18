# 历史 Bug 分析报告

**生成日期**: 2026-03-17  
**来源**: GitHub Issue 检索 + 微信公众号技术文章

---

## 一、Qdrant 已知问题

### Issue #7462: DATETIME Payload Index 接受无效时间戳且行为不一致

**严重程度**: Medium-High  
**发布日期**: 2025-10-28

**问题描述**: 当 Payload 字段索引为 DATETIME 类型时，Qdrant 在数据插入时不校验 RFC3339 标准，导致无效时间戳被静默接受。

**无效时间戳示例**:
- `"2025-01-01 00:00:00+00:00"` (空格分隔符)
- `"2025-01-01T00:00:00+0000"` (时区缺少冒号)
- `"2025-01-01T00:00:00+14:60"` (分钟超出范围)
- `"2025-13-01T00:00:00Z"` (无效月份)
- `"2025-01-32T00:00:00Z"` (无效日期)

**影响**: 范围查询时部分无效时间戳被匹配，部分被忽略，结果不一致。

**测试场景建议**:
1. 插入无效 DATETIME 字符串，验证是否被拒绝或标准化
2. 执行范围查询，验证无效时间戳的处理一致性

---

## 二、Weaviate 已知问题

### Issue #8921: DateTime 过滤返回错误结果 (2500年后)

**严重程度**: High  
**发布日期**: 2025-08-14  
**状态**: 已确认，有修复 PR

**问题描述**: 使用 `greater_than(datetime(2500, 1, 1))` 过滤时，返回的是 2024-2025 年的事件，而非 3000+ 年的事件。

**复现步骤**:
1. 创建包含 datetime 属性的集合
2. 插入 2024, 2025, 3000, 3026 年的事件
3. 执行 `filter: event_date > 2500-01-01`
4. 期望: 返回 3000, 3026 年事件
5. 实际: 返回 2024, 2025 年事件

**测试场景建议**:
1. 极端日期值过滤 (year > 2500)
2. 负数年份过滤
3. 闰年/夏令时边界条件

### Issue #7681: Hybrid Search Filters 无效 (Pre-filter)

**严重程度**: High  
**发布日期**: 2025-03-29  
**状态**: 已关闭

**问题描述**: Hybrid 搜索 (BM25 + vector) 中的过滤器没有作为严格预过滤器工作，不符合过滤条件的文档仍然出现在结果中。

**复现步骤**:
1. 创建包含 content 和 source 属性的集合
2. 插入 source="A" 和 source="B" 的文档
3. 执行 hybrid 搜索 with filter `source == "source-A"`
4. 期望: 只返回 source="A" 的文档
5. 实际: 返回了 source="B" 的文档

**影响**: 多租户应用和数据隔离场景的可靠性受损。

**测试场景建议**:
1. Hybrid search + filter 严格性验证
2. Filter 在 fusion 前/后的行为验证

---

## 三、Milvus 已知问题 (已发现)

### DEF-001: count_entities 不反映删除

详见 `docs/bug_issue_submission_plan.md`

### DEF-002/003/004: 动态字段问题

详见 `docs/bug_issue_submission_plan.md`

---

## 四、测试场景映射

| 数据库 | Bug 类型 | 对应 HYB/SCH 合约 | 优先级 |
|--------|----------|------------------|--------|
| Qdrant | DATETIME 验证 | HYB-001 (Filter Pre-app) | High |
| Qdrant | Payload 索引不一致 | HYB-002 (Filter Result) | High |
| Weaviate | DateTime >2500 过滤错误 | HYB-001 | High |
| Weaviate | Hybrid filter 泄漏 | HYB-001 | High |
| Weaviate | Multi-tenancy 隔离 | SCH-001 | Medium |
| pgvector | 动态列过滤 | SCH-002 | 已发现 (DEF-005) |

---

## 五、建议的下一步测试设计

### Qdrant Payload Filter 测试序列

1. **DATETIME 边界测试**
   - 插入无效 RFC3339 时间戳
   - 验证写入拒绝或标准化行为
   - 验证范围查询结果一致性

2. **Range Filter 测试**
   - 数值范围 (min <= x <= max)
   - 日期范围
   - 组合条件 (AND/OR)

3. **Nested JSON Filter 测试**
   - 嵌套对象属性过滤
   - 数组成员过滤

### Weaviate Hybrid Filter 测试序列

1. **Pre-filter 严格性测试**
   - Hybrid + filter 组合
   - 验证 filter 在 fusion 前应用
   - 对比 post-filter 结果差异

2. **极端日期过滤测试**
   - Year > 2500
   - Year < 1900
   - 时区边界

---

## 参考链接

- [Qdrant #7462: DATETIME payload index](https://github.com/qdrant/qdrant/issues/7462)
- [Weaviate #8921: DateTime filtering](https://github.com/weaviate/weaviate/issues/8921)
- [Weaviate #7681: Hybrid search filters](https://github.com/weaviate/weaviate/issues/7681)
