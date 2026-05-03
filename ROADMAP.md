# myAgent Roadmap: Building an Autonomous Coding Agent

> Goal: Build a coding agent that can autonomously develop complete projects using local 8B/9B models
> Reference: Claude Code open-source architecture

---

## Overall Architecture

```mermaid
flowchart TD
    subgraph UserLayer["User Layer"]
        A[User Input Task]
    end

    subgraph AgentCore["Agent Core Loop"]
        B[Task Parsing]
        C[Task Planning]
        D[Execute Action]
        E[Observe Reflect]
        F{Task Complete?}
        G[Self-Correction]
        H[Verify]
    end

    subgraph ToolLayer["Tool Layer"]
        I1[File Operations]
        I2[Code Execution]
        I3[Search Tools]
        I4[Git Operations]
        I5[MCP Tools]
        I6[Network Tools]
    end

    subgraph ModelLayer["Model Layer"]
        J1[Ollama Local]
        J2[OpenAI Compatible]
    end

    A --> B
    B --> C
    C --> D
    D --> I1 & I2 & I3 & I4 & I5 & I6
    I1 & I2 & I3 & I4 & I5 & I6 --> E
    E --> F
    F -- No --> G
    G --> C
    F -- Yes --> H
    H --> I[Output Result]

    D --> J1 & J2
```

---

## Phase 1: Core Agent Architecture Enhancement

### 1.1 Multi-Round Planning Loop (Plan → Act → Reflect)

```mermaid
flowchart LR
    subgraph PlanPhase["Plan Phase"]
        P1[Decompose Task]
        P2[Identify Dependencies]
        P3[Generate Execution Plan]
    end

    subgraph ActPhase["Act Phase"]
        A1[Select Tool]
        A2[Execute Operation]
        A3[Get Result]
    end

    subgraph ReflectPhase["Reflect Phase"]
        R1[Evaluate Result]
        R2{Success?}
        R3[Summarize Experience]
    end

    subgraph RevisePhase["Revise Phase"]
        V1[Analyze Error]
        V2[Adjust Strategy]
        V3[Replan]
    end

    P1 --> P2 --> P3
    P3 --> A1 --> A2 --> A3
    A3 --> R1 --> R2
    R2 -- Yes --> R3
    R2 -- No --> V1 --> V2 --> V3
    V3 --> P1
```

### 1.2 Task Queue and Subtask Decomposition

```mermaid
flowchart TD
    T1[Main Task] --> T2[Decompose to Subtask Queue]
    T2 --> T3[Subtask 1]
    T2 --> T4[Subtask 2]
    T2 --> T5[Subtask N]

    T3 --> T3A[Execute] --> T3B{Complete?}
    T4 --> T4A[Execute] --> T4B{Complete?}
    T5 --> T5A[Execute] --> T5B{Complete?}

    T3B -- No --> E1[Error Correction] --> T3A
    T4B -- No --> E2[Error Correction] --> T4A
    T5B -- No --> E3[Error Correction] --> T5A

    T3B -- Yes --> C1[Mark Complete]
    T4B -- Yes --> C2[Mark Complete]
    T5B -- Yes --> C3[Mark Complete]

    C1 & C2 & C3 --> T6[Verify Overall]
    T6 --> T7[Deliver Result]
```

### 1.3 Self-Correction Mechanism

```mermaid
flowchart TD
    E[Execution Failed] --> E1[Error Classification]
    E1 --> C1{Syntax Error?}
    E1 --> C2{Logic Error?}
    E1 --> C3{Tool Error?}
    E1 --> C4{Model Hallucination?}

    C1 --> A1[Fix Syntax]
    C2 --> A2[Redesign Logic]
    C3 --> A3[Check Tool Parameters]
    C4 --> A4[Verify Assumptions]

    A1 --> R[Retry]
    A2 --> R
    A3 --> R
    A4 --> R
    R --> E
```

### 1.4 Structured Tool Calling

