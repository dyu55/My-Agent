"""External Memory Integration - 外部记忆模式集成到 AgentEngine。

提供外部记忆模式的上下文监控、自动提示、工作流管理功能。
这是一个简洁的实现，通过装饰器或组合模式集成到现有 AgentEngine。
"""

from typing import Any


class ExternalMemoryManager:
    """
    外部记忆管理器。

    组合模式：管理外部记忆相关功能，不直接修改 AgentEngine。
    """

    def __init__(self, workspace: str | None = None):
        from pathlib import Path

        self.workspace = Path(workspace) if workspace else Path("workspace")
        self.enabled = False
        self.threshold = 8000  # 触发提示的 token 数
        self.context_size = 0
        self.workflow = None
        self.prompted_user = False

        # 延迟导入
        self._state_manager = None
        self._workflow_class = None

    def _get_state_manager(self):
        """延迟加载 StateManager"""
        if self._state_manager is None:
            from memory.state_manager import StateManager
            self._state_manager = StateManager(
                state_dir=str(self.workspace / "memory"),
                session_logs_dir=str(self.workspace / "memory" / "session_logs")
            )
        return self._state_manager

    def _get_workflow_class(self):
        """延迟加载 ExternalMemoryWorkflow"""
        if self._workflow_class is None:
            from memory.external_memory import ExternalMemoryWorkflow
            self._workflow_class = ExternalMemoryWorkflow
        return self._workflow_class

    # ==================== 核心功能 ====================

    def enable(self) -> None:
        """启用外部记忆模式"""
        if not self.enabled:
            self.enabled = True
            print("\n🔄 外部记忆模式已启用")

    def disable(self) -> None:
        """禁用外部记忆模式"""
        self.enabled = False
        self.workflow = None
        self.prompted_user = False
        print("\n🔄 外部记忆模式已禁用")

    def is_enabled(self) -> bool:
        """检查是否启用"""
        return self.enabled

    def update_context(self, tokens: int) -> tuple[bool, str]:
        """
        更新上下文大小，检查是否需要提示。

        Args:
            tokens: 估算的 token 数

        Returns:
            (是否应该提示用户, 提示消息)
        """
        self.context_size = tokens

        if not self.enabled and not self.prompted_user:
            state_manager = self._get_state_manager()
            should_prompt, message = state_manager.should_prompt_user(tokens)
            if should_prompt:
                self.prompted_user = True
                return True, message
        return False, ""

    def should_checkpoint(self) -> bool:
        """检查是否应该创建检查点"""
        return self.enabled and self.workflow is not None

    def get_info(self) -> dict[str, Any]:
        """获取状态信息"""
        return {
            "enabled": self.enabled,
            "context_size": self.context_size,
            "threshold": self.threshold,
            "workflow_active": self.workflow is not None,
            "should_activate": self.context_size >= self.threshold
        }

    # ==================== 工作流控制 ====================

    def start_workflow(self, task_name: str) -> str | None:
        """开始外部记忆工作流"""
        if not self.enabled:
            self.enable()

        if self.workflow is None:
            workflow_class = self._get_workflow_class()
            self.workflow = workflow_class(workspace=self.workspace)

        session_id = self.workflow.start_workflow(
            task_name=task_name,
            context={"agent_session": True}
        )
        return session_id

    def add_checkpoint(
        self,
        phase: str,
        status: str,
        summary: str,
        details: dict[str, Any] | None = None
    ) -> None:
        """添加检查点"""
        if self.workflow and self.workflow._current_session_id:
            self.workflow.state_manager.add_checkpoint(
                self.workflow._current_session_id,
                phase,
                status,
                summary,
                details or {}
            )

    def commit(self, message: str | None = None) -> dict[str, Any]:
        """提交更改"""
        if not self.workflow:
            return {"status": "skipped", "message": "工作流未激活"}
        result = self.workflow.git_commit_phase(message)
        return {"status": result.status, "summary": result.summary}

    def complete_workflow(self) -> dict[str, Any]:
        """完成工作流"""
        if not self.workflow:
            return {"status": "error", "message": "工作流未激活"}

        result = self.workflow.complete_workflow()
        self.disable()
        return result

    # ==================== 命令处理 ====================

    def handle_command(self, args: list[str]) -> str:
        """
        处理外部记忆命令。

        Args:
            args: 命令参数列表

        Returns:
            命令输出
        """
        if not args:
            return self._help_text()

        cmd = args[0].lower()

        if cmd == "start":
            task = " ".join(args[1:]) if len(args) > 1 else "Agent Task"
            session_id = self.start_workflow(task)
            return f"✅ 工作流已启动\nSession: {session_id}"

        elif cmd == "enable":
            self.enable()
            return "✅ 外部记忆模式已启用"

        elif cmd == "disable":
            self.disable()
            return "✅ 外部记忆模式已禁用"

        elif cmd == "status":
            return self._status_text()

        elif cmd == "info":
            info = self.get_info()
            return (
                f"外部记忆状态:\n"
                f"  启用: {'是' if info['enabled'] else '否'}\n"
                f"  上下文: ~{info['context_size']} tokens\n"
                f"  阈值: {info['threshold']} tokens\n"
                f"  工作流: {'激活' if info['workflow_active'] else '未激活'}"
            )

        elif cmd == "commit":
            result = self.commit()
            return f"提交: {result.get('summary', result.get('message', 'N/A'))}"

        elif cmd == "checkpoint":
            if len(args) < 2:
                return "用法: checkpoint <描述>"
            desc = " ".join(args[1:])
            self.add_checkpoint("manual", "success", desc)
            return f"✅ 检查点: {desc}"

        elif cmd == "complete":
            result = self.complete_workflow()
            return (
                f"✅ 工作流完成\n"
                f"阶段: {', '.join(result.get('phases_completed', []))}"
            )

        elif cmd in ("help", "h", "?"):
            return self._help_text()

        else:
            return f"未知命令: {cmd}\n\n{self._help_text()}"

    def _help_text(self) -> str:
        return """## /external-memory 命令

用法: /external-memory <subcommand>

子命令:
    start [task]    - 开始工作流
    enable          - 启用模式
    disable         - 禁用模式
    status          - 显示状态
    info            - 显示详细信息
    commit          - 提交更改
    checkpoint <d>  - 添加检查点
    complete        - 完成并清空上下文
    help            - 显示帮助"""

    def _status_text(self) -> str:
        info = self.get_info()
        if info["workflow_active"] and self.workflow:
            progress = self.workflow.get_progress()
            return (
                f"Session: {progress.get('session_id', 'N/A')}\n"
                f"阶段: {progress.get('phase_count', 0)} 完成\n"
                f"状态: {'启用' if info['enabled'] else '禁用'}"
            )
        return (
            f"模式: {'启用' if info['enabled'] else '禁用'}\n"
            f"上下文: ~{info['context_size']}/{info['threshold']} tokens"
        )


