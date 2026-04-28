# MyAgent 路线图：构建自主Coding Agent

> 目标：用本地 8B/9B 小模型实现能够自主开发完整项目的 Coding Agent
> 参考：Claude Code 开源代码架构

---

## 整体架构流程图

```mermaid
flowchart TD
    subgraph 用户层["用户层"]
        A[用户输入任务]
    end

    subgraph Agent核心["Agent 核心循环"]
        B[任务解析]
        C[任务规划 Plan]
        D[执行 Action]
        E[观察 Reflect]
        F{任务完成?}
        G[自我纠错 Revise]
        H[验证 Verify]
    end

    subgraph 工具层["工具层 Tools"]
        I1[文件操作]
        I2[代码执行]
        I3[搜索工具]
        I4[Git操作]
        I5[MCP工具]
        I6[网络工具]
    end

    subgraph 模型层["模型层"]
        J1[Ollama本地]
        J2[OpenAI兼容]
        J3[rsxermu]
    end

    A --> B
    B --> C
    C --> D
    D --> I1 & I2 & I3 & I4 & I5 & I6
    I1 & I2 & I3 & I4 & I5 & I6 --> E
    E --> F
    F -- 否 --> G
    G --> C
    F -- 是 --> H
    H --> I[输出结果]

    D --> J1 & J2 & J3
```

---

## Phase 1: 核心 Agent 架构增强

### 1.1 多轮规划循环 (Plan → Act → Reflect)

```mermaid
flowchart LR
    subgraph Plan阶段["Plan 阶段"]
        P1[分解任务]
        P2[识别依赖]
        P3[生成执行计划]
    end

    subgraph Act阶段["Act 阶段"]
        A1[选择工具]
        A2[执行操作]
        A3[获取结果]
    end

    subgraph Reflect阶段["Reflect 阶段"]
        R1[评估结果]
        R2{成功?}
        R3[总结经验]
    end

    subgraph Revise阶段["Revise 阶段"]
        V1[分析错误]
        V2[调整策略]
        V3[重新规划]
    end

    P1 --> P2 --> P3
    P3 --> A1 --> A2 --> A3
    A3 --> R1 --> R2
    R2 -- 是 --> R3
    R2 -- 否 --> V1 --> V2 --> V3
    V3 --> P1
```

### 1.2 任务队列与子任务分解

```mermaid
flowchart TD
    T1[主任务] --> T2[分解为子任务队列]
    T2 --> T3[子任务 1]
    T2 --> T4[子任务 2]
    T2 --> T5[子任务 N]

    T3 --> T3A[执行] --> T3B{完成?}
    T4 --> T4A[执行] --> T4B{完成?}
    T5 --> T5A[执行] --> T5B{完成?}

    T3B -- 否 --> E1[纠错] --> T3A
    T4B -- 否 --> E2[纠错] --> T4A
    T5B -- 否 --> E3[纠错] --> T5A

    T3B -- 是 --> C1[标记完成]
    T4B -- 是 --> C2[标记完成]
    T5B -- 是 --> C3[标记完成]

    C1 & C2 & C3 --> T6[验证整体]
    T6 --> T7[交付结果]
```

### 1.3 自我纠错机制

```mermaid
flowchart TD
    E[执行失败] --> E1[错误分类]
    E1 --> C1{语法错误?}
    E1 --> C2{逻辑错误?}
    E1 --> C3{工具错误?}
    E1 --> C4{模型幻觉?}

    C1 --> A1[修复语法]
    C2 --> A2[重新设计逻辑]
    C3 --> A3[检查工具参数]
    C4 --> A4[验证假设]

    A1 --> R[重试]
    A2 --> R
    A3 --> R
    A4 --> R
    R --> E
```

### 1.4 结构化工具调用

```mermaid
flowchart LR
    subgraph LLM输出["LLM 结构化输出"]
        O1[JSON Schema]
        O2[Tool Call格式]
    end

    subgraph 验证["输入验证"]
        V1[Pydantic验证]
        V2[必需字段检查]
        V3[类型检查]
    end

    subgraph 工具执行["工具执行"]
        T1[路由到工具]
        T2[执行操作]
        T3[捕获结果]
    end

    O1 --> V1 --> V2 --> V3
    V3 --> T1 --> T2 --> T3
    T3 --> E{执行成功?}
    E -- 否 --> R[返回错误信息]
    E -- 是 --> S[返回观测结果]
```

---

## Phase 2: Claude Code 核心功能

### 2.1 MCP 集成架构

```mermaid
flowchart TD
    subgraph MCP生态["MCP 生态系统"]
        M1[MCP Server 1]
        M2[MCP Server 2]
        M3[MCP Server N]
    end

    subgraph MCP客户端["MCP Client"]
        MC1[连接管理]
        MC2[协议解析]
        MC3[工具发现]
    end

    subgraph 工具注册["工具注册"]
        TR1[动态加载]
        TR2[统一接口]
        TR3[结果标准化]
    end

    M1 & M2 & M3 --> MC1
    MC1 --> MC2 --> MC3
    MC3 --> TR1 --> TR2 --> TR3
```

