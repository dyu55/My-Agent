# myAgent - Local Coding Agent

> A coding agent that uses local 8B/9B models to autonomously develop complete projects. Inspired by Claude Code architecture.

## Features

### Core Capabilities
- 🤖 **Claude Code Style Interaction** - Just type a task description to execute
- 🔄 **Plan/Act/Reflect Loop** - Task planning, execution, reflection, error recovery
- 🧠 **LLM Reflection** - Automatic error classification and recovery suggestions

### Memory System
- 💾 **Three-Layer Memory Architecture**:
  - Layer 1: Conversation memory (short-term, auto-compression)
  - Layer 2: Wiki + Embedding store (long-term, semantic search)
  - Layer 3: State manager (progress tracking, checkpoints)
- 🔍 **Embedding-based Search** - Semantic similarity search across sessions
- 📝 **Auto-capture** - Automatic task summaries with tags

### Tools
- 📁 **File Operations** - Read, write, edit, create, delete files
- ⚡ **Code Execution** - Run shell commands, tests, Python scripts
- 🔎 **Search** - File content search, web search, URL fetch
- 🔀 **Git Integration** - Commit, push, branch operations
- 🧪 **Test Tools** - Discover tests, run pytest
- ✅ **Quality Tools** - Lint, type check, security scan, complexity analysis
- 📦 **Dependency Tools** - Import analysis, requirements generation
- 🚀 **Deploy Tools** - Dockerfile, docker-compose, GitHub Actions generation
- 🔌 **MCP Protocol** - Model Context Protocol support

### Workflow
- 💾 **External Memory Mode** - Persistent state across sessions
- 🔀 **Auto Git** - Automatic staging and commit
- 📋 **Progress Tracking** - Feature and task status monitoring
- 🔄 **State Recovery** - Resume from checkpoints

### Multi-Agent
- 🤝 **MultiAgent Coordinator** - Parallel task execution
- ⚡ **Speedup** - Parallel vs sequential execution comparison

### Optimization
- 💰 **LLM Cache** - Response caching for cost reduction
- 📊 **Cost Tracker** - Usage monitoring and optimization

## Quick Start

### Installation

```bash
# Clone the project
git clone git@github.com:dyu55/My-Agent.git
cd My-Agent

# Install dependencies
pip install -r requirements.txt

# Run
python main.py --chat
```

### Usage

```bash
# Start interactive CLI
python main.py --chat

# Execute single task
python main.py "Create a TODO app"

# Specify model
python main.py --model qwen2.5:9b

# Specify provider (ollama, openai, anthropic, rsxermu)
python main.py --provider ollama --model gemma4:latest
```

## Interactive Mode

```
🎯 Create user login functionality
🔄 Add a registration page
🔄 /task Add payment module
```

### Commands

| Command | Description |
|---------|-------------|
| `/task <desc>` | Execute task |
| `/edit <file>` | Edit file |
| `/read <file>` | Read file |
| `/run <cmd>` | Execute shell command |
| `/test` | Run pytest |
| `/git <args>` | Git operations |
| `/search <query>` | Search memories |
| `/status` | Show status |
| `/help` | Help |
| `/exit` | Exit |

## External Memory Mode

When context approaches the limit, the system will automatically prompt to enable external memory mode:

```
/em start          # Start workflow
/em commit         # Commit changes
/em complete       # Complete and clear context
/em search <query> # Search memories
```

### Three-Layer Memory

```
┌─────────────────────────────────────────────────────────┐
│  Layer 1: Conversation Memory (短期记忆)                 │
│  └── Auto-compression when approaching token limit       │
├─────────────────────────────────────────────────────────┤
│  Layer 2: Wiki Store + Embeddings (长期记忆)             │
│  └── Semantic search, auto-capture task summaries        │
├─────────────────────────────────────────────────────────┤
│  Layer 3: State Manager (项目状态)                       │
│  └── progress.json, checkpoints, session logs           │
└─────────────────────────────────────────────────────────┘
```

### Features

- 📋 **Progress Table** - Auto-tracks features and tasks
- 📝 **Session Logs** - Persistent execution history
- 🔀 **Git Integration** - Auto-save changes
- 💾 **State Recovery** - Resume from last interruption
- 🔍 **Semantic Search** - Embedding-based memory retrieval

## Project Structure

```
myAgent/
├── agent/                 # Agent core
│   ├── engine.py         # Agent engine (Plan/Act/Reflect)
│   ├── planner.py        # Task planning & decomposition
│   ├── executor.py       # Tool execution
│   ├── reflector.py      # Error classification & recovery
│   ├── coordinator.py   # Multi-agent coordination
│   └── tools/            # Modular tool system
│       ├── file_tools.py
│       ├── exec_tools.py
│       ├── search_tools.py
│       ├── git_tools.py
│       ├── test_tools.py      # Test discovery & execution
│       ├── quality_tools.py   # lint, type_check, security_scan
│       ├── dependency_tools.py
│       ├── deploy_tools.py    # Dockerfile, CI/CD
│       └── mcp_tools.py
├── cli/
│   └── michael.py        # Claude Code style CLI
├── memory/                # External memory
│   ├── state_manager.py # Progress & checkpoints
│   ├── embedding_store.py  # Embedding storage
│   └── external_memory.py  # Workflow orchestrator
├── wiki/                  # Long-term knowledge
│   ├── store.py
│   └── llm_wiki.py       # Auto-capture & tagging
├── skills/                # Built-in skills
│   └── registry.py
├── utils/
│   ├── model_provider.py # Multi-provider (Ollama, OpenAI, etc.)
│   ├── llm_cache.py      # Response caching
│   ├── cost_tracker.py   # Usage monitoring
│   └── persistent_memory.py
└── tests/
```

## Workflow

```
┌──────────────────────────────────────────────────────────────┐
│                    External Memory Loop                       │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│   │ 1. READ     │ →  │ 2. WRITE    │ →  │ 3. TEST     │     │
│   │   STATE     │    │   CODE      │    │   CODE      │     │
│   └─────────────┘    └─────────────┘    └─────────────┘     │
│         ↑                                        │           │
│         │           ┌─────────────┐              ↓           │
│         └───────────│ 6. CLEAR    │ ← ┌─────────────┐        │
│                     │   CONTEXT   │   │ 4. GIT      │        │
│                     └─────────────┘   │   COMMIT    │        │
│                                        └─────────────┘        │
│                                              │                │
│                                              ↓                │
│                                        ┌─────────────┐        │
│                                        │ 5. UPDATE  │        │
│                                        │   PROGRESS │        │
│                                        └─────────────┘        │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

## Configuration

Copy `.env.example` to `.env` and configure your provider:

```bash
cp .env.example .env
```

Supported providers: Ollama, OpenAI, Anthropic, rsxermu

## Development

```bash
# Run tests
pytest -v

# Run specific test
pytest tests/test_agent.py -v

# Start dev CLI
python main.py --chat
```

## License

MIT License