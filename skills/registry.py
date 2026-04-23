"""Skills System - Custom agent capabilities."""

import json
import os
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


@dataclass
class Skill:
    """Represents a custom skill/capability."""

    name: str
    description: str
    trigger: str  # Command to invoke, e.g., "/code-review"
    handler: Callable[..., str]
    aliases: list[str] = field(default_factory=list)
    category: str = "general"

    def matches(self, input_str: str) -> bool:
        """Check if input matches this skill's trigger or aliases."""
        name = input_str.strip().split()[0].lower() if input_str else ""
        trigger_name = self.trigger.strip().lower()
        return (
            name == trigger_name
            or name in [a.lower() for a in self.aliases]
            or name == f"/{self.name.replace('_', '-')}"
        )


@dataclass
class SkillContext:
    """Context available during skill execution."""

    workspace: Path
    model: str
    provider: str
    current_task: str | None = None
    additional_data: dict[str, Any] = field(default_factory=dict)


class BaseSkill(ABC):
    """Base class for skills."""

    name: str = ""
    description: str = ""
    aliases: list[str] = []
    category: str = "general"

    @abstractmethod
    def execute(self, context: SkillContext, args: str) -> str:
        """Execute the skill with given context and arguments."""
        pass

    def get_trigger(self) -> str:
        """Get the trigger command."""
        return f"/{self.name.replace('_', '-')}"

    def to_skill(self) -> Skill:
        """Convert to Skill dataclass."""
        return Skill(
            name=self.name,
            description=self.description,
            trigger=self.get_trigger(),
            handler=self.execute_wrapper,
            aliases=self.aliases,
            category=self.category,
        )

    def execute_wrapper(self, context: SkillContext, args: str) -> str:
        """Wrapper to call the skill's execute method."""
        return self.execute(context, args)


class CodeReviewSkill(BaseSkill):
    """Code review skill."""

    name = "code-review"
    description = "Review code for issues, bugs, and improvements"
    aliases = ["review", "cr"]
    category = "development"

    def execute(self, context: SkillContext, args: str) -> str:
        """Run code review on workspace files."""
        files = list(context.workspace.rglob("*.py"))

        if not files:
            return "No Python files found in workspace."

        results = []
        for file in files:
            issues = self._review_file(file)
            if issues:
                results.append(f"\n📄 {file.name}:\n" + "\n".join(f"  - {i}" for i in issues))

        return (
            "📋 Code Review Results\n" + ("=" * 40) + "\n"
            + ("\n".join(results) if results else "✅ No issues found!")
        )

    def _review_file(self, file: Path) -> list[str]:
        """Review a single file."""
        issues = []
        try:
            content = file.read_text()

            # Check for common issues
            if "TODO" in content or "FIXME" in content:
                issues.append("Contains TODO/FIXME comments")

            if "print(" in content and "debug" not in file.name.lower():
                issues.append("Contains debug print statements")

            if "except:" in content:
                issues.append("Uses bare except clause")

            if len(content.splitlines()) > 300:
                issues.append("File is too long (>300 lines)")

        except Exception:
            issues.append("Could not read file")

        return issues


class SecurityReviewSkill(BaseSkill):
    """Security review skill."""

    name = "security-review"
    description = "Review code for security vulnerabilities"
    aliases = ["security", "sec"]
    category = "security"

    SECURITY_PATTERNS = {
        "hardcoded_password": r'password\s*=\s*["\'][^"\']+["\']',
        "sql_injection": r'execute\s*\([^)]*%\s*\(',
        "eval_usage": r'\beval\s*\(',
        "shell_injection": r'subprocess.*shell\s*=\s*True',
        "insecure_yaml": r'yaml\.load\s*\(',
    }

    def execute(self, context: SkillContext, args: str) -> str:
        """Run security review on workspace files."""
        files = list(context.workspace.rglob("*.py"))

        if not files:
            return "No Python files found in workspace."

        results = []
        for file in files:
            issues = self._scan_file(file)
            if issues:
                results.append(f"\n🔒 {file.name}:\n" + "\n".join(f"  ⚠️  {i}" for i in issues))

        return (
            "🔒 Security Review Results\n" + ("=" * 40) + "\n"
            + ("\n".join(results) if results else "✅ No security issues found!")
        )

    def _scan_file(self, file: Path) -> list[str]:
        """Scan a single file for security issues."""
        import re

        issues = []
        try:
            content = file.read_text()

            for issue_type, pattern in self.SECURITY_PATTERNS.items():
                if re.search(pattern, content, re.IGNORECASE):
                    issues.append(f"Potential {issue_type.replace('_', ' ')}")

        except Exception:
            pass

        return issues


