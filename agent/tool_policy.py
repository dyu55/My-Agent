"""Local policy checks for tool execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


SENSITIVE_ACTION_FIELDS = {"content", "script", "packages", "git_args"}


@dataclass
class ToolPolicyDecision:
    """Decision returned by a tool policy check."""

    status: str
    reason: str | None = None
    observed: bool = False

    @property
    def allows_execution(self) -> bool:
        return self.status == "allowed" or self.observed


@dataclass
class ToolPolicy:
    """Small, dependency-free command policy for local tool execution."""

    allowed_commands: set[str] | None = None
    blocked_commands: set[str] = field(default_factory=set)
    approval_required_commands: set[str] = field(default_factory=set)
    observe: bool = False
    audit_log: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_config(cls, config: dict[str, Any] | "ToolPolicy" | None) -> "ToolPolicy":
        """Build a policy from an existing policy or a plain config dict."""
        if isinstance(config, cls):
            return config
        if config is None:
            return cls()
        return cls(
            allowed_commands=set(config["allowed_commands"])
            if config.get("allowed_commands") is not None else None,
            blocked_commands=set(config.get("blocked_commands", [])),
            approval_required_commands=set(
                config.get("approval_required_commands", [])
            ),
            observe=bool(config.get("observe", False)),
        )

    def evaluate(
        self,
        command: str,
        action_payload: dict[str, Any],
    ) -> ToolPolicyDecision:
        """Evaluate whether a command may execute and record an audit entry."""
        status = "allowed"
        reason = None

        if command in self.blocked_commands:
            status = "blocked"
            reason = f"Command '{command}' is blocked by tool policy"
        elif (
            self.allowed_commands is not None
            and command not in self.allowed_commands
        ):
            status = "blocked"
            reason = f"Command '{command}' is not in the tool policy allowlist"
        elif command in self.approval_required_commands:
            status = "approval_required"
            reason = f"Command '{command}' requires approval by tool policy"

        observed = self.observe and status != "allowed"
        decision = ToolPolicyDecision(status=status, reason=reason, observed=observed)
        self.audit_log.append(
            {
                "command": command,
                "status": status,
                "observed": observed,
                "reason": reason,
                "action": self._redact_action(action_payload),
            }
        )
        return decision

    def _redact_action(self, action_payload: dict[str, Any]) -> dict[str, Any]:
        """Remove potentially sensitive action fields from audit records."""
        redacted = {}
        for key, value in action_payload.items():
            if key in SENSITIVE_ACTION_FIELDS and value:
                redacted[key] = "[redacted]"
            else:
                redacted[key] = value
        return redacted
