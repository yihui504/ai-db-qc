# Aggressive Bug Mining - 新增测试合约与工具

本文档描述了为 AI-DB-QC 项目创建的新测试合约、脚本和工具。

## 创建概览

### 1. Schema演化合约 (2个)

- **SCH-005**: Schema Extension Backward Compatibility
  - 位置: `contracts/schema/sch-005-schema-extension-compatibility.json`
  - 目标: 确保schema扩展不会破坏现有查询
  - 关键验证: 查询稳定性、结果一致性、无破坏性变更

- **SCH-006**: Schema Operation Atomicity
  - 位置: `contracts/schema/sch-006-schema-atomicity.json`
  - 目标: 确保schema操作是原子的（全有或全无）
  - 关键验证: 原子性、回滚完整性、无中间状态

### 2. Boundary条件合约 (4个)

- **BND-001**: Vector Dimension Boundaries
  - 位置: `contracts/schema/bnd-001-dimension-boundaries.json`
  - 目标: 验证向量维度边界值
  - 关键验证: 最小值(1)、零值、负值、最大值、向量维度不匹配

- **BND-002**: Top-K Parameter Boundaries
  - 位置: `contracts/schema/bnd-002-topk-boundaries.json`
  - 目标: 验证top_k参数边界
  - 关键验证: 零值、负值、超大值、结果数≤top_k

- **BND-003**: Metric Type Validation
  - 位置: `contracts/schema/bnd-003-metric-type-validation.json`
  - 目标: 验证metric_type参数
  - 关键验证: 有效类型(L2/IP/COSINE)、大小写一致性、无效类型拒绝

- **BND-004**: Collection Name Boundaries
  - 位置: `contracts/schema/bnd-004-collection-name-boundaries.json`
  - 目标: 验证collection_name命名约束
  - 关键验证: 空名、特殊字符、保留名、重复名、命名一致性

### 3. Stress压力测试合约 (2个)

- **STR-001**: High Throughput Stress Test
  - 位置: `contracts/schema/str-001-throughput-stress.json`
  - 目标: 测试高吞吐量下的数据库稳定性
  - 测试场景:
    - Low: 100 RPS for 60s
    - Medium: 1000 RPS for 60s
    - High: 5000 RPS for 60s
    - Extreme: 10000 RPS for 30s

- **STR-002**: Large Dataset Stress Test
  - 位置: `contracts/schema/str-002-volume-stress.json`
  - 目标: 测试大规模数据集的可扩展性
  - 测试规模:
    - Small: 10K vectors
    - Medium: 100K vectors
    - Large: 1M vectors
    - Extra Large: 10M vectors (可选)

### 4. 测试脚本 (3个)

- **Schema演化测试脚本**
  - 位置: `scripts/run_schema_evolution.py`
  - 测试合约: SCH-005, SCH-006
  - 使用方法:
    ```bash
    python scripts/run_schema_evolution.py --db milvus
    python scripts/run_schema_evolution.py --db qdrant
    python scripts/run_schema_evolution.py --db all
    ```

- **Boundary测试脚本**
  - 位置: `scripts/run_boundary_tests.py`
  - 测试合约: BND-001, BND-002, BND-003, BND-004
  - 使用方法:
    ```bash
    python scripts/run_boundary_tests.py --db milvus
    python scripts/run_boundary_tests.py --db qdrant
    python scripts/run_boundary_tests.py --db all
    ```

- **Stress测试脚本**
  - 位置: `scripts/run_stress_tests.py`
  - 测试合约: STR-001, STR-002
  - 使用方法:
    ```bash
    python scripts/run_stress_tests.py --db milvus --contract STR-001
    python scripts/run_stress_tests.py --db qdrant --contract STR-002
    python scripts/run_stress_tests.py --db all --contract all
    ```

### 5. Fuzzing工具 (2个)

- **Targeted Fuzzer**
  - 位置: `casegen/fuzzing/targeted_fuzzer.py`
  - 功能: 针对特定合约和参数的模糊测试
  - 变异类型:
    - boundary: 边界值测试
    - type: 类型变异
    - format: 格式变异
    - sequence: 序列操作
    - concurrent: 并发操作
  - 工厂函数:
    - `create_boundary_fuzzer()`: 专注于边界测试
    - `create_schema_fuzzer()`: 专注于schema演化
    - `create_stress_fuzzer()`: 专注于压力测试

- **Schema Fuzzer**
  - 位置: `casegen/fuzzing/schema_fuzzer.py`
  - 功能: 专门针对schema演化的模糊测试
  - 关注领域:
    - Atomicity: 原子性
    - Backward Compatibility: 向后兼容性
    - Data Preservation: 数据保留
    - Concurrent Operations: 并发操作
  - 变异类型:
    - field_addition: 添加字段
    - field_removal: 删除字段
    - field_modification: 修改字段
    - concurrent_operations: 并发操作
    - invalid_operations: 无效操作
    - state_transitions: 状态转换
  - 工厂函数:
    - `create_schema_evolution_fuzzer()`: 创建完整的schema演化fuzzer
    - `create_backward_compatibility_fuzzer()`: 专注于SCH-005
    - `create_atomicity_fuzzer()`: 专注于SCH-006