### 2.2 进程监控能力

```mermaid
flowchart TD
    subgraph 监控触发["监控触发"]
        W1[手动触发 /watch]
        W2[自动触发]
    end

    subgraph 监控循环["监控循环"]
        M1[检查进程状态]
        M2[捕获输出]
        M3[检测错误模式]
        M4[记录日志]
    end

    subgraph 响应处理["响应处理"]
        R1{发现问题?}
        R2[通知Agent]
        R3[建议修复]
    end

    W1 & W2 --> M1 --> M2 --> M3 --> M4
    M4 --> R1
    R1 -- 是 --> R2 --> R3
    R1 -- 否 --> 继续
```

---

## Phase 3: 小模型适配

### 3.1 Chain-of-Thought 提示模板

```mermaid
flowchart LR
    subgraph FewShot["Few-shot Examples"]
        F1[示例1: 任务分解]
        F2[示例2: 工具选择]
        F3[示例3: 错误恢复]
    end

    subgraph CoT模板["Chain-of-Thought"]
        C1[问题理解]
        C2[分解步骤]
        C3[工具规划]
        C4[执行验证]
    end

    F1 & F2 & F3 --> C1 --> C2 --> C3 --> C4
```

### 3.2 降级与回退策略

```mermaid
flowchart TD
    subgraph 主要流程["主要流程"]
        M1[结构化JSON输出]
        M2[Pydantic验证]
    end

    subgraph 降级1["降级策略 1"]
        D1[正则提取]
        D1T[尝试提取JSON]
    end

    subgraph 降级2["降级策略 2"]
        D2[简化指令]
        D2T[使用更简单的提示]
    end

    subgraph 降级3["降级策略 3"]
        D3[默认操作]
        D3T[执行安全默认操作]
    end

    M2 -- 失败 --> D1 --> D1T
    D1T -- 失败 --> D2 --> D2T
    D2T -- 失败 --> D3 --> D3T
```

---

## Phase 4: 验证与迭代

```mermaid
flowchart TD
    subgraph 测试分层["测试分层"]
        T1[单元测试]
        T2[集成测试]
        T3[E2E测试]
    end

    subgraph 项目验证["项目级验证"]
        P1[功能完整性]
        P2[代码质量]
        P3[可运行性]
    end

    subgraph 基准测试["性能基准"]
        B1[执行时间]
        B2[工具调用次数]
        B3[成功率]
    end

    T1 & T2 & T3 --> P1 & P2 & P3
    P1 & P2 & P3 --> B1 & B2 & B3
```

---

## 实现优先级

| 优先级 | 阶段 | 任务 | 预计时间 |
|--------|------|------|----------|
| P0 | Phase 1 | 重构 Agent 循环为 Plan/Act/Reflect | 2-3 天 |
| P0 | Phase 1 | 实现任务队列和分解 | 1-2 天 |
| P1 | Phase 1 | 自我纠错机制 | 1-2 天 |
| P1 | Phase 1 | 强化结构化输出 | 1 天 |
| P2 | Phase 2 | MCP 客户端集成 | 2-3 天 |
| P2 | Phase 2 | 进程监控能力 | 1-2 天 |
| P3 | Phase 3 | 小模型适配优化 | 持续 |
| P3 | Phase 4 | 测试和验证 | 持续 |

---

## 文件结构规划

```
MyAgent/
├── main.py                 # 入口
├── agent/
│   ├── __init__.py
│   ├── engine.py          # Agent 核心引擎 (Plan/Act/Reflect)
│   ├── planner.py         # 任务规划和分解
│   ├── executor.py        # 工具执行器
│   ├── reflector.py       # 结果反思和纠错
│   └── tools/
│       ├── __init__.py
│       ├── base.py        # 工具基类
│       ├── file_tools.py  # 文件操作
│       ├── exec_tools.py  # 执行工具
│       ├── search_tools.py # 搜索工具
│       └── mcp_tools.py   # MCP 集成
├── providers/
│   ├── __init__.py
│   ├── base.py           # Provider 基类
│   ├── ollama.py         # Ollama 实现
│   └── openai.py         # OpenAI 兼容
├── utils/
│   ├── __init__.py
│   ├── memory.py         # 对话记忆
│   ├── schema.py         # 结构化输出
│   └── logger.py         # 日志追踪
├── mcp/
│   ├── __init__.py
│   ├── client.py         # MCP 客户端
│   └── protocol.py      # MCP 协议
└── tests/
    ├── test_agent.py
    ├── test_tools.py
    └── test_e2e.py
```

---

*最后更新: 2026-04-21*

---

## 模块化重构 (2026-04-21)

根据 ROADMAP 结构重构代码，新增模块：

