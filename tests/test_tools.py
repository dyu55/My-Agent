import sys
import uuid

import pytest

from myagent.models import Action, Limits, Permissions, Run
from myagent.store import RunStore, digest
from myagent.tools import ToolRegistry, process
from myagent.workspace import Workspace


@pytest.fixture
def setup(tmp_path):
    store = RunStore(tmp_path)
    run = Run(
        id=uuid.uuid4().hex, task="test", workspace=str(tmp_path), provider="demo", model="demo"
    )
    store.save(run)
    workspace = Workspace(tmp_path, store)
    registry = ToolRegistry(workspace, run.id, Permissions(write=True, execute=True), Limits())
    return workspace, store, run, registry


@pytest.mark.parametrize(
    "path",
    [
        "../escape.txt",
        "/tmp/escape.txt",
        ".env",
        ".env.local",
        ".git/config",
        ".myagent/runs.sqlite3",
        ".ssh/id_rsa",
        "sub/../../escape",
    ],
)
def test_protected_and_external_paths_are_rejected(setup, path):
    workspace, _, _, registry = setup
    with pytest.raises(ValueError):
        workspace.resolve(path)
    result = registry.execute(Action(tool="write_file", arguments={"path": path, "content": "bad"}))
    assert not result.ok


def test_symlink_escape_and_protected_alias_are_rejected(setup, tmp_path):
    workspace, _, _, _ = setup
    outside = tmp_path.parent / (tmp_path.name + "-sibling")
    outside.mkdir()
    (tmp_path / "linked").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="escapes"):
        workspace.resolve("linked/x.txt")
    (tmp_path / "secret-alias").symlink_to(tmp_path / ".myagent", target_is_directory=True)
    with pytest.raises(ValueError, match="protected"):
        workspace.resolve("secret-alias/runs.sqlite3")


def test_write_hash_check_and_unique_edit(setup):
    workspace, _, run, _ = setup
    created = workspace.write(run.id, "module.py", "value = 1\n")
    with pytest.raises(ValueError, match="current expected_sha256"):
        workspace.write(run.id, "module.py", "value = 2\n")
    changed = workspace.edit(run.id, "module.py", "value = 1", "value = 2", created["sha256"])
    assert workspace.read("module.py")["text"] == "value = 2"
    with pytest.raises(ValueError, match="exactly once"):
        workspace.edit(run.id, "module.py", "missing", "new", changed["sha256"])
    with pytest.raises(ValueError):
        workspace.write(run.id, "module.py", "value = 3\n", created["sha256"])


def test_invalid_python_does_not_modify_original(setup):
    workspace, store, run, registry = setup
    original = workspace.write(run.id, "module.py", "value = 1\n")
    result = registry.execute(
        Action(
            tool="write_file",
            arguments={
                "path": "module.py",
                "content": "def broken(:",
                "expected_sha256": original["sha256"],
            },
        )
    )
    assert not result.ok and "SyntaxError" in result.error
    assert workspace.read("module.py")["sha256"] == original["sha256"]
    assert len(store.changes(run.id)) == 1


def test_undo_restores_original_and_removes_created_file(setup):
    workspace, store, run, _ = setup
    path = workspace.root / "existing.txt"
    path.write_text("original\n")
    workspace.write(run.id, "existing.txt", "changed\n", digest(path.read_bytes()))
    workspace.write(run.id, "new.txt", "new file\n")
    assert set(workspace.undo(run.id)) == {"existing.txt", "new.txt"}
    assert path.read_text() == "original\n" and not (workspace.root / "new.txt").exists()
    assert store.load(run.id).status == "reverted"


def test_undo_preflights_all_files_before_any_restore(setup):
    workspace, _, run, _ = setup
    workspace.write(run.id, "one.txt", "first\n")
    workspace.write(run.id, "two.txt", "second\n")
    (workspace.root / "two.txt").write_text("user edit\n")
    with pytest.raises(ValueError, match="no files were restored"):
        workspace.undo(run.id)
    assert (workspace.root / "one.txt").read_text() == "first\n"
    assert (workspace.root / "two.txt").read_text() == "user edit\n"


