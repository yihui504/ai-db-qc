# Aggressive Bug Mining - 实现总结

## 创建完成

已成功创建所有请求的测试合约、脚本、Fuzzing工具和Campaign配置。

## 文件清单

### 1. Schema演化合约 (SCH-005, SCH-006) ✅

| 文件 | 路径 | 描述 |
|------|------|------|
| SCH-005 | `contracts/schema/sch-005-schema-extension-compatibility.json` | Schema扩展向后兼容性 |
| SCH-006 | `contracts/schema/sch-006-schema-atomicity.json` | Schema操作原子性 |

### 2. Boundary条件合约 (BND-001~004) ✅

| 文件 | 路径 | 描述 |
|------|------|------|
| BND-001 | `contracts/schema/bnd-001-dimension-boundaries.json` | 向量维度边界验证 |
| BND-002 | `contracts/schema/bnd-002-topk-boundaries.json` | Top-K参数边界验证 |
| BND-003 | `contracts/schema/bnd-003-metric-type-validation.json` | Metric类型验证 |
| BND-004 | `contracts/schema/bnd-004-collection-name-boundaries.json` | Collection名称边界验证 |

### 3. Stress压力测试合约 (STR-001~002) ✅

| 文件 | 路径 | 描述 |
|------|------|------|
| STR-001 | `contracts/schema/str-001-throughput-stress.json` | 高吞吐量压力测试 |
| STR-002 | `contracts/schema/str-002-volume-stress.json` | 大规模数据集压力测试 |

### 4. 测试脚本 (3个) ✅

| 脚本 | 路径 | 测试合约 | 用法 |
|------|------|----------|------|
| Schema演化 | `scripts/run_schema_evolution.py` | SCH-005, SCH-006 | `python scripts/run_schema_evolution.py --db milvus` |
| Boundary测试 | `scripts/run_boundary_tests.py` | BND-001~BND-004 | `python scripts/run_boundary_tests.py --db qdrant` |
| Stress测试 | `scripts/run_stress_tests.py` | STR-001, STR-002 | `python scripts/run_stress_tests.py --db milvus --contract STR-001` |

### 5. Fuzzing工具 (2个) ✅

| 工具 | 路径 | 功能 | 工厂函数 |
|------|------|------|----------|
| Targeted Fuzzer | `casegen/fuzzing/targeted_fuzzer.py` | 针对特定合约和参数的模糊测试 | `create_boundary_fuzzer()`, `create_schema_fuzzer()`, `create_stress_fuzzer()` |
| Schema Fuzzer | `casegen/fuzzing/schema_fuzzer.py` | 专门针对Schema演化的模糊测试 | `create_schema_evolution_fuzzer()`, `create_backward_compatibility_fuzzer()`, `create_atomicity_fuzzer()` |

### 6. Campaign配置 (1个) ✅

| 文件 | 路径 | 描述 |
|------|------|------|
| Aggressive Bug Mining | `campaigns/aggressive_bug_mining.yaml` | 综合Bug挖掘活动配置 |

### 7. Campaign运行脚本 (1个) ✅

| 脚本 | 路径 | 用法 |
|------|------|------|
| Campaign Runner | `scripts/run_aggressive_bug_mining.py` | `python scripts/run_aggressive_bug_mining.py --db all` |

### 8. 文档 (2个) ✅

| 文档 | 路径 | 描述 |
|------|------|------|
| README | `AGGRESSIVE_BUG_MINING_README.md` | 详细使用指南 |
| Summary | `IMPLEMENTATION_SUMMARY.md` | 本文件，实现总结 |

## 功能特性

### Schema演化测试 (SCH-005, SCH-006)

**SCH-005 - Backward Compatibility:**
- Schema扩展后现有查询仍可正常工作
- 结果格式保持一致
- 无破坏性变更

**SCH-006 - Atomicity:**
- Schema操作是原子的（全有或全无）
- 失败操作后schema和数据完整回滚
- 并发schema操作的正确处理

