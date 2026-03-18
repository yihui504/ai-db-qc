# AI-DB-QC 理论体系详解

**文档版本**: 2.0  
**生成日期**: 2026-03-16  
**范围**: 完整理论框架、核心概念、设计原则、实现映射

---

## 一、理论体系总览

AI-DB-QC 理论体系是一个**合约驱动的向量数据库质量保障框架**，其核心创新在于将形式化合约、多层Oracle验证、四类型缺陷分类有机结合，形成一套可自动化、可扩展、可复现的AI数据库测试方法论。

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     AI-DB-QC 理论体系架构                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                  │
│   │  合约模型   │────▶│  测试生成   │────▶│  执行流水线 │                  │
│   │  Contract   │     │  Generator  │     │  Pipeline   │                  │
│   └─────────────┘     └─────────────┘     └──────┬──────┘                  │
│          │                                         │                        │
│          ▼                                         ▼                        │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                  │
│   │  五类合约   │     │  适配器层   │     │  Oracle系统 │                  │
│   │  5 Types    │     │  Adapters   │     │  MultiLayer │                  │
│   └─────────────┘     └─────────────┘     └──────┬──────┘                  │
│                                                    │                        │
│                                                    ▼                        │
│                                            ┌─────────────┐                 │
│                                            │  缺陷分类   │                 │
│                                            │  Triage     │                 │
│                                            └─────────────┘                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 二、核心理论支柱

### 2.1 合约理论（Contract Theory）

#### 定义与本质

**合约（Contract）** 是对系统预期行为的形式化规范，具有以下特征：

1. **约束性**：明确界定合法/非法操作边界
2. **可测试性**：可自动生成测试用例
3. **可判断性**：提供Oracle判断标准
4. **范围明确**：定义适用边界（全局/数据库特定/操作级）

#### 五类合约体系

```
CONTRACTS
├── 1. 强通用合约 (Strong Universal Contracts)
│   ├── 适用范围：所有向量数据库
│   ├── 来源：数据管理第一性原理
│   ├── 违规判定：必然是Bug
│   └── 示例：
│       ├── UC-001: 已删除实体不应出现在搜索结果中
│       ├── UC-002: 已删除集合应拒绝所有操作
│       ├── UC-003: 幂等操作应有确定性行为
│       └── UC-005: 数据必须持久化
│
├── 2. 数据库特定合约 (Database-Specific Contracts)
│   ├── 适用范围：特定数据库实现
│   ├── 来源：数据库文档/观测行为
│   ├── 违规判定：该数据库的Bug
│   ├── 跨数据库差异：允许差异（ALLOWED_DIFFERENCE）
│   └── 示例：
│       ├── MS-001: Milvus搜索前必须Load集合
│       ├── MS-002: Milvus Load前必须创建索引
│       └── QD-001: Qdrant不允许创建同名集合
│
├── 3. 操作级合约 (Operation-Level Contracts)
│   ├── 适用范围：单个操作
│   ├── 来源：API签名/文档
│   ├── 测试重点：参数边界验证
│   └── 示例：
│       ├── OP-001: 集合维度必须是正整数
│       ├── OP-002: 维度必须在支持范围内(1-32768)
│       ├── OP-003: top_k必须 >= 0
│       └── OP-004: 插入向量维度必须匹配集合维度
│
├── 4. 序列/状态合约 (Sequence/State Contracts)
│   ├── 适用范围：操作序列/状态转换
│   ├── 来源：状态机模型
│   ├── 测试重点：状态转换正确性
│   └── 示例：
│       ├── SS-001: 集合必须存在才能执行操作
│       ├── SS-002: Load需要先创建索引
│       ├── SS-003: Delete是幂等的
│       └── SS-005: Drop后状态是永久的
│
└── 5. 结果/输出合约 (Result/Output Contracts)
    ├── 适用范围：操作输出
    ├── 来源：输出模式定义
    ├── 测试重点：输出格式/内容验证
    └── 示例：
        ├── RS-001: 搜索返回结果数 ≤ top_k
        ├── RS-002: 结果按相似度排序
        ├── RS-003: Insert返回插入的ID列表
        └── RS-005: 错误信息应具有描述性
```

#### 合约信息模型

每个合约包含以下结构化信息：

