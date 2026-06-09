"""Smart input handler using prompt_toolkit."""

from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion, PathCompleter, WordCompleter, merge_completers
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML


# Color style for the prompt
CLI_STYLE = Style.from_dict({
    "prompt": "cyan bold",
    "mode.chat": "yellow bold",
    "mode.task": "green bold",
    "path": "dim",
})


class SlashCommandCompleter(Completer):
    """Completes slash commands."""

    def __init__(self, commands: list[tuple[str, list[str]]]):
        """
        Args:
            commands: list of (name, aliases) e.g. [("help", ["h", "?"]), ("exit", ["quit", "q"])]
        """
        self.entries: list[tuple[str, str]] = []  # (completion_text, display_text)
        for name, aliases in commands:
            self.entries.append((f"/{name}", f"/{name}"))
            for alias in aliases:
                self.entries.append((f"/{alias}", f"/{alias} → /{name}"))

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        # Only complete if user is typing at the start and input starts with /
        if not text.startswith("/"):
            return
        word = text.lstrip("/")
        for completion_text, display_text in self.entries:
            cmd = completion_text.lstrip("/")
            if cmd.startswith(word):
                yield Completion(
                    completion_text,
                    start_position=-len(text),
                    display=display_text,
                )


class CLIPathCompleter(Completer):
    """Completes file paths relative to workspace."""

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self._inner = PathCompleter(
            get_paths=lambda: [str(workspace)],
            file_filter=lambda name: not name.startswith("."),
        )

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        parts = text.split(maxsplit=1)
        # Only complete after commands that take file args
        if not parts or not parts[0].startswith("/"):
            return
        cmd = parts[0].lstrip("/").lower()
        file_commands = {"edit", "read", "cd", "ls", "dir"}
        if cmd not in file_commands:
            return
        # Create a sub-document with just the path part
        path_part = parts[1] if len(parts) > 1 else ""
        from prompt_toolkit.document import Document
        sub_doc = Document(path_part, cursor_position=len(path_part))
        for c in self._inner.get_completions(sub_doc, complete_event):
            # Also filter hidden dirs (PathCompleter file_filter only applies to files)
            basename = Path(c.text).name
            if basename.startswith("."):
                continue
            yield c


class CLIPrompt:
    """Smart input handler with completion, history, and key bindings."""

    def __init__(
        self,
        commands: list[tuple[str, list[str]]],
        workspace: Path,
        history_path: str = "~/.myagent_history",
    ):
        """
        Args:
            commands: list of (name, aliases) for slash command completion
            workspace: base path for file completion
        """
        slash_completer = SlashCommandCompleter(commands)
        path_completer = CLIPathCompleter(workspace)
        completer = merge_completers([slash_completer, path_completer])

        bindings = KeyBindings()

        @bindings.add("escape", "enter")
        def _(event):
            """Alt+Enter inserts a newline for multi-line input."""
            event.current_buffer.insert_text("\n")

        self.session = PromptSession(
            completer=completer,
            history=FileHistory(str(Path(history_path).expanduser())),
            multiline=False,
            key_bindings=bindings,
            style=CLI_STYLE,
            complete_while_typing=True,
        )

        self._mode = "task"

    def set_mode(self, mode: str) -> None:
        """Update the current mode for prompt styling."""
        self._mode = mode

    def prompt(self) -> str | None:
        """Show the prompt and get user input.

        Returns:
            User input string, or None on Ctrl+D (EOF).
        """
        if self._mode == "chat":
            prompt_text = HTML("<ansiyellow><b>chat</b></ansiyellow> <b>&gt;</b> ")
        else:
            prompt_text = HTML("<ansigreen><b>task</b></ansigreen> <b>&gt;</b> ")

        try:
            return self.session.prompt(prompt_text).strip()
        except KeyboardInterrupt:
            return ""  # Ctrl+C returns empty, handled by caller
        except EOFError:
            return None  # Ctrl+D signals exit