### Boundary条件测试 (BND-001~BND-004)

**BND-001 - Dimension Boundaries:**
- 最小维度(1)、零值、负值
- 最大维度、过大维度
- 向量维度不匹配检测

**BND-002 - Top-K Boundaries:**
- Top-K = 0, 1, -1, 超大值
- 结果数≤Top-K验证
- 大于集合大小的Top-K处理

**BND-003 - Metric Type Validation:**
- 标准类型(L2, IP, COSINE)
- 大小写一致性
- 无效类型拒绝

**BND-004 - Collection Name Boundaries:**
- 空名、特殊字符
- 保留名检测
- 重复名拒绝
- 命名一致性

### Stress压力测试 (STR-001, STR-002)

**STR-001 - High Throughput:**
- 多级吞吐量测试（100, 1000, 5000, 10000 RPS）
- 操作混合（insert, search, bulk_insert）
- 延迟和成功率监控

**STR-002 - Large Dataset:**
- 多规模测试（10K, 100K, 1M, 10M vectors）
- Insert/Search性能测量
- 索引构建和加载时间
- 内存使用监控

### Fuzzing工具特性

**Targeted Fuzzer:**
- 针对特定合约的模糊测试
- 支持多种变异类型（boundary, type, format, sequence, concurrent）
- 参数特异性测试（dimension, top_k, metric_type, collection_name）
- 特定场景测试（序列操作、并发操作）

**Schema Fuzzer:**
- 专门针对schema演化
- 字段添加/删除/修改测试
- 并发schema操作测试
- 状态转换测试（空集合、有数据、有索引）
- 无效schema操作测试

### Aggressive Bug Mining Campaign

**Phase 1 - Schema Evolution Testing:**
- SCH-005, SCH-006合约测试
- Schema Fuzzer集成
- 向后兼容性和原子性验证

**Phase 2 - Boundary Condition Testing:**
- BND-001~BND-004合约测试
- Targeted Fuzzer集成
- 参数边界和验证测试

**Phase 3 - Stress Testing:**
- STR-001, STR-002合约测试
- Stress Fuzzer集成
- 吞吐量和可扩展性测试

**Phase 4 - Targeted Fuzzing:**
- Schema、Boundary、Stress focused fuzzing
- 多种变异策略
- 覆盖率驱动

**Phase 5 - Integration Testing:**
- Schema change under stress
- Boundary conditions at scale
- Cross-contract scenarios

## 使用示例

### 单独运行测试

```bash
# Schema演化测试
python scripts/run_schema_evolution.py --db milvus

# Boundary测试
python scripts/run_boundary_tests.py --db qdrant

# Stress测试（仅STR-001）
python scripts/run_stress_tests.py --db milvus --contract STR-001
```

### 运行完整Campaign

```bash
# 单个数据库
python scripts/run_aggressive_bug_mining.py --db milvus

# 所有数据库
python scripts/run_aggressive_bug_mining.py --db all

# 自定义配置
python scripts/run_aggressive_bug_mining.py --config campaigns/aggressive_bug_mining.yaml
```

### 使用Fuzzing工具

```python
from casegen.fuzzing.targeted_fuzzer import create_boundary_fuzzer
from casegen.fuzzing.schema_fuzzer import create_schema_evolution_fuzzer

# Boundary Fuzzer
fuzzer = create_boundary_fuzzer("BND-001", ["dimension"])
base_case = {
    "operation": "create_collection",
    "params": {"collection_name": "test", "dimension": 128, "metric_type": "L2"}
}
results = fuzzer.fuzz(base_case)

# Schema Fuzzer
schema_fuzzer = create_schema_evolution_fuzzer()
results = schema_fuzzer.fuzz(base_case)
```

## 预期输出

### 测试结果文件