```json
{
  "contract_id": "ANN-001",
  "name": "Top-K Cardinality Correctness",
  "type": "universal",
  "scope": {
    "databases": ["all"],
    "operations": ["search"],
    "conditions": ["top_k >= 0"]
  },
  "statement": "Search with top_k must return at most K results",
  "preconditions": ["collection_exists", "index_loaded"],
  "postconditions": ["result_count <= top_k"],
  "invariants": ["cardinality_bound"],
  "violation_criteria": {
    "condition": "len(results) > top_k",
    "severity": "high"
  },
  "test_generation": {
    "strategy": "boundary",
    "legal_cases": [...],
    "illegal_cases": [...],
    "boundary_cases": [...]
  },
  "oracle": {
    "check": "count(results) <= top_k",
    "classification_rules": {...}
  }
}
```

---

### 2.2 Oracle理论（Oracle Theory）

#### Test Oracle问题

向量数据库测试面临独特的Oracle问题：

1. **无唯一正确答案**：ANN是近似搜索，"正确结果"是统计概念
2. **语义相关性模糊**：相似度阈值难以精确定义
3. **非确定性**：相同查询可能返回不同结果（ANN特性）
4. **质量评估多维**：性能、召回、精度、语义相关性

#### 三层Oracle架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Multi-Layer Oracle System                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Layer 1: ExactOracle (精确验证)                                           │
│   ─────────────────────────────────────                                     │
│   性质：确定性检查，信心度=1.0                                                │
│   检查项：                                                                   │
│     ├── 基数约束：|results| <= top_k                                         │
│     ├── 数据类型：results必须是List                                          │
│     ├── API契约：status字段正确                                               │
│     ├── 距离单调性：results按distance升序排列                                 │
│     ├── 数据保持：非变更操作后count不变                                       │
│     └── 崩溃检测：无异常/服务器错误                                           │
│                                                                             │
│   优先级：最高（发现VIOLATION直接覆盖所有其他层）                              │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Layer 2: ApproximateOracle (近似验证)                                      │
│   ─────────────────────────────────────────                                 │
│   性质：统计检查，有容差                                                     │
│   检查项：                                                                   │
│     ├── Recall@K：召回率 >= 阈值（按索引类型）                                │
│     │   └── FLAT: 0.99, HNSW: 0.80, IVF_FLAT: 0.75, IVF_PQ: 0.65           │
│     ├── 召回稳定性：多次查询召回率标准差 <= 0.05                              │
│     └── 变质一致性：语义等价查询结果重叠率 >= 0.70                            │
│                                                                             │
│   判决类型：                                                                 │
│     ├── PASS：召回达标                                                       │
│     ├── ALLOWED_DIFFERENCE：召回不达标但属于ANN近似行为（不是Bug）            │
│     └── VIOLATION：变质关系违反                                              │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Layer 3: SemanticOracle (语义验证)                                         │
│   ─────────────────────────────────────                                     │
│   性质：LLM辅助软判断，输出信心加权判决                                       │
│   设计原则（来自Argus论文）：                                                 │
│     ├── "LLM作为生成器，而非最终裁决者"                                       │
│     ├── 多次采样降低LLM方差                                                  │
│     ├── 信心阈值过滤低质量判断                                                │
│     └── 永不覆盖Layer 1/2的VIOLATION发现                                     │
│                                                                             │
│   检查流程：                                                                 │
│     1. 对每个检索文档进行N次LLM打分（0-10）                                   │
│     2. 计算平均分和标准差                                                    │
│     3. 标准差 → 信心度（方差小=信心高）                                       │
│     4. 判决：                                                                │
│        ├── 信心 < min_confidence → OBSERVATION（需人工审核）                 │
│        ├── avg_score >= threshold → PASS                                    │
│        └── avg_score < threshold → VIOLATION（仅高信心时）                   │
│                                                                             │
│   关键参数：                                                                 │
│     ├── relevance_threshold: 4.0（语义相关性阈值）                           │
│     ├── min_confidence: 0.7（最低信心要求）                                  │
│     └── n_samples: 3（每个文档采样次数）                                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Oracle判决优先级

