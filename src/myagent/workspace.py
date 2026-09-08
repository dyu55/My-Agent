from __future__ import annotations

import ast
import os
import tempfile
from pathlib import Path

from .store import RunStore, digest

SKIP = {
    ".git",
    ".myagent",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "build",
    ".idea",
    ".vscode",
}


class Workspace:
    def __init__(self, root: Path, store: RunStore):
        self.root = root.resolve()
        self.store = store

    def resolve(self, relative: str) -> Path:
        candidate = Path(relative)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise ValueError("Use a relative path within the workspace")
        for part in candidate.parts:
            if (
                part in {".git", ".myagent", ".ssh", ".aws", ".gnupg"}
                or part == ".env"
                or (part.startswith(".env.") and part != ".env.example")
            ):
                raise ValueError("This path is protected")
        path = (self.root / candidate).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("Path or symlink escapes the workspace")
        # A symlink into a protected directory must not bypass lexical checks.
        for part in path.relative_to(self.root).parts:
            if (
                part in {".git", ".myagent", ".ssh", ".aws", ".gnupg"}
                or part == ".env"
                or (part.startswith(".env.") and part != ".env.example")
            ):
                raise ValueError("This path resolves into protected data")
        return path

    def files(self, limit: int = 1000) -> list[Path]:
        result = []
        for base, dirs, names in os.walk(self.root, followlinks=False):
            dirs[:] = sorted(d for d in dirs if d not in SKIP and not (Path(base) / d).is_symlink())
            for name in sorted(names):
                path = Path(base) / name
                if path.is_symlink():
                    continue
                try:
                    self.resolve(str(path.relative_to(self.root)))
                except ValueError:
                    continue
                result.append(path)
                if len(result) >= limit:
                    return result
        return result

    def read(self, relative: str, start_line: int = 1, lines: int = 250) -> dict:
        path = self.resolve(relative)
        if not path.is_file():
            raise ValueError("File does not exist")
        if path.stat().st_size > 1_000_000:
            raise ValueError("File exceeds the 1 MB text limit")
        content = path.read_bytes()
        text = content.decode("utf-8")
        if "\x00" in text:
            raise ValueError("Binary files are not supported")
        all_lines = text.splitlines()
        selected = all_lines[start_line - 1 : start_line - 1 + lines]
        return {
            "path": relative,
            "sha256": digest(content),
            "total_lines": len(all_lines),
            "start_line": start_line,
            "text": "\n".join(selected),
            "truncated": start_line - 1 + lines < len(all_lines),
        }

    @staticmethod
    def atomic_write(path: Path, content: bytes):
        path.parent.mkdir(parents=True, exist_ok=True)
        old_mode = path.stat().st_mode & 0o777 if path.exists() else 0o644
        fd, name = tempfile.mkstemp(prefix=".myagent-write-", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as output:
                output.write(content)
                output.flush()
                os.fsync(output.fileno())
            os.chmod(name, old_mode)
            os.replace(name, path)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def write(
        self, run_id: str, relative: str, text: str, expected_sha256: str | None = None
    ) -> dict:
        path = self.resolve(relative)
        if path == self.root or path.is_dir():
            raise ValueError("Choose a file path")
        after = text.encode("utf-8")
        if len(after) > 1_000_000:
            raise ValueError("File exceeds the 1 MB limit")
        if path.exists() and path.stat().st_size > 1_000_000:
            raise ValueError("Existing file exceeds the 1 MB limit")
        before = path.read_bytes() if path.exists() else None
        if before is not None and (expected_sha256 is None or expected_sha256 != digest(before)):
            raise ValueError(
                "File exists or changed; read it and supply its current expected_sha256"
            )
        if before is None and expected_sha256 is not None:
            raise ValueError("File was removed after it was read")
        if path.suffix == ".py":
            ast.parse(text, filename=relative)
        if before == after:
            return {"path": relative, "sha256": digest(after), "changed": False}
        seq = self.store.prepare_change(run_id, relative, before, after)
        try:
            # Re-resolve immediately before mutation in case a parent path changed.
            if self.resolve(relative) != path:
                raise ValueError("File location changed while preparing the edit")
            self.atomic_write(path, after)
        except Exception:
            self.store.mark_change(seq, "failed")
            raise
        self.store.mark_change(seq, "applied")
        return {
            "path": relative,
            "sha256": digest(after),
            "changed": True,
            "created": before is None,
            "bytes": len(after),
        }

    def edit(self, run_id: str, relative: str, old: str, new: str, expected_sha256: str) -> dict:
        path = self.resolve(relative)
        if not path.is_file() or path.stat().st_size > 1_000_000:
            raise ValueError("File is missing or exceeds the text limit")
        text = path.read_text()
        if not old or text.count(old) != 1:
            raise ValueError("The old text must occur exactly once; include more context")
        return self.write(run_id, relative, text.replace(old, new, 1), expected_sha256)

    def repo_map(self) -> str:
        parts, size = [], 0
        for path in self.files(400):
            relative = str(path.relative_to(self.root))
            line = relative
            if path.suffix == ".py" and path.stat().st_size < 100_000:
                try:
                    tree = ast.parse(path.read_text())
                    symbols = [
                        f"{n.name}:{n.lineno}"
                        for n in ast.walk(tree)
                        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                    ]
                    if symbols:
                        line += " — " + ", ".join(symbols[:30])
                except (ValueError, SyntaxError, UnicodeError):
                    line += " [unable to parse]"
            parts.append(line)
            size += len(line)
            if size > 12000:
                parts.append("[map truncated]")
                break
        return "\n".join(parts) or "[empty workspace]"

    def undo(self, run_id: str) -> list[str]:
        with self.store.lock(run_id):
            run = self.store.load(run_id)
            if run.status == "running":
                raise ValueError("Pause or finish this run before restoring files")
            changes = self.store.changes(run_id)
            resolved = []
            for change in changes:
                path = self.resolve(change["path"])
                if (
                    not path.is_file()
                    or path.stat().st_size > 1_000_000
                    or digest(path.read_bytes()) != change["after_sha"]
                ):
                    raise ValueError(
                        f"{change['path']} changed after this run; no files were restored"
                    )
                resolved.append((change, path))
            for change, path in resolved:
                if change["before"] is None:
                    path.unlink()
                else:
                    self.atomic_write(path, change["before"])
            with self.store.connect() as db:
                db.execute(
                    "UPDATE changes SET state='reverted' WHERE run_id=? AND state IN ('applied','prepared')",
                    (run_id,),
                )
                db.execute("DELETE FROM memories WHERE run_id=?", (run_id,))
            run.status, run.summary = (
                "reverted",
                "File-tool changes restored. Command side effects are not automatically reversible.",
            )
            self.store.save(run)
            self.store.event(run.id, "reverted", {"paths": [c["path"] for c in changes]})
            return [change["path"] for change in changes]