def test_multiedit_undo_and_diff(setup):
    workspace, store, run, _ = setup
    first = workspace.write(run.id, "note.txt", "one\n")
    workspace.write(run.id, "note.txt", "two\n", first["sha256"])
    diff = store.diff(run.id, workspace.resolve)
    assert len(diff) == 1 and "+two" in diff[0]["diff"] and diff[0]["created"]
    workspace.undo(run.id)
    assert not (workspace.root / "note.txt").exists()


def test_permissions_and_unknown_arguments_fail_without_side_effects(setup):
    workspace, _, _, registry = setup
    registry.permissions = Permissions()
    result = registry.execute(
        Action(tool="write_file", arguments={"path": "bad.txt", "content": "no"})
    )
    assert result.requires_permission == "write" and not (workspace.root / "bad.txt").exists()
    command = registry.execute(Action(tool="run_command", arguments={"argv": ["echo", "hello"]}))
    assert command.requires_permission == "execute"
    assert not registry.execute(Action(tool="unknown", arguments={})).ok
    assert not registry.execute(Action(tool="list_files", arguments={"extra": "no"})).ok


def test_read_pagination_search_and_repo_map(setup):
    workspace, _, run, registry = setup
    workspace.write(run.id, "example.py", "def useful():\n    return 'needle'\n")
    result = registry.execute(
        Action(tool="read_file", arguments={"path": "example.py", "lines": 1})
    )
    assert result.ok and result.data["truncated"] and result.output == "def useful():"
    found = registry.execute(Action(tool="search", arguments={"pattern": "NEEDLE"}))
    assert found.data["matches"][0]["line"] == 2
    assert "useful:1" in workspace.repo_map()
    assert ".myagent" not in registry.execute(Action(tool="list_files")).output


@pytest.mark.parametrize(
    "source,passed,failed",
    [
        ("def test_ok():\n    assert 2 + 2 == 4\n", 1, 0),
        ("def test_bad():\n    assert False\n", 0, 1),
    ],
)
def test_pytest_uses_real_exit_status_and_report(setup, source, passed, failed):
    workspace, _, _, registry = setup
    (workspace.root / "test_example.py").write_text(source)
    result = registry.execute(Action(tool="run_tests", arguments={"path": "test_example.py"}))
    assert result.ok == (passed == 1)
    assert result.data["passed"] == passed and result.data["failed"] == failed
    assert result.data["returncode"] == (0 if passed else 1)


@pytest.mark.parametrize(
    "source",
    [
        "value = 1\n",
        "import does_not_exist_at_all\n",
        "import pytest\n@pytest.mark.skip(reason='skip')\ndef test_skip():\n    assert True\n",
    ],
)
def test_empty_collection_import_error_and_only_skips_fail(setup, source):
    workspace, _, _, registry = setup
    (workspace.root / "test_example.py").write_text(source)
    result = registry.execute(Action(tool="run_tests", arguments={"path": "test_example.py"}))
    assert not result.ok and result.error


def test_subprocess_failure_timeout_and_output_limit(tmp_path):
    failed = process(
        [sys.executable, "-c", "import sys; print('failed'); sys.exit(7)"], tmp_path, 10
    )
    assert not failed.ok and failed.data["returncode"] == 7 and "failed" in failed.output
    timeout = process([sys.executable, "-c", "import time; time.sleep(10)"], tmp_path, 0.1)
    assert not timeout.ok and "timed out" in timeout.error and timeout.data["seconds"] < 2
    large = process([sys.executable, "-c", "print('x' * 50000)"], tmp_path, 10)
    assert large.ok and large.data["truncated"] and len(large.output) == 16000


def test_state_directory_symlink_is_rejected(tmp_path):
    outside = tmp_path.parent / (tmp_path.name + "-state")
    outside.mkdir()
    (tmp_path / ".myagent").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        RunStore(tmp_path)