```python
def decide(layer_results: List[LayerResult]) -> OracleDecision:
    """
    判决优先级（从高到低）：
    
    1. INFRA_FAILURE   - 测试基础设施故障（无法判断）
    2. Exact VIOLATION - 精确违规（确定性，信心=1.0，覆盖所有）
    3. Approx VIOLATION - 统计违规（高信心）
    4. Semantic VIOLATION - 语义违规（仅高信心时，confidence >= 0.80）
    5. ALLOWED_DIFF    - 允许差异（ANN近似行为，不是Bug）
    6. OBSERVATION     - 观察结果（需人工审核）
    7. PASS            - 所有适用层通过
    """
```

#### Verdict类型语义

| Verdict | 含义 | 后续动作 |
|---------|------|---------|
| **PASS** | 合约满足 | 无需处理 |
| **VIOLATION** | 确定违规 | 生成Bug报告 |
| **ALLOWED_DIFFERENCE** | 架构差异 | 标记为预期行为 |
| **OBSERVATION** | 待审核 | 需人工判断 |
| **INFRA_FAILURE** | 基础设施故障 | 修复测试环境 |
| **SKIP** | Oracle不适用 | 跳过该层 |

---

### 2.3 缺陷分类理论（Bug Taxonomy）

#### 四类型分类法

AI-DB-QC采用**严格的四类型缺陷分类**，每种类型有明确的判断条件和边界。

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Four-Type Bug Classification                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Type-1: Illegal Operation Succeeded (非法操作成功)                         │
│   ─────────────────────────────────────────────────────                     │
│   条件：input_validity=ILLEGAL ∧ observed_success=TRUE                      │
│   严重性：HIGH                                                               │
│   含义：系统接受了本应拒绝的非法输入                                          │
│   示例：                                                                     │
│     ├── 插入错误维度的向量被接受                                             │
│     ├── 负数的top_k被接受                                                   │
│     └── 非法filter表达式被接受                                               │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Type-2: Illegal Operation Failed with Poor Diagnostic (非法失败，诊断差)   │
│   ─────────────────────────────────────────────────────────────────────     │
│   条件：input_validity=ILLEGAL ∧ observed_success=FALSE                     │
│         ∧ error_message_lacks_root_cause=TRUE                               │
│   严重性：MEDIUM                                                             │
│   含义：正确拒绝了非法操作，但错误信息无诊断价值                              │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ Type-2.PreconditionFailed (子类型)                                   │   │
│   │ ─────────────────────────────────────                                │   │
│   │ 条件：input_validity=LEGAL ∧ precondition_pass=FALSE                 │   │
│   │       ∧ observed_success=FALSE ∧ poor_diagnostic=TRUE                │   │
│   │                                                                     │   │
│   │ 重要：这是Type-2的子类型，NOT第五种顶层类型！                         │   │
│   │                                                                     │   │
│   │ 含义：合约合法但运行时前置条件不满足，且错误信息模糊                   │   │
│   │ 示例：                                                               │   │
│   │   ├── 在不存在的集合上搜索，错误信息"操作失败"（未说明集合不存在）     │   │
│   │   ├── 在索引未加载时搜索，错误信息"Error"（未说明索引要求）           │   │
│   │   └── 向不存在的集合插入，错误信息"internal error"                   │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Type-3: Legal Operation Failed (合法操作失败)                              │
│   ─────────────────────────────────────────────────                        │
│   条件：input_validity=LEGAL ∧ precondition_pass=TRUE                       │
│         ∧ observed_success=FALSE                                            │
│   严重性：HIGH                                                               │
│   含义：所有条件满足，但操作仍然失败/崩溃/超时                                │
│                                                                             │
│   🔴 RED-LINE: precondition_pass=TRUE 是强制要求！                          │
│   如果 precondition_pass=FALSE，必须归类为 Type-2.PreconditionFailed        │
│                                                                             │
│   子类型：                                                                   │
│     ├── Type-3.A: 抛出异常/错误                                              │
│     ├── Type-3.B: 崩溃/段错误                                               │
│     ├── Type-3.C: 挂起/无限等待                                             │
│     └── Type-3.D: 超时                                                      │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Type-4: Semantic Violation (语义违规)                                      │
│   ─────────────────────────────────────────                                │
│   条件：input_validity=LEGAL ∧ precondition_pass=TRUE                       │
│         ∧ observed_success=TRUE ∧ oracle_result=FAILED                      │
│   严重性：MEDIUM                                                             │
│   含义：操作成功但违反了语义不变量                                            │
│                                                                             │
│   🔴 RED-LINE: precondition_pass=TRUE 是强制要求！                          │
│                                                                             │
│   子类型（按Oracle分类）：                                                   │
│     ├── Type-4.Monotonicity: Top-K单调性违反（K=5返回结果多于K=10）          │
│     ├── Type-4.Consistency: 写读不一致（写入数据读不回）                     │
│     └── Type-4.Strictness: 过滤严格性违反（过滤结果不是全集子集）            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 分类决策树

