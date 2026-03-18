# SBMF & CC 项目调研与 ai-db-qc 优化方向分析

**调研日期**: 2026-03-17  
**调研目标**: https://github.com/yihui504/SBMF 和 https://github.com/yihui504/CC

---

## 一、项目关系梳理

### 1.1 三个项目的演进关系

```
SBMF (Semantic Bug Mining Framework)
    │
    ├── 基础：Contract DSL + Agent驱动测试 + Fuzzing
    ├── 目标：SeekDB、Milvus、Weaviate 等向量数据库
    └── 成果：6个产品级Bug
            │
            ▼
CC (AI数据库Bug挖掘框架)  
    │
    ├── 继承：Contract-driven 理念
    ├── 改进：四类Bug检测体系 (Type-1/2/3/4)
    ├── 新增：六阶段流水线 (文档爬取→研究分析→优化处理→测试执行→验证确认→证据验证)
    └── 目标：Milvus、SeekDB
            │
            ▼
ai-db-qc (当前项目)
    │
    ├── 继承：Contract-driven 核心
    ├── 改进：多数据库适配器架构 (Milvus/Qdrant/Weaviate/pgvector)
    ├── 新增：16个合约、4个合约族 (ANN/Index/Schema/Hybrid)
    └── 成果：7个可提交Bug (DEF-001~007)
```

### 1.2 技术对比矩阵

| 维度 | SBMF | CC | ai-db-qc |
|------|------|-----|----------|
| **合约定义** | YAML DSL | YAML DSL | JSON + YAML |
| **测试生成** | Agent驱动 + Fuzzing | 六阶段流水线 | Contract-based生成 |
| **Bug分类** | 三值逻辑 | Type-1/2/3/4 | PASS/VIOLATION/ALLOWED_DIFFERENCE |
| **适配器** | SeekDB、Milvus、Weaviate | SeekDB、Milvus | Milvus、Qdrant、Weaviate、pgvector |
| **并发测试** | 支持 (55k ops/s) | 未明确 | 基础支持 (R7) |
| **证据链** | 基础 | 完整六阶段 | 完整 (precondition + oracle) |
| **论文支撑** | 未提及 | 未提及 | 进行中 |

---

## 二、SBMF 核心特性分析

### 2.1 技术优势

1. **Agent驱动测试**
   - 智能测试用例生成
   - 记忆管理（短期/长期/工作记忆）
   - 性能监控和异常检测

2. **智能Fuzzing**
   - 6种变异策略：RANDOM、BOUNDARY、ARITHMETIC、DICTIONARY、SPLICING、CROSSOVER
   - 反馈驱动的智能变异机制
   - 覆盖率导向的测试生成

3. **异常检测系统**
   - Z-score和IQR方法
   - 自适应阈值管理
   - 实时模式学习

4. **并发测试能力**
   - 竞态条件检测
   - 高并发场景（55,144 ops/s）

### 2.2 可借鉴点

| SBMF特性 | ai-db-qc应用建议 | 优先级 |
|----------|------------------|--------|
| Agent驱动测试 | 引入LLM Agent优化测试生成策略 | 中 |
| 6种Fuzzing策略 | 增强casegen的变异能力 | 高 |
| 异常检测(Z-score/IQR) | 替代/增强现有的简单阈值判断 | 中 |
| 高并发测试框架 | 完善R7并发压力测试 | 高 |
| AST-based Oracle | 增强oracle的可编程性 | 中 |

---

## 三、CC 核心特性分析

### 3.1 技术优势

1. **四类Bug检测体系**
   - Type-1: 非法操作成功 (HIGH)
   - Type-2: 错误不可诊断 (MEDIUM)  
   - Type-3: 合法操作失败 (HIGH)
   - Type-4: 语义违背 (MEDIUM)

2. **六阶段流水线**
   - 文档爬取 → 研究分析 → 优化处理 → 测试执行 → 验证确认 → 证据验证

