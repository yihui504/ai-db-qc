# AI-DB-QC 项目结构与理论体系梳理

**生成日期**: 2026-03-16  
**项目版本**: 0.1.0  
**工作区**: `c:/Users/11428/Desktop/ai-db-qc`

---

## 一、项目定位与核心价值

AI-DB-QC是一个**合约驱动的向量数据库质量保障框架**，专注于发现AI数据库（Milvus、Qdrant、SeekDB等）中的语义缺陷、API违规和正确性问题。

### 核心创新点

1. **合约驱动测试** - 用形式化合约定义预期行为，自动生成测试用例
2. **四类型缺陷分类** - Type-1/2/3/4 + Type-2.PreconditionFailed 子类型
3. **多层Oracle架构** - ExactOracle + ApproximateOracle + SemanticOracle
4. **适配器模式** - 统一接口支持多数据库（Milvus/Qdrant/SeekDB/Mock）
5. **语义变质测试** - LLM驱动的语义数据生成 + 变质关系验证

---

## 二、项目目录结构

```
ai-db-qc/
├── pyproject.toml              # 项目配置（CLI入口点: ai-db-qa）
├── docker-compose.yml          # 基础设施（Milvus:19530, Qdrant:6333）
├── requirements.txt            # 最小依赖
├── conftest.py                 # pytest根配置
│
├── ai_db_qa/                   # CLI + 工作流 + 语义测试核心
│   ├── __main__.py             # CLI入口点
│   ├── cli_parsers.py          # 四大子命令参数解析
│   ├── embedding.py            # Embedding后端（ST/OpenAI/Hash）
│   ├── semantic_datagen.py     # LLM驱动语义数据生成
│   ├── multi_layer_oracle.py   # 多层语义Oracle
│   └── workflows/
│       ├── generate.py         # generate: 模板→用例包
│       ├── validate.py         # validate: 单数据库验证
│       ├── compare.py          # compare: 跨数据库差分
│       └── export.py           # export: 结果导出
│
├── adapters/                   # 数据库适配器层
│   ├── base.py                 # AdapterBase抽象类
│   ├── mock.py                 # 可控Mock适配器
│   ├── milvus_adapter.py       # Milvus适配器（~35KB）
│   ├── qdrant_adapter.py       # Qdrant适配器（~23KB）
│   └── seekdb_adapter.py       # SeekDB适配器（~15KB）
│
├── pipeline/                   # 测试执行流水线
│   ├── executor.py             # Executor: 执行用例 + 调用Oracle
│   ├── preconditions.py        # PreconditionEvaluator（合约+运行时）
│   ├── gate.py                 # GateStub（简化前置条件门）
│   ├── triage.py               # Triage: 四类型Bug分类
│   ├── confirm.py              # ConfirmPlaceholder（Phase 3占位）
│   └── oracles/
│       ├── exa_001_oracle.py
│       ├── r6a_001_oracle.py
│       └── sch006b_001_oracle.py
│
├── oracles/                    # 语义Oracle实现
│   ├── base.py                 # OracleBase抽象类
│   ├── write_read_consistency.py  # 写读一致性检验
│   ├── filter_strictness.py       # 过滤严格性检验
│   └── monotonicity.py            # Top-K单调性检验
│
├── schemas/                    # Pydantic数据模型
│   ├── case.py                 # TestCase
│   ├── common.py               # InputValidity/BugType/OperationType
│   ├── result.py               # ExecutionResult/OracleResult
│   ├── triage.py               # TriageResult
│   └── evidence.py             # Fingerprint/RuntimeSnapshot
│
├── core/                       # 历史核心框架（合约注册、测试生成、Oracle引擎）
│   ├── contract_registry.py
│   ├── contract_test_generator.py
│   ├── oracle_engine.py        # ~63KB 最大单文件
│   ├── dataset_generators.py
│   ├── discovery_generator.py
│   └── hybrid_generator.py
│
├── contracts/                  # 合约定义
│   ├── core/
│   │   ├── default_contract.yaml   # 数据库无关核心合约（9操作）
│   │   ├── schema.py               # CoreContract/OperationContract
│   │   └── loader.py
│   ├── db_profiles/
│   │   ├── milvus_profile.yaml     # Milvus 2.3.x 能力配置
│   │   ├── seekdb_profile.yaml
│   │   └── schema.py               # DBProfile
│   ├── ann/                    # ANN合约（5个）
│   ├── index/                  # Index合约（4个）
│   ├── hybrid/                 # Hybrid合约（3个）
│   ├── schema/                 # Schema合约（4个）
│   ├── cons/                   # 一致性合约
│   ├── CONTRACT_COVERAGE_INDEX.json   # ~28KB
│   └── VALIDATION_MATRIX.json        # ~42KB
│
├── casegen/                    # 测试用例生成
│   ├── generators/
│   │   ├── instantiator.py     # YAML模板→TestCase实例化
│   │   ├── exa_001_generator.py
│   │   ├── r6a_001_generator.py
│   │   └── sch006b_001_generator.py
│   └── templates/              # YAML模板库（18个）
│       ├── basic_templates.yaml
│       ├── r1_core.yaml
│       ├── r2_param_validation.yaml
│       ├── r3_sequence_state.yaml
│       ├── r5b_lifecycle.yaml
│       ├── differential_shared_pack.yaml
│       └── ...
│
├── campaigns/                  # Campaign配置
│   ├── r1_milvus_core.yaml
│   ├── r2_param_validation.yaml
│   ├── r6a_consistency/config.yaml
│   ├── sch006b_followup/config.yaml
│   └── ...
│
├── capabilities/               # 数据库能力注册表
│   ├── milvus_capabilities.json
│   ├── qdrant_capabilities.json
│   ├── seekdb_capabilities.json
│   └── mock_capabilities.json
│
├── scripts/                    # 执行脚本（41个）
│   ├── run_semantic_campaign.py    # 语义变形测试
│   ├── run_r7_concurrency.py       # R7并发测试
│   ├── run_r6_differential.py      # R6 Milvus vs Qdrant
│   ├── run_r5bc_idx003_idx004.py   # IDX-003/004合约测试
│   ├── run_r5b_index_pilot.py      # R5B索引合约
│   ├── run_ann_pilot.py            # R5A ANN合约
│   ├── run_hybrid_pilot.py         # R5C混合查询
│   ├── run_full_r4_differential.py # R4完整差分
│   ├── bootstrap_campaign.py       # Campaign脚手架生成
│   └── ...
│
├── results/                    # 执行结果
│   ├── semantic-finance-*.json
│   ├── semantic-medical-*.json
│   ├── idx003-idx004-*.json
│   ├── r7-concurrency-*.json
│   └── ...
│
├── generated_tests/            # 自动生成的测试
├── packs/                      # 生成的用例包
├── runs/                       # 历史运行记录
├── evidence/                   # 测试证据
├── tests/                      # 单元/集成测试
│
└── docs/                       # 文档（164个）
    ├── FRAMEWORK_ARCHITECTURE.md
    ├── BUG_TAXONOMY.md
    ├── CONTRACT_MODEL.md
    ├── PROJECT_PROGRESS_SUMMARY.md
    ├── R5A_ANN_PILOT_REPORT.md
    ├── R5C_HYBRID_PILOT_REPORT.md
    ├── experiments/
    ├── handoffs/
    ├── issues/
    └── reports/
```

