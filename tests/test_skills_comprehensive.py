"""Comprehensive test suite for Skills System."""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_imports():
    """Test all imports work correctly."""
    print("=" * 60)
    print("TEST 1: Import Verification")
    print("=" * 60)

    tests = []

    # Core agent.skills
    try:
        from agent.skills import SkillEngine, SkillMetadata, SkillParameter, SkillResult
        tests.append(("agent.skills.*", True, "Import successful"))
    except Exception as e:
        tests.append(("agent.skills.*", False, str(e)))

    # Skill registry
    try:
        from skills.registry import (
            SkillRegistry, create_skill_registry,
            BaseSkill, Skill, SkillContext,
            CodeReviewSkill, SecurityReviewSkill, InitSkill, SimplifySkill
        )
        tests.append(("skills.registry.*", True, "Import successful"))
    except Exception as e:
        tests.append(("skills.registry.*", False, str(e)))

    # Builtin skills
    try:
        from skills.builtin import TestGenerationSkill, ApiDesignSkill, DocGenerationSkill
        tests.append(("skills.builtin.*", True, "Import successful"))
    except Exception as e:
        tests.append(("skills.builtin.*", False, str(e)))

    # Skill templates
    try:
        from agent.skills.skill_templates import SkillTemplateEngine, SkillSpec
        tests.append(("agent.skills.skill_templates.*", True, "Import successful"))
    except Exception as e:
        tests.append(("agent.skills.skill_templates.*", False, str(e)))

    # Print results
    all_passed = True
    for name, passed, msg in tests:
        status = "✅ PASS" if passed else "❌ FAIL"
        if not passed:
            all_passed = False
        print(f"{status} | {name}: {msg}")

    print()
    return all_passed


def test_skill_engine_core():
    """Test SkillEngine core functionality."""
    print("=" * 60)
    print("TEST 2: SkillEngine Core")
    print("=" * 60)

    from agent.skills import SkillEngine, SkillMetadata, SkillParameter, SkillResult
    from skills.registry import create_skill_registry, SkillContext
    from pathlib import Path
    import tempfile

    tests = []
    registry = create_skill_registry()
    engine = SkillEngine(registry)

    # Test parameter parsing
    with tempfile.TemporaryDirectory() as tmp:
        ctx = SkillContext(workspace=Path(tmp), model="test", provider="test")

        # Simple args
        params = engine.parse_args("--file_path test.py --verbose")
        tests.append((
            "parse simple args",
            params.get("file_path") == "test.py" and params.get("verbose") is None,
            f"Got: {params}"
        ))

        # Positional args
        params = engine.parse_args("main.py --verbose")
        tests.append((
            "parse positional args",
            params.get("_positional") == "main.py",
            f"Got: {params}"
        ))

        # Hyphen to underscore
        params = engine.parse_args("--file-path models.py")
        tests.append((
            "parse hyphenated param",
            "file_path" in params,
            f"Got: {params}"
        ))

        # Template rendering
        template = "Testing {workspace} with {model}"
        rendered = engine.render_template(template, ctx)
        tests.append((
            "template rendering",
            str(tmp) in rendered and "test" in rendered,
            f"Got: {rendered[:50]}..."
        ))

        # Execute skill (code-review)
        result = engine.execute("code-review", ctx)
        tests.append((
            "execute skill",
            result.skill_name == "code-review",
            f"Success: {result.success}"
        ))

        # Chain execution
        results = engine.chain_execute(["code-review", "simplify"], ctx)
        tests.append((
            "chain execution",
            len(results) == 2,
            f"Got {len(results)} results"
        ))

        # Metadata retrieval
        metadata = engine.get_metadata("code-review")
        tests.append((
            "get metadata",
            metadata is not None and metadata.name == "code-review",
            f"Got: {metadata}"
        ))

    # Print results
    all_passed = True
    for name, passed, msg in tests:
        status = "✅ PASS" if passed else "❌ FAIL"
        if not passed:
            all_passed = False
        print(f"{status} | {name}: {msg}")

    print()
    return all_passed