3. **红线约束 (质量保证)**
   - R1: 禁止把DB特定参数写回contract
   - R2: 禁止放松门禁或oracle
   - R3: 禁止报告口径不一致
   - R4: Type-3/4必须precondition_pass=true
   - R5: 证据来源必须是官方文档

### 3.2 可借鉴点

| CC特性 | ai-db-qc应用建议 | 优先级 |
|--------|------------------|--------|
| 四类Bug分类 | 统一现有分类体系，与CC对齐 | 高 |
| 六阶段流水线 | 规范化测试执行流程 | 中 |
| 红线约束 | 建立质量保证检查清单 | 中 |
| 文档爬取 | 自动化contract与文档同步 | 低 |

---

## 四、ai-db-qc 当前状态评估

### 4.1 已完成优势

1. **多数据库支持**: Milvus、Qdrant、Weaviate、pgvector (SBMF/CC仅2-3个)
2. **合约体系完善**: 16个合约、4个合约族 (ANN/Index/Schema/Hybrid)
3. **Bug发现数量**: 7个可提交Bug (超过SBMF的6个)
4. **论文框架**: 已有完整论文结构 (SBMF/CC未提及)

### 4.2 相对短板

1. **测试生成智能化**: 缺乏SBMF的Agent驱动和Fuzzing策略
2. **并发测试深度**: 虽有R7但不如SBMF的55k ops/s框架完善
3. **异常检测**: 简单阈值 vs SBMF的Z-score/IQR
4. **Bug分类统一性**: 需要与CC的四类体系对齐
5. **流水线规范化**: 需要CC式的六阶段标准化流程

---

## 五、下一步优化方向 (按优先级排序)

### 5.1 高优先级 (立即执行)

#### 方向1: 完善并发测试框架 (借鉴SBMF)

**目标**: 建立可复用的并发测试基础设施，支持高ops/s压力测试

**具体任务**:
- 设计 CONC 合约族 (并发安全合约)
  - CONC-001: 并发插入后count一致性
  - CONC-002: 并发搜索不返回幽灵数据
  - CONC-003: 并发删除-搜索交叉一致性
- 实现 `scripts/run_concurrent_test.py` 通用并发测试框架
- 支持多线程/多进程并发模式
- 集成性能监控 (ops/s、延迟分布)

**预期产出**: 发现1-2个并发相关Bug，完善论文Evaluation章节

---

#### 方向2: 统一Bug分类体系 (借鉴CC)

**目标**: 与CC的四类Bug检测体系对齐，提升论文专业性

**具体任务**:
- 将现有7个DEF映射到CC分类:
  - DEF-001 (count延迟更新) → Type-4 (语义违背)
  - DEF-002 (动态字段不可见) → Type-4 (语义违背)
  - DEF-003 (过滤假阳性) → Type-4 (语义违背)
  - DEF-004 (混合schema count) → Type-4 (语义违背)
  - DEF-005 (pgvector过滤假阴性) → Type-4 (语义违背)
  - DEF-006 (Qdrant范围过滤) → Type-4 (语义违背)
  - DEF-007 (Weaviate过滤假阴性) → Type-4 (语义违背)
- 扩展测试发现Type-1/2/3类型Bug
- 更新所有issue文档和论文表格

**预期产出**: 论文Section 5表格标准化，与CC框架可比

---

#### 方向3: 增强Fuzzing能力 (借鉴SBMF)

**目标**: 引入6种变异策略，提升测试覆盖率

**具体任务**:
- 在 `casegen/` 模块实现6种变异策略:
  - RANDOM: 随机参数替换
  - BOUNDARY: 边界值测试 (min-1, min, max, max+1)
  - ARITHMETIC: 算术变异 (±1, ×2, ÷2)
  - DICTIONARY: 基于历史有效值的字典替换
  - SPLICING: 测试用例片段拼接
  - CROSSOVER: 多测试用例交叉组合
- 实现反馈驱动的智能选择机制
- 集成到现有pipeline

