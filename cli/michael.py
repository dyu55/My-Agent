"""
MyAgent CLI - Claude Code 风格的交互式编程 Agent

交互模式:
    ./michael                      # 启动交互式 CLI
    >>> 实现用户登录功能
    >>> 帮我添加注册页面
    >>> /task 添加支付模块

命令:
    /task <描述>    执行任务（也可以直接输入任务描述）
    /edit <文件>    编辑文件
    /read <文件>    读取文件
    /run <命令>     执行命令
    /test          运行测试
    /git <args>    Git 操作
    /status        显示状态
    /help          显示帮助
    /exit          退出

快捷键:
    Ctrl+C         取消当前任务
    Ctrl+D         退出
"""

import os
import readline
import sys
from pathlib import Path
from typing import Optional

from agent import AgentEngine
from agent.engine import AgentConfig
from agent.external_memory_integration import create_external_memory_manager


class MichaelCLI:
    """
    Claude Code 风格的交互式 CLI。

    特点:
    - 任务优先: 直接输入任务描述即可执行
    - 智能编辑: Agent 自动决定如何修改文件
    - 进度跟踪: 显示任务执行进度
    - 自动测试: 任务完成后自动运行测试
    - Git 集成: 自动保存更改
    """

    BANNER = """
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║   🤖 Michael - 本地 Coding Agent                                           ║
║                                                                            ║
║   输入任务描述即可执行，例如:                                               ║
║   → "实现用户登录功能"                                                      ║
║   → "帮我重构 auth.py 模块"                                                 ║
║   → "添加单元测试覆盖率"                                                    ║
║                                                                            ║
║   命令: /help 查看所有命令                                                  ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
"""

    def __init__(
        self,
        workspace: Path | str = "workspace",
        model: str = "gemma4:latest",
        provider: str = "ollama",
        base_url: str = "http://localhost:11434",
        api_key: Optional[str] = None,
    ):
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)

        self.model = model
        self.provider = provider
        self.base_url = base_url
        self.api_key = api_key

        self.agent: Optional[AgentEngine] = None
        self.external_memory = create_external_memory_manager(str(self.workspace))

        self.is_running = False
        self.current_task: Optional[str] = None
        self.task_count = 0

        self._init_agent()

    def _init_agent(self) -> None:
        """初始化 Agent"""
        config = AgentConfig(
            workspace=self.workspace,
            model=self.model,
            provider=self.provider,
            base_url=self.base_url,
            api_key=self.api_key,
            trace_enabled=True,
        )
        self.agent = AgentEngine(config)

    def run(self) -> None:
        """启动交互式 CLI"""
        self.is_running = True
        print(self.BANNER)
        print(f"📦 Model: {self.model} ({self.provider})")
        print(f"📁 Workspace: {self.workspace}\n")

        self._setup_readline()

        while self.is_running:
            try:
                user_input = self._read_input()
                if not user_input:
                    continue

                self._process_input(user_input)

            except KeyboardInterrupt:
                print("\n⚠️  输入 /exit 退出，或直接输入新任务继续")
            except EOFError:
                print("\n再见!")
                break
            except Exception as e:
                print(f"\n❌ 错误: {e}")

        self.is_running = False

    def _setup_readline(self) -> None:
        """Setup readline"""
        try:
            readline.parse_and_bind("tab: complete")
            readline.parse_and_bind("set editing-mode vi")
        except Exception:
            pass

    def _read_input(self) -> str:
        """读取输入"""
        try:
            prompt = f"🎯 " if not self.current_task else f"🔄 "
            return input(prompt).strip()
        except (KeyboardInterrupt, EOFError):
            raise

    def _process_input(self, user_input: str) -> None:
        """处理输入"""
        user_input = user_input.strip()
        if not user_input:
            return

        # 命令模式
        if user_input.startswith("/"):
            self._handle_command(user_input)
            return

        # 直接执行任务（最常用场景）
        self._execute_task(user_input)

    def _handle_command(self, user_input: str) -> None:
        """处理命令"""
        parts = user_input.split(maxsplit=1)
        cmd = parts[0].lstrip("/").lower()
        args = parts[1] if len(parts) > 1 else ""

        handlers = {
            "task": self._cmd_task,
            "t": self._cmd_task,
            "edit": self._cmd_edit,
            "read": self._cmd_read,
            "run": self._cmd_run,
            "test": self._cmd_test,
            "git": self._cmd_git,
            "status": self._cmd_status,
            "help": self._cmd_help,
            "h": self._cmd_help,
            "exit": self._cmd_exit,
            "quit": self._cmd_exit,
            "q": self._cmd_exit,
            # 外部记忆模式命令
            "em": self._cmd_external_memory,
            "external-memory": self._cmd_external_memory,
            "memory": self._cmd_external_memory,
            "mem": self._cmd_external_memory,
        }

        handler = handlers.get(cmd)
        if handler:
            handler(args)
        else:
            print(f"❌ 未知命令: /{cmd}")
            print("   输入 /help 查看可用命令")

    def _execute_task(self, task: str) -> None:
        """执行任务"""
        self.task_count += 1
        self.current_task = task

        print(f"\n{'='*70}")
        print(f"🚀 任务 #{self.task_count}: {task}")
        print(f"{'='*70}\n")

        try:
            # 开始外部记忆工作流
            self.external_memory.start_workflow(task)

            # 执行任务
            result = self.agent.run(task)

            # 添加检查点
            self.external_memory.add_checkpoint(
                "write_code",
                "success",
                f"任务完成: {task[:50]}",
                {"result": result[:200] if result else ""}
            )

            print(f"\n{'='*70}")
            print(f"✅ 任务完成")
            print(f"{'='*70}")
            print(f"📊 结果: {result}")

            # 自动询问是否提交
            self._prompt_git_commit()

        except KeyboardInterrupt:
            print("\n\n⚠️  任务已取消")
            self.external_memory.add_checkpoint(
                "write_code",
                "cancelled",
                "任务被用户取消",
                {}
            )
        except Exception as e:
            print(f"\n❌ 任务执行失败: {e}")
            self.external_memory.add_checkpoint(
                "write_code",
                "failed",
                f"任务失败: {str(e)}",
                {}
            )
        finally:
            self.current_task = None

    def _prompt_git_commit(self) -> None:
        """提示用户是否提交"""
        print("\n是否提交更改? (y/n): ", end="")
        try:
            response = input().strip().lower()
            if response == "y":
                result = self.external_memory.commit()
                print(f"✅ 已提交: {result.get('summary', 'OK')}")
        except (KeyboardInterrupt, EOFError):
            pass

    # ==================== 命令处理 ====================

    def _cmd_task(self, args: str) -> None:
        """执行任务"""
        if not args:
            print("用法: /task <任务描述>")
            return
        self._execute_task(args)

    def _cmd_edit(self, args: str) -> None:
        """编辑文件"""
        if not args:
            print("用法: /edit <文件路径>")
            return
        file_path = self.workspace / args
        if not file_path.exists():
            print(f"❌ 文件不存在: {args}")
            return
        print(f"📝 读取文件: {file_path}")
        print(file_path.read_text(encoding="utf-8")[:1000])

    def _cmd_read(self, args: str) -> None:
        """读取文件"""
        self._cmd_edit(args)

    def _cmd_run(self, args: str) -> None:
        """执行命令"""
        if not args:
            print("用法: /run <命令>")
            return
        print(f"\n⚡ 执行: {args}\n")
        import subprocess
        try:
            result = subprocess.run(
                args,
                shell=True,
                capture_output=True,
                text=True,
                cwd=str(self.workspace),
                timeout=60,
            )
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(f"❌ Stderr: {result.stderr}")
            print(f"\n📊 Exit code: {result.returncode}")
        except subprocess.TimeoutExpired:
            print("❌ 命令超时 (60s)")
        except Exception as e:
            print(f"❌ 执行失败: {e}")

    def _cmd_test(self, args: str) -> None:
        """运行测试"""
        print("\n🧪 运行测试...\n")
        import subprocess
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "-v", "--tb=short"],
                capture_output=True,
                text=True,
                cwd=str(self.workspace),
                timeout=120,
            )
            print(result.stdout or result.stderr)
            if result.returncode == 0:
                print("✅ 所有测试通过!")
            else:
                print("❌ 有测试失败")
        except FileNotFoundError:
            print("❌ pytest 未安装")
        except Exception as e:
            print(f"❌ 测试失败: {e}")

    def _cmd_git(self, args: str) -> None:
        """Git 操作"""
        if not args:
            args = "status"
        print(f"\n🔀 Git: {args}\n")
        import subprocess
        try:
            result = subprocess.run(
                ["git"] + args.split(),
                capture_output=True,
                text=True,
                cwd=str(self.workspace),
                timeout=30,
            )
            print(result.stdout or result.stderr)
        except Exception as e:
            print(f"❌ Git 失败: {e}")

    def _cmd_status(self, args: str) -> None:
        """显示状态"""
        print(f"""
📊 Michael 状态
────────────────────
任务数: {self.task_count}
当前任务: {self.current_task or "无"}
模型: {self.model}
Provider: {self.provider}
Workspace: {self.workspace}
────────────────────
外部记忆: {'启用' if self.external_memory.is_enabled() else '禁用'}
""")

    def _cmd_help(self, args: str) -> None:
        """显示帮助"""
        print("""
📖 命令帮助

直接输入任务描述即可执行，例如:
  → 实现用户登录功能
  → 帮我添加注册页面

/命令:
  /task <描述>    执行任务
  /edit <文件>    查看文件
  /read <文件>    查看文件 (同 /edit)
  /run <命令>     执行 Shell 命令
  /test           运行 pytest
  /git <args>     Git 操作
  /status         显示状态
  /help           显示此帮助

快捷键:
  Ctrl+C          取消当前任务
  Ctrl+D          退出

外部记忆:
  /em start        开始外部记忆工作流
  /em status       查看工作流状态
  /em commit       提交更改
""")

    def _cmd_exit(self, args: str) -> None:
        """退出"""
        print("\n👋 再见!")
        self.is_running = False

    def _cmd_external_memory(self, args: str) -> None:
        """外部记忆模式命令"""
        parts = args.split() if args else []
        result = self.external_memory.handle_command(parts)
        print(result)

    def stop(self) -> None:
        """停止 CLI"""
        self.is_running = False


