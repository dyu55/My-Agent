"""API Design Review Skill - Review and suggest API improvements."""

from __future__ import annotations

import re
from pathlib import Path

from skills.registry import BaseSkill, SkillContext


class ApiDesignSkill(BaseSkill):
    """Review API design and suggest improvements."""

    name = "api-design"
    description = "Review API design patterns and suggest improvements"
    aliases = ["review-api", "api-review", "api-check"]
    category = "development"

    # Common API design issues
    ISSUE_PATTERNS = {
        "inconsistent_naming": {
            "pattern": r"get_|set_|fetch_|load_|retrieve_",
            "message": "Inconsistent naming convention detected",
        },
        "missing_docstrings": {
            "pattern": r'def \w+\([^)]*\):\s*(?:\n\s*"""[^"]*""")?',
            "check": "has_docstring",
        },
        "long_parameter_lists": {
            "pattern": r"def \w+\(([^)]+)\)",
            "check": "param_count",
            "threshold": 5,
        },
        "inconsistent_return_types": {
            "pattern": r"return \w+",
            "check": "return_consistency",
        },
    }

    def execute(self, context: SkillContext, args: str) -> str:
        """Review API design in Python files."""
        params = self._parse_args(args)
        target_path = params.get("path") or params.get("_positional")

        if not target_path:
            files = list(context.workspace.rglob("*.py"))
        else:
            target = context.workspace / target_path if not Path(target_path).is_absolute() else Path(target_path)
            files = [target] if target.exists() else []

        if not files:
            return "❌ No Python files found to review."

        results = []
        for file in files[:10]:  # Limit to 10 files
            issues = self._review_file(file)
            if issues:
                results.append(f"\n📄 {file.relative_to(context.workspace)}:")
                for issue in issues:
                    results.append(f"  ⚠️  {issue}")

        if not results:
            return "✅ API design looks good! No major issues found."

        header = "🔍 API Design Review\n" + "=" * 40
        return header + "\n" + "\n".join(results) + "\n\n💡 See above for suggested improvements."

    def _parse_args(self, args: str) -> dict[str, str | None]:
        """Parse command-line style arguments."""
        params = {}
        if not args:
            return params

        parts = args.split()
        for i, part in enumerate(parts):
            if part.startswith("--"):
                param_name = part[2:].replace("-", "_")
                if i + 1 < len(parts) and not parts[i + 1].startswith("--"):
                    params[param_name] = parts[i + 1]
                else:
                    params[param_name] = None

        return params

    def _review_file(self, file: Path) -> list[str]:
        """Review a single file for API design issues."""
        issues = []

        try:
            content = file.read_text()
            lines = content.splitlines()

            for i, line in enumerate(lines, 1):
                # Check for long function definitions
                if line.strip().startswith("def "):
                    func_issues = self._check_function_def(line, file.name)
                    issues.extend(func_issues)

                # Check for missing type hints
                if "def " in line and ":" in line and " -> " not in line:
                    # Skip if it has a docstring (may have return type there)
                    pass  # Could be enhanced to check docstrings

            # Check naming conventions
            naming_issues = self._check_naming_consistency(content)
            issues.extend(naming_issues)

        except Exception:
            issues.append("Could not read file for review")

        return issues

    def _check_function_def(self, line: str, filename: str) -> list[str]:
        """Check a function definition for issues."""
        issues = []

        # Check parameter count
        match = re.search(r"def \w+\(([^)]+)\)", line)
        if match:
            params = match.group(1)
            if params.strip():
                param_list = [p.strip() for p in params.split(",")]
                # Count args and kwargs
                param_count = len([p for p in param_list if p and not p.startswith("*")])
                if param_count > 5:
                    issues.append(
                        f"Line {line.strip()[:50]}...: Long parameter list ({param_count} params). "
                        "Consider grouping into a config/dto object."
                    )

        return issues

    def _check_naming_consistency(self, content: str) -> list[str]:
        """Check for naming convention consistency."""
        issues = []

        # Find all function definitions
        funcs = re.findall(r"def (get|set|fetch|load|retrieve|create|update|delete)_\w+\(", content)

        # Check if there's mixing of prefixes
        prefixes = set()
        for match in funcs:
            prefixes.add(match)

        # If multiple prefix styles are used, flag it
        if len(prefixes) > 1:
            issue = (
                f"Inconsistent API prefix style detected: {', '.join(sorted(prefixes))}. "
                "Pick one style (e.g., get_ vs fetch_) and stick to it."
            )
            issues.append(issue)

        return issues

    def suggest_improvements(self, issues: list[str]) -> str:
        """Generate improvement suggestions based on detected issues."""
        suggestions = []

        for issue in issues:
            if "parameter" in issue.lower():
                suggestions.append(
                    "- Group related parameters into a configuration object or data class"
                )
            if "naming" in issue.lower():
                suggestions.append(
                    "- Standardize naming conventions across the API"
                )
            if "return" in issue.lower():
                suggestions.append(
                    "- Ensure consistent return types or use Optional/Result types"
                )

        if suggestions:
            return "\n💡 Suggestions:\n" + "\n".join(suggestions)
        return ""