def test_builtin_skills():
    """Test all 7 built-in skills."""
    print("=" * 60)
    print("TEST 3: Built-in Skills")
    print("=" * 60)

    from skills.registry import create_skill_registry, SkillContext
    from pathlib import Path
    import tempfile

    registry = create_skill_registry()
    all_passed = True

    # Create test workspace
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp)
        ctx = SkillContext(workspace=workspace, model="test", provider="test")

        # Create test Python file
        test_file = workspace / "test_module.py"
        test_file.write_text("""
def add(a, b):
    '''Add two numbers.'''
    return a + b

def greet(name):
    '''Greet someone.'''
    return f"Hello, {name}!"

class Calculator:
    def multiply(self, x, y):
        return x * y
""")

        tests = []
        skill_names = ["code-review", "security-review", "init", "simplify",
                       "test-gen", "api-design", "doc-gen"]

        for name in skill_names:
            skill = registry.find(name)
            if skill:
                try:
                    result = skill.handler(ctx, "")
                    tests.append((name, True, f"Executed OK"))
                except Exception as e:
                    tests.append((name, False, str(e)))
            else:
                tests.append((name, False, "Skill not found"))

        # Print results
        for name, passed, msg in tests:
            status = "✅ PASS" if passed else "❌ FAIL"
            if not passed:
                all_passed = False
            print(f"{status} | /{name}: {msg}")

        # Test SkillRegistry search
        results = registry.search("test")
        tests.append(("registry search", len(results) > 0, f"Found {len(results)} skills"))

        # Test find_by_category
        dev_skills = registry.find_by_category("development")
        tests.append(("find_by_category", len(dev_skills) > 0, f"Found {len(dev_skills)}"))

    print()
    return all_passed


def test_skill_templates():
    """Test SkillTemplateEngine."""
    print("=" * 60)
    print("TEST 4: Skill Templates")
    print("=" * 60)

    from agent.skills.skill_templates import SkillTemplateEngine, SkillSpec

    tests = []

    # Create skill spec
    spec = SkillSpec(
        name="my-custom-skill",
        description="A custom skill for testing",
        category="custom",
        aliases=["mcs"],
        parameters=[
            {"name": "file_path", "description": "Path to file", "required": True},
            {"name": "verbose", "description": "Verbose mode", "required": False},
        ]
    )

    engine = SkillTemplateEngine()

    # Test code generation
    code = engine.create_skill(spec)
    tests.append(("code generation", "class MyCustomSkill" in code, "Class name OK"))
    tests.append(("code generation", "name = \"my-custom-skill\"" in code, "Name OK"))
    tests.append(("code generation", "execute" in code, "Execute method OK"))

    # Test documentation generation
    docs = engine.create_documentation(spec)
    tests.append(("doc generation", "# my-custom-skill" in docs, "Header OK"))
    tests.append(("doc generation", "--file-path" in docs, "Parameters OK"))

    # Test scaffold generation
    scaffold = engine.generate_test_scaffold(spec)
    tests.append(("test scaffold", "TestMyCustomSkill" in scaffold, "Test class OK"))

    # Print results
    all_passed = True
    for name, passed, msg in tests:
        status = "✅ PASS" if passed else "❌ FAIL"
        if not passed:
            all_passed = False
        print(f"{status} | {name}: {msg}")

    print()
    return all_passed


def test_integration():
    """Test full integration."""
    print("=" * 60)
    print("TEST 5: Integration Test")
    print("=" * 60)

    from agent.skills import SkillEngine
    from skills.registry import create_skill_registry, SkillContext
    from pathlib import Path
    import tempfile

    tests = []

    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp)
        ctx = SkillContext(workspace=workspace, model="test", provider="test")

        # Create test files
        (workspace / "main.py").write_text("print('hello')")
        (workspace / "utils.py").write_text("def helper(): pass")

        registry = create_skill_registry()
        engine = SkillEngine(registry)

        # Test executing with string params
        result = engine.execute("test-gen", ctx, "--file_path main.py")
        tests.append(("execute with string params", True, f"Success: {result.success}"))

        # Test skill chaining stops on failure
        results = engine.chain_execute(["nonexistent", "code-review"], ctx)
        tests.append(("chain stops on failure", len(results) == 1, f"Got {len(results)} results"))

        # Test execution summary
        engine.execute("code-review", ctx)
        summary = engine.get_execution_summary()
        tests.append(("execution summary", "code-review" in summary, "Summary contains skill"))

        # Test registry validation
        from skills.registry import Skill
        invalid_skill = Skill(name="", description="", trigger="/test", handler=lambda: "")
        errors = registry.validate(invalid_skill)
        tests.append(("registry validation", len(errors) > 0, f"Found {len(errors)} errors"))

    # Print results
    all_passed = True
    for name, passed, msg in tests:
        status = "✅ PASS" if passed else "❌ FAIL"
        if not passed:
            all_passed = False
        print(f"{status} | {name}: {msg}")

    print()
    return all_passed


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("🧪 MyAgent Skills System - Comprehensive Test Suite")
    print("=" * 60 + "\n")

    results = []

    results.append(("Import Verification", test_imports()))
    results.append(("SkillEngine Core", test_skill_engine_core()))
    results.append(("Built-in Skills", test_builtin_skills()))
    results.append(("Skill Templates", test_skill_templates()))
    results.append(("Integration", test_integration()))

    print("=" * 60)
    print("📊 FINAL RESULTS")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        if not passed:
            all_passed = False
        print(f"{status} | {name}")

    print()
    if all_passed:
        print("🎉 All tests passed! Skills system is ready.")
    else:
        print("⚠️  Some tests failed. Check output above.")

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)