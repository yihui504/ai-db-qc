# Bug挖掘执行计划与进度

## 已完成的准备工作

### 1. 优化实施完成 ✅
- **CONC合约族**: CONC-001/002/003 已创建
- **Fuzzing策略**: 6种策略已实现 (Random, Boundary, Arithmetic, Dictionary, Splicing, Crossover)
- **CC分类映射**: 7个DEF全部映射为Type-4
- **Pipeline集成**: conc_integration.py, fuzzing_integration.py 已创建

### 2. Bug挖掘Campaign配置 ✅
- 配置文件: `campaigns/bug_mining_conc_fuzz.yaml`
- 执行脚本: `scripts/run_bug_mining.py`

---

## 执行阶段

### Phase 1: 环境验证 ✅
**状态**: 已完成基础验证

**结果**:
- 并发测试脚本可用: `scripts/run_concurrent_test.py --help` ✓
- CONC合约文件已创建 ✓
- Fuzzing模块已安装 ✓

### Phase 2: 并发测试挖掘 ⏳
**目标**: 在真实数据库上执行CONC-001/002/003测试

**执行命令**:

```bash
# CONC-001: 并发插入计数一致性 (Milvus)
python scripts/run_concurrent_test.py \
  --contract CONC-001 \
  --target milvus \
  --threads 4 \
  --vectors-per-thread 100 \
  --output results/conc001_milvus_t4.json

# CONC-001: 更高并发压力测试
python scripts/run_concurrent_test.py \
  --contract CONC-001 \
  --target milvus \
  --threads 8 \
  --vectors-per-thread 100 \
  --output results/conc001_milvus_t8.json

# CONC-002: 并发搜索隔离性
python scripts/run_concurrent_test.py \
  --contract CONC-002 \
  --target milvus \
  --readers 4 \
  --deleters 2 \
  --duration 60 \
  --output results/conc002_milvus.json

# CONC-003: 删除-搜索交叉一致性
python scripts/run_concurrent_test.py \
  --contract CONC-003 \
  --target milvus \
  --searchers 4 \
  --deleters 2 \
  --duration 90 \
  --output results/conc003_milvus.json
```

**预期发现**:
- 计数不一致（count_entities != 实际插入数）
- 竞态条件导致的重复/丢失实体
- 删除后实体仍出现在搜索结果中（幽灵数据）

### Phase 3: Fuzzing策略挖掘 ⏳
**目标**: 使用6种Fuzzing策略进行深度测试

**执行方式**:
```python
# 使用pipeline fuzzing集成
from pipeline.fuzzing_integration import run_fuzzing_suite
from adapters.milvus_adapter import MilvusAdapter

adapter = MilvusAdapter()
adapter.connect({'host': 'localhost', 'port': 19530})

# 运行fuzzing campaign
result = run_fuzzing_suite(
    adapter=adapter,
    executor=executor,
    triage=triage,
    base_cases=load_base_cases(),
    strategies=['random', 'boundary', 'arithmetic', 'dictionary'],
    selection_mode='adaptive',
    max_iterations=500
)
```

**边界值专项测试**:
- top_k = 0, 1, max, max+1
- dimension边界（min-1, min, max, max+1）
- 空字符串、超长字符串
- 负数、极大值

### Phase 4: 回归测试 ⏳
**目标**: 验证新优化能否发现已有DEF类型Bug

**测试项**:
1. **DEF-001类型**（count未反映删除）
   - 使用CONC-001合约测试
   
2. **DEF-003类型**（过滤假阳性）
   - 使用BoundaryFuzzer生成边界过滤条件
   
3. **DEF-005类型**（过滤假阴性）
   - 使用DictionaryFuzzer进行历史值替换

---

## 执行检查清单

### 前置条件
- [ ] Milvus数据库运行中 (localhost:19530)
- [ ] Qdrant数据库运行中 (localhost:6333)
- [ ] 磁盘空间充足 (> 10GB)
- [ ] Python环境正常

### 执行步骤
- [ ] Phase 1: 环境验证
- [ ] Phase 2.1: CONC-001测试 (Milvus)
- [ ] Phase 2.2: CONC-001测试 (Qdrant)
- [ ] Phase 2.3: CONC-002测试
- [ ] Phase 2.4: CONC-003测试
- [ ] Phase 3.1: RandomFuzzer验证
- [ ] Phase 3.2: BoundaryFuzzer验证
- [ ] Phase 3.3: 组合策略挖掘
- [ ] Phase 4: 回归测试
- [ ] 结果分析与报告

---

## 预期产出

1. **测试结果文件**: `results/conc*.json`
2. **Bug报告**: `docs/NEW_BUGS_CC_CLASSIFICATION.md`
3. **覆盖率更新**: `contracts/CONTRACT_COVERAGE_INDEX.json`
4. **执行报告**: `results/bug_mining_report.md`

---

## 下一步行动

1. **确认数据库状态**: 请确认Milvus/Qdrant是否已启动
2. **开始Phase 2**: 执行CONC-001并发测试
3. **监控执行**: 观察测试结果和性能指标
4. **分析结果**: 检查是否有violation发现

**请确认是否开始执行Phase 2并发测试？**