def create_external_memory_manager(workspace: str | None = None) -> ExternalMemoryManager:
    """创建外部记忆管理器"""
    return ExternalMemoryManager(workspace)


class AgentEngineWithExternalMemory:
    """
    支持外部记忆模式的 AgentEngine。

    包装现有的 AgentEngine，添加外部记忆功能。
    """

    def __init__(self, agent_engine, workspace: str | None = None):
        """
        Args:
            agent_engine: 现有的 AgentEngine 实例
            workspace: 工作目录路径
        """
        self._agent = agent_engine
        self._external_memory = ExternalMemoryManager(workspace or str(agent_engine.config.workspace))

        # 代理属性
        self.config = agent_engine.config
        self.llm = agent_engine.llm
        self.planner = agent_engine.planner
        self.executor = agent_engine.executor
        self.reflector = agent_engine.reflector
        self.memory = agent_engine.memory
        self.state = agent_engine.state

    def __getattr__(self, name):
        """代理所有其他属性到 _agent"""
        return getattr(self._agent, name)

    def run(self, task: str) -> str:
        """运行 agent，自动检查上下文"""
        # 检查是否需要提示用户
        should_prompt, message = self._external_memory.update_context(
            self._estimate_context_size()
        )
        if should_prompt:
            print(f"\n💡 {message}")
            print("   输入 /external-memory start 开启")

        return self._agent.run(task)

    def update_context_size(self, tokens: int) -> None:
        """更新上下文大小"""
        self._external_memory.update_context(tokens)

    def _estimate_context_size(self) -> int:
        """估算当前上下文大小"""
        # 简单估算：基于 memory 中的对话数量
        base_size = len(self._agent.memory.recent_turns) * 200 if hasattr(self._agent.memory, 'recent_turns') else 0
        return self._external_memory.context_size + base_size

    @property
    def external_memory(self) -> ExternalMemoryManager:
        """获取外部记忆管理器"""
        return self._external_memory

    def handle_command(self, args: list[str]) -> str:
        """处理命令"""
        return self._external_memory.handle_command(args)