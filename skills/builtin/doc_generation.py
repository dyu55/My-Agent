"""Documentation Generation Skill - Auto-generate documentation from code."""

from __future__ import annotations

import re
from pathlib import Path

from skills.registry import BaseSkill, SkillContext


class DocGenerationSkill(BaseSkill):
    """Generate documentation from Python source code."""

    name = "doc-gen"
    description = "Generate README and API documentation from code"
    aliases = ["generate-docs", "gen-docs", "mkdocs", "document"]
    category = "documentation"

    def execute(self, context: SkillContext, args: str) -> str:
        """Generate documentation for the project."""
        params = self._parse_args(args)
        output_type = params.get("type", "readme").lower()
        output_path = params.get("output", "README.md")
        include_private = params.get("include-private") == None  # Flag to include private items

        # Generate documentation based on type
        if output_type == "readme":
            doc = self._generate_readme(context.workspace, include_private)
        elif output_type == "api":
            doc = self._generate_api_docs(context.workspace, include_private)
        elif output_type == "changelog":
            doc = self._generate_changelog_skeleton()
        else:
            doc = self._generate_readme(context.workspace, include_private)

        # Write or return
        output_file = context.workspace / output_path
        output_file.write_text(doc)

        return f"✅ Documentation generated: {output_path}\n\n```markdown\n{doc[:500]}...\n```"

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

    def _generate_readme(self, workspace: Path, include_private: bool) -> str:
        """Generate README.md content."""
        sections = ["# Project\n"]

        # Project overview
        overview = self._extract_project_overview(workspace)
        sections.append(overview)

        # Directory structure
        sections.append("\n## Project Structure\n")
        sections.append("```\n" + self._generate_tree(workspace, max_depth=2) + "\n```\n")

        # Installation
        sections.append("\n## Installation\n")
        if (workspace / "requirements.txt").exists():
            sections.append("```bash\npip install -r requirements.txt\n```\n")
        elif (workspace / "pyproject.toml").exists():
            sections.append("```bash\npip install -e .\n```\n")
        else:
            sections.append("```bash\npip install -e .\n```\n")

        # Usage
        sections.append("\n## Usage\n")
        sections.append("```python\n# TODO: Add usage examples\n```\n")

        # Key files documentation
        py_files = list(workspace.rglob("*.py"))
        if py_files:
            sections.append("\n## Key Files\n")
            for f in py_files[:5]:  # Top 5 files
                rel_path = f.relative_to(workspace)
                sections.append(f"- `{rel_path}`\n")

        # Contributing
        sections.append("\n## Contributing\n")
        sections.append("1. Fork the repository\n2. Create your feature branch\n3. Commit your changes\n4. Push to the branch\n5. Open a Pull Request\n")

        return "".join(sections)

    def _generate_api_docs(self, workspace: Path, include_private: bool) -> str:
        """Generate API documentation."""
        sections = ["# API Documentation\n"]

        py_files = list(workspace.rglob("*.py"))
        for file in py_files[:20]:  # Limit to 20 files
            try:
                content = file.read_text()
                rel_path = file.relative_to(workspace)

                sections.append(f"\n## `{rel_path}`\n")

                # Extract classes
                classes = re.findall(r"class (\w+)", content)
                for cls in classes:
                    if not include_private and cls.startswith("_"):
                        continue
                    sections.append(f"### class {cls}\n")
                    sections.append(f"*(defined in {rel_path})*\n\n")

                # Extract functions
                funcs = re.findall(r"def (\w+)\(", content)
                for func in funcs:
                    if not include_private and func.startswith("_"):
                        continue
                    sections.append(f"- `{func}()`\n")

            except Exception:
                pass

        return "".join(sections)

    def _generate_changelog_skeleton(self) -> str:
        """Generate a CHANGELOG skeleton."""
        from datetime import datetime

        date = datetime.now().strftime("%Y-%m-%d")
        return f"""# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [{datetime.now().strftime("%Y-%m-%d")}] - Unreleased

### Added
- Initial documentation skeleton

### Changed

### Deprecated

### Removed

### Fixed

### Security

---

## Template

## [0.0.1] - {date}

### Added
- Feature description

### Changed
- Change description

### Fixed
- Bug fix description
"""

    def _extract_project_overview(self, workspace: Path) -> str:
        """Extract project overview from existing files."""
        # Check for existing README
        readme_candidates = ["README.md", "readme.md", "README.txt"]
        for name in readme_candidates:
            path = workspace / name
            if path.exists():
                return path.read_text()[:1000]  # First 1000 chars

        # Check for pyproject.toml
        pyproject = workspace / "pyproject.toml"
        if pyproject.exists():
            try:
                content = pyproject.read_text()
                name_match = re.search(r'name\s*=\s*"([^"]+)"', content)
                desc_match = re.search(r'description\s*=\s*"([^"]+)"', content)

                name = name_match.group(1) if name_match else "Project"
                desc = desc_match.group(1) if desc_match else "Generated by MyAgent"

                return f"{name}\n\n{desc}\n"
            except Exception:
                pass

        return "Project generated by MyAgent\n"

    def _generate_tree(self, path: Path, max_depth: int = 2, current_depth: int = 0) -> str:
        """Generate a directory tree."""
        if current_depth >= max_depth:
            return ""

        lines = []
        indent = "  " * current_depth

        try:
            items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name))
            for i, item in enumerate(items):
                if item.name.startswith("."):
                    continue

                is_last = i == len(items) - 1
                prefix = "└── " if is_last else "├── "

                lines.append(f"{indent}{prefix}{item.name}")

                if item.is_dir():
                    subtree = self._generate_tree(item, max_depth, current_depth + 1)
                    if subtree:
                        lines.append(subtree)

        except Exception:
            pass

        return "\n".join(lines)