```
                        ┌─────────────────────┐
                        │ input_validity == ? │
                        └──────────┬──────────┘
                                   │
                 ┌─────────────────┴─────────────────┐
                 │                                   │
             ILLEGAL                               LEGAL
                 │                                   │
                 ▼                                   ▼
        ┌────────────────┐                  ┌──────────────────┐
        │success == TRUE?│                  │precondition_pass?│
        └───────┬────────┘                  └────────┬─────────┘
                │                                    │
         ┌──────┴──────┐                      ┌──────┴──────┐
         │             │                      │             │
       FALSE         TRUE                   FALSE         TRUE
         │             │                      │             │
         ▼             ▼                      ▼             ▼
    ┌─────────┐   ┌─────────┐           ┌──────────┐  ┌──────────┐
    │诊断质量?│   │ TYPE-1  │           │诊断质量? │  │success ? │
    └────┬────┘   │(非法   │           └────┬─────┘  └────┬─────┘
         │        │成功)   │                │             │
    ┌────┴────┐   └─────────┘          ┌────┴────┐   ┌────┴────┐
    │         │                        │         │   │         │
   GOOD      POOR                     GOOD      POOR FALSE    TRUE
    │         │                        │         │     │         │
    ▼         ▼                        ▼         ▼     ▼         ▼
┌───────┐┌─────────┐              ┌───────┐┌──────────┐┌───────┐┌──────────┐
│Not Bug││ TYPE-2  │              │Not Bug││TYPE-2.PF ││TYPE-3 ││oracle ?  │
│(正确  ││(诊断差) │              │(预期的││(Type-2   ││(合法  │└────┬─────┘
│拒绝)  │└─────────┘              │失败)  ││子类型)   ││失败) │     │
└───────┘                         └───────┘└──────────┘└───────┘┌────┴────┐
                                                              │         │
                                                           PASS      VIOLATION
                                                              │         │
                                                              ▼         ▼
                                                          ┌───────┐┌─────────┐
                                                          │Not Bug││ TYPE-4  │
                                                          │(正确) ││(语义    │
                                                          └───────┘│违规)   │
                                                                   └─────────┘
```

#### 红线规则（Red-Line Enforcement）

**核心原则**：Type-3 和 Type-4 必须 `precondition_pass=TRUE`。

**原因**：区分真正的Bug和预期失败。

```
伪合法案例 (Pseudo-Valid Cases)：
├── 合约合法 + 运行时前置条件不满足 = 预期失败
│   ├── 在不存在的集合上搜索
│   ├── 在索引未加载时搜索
│   └── 向不存在的集合插入
│
└── 这些不应归类为Type-3/4，因为它们代表预期失败
```

**判断维度**：

| 概念 | 定义 | 评估者 |
|------|------|--------|
| **抽象合法性** | 请求是否满足合约约束？ | Contract validator（静态） |
| **运行时就绪性** | 环境状态是否允许执行？ | Precondition gate（动态） |
| **precondition_pass** | 所有运行时前置条件是否满足？ | ExecutionResult中的布尔标志 |

---

### 2.4 测试生成理论（Test Generation Theory）

#### 生成策略

| 策略 | 描述 | 用例 |
|------|------|------|
| **Legal** | 满足所有约束的合法输入 | 正常操作测试 |
| **Illegal** | 故意违反约束的非法输入 | 参数验证测试 |
| **Boundary** | 边界值（最小、最大、空） | 边界条件测试 |
| **Sequence** | 多步操作序列 | 状态转换测试 |
| **Combinatorial** | 多约束组合 | 约束交互测试 |

#### 用例结构

```python
@dataclass
class TestCase:
    """测试用例数据模型"""
    
    # 身份标识
    case_id: str                    # 唯一ID，如 "r1_core_001"
    
    # 操作定义
    operation: OperationType        # 操作类型（create/insert/search等）
    params: Dict[str, Any]          # 操作参数
    
    # 预期属性
    expected_validity: InputValidity  # LEGAL 或 ILLEGAL
    required_preconditions: List[str]  # 前置条件列表
    
    # Oracle配置
    oracle_refs: List[str]          # 引用的Oracle ID列表
    
    # 元数据
    rationale: str                  # 测试意图说明
    contract_id: Optional[str]      # 关联合约ID
    tags: List[str]                 # 分类标签
```

