"""Test Generation Skill - Auto-generate unit tests for Python code."""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

from agent.skills.skill_engine import SkillEngine
from skills.registry import BaseSkill, SkillContext


class TestGenerationSkill(BaseSkill):
    """Automatically generate unit tests for Python functions."""

    name = "test-gen"
    description = "Generate unit tests for Python functions using pytest"
    aliases = ["generate-tests", "gen-test", "mk-tests"]
    category = "development"

    # Known test patterns to look for
    TEST_FRAMEWORKS = {
        "pytest": {
            "import": "import pytest",
            "fixture": "@pytest.fixture",
            "parametrize": "@pytest.mark.parametrize",
            "skip": "@pytest.mark.skip",
        },
        "unittest": {
            "import": "import unittest",
            "fixture": None,  # unittest doesn't use fixtures
            "parametrize": None,
            "skip": "@unittest.skip",
        },
    }

    def execute(self, context: SkillContext, args: str) -> str:
        """Generate tests for Python files."""
        # Parse arguments
        params = self._parse_args(args)
        file_path = params.get("file_path")
        framework = params.get("framework", "pytest")
        output_path = params.get("output")

        if not file_path:
            return self._error("No file path specified. Use --file_path <path>")

        # Resolve file path
        target = context.workspace / file_path if not Path(file_path).is_absolute() else Path(file_path)

        if not target.exists():
            return self._error(f"File not found: {file_path}")

        try:
            # Analyze the source file
            source_code = target.read_text()
            functions = self._extract_functions(source_code)

            if not functions:
                return "No functions found to test."

            # Generate test code
            test_code = self._generate_tests(functions, framework, target.stem)

            # Write tests or return them
            if output_path:
                output_file = context.workspace / output_path if not Path(output_path).is_absolute() else Path(output_path)
                output_file.parent.mkdir(parents=True, exist_ok=True)
                output_file.write_text(test_code)
                return f"✅ Tests written to {output_path}\n\n{test_code}"
            else:
                return f"📝 Generated Tests:\n\n{test_code}"

        except Exception as e:
            return self._error(f"Failed to generate tests: {str(e)}")

    def _parse_args(self, args: str) -> dict[str, str | None]:
        """Parse command-line style arguments."""
        engine = SkillEngine.__new__(SkillEngine)
        engine.PARAM_PATTERN = re.compile(r"--(\w+)(?:\s+(.+?))?(?=\s+--|$)")
        return engine.parse_args(args) if hasattr(engine, 'parse_args') else self._simple_parse(args)

    def _simple_parse(self, args: str) -> dict[str, str | None]:
        """Simple argument parsing fallback."""
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
            elif "=" in part:
                key, val = part.split("=", 1)
                params[key.replace("-", "_")] = val

        return params

    def _extract_functions(self, source_code: str) -> list[dict[str, Any]]:
        """Extract function definitions from Python source."""
        functions = []

        try:
            tree = ast.parse(source_code)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Skip private functions and dunder methods (except __init__)
                    if node.name.startswith("_") and not node.name == "__init__":
                        continue

                    # Get function parameters
                    args = node.args
                    params = [arg.arg for arg in args.args if arg.arg not in ("self", "cls")]
                    defaults = [d for d in args.defaults] if args.defaults else []

                    # Get return type hint from annotation
                    returns = None
                    if node.returns:
                        if isinstance(node.returns, ast.Name):
                            returns = node.returns.id

                    functions.append({
                        "name": node.name,
                        "params": params,
                        "returns": returns,
                        "decorators": [d for d in node.decorator_list if isinstance(d, ast.Name)],
                        "line": node.lineno,
                    })

        except SyntaxError:
            pass

        return functions

    def _generate_tests(self, functions: list[dict], framework: str, module_name: str) -> str:
        """Generate test code for extracted functions."""
        if framework == "pytest":
            return self._generate_pytest_tests(functions, module_name)
        else:
            return self._generate_unittest_tests(functions, module_name)

    def _generate_pytest_tests(self, functions: list[dict], module_name: str) -> str:
        """Generate pytest-style tests."""
        lines = [
            '"""Auto-generated tests for ' + module_name + '."""',
            "",
            "import pytest",
            f"from {module_name} import *",
            "",
        ]

        for func in functions:
            func_name = func["name"]
            params = func["params"]
            returns = func["returns"]

            # Test function
            test_name = f"test_{func_name}"
            lines.append(f"def {test_name}():")
            lines.append(f'    """Test {func_name} function."""')

            if params:
                # Create dummy args for testing
                arg_str = ", ".join(f'"{p}"' if p != "int" else "1" for p in params[:3])
                lines.append(f"    result = {func_name}({arg_str})")
            else:
                lines.append(f"    result = {func_name}()")

            if returns:
                lines.append(f"    assert result is not None  # TODO: check return type {returns}")
            else:
                lines.append("    # TODO: Add assertions based on expected behavior")

            lines.append("")

        return "\n".join(lines)

    def _generate_unittest_tests(self, functions: list[dict], module_name: str) -> str:
        """Generate unittest-style tests."""
        lines = [
            '"""Auto-generated tests for ' + module_name + '."""',
            "",
            "import unittest",
            f"from {module_name} import *",
            "",
            f"class Test{module_name.capitalize()}(unittest.TestCase):",
            "",
        ]

        for func in functions:
            func_name = func["name"]
            params = func["params"]

            lines.append(f"    def test_{func_name}(self):")
            lines.append(f'        """Test {func_name} method."""')

            if params:
                arg_str = ", ".join(f'"{p}"' if p != "int" else "1" for p in params[:3])
                lines.append(f"        result = {func_name}({arg_str})")
            else:
                lines.append(f"        result = {func_name}()")

            lines.append("        self.assertIsNotNone(result)")
            lines.append("")

        lines.append("if __name__ == '__main__':")
        lines.append("    unittest.main()")

        return "\n".join(lines)

    def _error(self, message: str) -> str:
        """Format error message."""
        return f"❌ Test Generation Error: {message}"