### 6. Aggressive Bug Mining Campaign

- **Campaign配置文件**
  - 位置: `campaigns/aggressive_bug_mining.yaml`
  - 描述: 综合的Bug挖掘活动配置
  - 包含阶段:
    1. Schema演化测试 (SCH-005, SCH-006)
    2. Boundary条件测试 (BND-001~BND-004)
    3. Stress压力测试 (STR-001, STR-002)
    4. Targeted Fuzzing (Schema, Boundary, Stress)
    5. Cross-Contract Integration Testing
  - 目标数据库: Milvus, Qdrant, Weaviate, Pgvector

- **Campaign运行脚本**
  - 位置: `scripts/run_aggressive_bug_mining.py`
  - 使用方法:
    ```bash
    python scripts/run_aggressive_bug_mining.py --db milvus
    python scripts/run_aggressive_bug_mining.py --db all
    python scripts/run_aggressive_bug_mining.py --config campaigns/aggressive_bug_mining.yaml
    ```

## 使用指南

### 快速开始

1. **测试单个数据库的Schema演化**
   ```bash
   python scripts/run_schema_evolution.py --db milvus
   ```

2. **测试单个数据库的Boundary条件**
   ```bash
   python scripts/run_boundary_tests.py --db qdrant
   ```

3. **测试单个数据库的Stress性能**
   ```bash
   python scripts/run_stress_tests.py --db milvus --contract STR-001
   ```

4. **运行完整的Aggressive Bug Mining Campaign**
   ```bash
   python scripts/run_aggressive_bug_mining.py --db all
   ```

### 使用Fuzzing工具

```python
from casegen.fuzzing.targeted_fuzzer import create_boundary_fuzzer
from casegen.fuzzing.schema_fuzzer import create_schema_evolution_fuzzer

# 创建boundary fuzzer
boundary_fuzzer = create_boundary_fuzzer("BND-001", ["dimension"])
base_case = {
    "operation": "create_collection",
    "params": {
        "collection_name": "test",
        "dimension": 128,
        "metric_type": "L2"
    }
}
results = boundary_fuzzer.fuzz(base_case)

# 创建schema fuzzer
schema_fuzzer = create_schema_evolution_fuzzer()
results = schema_fuzzer.fuzz(base_case)
```

## 预期输出

所有测试脚本会生成JSON格式的结果文件，保存在`results/`目录下：

- `results/schema_evolution_2025_001/` - Schema演化测试结果
- `results/boundary_2025_001/` - Boundary测试结果
- `results/stress_2025_001/` - Stress测试结果
- `results/aggressive_bug_mining_2025_001/` - Campaign汇总结果

每个结果文件包含：
- 测试用例详情
- 每个测试的verdict (PASS/BUG/TYPE-1/TYPE-2/etc.)
- 诊断信息
- 性能指标（针对stress测试）

## 缺陷分类

测试使用四类型缺陷分类法：

- **Type-1**: `validity=illegal ∧ success=true`
  - 无效参数被接受
  - 严重性: HIGH

- **Type-2**: `validity=illegal ∧ success=false ∧ poor_diagnostic`
  - 有效参数被拒绝或错误信息不明确
  - 严重性: MEDIUM

- **Type-2.PF**: `validity=legal ∧ precondition=false ∧ poor_diagnostic`
  - 前置条件不满足但错误信息模糊
  - 严重性: MEDIUM

- **Type-3**: `validity=legal ∧ precondition=true ∧ success=false`
  - 合法操作失败或崩溃
  - 严重性: HIGH

- **Type-4**: `validity=legal ∧ precondition=true ∧ oracle=false`
  - 语义不变量违反
  - 严重性: MEDIUM

## 成功标准

根据campaign配置，成功标准包括：

- 至少发现5个新bug
- 至少验证8个合约（全部）
- 最小合约覆盖率: 80%
- 至少3个fuzzing触发的bug
- 至少2个有效的fuzzing策略
- 完整的CC分类

## 注意事项

1. **Stress测试**: STR-002的大规模测试（1M+ vectors）可能需要较长时间和较多资源，可以根据需要调整配置

2. **并发测试**: 并发测试可能暴露竞态条件，建议在隔离环境中运行

3. **数据库支持**: 不同数据库对schema演化、并发操作等特性的支持程度不同，某些测试可能根据数据库特性进行调整

4. **资源消耗**: 高吞吐量测试和大规模测试会消耗较多系统资源，确保测试环境有足够的CPU、内存和磁盘空间

## 下一步

1. 运行campaign并收集结果
2. 分析发现的bug并进行分类
3. 为发现的bug创建GitHub issues
4. 根据bug模式改进测试策略
5. 扩展到更多数据库或添加新的测试合约

---

**创建日期**: 2025-03-17  
**版本**: 1.0
