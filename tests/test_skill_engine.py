"""Tests for agent/skills/skill_engine.py."""

import pytest
from pathlib import Path

from agent.skills.skill_engine import (
    SkillEngine,
    SkillMetadata,
    SkillParameter,
    SkillResult,
)


class TestSkillParameter:
    """Tests for SkillParameter class."""

    def test_required_param_validation(self):
        """Test required parameter validation."""
        param = SkillParameter("file_path", "Path to file", required=True)

        # Missing value should fail
        is_valid, error = param.validate(None)
        assert is_valid is False
        assert "missing" in error.lower()

    def test_optional_param_validation(self):
        """Test optional parameter validation."""
        param = SkillParameter("verbose", "Verbose mode", required=False)

        # Missing value should pass for optional
        is_valid, error = param.validate(None)
        assert is_valid is True

    def test_default_value(self):
        """Test parameter with default value."""
        param = SkillParameter(
            "framework",
            "Test framework",
            required=False,
            default="pytest"
        )

        # No value should use default
        assert param.default == "pytest"

    def test_pattern_validation(self):
        """Test regex pattern validation."""
        param = SkillParameter(
            "port",
            "Port number",
            pattern=r"^\d{1,5}$"
        )

        # Valid port
        is_valid, _ = param.validate("8080")
        assert is_valid is True

        # Invalid port
        is_valid, _ = param.validate("not_a_port")
        assert is_valid is False


class TestSkillEngine:
    """Tests for SkillEngine class."""

    @pytest.fixture
    def registry(self):
        """Create a skill registry."""
        from skills.registry import create_skill_registry
        return create_skill_registry()

    @pytest.fixture
    def engine(self, registry):
        """Create a SkillEngine."""
        return SkillEngine(registry)

    @pytest.fixture
    def context(self, tmp_path):
        """Create a skill context."""
        from skills.registry import SkillContext
        return SkillContext(
            workspace=tmp_path,
            model="test-model",
            provider="test-provider",
        )

    def test_parse_simple_args(self, engine):
        """Test parsing simple --param value args."""
        args = "--file_path main.py --verbose"
        params = engine.parse_args(args)

        assert params["file_path"] == "main.py"
        assert params["verbose"] is None  # Flag has no value

    def test_parse_positional_args(self, engine):
        """Test parsing positional arguments."""
        args = "main.py --verbose"
        params = engine.parse_args(args)

        assert params["_positional"] == "main.py"

    def test_parse_empty_args(self, engine):
        """Test parsing empty args."""
        params = engine.parse_args("")
        assert params == {}

        params = engine.parse_args(None)
        assert params == {}

    def test_parse_hyphenated_params(self, engine):
        """Test that hyphens are converted to underscores."""
        args = "--file-path models.py"
        params = engine.parse_args(args)

        assert "file_path" in params
        assert params["file_path"] == "models.py"

    def test_execute_nonexistent_skill(self, engine, context):
        """Test executing a non-existent skill."""
        result = engine.execute("nonexistent-skill", context, {})

        assert result.success is False
        assert "not found" in result.error.lower()

    def test_execute_with_params(self, engine, registry, context, tmp_path):
        """Test executing a skill with parameters."""
        # Create a test file
        (tmp_path / "test.py").write_text("print('hello')")

        result = engine.execute("code-review", context, "--file_path test.py")

        assert result.skill_name == "code-review"

    def test_chain_execute(self, engine, context, tmp_path):
        """Test chaining multiple skills."""
        (tmp_path / "test.py").write_text("print('hello')")

        results = engine.chain_execute(
            ["code-review", "simplify"],
            context,
            {"workspace": str(tmp_path)}
        )

        assert len(results) == 2
        assert all(r.skill_name in ["code-review", "simplify"] for r in results)

    def test_chain_stops_on_failure(self, engine, context):
        """Test that skill chain stops when a skill fails."""
        results = engine.chain_execute(
            ["nonexistent-skill", "code-review"],
            context,
        )

        # Should only have the first (failed) result
        assert len(results) == 1
        assert results[0].success is False

    def test_validate_prerequisites(self, engine):
        """Test prerequisite validation."""
        metadata = SkillMetadata(
            name="test-skill",
            description="Test",
            prerequisites=["prereq-skill"]
        )

        # Without prerequisites met
        is_valid, error = engine.validate_prerequisites("test-skill", metadata)
        assert is_valid is False
        assert "prerequisite" in error.lower()

        # With prerequisites met (simulate)
        engine._execution_history.append(
            SkillResult(skill_name="prereq-skill", success=True, output="")
        )

        is_valid, error = engine.validate_prerequisites("test-skill", metadata)
        assert is_valid is True

    def test_render_template(self, engine, context):
        """Test template rendering."""
        template = "Workspace: {workspace}, Model: {model}"
        rendered = engine.render_template(template, context)

        assert str(context.workspace) in rendered
        assert context.model in rendered

    def test_render_template_with_params(self, engine, context):
        """Test template rendering with custom params."""
        template = "Testing {file_path} on {model}"
        rendered = engine.render_template(
            template,
            context,
            {"file_path": "main.py"}
        )

        assert "main.py" in rendered

    def test_execution_summary(self, engine, context, tmp_path):
        """Test execution summary generation."""
        (tmp_path / "test.py").write_text("print('hello')")

        # Execute some skills
        engine.execute("code-review", context)
        engine.execute("simplify", context)

        summary = engine.get_execution_summary()
        assert "2" in summary
        assert "code-review" in summary
        assert "simplify" in summary

    def test_execution_history_tracking(self, engine, context, tmp_path):
        """Test that execution history is tracked."""
        (tmp_path / "test.py").write_text("print('hello')")

        engine.execute("code-review", context)
        assert len(engine._execution_history) == 1

        engine.execute("simplify", context)
        assert len(engine._execution_history) == 2

    def test_get_metadata(self, engine):
        """Test getting skill metadata."""
        metadata = engine.get_metadata("code-review")

        assert metadata is not None
        assert metadata.name == "code-review"
        assert metadata.description is not None

    def test_get_metadata_nonexistent(self, engine):
        """Test getting metadata for non-existent skill."""
        metadata = engine.get_metadata("nonexistent-skill")
        assert metadata is None

    def test_build_args_string(self, engine):
        """Test building args string from params."""
        params = {
            "_positional": "main.py",
            "verbose": None,
            "file_path": "test.py"
        }

        args = engine._build_args_string(params)
        assert "main.py" in args
        assert "--file-path" in args or "--file_path" in args


class TestSkillMetadata:
    """Tests for SkillMetadata class."""

    def test_create_metadata(self):
        """Test creating skill metadata."""
        metadata = SkillMetadata(
            name="test-skill",
            description="A test skill",
            category="testing",
            model_hint="gemma4:26b"
        )

        assert metadata.name == "test-skill"
        assert metadata.category == "testing"
        assert metadata.model_hint == "gemma4:26b"
        assert metadata.prerequisites == []

    def test_metadata_with_parameters(self):
        """Test metadata with parameter definitions."""
        params = [
            SkillParameter("file_path", "File to process", required=True),
            SkillParameter("verbose", "Verbose output", required=False),
        ]

        metadata = SkillMetadata(
            name="processor",
            description="Process files",
            parameters=params
        )

        assert len(metadata.parameters) == 2
        assert metadata.parameters[0].name == "file_path"
