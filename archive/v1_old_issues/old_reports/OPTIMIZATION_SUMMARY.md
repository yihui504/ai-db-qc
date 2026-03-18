# ai-db-qc 优化实施总结

基于 SBMF 和 CC 项目调研结果，已完成三大优化方向的实施。

## 1. 并发测试框架 (CONC Contract Family)

### 已完成内容

**合约定义** (`contracts/conc/`)
- **CONC-001**: 并发插入后 count 一致性
  - 验证 N 个并发插入操作后，count_entities 必须等于总插入数量
  - 支持多线程/多进程并发模式
  - 集成性能监控（ops/s、延迟分布 P50/P95/P99）
  
- **CONC-002**: 并发搜索隔离性
  - 验证并发搜索操作不返回幽灵数据或损坏结果
  - 支持读写交错场景测试
  - 检查搜索结果基数约束
  
- **CONC-003**: 删除-搜索交叉一致性
  - 验证删除和搜索操作并发执行时保持交叉一致性
  - 检查删除后实体不可搜索
  - 验证计数单调递减

**测试脚本** (`scripts/run_concurrent_test.py`)
- 通用并发测试框架，支持所有 CONC 合约
- 多数据库适配器统一接口（Milvus、Qdrant、Weaviate、pgvector）
- 配置化并发参数（线程数、操作比例、持续时间）
- 性能指标收集（吞吐量、延迟 P50/P95/P99）
- 一致性校验 oracle

**Pipeline 集成** (`pipeline/conc_integration.py`)
- `ConcurrentTestRunner` 类集成到现有 pipeline
- 支持通过 Executor 和 Triage 执行并发测试
- `run_conc_suite()` 函数支持批量运行 CONC 合约测试

### 使用方法

```bash
# 运行单个 CONC 合约测试
python scripts/run_concurrent_test.py --contract CONC-001 --target milvus

# 运行所有 CONC 合约测试
python scripts/run_concurrent_test.py --all --target qdrant --threads 8

# 使用 Pipeline 集成
from pipeline.conc_integration import run_conc_suite
results = run_conc_suite(adapter, executor, triage)
```

## 2. Bug 分类对齐 (CC Classification Mapping)

### 已完成内容

**映射文档** (`docs/DEF_CC_MAPPING.md`)

| DEF ID | 数据库 | 合约 | 严重程度 | CC 分类 | 核心问题 |
|--------|--------|------|----------|---------|----------|
| DEF-001 | Milvus | R3B | High | **Type-4** | count 未反映删除 |
| DEF-002 | Milvus | SCH-001 | High | **Type-4** | 动态字段不可见 |
| DEF-003 | Milvus | SCH-002 | High | **Type-4** | 过滤假阳性 |
| DEF-004 | Milvus | SCH-004 | Medium | **Type-4** | 混合 schema count 错误 |
| DEF-005 | pgvector | SCH-002 | High | **Type-4** | 过滤假阴性 |
| DEF-006 | Qdrant | HYB-001 | High | **Type-4** | 范围过滤失效 |
| DEF-007 | Weaviate | SCH-002 | High | **Type-4** | 过滤假阴性 |

**CC 四类 Bug 定义**
- **Type-1**: 非法操作成功（非法输入但操作成功）
- **Type-2**: 错误不可诊断（报错但无具体原因）
- **Type-3**: 合法操作失败（合法输入但操作失败）
- **Type-4**: 语义违背（操作成功但结果不符合预期）

**映射结论**
- 所有 7 个 DEF 全部映射为 **Type-4（语义违背）**
- 原因：所有 DEF 都满足以下条件：
  1. 合法输入
  2. 前置条件满足
  3. 操作成功执行
  4. 结果不符合预期语义

## 3. Fuzzing 增强 (6种变异策略)

### 已完成内容

**变异策略实现** (`casegen/fuzzing/`)

1. **RandomFuzzer** (`random_fuzzer.py`)
   - 完全随机参数替换
   - 支持 int、float、str、list 类型感知变异
   - 包含边界值、注入尝试、空值等特殊值

2. **BoundaryFuzzer** (`boundary_fuzzer.py`)
   - 边界值测试（min-1, min, max, max+1）
   - 支持数值和字符串边界
   - 可配置约束条件

3. **ArithmeticFuzzer** (`arithmetic_fuzzer.py`)
   - 算术变异（±1, ×2, ÷2）
   - 支持 int 和 float
   - 记录具体操作类型

