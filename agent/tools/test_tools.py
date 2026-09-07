"""Test Tools - Pytest integration for automated testing."""

import json
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class TestResult:
    """Result of running tests."""

    passed: int
    failed: int
    skipped: int
    errors: int
    total_time: float
    output: str
    coverage: dict[str, float] | None = None
    exit_code: int = 0

    @property
    def is_success(self) -> bool:
        return self.exit_code == 0 and self.failed == 0 and self.errors == 0

    @property
    def total_tests(self) -> int:
        return self.passed + self.failed + self.skipped


class TestTools:
    """Automated testing tools using pytest."""

    def __init__(self, workspace_path: str):
        self.workspace = Path(workspace_path)

    def discover_tests(self, path: str | None = None) -> list[str]:
        """
        Auto-discover test files in the project.

        Args:
            path: Directory to search (defaults to workspace)

        Returns:
            List of test file paths
        """
        search_path = self.workspace if path is None else Path(path)
        test_files = []

        # Standard test patterns
        patterns = ["**/test_*.py", "**/*_test.py", "**/tests/*.py"]

        for pattern in patterns:
            test_files.extend(search_path.glob(pattern))

        # Filter out __init__.py and non-test files
        test_files = [
            f
            for f in test_files
            if f.is_file()
            and f.name != "__init__.py"
            and ("test_" in f.name or f.name.endswith("_test.py"))
        ]

        return sorted({str(f.relative_to(search_path)) for f in test_files})

    def run_tests(
        self,
        path: str | None = None,
        pattern: str = "test_*.py",
        verbose: bool = True,
        coverage: bool = False,
        fail_fast: bool = True,
        parallel: bool = False,
    ) -> TestResult:
        """
        Run pytest tests and return results.

        Args:
            path: Directory or file to test
            pattern: Test file pattern
            verbose: Verbose output
            coverage: Generate coverage report
            fail_fast: Stop on first failure
            parallel: Run tests in parallel

        Returns:
            TestResult with pass/fail counts
        """
        workspace = self.workspace.resolve()
        target = workspace if path is None else (workspace / path).resolve()
        cmd = [sys.executable, "-m", "pytest", str(target), "--tb=short", "-q"]
        cmd.extend(["-o", f"python_files={pattern}"])
        if verbose:
            cmd.append("-v")
        if fail_fast:
            cmd.append("-x")
        if parallel:
            cmd.extend(["-n", "auto"])
            self._ensure_package("pytest-xdist")

        try:
            with tempfile.TemporaryDirectory(prefix="myagent-pytest-") as report_dir:
                junit_path = Path(report_dir) / "results.xml"
                coverage_path = Path(report_dir) / "coverage.json"
                cmd.append(f"--junitxml={junit_path}")
                if coverage:
                    self._ensure_package("pytest-cov")
                    cmd.extend(
                        [f"--cov={workspace}", f"--cov-report=json:{coverage_path}"]
                    )
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    cwd=workspace,
                    timeout=120,
                )
                output = result.stdout + result.stderr
                passed = failed = skipped = errors = 0
                total_time = 0.0
                if junit_path.exists():
                    root = ET.parse(junit_path).getroot()
                    for suite in root.iter("testsuite"):
                        failed += int(suite.get("failures", 0))
                        errors += int(suite.get("errors", 0))
                        skipped += int(suite.get("skipped", 0))
                        passed += max(
                            0,
                            int(suite.get("tests", 0))
                            - int(suite.get("failures", 0))
                            - int(suite.get("errors", 0))
                            - int(suite.get("skipped", 0)),
                        )
                        total_time += float(suite.get("time", 0))
                elif result.returncode == 0:
                    # Missing structured evidence is not a successful test run.
                    errors = 1
                if result.returncode and not failed and not errors:
                    errors = 1
                coverage_result = None
                if coverage and coverage_path.exists():
                    data = json.loads(coverage_path.read_text())
                    coverage_result = {
                        "total": data.get("totals", {}).get("percent_covered", 0) / 100
                    }
                return TestResult(
                    passed=passed,
                    failed=failed,
                    skipped=skipped,
                    errors=errors,
                    total_time=total_time,
                    output=output[:2000],
                    coverage=coverage_result,
                    exit_code=result.returncode,
                )
        except subprocess.TimeoutExpired:
            return TestResult(
                0,
                0,
                0,
                1,
                120.0,
                "Test execution timed out after 120 seconds",
                exit_code=124,
            )
        except Exception as exc:
            return TestResult(
                0, 0, 0, 1, 0.0, f"Error running tests: {exc}", exit_code=1
            )

    def generate_fixture(
        self,
        model_class: str,
        fields: dict[str, str],
        output_path: str | None = None,
    ) -> str:
        """
        Generate pytest fixtures for a data model.

        Args:
            model_class: Name of the model class
            fields: Dict of field names to types (e.g., {"name": "str", "age": "int"})
            output_path: Optional path to write fixture file

        Returns:
            Generated fixture code
        """
        fixture_code = f'''"""Pytest fixtures for {model_class}."""

import pytest
from your_module import {model_class}


@pytest.fixture
def sample_{model_class.lower()}() -> {model_class}:
    """Create a sample {model_class} instance."""
    return {model_class}(
'''

        for field_name, field_type in fields.items():
            # Generate sample values based on type
            if field_type == "str":
                sample_value = f'"{field_name}_sample"'
            elif field_type == "int":
                sample_value = "42"
            elif field_type == "float":
                sample_value = "3.14"
            elif field_type == "bool":
                sample_value = "True"
            elif field_type == "list":
                sample_value = "[]"
            elif field_type == "dict":
                sample_value = "{}"
            else:
                sample_value = "None"

            fixture_code += f"        {field_name}={sample_value},\n"

        fixture_code += "    )\n\n"

        # Build remaining fixtures without f-strings to avoid issues
        model_lower = model_class.lower()

        # List fixture
        fixture_code += "@pytest.fixture\n"
        fixture_code += "def " + model_lower + "_list() -> list[" + model_class + "]:\n"
        fixture_code += '    """Create a list of ' + model_class + ' instances."""\n'
        fixture_code += "    return [\n"
        fixture_code += "        " + model_class + "(\n"

        for field_name, field_type in fields.items():
            if field_type == "str":
                sample_value = '"' + field_name + '_1"'
            else:
                sample_value = "1"
            fixture_code += "            " + field_name + "=" + sample_value + ",\n"

        fixture_code += "        ),\n"
        fixture_code += "        # Add more samples as needed\n"
        fixture_code += "    ]\n"
        fixture_code += "\n\n"

        # Relations fixture
        fixture_code += "@pytest.fixture\n"
        fixture_code += (
            "def " + model_lower + "_with_relations() -> " + model_class + ":\n"
        )
        fixture_code += '    """Create a ' + model_class + ' with related objects."""\n'
        fixture_code += "    # Customize based on your model's relationships\n"
        fixture_code += "    return " + model_class + "(\n"
        fixture_code += "        # Add related objects here\n"
        fixture_code += "    )\n"

        if output_path:
            with open(output_path, "w") as f:
                f.write(fixture_code)

        return fixture_code

    def create_test_file(
        self,
        module_name: str,
        test_cases: list[dict[str, Any]],
        output_path: str | None = None,
    ) -> str:
        """
        Create a test file with test cases.

        Args:
            module_name: Module to test
            test_cases: List of test case dicts with 'name', 'function', 'params'
            output_path: Optional path to write test file

        Returns:
            Generated test code
        """
        test_code = f'''"""Tests for {module_name}."""

import pytest


class Test{model_class_to_classname(module_name)}:
    """Test suite for {module_name}."""

'''

        for i, case in enumerate(test_cases):
            test_name = case.get("name", f"test_case_{i + 1}")
            test_func = case.get("function", "")
            params = case.get("params", {})
            expected = case.get("expected", None)

            # Generate test method
            test_code += f"    def {test_name}(self):\n"
            test_code += f'        """Test: {case.get("description", test_name)}"""\n'

            if params:
                test_code += "        # Setup\n"
                for param_name, param_value in params.items():
                    if isinstance(param_value, str):
                        test_code += f'        {param_name} = "{param_value}"\n'
                    else:
                        test_code += f"        {param_name} = {param_value}\n"

            if test_func:
                test_code += f"\n        # Action\n"
                test_code += f"        result = {test_func}\n"

            if expected:
                test_code += "\n        # Assert\n"
                if isinstance(expected, str):
                    test_code += f'        assert result == "{expected}"\n'
                else:
                    test_code += f"        assert result == {expected}\n"

            test_code += "\n"

        if output_path:
            with open(output_path, "w") as f:
                f.write(test_code)

        return test_code

    def _ensure_package(self, package: str) -> bool:
        """Ensure a package is installed, install if not."""
        try:
            __import__(package.replace("-", "_"))
            return True
        except ImportError:
            try:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", package],
                    capture_output=True,
                    check=True,
                    timeout=120,
                )
                return True
            except Exception:
                return False


def model_class_to_classname(module_name: str) -> str:
    """Convert module name to ClassName format."""
    parts = module_name.replace("_", "-").split("-")
    return "".join(p.capitalize() for p in parts)


def get_test_handlers() -> dict[str, Any]:
    """Get test tool handlers for ToolExecutor."""
    return {
        "discover_tests": lambda path: TestTools("").discover_tests(path),
        "run_tests": lambda path, **kwargs: TestTools("").run_tests(path, **kwargs),
        "generate_fixture": lambda model, fields, **kw: TestTools("").generate_fixture(
            model, fields, **kw
        ),
        "create_test_file": lambda module, cases, **kw: TestTools("").create_test_file(
            module, cases, **kw
        ),
    }
