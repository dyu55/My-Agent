"""AST-based Repo Map - Extracts high-level code structure and symbol signatures.

Provides a compact summary of project architecture and APIs within token budget.
"""

from __future__ import annotations

import ast
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class RepoMap:
    """Extracts AST symbols (classes, methods, functions) to build a project map."""

    def __init__(self, workspace: str | Path, max_chars: int = 4000):
        self.workspace = Path(workspace)
        self.max_chars = max_chars

    def extract_file_symbols(self, file_path: Path) -> str:
        """Extract classes and functions from a single Python file using AST."""
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(file_path))
        except Exception:
            return ""

        lines: list[str] = []

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                bases = [ast.unparse(b) for b in node.bases]
                base_str = f"({', '.join(bases)})" if bases else ""
                lines.append(f"  class {node.name}{base_str}:")
                # Docstring
                doc = ast.get_docstring(node)
                if doc:
                    first_line = doc.strip().split("\n")[0][:60]
                    lines.append(f'    """{first_line}"""')
                # Methods
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        args_list = []
                        for arg in item.args.args:
                            if arg.arg == "self" or arg.arg == "cls":
                                args_list.append(arg.arg)
                            elif arg.annotation:
                                args_list.append(f"{arg.arg}: {ast.unparse(arg.annotation)}")
                            else:
                                args_list.append(arg.arg)
                        ret_str = f" -> {ast.unparse(item.returns)}" if item.returns else ""
                        prefix = "async def" if isinstance(item, ast.AsyncFunctionDef) else "def"
                        lines.append(f"    {prefix} {item.name}({', '.join(args_list)}){ret_str}: ...")

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args_list = []
                for arg in node.args.args:
                    if arg.annotation:
                        args_list.append(f"{arg.arg}: {ast.unparse(arg.annotation)}")
                    else:
                        args_list.append(arg.arg)
                ret_str = f" -> {ast.unparse(node.returns)}" if node.returns else ""
                prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
                lines.append(f"  {prefix} {node.name}({', '.join(args_list)}){ret_str}: ...")
                doc = ast.get_docstring(node)
                if doc:
                    first_line = doc.strip().split("\n")[0][:60]
                    lines.append(f'    """{first_line}"""')

        return "\n".join(lines) if lines else ""

    def generate_map(self) -> str:
        """
        Scan workspace Python files and generate a compact repository symbol map.
        Respects max_chars budget.
        """
        output_chunks: list[str] = []
        total_len = 0

        # Ignore standard build/cache directories
        ignore_dirs = {".git", ".pytest_cache", "__pycache__", "venv", ".venv", "build", "dist", ".agent_backups", "_benchmark_workspaces"}

        # Gather python files sorted by depth then name
        py_files: list[Path] = []
        for path in self.workspace.rglob("*.py"):
            parts = path.relative_to(self.workspace).parts
            if any(p in ignore_dirs or p.startswith(".") or p.startswith("_test") for p in parts):
                continue
            py_files.append(path)

        py_files.sort(key=lambda p: (len(p.parts), str(p)))

        for file_path in py_files:
            rel_path = file_path.relative_to(self.workspace)
            symbols = self.extract_file_symbols(file_path)
            if not symbols:
                continue

            chunk = f"📄 {rel_path}:\n{symbols}\n"
            if total_len + len(chunk) > self.max_chars:
                output_chunks.append("... [Repo Map truncated to fit budget]")
                break

            output_chunks.append(chunk)
            total_len += len(chunk)

        return "\n".join(output_chunks) if output_chunks else "No Python symbols found."
