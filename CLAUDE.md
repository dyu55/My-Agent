# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Michael** is a local coding agent that uses small LLM models (8B/9B) running via Ollama to autonomously develop complete projects. Inspired by Claude Code architecture with Plan/Act/Reflect loop.

## Common Commands

```bash
# Run a task
python main.py "Create a TODO app"

# Interactive CLI mode
python main.py --chat

# Specify model/provider
python main.py --model qwen2.5:9b --provider ollama

# Run tests
pytest -v

# Run specific test
pytest tests/test_agent.py -v

# Install dependencies
pip install -r requirements.txt
```

## Architecture

### Core Agent Loop (Plan → Act → Reflect)

```
agent/engine.py          # Main AgentEngine orchestrating the loop
├── planner.py           # TaskPlanner - decomposes tasks into subtasks
├── executor.py          # ToolExecutor - executes actions via modular tools
└── reflector.py         # ResultReflector - analyzes errors, provides recovery suggestions
```

The agent uses `AgentConfig` (dataclass) for configuration and `AgentState` for tracking execution state.

### Modular Tool System

Tools are organized in `agent/tools/`:
- `file_tools.py` - write, edit, read, mkdir, list_dir, create_files
- `exec_tools.py` - execute, check_dependencies, run_tests, pip_install
- `search_tools.py` - search_files, search_web, fetch_url
- `git_tools.py` - git operations

### Model Providers

Unified model access via `utils/model_provider.py`:
- `ModelManager` - main interface for model selection/switching
- `OllamaProvider` - local models (default: gemma4:latest)
- `OpenAIProvider` - OpenAI API
- `AnthropicProvider` - Anthropic API

Factory pattern: `ModelProviderFactory.create(provider, **kwargs)`

### External Memory Mode

Long-running workflow with state persistence in `memory/`:
- `state_manager.py` - manages progress.json, sessions, checkpoints
- `external_memory.py` - workflow orchestrator (Read State → Write Code → Run Tests → Git Commit → Clear Context)
- `progress.json` - tracks features and tasks

### CLI Interface

`cli/michael.py` provides Claude Code-style interactive CLI:
- Direct task entry (no prefix needed)
- Commands: `/task`, `/edit`, `/read`, `/run`, `/test`, `/git`, `/status`, `/help`
- External memory integration via `/em` commands

## Configuration

Environment variables (see `.env.example`):
```bash
ACTIVE_PROVIDER=ollama           # ollama, openai, anthropic, rsxermu
MODEL_NAME=gemma4:latest        # model name
OLLAMA_HOST=http://192.168.0.124:11434  # Ollama server URL
RSXERMU_BASE_URL=...           # For rsxermu provider
RSXERMU_API_KEY=...             # API key for rsxermu
```

## Key Data Structures

- `ExecutionPlan` / `SubTask` - task decomposition with dependency tracking
- `Action` - represents a single tool execution
- `ExecutionResult` - result with status (SUCCESS/FAILURE/PARTIAL/SKIPPED)
- `Reflection` - error classification and recovery suggestions
- `ErrorCategory` enum: SYNTAX_ERROR, LOGIC_ERROR, TOOL_ERROR, MODEL_HALLUCINATION, DEPENDENCY_ERROR

## File Paths

- `workspace/` - default working directory for generated code
- `logs/` - execution trace logs
- `memory/` - external memory state
- `tests/` - pytest tests