```
results/
├── schema_evolution_2025_001/
│   ├── milvus_schema_evolution_results.json
│   ├── qdrant_schema_evolution_results.json
│   └── weaviate_schema_evolution_results.json
├── boundary_2025_001/
│   ├── milvus_boundary_results.json
│   ├── qdrant_boundary_results.json
│   └── pgvector_boundary_results.json
├── stress_2025_001/
│   ├── milvus_stress_results.json
│   ├── qdrant_stress_results.json
│   └── weaviate_stress_results.json
└── aggressive_bug_mining_2025_001/
    ├── campaign_results.json
    └── campaign.log
```

### 结果格式

每个结果文件包含：
- 测试用例详情
- 每个测试的verdict (PASS/BUG/TYPE-1/TYPE-2/etc.)
- 诊断信息
- 性能指标（stress测试）
- Bug分类

## 缺陷分类

使用四类型缺陷分类法：

| 类型 | 条件 | 严重性 | 示例 |
|------|------|--------|------|
| **Type-1** | `validity=illegal ∧ success=true` | HIGH | 无效dimension被接受 |
| **Type-2** | `validity=illegal ∧ success=false ∧ poor_diagnostic` | MEDIUM | 错误信息不指明具体参数 |
| **Type-2.PF** | `validity=legal ∧ precondition=false ∧ poor_diagnostic` | MEDIUM | 前置条件不满足但错误信息模糊 |
| **Type-3** | `validity=legal ∧ precondition=true ∧ success=false` | HIGH | 合法操作失败/崩溃 |
| **Type-4** | `validity=legal ∧ precondition=true ∧ oracle=false` | MEDIUM | 语义不变量违反 |

## 成功标准

根据campaign配置，成功标准包括：

- ✅ 至少验证8个合约（全部）
- ✅ 最小合约覆盖率: 80%
- ✅ 至少发现5个新bug
- ✅ 至少3个fuzzing触发的bug
- ✅ 至少2个有效的fuzzing策略
- ✅ 完整的CC分类
- ✅ 最小诊断质量: 70%

## 技术栈

- **Python 3.8+**
- **NumPy** - 向量生成和操作
- **PyYAML** - 配置文件解析
- **标准库** - subprocess, threading, json, etc.

## 数据库支持

所有测试脚本支持以下数据库：

- ✅ Milvus
- ✅ Qdrant
- ✅ Weaviate
- ✅ Pgvector

## 资源需求

### Schema & Boundary测试
- CPU: 1-2核
- 内存: 1-2GB
- 磁盘: <100MB
- 时间: 每个数据库 ~5-10分钟

### Stress测试
- CPU: 2-4核（吞吐量测试）
- 内存: 4-8GB（大规模测试）
- 磁盘: 10-50GB（取决于测试规模）
- 时间: 每个数据库 ~30-60分钟

### 完整Campaign
- CPU: 4核以上（推荐8核）
- 内存: 16GB以上
- 磁盘: 100GB以上
- 时间: 所有数据库 ~2-4小时

## 下一步行动

1. **运行Campaign**
   ```bash
   python scripts/run_aggressive_bug_mining.py --db all
   ```

2. **分析结果**
   - 查看 `results/aggressive_bug_mining_2025_001/campaign_results.json`
   - 检查发现的bug数量和类型

3. **Bug报告**
   - 为每个发现的bug创建GitHub issue
   - 包含测试用例、错误信息、复现步骤

4. **优化**
   - 根据发现的bug模式改进fuzzing策略
   - 添加新的测试合约
   - 扩展到更多数据库

5. **回归测试**
   - 将新测试集成到CI/CD
   - 定期运行防止regression

## 文件统计

- **合约文件**: 8个 (SCH-005, SCH-006, BND-001~BND-004, STR-001~STR-002)
- **测试脚本**: 3个 (Schema, Boundary, Stress)
- **Fuzzing工具**: 2个 (Targeted, Schema)
- **Campaign配置**: 1个 (Aggressive Bug Mining)
- **Campaign脚本**: 1个 (Runner)
- **文档文件**: 2个 (README, Summary)

**总计**: 17个新文件

---

**创建日期**: 2025-03-17
**版本**: 1.0
**状态**: ✅ 完成
