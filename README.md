# MyAgent - Local Coding Agent

> A coding agent that uses local 8B/9B models to autonomously develop complete projects. Inspired by Claude Code architecture with Plan/Act/Reflect loop and multi-layer external memory.

**GitHub**: [dyu55/My-Agent](https://github.com/dyu55/My-Agent)

## Features

### Core Agent Architecture

- 🤖 **Claude Code Style Interaction** - Type a task description to execute
- 🔄 **Plan/Act/Reflect Loop** - Task planning, execution, reflection, error recovery
- 🧠 **LLM Reflection** - Automatic error classification (5 categories) and recovery suggestions
- 📋 **Task Decomposition** - Subtask queue with dependency tracking
- 🔀 **Multi-Agent Coordination** - Parallel task execution with speedup measurement

### Memory System (Three-Layer Architecture)

| Layer | Component | Function |
|-------|-----------|----------|
| L1 | ConversationMemory | Short-term, auto-compression |
| L2 | Wiki + Embeddings | Long-term, semantic search |
| L3 | ChromaDB + Ollama | Vector storage, cross-session persistence |

- 🔍 **Semantic Search** - ChromaDB vector storage with `nomic-embed-text` embeddings
- 🧹 **MemoryCleanupPolicy** - Age-based and access-based cleanup strategies
- 📝 **Auto-capture** - Automatic task summaries with tags
- 💾 **State Persistence** - progress.json, checkpoints, session logs

### Modular Tool System

| Tool | Capabilities |
|------|--------------|
| `file_tools` | Read, write, edit, mkdir, glob, create_files |
| `exec_tools` | Shell commands, dependency check, pip install |
| `search_tools` | File search, web search, URL fetch |
| `git_tools` | Commit, push, branch, status |
| `test_tools` | Test discovery, pytest execution |
| `quality_tools` | Lint, type check, security scan |
| `deploy_tools` | Dockerfile, docker-compose, GitHub Actions |
| `mcp_tools` | Model Context Protocol support |
| `browser_tools` | Browser automation |
| `rollback_tools` | Safe rollback mechanism |

### Skills System

Parameterized skills with chaining, prerequisites, and template rendering:

| Command | Function |
|---------|----------|
| `/code-review` | Code review (TODO/FIXME, debug statements, bare except) |
| `/security-review` | Security scan (hardcoded passwords, SQL injection, shell injection) |
| `/simplify` | Code refactoring (duplicate code, long functions) |
| `/init` | Initialize CLAUDE.md project documentation |
| `/test-gen` | Auto-generate unit tests |
| `/api-design` | API design review |
| `/doc-gen` | Documentation generation |
| `/browser` | Browser automation |

**SkillEngine Features:**
- Parameter parsing with hyphen support (`--file-path`)
- Chain execution (multi-skill pipelines)
- Prerequisite validation
- Template rendering with context variables

### Multi-Model Support (2026 Lineup)

Factory pattern unified access with native thinking stream extraction:

- **Ollama** (default) - Local models (`gemma-4-31b-it`, `gemma-4-26b-a4b-it`, `qwen3.6-27b`)
- **Anthropic** - Claude API (`claude-opus-5-latest`, `claude-fable-5`, `claude-3-7-sonnet-latest`, `claude-3-5-haiku-20241022`)
- **OpenAI** - OpenAI API (`gpt-5.6-sol`, `gpt-5.5`, `o3-mini`, `o1`, `gpt-4o`)
- **Google Gemini** - Gemini API (`gemini-3.1-pro`, `gemini-3.7-flash`, `gemma-4-31b-it`)
- **DeepSeek** - DeepSeek API (`deepseek-v4-pro`, `deepseek-v4-flash`, `deepseek-reasoner`)
- **Ollama Cloud / Custom endpoints** - OpenAI-compatible APIs

### 2026 Coding Agent Enhancements

- 🗺️ **AST Repo Map** - Extracts Class/Function/Method signatures to provide project-wide architectural context within ~2k tokens.
- ✏️ **Fuzzy Search-and-Replace** - Multi-level fuzzy matching for code edits (whitespace-insensitive, difflib similarity) preventing unnecessary full file rewrites.
- ⚡ **Post-Edit Fast Static Diagnostics** - Sub-millisecond `ast.parse` syntax verification immediately after code edits for instant self-correction.
- 🧠 **Reasoning / Thinking Stream Decoupling** - Cleanly isolates `<think>` traces from Action JSON payloads.

## Quick Start

```bash
# Clone and install
git clone git@github.com:dyu55/My-Agent.git
cd My-Agent
pip install -r requirements.txt

# Interactive CLI mode
python main.py --chat

# Execute single task
python main.py "Create a TODO app"

# Specify model/provider
python main.py --provider ollama --model gemma-4-31b-it
```

## Project Structure

```
myAgent/
├── agent/                     # Agent core
│   ├── engine.py             # AgentEngine - Plan/Act/Reflect loop
│   ├── planner.py           # TaskPlanner - task decomposition
│   ├── executor.py          # ToolExecutor - action execution
│   ├── reflector.py         # ResultReflector - error classification
│   ├── coordinator.py       # Multi-agent coordination
│   ├── skills/              # Skills system
│   │   ├── skill_engine.py  # Parameterized skill execution
│   │   └── skill_templates.py # Skill scaffolding
│   └── tools/               # Modular tools
│       ├── file_tools.py    # File tools with Fuzzy Search-and-Replace
│       ├── repo_map.py      # AST-based project symbol map
│       ├── exec_tools.py
│       ├── search_tools.py
│       ├── git_tools.py
│       ├── test_tools.py
│       ├── quality_tools.py
│       ├── deploy_tools.py
│       ├── mcp_tools.py
│       ├── browser_tools.py
│       └── rollback_tools.py
├── cli/
│   ├── michael.py           # Claude Code style CLI
│   ├── interface.py
│   └── commands.py
├── memory/                   # External memory
│   ├── embedding_store.py   # Layer 3: ChromaDB + Ollama embeddings
│   ├── state_manager.py     # Progress tracking
│   ├── external_memory.py   # Workflow orchestrator
│   └── cross_session_memory.py
├── skills/                    # Skills registry
│   ├── registry.py          # SkillRegistry + BaseSkill
│   └── builtin/             # Built-in skills
│       ├── test_generation.py
│       ├── api_design.py
│       ├── doc_generation.py
│       └── browser_skill.py
├── utils/
│   ├── model_provider.py    # ModelProviderFactory
│   ├── llm_cache.py         # Response caching
│   ├── cost_tracker.py      # Usage monitoring
│   └── streaming_progress.py
├── mcp/                      # Model Context Protocol
├── tests/                    # pytest test suite
└── main.py                  # Entry point
```

## External Memory Workflow

```
┌──────────────────────────────────────────────────────────────┐
│                   External Memory Loop                       │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│   │ 1. READ     │ →  │ 2. WRITE    │ →  │ 3. TEST     │     │
│   │   STATE     │    │   CODE      │    │   CODE      │     │
│   └─────────────┘    └─────────────┘    └─────────────┘     │
│         ↑                                        │           │
│         │           ┌─────────────┐              ↓           │
│         └───────────│ 6. CLEAR    │ ← ┌─────────────┐       │
│                     │   CONTEXT   │   │ 4. GIT      │       │
│                     └─────────────┘   │   COMMIT    │       │
│                                        └─────────────┘       │
│                                              │               │
│                                              ↓               │
│                                        ┌─────────────┐       │
│                                        │ 5. UPDATE  │       │
│                                        │   PROGRESS │       │
│                                        └─────────────┘       │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

## Configuration

```bash
cp .env.example .env
```

Environment variables:

```bash
# Provider (ollama, openai, anthropic)
ACTIVE_PROVIDER=ollama

# Model (gemma4:latest, qwen2.5:9b, etc.)
MODEL_NAME=gemma4:latest

# Ollama endpoint
OLLAMA_HOST=http://localhost:11434

# Optional: Ollama Cloud API key
# OLLAMA_API_KEY=your-api-key
```

## Development

```bash
# Run all tests
pytest -v

# Run specific test suites
pytest tests/test_skill_engine.py -v
pytest tests/test_memory_interface.py -v

# Start interactive CLI
python main.py --chat
```

## Architecture Highlights

### Error Classification (5 Categories)

```
ErrorCategory:
├── SYNTAX_ERROR      → Fix syntax
├── LOGIC_ERROR       → Redesign logic
├── TOOL_ERROR        → Check tool parameters
├── MODEL_HALLUCINATION → Verify assumptions
└── DEPENDENCY_ERROR  → Check dependencies
```

### Data Structures

```python
ExecutionPlan / SubTask    # Task decomposition with dependencies
Action                     # Single tool execution
ExecutionResult            # SUCCESS / FAILURE / PARTIAL / SKIPPED
Reflection                 # Error classification + recovery suggestions
MemoryEntry               # Memory with embedding, tags, session_id
```

## Tech Stack

- **Runtime**: Python 3.13+
- **LLM**: Ollama (local), OpenAI, Anthropic
- **Vector DB**: ChromaDB + Ollama embeddings
- **Testing**: pytest (44+ test cases)
- **CLI**: Claude Code style interaction

## License

MIT License