4. **DictionaryFuzzer** (`dictionary_fuzzer.py`)
   - 基于历史有效值的字典替换
   - 自动学习有效值
   - 支持外部字典加载

5. **SplicingFuzzer** (`splicing_fuzzer.py`)
   - 测试用例片段拼接
   - 从多个用例中组合参数
   - 支持片段池管理

6. **CrossoverFuzzer** (`crossover_fuzzer.py`)
   - 多测试用例交叉组合
   - 单点交叉和均匀交叉
   - 父代选择机制

**策略选择引擎** (`strategy_selector.py`)
- 支持 4 种选择模式：
  - **RANDOM**: 随机选择
  - **ROUND_ROBIN**: 轮询
  - **FEEDBACK_DRIVEN**: 反馈驱动
  - **ADAPTIVE**: 自适应（基于成功率）
- 策略注册表机制
- 成功率跟踪和评分
- 与 FeedbackCollector 集成

**Pipeline 集成** (`pipeline/fuzzing_integration.py`)
- `FuzzingCampaignRunner` 类集成到现有 pipeline
- `run_fuzzing_suite()` 函数支持批量 fuzzing 活动
- `FuzzingStrategyFactory` 工厂类创建策略

**单元测试** (`tests/test_fuzzing_strategies.py`)
- 覆盖所有 6 种策略的单元测试
- StrategySelector 测试
- FeedbackCollector 测试
- 集成测试

### 使用方法

```python
# 使用单个策略
from casegen.fuzzing.random_fuzzer import RandomFuzzer
fuzzer = RandomFuzzer(seed=42)
results = fuzzer.fuzz(base_case)

# 使用策略选择器
from casegen.fuzzing.strategy_selector import create_selector
selector = create_selector(mode="feedback_driven", seed=42)
results = selector.execute_fuzzing(base_case, num_iterations=10)

# 使用 Pipeline 集成
from pipeline.fuzzing_integration import run_fuzzing_suite
result = run_fuzzing_suite(adapter, executor, triage, base_cases)
```

## 文件清单

### 新增文件
```
ai-db-qc/
├── contracts/conc/
│   ├── conc-001-insert-count-consistency.json
│   ├── conc-002-concurrent-search-isolation.json
│   └── conc-003-delete-search-consistency.json
├── casegen/fuzzing/
│   ├── random_fuzzer.py
│   ├── boundary_fuzzer.py
│   ├── arithmetic_fuzzer.py
│   ├── dictionary_fuzzer.py
│   ├── splicing_fuzzer.py
│   ├── crossover_fuzzer.py
│   └── strategy_selector.py
├── scripts/
│   └── run_concurrent_test.py
├── pipeline/
│   ├── conc_integration.py
│   └── fuzzing_integration.py
├── tests/
│   └── test_fuzzing_strategies.py
└── docs/
    └── DEF_CC_MAPPING.md
```

## 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                     并发测试框架 (CONC)                       │
├─────────────────────────────────────────────────────────────┤
│  CONC-001 ──→ ConcurrentTestRunner ──→ Adapter ──→ Database │
│  CONC-002 ──→ run_concurrent_test.py ──→ Metrics/Oracle     │
│  CONC-003 ──→ conc_integration.py ──→ Pipeline              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                     Fuzzing 增强                             │
├─────────────────────────────────────────────────────────────┤
│  RandomFuzzer                                               │
│  BoundaryFuzzer                                             │
│  ArithmeticFuzzer ──→ StrategySelector ──→ Pipeline         │
│  DictionaryFuzzer                                           │
│  SplicingFuzzer                                             │
│  CrossoverFuzzer                                            │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                     Bug 分类对齐                             │
├─────────────────────────────────────────────────────────────┤
│  DEF-001 ~ DEF-007 ──→ Type-4 (Semantic Violation)          │
│  文档: docs/DEF_CC_MAPPING.md                               │
└─────────────────────────────────────────────────────────────┘
```

## 后续建议

1. **执行验证**: 运行 `scripts/run_concurrent_test.py` 和单元测试验证实现正确性
2. **性能调优**: 根据实际数据库性能调整并发参数
3. **扩展合约**: 基于 CONC 模式添加更多并发测试场景
4. **策略优化**: 根据 fuzzing 结果优化策略选择算法
