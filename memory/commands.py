"""External Memory CLI Commands - 外部记忆模式的 CLI 命令集成。

提供 /external-memory 和 /memory-status 命令。
"""

from pathlib import Path
from typing import Any

from memory.state_manager import StateManager
from memory.external_memory import create_external_memory_mode, Phase


def cmd_external_memory(args: list[str], workspace: Path | None = None) -> str:
    """
    外部记忆模式命令。

    用法:
        /external-memory start <task_name>     - 开始外部记忆工作流
        /external-memory status                - 显示当前状态
        /external-memory commit               - 手动提交更改
        /external-memory checkpoint            - 添加检查点
        /external-memory complete             - 完成工作流并清空上下文
    """
    if workspace is None:
        workspace = Path("workspace")

    workflow = create_external_memory_mode(workspace)

    if not args:
        return _show_help()

    subcommand = args[0].lower()

    if subcommand == "start":
        if len(args) < 2:
            return "用法: /external-memory start <task_name>"

        task_name = " ".join(args[1:])
        session_id = workflow.start_workflow(task_name)
        progress = workflow.get_progress()

        return (
            f"✅ 外部记忆模式已启动\n"
            f"Session: {session_id}\n"
            f"任务: {task_name}\n"
            f"\n后续步骤:\n"
            f"1. Agent 执行任务\n"
            f"2. /external-memory commit - 提交更改\n"
            f"3. /external-memory complete - 完成并清空上下文"
        )

    elif subcommand == "status":
        return _show_status(workflow)

    elif subcommand == "commit":
        result = workflow.git_commit_phase()
        if result.status == "skipped":
            return "没有需要提交的更改"
        return f"✅ 已提交: {result.summary}"

    elif subcommand == "checkpoint":
        if len(args) < 2:
            return "用法: /external-memory checkpoint <description>"

        session_id = workflow.get_progress().get("session_id")
        if not session_id:
            return "没有活动的会话，请先 /external-memory start"

        description = " ".join(args[1:])
        workflow.state_manager.add_checkpoint(
            session_id,
            "manual_checkpoint",
            "success",
            description,
            {}
        )
        return f"✅ 检查点已添加: {description}"

    elif subcommand == "complete":
        result = workflow.complete_workflow()
        return (
            f"✅ 工作流已完成\n"
            f"Session: {result['session_id']}\n"
            f"完成的阶段: {', '.join(result['phases_completed'])}\n"
            f"\n上下文已清空，可以开始新任务。"
        )

    elif subcommand == "help":
        return _show_help()

    else:
        return f"未知命令: {subcommand}\n\n{_show_help()}"


def cmd_memory_status(args: list[str], workspace: Path | None = None) -> str:
    """
    内存状态命令。

    用法:
        /memory-status                    - 显示状态摘要
        /memory-status features            - 显示功能清单
        /memory-status sessions            - 显示最近会话
        /memory-status prompt              - 检查是否需要提示用户
    """
    if workspace is None:
        workspace = Path("workspace")

    state_manager = StateManager(
        state_dir=str(workspace / "memory"),
        session_logs_dir=str(workspace / "memory" / "session_logs")
    )

    if not args or args[0] == "summary":
        return state_manager.get_summary()

    subcommand = args[0].lower()

    if subcommand == "features":
        features = state_manager.get_features()
        if not features:
            return "没有已记录的功能"

        lines = ["## 功能清单\n"]
        for f in features:
            progress = state_manager.get_feature_progress(f["id"])
            lines.append(
                f"- [{f['status']}] {f['name']} "
                f"(任务: {progress['completed']}/{progress['total']}, "
                f"{progress['percentage']:.0f}%)"
            )
            if f.get("description"):
                lines.append(f"  {f['description']}")
        return "\n".join(lines)

    elif subcommand == "sessions":
        sessions = state_manager.get_recent_sessions(limit=5)
        if not sessions:
            return "没有最近的会话"

        lines = ["## 最近会话\n"]
        for s in sessions:
            started = s.get("started_at", "")[:16]
            ended = s.get("ended_at", "")
            status = "进行中" if not ended else "已结束"
            lines.append(f"- [{status}] {s.get('task_name', 'Unknown')} ({started})")
        return "\n".join(lines)

    elif subcommand == "prompt":
        # 检查上下文估算
        context_size = 5000  # 默认值，实际应用中应该从 agent 获取
        should_prompt, msg = state_manager.should_prompt_user(context_size)
        return (
            f"当前上下文估算: ~{context_size} tokens\n"
            f"应提示用户: {'是' if should_prompt else '否'}\n"
            f"{msg if msg else '上下文状态良好'}"
        )

    else:
        return f"未知子命令: {subcommand}\n显示摘要: /memory-status"


def _show_help() -> str:
    return """## 外部记忆模式命令

用法: /external-memory <subcommand>

子命令:
    start <task_name>    - 开始外部记忆工作流
    status               - 显示当前工作流状态
    commit               - 手动提交所有更改
    checkpoint <desc>    - 添加检查点
    complete             - 完成工作流并清空上下文
    help                 - 显示此帮助

触发条件:
    - 用户手动输入 /external-memory start
    - 上下文超过 ~8000 tokens 时系统提示
"""


def _show_status(workflow) -> str:
    progress = workflow.get_progress()

    if not progress["session_id"]:
        return "外部记忆模式未激活。使用 /external-memory start 开始。"

    lines = [
        "## 外部记忆模式状态",
        f"Session: {progress['session_id']}",
        f"Task ID: {progress['task_id'] or 'N/A'}",
        f"已完成的阶段: {progress['phase_count']}",
        "",
        "阶段列表:"
    ]

    for i, phase in enumerate(progress["phases"], 1):
        lines.append(f"  {i}. {phase}")

    if progress["phase_count"] == 0:
        lines.append("\n提示: 完成代码编写后，使用 /external-memory commit 提交更改，")
        lines.append("      然后使用 /external-memory complete 完成工作流。")

    return "\n".join(lines)