---

## 三、理论体系架构

### 3.1 核心概念层级

```
┌─────────────────────────────────────────────────────────────────────┐
│                        理论体系层级                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Layer 5: Campaign（测试活动）                                        │
│      └── 组织：template + substitutions + databases + output        │
│                                                                       │
│  Layer 4: Contract（合约定义）                                        │
│      └── 核心：operations + parameters + preconditions              │
│      └── 家族：ANN / Index / Hybrid / Schema / Cons                 │
│                                                                       │
│  Layer 3: TestCase（测试用例）                                        │
│      └── 字段：case_id, operation, params, expected_validity        │
│      └── 属性：required_preconditions, oracle_refs, rationale       │
│                                                                       │
│  Layer 2: Execution（执行流水线）                                     │
│      └── 组件：PreconditionEvaluator → Adapter → Oracle → Triage    │
│      └── 状态：mock_state, write_history, unfiltered_result_ids     │
│                                                                       │
│  Layer 1: Classification（缺陷分类）                                 │
│      └── 四类型：Type-1/2/3/4 + Type-2.PreconditionFailed           │
│      └── 决策树：基于 (validity, precondition, outcome, diagnostics) │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 四类型缺陷分类（Bug Taxonomy）

| 类型 | 条件 | 严重性 | 示例 |
|------|------|--------|------|
| **Type-1** | `validity=illegal ∧ success=true` | HIGH | 无效metric_type被接受 |
| **Type-2** | `validity=illegal ∧ success=false ∧ poor_diagnostic` | MEDIUM | 错误信息不指明具体参数 |
| **Type-2.PF** | `validity=legal ∧ precondition=false ∧ poor_diagnostic` | MEDIUM | 前置条件不满足但错误信息模糊 |
| **Type-3** | `validity=legal ∧ precondition=true ∧ success=false` | HIGH | 合法操作失败/崩溃 |
| **Type-4** | `validity=legal ∧ precondition=true ∧ oracle=false` | MEDIUM | 语义不变量违反 |

**红线规则**: Type-3/4 必须满足 `precondition_pass=true`，否则为 Type-2.PF。

### 3.3 合约模型（Contract Model）

```yaml
# 核心合约结构（default_contract.yaml）
operations:
  create_collection:
    parameters:
      collection_name: {type: str, required: true}
      dimension: {type: int, required: true, min_value: 1}
      metric_type: {type: str, required: false, allowed_values: [L2, IP, COSINE]}
    required_preconditions: []
  
  search:
    parameters:
      collection_name: {type: str, required: true}
      vector: {type: list, required: true}
      top_k: {type: int, required: true, min_value: 1}
    required_preconditions:
      - collection_exists
      - index_built
      - index_loaded