#### Campaign组织

```yaml
# campaign配置示例
name: "R1 - Milvus Core Operations"
description: "Test core Milvus operations for parameter boundaries"

template: "casegen/templates/r1_core.yaml"

substitutions:
  collection_name: "test_collection_{run_id}"
  dimension: [32, 128, 768]
  metric_type: ["L2", "IP", "COSINE"]

databases:
  - milvus
  
output:
  pack_path: "packs/r1_pack_{timestamp}.json"
  results_path: "results/r1_results_{timestamp}.json"
```

---

### 2.5 变质测试理论（Metamorphic Testing Theory）

#### 背景

变质测试（Metamorphic Testing, MT）是解决Oracle问题的经典方法，通过定义变质关系（Metamorphic Relations, MRs）来验证系统行为的正确性，无需知道精确的预期输出。

#### 变质关系定义

**变质关系（MR）**：如果输入X产生输出Y，那么变换后的输入X'应产生满足某种关系的输出Y'。

```
原始测试用例：
  Input: X → Output: Y

衍生测试用例：
  Input: X' = transform(X) → Output: Y'

变质关系：
  check(Y, Y') == True  // Y和Y'满足某种关系
```

#### AI-DB-QC中的变质关系

| MR ID | 名称 | 关系定义 | 应用场景 |
|-------|------|---------|---------|
| **MR-01** | Top-K单调性 | K₁ < K₂ → Results(K₁) ⊆ Results(K₂) | 搜索结果验证 |
| **MR-02** | 写读一致性 | Insert(X) → Search应能找到X | 数据持久化验证 |
| **MR-03** | Hard Negative判别 | semantic_opposite(X, Y) → distance(X, Y)应较大 | 语义质量验证 |
| **MR-04** | 过滤严格性 | Filter(X, condition) ⊆ Search(X) | 过滤功能验证 |

#### MR-03详解：Hard Negative判别

**定义**：语义相反的词对在向量空间中应该有较大距离。

**实现逻辑**：

```python
def check_mr03_hard_negative(query_terms: List[Tuple[str, str]]) -> List[Violation]:
    """
    MR-03: Hard Negative Discrimination
    
    检查语义相反词对在向量空间中的距离。
    如果语义相反词距离过近，说明embedding模型存在问题。
    
    Args:
        query_terms: List of (term, antonym) pairs
                     e.g., [("rose", "fell"), ("benign", "malignant")]
    
    Returns:
        List of violations where distance(term, antonym) < threshold
    """
    violations = []
    for term, antonym in query_terms:
        vec_term = embed(term)
        vec_antonym = embed(antonym)
        distance = cosine_distance(vec_term, vec_antonym)
        
        # 语义相反词应该距离较远
        # 如果距离 < 0.3，认为违反了MR-03
        if distance < 0.3:
            violations.append({
                "term": term,
                "antonym": antonym,
                "distance": distance,
                "expected": "large distance",
                "actual": "small distance"
            })
    
    return violations
```

**实际发现**：在金融和医疗领域测试中，MR-03违规率达到100%，说明语义相反词在向量空间中距离过近，这是一个重要的语义质量缺陷。

---

## 三、执行流水线理论