class InitSkill(BaseSkill):
    """Initialize CLAUDE.md file with project documentation."""

    name = "init"
    description = "Initialize CLAUDE.md with project documentation"
    aliases = ["init-project"]
    category = "setup"

    def execute(self, context: SkillContext, args: str) -> str:
        """Create or update CLAUDE.md."""
        claude_md = context.workspace / "CLAUDE.md"

        template = f"""# Project Documentation

Generated by michael on {Path().resolve().name}

## Project Overview
{args or "Project created by michael agent"}

## Directory Structure
```
{self._generate_tree(context.workspace)}
```

## Key Files
{self._list_key_files(context.workspace)}

## Notes
- This file helps the agent understand your project
- Update as needed
"""

        claude_md.write_text(template)
        return f"✅ CLAUDE.md created at {claude_md}"

    def _generate_tree(self, path: Path, max_depth: int = 2, current_depth: int = 0) -> str:
        """Generate directory tree."""
        if current_depth >= max_depth:
            return "..."

        lines = []
        try:
            for item in sorted(path.iterdir()):
                if item.name.startswith("."):
                    continue

                prefix = "├── " if item != sorted(path.iterdir(), key=lambda x: x.is_dir())[-1] else "└── "
                lines.append(f"{prefix}{item.name}")

                if item.is_dir():
                    subtree = self._generate_tree(item, max_depth, current_depth + 1)
                    for line in subtree.split("\n"):
                        lines.append("    " + line)

        except Exception:
            pass

        return "\n".join(lines)

    def _list_key_files(self, path: Path) -> str:
        """List key files in the project."""
        key_patterns = ["*.py", "*.md", "*.json", "*.yaml", "*.txt", "requirements.txt"]
        key_files = []

        for pattern in key_patterns:
            key_files.extend(path.rglob(pattern))

        return "\n".join(f"- {f.relative_to(path)}" for f in key_files[:10])


class SimplifySkill(BaseSkill):
    """Code simplification and refactoring skill."""

    name = "simplify"
    description = "Review code for reuse, quality, and efficiency, then fix issues"
    aliases = ["refactor", "clean"]
    category = "development"

    def execute(self, context: SkillContext, args: str) -> str:
        """Simplify code in workspace."""
        files = list(context.workspace.rglob("*.py"))

        if not files:
            return "No Python files found in workspace."

        improvements = []
        for file in files:
            result = self._analyze_file(file)
            if result:
                improvements.append(f"\n📝 {file.name}:\n" + "\n".join(f"  → {i}" for i in result))

        return (
            "🔧 Simplification Results\n" + ("=" * 40) + "\n"
            + ("\n".join(improvements) if improvements else "✅ Code looks clean!")
        )

    def _analyze_file(self, file: Path) -> list[str]:
        """Analyze file for simplification opportunities."""
        improvements = []
        try:
            content = file.read_text()
            lines = content.splitlines()

            # Check for repeated code patterns
            if len(set(lines)) < len(lines) * 0.7:
                improvements.append("Contains repeated code patterns")

            # Check function length
            for i, line in enumerate(lines, 1):
                if line.strip().startswith("def "):
                    # Find function end
                    indent = len(line) - len(line.lstrip())
                    end = i + 1
                    for j in range(i, min(i + 100, len(lines))):
                        if lines[j].strip() and not lines[j].startswith(" " * (indent + 1)):
                            end = j
                            break

                    func_length = end - i
                    if func_length > 50:
                        improvements.append(f"Function at line {i} is too long ({func_length} lines)")

        except Exception:
            pass

        return improvements


class SkillRegistry:
    """Registry for all available skills."""

    def __init__(self):
        self.skills: list[Skill] = []
        self._register_builtins()

    def _register_builtins(self) -> None:
        """Register built-in skills."""
        builtins = [
            CodeReviewSkill(),
            SecurityReviewSkill(),
            InitSkill(),
            SimplifySkill(),
        ]

        for skill in builtins:
            self.register(skill.to_skill())

    def register(self, skill: Skill) -> None:
        """Register a new skill."""
        self.skills.append(skill)

    def find(self, trigger: str) -> Skill | None:
        """Find a skill by trigger."""
        for skill in self.skills:
            if skill.matches(trigger):
                return skill
        return None

    def list_by_category(self) -> dict[str, list[Skill]]:
        """List skills grouped by category."""
        categories = {}
        for skill in self.skills:
            if skill.category not in categories:
                categories[skill.category] = []
            categories[skill.category].append(skill)
        return categories

    def get_help(self) -> str:
        """Get help text for all skills."""
        categories = self.list_by_category()
        lines = ["📚 Available Skills:\n"]

        for category, skills in categories.items():
            lines.append(f"\n### {category.title()}")
            for skill in skills:
                aliases = f" ({', '.join(skill.aliases)})" if skill.aliases else ""
                lines.append(f"  {skill.trigger}{aliases} - {skill.description}")

        return "\n".join(lines)


def create_skill_registry() -> SkillRegistry:
    """Create a skill registry with default skills."""
    return SkillRegistry()