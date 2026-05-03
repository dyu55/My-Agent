#!/usr/bin/env python3
"""
MyAgent - Coding Agent with local 8B/9B models
Reference: Claude Code architecture

Usage:
    python main.py "你的任务描述"           # 执行单次任务
    python main.py --chat                  # 启动交互式 CLI
    python main.py --provider ollama "任务"
    python main.py --model qwen2.5:9b "任务"
"""

import argparse
import os
import sys
from pathlib import Path

from agent import AgentEngine, create_agent_from_env


def load_env_file(path: Path) -> None:
    """Load environment variables from .env file."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="MyAgent - Coding Agent with local models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python main.py "创建一个 TODO 应用"
    python main.py --chat                    # 交互式对话
    python main.py --chat --model qwen2.5:9b
    python main.py --model qwen2.5:9b "实现用户认证功能"
    python main.py --provider openai "重构代码并添加测试"
        """,
    )
    parser.add_argument(
        "task",
        nargs="?",
        default=None,
        help="The task to execute",
    )
    parser.add_argument(
        "--chat",
        "-c",
        action="store_true",
        help="Start interactive CLI mode (like Claude Code)",
    )
    parser.add_argument(
        "--model",
        "-m",
        help="Model to use (overrides MODEL_NAME env var)",
    )
    parser.add_argument(
        "--provider",
        "-p",
        choices=["ollama", "openai", "anthropic"],
        help="Provider to use (overrides ACTIVE_PROVIDER env var)",
    )
    parser.add_argument(
        "--workspace",
        "-w",
        default="workspace",
        help="Workspace directory (default: workspace)",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Max retries per task (default: 3)",
    )
    parser.add_argument(
        "--no-llm-reflection",
        action="store_true",
        help="Disable LLM-based reflection (faster but less accurate)",
    )
    parser.add_argument(
        "--list-providers",
        action="store_true",
        help="List available providers",
    )
    return parser.parse_args()


def list_providers() -> None:
    """List available providers."""
    print("Available providers:")
    print("  - ollama: Local Ollama server (default: http://localhost:11434)")
    print("  - openai: OpenAI API")
    print()
    print("Environment variables:")
    print("  OLLAMA_HOST: Ollama server URL (default: http://localhost:11434)")
    print("  MODEL_NAME: 模型名称 (默认: gemma4:latest)")
    print("  OPENAI_API_KEY: OpenAI API key")


def create_agent(args: argparse.Namespace) -> AgentEngine:
    """Create agent with given arguments."""
    from agent.engine import AgentConfig

    workspace = Path(args.workspace).resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    config = AgentConfig(
        workspace=workspace,
        model=args.model or os.environ.get("MODEL_NAME", "gemma4:latest"),
        provider=args.provider or os.environ.get("ACTIVE_PROVIDER", "ollama"),
        base_url=os.environ.get("OLLAMA_HOST", "http://localhost:11434"),
        api_key=os.environ.get("OPENAI_API_KEY"),
        max_task_retries=args.max_retries,
        enable_llm_reflection=not args.no_llm_reflection,
        trace_enabled=True,
    )

    return AgentEngine(config)


def run_cli(args: argparse.Namespace) -> int:
    """Run interactive CLI mode."""
    from cli import CLIInterface

    workspace = Path(args.workspace).resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    model = args.model or os.environ.get("MODEL_NAME", "gemma4:latest")
    provider = args.provider or os.environ.get("ACTIVE_PROVIDER", "ollama")

    if provider == "ollama":
        base_url = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    else:
        base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com")

    cli = CLIInterface(
        workspace=workspace,
        model=model,
        provider=provider,
        base_url=base_url,
        api_key=os.environ.get("OPENAI_API_KEY"),
    )

    try:
        cli.run()
        return 0
    except KeyboardInterrupt:
        print("\n再见!")
        return 0
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        return 1


def main() -> int:
    """Main entry point."""
    load_env_file(Path(__file__).parent / ".env")

    args = parse_args()

    # 交互式 CLI 模式
    if args.chat:
        return run_cli(args)

    if args.list_providers:
        list_providers()
        return 0

    task = args.task
    if not task:
        print("Error: No task provided.")
        print("Usage: python main.py \"your task description\"")
        print("       python main.py --chat  # 交互式对话")
        print("       python main.py --help for more options")
        return 1

    print(f"🚀 初始化 Agent...")
    print(f"   Provider: {args.provider or os.environ.get('ACTIVE_PROVIDER', 'ollama')}")
    print(f"   Model: {args.model or os.environ.get('MODEL_NAME', 'gemma4:latest')}")
    print(f"   Workspace: {args.workspace}")
    print()

    try:
        agent = create_agent(args)
        result = agent.run(task)
        print(f"\n✨ 完成: {result}")
        return 0
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
        return 130
    except Exception as e:
        print(f"\n\n❌ 错误: {e}")
        if os.environ.get("DEBUG"):
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())