```

```yaml
# 数据库Profile（milvus_profile.yaml）
supported_operations: [create_collection, insert, search, ...]
parameter_relaxations:
  search:
    top_k: {max_value: 16384}  # Milvus允许更大的top_k
supported_features: [IVF_FLAT, HNSW, FILTERED_SEARCH, HYBRID_SEARCH]
```

### 3.4 前置条件评估（Precondition Evaluator）

```
前置条件检查类型：
├── legality（合法性检查）
│   ├── operation_supported: 操作是否在核心合约中
│   ├── operation_in_profile: 操作是否在数据库profile中
│   └── param_required: 必填参数是否提供
│
└── runtime（运行时检查）
    ├── collection_exists: 集合是否存在
    ├── index_built: 索引是否构建
    ├── index_loaded: 索引是否加载
    ├── connection_active: 连接是否活跃
    └── min_data_count: 数据量是否满足阈值
```

### 3.5 Oracle架构

```
Oracle类型：
├── ExactOracle（精确验证）
│   └── ANN-001: Top-K cardinality（结果数≤top_k）
│   └── ANN-002: Distance monotonicity（距离递增）
│   └── ANN-003: Nearest neighbor inclusion
│
├── ApproximateOracle（近似验证）
│   └── ANN recall ≥ threshold（召回率阈值）
│   └── HNSW/IVF近似质量
│
├── SemanticOracle（语义验证）
│   └── MR-03: Hard Negative判别（语义相反词不应相邻）
│   └── WriteReadConsistency（写入数据可读回）
│   └── FilterStrictness（过滤结果是全集子集）
│   └── Monotonicity（K5 ≤ K10）
│
└── MultiLayerOracle（多层组合）
    └── Layer 1: Exact检查 → Layer 2: Approximate检查 → Layer 3: Semantic检查
```

---

## 四、数据流与执行流程

### 4.1 Generate工作流

```
campaign.yaml
    │
    ▼
load_templates(template.yaml)
    │
    ▼
instantiate_all(templates, substitutions)
    │  └── _substitute_placeholders(): {collection} → "test_collection"
    │
    ▼
TestCase[]
    │
    ▼
pack.json → packs/generated_pack.json
```

### 4.2 Validate工作流

```
pack.json
    │
    ▼
TestCase[]
    │
    ▼
PreconditionEvaluator.evaluate(case)
    │  ├── legality checks
    │  └── runtime checks
    │
    ▼
Adapter.execute(request)
    │
    ▼
ExecutionResult
    │
    ▼
Oracle.validate(case, result, context)
    │  ├── WriteReadConsistency
    │  ├── FilterStrictness
    │  └── Monotonicity
    │
    ▼
Triage.classify(case, result)
    │  └── Bug Type Decision Tree
    │
    ▼
TriageResult
    │
    ▼
保存：execution_results.jsonl, triage_results.json, summary.json
```

### 4.3 Compare工作流

```
pack.json
    │
    ├──▶ MilvusAdapter → validate → results_by_db["milvus"]
    │
    └──▶ QdrantAdapter → validate → results_by_db["qdrant"]
    
    │
    ▼
