"""Skill Templates - Generate scaffold code for new skills."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# Template for new skill files
SKILL_FILE_TEMPLATE = '''"""Generated skill: {skill_name}."""

from skills.registry import BaseSkill, SkillContext


class {class_name}(BaseSkill):
    """Auto-generated skill."""

    name = "{skill_name}"
    description = "{description}"
    aliases = {aliases}
    category = "{category}"

    def execute(self, context: SkillContext, args: str) -> str:
        \"\"\"Execute the skill.

        Args:
            context: Skill execution context
            args: Arguments (can be parsed with SkillEngine.parse_args)

        Returns:
            Result string describing what was done
        \"\"\"
        # TODO: Implement skill logic
        return "Skill '{name}' executed successfully"
'''


# Template for skill documentation
SKILL_DOC_TEMPLATE = '''# {skill_name}

## Description
{description}

## Usage
```
{syntax}
```

## Parameters

{parameters}

## Examples

### Basic Usage
```
{syntax_example}
```

### With Options
```
{syntax_with_options}
```

## Notes

{notes}
'''


@dataclass
class SkillSpec:
    """Specification for a new skill."""

    name: str
    description: str
    category: str = "custom"
    aliases: list[str] = field(default_factory=list)
    parameters: list[dict[str, Any]] = field(default_factory=list)
    notes: str = ""

    @property
    def class_name(self) -> str:
        """Convert name to PascalCase class name."""
        return "".join(word.capitalize() for word in self.name.replace("-", "_").split("_"))

    @property
    def trigger(self) -> str:
        """Get the trigger command."""
        return f"/{self.name.replace('_', '-')}"


class SkillTemplateEngine:
    """
    Generate scaffold code for new skills.

    Usage:
        engine = SkillTemplateEngine()
        code = engine.create_skill(SkillSpec(
            name="my-skill",
            description="Does something useful"
        ))
        print(code)
    """

    def create_skill(self, spec: SkillSpec) -> str:
        """
        Generate skill file content from specification.

        Args:
            spec: Skill specification

        Returns:
            Python code for the new skill
        """
        return SKILL_FILE_TEMPLATE.format(
            skill_name=spec.name,
            class_name=spec.class_name,
            description=spec.description,
            aliases=spec.aliases,
            category=spec.category,
            name=spec.name,
        )

    def create_documentation(self, spec: SkillSpec) -> str:
        """
        Generate documentation for a skill.

        Args:
            spec: Skill specification

        Returns:
            Markdown documentation for the skill
        """
        # Build parameters section
        if spec.parameters:
            params_lines = []
            for param in spec.parameters:
                required = "Required" if param.get("required", True) else "Optional"
                default = f" (default: {param['default']})" if "default" in param else ""
                params_lines.append(f"- `{param['name']}`: {param['description']} ({required}){default}")
            parameters = "\n".join(params_lines)
        else:
            parameters = "No parameters required."

        # Build syntax example
        param_parts = " ".join(f"--{p['name']} <value>" for p in spec.parameters if p.get("required", True))
        syntax = f"{spec.trigger} {param_parts}".strip()
        syntax_example = f"{spec.trigger} {' '.join('--' + p['name'] + ' test' for p in spec.parameters[:2] if p.get('required', True))}"
        syntax_with_options = f"{spec.trigger} {' '.join('--' + p['name'] + ' value' for p in spec.parameters)}"

        return SKILL_DOC_TEMPLATE.format(
            skill_name=spec.name,
            description=spec.description,
            syntax=syntax,
            parameters=parameters,
            syntax_example=syntax_example,
            syntax_with_options=syntax_with_options,
            notes=spec.notes or "No additional notes.",
        )

    def create_skill_with_docs(self, spec: SkillSpec) -> dict[str, str]:
        """
        Generate both skill code and documentation.

        Args:
            spec: Skill specification

        Returns:
            Dict with 'code' and 'docs' keys
        """
        return {
            "code": self.create_skill(spec),
            "docs": self.create_documentation(spec),
        }

    def generate_test_scaffold(self, spec: SkillSpec) -> str:
        """
        Generate test scaffold for a skill.

        Args:
            spec: Skill specification

        Returns:
            Test code for the new skill
        """
        class_name = spec.class_name
        trigger = spec.trigger

        return f'''"""Tests for {spec.name} skill."""

import pytest
from pathlib import Path

from skills.registry import SkillContext
from skills.builtin.{spec.name} import {class_name}


class Test{class_name}:
    """Tests for {class_name}."""

    @pytest.fixture
    def context(self, tmp_path):
        """Create test context."""
        return SkillContext(
            workspace=tmp_path,
            model="test-model",
            provider="test"
        )

    def test_execute_basic(self, context):
        """Test basic skill execution."""
        skill = {class_name}()
        result = skill.execute(context, "")

        assert result is not None
        assert "{spec.name}" in result.lower() or len(result) > 0

    def test_trigger_matching(self):
        """Test that trigger pattern works."""
        skill = {class_name}()
        trigger = skill.get_trigger()

        assert trigger == "{trigger}"

    def test_help_text(self):
        """Test help text generation."""
        skill = {class_name}()
        skill_obj = skill.to_skill()

        assert skill_obj.name == "{spec.name}"
        assert skill_obj.description == "{spec.description}"
'''


def create_skill_from_dict(spec: dict[str, Any]) -> str:
    """
    Create a new skill from a dictionary specification.

    Convenience function for quick skill creation.

    Args:
        spec: Dict with 'name', 'description', etc.

    Returns:
        Python code for the skill
    """
    skill_spec = SkillSpec(**spec)
    engine = SkillTemplateEngine()
    return engine.create_skill(skill_spec)