| 模块 | 状态 | 说明 |
|------|------|------|
| `agent/tools/` | ✅ | 工具模块化 |
| `agent/tools/base.py` | ✅ | 基础工具类 |
| `agent/tools/file_tools.py` | ✅ | 文件操作工具 |
| `agent/tools/exec_tools.py` | ✅ | 执行工具 |
| `agent/tools/search_tools.py` | ✅ | 搜索工具 |
| `agent/tools/git_tools.py` | ✅ | Git 操作工具 |
| `agent/tools/mcp_tools.py` | ✅ | MCP 工具 |
| `utils/memory.py` | ✅ | 对话记忆 |
| `utils/logger.py` | ✅ | 日志追踪 |
| `utils/schema.py` | ✅ | 结构化输出 |
| `mcp/protocol.py` | ✅ | MCP 协议定义 |

## 当前进度

### ✅ 已完成

| 阶段 | 内容 | 完成日期 |
|------|------|----------|
| Phase 1 | Agent 核心架构 (Plan/Act/Reflect) | 2026-04-20 |
| Phase 2.1 | 交互式 CLI | 2026-04-20 |
| Phase 2.2 | MCP 客户端集成 | 2026-04-21 |
| Phase 2.3 | 进程监控 (/watch) | 2026-04-21 |
| Phase 2.4 | Skills 系统 | 2026-04-21 |
| Phase 3 | 小模型适配优化 (CoT 提示 + 降级策略) | 2026-04-21 |
| Phase 4.1 | 单元测试 + 集成测试 | 2026-04-20 |
| Phase 4.2 | E2E 端到端测试 | 2026-04-20 |
| Phase 4.3 | 性能基准测试 | 2026-04-20 |

### ⏳ 待做

- 无

### 📊 测试覆盖

```
tests/
├── test_agent.py           # Agent 核心功能测试
├── test_llm_models.py      # LLM 模型能力测试
├── test_phase3_small_model.py  # 小模型优化测试
├── test_skills_models.py   # Skills 系统测试
├── test_phase4_validation.py   # Phase 4 验证测试 ⭐NEW
└── test_e2e.py             # 端到端测试 ⭐NEW
```

---

## Skills 系统 (已实现)

```mermaid
flowchart TD
    subgraph 技能注册["技能注册"]
        R1[SkillRegistry]
        R2[BaseSkill]
    end

    subgraph 内置技能["内置技能"]
        S1[code-review<br>代码审查]
        S2[security-review<br>安全审查]
        S3[simplify<br>代码简化]
        S4[init<br>初始化文档]
    end

    subgraph CLI命令["CLI 命令"]
        C1[/code-review]
        C2[/security-review]
        C3[/simplify]
        C4[/init]
    end

    R1 --> S1 & S2 & S3 & S4
    S1 --> C1
    S2 --> C2
    S3 --> C3
    S4 --> C4
```

### 内置 Skills

| 命令 | 功能 |
|------|------|
| `/code-review` | 代码审查（TODO/FIXME、调试语句、空异常等） |
| `/security-review` | 安全扫描（硬编码密码、SQL注入、shell注入等） |
| `/simplify` | 代码重构（重复代码、函数过长等） |
| `/init` | 初始化 CLAUDE.md 项目文档 |

---

## 外部记忆系统 - Layer 1 实现计划

> 基于 Codex 审查反馈，采用战略捷径：最小化内存接口 + 模拟嵌入，真实向量搜索延后至 Layer 3

**架构决策：**
1. 最小化内存接口优先于存储和嵌入
2. 使用模拟嵌入用于 MVP，真实 Ollama 嵌入延后
3. 文件追加存储（无索引），后期迁移到向量数据库

**实现范围（Layer 1）：**
- ✅ 内存接口：`remember()` 和 `recall()` 方法
- ✅ 内存 Schema：会话元数据捕获（文件、标签、摘要）
- ✅ 追加存储：`memory/sessions/` 下的 JSON 文件
- ✅ `/search` CLI 命令（使用模拟嵌入）
- ✅ 自动捕获：在 `AgentEngine` 的 `task_complete` 阶段钩入

**不在 Layer 1 范围内：**
- ❌ ChromaDB / 向量数据库（延后至 Layer 3）
- ❌ 真实 Ollama 嵌入生成（延后）
- ❌ 记忆清理和过期策略（延后）
- ❌ 语义相似度搜索（延后）

**文件变更：**
| 文件 | 操作 |
|------|------|
| `memory/state_manager.py` | 扩展 richer metadata + retrieval API |
| `memory/embedding_store.py` | 新建（模拟嵌入 + 文本回退） |
| `memory/external_memory.py` | 增强 auto-capture |
| `agent/engine.py` | 接入 auto-capture 钩子 |
| `cli/michael.py` | 新增 `/search` 命令 |
| `utils/model_provider.py` | 预留 `get_embeddings()` 接口 |

**测试计划：**
- `tests/test_memory_interface.py` - 内存接口 + 模拟嵌入
- `tests/test_session_capture.py` - 会话元数据捕获
- `tests/test_search_flow.py` - /search 命令流程

**风险缓解：**
- 嵌入失败 → 文本关键词搜索回退
- 存储损坏 → 从会话日志重建

*最后更新: 2026-04-27*