**预期产出**: 测试用例生成效率提升30%+，发现更多边界Bug

---

### 5.2 中优先级 (后续迭代)

#### 方向4: 引入Agent驱动测试 (借鉴SBMF)

**目标**: 使用LLM Agent优化测试策略选择和参数生成

**具体任务**:
- 设计Agent记忆系统 (短期/长期/工作记忆)
- 实现基于历史测试结果的学习机制
- 集成到test generator，动态调整测试策略

---

#### 方向5: 增强Oracle可编程性 (借鉴SBMF)

**目标**: 使用AST实现更灵活的验证逻辑

**具体任务**:
- 设计AST-based oracle表达式语言
- 支持复杂条件组合 (AND/OR/NOT)
- 支持数学表达式验证

---

#### 方向6: 异常检测升级 (借鉴SBMF)

**目标**: 用统计方法替代简单阈值

**具体任务**:
- 实现Z-score异常检测
- 实现IQR异常检测
- 支持自适应阈值调整

---

### 5.3 低优先级 (长期规划)

#### 方向7: 文档自动化 (借鉴CC)

**目标**: 自动化contract与官方文档同步

**具体任务**:
- 实现文档爬取模块
- 自动检测API变更
- 提示contract更新需求

---

#### 方向8: 六阶段流水线规范化 (借鉴CC)

**目标**: 建立标准化的测试执行流程

**具体任务**:
- 文档爬取 → 研究分析 → 优化处理 → 测试执行 → 验证确认 → 证据验证
- 每个阶段定义明确的输入输出
- 实现阶段间自动化流转

---

## 六、推荐执行路线图

```
Phase 1 (2-3周): 高优先级落地
├── Week 1-2: 并发测试框架 (CONC合约族 + run_concurrent_test.py)
├── Week 2-3: Bug分类统一 (映射7个DEF到CC分类，更新文档)
└── Week 3: Fuzzing增强 (6种变异策略实现)

Phase 2 (3-4周): 论文完善
├── 基于新发现的并发Bug更新Evaluation章节
├── 完善Case Study (加入并发场景)
└── 提交所有DEF到GitHub

Phase 3 (4-6周): 中优先级迭代
├── Agent驱动测试原型
├── AST-based Oracle
└── 统计异常检测

Phase 4 (长期): 生态建设
├── 文档自动化
├── 流水线规范化
└── 开源社区建设
```

---

## 七、关键决策建议

### 7.1 技术选型决策

| 决策项 | 建议 | 理由 |
|--------|------|------|
| 并发测试框架 | 独立实现，参考SBMF设计 | ai-db-qc多数据库适配器架构与SBMF不同，需要定制化 |
| Bug分类 | 完全对齐CC四类体系 | 提升论文专业性，便于与CC对比 |
| Fuzzing策略 | 移植SBMF的6种策略 | 策略与框架无关，可直接复用 |
| Agent驱动 | 暂缓，优先完善基础能力 | Agent是锦上添花，当前基础框架更重要 |

### 7.2 资源分配建议

- **60%精力**: 并发测试 + Bug分类统一 (论文核心支撑)
- **25%精力**: Fuzzing增强 (测试能力提升)
- **15%精力**: 其他优化方向

---

## 八、总结

通过对SBMF和CC的调研，发现ai-db-qc在**多数据库支持**和**Bug发现数量**上已超越前两者，但在**测试生成智能化**、**并发测试深度**、**Bug分类统一性**方面仍有提升空间。

**最核心的下一步**:
1. **立即执行**: 并发测试框架 (CONC合约族) - 这是ai-db-qc相对于SBMF/CC的明显短板，也是高价值Bug的潜在来源
2. **同步进行**: Bug分类与CC对齐 - 提升论文专业性和可比性
3. **持续优化**: Fuzzing策略增强 - 提升测试效率和覆盖率

这三项工作将直接支撑论文的Evaluation章节，并为框架的长期竞争力奠定基础。