```mermaid
flowchart LR
    subgraph LLMOutput["LLM Structured Output"]
        O1[JSON Schema]
        O2[Tool Call Format]
    end

    subgraph Validation["Input Validation"]
        V1[Pydantic Validation]
        V2[Required Field Check]
        V3[Type Check]
    end

    subgraph ToolExecution["Tool Execution"]
        T1[Route to Tool]
        T2[Execute Operation]
        T3[Capture Result]
    end

    O1 --> V1 --> V2 --> V3
    V3 --> T1 --> T2 --> T3
    T3 --> E{Success?}
    E -- No --> R[Return Error]
    E -- Yes --> S[Return Observation]
```

---

## Phase 2: Claude Code Core Features

### 2.1 MCP Integration Architecture

```mermaid
flowchart TD
    subgraph MCPEcosystem["MCP Ecosystem"]
        M1[MCP Server 1]
        M2[MCP Server 2]
        M3[MCP Server N]
    end

    subgraph MCPClient["MCP Client"]
        MC1[Connection Management]
        MC2[Protocol Parsing]
        MC3[Tool Discovery]
    end

    subgraph ToolRegistry["Tool Registry"]
        TR1[Dynamic Loading]
        TR2[Unified Interface]
        TR3[Result Standardization]
    end

    M1 & M2 & M3 --> MC1
    MC1 --> MC2 --> MC3
    MC3 --> TR1 --> TR2 --> TR3
```

### 2.2 Process Monitoring

```mermaid
flowchart TD
    subgraph MonitorTrigger["Monitor Trigger"]
        W1[Manual Trigger /watch]
        W2[Auto Trigger]
    end

    subgraph MonitorLoop["Monitor Loop"]
        M1[Check Process Status]
        M2[Capture Output]
        M3[Detect Error Patterns]
        M4[Log]
    end

    subgraph ResponseHandling["Response Handling"]
        R1{Problem Found?}
        R2[Notify Agent]
        R3[Suggest Fix]
    end

    W1 & W2 --> M1 --> M2 --> M3 --> M4
    M4 --> R1
    R1 -- Yes --> R2 --> R3
    R1 -- No --> Continue
```

---

## Phase 3: Small Model Adaptation

### 3.1 Chain-of-Thought Prompt Templates

```mermaid
flowchart LR
    subgraph FewShot["Few-shot Examples"]
        F1[Example 1: Task Decomposition]
        F2[Example 2: Tool Selection]
        F3[Example 3: Error Recovery]
    end

    subgraph CoTTemplate["Chain-of-Thought"]
        C1[Problem Understanding]
        C2[Decompose Steps]
        C3[Tool Planning]
        C4[Execute Verify]
    end

    F1 & F2 & F3 --> C1 --> C2 --> C3 --> C4
```

### 3.2 Fallback Strategies

```mermaid
flowchart TD
    subgraph MainFlow["Main Flow"]
        M1[Structured JSON Output]
        M2[Pydantic Validation]
    end

    subgraph Fallback1["Fallback 1"]
        D1[Regex Extraction]
        D1T[Try Extract JSON]
    end

    subgraph Fallback2["Fallback 2"]
        D2[Simplified Instructions]
        D2T[Use Simpler Prompt]
    end

    subgraph Fallback3["Fallback 3"]
        D3[Default Operation]
        D3T[Execute Safe Default]
    end

    M2 -- Failed --> D1 --> D1T
    D1T -- Failed --> D2 --> D2T
    D2T -- Failed --> D3 --> D3T
```

---

## Phase 4: Validation and Iteration

```mermaid
flowchart TD
    subgraph TestLayers["Test Layers"]
        T1[Unit Tests]
        T2[Integration Tests]
        T3[E2E Tests]
    end

    subgraph ProjectValidation["Project Validation"]
        P1[Functionality Completeness]
        P2[Code Quality]
        P3[Runnability]
    end

    subgraph Benchmark["Performance Benchmark"]
        B1[Execution Time]
        B2[Tool Call Count]
        B3[Success Rate]
    end

    T1 & T2 & T3 --> P1 & P2 & P3
    P1 & P2 & P3 --> B1 & B2 & B3
```

---

## Implementation Priority

