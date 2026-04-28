"""Quality Tools - Code quality, linting, and security scanning."""

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class QualityResult:
    """Result of quality checks."""
    tool: str
    passed: bool
    issues: list[dict[str, Any]]
    score: float  # 0-100
    output: str

    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.issues if i.get("severity") == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.get("severity") == "warning")


class QualityTools:
    """Code quality checking tools."""

    def __init__(self, workspace_path: str):
        self.workspace = Path(workspace_path)
        self._linters = ["ruff", "pylint", "flake8"]

    def lint(
        self,
        path: str | None = None,
        linter: str = "ruff",
        fix: bool = False,
    ) -> QualityResult:
        """
        Run a linter on Python code.

        Args:
            path: File or directory to lint
            linter: Linter to use (ruff, pylint, flake8)
            fix: Attempt to auto-fix issues

        Returns:
            QualityResult with issues found
        """
        search_path = self.workspace if path is None else Path(path)
        issues = []

        if linter == "ruff":
            return self._lint_ruff(search_path, fix)
        elif linter == "pylint":
            return self._lint_pylint(search_path)
        elif linter == "flake8":
            return self._lint_flake8(search_path)
        else:
            return QualityResult(
                tool=linter,
                passed=False,
                issues=[],
                score=0,
                output=f"Unknown linter: {linter}",
            )

    def _lint_ruff(self, path: Path, fix: bool) -> QualityResult:
        """Run ruff linter."""
        cmd = ["ruff", "check", str(path)]
        if fix:
            cmd.append("--fix")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            output = result.stdout + result.stderr

            # Parse ruff output
            issues = []
            for line in output.split("\n"):
                if ":" in line and not line.startswith("Found"):
                    parts = line.split(":", 3)
                    if len(parts) >= 4:
                        issues.append({
                            "file": parts[0],
                            "line": parts[1],
                            "column": parts[2] if len(parts) > 2 else "0",
                            "message": parts[3] if len(parts) > 3 else "",
                            "severity": "error" if "error" in line.lower() else "warning",
                            "code": self._extract_ruff_code(line),
                        })

            score = self._calculate_score(len(issues), 0)

            return QualityResult(
                tool="ruff",
                passed=result.returncode == 0,
                issues=issues,
                score=score,
                output=output[:2000],
            )

        except FileNotFoundError:
            return QualityResult(
                tool="ruff",
                passed=False,
                issues=[],
                score=0,
                output="ruff not installed. Run: pip install ruff",
            )
        except Exception as e:
            return QualityResult(
                tool="ruff",
                passed=False,
                issues=[],
                score=0,
                output=f"Error running ruff: {str(e)}",
            )

    def _lint_pylint(self, path: Path) -> QualityResult:
        """Run pylint linter."""
        cmd = ["pylint", str(path), "--output-format=text"]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

            output = result.stdout + result.stderr

            # Parse pylint output
            issues = []
            error_count = warning_count = 0

            for line in output.split("\n"):
                if ": error:" in line:
                    error_count += 1
                    issues.append({
                        "message": line,
                        "severity": "error",
                    })
                elif ": warning:" in line:
                    warning_count += 1
                    issues.append({
                        "message": line,
                        "severity": "warning",
                    })

            score = self._calculate_score(error_count, warning_count)

            return QualityResult(
                tool="pylint",
                passed=error_count == 0,
                issues=issues,
                score=score,
                output=output[:2000],
            )

        except FileNotFoundError:
            return QualityResult(
                tool="pylint",
                passed=False,
                issues=[],
                score=0,
                output="pylint not installed. Run: pip install pylint",
            )
        except Exception as e:
            return QualityResult(
                tool="pylint",
                passed=False,
                issues=[],
                score=0,
                output=f"Error running pylint: {str(e)}",
            )

    def _lint_flake8(self, path: Path) -> QualityResult:
        """Run flake8 linter."""
        cmd = ["flake8", str(path)]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            output = result.stdout + result.stderr

            issues = []
            for line in output.split("\n"):
                if line.strip() and ":" in line:
                    issues.append({
                        "message": line,
                        "severity": "warning",
                    })

            score = self._calculate_score(len(issues), 0)

            return QualityResult(
                tool="flake8",
                passed=result.returncode == 0,
                issues=issues,
                score=score,
                output=output[:2000],
            )

        except FileNotFoundError:
            return QualityResult(
                tool="flake8",
                passed=False,
                issues=[],
                score=0,
                output="flake8 not installed. Run: pip install flake8",
            )
        except Exception as e:
            return QualityResult(
                tool="flake8",
                passed=False,
                issues=[],
                score=0,
                output=f"Error running flake8: {str(e)}",
            )

    def type_check(
        self,
        path: str | None = None,
        strict: bool = False,
    ) -> QualityResult:
        """
        Run mypy type checker.

        Args:
            path: File or directory to check
            strict: Use strict mode

        Returns:
            QualityResult with type errors
        """
        search_path = self.workspace if path is None else Path(path)
        cmd = ["mypy", str(search_path)]

        if strict:
            cmd.append("--strict")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

            output = result.stdout + result.stderr

            issues = []
            for line in output.split("\n"):
                if ":" in line and ("error:" in line or "warning:" in line):
                    issues.append({
                        "message": line,
                        "severity": "error" if "error:" in line else "warning",
                    })

            score = self._calculate_score(
                sum(1 for i in issues if i["severity"] == "error"),
                sum(1 for i in issues if i["severity"] == "warning"),
            )

            return QualityResult(
                tool="mypy",
                passed=result.returncode == 0,
                issues=issues,
                score=score,
                output=output[:2000],
            )

        except FileNotFoundError:
            return QualityResult(
                tool="mypy",
                passed=False,
                issues=[],
                score=0,
                output="mypy not installed. Run: pip install mypy",
            )
        except Exception as e:
            return QualityResult(
                tool="mypy",
                passed=False,
                issues=[],
                score=0,
                output=f"Error running mypy: {str(e)}",
            )

    def security_scan(self, path: str | None = None) -> QualityResult:
        """
        Scan for security vulnerabilities.

        Args:
            path: File or directory to scan

        Returns:
            QualityResult with security issues
        """
        search_path = self.workspace if path is None else Path(path)
        issues = []
        output_lines = []

        # 1. Check for hardcoded secrets
        secret_patterns = [
            (r"api[_-]?key\s*=\s*['\"][a-zA-Z0-9]{20,}['\"]", "Hardcoded API key"),
            (r"password\s*=\s*['\"][^'\"]{8,}['\"]", "Hardcoded password"),
            (r"secret\s*=\s*['\"][^'\"]{8,}['\"]", "Hardcoded secret"),
            (r"token\s*=\s*['\"][a-zA-Z0-9]{20,}['\"]", "Hardcoded token"),
            (r"github[_-]?token\s*=\s*['\"][a-zA-Z0-9]{20,}['\"]", "Hardcoded GitHub token"),
            (r"aws[_-]?access[_-]?key\s*=\s*['\"][A-Z0-9]{20,}['\"]", "Hardcoded AWS key"),
        ]

        for py_file in search_path.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue

            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()

                for line_num, line in enumerate(content.split("\n"), 1):
                    for pattern, issue_type in secret_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            issues.append({
                                "file": str(py_file.relative_to(search_path)),
                                "line": str(line_num),
                                "message": f"{issue_type} found",
                                "severity": "error",
                                "type": "security",
                            })
                            output_lines.append(
                                f"{py_file}:{line_num}: {issue_type}"
                            )

                # Check for SQL injection patterns
                if re.search(r'["\']\s*\+.*\s*\+\s*["\']', line) and "sql" in line.lower():
                    issues.append({
                        "file": str(py_file.relative_to(search_path)),
                        "line": str(line_num),
                        "message": "Potential SQL injection (string concatenation in query)",
                        "severity": "warning",
                        "type": "security",
                    })

                # Check for eval usage
                if re.search(r"\beval\s*\(", line):
                    issues.append({
                        "file": str(py_file.relative_to(search_path)),
                        "line": str(line_num),
                        "message": "Use of eval() is a security risk",
                        "severity": "error",
                        "type": "security",
                    })

                # Check for pickle usage
                if re.search(r"\bpickle\.(load|loads)\s*\(", line):
                    issues.append({
                        "file": str(py_file.relative_to(search_path)),
                        "line": str(line_num),
                        "message": "Unpickling untrusted data is a security risk",
                        "severity": "warning",
                        "type": "security",
                    })

            except Exception:
                continue

        # 2. Try bandit if available
        try:
            result = subprocess.run(
                ["bandit", "-r", str(search_path), "-f", "json"],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode in [0, 1]:  # 0=no issues, 1=issues found
                bandit_data = json.loads(result.stdout)
                for issue in bandit_data.get("results", []):
                    issues.append({
                        "file": issue["filename"],
                        "line": str(issue["line_number"]),
                        "message": issue["issue_text"],
                        "severity": "warning",
                        "type": "security",
                        "confidence": issue["issue_confidence"],
                    })
                    output_lines.append(
                        f"{issue['filename']}:{issue['line_number']}: {issue['issue_text']}"
                    )

        except FileNotFoundError:
            pass  # bandit not installed
        except json.JSONDecodeError:
            pass

        score = self._calculate_score(
            sum(1 for i in issues if i["severity"] == "error"),
            sum(1 for i in issues if i["severity"] == "warning"),
        )

        return QualityResult(
            tool="security",
            passed=len([i for i in issues if i["severity"] == "error"]) == 0,
            issues=issues,
            score=score,
            output="\n".join(output_lines[:50]),
        )

    def complexity(self, path: str | None = None) -> QualityResult:
        """
        Analyze code complexity.

        Args:
            path: File or directory to analyze

        Returns:
            QualityResult with complexity metrics
        """
        search_path = self.workspace if path is None else Path(path)
        issues = []

        for py_file in search_path.rglob("*.py"):
            if "__pycache__" in str(py_file) or "test_" in py_file.name:
                continue

            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # Count functions
                functions = re.findall(r"def\s+(\w+)\s*\(", content)
                classes = re.findall(r"class\s+(\w+)\s*[:(]", content)

                # Estimate cyclomatic complexity
                # Count decision points (if, for, while, and, or)
                decision_points = len(re.findall(
                    r"\b(if|elif|for|while|and|or|\?|case)\b",
                    content
                ))

                # Calculate per-function complexity
                func_count = len(functions)
                if func_count > 0:
                    avg_complexity = decision_points / func_count
                else:
                    avg_complexity = 0

                if avg_complexity > 10:
                    issues.append({
                        "file": str(py_file.relative_to(search_path)),
                        "message": f"High complexity: {avg_complexity:.1f} avg per function",
                        "severity": "warning",
                        "type": "complexity",
                        "metrics": {
                            "functions": func_count,
                            "classes": len(classes),
                            "decision_points": decision_points,
                            "avg_complexity": avg_complexity,
                        },
                    })

            except Exception:
                continue

        # Try radon if available
        try:
            result = subprocess.run(
                ["radon", "cc", str(search_path), "-a"],
                capture_output=True,
                text=True,
                timeout=60,
            )

            for line in result.stdout.split("\n"):
                if "F" in line or "E" in line:  # High complexity grades
                    issues.append({
                        "message": line,
                        "severity": "warning",
                        "type": "complexity",
                    })

        except FileNotFoundError:
            pass

        score = self._calculate_score(
            sum(1 for i in issues if i["severity"] == "error"),
            sum(1 for i in issues if i["severity"] == "warning"),
        )

        return QualityResult(
            tool="complexity",
            passed=score >= 80,
            issues=issues,
            score=score,
            output=f"Found {len(issues)} complexity issues",
        )

    def check_all(self, path: str | None = None) -> dict[str, QualityResult]:
        """
        Run all quality checks.

        Args:
            path: File or directory to check

        Returns:
            Dict of tool name to QualityResult
        """
        results = {}

        # Run each check
        checks = [
            ("lint", lambda: self.lint(path)),
            ("type_check", lambda: self.type_check(path)),
            ("security", lambda: self.security_scan(path)),
            ("complexity", lambda: self.complexity(path)),
        ]

        for name, check_func in checks:
            try:
                results[name] = check_func()
            except Exception as e:
                results[name] = QualityResult(
                    tool=name,
                    passed=False,
                    issues=[],
                    score=0,
                    output=f"Error: {str(e)}",
                )

        return results

    def _calculate_score(self, errors: int, warnings: int) -> float:
        """Calculate quality score from issues."""
        if errors == 0 and warnings == 0:
            return 100.0

        # Deduct 10 for each error, 2 for each warning
        score = 100.0 - (errors * 10) - (warnings * 2)

        return max(0.0, min(100.0, score))

    def _extract_ruff_code(self, line: str) -> str:
        """Extract error code from ruff output."""
        match = re.search(r"\[([A-Z]\d+)\]", line)
        return match.group(1) if match else ""


def get_quality_handlers() -> dict[str, Any]:
    """Get quality tool handlers for ToolExecutor."""
    tools = QualityTools("")
    return {
        "lint": lambda path, **kw: tools.lint(path, **kw),
        "type_check": lambda path, **kw: tools.type_check(path, **kw),
        "security_scan": lambda path: tools.security_scan(path),
        "complexity": lambda path: tools.complexity(path),
        "check_all": lambda path: tools.check_all(path),
    }
