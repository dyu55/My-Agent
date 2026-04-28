"""Dependency Tools - Analyze and manage Python dependencies."""

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Dependency:
    """A Python dependency."""
    name: str
    version: str | None = None
    is_direct: bool = True  # Direct vs transitive dependency
    source: str | None = None  # requirements.txt, setup.py, etc.
    imports: list[str] = field(default_factory=list)


@dataclass
class DependencyAnalysis:
    """Result of dependency analysis."""
    dependencies: list[Dependency]
    missing: list[str]
    outdated: list[dict[str, str]]
    conflicts: list[str]
    orphan_imports: list[str]


class DependencyTools:
    """Tools for analyzing and managing dependencies."""

    def __init__(self, workspace_path: str):
        self.workspace = Path(workspace_path)

    def analyze_imports(self, path: str | None = None) -> list[str]:
        """
        Analyze all imports in Python files.

        Args:
            path: Directory to analyze (defaults to workspace)

        Returns:
            List of import names
        """
        search_path = self.workspace if path is None else Path(path)
        all_imports = []

        for py_file in search_path.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue

            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # Parse imports
                imports = self._extract_imports(content)
                all_imports.extend(imports)

            except Exception:
                continue

        # Remove duplicates and sort
        return sorted(set(all_imports))

    def _extract_imports(self, content: str) -> list[str]:
        """Extract import statements from Python code."""
        imports = []

        # Match: import x, from x import y
        patterns = [
            r"^(?:from\s+)?([a-zA-Z_][a-zA-Z0-9_\.]+)",
            r"^import\s+([a-zA-Z_][a-zA-Z0-9_\.]+)",
        ]

        for line in content.split("\n"):
            line = line.strip()
            for pattern in patterns:
                match = re.search(pattern, line)
                if match:
                    module = match.group(1).split(".")[0]
                    # Filter out stdlib and local imports
                    stdlib = {
                        "os", "sys", "json", "re", "math", "time", "datetime",
                        "pathlib", "typing", "collections", "itertools", "functools",
                        "string", "random", "uuid", "hashlib", "pickle", "shelve",
                        "logging", "warnings", "copy", "abc", "enum", "dataclasses",
                        "contextlib", "heapq", "bisect", "deque", "defaultdict",
                        "subprocess", "threading", "multiprocessing", "asyncio",
                        "socket", "http", "urllib", "html", "xml", "csv", "io",
                        "configparser", "argparse", "getpass", "tempfile", "shutil",
                        "zipfile", "tarfile", "gzip", "zlib", "base64", "binascii",
                        "struct", "codecs", "locale", "atexit", "gc", "weakref",
                        "types", "inspect", "traceback", "sysconfig", "platform",
                        "unittest", "doctest", "ast", "dis", "compiler", "code",
                        "fractions", "decimal", "numbers", "cmath", "statistics",
                        "array", "cmath", "operator", "reprlib", "textwrap",
                        "stringprep", "readline", "rlcompleter", "cmd", "shlex",
                        "typing", "concurrent", "contextvars", "dataclasses",
                        "graphlib", "graphlib", "pprint", "pprint"
                    }

                    # Filter out local imports (starting with .)
                    if module not in stdlib and not module.startswith("_"):
                        imports.append(module)

        return imports

    def check_installed(self, packages: list[str]) -> dict[str, bool]:
        """
        Check which packages are installed.

        Args:
            packages: List of package names to check

        Returns:
            Dict mapping package name to installed status
        """
        results = {}

        for package in packages:
            try:
                __import__(package)
                results[package] = True
            except ImportError:
                # Try alternative names
                alt_names = [
                    package.replace("-", "_"),
                    package.replace("_", "-"),
                ]
                found = False
                for alt in alt_names:
                    try:
                        __import__(alt)
                        results[package] = True
                        found = True
                        break
                    except ImportError:
                        continue

                if not found:
                    results[package] = False

        return results

    def generate_requirements(
        self,
        path: str | None = None,
        output_path: str | None = None,
        include_versions: bool = True,
    ) -> str:
        """
        Generate requirements.txt from imports.

        Args:
            path: Directory to analyze
            output_path: Path to write requirements.txt
            include_versions: Include version specifiers

        Returns:
            Generated requirements.txt content
        """
        search_path = self.workspace if path is None else Path(path)

        # Get imports
        imports = self.analyze_imports(search_path)

        # Check which are installed
        installed = self.check_installed(imports)
        installed_packages = [pkg for pkg, is_installed in installed.items() if is_installed]

        # Get versions if requested
        requirements = []
        if include_versions:
            for package in installed_packages:
                version = self._get_installed_version(package)
                if version:
                    requirements.append(f"{package}=={version}")
                else:
                    requirements.append(package)
        else:
            requirements = installed_packages

        content = "\n".join(sorted(requirements))

        if output_path:
            with open(output_path, "w") as f:
                f.write(content)

        return content

    def _get_installed_version(self, package: str) -> str | None:
        """Get the installed version of a package."""
        try:
            # Try to get version from package
            import importlib.metadata
            try:
                return importlib.metadata.version(package)
            except importlib.metadata.PackageNotFoundError:
                pass

            # Try pip show
            result = subprocess.run(
                ["pip", "show", package],
                capture_output=True,
                text=True,
                timeout=10,
            )

            for line in result.stdout.split("\n"):
                if line.startswith("Version:"):
                    return line.split(":", 1)[1].strip()

        except Exception:
            pass

        return None

    def full_analysis(self, path: str | None = None) -> DependencyAnalysis:
        """
        Perform full dependency analysis.

        Args:
            path: Directory to analyze

        Returns:
            DependencyAnalysis with all findings
        """
        search_path = self.workspace if path is None else Path(path)

        imports = self.analyze_imports(search_path)
        installed = self.check_installed(imports)

        dependencies = []
        missing = []
        orphan_imports = []

        for imp in imports:
            if installed.get(imp, False):
                version = self._get_installed_version(imp)
                dependencies.append(Dependency(
                    name=imp,
                    version=version,
                    source="auto-detected",
                ))
            else:
                missing.append(imp)

        # Check for orphan imports (used but not defined locally)
        for py_file in search_path.rglob("*.py"):
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # Find local definitions
                local_defs = set(re.findall(r"^class\s+(\w+)", content, re.MULTILINE))
                local_defs.update(re.findall(r"^def\s+(\w+)", content, re.MULTILINE))

                # Check imports
                for imp in self._extract_imports(content):
                    if imp not in installed and imp not in local_defs:
                        orphan_imports.append(imp)

            except Exception:
                continue

        return DependencyAnalysis(
            dependencies=dependencies,
            missing=missing,
            outdated=[],  # Could add pip list --outdated parsing
            conflicts=[],
            orphan_imports=list(set(orphan_imports)),
        )

    def install_package(self, package: str, version: str | None = None) -> bool:
        """
        Install a package.

        Args:
            package: Package name
            version: Optional version specifier

        Returns:
            True if successful
        """
        pkg_spec = package if version is None else f"{package}=={version}"

        try:
            result = subprocess.run(
                ["python3", "-m", "pip", "install", pkg_spec],
                capture_output=True,
                text=True,
                timeout=120,
            )
            return result.returncode == 0
        except Exception:
            return False

    def check_updates(self) -> list[dict[str, str]]:
        """
        Check for available package updates.

        Returns:
            List of packages with available updates
        """
        updates = []

        try:
            result = subprocess.run(
                ["pip", "list", "--outdated", "--format=json"],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                try:
                    packages = json.loads(result.stdout)
                    for pkg in packages:
                        updates.append({
                            "name": pkg["name"],
                            "current_version": pkg["version"],
                            "latest_version": pkg["latest_version"],
                        })
                except json.JSONDecodeError:
                    pass

        except Exception:
            pass

        return updates


def get_dependency_handlers() -> dict[str, Any]:
    """Get dependency tool handlers."""
    return {
        "analyze_imports": lambda path: DependencyTools("").analyze_imports(path),
        "check_installed": lambda pkgs: DependencyTools("").check_installed(pkgs),
        "generate_requirements": lambda path, **kw: DependencyTools("").generate_requirements(path, **kw),
        "install_package": lambda pkg, **kw: DependencyTools("").install_package(pkg, **kw),
        "check_updates": lambda: DependencyTools("").check_updates(),
    }