| Priority | Phase | Task | Estimated Time |
|----------|-------|------|----------------|
| P0 | Phase 1 | Refactor Agent loop to Plan/Act/Reflect | 2-3 days |
| P0 | Phase 1 | Implement task queue and decomposition | 1-2 days |
| P1 | Phase 1 | Self-correction mechanism | 1-2 days |
| P1 | Phase 1 | Enhance structured output | 1 day |
| P2 | Phase 2 | MCP client integration | 2-3 days |
| P2 | Phase 2 | Process monitoring | 1-2 days |
| P3 | Phase 3 | Small model adaptation | Ongoing |
| P3 | Phase 4 | Testing and validation | Ongoing |

---

## File Structure

```
myAgent/
├── main.py                 # Entry point
├── agent/
│   ├── __init__.py
│   ├── engine.py          # Agent core engine (Plan/Act/Reflect)
│   ├── planner.py         # Task planning and decomposition
│   ├── executor.py        # Tool executor
│   ├── reflector.py       # Result reflection and correction
│   └── tools/
│       ├── __init__.py
│       ├── base.py        # Tool base class
│       ├── file_tools.py  # File operations
│       ├── exec_tools.py  # Execution tools
│       ├── search_tools.py # Search tools
│       ├── git_tools.py   # Git operations
│       ├── test_tools.py  # Test tools
│       ├── quality_tools.py # Quality tools
│       ├── dependency_tools.py # Dependency tools
│       ├── deploy_tools.py # Deployment tools
│       └── mcp_tools.py   # MCP integration
├── cli/
│   └── michael.py         # CLI interface
├── memory/                 # External memory
│   ├── state_manager.py  # Progress & checkpoints
│   ├── embedding_store.py # Embedding storage
│   └── external_memory.py # Workflow orchestrator
├── utils/
│   ├── model_provider.py  # Multi-provider (Ollama, OpenAI, Anthropic)
│   ├── llm_cache.py      # LLM response caching
│   ├── cost_tracker.py   # Cost tracking
│   └── persistent_memory.py
├── skills/                # Built-in skills
│   └── registry.py
└── tests/
```

---

*Last Updated: 2026-04-21*

---

## Modular Refactoring (2026-04-21)

Refactored code according to ROADMAP structure, new modules:

| Module | Status | Description |
|--------|--------|-------------|
| `agent/tools/` | ✅ | Tool modularization |
| `agent/tools/base.py` | ✅ | Base tool class |
| `agent/tools/file_tools.py` | ✅ | File operation tools |
| `agent/tools/exec_tools.py` | ✅ | Execution tools |
| `agent/tools/search_tools.py` | ✅ | Search tools |
| `agent/tools/git_tools.py` | ✅ | Git operation tools |
| `agent/tools/test_tools.py` | ✅ | Test tools |
| `agent/tools/quality_tools.py` | ✅ | Quality tools |
| `agent/tools/dependency_tools.py` | ✅ | Dependency tools |
| `agent/tools/deploy_tools.py` | ✅ | Deploy tools |
| `agent/tools/mcp_tools.py` | ✅ | MCP tools |
| `utils/llm_cache.py` | ✅ | LLM response caching |
| `utils/cost_tracker.py` | ✅ | Cost tracking |
| `agent/coordinator.py` | ✅ | Multi-agent coordination |

## Current Progress

### ✅ Completed

| Phase | Content | Completion Date |
|-------|---------|-----------------|
| Phase 1 | Agent core architecture (Plan/Act/Reflect) | 2026-04-20 |
| Phase 2.1 | Interactive CLI | 2026-04-20 |
| Phase 2.2 | MCP client integration | 2026-04-21 |
| Phase 2.3 | Process monitoring (/watch) | 2026-04-21 |
| Phase 2.4 | Skills system | 2026-04-21 |
| Phase 3 | Small model adaptation (CoT prompts + fallback) | 2026-04-21 |
| Phase 4.1 | Unit tests + Integration tests | 2026-04-20 |
| Phase 4.2 | E2E tests | 2026-04-20 |
| Phase 4.3 | Performance benchmarks | 2026-04-20 |
| Layer 1 | External Memory System - Core Interface | 2026-04-27 |
| Layer 3 | External Memory System - ChromaDB + Ollama Embeddings | 2026-04-28 |

### ⏳ Pending

- None

### 📊 Test Coverage

