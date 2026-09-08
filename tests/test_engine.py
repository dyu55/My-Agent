import uuid

import pytest
from fastapi.testclient import TestClient

from myagent.engine import Engine
from myagent.models import Limits, Permissions, Plan, Run
from myagent.providers import DemoModel, ProviderError
from myagent.tools import ToolRegistry
from myagent.viewer import create_app


class ScriptedModel:
    provider, model, base_url = "scripted", "test", ""
    timeout = 60

    def __init__(self, responses):
        self.responses = iter(responses)

    def complete(self, phase, payload, schema):
        value = next(self.responses)
        if isinstance(value, BaseException):
            raise value
        return value


PLAN = {"steps": [{"id": "step", "title": "Perform the task", "depends_on": []}]}
DONE = {"complete": True, "summary": "Task completed."}
PASSED = {"verdict": "passed", "summary": "Observed results support completion."}


def test_demo_runs_real_tools_and_remembers_success(tmp_path):
    engine = Engine(tmp_path, DemoModel(), Permissions(write=True, execute=True))
    run = engine.new("Build temperature conversions with tests")
    assert run.status == "succeeded" and run.verified_version == run.mutation_version
    assert run.steps[-1].last_result["data"]["passed"] == 10
    assert (tmp_path / "temperatures.py").is_file()
    assert len(engine.store.diff(run.id, engine.workspace.resolve)) == 2
    assert engine.store.recall("temperature conversions")[0]["run_id"] == run.id
    assert engine.advance(run.id).calls == run.calls


def test_permission_pause_then_resume_has_no_early_side_effects(tmp_path):
    engine = Engine(tmp_path, DemoModel(), Permissions())
    paused = engine.new("Build temperature conversions with tests")
    assert paused.status == "paused" and "allow-write" in paused.summary
    assert not (tmp_path / "temperatures.py").exists() and paused.pending_action is None
    resumed = Engine(tmp_path, DemoModel(), Permissions(write=True, execute=True)).advance(
        paused.id
    )
    assert resumed.status == "succeeded" and resumed.steps[-1].last_result["data"]["passed"] == 10


@pytest.mark.parametrize(
    "steps",
    [
        [
            {"id": "one", "title": "A", "depends_on": ["two"]},
            {"id": "two", "title": "B", "depends_on": ["one"]},
        ],
        [{"id": "one", "title": "A", "depends_on": ["missing"]}],
        [{"id": "one", "title": "A"}, {"id": "one", "title": "B"}],
    ],
)
def test_invalid_plan_dependencies_are_rejected(steps):
    with pytest.raises(ValueError):
        Plan(steps=steps)


def test_model_cannot_preset_completed_plan_state(tmp_path):
    model = ScriptedModel(
        [{"steps": [{"id": "step", "title": "Check", "status": "succeeded"}]}, DONE, PASSED]
    )
    run = Engine(tmp_path, model).new("Read-only analysis")
    assert run.status == "succeeded" and run.calls == 3


def test_failed_command_cannot_be_reported_success(tmp_path):
    model = ScriptedModel(
        [
            PLAN,
            {
                "action": {
                    "tool": "run_command",
                    "arguments": {"argv": ["python", "-c", "raise SystemExit(3)"]},
                }
            },
            DONE,
            DONE,
            DONE,
        ]
    )
    run = Engine(tmp_path, model, Permissions(execute=True)).new("Run a command")
    assert run.status == "failed" and run.steps[0].unresolved_tools == ["run_command"]
    assert run.steps[0].last_result["data"]["returncode"] == 3


def test_write_without_verification_is_paused_and_gets_verification_step(tmp_path):
    model = ScriptedModel(
        [
            PLAN,
            {
                "action": {
                    "tool": "write_file",
                    "arguments": {"path": "new.py", "content": "value = 1\n"},
                }
            },
            DONE,
            PASSED,
        ]
    )
    run = Engine(tmp_path, model, Permissions(write=True)).new("Write a Python module")
    assert run.status == "paused" and run.steps[-1].id == "verify_final"
    assert run.needs_verification and run.verified_version == -1