def main():
    """CLI 入口点"""
    import argparse

    parser = argparse.ArgumentParser(description="Michael - 本地 Coding Agent")
    parser.add_argument(
        "--model", "-m",
        default=os.environ.get("MODEL_NAME", "gemma4:latest"),
        help="模型名称"
    )
    parser.add_argument(
        "--provider", "-p",
        choices=["ollama", "rsxermu"],
        default=os.environ.get("ACTIVE_PROVIDER", "ollama"),
        help="Provider"
    )
    parser.add_argument(
        "--base-url", "-u",
        default=None,
        help="API Base URL"
    )
    parser.add_argument(
        "--workspace", "-w",
        default="workspace",
        help="工作目录"
    )
    parser.add_argument(
        "--api-key", "-k",
        default=None,
        help="API Key"
    )

    args = parser.parse_args()

    # 根据 provider 确定 base_url
    if args.base_url:
        base_url = args.base_url
    elif args.provider == "ollama":
        base_url = os.environ.get("OLLAMA_HOST", "http://192.168.0.124:11434")
    else:
        base_url = os.environ.get("RSXERMU_BASE_URL", "https://rsxermu666.cn")

    cli = MichaelCLI(
        workspace=args.workspace,
        model=args.model,
        provider=args.provider,
        base_url=base_url,
        api_key=args.api_key,
    )

    try:
        cli.run()
    except KeyboardInterrupt:
        print("\n再见!")


if __name__ == "__main__":
    main()