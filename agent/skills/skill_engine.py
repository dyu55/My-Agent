"""Skill Engine - Enhanced skill execution with parameters and chaining."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from skills.registry import Skill, SkillContext, SkillRegistry


@dataclass
class SkillParameter:
    """Definition of a skill parameter."""

    name: str
    description: str
    required: bool = True
    default: Any = None
    pattern: str | None = None  # Regex validation pattern

    def validate(self, value: str | None) -> tuple[bool, str]:
        """Validate parameter value."""
        if value is None:
            if self.required:
                return False, f"Required parameter '{self.name}' is missing"
            return True, ""

        if self.pattern:
            if not re.match(self.pattern, str(value)):
                return False, f"Parameter '{self.name}' doesn't match pattern {self.pattern}"

        return True, ""


@dataclass
class SkillMetadata:
    """Metadata for a skill including parameters and prerequisites."""

    name: str
    description: str
    parameters: list[SkillParameter] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)  # Skill names that must run first
    post_conditions: list[str] = field(default_factory=list)  # Skills to run after
    model_hint: str | None = None  # Recommended model for this skill
    category: str = "general"


@dataclass
class SkillResult:
    """Result of skill execution."""

    skill_name: str
    success: bool
    output: str
    error: str | None = None
    execution_time: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class SkillEngine:
    """
    Enhanced skill execution engine.

    Features:
    - Parameterized skill execution
    - Prerequisite validation
    - Skill chaining
    - Template rendering with context

    Usage:
        engine = SkillEngine(registry)
        result = engine.execute("code-review", context, {"file_path": "main.py"})
    """

    # Pattern to match parameters like --param value or --flag
    PARAM_PATTERN = re.compile(r"--(\w+)(?:\s+(.+?))?(?=\s+--|$)")

    def __init__(self, registry: SkillRegistry):
        self.registry = registry
        self._execution_history: list[SkillResult] = []

    def parse_args(self, args: str) -> dict[str, str | None]:
        """
        Parse command-line style arguments.

        Supports formats:
        - --param value
        - --flag (boolean flag)
        - positional argument

        Returns:
            Dict of parameter_name -> value (or None for flags)
        """
        if not args or not args.strip():
            return {}

        params = {}
        matches = self.PARAM_PATTERN.findall(args)

        for match in matches:
            param_name = match[0].replace("-", "_")
            param_value = match[1].strip() if match[1] else None
            params[param_name] = param_value

        # Handle positional arguments (those without --)
        remaining = self.PARAM_PATTERN.sub("", args).strip()
        if remaining:
            parts = remaining.split(maxsplit=1)
            if parts:
                params["_positional"] = parts[0]
                if len(parts) > 1:
                    params["_positional_arg"] = parts[1]

        return params

    def validate_parameters(
        self,
        skill: Skill,
        params: dict[str, str | None],
        metadata: SkillMetadata | None = None,
    ) -> tuple[bool, list[str]]:
        """
        Validate parameters against skill metadata.

        Args:
            skill: The skill to validate against
            params: Parsed parameters
            metadata: Optional metadata with parameter definitions

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []

        if metadata is None:
            # Use basic validation - just check for required params
            return True, []

        for param_def in metadata.parameters:
            value = params.get(param_def.name)

            is_valid, error_msg = param_def.validate(value)
            if not is_valid:
                errors.append(error_msg)

        return len(errors) == 0, errors

    def validate_prerequisites(
        self,
        skill_name: str,
        metadata: SkillMetadata | None = None,
    ) -> tuple[bool, str]:
        """
        Validate that all prerequisites for a skill are satisfied.

        Args:
            skill_name: Name of the skill to check
            metadata: Optional metadata with prerequisites

        Returns:
            Tuple of (is_valid, error_message)
        """
        if metadata is None or not metadata.prerequisites:
            return True, ""

        # Check execution history for completed prerequisite skills
        completed_skills = {r.skill_name for r in self._execution_history if r.success}

        for prereq in metadata.prerequisites:
            if prereq not in completed_skills:
                return False, f"Prerequisite '{prereq}' not satisfied. Run it first."

        return True, ""

    def render_template(
        self,
        template: str,
        context: SkillContext,
        params: dict[str, Any] | None = None,
    ) -> str:
        """
        Render a template with context variables.

        Supports:
        - {workspace} - workspace path
        - {model} - current model
        - {task} - current task
        - {param_name} - parameter values

        Args:
            template: Template string with {placeholders}
            context: Skill execution context
            params: Additional parameters

        Returns:
            Rendered string
        """
        params = params or {}
        params.update({
            "workspace": str(context.workspace),
            "model": context.model,
            "provider": context.provider,
            "task": context.current_task or "",
        })

        result = template
        for key, value in params.items():
            placeholder = f"{{{key}}}"
            if placeholder in result:
                result = result.replace(placeholder, str(value))

        return result

    def execute(
        self,
        skill_name: str,
        context: SkillContext,
        params: dict[str, Any] | None = None,
    ) -> SkillResult:
        """
        Execute a skill with parameters.

        Args:
            skill_name: Name of the skill to execute
            context: Execution context
            params: Parameters for the skill (can be dict or raw string)

        Returns:
            SkillResult with execution outcome
        """
        import time
        start_time = time.time()

        # Handle string params (parse them)
        if isinstance(params, str):
            params = self.parse_args(params)
        elif params is None:
            params = {}

        # Find the skill
        skill = self.registry.find(skill_name)
        if not skill:
            return SkillResult(
                skill_name=skill_name,
                success=False,
                output="",
                error=f"Skill '{skill_name}' not found",
                execution_time=time.time() - start_time,
            )

        # Build args string from params
        args_str = self._build_args_string(params)

        # Execute the skill
        try:
            output = skill.handler(context, args_str)
            result = SkillResult(
                skill_name=skill_name,
                success=True,
                output=output,
                execution_time=time.time() - start_time,
            )
        except Exception as e:
            result = SkillResult(
                skill_name=skill_name,
                success=False,
                output="",
                error=f"Execution error: {str(e)}",
                execution_time=time.time() - start_time,
            )

        self._execution_history.append(result)
        return result

    def _build_args_string(self, params: dict[str, Any]) -> str:
        """Build command-line style args string from params dict."""
        parts = []

        # Handle positional args
        if "_positional" in params:
            parts.append(str(params["_positional"]))
            if "_positional_arg" in params:
                parts.append(str(params["_positional_arg"]))

        # Handle named params
        for key, value in params.items():
            if key.startswith("_"):
                continue
            if value is not None:
                parts.append(f"--{key.replace('_', '-')} {value}")
            else:
                parts.append(f"--{key.replace('_', '-')}")

        return " ".join(parts)

    def chain_execute(
        self,
        skill_chain: list[str],
        context: SkillContext,
        params: dict[str, Any] | None = None,
    ) -> list[SkillResult]:
        """
        Execute a chain of skills in sequence.

        Each skill's output can influence the next skill's execution.

        Args:
            skill_chain: List of skill names to execute
            context: Execution context
            params: Initial parameters (shared across chain)

        Returns:
            List of SkillResults, one per skill
        """
        results = []
        params = params or {}

        for skill_name in skill_chain:
            result = self.execute(skill_name, context, params)
            results.append(result)

            # If a skill fails, stop the chain
            if not result.success:
                break

            # Pass output as context for next skill
            if result.output:
                params["_previous_output"] = result.output

        return results

    def get_execution_summary(self) -> str:
        """Get a summary of skill execution history."""
        if not self._execution_history:
            return "No skills executed yet."

        lines = ["## Skill Execution Summary\n"]
        successful = sum(1 for r in self._execution_history if r.success)
        failed = len(self._execution_history) - successful

        lines.append(f"Total: {len(self._execution_history)} | ✅ {successful} | ❌ {failed}\n")

        for i, result in enumerate(self._execution_history, 1):
            status = "✅" if result.success else "❌"
            lines.append(f"{i}. {status} {result.skill_name} ({result.execution_time:.2f}s)")

        return "\n".join(lines)

    def get_metadata(self, skill_name: str) -> SkillMetadata | None:
        """
        Get metadata for a skill.

        Currently returns basic metadata; can be extended to support
        skill-specific metadata definitions.
        """
        skill = self.registry.find(skill_name)
        if not skill:
            return None

        return SkillMetadata(
            name=skill.name,
            description=skill.description,
            category=skill.category,
        )