def test_budget_pause_can_resume_with_larger_limit(tmp_path):
    engine = Engine(
        tmp_path, DemoModel(), Permissions(write=True, execute=True), Limits(max_calls=1)
    )
    run = engine.new("Build temperature conversions")
    assert run.status == "paused" and run.calls == 1 and not (tmp_path / "temperatures.py").exists()
    completed = Engine(
        tmp_path, DemoModel(), Permissions(write=True, execute=True), Limits(max_calls=40)
    ).advance(run.id)
    assert completed.status == "succeeded"


def test_provider_outage_preserves_run_without_claiming_completion(tmp_path):
    engine = Engine(tmp_path, ScriptedModel([ProviderError("Service unavailable")]))
    run = engine.new("Build something")
    assert run.status == "paused" and run.calls == 1 and run.steps == []
    assert engine.store.load(run.id).summary == "Service unavailable"


def test_invalid_action_schema_is_recoverable(tmp_path):
    run = Engine(
        tmp_path, ScriptedModel([PLAN, {"action": {"tool": "list_files"}, "complete": True}])
    ).new("Inspect files")
    assert run.status == "paused" and "schema" in run.summary
    assert run.pending_action is None


def test_interrupted_action_is_not_replayed_without_acknowledgment(tmp_path, monkeypatch):
    engine = Engine(tmp_path, DemoModel(), Permissions(write=True, execute=True))
    real_execute = ToolRegistry.execute

    def interrupt(self, action):
        raise KeyboardInterrupt()

    monkeypatch.setattr(ToolRegistry, "execute", interrupt)
    run = engine.new("Build conversions")
    assert run.status == "paused" and run.pending_action.tool == "repo_map"
    monkeypatch.setattr(ToolRegistry, "execute", real_execute)
    paused = engine.advance(run.id)
    assert paused.calls == run.calls and "acknowledge-interrupted" in paused.summary
    completed = engine.advance(run.id, acknowledge_interrupted=True)
    assert completed.status == "succeeded"


def test_resume_refuses_another_model_or_concurrent_writer(tmp_path):
    engine = Engine(tmp_path, DemoModel())
    run = Run(
        id=uuid.uuid4().hex,
        task="test",
        workspace=str(tmp_path),
        provider="demo",
        model="deterministic-replay",
    )
    engine.store.save(run)
    with pytest.raises(ValueError, match="original provider"):
        Engine(tmp_path, ScriptedModel([])).advance(run.id)
    with engine.store.lock(run.id), pytest.raises(ValueError, match="already active"):
        engine.advance(run.id)


def test_reflection_retry_limit_prevents_infinite_loop(tmp_path):
    retry = {"verdict": "retry", "summary": "Need more evidence."}
    run = Engine(tmp_path, ScriptedModel([PLAN, DONE, retry, DONE, retry, DONE, retry])).new(
        "Inspect files"
    )
    assert run.status == "failed" and run.steps[0].attempts == 3


def test_run_studio_shows_real_results_and_has_no_execution_endpoint(tmp_path):
    engine = Engine(tmp_path, DemoModel(), Permissions(write=True, execute=True))
    run = engine.new("Build temperature conversions")
    with TestClient(create_app(tmp_path)) as client:
        assert client.get("/").status_code == 200
        assert client.get("/static/app.js").status_code == 200
        assert client.get("/api/health").json()["read_only"]
        assert client.get("/api/runs").json()[0]["id"] == run.id
        detail = client.get(f"/api/runs/{run.id}").json()
        assert len(detail["changes"]) == 2 and detail["events"]
        assert "workspace" not in detail["run"] and "base_url" not in detail["run"]
        assert client.post("/api/run", json={"task": "do something"}).status_code in {404, 405}
        assert client.get("/api/runs/missing").status_code == 404