```
tests/
├── test_agent.py           # Agent core functionality tests
├── test_llm_models.py      # LLM model capability tests
├── test_phase3_small_model.py  # Small model optimization tests
├── test_skills_models.py   # Skills system tests
├── test_phase4_validation.py   # Phase 4 validation tests
├── test_memory_interface.py   # Memory interface tests
└── test_e2e.py             # End-to-end tests
```

---

## Skills System (Implemented)

```mermaid
flowchart TD
    subgraph SkillRegistry["Skill Registry"]
        R1[SkillRegistry]
        R2[BaseSkill]
    end

    subgraph BuiltInSkills["Built-in Skills"]
        S1["code-review<br/>Code Review"]
        S2["security-review<br/>Security Review"]
        S3["simplify<br/>Code Simplify"]
        S4["init<br/>Initialize Docs"]
    end

    subgraph CLICommands["CLI Commands"]
        C1["code-review"]
        C2["security-review"]
        C3["simplify"]
        C4["init"]
    end

    R1 --> S1 & S2 & S3 & S4
    S1 --> C1
    S2 --> C2
    S3 --> C3
    S4 --> C4
```

### Built-in Skills

| Command | Function |
|---------|----------|
| `/code-review` | Code review (TODO/FIXME, debug statements, empty exceptions) |
| `/security-review` | Security scan (hardcoded passwords, SQL injection, shell injection) |
| `/simplify` | Code refactoring (duplicate code, long functions) |
| `/init` | Initialize CLAUDE.md project documentation |

---

## External Memory System - Layer 1 Implementation Plan

> Based on Codex review feedback, using strategic shortcuts: minimal memory interface + mock embeddings, real vector search deferred to Layer 3

**Architecture Decisions:**
1. Minimal memory interface prioritized over storage and embeddings
2. Using mock embeddings for MVP, real Ollama embeddings deferred
3. File append storage (no indexing), migrate to vector DB later

**Implementation Scope (Layer 1):**
- ✅ Memory interface: `remember()` and `recall()` methods
- ✅ Memory schema: Session metadata capture (files, tags, summaries)
- ✅ Append storage: JSON files under `memory/sessions/`
- ✅ `/search` CLI command (using mock embeddings)
- ✅ Auto-capture: Hook into `AgentEngine` task_complete phase

**Layer 3 Implementation (Completed 2026-04-28):**
- ✅ ChromaDB / Vector DB integration
- ✅ Real Ollama embedding generation (nomic-embed-text)
- ✅ Memory cleanup and expiration strategies
- ✅ Semantic similarity search

**Layer 3 Architecture:**
1. ChromaDB PersistentClient for vector storage with cosine similarity
2. OllamaEmbeddings class using nomic-embed-text model
3. MemoryCleanupPolicy with age-based and access-based cleanup
4. Hybrid search combining semantic (ChromaDB) and keyword matching

**Out of Layer 3 Scope (Future Layers):**
- ⏳ Cross-session memory linking and graph relationships
- ⏳ Importance scoring based on task outcomes
- ⏳ Memory summarization and compression

**File Changes (Layer 3):**
| File | Operation |
|------|-----------|
| `memory/embedding_store.py` | Complete rewrite with ChromaDB + Ollama embeddings |
| `memory/chroma_db/` | New ChromaDB persistent storage |

**Test Plan (Layer 3):**
- Semantic search accuracy testing
- Cleanup policy verification
- Ollama embedding fallback handling

**File Changes:**
| File | Operation |
|------|-----------|
| `memory/state_manager.py` | Extended richer metadata + retrieval API |
| `memory/embedding_store.py` | New (mock embeddings + text fallback) |
| `memory/external_memory.py` | Enhanced auto-capture |
| `agent/engine.py` | Hooked auto-capture |
| `cli/michael.py` | Added `/search` command |
| `utils/model_provider.py` | Reserved `get_embeddings()` interface |

**Test Plan:**
- `tests/test_memory_interface.py` - Memory interface + mock embeddings
- `tests/test_session_capture.py` - Session metadata capture
- `tests/test_search_flow.py` - /search command flow

**Risk Mitigation:**
- Embedding failure → Text keyword search fallback
- Storage corruption → Rebuild from session logs

*Last Updated: 2026-04-27*