### 3.1 执行阶段

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Test Execution Pipeline                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Phase 1: Setup（前置准备）                                                 │
│   ────────────────────────                                                  │
│   ├── 加载TestCase                                                          │
│   ├── 初始化Adapter（连接数据库）                                            │
│   ├── 获取运行时快照（RuntimeSnapshot）                                      │
│   └── 执行setup步骤（创建集合、插入数据等）                                   │
│                                                                             │
│   Phase 2: Precondition Evaluation（前置条件评估）                           │
│   ──────────────────────────────────────────                                │
│   ├── legality checks（合法性检查）                                          │
│   │   ├── operation_supported: 操作在核心合约中？                            │
│   │   ├── operation_in_profile: 操作在数据库profile中？                      │
│   │   └── param_required: 必填参数已提供？                                   │
│   │                                                                         │
│   └── runtime checks（运行时检查）                                           │
│       ├── collection_exists: 集合存在？                                      │
│       ├── index_built: 索引已构建？                                          │
│       ├── index_loaded: 索引已加载？                                         │
│       └── min_data_count: 数据量满足阈值？                                   │
│                                                                             │
│   Phase 3: Execution（操作执行）                                             │
│   ────────────────────────                                                  │
│   ├── Adapter.execute(operation, params)                                    │
│   ├── 捕获ExecutionResult                                                   │
│   │   ├── observed_success: TRUE/FALSE                                      │
│   │   ├── observed_outcome: SUCCESS/ERROR/TIMEOUT/CRASH                     │
│   │   ├── response: 返回数据                                                │
│   │   ├── error_message: 错误信息                                           │
│   │   └── precondition_pass: 所有前置条件满足？                              │
│   │                                                                         │
│   └── 更新mock_state（记录状态变化）                                         │
│                                                                             │
│   Phase 4: Oracle Evaluation（Oracle评估）                                   │
│   ──────────────────────────────────                                        │
│   ├── Layer 1: ExactOracle                                                  │
│   │   └── 检查基数、类型、API契约                                            │
│   │                                                                         │
│   ├── Layer 2: ApproximateOracle                                            │
│   │   └── 检查召回率、稳定性、变质关系                                       │
│   │                                                                         │
│   ├── Layer 3: SemanticOracle                                               │
│   │   └── LLM辅助语义相关性判断                                              │
│   │                                                                         │
│   └── MultiLayerOracle.decide() → OracleDecision                           │
│                                                                             │
│   Phase 5: Triage Classification（缺陷分类）                                 │
│   ────────────────────────────────────                                      │
│   ├── Triage.classify(case, result)                                         │
│   ├── 应用四类型分类决策树                                                   │
│   ├── 生成TriageResult                                                      │
│   │   ├── final_type: TYPE_1/2/3/4/TYPE_2_PF                               │
│   │   ├── rationale: 分类理由                                               │
│   │   └── evidence: 证据数据                                                │
│   │                                                                         │
│   └── 返回 None（非Bug）或 TriageResult（Bug）                              │
│                                                                             │
│   Phase 6: Cleanup（清理）                                                  │
│   ───────────────────                                                       │
│   ├── 执行cleanup步骤（删除集合等）                                          │
│   ├── 断开Adapter连接                                                       │
│   └── 保存结果到文件                                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 数据流图

```
TestCase (YAML)
     │
     ▼
┌──────────────┐
│ Instantiator │ ──── TestCase实例化（参数替换）
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   Pack JSON  │ ──── 测试用例包（可序列化）
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│ PreconditionEval │ ──── 前置条件评估
└────────┬─────────┘
         │
         ▼
┌──────────────┐
│   Adapter    │ ──── 数据库操作执行
└──────┬───────┘
       │
       ▼
┌─────────────────┐
│ ExecutionResult │ ──── 原始执行结果
└────────┬────────┘
         │
         ▼
┌───────────────────┐
│  OraclePipeline   │ ──── 多层Oracle评估
└────────┬──────────┘
         │
         ▼
┌─────────────────┐
│ OracleDecision  │ ──── Oracle判决
└────────┬────────┘
         │
         ▼
┌───────────────┐
│    Triage     │ ──── 缺陷分类
└───────┬───────┘
        │
        ▼
┌─────────────────┐
│ TriageResult    │ ──── 最终分类结果
│ (or None)       │
└─────────────────┘
```

---

## 四、设计原则与约束

### 4.1 核心设计原则

#### 1. 关注点分离（Separation of Concerns）

```
Contract → 定义预期行为（What）
Generator → 生成测试用例（How to create）
Adapter → 执行数据库操作（How to run）
Oracle → 验证结果正确性（How to judge）
Triage → 分类缺陷类型（How to classify）
```

#### 2. 可扩展性（Extensibility）

- **新增数据库**：实现AdapterBase接口
- **新增合约**：添加JSON定义文件
- **新增Oracle**：扩展OracleBase类
- **新增生成策略**：添加Strategy实现

#### 3. 可复现性（Reproducibility）

- 所有测试用例可序列化为JSON
- 运行时状态可快照
- 结果可持久化
- 随机种子可控

#### 4. LLM独立性（LLM-Independence）

