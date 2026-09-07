"""Exercise observable tool outcomes, path boundaries and concurrent dispatch."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace

import pytest

from agent.executor import Action, ExecutionStatus, ToolExecutor
from agent.tools.base import ToolResult
from agent.tools.test_tools import TestTools as PytestTools


def test_nonzero_shell_exit_propagates_failure(tmp_path):
    executor = ToolExecutor(str(tmp_path))
    result = executor.execute_action(Action(command="execute", script="exit 7"))
    assert result.status is ExecutionStatus.FAILURE
    assert "Exit Code: 7" in result.output
    assert "7" in result.error
    assert executor.action_history == [result]


def test_error_like_successful_output_is_not_misclassified(tmp_path):
    executor = ToolExecutor(str(tmp_path))
    executor.registry.register(
        "message", lambda action: ToolResult.ok("Error handling guide")
    )
    assert executor.execute_action(Action(command="message")).is_success()


def test_empty_failure_output_retains_error(tmp_path):
    executor = ToolExecutor(str(tmp_path))
    executor.registry.register(
        "fail", lambda action: ToolResult.err("database offline")
    )
    result = executor.execute_action(Action(command="fail"))
    assert not result.is_success()
    assert result.error == "database offline"
    assert "database offline" in result.output


def test_raised_error_and_unknown_tool_are_recorded(tmp_path):
    executor = ToolExecutor(str(tmp_path))

    def broken(action):
        raise ValueError("broken handler")

    executor.registry.register("broken", broken)
    assert executor.execute_action(Action(command="broken")).error == "broken handler"
    assert not executor.execute_action(Action(command="unknown")).is_success()
    assert len(executor.action_history) == 2


def test_policy_blocks_before_optional_tool_is_loaded(tmp_path):
    executor = ToolExecutor(str(tmp_path), {"blocked_commands": ["run_tests"]})
    assert not executor.execute_action(Action(command="run_tests")).is_success()
    assert executor.registry._instances == {}
    assert executor.execute_action(
        Action(command="write", path="x.txt", content="ok")
    ).is_success()
    assert executor.registry._instances == {}


def test_concurrent_actions_keep_their_own_payloads(tmp_path):
    executor = ToolExecutor(str(tmp_path))
    barrier = Barrier(2)

    def echo(action):
        barrier.wait(timeout=5)
        return ToolResult.ok(action["content"])

    executor.registry.register("echo", echo)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                executor.execute_action,
                [
                    Action(command="echo", content="first"),
                    Action(command="echo", content="second"),
                ],
            )
        )
    assert [result.output for result in results] == ["first", "second"]


@pytest.mark.parametrize(
    "command", ["write", "edit", "read", "mkdir", "list_dir", "create_file"]
)
def test_sibling_prefix_path_cannot_escape_workspace(tmp_path, command):
    workspace = tmp_path / "work"
    workspace.mkdir()
    outside = tmp_path / "work-private"
    outside.mkdir()
    target = outside / "file.txt"
    target.write_text("unchanged")
    path = str(outside if command in {"mkdir", "list_dir"} else target)
    executor = ToolExecutor(str(workspace))
    result = executor.execute_action(
        Action(
            command=command,
            path=path,
            old_text="unchanged",
            content="changed",
            files=[{"path": path, "content": "changed"}],
        )
    )
    assert not result.is_success()
    assert target.read_text() == "unchanged"


def test_symlink_escape_is_rejected(tmp_path):
    workspace = tmp_path / "work"
    workspace.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (workspace / "link").symlink_to(outside, target_is_directory=True)
    executor = ToolExecutor(str(workspace))
    assert not executor.execute_action(
        Action(command="write", path="link/new.txt", content="bad")
    ).is_success()
    assert not (outside / "new.txt").exists()


def test_batch_creation_reports_partial_failure_and_preserves_successes(tmp_path):
    executor = ToolExecutor(str(tmp_path))
    result = executor.execute_action(
        Action(
            command="create_file",
            files=[
                {"path": "ok.txt", "content": "ok"},
                {"path": "./.env", "content": "blocked"},
            ],
        )
    )
    assert not result.is_success()
    assert (tmp_path / "ok.txt").read_text() == "ok"
    assert not (tmp_path / ".env").exists()


def test_syntax_diagnostic_handles_workspace_prefixed_path(tmp_path):
    executor = ToolExecutor(str(tmp_path))
    result = executor.execute_action(
        Action(
            command="write",
            path=f"{tmp_path.name}/broken.py",
            content="def broken(\n",
        )
    )
    assert "Static Diagnostic Warning" in result.output


@pytest.mark.parametrize("value", [False, lambda: False])
def test_result_adapter_evaluates_boolean_and_callable_status(value):
    assert not ToolResult.from_result(SimpleNamespace(is_success=value)).success


def test_result_adapter_cannot_hide_failed_tests():
    assert not ToolResult.from_result(
        SimpleNamespace(passed=4, failed=1, errors=0)
    ).success


@pytest.mark.parametrize(
    "source,passed,failed,skipped,errors",
    [
        ("def test_ok(): assert True\n", 1, 0, 0, 0),
        ("def test_bad(): assert False\n", 0, 1, 0, 0),
        (
            "import pytest\n@pytest.mark.skip(reason='example')\ndef test_skip(): pass\n",
            0,
            0,
            1,
            0,
        ),
        ("def test_broken(\n", 0, 0, 0, 1),
    ],
)
def test_real_pytest_subprocess_reports_counts(
    tmp_path, source, passed, failed, skipped, errors
):
    (tmp_path / "test_example.py").write_text(source)
    result = PytestTools(str(tmp_path)).run_tests()
    assert (result.passed, result.failed, result.skipped, result.errors) == (
        passed,
        failed,
        skipped,
        errors,
    )
    assert result.is_success == (failed == 0 and errors == 0)


def test_no_collected_tests_is_not_success(tmp_path):
    result = ToolExecutor(str(tmp_path)).execute_action(Action(command="run_tests"))
    assert not result.is_success()


def test_dependency_report_is_valid_json(tmp_path):
    import json

    result = ToolExecutor(str(tmp_path)).execute_action(
        Action(
            command="check_dependencies",
            modules=["json", "not_a_real_module_zz"],
        )
    )
    assert json.loads(result.output) == {
        "available": ["json"],
        "missing": ["not_a_real_module_zz"],
    }


def test_junit_entity_expansion_is_rejected(tmp_path, monkeypatch):
    from pathlib import Path
    from subprocess import CompletedProcess

    def malicious_report(command, **kwargs):
        report = next(
            arg.split("=", 1)[1] for arg in command if arg.startswith("--junitxml=")
        )
        Path(report).write_text(
            '<!DOCTYPE testsuites [<!ENTITY payload "untrusted">]>'
            '<testsuites><testsuite tests="1" failures="0" errors="0">'
            '<testcase name="&payload;"/></testsuite></testsuites>'
        )
        return CompletedProcess(command, 0, "", "")

    monkeypatch.setattr("agent.tools.test_tools.subprocess.run", malicious_report)
    result = PytestTools(str(tmp_path)).run_tests()
    assert not result.is_success
    assert result.errors == 1
    assert "EntitiesForbidden" in result.output
