# Aggressive Bug Mining - 快速开始

## 5分钟快速启动

### 1. 测试单个数据库的Boundary条件

```bash
# 测试Milvus的Boundary条件
python scripts/run_boundary_tests.py --db milvus
```

### 2. 测试Schema演化

```bash
# 测试Qdrant的Schema演化
python scripts/run_schema_evolution.py --db qdrant
```

### 3. 运行完整的Aggressive Bug Mining Campaign

```bash
# 在所有数据库上运行完整campaign
python scripts/run_aggressive_bug_mining.py --db all
```

## 常用命令

### Schema演化测试

```bash
# 单个数据库
python scripts/run_schema_evolution.py --db milvus

# 所有数据库
python scripts/run_schema_evolution.py --db all

# 保存结果到指定位置
python scripts/run_schema_evolution.py --db milvus --output results/my_results.json
```

### Boundary条件测试

```bash
# 单个数据库
python scripts/run_boundary_tests.py --db milvus

# 所有数据库
python scripts/run_boundary_tests.py --db all

# 保存结果
python scripts/run_boundary_tests.py --db milvus --output results/boundary_test.json
```

### Stress压力测试

```bash
# 仅吞吐量测试（STR-001）
python scripts/run_stress_tests.py --db milvus --contract STR-001

# 仅规模测试（STR-002）
python scripts/run_stress_tests.py --db qdrant --contract STR-002

# 所有stress测试
python scripts/run_stress_tests.py --db milvus --contract all
```

### Campaign运行

```bash
# 单个数据库
python scripts/run_aggressive_bug_mining.py --db milvus

# 所有数据库
python scripts/run_aggressive_bug_mining.py --db all

# 使用自定义配置
python scripts/run_aggressive_bug_mining.py --config campaigns/aggressive_bug_mining.yaml
```

## 结果查看

测试完成后，结果保存在 `results/` 目录下：

```bash
# 查看Schema演化结果
ls results/schema_evolution_2025_001/

# 查看Boundary测试结果
ls results/boundary_2025_001/

# 查看Stress测试结果
ls results/stress_2025_001/

# 查看Campaign汇总
cat results/aggressive_bug_mining_2025_001/campaign_results.json
```

## 使用Fuzzing工具

### 在Python脚本中使用

```python
# 创建Boundary Fuzzer
from casegen.fuzzing.targeted_fuzzer import create_boundary_fuzzer

fuzzer = create_boundary_fuzzer("BND-001", ["dimension"])

# 定义基础测试用例
base_case = {
    "operation": "create_collection",
    "params": {
        "collection_name": "test",
        "dimension": 128,
        "metric_type": "L2"
    }
}

# 生成模糊测试用例
results = fuzzer.fuzz(base_case)

# 处理结果
for result in results:
    print(f"Status: {result.status}")
    print(f"Test case: {result.test_case}")
    print(f"Metadata: {result.metadata}")
```

```python
# 创建Schema Fuzzer
from casegen.fuzzing.schema_fuzzer import create_schema_evolution_fuzzer

fuzzer = create_schema_evolution_fuzzer()

# 生成schema演化测试用例
results = fuzzer.fuzz(base_case)

# 处理结果
for result in results:
    print(f"Focus: {result.metadata.get('focus')}")
    print(f"Mutation: {result.metadata.get('mutation')}")
```

## 支持的数据库

所有测试支持以下数据库：

- **milvus** - Milvus向量数据库
- **qdrant** - Qdrant向量数据库
- **weaviate** - Weaviate向量数据库
- **pgvector** - PostgreSQL pgvector扩展

## 测试合约说明

### Schema演化合约
- **SCH-005**: Schema扩展向后兼容性
- **SCH-006**: Schema操作原子性

### Boundary条件合约
- **BND-001**: 向量维度边界验证
- **BND-002**: Top-K参数边界验证
- **BND-003**: Metric类型验证
- **BND-004**: Collection名称边界验证

### Stress压力测试合约
- **STR-001**: 高吞吐量压力测试
- **STR-002**: 大规模数据集压力测试

## 缺陷分类

测试使用四类型缺陷分类：

- **Type-1**: 无效参数被接受 (HIGH)
- **Type-2**: 有效参数被拒绝或错误信息不明确 (MEDIUM)
- **Type-2.PF**: 前置条件不满足但错误信息模糊 (MEDIUM)
- **Type-3**: 合法操作失败/崩溃 (HIGH)
- **Type-4**: 语义不变量违反 (MEDIUM)

## 资源需求

### Schema & Boundary测试
- CPU: 1-2核
- 内存: 1-2GB
- 时间: 每个数据库 ~5-10分钟

### Stress测试
- CPU: 2-4核
- 内存: 4-8GB
- 时间: 每个数据库 ~30-60分钟

### 完整Campaign
- CPU: 4-8核
- 内存: 16GB
- 时间: 所有数据库 ~2-4小时

## 故障排查

### 连接失败

```bash
# 检查数据库是否运行
docker ps

# 查看日志
docker-compose logs milvus
docker-compose logs qdrant
```

### 超时错误

```bash
# 减少stress测试规模
# 编辑 campaigns/aggressive_bug_mining.yaml
# 修改 dataset_sizes 或 throughput_levels
```

### 权限错误

```bash
# 确保有写入权限
chmod +x scripts/run_*.py

# 创建results目录
mkdir -p results
```

## 获取帮助

```bash
# 查看脚本帮助
python scripts/run_schema_evolution.py --help
python scripts/run_boundary_tests.py --help
python scripts/run_stress_tests.py --help
python scripts/run_aggressive_bug_mining.py --help
```

## 更多信息

- 详细文档: `AGGRESSIVE_BUG_MINING_README.md`
- 实现总结: `IMPLEMENTATION_SUMMARY.md`
- 项目结构: `PROJECT_STRUCTURE_AND_THEORY.md`

---

**快速开始，立即开始发现Bug！** 🚀
