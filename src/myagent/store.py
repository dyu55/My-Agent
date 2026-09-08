from __future__ import annotations

import difflib
import fcntl
import hashlib
import json
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .models import Run, now


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


class RunStore:
    def __init__(self, workspace: Path):
        self.workspace = workspace.resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.directory = self.workspace / ".myagent"
        if self.directory.is_symlink():
            raise ValueError("The agent state directory must not be a symlink")
        self.directory.mkdir(mode=0o700, exist_ok=True)
        self.path = self.directory / "runs.sqlite3"
        if self.path.is_symlink():
            raise ValueError("The agent database must not be a symlink")
        with self.connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, updated_at TEXT, payload TEXT);
                CREATE TABLE IF NOT EXISTS events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, created_at TEXT, kind TEXT, payload TEXT);
                CREATE INDEX IF NOT EXISTS events_run ON events(run_id, seq);
                CREATE TABLE IF NOT EXISTS changes (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, path TEXT,
                    before BLOB, after_sha TEXT, state TEXT);
                CREATE TABLE IF NOT EXISTS memories (
                    run_id TEXT PRIMARY KEY, task TEXT, summary TEXT, created_at TEXT);
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    @contextmanager
    def lock(self, run_id: str):
        if not re.fullmatch(r"[a-f0-9]{32}", run_id):
            raise ValueError("Invalid run ID")
        path = self.directory / f"{run_id}.lock"
        if path.is_symlink():
            raise ValueError("Run lock must not be a symlink")
        with path.open("a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise ValueError("This run is already active in another process") from exc
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def save(self, run: Run):
        run.updated_at = now()
        with self.connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO runs VALUES (?, ?, ?)",
                (run.id, run.updated_at, run.model_dump_json()),
            )

    def load(self, run_id: str) -> Run:
        with self.connect() as db:
            row = db.execute("SELECT payload FROM runs WHERE id=?", (run_id,)).fetchone()
        if not row:
            raise ValueError("Run not found in this workspace")
        return Run.model_validate_json(row[0])

    def list_runs(self) -> list[Run]:
        with self.connect() as db:
            return [
                Run.model_validate_json(row[0])
                for row in db.execute("SELECT payload FROM runs ORDER BY updated_at DESC LIMIT 100")
            ]

    def event(self, run_id: str, kind: str, payload: dict):
        with self.connect() as db:
            db.execute(
                "INSERT INTO events (run_id, created_at, kind, payload) VALUES (?, ?, ?, ?)",
                (run_id, now(), kind, json.dumps(payload, ensure_ascii=False)),
            )

    def events(self, run_id: str) -> list[dict]:
        with self.connect() as db:
            return [
                {**dict(row), "payload": json.loads(row["payload"])}
                for row in db.execute(
                    "SELECT seq, created_at, kind, payload FROM events WHERE run_id=? ORDER BY seq",
                    (run_id,),
                )
            ]

    def prepare_change(self, run_id: str, path: str, before: bytes | None, after: bytes) -> int:
        with self.connect() as db:
            return db.execute(
                "INSERT INTO changes (run_id, path, before, after_sha, state) VALUES (?, ?, ?, ?, 'prepared')",
                (run_id, path, before, digest(after)),
            ).lastrowid

    def mark_change(self, seq: int, state: str):
        with self.connect() as db:
            db.execute("UPDATE changes SET state=? WHERE seq=?", (state, seq))

    def changes(self, run_id: str) -> list[dict]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT * FROM changes WHERE run_id=? AND state IN ('applied', 'prepared') ORDER BY seq",
                (run_id,),
            ).fetchall()
        merged = {}
        for row in rows:
            if row["path"] not in merged:
                merged[row["path"]] = dict(row)
            else:
                merged[row["path"]]["after_sha"] = row["after_sha"]
        return list(merged.values())

    def diff(self, run_id: str, resolve) -> list[dict]:
        result = []
        for change in self.changes(run_id):
            path = resolve(change["path"])
            after = (
                path.read_bytes() if path.is_file() and path.stat().st_size <= 1_000_000 else b""
            )
            before = change["before"] or b""
            diff = "".join(
                difflib.unified_diff(
                    before.decode("utf-8", "replace").splitlines(True),
                    after.decode("utf-8", "replace").splitlines(True),
                    fromfile=f"a/{change['path']}",
                    tofile=f"b/{change['path']}",
                )
            )
            result.append(
                {
                    "path": change["path"],
                    "created": change["before"] is None,
                    "diff": diff[:50000],
                    "current_matches": digest(after) == change["after_sha"],
                }
            )
        return result

    def remember(self, run: Run):
        with self.connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO memories VALUES (?, ?, ?, ?)",
                (run.id, run.task, run.summary, now()),
            )

    def recall(self, task: str) -> list[dict]:
        terms = set(re.findall(r"\w+", task.casefold()))
        with self.connect() as db:
            rows = [
                dict(row)
                for row in db.execute("SELECT * FROM memories ORDER BY created_at DESC LIMIT 200")
            ]
        ranked = sorted(
            rows,
            key=lambda row: len(
                terms & set(re.findall(r"\w+", (row["task"] + " " + row["summary"]).casefold()))
            ),
            reverse=True,
        )
        return [row for row in ranked if terms & set(re.findall(r"\w+", row["task"].casefold()))][
            :4
        ]
