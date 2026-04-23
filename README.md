# Michael - Local Coding Agent

> A coding agent that uses local 8B/9B models to autonomously develop complete projects. Inspired by Claude Code architecture.

## Features

- 🤖 **Claude Code Style Interaction** - Just type a task description to execute
- 💾 **External Memory Mode** - Persistent logs + Git version control + Feature tracking
- 🔧 **Modular Tool System** - File operations, code execution, search, Git, MCP
- 🌐 **Multi-Provider Support** - Ollama, OpenAI compatible APIs
- 🔄 **Plan/Act/Reflect Loop** - Task planning, execution, reflection, error recovery
- 🧠 **LLM Reflection** - Automatic error classification and recovery suggestions

## Quick Start

### Installation

```bash
# Clone the project
git clone git@github.com:dyu55/My-Agent.git
cd My-Agent

# Install dependencies
pip install -r requirements.txt

# Configure Ollama (or use other providers)
export OLLAMA_HOST=http://192.168.0.124:11434
export MODEL_NAME=gemma4:latest
```

### Usage

```bash
# Start interactive CLI
michael

# Execute single task
michael "Create a TODO app"

# Specify model
michael -m qwen2.5:9b
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
| `/edit <file>` | View file |
| `/run <cmd>` | Execute shell command |
| `/test` | Run pytest |
| `/git <args>` | Git operations |
| `/status` | Show status |
| `/help` | Help |
| `/exit` | Exit |

## External Memory Mode

When context approaches the limit, the system will automatically prompt to enable external memory mode:

```
/em start          # Start workflow
/em commit         # Commit changes
/em complete       # Complete and clear context
```

### Features

- 📋 **Progress Table** - Auto-tracks features and tasks
- 📝 **Session Logs** - Persistent execution history
- 🔀 **Git Integration** - Auto-save changes
- 💾 **State Recovery** - Resume from last interruption

## Project Structure

```
MyAgent/
├── agent/                 # Agent core
│   ├── engine.py         # Agent engine
│   ├── planner.py        # Task planning
│   ├── executor.py       # Tool execution
│   ├── reflector.py      # Reflection & error recovery
│   └── external_memory_integration.py  # External memory
├── cli/                   # CLI
│   ├── michael.py        # Claude Code style CLI
│   └── interface.py      # Classic CLI
├── memory/                # External memory
│   ├── state_manager.py # State management
│   ├── external_memory.py  # Workflow
│   └── progress.json     # Progress table
├── skills/                # Built-in skills
│   ├── code-review       # Code review
│   ├── security-review   # Security review
│   └── simplify          # Code simplification
├── mcp/                   # MCP protocol
├── utils/                 # Utilities
└── tests/                 # Tests
```

## Workflow

```
┌─────────────┐
│ 1. Read State │ ← Load tasks from progress.json
├─────────────┤
│ 2. Write Code │ ← Agent executes tasks
├─────────────┤
│ 3. Run Tests │ ← pytest validation
├─────────────┤
│ 4. Git Commit │ ← Auto stage + commit
├─────────────┤
│ 5. Clear Context │ ← Persist and release
└─────────────┘
```

## Configuration

### Environment Variables

```bash
# Ollama
OLLAMA_HOST=http://192.168.0.124:11434
MODEL_NAME=gemma4:latest

# Or rsxermu
ACTIVE_PROVIDER=rsxermu
RSXERMU_BASE_URL=https://rsxermu666.cn
RSXERMU_API_KEY=your_key
```

### .env File

```bash
cp .env.example .env
# Edit .env with your configuration
```

## Development

```bash
# Run tests
pytest -v

# Run specific test
pytest tests/test_agent.py -v

# Start dev CLI
python main.py --chat
```

## Recommended Models

| Model | Parameters | Characteristics |
|-------|------------|------------------|
| gemma4:latest | 8B | Fast, fully on GPU |
| gemma4:26b | 26B | Capable, partial RAM |
| qwen2.5:9b | 9B | Chinese optimized |

## License

MIT License