_analyze_differential(results_by_db, cases)
    │  ├── compare_outcomes()
    │  ├── label_differences()
    │  └── identify_stricter_database()
    │
    ▼
differential_details.json + differential_report.md
```

---

## 五、已完成测试活动汇总

| Campaign | 测试数 | 重点 | 关键发现 |
|----------|--------|------|---------|
| **R1** | 50 | 参数边界/能力边界 | 3 bugs |
| **R2** | 40 | API参数验证 | 2 bugs |
| **R3** | 30 | 序列与状态 | 1 bug |
| **R4** | 100+ | Milvus vs Qdrant差分 | 4 ALLOWED_DIFFERENCE |
| **R5A** | 10 | ANN合约 | 0 violations |
| **R5B/C** | 20 | 索引生命周期/混合查询 | 0 violations |
| **R6** | - | Milvus vs Qdrant新差分 | 差分分析 |
| **R6A** | 6 | 一致性/可见性 | 6/6 PASS |
| **R7** | 4 | 并发测试 | 4/4 PASS |
| **语义测试** | 42 | Finance + Medical | **MR-03: 100% VIOLATION** |

**总计**: 244+用例，发现10+合约违规

### MR-03 Hard Negative判别缺陷（关键发现）

- **现象**: 语义相反词对（rose/fell, benign/malignant）在向量空间相邻
- **违规率**: Finance 100%, Medical 100%
- **类型**: Type-4（语义不变量违反）
- **根因**: 向量嵌入空间中，语义对立词距离过近，导致搜索结果混淆

---

## 六、关键技术发现与修复

### 6.1 Embedding离线加载Bug

**问题**: `_hf_cache_has_model`中`pathlib.Path("")`展开为当前目录导致缓存检测失败

**修复**:
```python
def _hf_cache_has_model(model_slug: str) -> bool:
    hf_home = os.environ.get("HF_HOME", "").strip()
    if hf_home:
        cache_root = pathlib.Path(hf_home).expanduser() / "hub"
    else:
        cache_root = pathlib.Path.home() / ".cache" / "huggingface" / "hub"
    # ...
```

### 6.2 IDX-004索引重建幂等性

**问题**: Milvus v2.6强制"at most one index per field"，直接rebuild失败

**修复**: `drop_index()` → `create_index()` 流程

### 6.3 Triage诊断感知

**增强**: `_has_good_diagnostics()`区分好/差诊断信息
- 好: 包含具体参数名、值、解决方案
- 差: "Error", "Operation failed"等模糊信息

---

## 七、CLI使用指南

```bash
# 安装
pip install -e .

# 生成用例包
ai-db-qa generate --campaign campaigns/r1_milvus_core.yaml

# 单数据库验证
ai-db-qa validate --campaign campaigns/r1_milvus_core.yaml

# 跨数据库差分
ai-db-qa compare --campaign campaigns/compare_example.yaml

# 导出结果
ai-db-qa export --input results/run/ --type issue-report --output report.md
```

---

## 八、下一步研究方向

### 短期（R5B完整）
- 完成索引行为合约测试
- 细化IDX-001 Oracle（区分硬合约检查与ANN近似容忍）

### 中期
- 扩展至Qdrant、Weaviate等多数据库
- 提高Bug-yield（成熟数据库核心操作测试完善，需探索新领域）

### 长期
- 演化为通用AI数据库QA框架
- 支持向量、图、时序数据库

---

## 九、关键文件索引

| 文件 | 用途 |
|------|------|
| `contracts/core/default_contract.yaml` | 数据库无关核心合约 |
| `contracts/db_profiles/milvus_profile.yaml` | Milvus能力配置 |
| `pipeline/executor.py` | 测试执行核心 |
| `pipeline/triage.py` | 缺陷分类引擎 |
| `ai_db_qa/embedding.py` | Embedding后端 |
| `ai_db_qa/semantic_datagen.py` | 语义数据生成 |
| `ai_db_qa/multi_layer_oracle.py` | 多层Oracle |
| `scripts/run_semantic_campaign.py` | 语义测试入口 |
| `scripts/run_r7_concurrency.py` | 并发测试入口 |

---

**文档维护**: 本文档应随项目迭代持续更新  
**最后更新**: 2026-03-16
