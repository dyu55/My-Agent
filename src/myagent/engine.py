from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from pathlib import Path

from pydantic import ValidationError

from .models import Decision, Limits, Permissions, Plan, Reflection, Run, Step
from .providers import ProviderError
from .sensitivity import Sensitivity, assess
from .store import RunStore
from .tools import ToolRegistry
from .workspace import Workspace


class BudgetReached(RuntimeError):
    pass


class Engine:
    def __init__(
        self,
        root: Path,
        model,
        permissions: Permissions | None = None,
        limits: Limits | None = None,
        on_event: Callable | None = None,
    ):
        self.store = RunStore(root)
        self.workspace = Workspace(root, self.store)
        self.model = model
        self.permissions = permissions or Permissions()
        self.limits = limits or Limits()
        self.on_event = on_event
        self.started = 0.0
        self.prior_elapsed = 0.0

    def event(self, run: Run, kind: str, payload: dict):
        self.store.event(run.id, kind, payload)
        if self.on_event:
            self.on_event(kind, payload)

    def remaining(self) -> float:
        return self.limits.max_seconds - self.prior_elapsed - (time.monotonic() - self.started)

    def call(self, run: Run, phase: str, payload: dict, schema):
        if run.calls >= self.limits.max_calls or self.remaining() <= 0:
            raise BudgetReached(
                "Run budget reached; increase --max-calls or --max-seconds to resume"
            )
        run.calls += 1
        self.store.save(run)
        self.model.timeout = min(60, self.remaining())
        result = self.model.complete(phase, payload, schema.model_json_schema())
        return schema.model_validate(result)

    def new(self, task: str) -> Run:
        if not task.strip() or len(task) > 12000:
            raise ValueError("Provide a task between 1 and 12,000 characters")
        assessment = assess(task)
        if assessment.level == Sensitivity.SECRET:
            raise ValueError("Secret material detected; remove it before starting an AI run")
        run = Run(
            id=uuid.uuid4().hex,
            task=task.strip(),
            workspace=str(self.workspace.root),
            provider=self.model.provider,
            model=self.model.model,
            base_url=self.model.base_url,
            sensitivity=assessment.level.name,
            routing=assessment.route,
            sensitivity_findings=[f"{f.level.name}: {f.label}" for f in assessment.findings],
        )
        self.store.save(run)
        self.event(run, "created", {"task": run.task, "provider": run.provider, "sensitivity": run.sensitivity, "routing": run.routing, "findings": run.sensitivity_findings})
        return self.advance(run.id)

    def advance(self, run_id: str, acknowledge_interrupted: bool = False) -> Run:
        with self.store.lock(run_id):
            run = self.store.load(run_id)
            if run.status == "succeeded":
                return run
            if run.status == "reverted":
                raise ValueError("A reverted run cannot resume; start a new task")
            if str(self.workspace.root) != run.workspace:
                raise ValueError("Run belongs to a different workspace")
            if (run.provider, run.model, run.base_url) != (
                self.model.provider,
                self.model.model,
                self.model.base_url,
            ):
                raise ValueError("Resume must use the original provider, model and endpoint")
            if run.pending_action:
                if not acknowledge_interrupted:
                    run.status = "paused"
                    run.summary = "A tool was interrupted and may already have changed files. Inspect the workspace and use --acknowledge-interrupted before resuming."
                    self.store.save(run)
                    return run
                self.event(run, "interruption_acknowledged", {"tool": run.pending_action.tool})
                run.pending_action = None
                run.needs_verification = True
                run.mutation_version += 1
            self.started, self.prior_elapsed = time.monotonic(), run.elapsed_seconds
            run.status, run.summary = "running", ""
            registry = ToolRegistry(
                self.workspace, run.id, self.permissions, self.limits.model_copy()
            )
            self.store.save(run)
            try:
                if not run.steps:
                    plan = self.call(
                        run,
                        "plan",
                        {
                            "task": run.task if run.routing == "external_allowed" else assess(run.task).redacted_text,
                            "sensitivity": run.sensitivity,
                            "routing": run.routing,
                            "repository": self.workspace.repo_map(),
                            "memories": self.store.recall(run.task),
                        },
                        Plan,
                    )
                    # The model proposes a DAG, but cannot set execution state or declare work done.
                    run.steps = [
                        Step(id=step.id, title=step.title, depends_on=step.depends_on)
                        for step in plan.steps
                    ]
                    self.store.save(run)
                    self.event(run, "planned", {"steps": [step.model_dump() for step in run.steps]})
                while any(step.status != "succeeded" for step in run.steps):
                    if self.remaining() <= 0:
                        raise BudgetReached("Run time budget reached")
                    completed = {step.id for step in run.steps if step.status == "succeeded"}
                    step = next(
                        (
                            step
                            for step in run.steps
                            if step.status != "succeeded" and set(step.depends_on) <= completed
                        ),
                        None,
                    )
                    if step is None:
                        raise ValueError("No runnable step; dependencies are incomplete")
                    step.status = "running"
                    self.store.save(run)
                    payload = {
                        "task": run.task,
                        "step": step.model_dump(),
                        "tools": registry.catalog(),
                        "recent_results": run.messages[-8:],
                        "repository": self.workspace.repo_map(),
                    }
                    decision = self.call(run, "act", payload, Decision)
                    if decision.complete:
                        if step.unresolved_tools or (
                            step.last_result and not step.last_result["ok"]
                        ):
                            step.attempts += 1
                            step.summary = (
                                "Resolve failed tool results before completing this step."
                            )
                            self.event(
                                run,
                                "completion_rejected",
                                {"step": step.id, "reason": step.summary},
                            )
                            if step.attempts > self.limits.max_retries:
                                step.status = "failed"
                                run.status, run.summary = "failed", step.summary
                                break
                            self.store.save(run)
                            continue
                        reflection = self.call(
                            run,
                            "reflect",
                            {
                                "task": run.task,
                                "step": step.model_dump(),
                                "proposed_summary": decision.summary,
                                "recent_results": run.messages[-8:],
                            },
                            Reflection,
                        )
                        self.event(run, "reflected", {"step": step.id, **reflection.model_dump()})
                        if reflection.verdict == "passed":
                            step.status, step.summary = (
                                "succeeded",
                                decision.summary or reflection.summary,
                            )
                            self.event(
                                run, "step_completed", {"step": step.id, "summary": step.summary}
                            )
                        elif reflection.verdict == "blocked":
                            run.status, run.summary = "paused", reflection.summary
                            break
                        else:
                            step.attempts += 1
                            step.summary = reflection.summary
                            if step.attempts > self.limits.max_retries:
                                step.status = "failed"
                                run.status, run.summary = "failed", "Reflection retry limit reached"
                                break
                        self.store.save(run)
                        continue
                    action = decision.action
                    if step.actions >= self.limits.max_actions_per_step:
                        raise BudgetReached(f"Action budget reached for step {step.id}")
                    permission = registry.check_permission(action)
                    if permission:
                        run.status = "paused"
                        run.summary = f"Tool {action.tool} requires --allow-{'exec' if permission == 'execute' else 'write'}. Resume with that permission to continue."
                        self.event(
                            run,
                            "permission_required",
                            {"step": step.id, "tool": action.tool, "permission": permission},
                        )
                        break
                    if self.remaining() <= 0:
                        raise BudgetReached("Run time budget reached before tool execution")
                    registry.limits.command_timeout = max(
                        0.001, min(self.limits.command_timeout, self.remaining())
                    )
                    run.pending_action = action
                    self.store.save(run)
                    self.event(run, "tool_started", {"step": step.id, "tool": action.tool})
                    result = registry.execute(action)
                    step.actions += 1
                    step.last_result = result.model_dump()
                    if result.ok:
                        step.unresolved_tools = [
                            name for name in step.unresolved_tools if name != action.tool
                        ]
                    elif action.tool not in step.unresolved_tools:
                        step.unresolved_tools.append(action.tool)
                    if action.tool == "run_command" or (result.ok and result.data.get("changed")):
                        run.mutation_version += 1
                        run.needs_verification = True
                    if action.tool == "run_tests" and result.ok:
                        run.verified_version = run.mutation_version
                    run.pending_action = None
                    run.messages.append(
                        {"tool": action.tool, "content": result.model_dump_json()[:20000]}
                    )
                    run.messages = run.messages[-20:]
                    self.event(
                        run,
                        "tool_completed",
                        {"step": step.id, "tool": action.tool, **result.model_dump()},
                    )
                    self.store.save(run)
                if all(step.status == "succeeded" for step in run.steps):
                    if run.needs_verification and run.verified_version != run.mutation_version:
                        run.status = "paused"
                        run.summary = "Changes are recorded, but tests have not passed after the latest mutation. Resume to verify."
                        verify_step = next((s for s in run.steps if s.id == "verify_final"), None)
                        if verify_step is None:
                            run.steps.append(
                                Step(
                                    id="verify_final",
                                    title="Run tests after the latest changes",
                                    depends_on=[s.id for s in run.steps],
                                )
                            )
                        else:
                            verify_step.status = "pending"
                    else:
                        run.status = "succeeded"
                        run.summary = "\n".join(step.summary for step in run.steps)
                        self.store.remember(run)
                self.event(run, run.status, {"summary": run.summary})
            except KeyboardInterrupt:
                run.status, run.summary = (
                    "paused",
                    "Interrupted. The checkpoint is saved; inspect any pending action before resuming.",
                )
                self.event(run, "paused", {"summary": run.summary})
            except (ProviderError, ValidationError, BudgetReached) as exc:
                run.status = "paused"
                run.summary = (
                    str(exc)[:2000]
                    if not isinstance(exc, ValidationError)
                    else "Model output did not match the required schema. Inspect the run and resume to retry."
                )
                self.event(run, "paused", {"summary": run.summary})
            except (ValueError, OSError) as exc:
                run.status, run.summary = "failed", str(exc)[:2000]
                self.event(run, "failed", {"summary": run.summary})
            finally:
                run.elapsed_seconds = round(self.prior_elapsed + time.monotonic() - self.started, 3)
                self.store.save(run)
            return run