**关键原则**：最终缺陷分类永不委托给LLM。

- LLM仅用于语义数据生成（Generator角色）
- LLM仅用于语义相关性软判断（Soft Judge角色）
- 所有分类决策由确定性代码执行
- Oracle的VIOLATION判决需满足信心阈值

### 4.2 理论约束

#### 约束1：前置条件红线

Type-3 和 Type-4 必须满足 `precondition_pass=true`。这是区分真正Bug和预期失败的唯一可靠标准。

#### 约束2：四类型互斥性

每个发现属于且仅属于一个顶层类型（TYPE_1/2/3/4）。TYPE_2.PreconditionFailed是TYPE_2的子类型，不是第五种类型。

#### 约束3：Oracle优先级

ExactOracle的VIOLATION判决覆盖所有其他层。精确违规的确定性高于统计/语义判断。

#### 约束4：合约范围明确性

跨数据库差异必须标记为ALLOWED_DIFFERENCE，而非VIOLATION。数据库特定合约仅在对应数据库上生效。

---

## 五、实现映射

### 5.1 核心类与模块

| 理论概念 | 实现模块 | 核心类 |
|---------|---------|--------|
| 合约定义 | `contracts/core/schema.py` | CoreContract, OperationContract |
| 合约注册 | `core/contract_registry.py` | ContractRegistry |
| 测试生成 | `casegen/generators/instantiator.py` | Instantiator |
| 数据库适配 | `adapters/base.py` | AdapterBase |
| Milvus适配 | `adapters/milvus_adapter.py` | MilvusAdapter |
| 前置条件 | `pipeline/preconditions.py` | PreconditionEvaluator |
| 执行流水线 | `pipeline/executor.py` | Executor |
| 精确Oracle | `ai_db_qa/multi_layer_oracle.py` | ExactOracle |
| 近似Oracle | `ai_db_qa/multi_layer_oracle.py` | ApproximateOracle |
| 语义Oracle | `ai_db_qa/multi_layer_oracle.py` | SemanticOracle |
| 多层协调 | `ai_db_qa/multi_layer_oracle.py` | MultiLayerOracle |
| 缺陷分类 | `pipeline/triage.py` | Triage |
| 数据模型 | `schemas/*.py` | TestCase, ExecutionResult, TriageResult |

### 5.2 配置文件

| 配置类型 | 文件位置 | 用途 |
|---------|---------|------|
| 项目配置 | `pyproject.toml` | 依赖、入口点 |
| 核心合约 | `contracts/core/default_contract.yaml` | 数据库无关核心合约 |
| 数据库Profile | `contracts/db_profiles/milvus_profile.yaml` | Milvus能力配置 |
| Campaign配置 | `campaigns/*.yaml` | 测试活动配置 |
| 模板库 | `casegen/templates/*.yaml` | 测试用例模板 |

---

## 六、关键发现与应用

### 6.1 MR-03 Hard Negative判别缺陷

**发现**：在Finance和Medical领域的语义测试中，MR-03违规率达到100%。

**现象**：语义相反词对（如 rose/fell, benign/malignant）在向量空间中距离过近（< 0.3）。

**类型**：Type-4 语义违规。

**影响**：搜索结果可能将语义相反的文档混在一起，降低搜索质量。

**根因**：Embedding模型在训练时未充分考虑语义对立关系。

### 6.2 IDX-004 索引重建幂等性问题

**发现**：Milvus v2.6强制"每个字段最多一个索引"，直接rebuild失败。

**修复**：改为 `drop_index()` → `create_index()` 流程。

### 6.3 Embedding离线加载Bug

**发现**：`_hf_cache_has_model` 中 `Path("")` 展开为当前目录导致缓存检测失败。

**修复**：正确处理空字符串HF_HOME环境变量。

---

## 七、未来演进方向

### 7.1 短期

- 完成IDX-003/004索引行为合约测试
- 细化Oracle近似容忍阈值
- 增强诊断质量检测

### 7.2 中期

- 扩展至Qdrant、Weaviate、Pinecone
- 增加性能回归测试
- 支持分布式部署测试

### 7.3 长期

- 演化为通用AI数据库QA框架
- 支持向量、图、时序、键值多模数据库
- 提供SaaS化测试服务

---

**文档维护**: 本文档随项目迭代持续更新  
**最后更新**: 2026-03-16  
**理论体系版本**: 2.0
