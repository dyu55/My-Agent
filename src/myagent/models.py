from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


def now() -> str:
    return datetime.now(UTC).isoformat()


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Step(StrictModel):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,40}$")
    title: str = Field(min_length=1, max_length=250)
    depends_on: list[str] = Field(default_factory=list, max_length=12)
    status: Literal["pending", "running", "succeeded", "failed"] = "pending"
    summary: str = ""
    actions: int = 0
    attempts: int = 0
    last_result: dict[str, Any] | None = None
    unresolved_tools: list[str] = Field(default_factory=list)


class Plan(StrictModel):
    steps: list[Step] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def acyclic(self):
        ids = {step.id for step in self.steps}
        if len(ids) != len(self.steps):
            raise ValueError("Step IDs must be unique")
        resolved = set()
        while len(resolved) < len(ids):
            ready = {
                step.id
                for step in self.steps
                if step.id not in resolved and set(step.depends_on) <= resolved
            }
            if not ready:
                raise ValueError("Plan contains unknown dependencies or a cycle")
            resolved.update(ready)
        return self


class Action(StrictModel):
    tool: str = Field(min_length=1, max_length=60)
    arguments: dict[str, Any] = Field(default_factory=dict)


class Decision(StrictModel):
    action: Action | None = None
    complete: bool = False
    summary: str = Field(default="", max_length=3000)

    @model_validator(mode="after")
    def one_decision(self):
        if (self.action is not None) == self.complete:
            raise ValueError("Return either an action or complete=true, exclusively")
        return self


class Reflection(StrictModel):
    verdict: Literal["passed", "retry", "blocked"]
    summary: str = Field(min_length=1, max_length=3000)


class ToolResult(StrictModel):
    ok: bool
    output: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
    error: str = ""
    requires_permission: str = ""


class Run(BaseModel):
    id: str
    task: str
    workspace: str
    provider: str
    model: str
    status: Literal["pending", "running", "paused", "failed", "succeeded", "reverted"] = "pending"
    created_at: str = Field(default_factory=now)
    updated_at: str = Field(default_factory=now)
    steps: list[Step] = Field(default_factory=list)
    summary: str = ""
    calls: int = 0
    elapsed_seconds: float = 0
    pending_action: Action | None = None
    messages: list[dict[str, str]] = Field(default_factory=list)
    mutation_version: int = 0
    verified_version: int = -1
    needs_verification: bool = False
    base_url: str = ""
    sensitivity: str = "PUBLIC"
    routing: str = "external_allowed"
    sensitivity_findings: list[str] = Field(default_factory=list)


class Limits(StrictModel):
    max_calls: int = Field(default=40, ge=1, le=300)
    max_seconds: float = Field(default=600, gt=0, le=7200)
    max_actions_per_step: int = Field(default=12, ge=1, le=50)
    max_retries: int = Field(default=2, ge=0, le=5)
    command_timeout: float = Field(default=60, gt=0, le=300)


class Permissions(StrictModel):
    write: bool = False
    execute: bool = False
