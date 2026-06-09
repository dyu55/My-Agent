"""Rich terminal display manager for MyAgent CLI."""

from contextlib import contextmanager
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.spinner import Spinner
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.columns import Columns


console = Console()


class Display:
    """Rich terminal display helpers."""

    def __init__(self):
        self.console = console

    # ── Startup ──────────────────────────────────────────

    def banner(self, model: str, provider: str, workspace: Path, mode: str) -> None:
        """Show startup banner with session info."""
        self.console.print()
        self.console.print(
            Text("  MyAgent CLI", style="bold cyan"),
            end="",
        )
        self.console.print(Text("  —  Local Coding Agent", style="dim"))
        self.console.print()

        info = Table.grid(padding=(0, 2))
        info.add_row(
            Text("Model", style="dim"),
            Text(f"{model}", style="bold"),
            Text("Provider", style="dim"),
            Text(f"{provider}", style="bold"),
        )
        info.add_row(
            Text("Workspace", style="dim"),
            Text(str(workspace), style="bold"),
            Text("Mode", style="dim"),
            Text(f"{mode}", style="bold green" if mode == "TASK" else "bold yellow"),
        )
        self.console.print(Panel(info, border_style="cyan", padding=(0, 1)))
        self.console.print()
        self.console.print(
            Text("  Type a task to execute, or ", style="dim")
            + Text("/help", style="bold cyan")
            + Text(" for commands.", style="dim")
        )
        self.console.print()

    # ── Help ─────────────────────────────────────────────

    def help_table(self, commands: list[tuple[str, str, str]]) -> None:
        """Show commands as a formatted table.

        Args:
            commands: list of (name_with_aliases, description, category)
        """
        table = Table(
            title="Commands",
            border_style="cyan",
            title_style="bold cyan",
            padding=(0, 1),
            show_header=True,
            header_style="bold",
        )
        table.add_column("Command", style="cyan", min_width=20)
        table.add_column("Description")

        for cmd_str, desc, _ in commands:
            table.add_row(cmd_str, desc)

        self.console.print(table)
        self.console.print()

    # ── Status / Context ─────────────────────────────────

    def status_panel(self, data: dict[str, Any]) -> None:
        """Show status info in a panel."""
        table = Table.grid(padding=(0, 2))
        for key, value in data.items():
            table.add_row(
                Text(key, style="dim"),
                Text(str(value), style="bold"),
            )
        self.console.print(Panel(table, title="Status", border_style="cyan"))

    def context_panel(self, data: dict[str, Any]) -> None:
        """Show context info."""
        table = Table.grid(padding=(0, 2))
        for key, value in data.items():
            style = "bold green" if value == "Yes" else "bold" if value != "No" else "dim"
            table.add_row(Text(key, style="dim"), Text(str(value), style=style))
        self.console.print(Panel(table, title="Context", border_style="cyan"))

    # ── Task Execution ───────────────────────────────────

    def task_header(self, task_num: int, task_desc: str) -> None:
        """Show task execution header."""
        self.console.print()
        self.console.print(
            Panel(
                Text(task_desc, style="bold"),
                title=f"Task #{task_num}",
                border_style="cyan",
                padding=(0, 1),
            )
        )

    def task_result(self, result: str, success: bool = True) -> None:
        """Show task result."""
        style = "green" if success else "red"
        icon = "Done" if success else "Failed"
        self.console.print()
        self.console.print(
            Panel(
                Text(result[:500], style=style),
                title=f"Result  {icon}",
                border_style=style,
                padding=(0, 1),
            )
        )

    def task_cancelled(self) -> None:
        """Show task cancelled message."""
        self.console.print()
        self.console.print(
            Panel(
                Text("Task cancelled by user", style="yellow"),
                title="Cancelled",
                border_style="yellow",
            )
        )

    # ── Messages ─────────────────────────────────────────

    def error(self, message: str) -> None:
        """Show error message."""
        self.console.print(
            Panel(Text(message, style="red"), border_style="red", title="Error")
        )

    def success(self, message: str) -> None:
        """Show success message."""
        self.console.print(Text(f"  {message}", style="green"))

    def info(self, message: str) -> None:
        """Show info message."""
        self.console.print(Text(f"  {message}", style="cyan"))

    def warning(self, message: str) -> None:
        """Show warning message."""
        self.console.print(Text(f"  {message}", style="yellow"))

    def plain(self, message: str) -> None:
        """Show plain text (no styling)."""
        self.console.print(message)

    # ── LLM Output ───────────────────────────────────────

    def stream_text(self, text: str) -> None:
        """Print text, rendering markdown if it looks like markdown."""
        if any(marker in text for marker in ["```", "## ", "**", "- ", "1. "]):
            self.console.print(Markdown(text))
        else:
            self.console.print(text)

    # ── File / Command Output ────────────────────────────

    def file_content(self, path: Path, content: str, lexer: str | None = None) -> None:
        """Show file content with syntax highlighting."""
        if lexer is None:
            try:
                from pygments.lexers import get_lexer_for_filename
                lexer_obj = get_lexer_for_filename(str(path))
                lexer = lexer_obj.name.lower()
            except Exception:
                lexer = "text"
        syntax = Syntax(content, lexer, theme="monokai", line_numbers=True)
        self.console.print(
            Panel(syntax, title=str(path), border_style="cyan", padding=(0, 1))
        )

    def command_output(self, text: str, title: str = "Output") -> None:
        """Show command output in a panel."""
        self.console.print(
            Panel(Text(text), title=title, border_style="dim", padding=(0, 1))
        )

    # ── Directory Listing ────────────────────────────────

    def directory_listing(self, path: Path, entries: list[tuple[str, bool, str]]) -> None:
        """Show directory listing as a table.

        Args:
            entries: list of (name, is_dir, size_str)
        """
        table = Table(
            title=str(path),
            border_style="cyan",
            title_style="bold",
            padding=(0, 1),
            show_header=True,
        )
        table.add_column("", width=4)
        table.add_column("Name", style="bold")
        table.add_column("Size", style="dim", justify="right")

        for name, is_dir, size_str in entries:
            icon = "DIR" if is_dir else "---"
            name_style = "bold cyan" if is_dir else ""
            table.add_row(Text(icon, style="dim"), Text(name, style=name_style), size_str)

        self.console.print(table)
        self.console.print()

    # ── Model / Provider ─────────────────────────────────

    def model_info(self, current_model: str, current_provider: str, available: list[str] | None = None) -> None:
        """Show model info."""
        table = Table.grid(padding=(0, 2))
        table.add_row(Text("Model", style="dim"), Text(current_model, style="bold"))
        table.add_row(Text("Provider", style="dim"), Text(current_provider, style="bold"))
        if available:
            table.add_row(Text("Available", style="dim"), Text(", ".join(available), style="dim"))
        self.console.print(Panel(table, title="Model", border_style="cyan"))

    def provider_list(self, current: str, providers: list[str]) -> None:
        """Show provider list."""
        table = Table(border_style="cyan", padding=(0, 1))
        table.add_column("Provider", style="bold")
        table.add_column("Status")
        for p in providers:
            status = "current" if p == current else ""
            table.add_row(p, Text(status, style="green" if status else "dim"))
        self.console.print(table)

    # ── MCP ──────────────────────────────────────────────

    def mcp_status(self, servers: dict[str, dict]) -> None:
        """Show MCP server status."""
        table = Table(title="MCP Servers", border_style="cyan", padding=(0, 1))
        table.add_column("Server", style="bold")
        table.add_column("State")
        table.add_column("Tools", style="dim")

        for name, info in servers.items():
            state = info.get("state", "unknown")
            state_style = {"connected": "green", "disconnected": "dim", "error": "red"}.get(state, "yellow")
            tools = ", ".join(info.get("tools", []))
            table.add_row(name, Text(state, style=state_style), tools)

        self.console.print(table)

    # ── Spinners / Live ──────────────────────────────────

    @contextmanager
    def spinner(self, text: str = "Thinking..."):
        """Context manager for a spinner during long operations."""
        with self.console.status(Text(text, style="cyan"), spinner="dots"):
            yield

    @contextmanager
    def live_status(self):
        """Context manager for a live-updating status display."""
        from rich.live import Live
        with Live(console=self.console, refresh_per_second=10) as live:
            yield live

    # ── Utilities ────────────────────────────────────────

    def clear(self) -> None:
        """Clear the terminal."""
        self.console.clear()

    def divider(self, char: str = "─", style: str = "dim") -> None:
        """Print a horizontal divider."""
        width = self.console.width or 80
        self.console.print(Text(char * width, style=style))
