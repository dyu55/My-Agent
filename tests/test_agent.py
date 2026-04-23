import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from main import (
    Action,
    ConversationMemory,
    ProviderSettings,
    TraceLogger,
    WorkspaceTools,
    build_provider_registry,
    chat_with_provider,
    get_active_provider,
    parse_action_response,
    parse_cli_args,
    WORKSPACE,
)


class StructuredOutputTests(unittest.TestCase):
    def test_parse_action_response_returns_validated_action(self):
        action = parse_action_response(
            json.dumps(
                {
                    "command": "write",
                    "path": "app.py",
                    "content": "print('hello')",
                }
            )
        )

        self.assertIsInstance(action, Action)
        self.assertEqual(action.command, "write")
        self.assertEqual(action.path, "app.py")


class ContextManagementTests(unittest.TestCase):
    def test_memory_summarizes_old_steps_and_keeps_recent_turns(self):
        memory = ConversationMemory(max_recent_pairs=2)
        memory.record_turn("assistant", "first thought")
        memory.record_turn("user", "first observation")
        memory.record_turn("assistant", "second thought")
        memory.record_turn("user", "second observation")
        memory.record_turn("assistant", "third thought")
        memory.record_turn("user", "third observation")

        messages = memory.build_messages(
            system_prompt="system prompt",
            task="do something useful",
        )

        self.assertEqual(messages[0]["role"], "system")
        summary_messages = [
            m
            for m in messages
            if m["role"] == "system" and "Summary of earlier progress" in m["content"]
        ]
        self.assertEqual(len(summary_messages), 1)
        self.assertIn("first observation", summary_messages[0]["content"])
        self.assertTrue(any(m["content"] == "third observation" for m in messages))


class ObservabilityTests(unittest.TestCase):
    def test_trace_logger_writes_jsonl_events(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = TraceLogger(Path(temp_dir) / "logs")
            logger.log("tool_result", {"command": "read", "status": "ok"})

            trace_file = logger.trace_file
            self.assertTrue(trace_file.exists())
            record = json.loads(trace_file.read_text(encoding="utf-8").strip())
            self.assertEqual(record["event"], "tool_result")
            self.assertEqual(record["payload"]["command"], "read")


class EnvironmentFeedbackTests(unittest.TestCase):
    def test_workspace_tools_can_list_search_and_check_dependencies(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            tools = WorkspaceTools(workspace)
            tools.write("notes.txt", "hello harness engineering")

            listed = tools.list_files(".")
            self.assertIn("notes.txt", listed)

            searched = tools.search("harness")
            self.assertIn("notes.txt:1: hello harness engineering", searched)

            dependencies = json.loads(
                tools.check_dependencies(["json", "definitely_missing_module_123"])
            )
            self.assertIn("json", dependencies["available"])
            self.assertIn("definitely_missing_module_123", dependencies["missing"])

    def test_search_web_returns_results(self):
        # 使用 mock 测试 search_web
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            tools = WorkspaceTools(workspace)

            # Mock requests.get 来模拟 PyPI API 响应
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "info": {
                    "name": "fastapi",
                    "version": "0.136.0",
                    "summary": "FastAPI framework for building APIs",
                    "home_page": "https://fastapi.tiangolo.com",
                }
            }

            with patch("main.requests.get", return_value=mock_response) as mock_get:
                result = tools.search_web("FastAPI tutorial")

                mock_get.assert_called()
                # PyPI API 返回包信息
                self.assertIn("Latest version:", result)
                self.assertIn("FASTAPI", result)

    def test_search_web_handles_api_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            tools = WorkspaceTools(workspace)

            with patch("main.requests.get", side_effect=Exception("Network error")):
                result = tools.search_web("test query")
                self.assertIn("Error during web search:", result)

    def test_edit_file_success(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            tools = WorkspaceTools(workspace)

            # 创建测试文件
            tools.write("test.txt", "Hello World\nPython is great\nEnd of file")

            # 编辑文件
            result = tools.edit("test.txt", "Hello World", "Hello Universe")
            self.assertIn("Success:", result)

            # 验证修改
            content = (workspace / "test.txt").read_text()
            self.assertIn("Hello Universe", content)
            self.assertNotIn("Hello World", content)

    def test_edit_file_not_found(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            tools = WorkspaceTools(workspace)

            result = tools.edit("nonexistent.txt", "old", "new")
            self.assertIn("Error:", result)
            self.assertIn("not found", result)

    def test_web_fetch_success(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            tools = WorkspaceTools(workspace)

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "<html><body>Test content</body></html>"

            with patch("main.requests.get", return_value=mock_response):
                result = tools.web_fetch("https://example.com")
                self.assertIn("=== Page Content", result)
                self.assertIn("Test content", result)

    def test_run_tests_success(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            tools = WorkspaceTools(workspace)

            # Mock subprocess.run 来模拟测试成功
            mock_result = MagicMock()
            mock_result.stdout = "test_example PASSED\n\n1 passed in 0.1s"
            mock_result.stderr = ""
            mock_result.returncode = 0

            with patch("subprocess.run", return_value=mock_result) as mock_run:
                result = tools.run_tests()
                self.assertIn("passed", result.lower())


class ProviderTests(unittest.TestCase):
    def test_parse_cli_args_accepts_provider_override(self):
        args = parse_cli_args(["--provider", "rsxermu"])

        self.assertEqual(args.provider, "rsxermu")

    def test_get_active_provider_prefers_cli_override(self):
        provider = get_active_provider(
            {
                "ACTIVE_PROVIDER": "ollama",
                "MODEL_NAME": "gemma4:latest",
                "OLLAMA_HOST": "http://192.168.0.124:11434",
                "RSXERMU_BASE_URL": "https://rsxermu666.cn",
                "RSXERMU_API_KEY": "secret-key",
                "RSXERMU_MODEL": "gpt-4.1-mini",
            },
            provider_name="rsxermu",
        )

        self.assertEqual(provider.name, "rsxermu")
        self.assertEqual(provider.model, "gpt-4.1-mini")

    def test_build_provider_registry_includes_rsxermu(self):
        registry = build_provider_registry(
            {
                "MODEL_NAME": "gemma4:latest",
                "OLLAMA_HOST": "http://192.168.0.124:11434",
                "RSXERMU_BASE_URL": "https://rsxermu666.cn",
                "RSXERMU_API_KEY": "secret-key",
                "RSXERMU_MODEL": "gpt-4.1-mini",
            }
        )

        self.assertEqual(registry["rsxermu"].client_type, "openai")
        self.assertEqual(registry["rsxermu"].base_url, "https://rsxermu666.cn")
        self.assertEqual(registry["rsxermu"].api_key, "secret-key")
        self.assertEqual(registry["rsxermu"].model, "gpt-4.1-mini")

    def test_chat_with_provider_uses_openai_base_url_and_key(self):
        provider = ProviderSettings(
            name="rsxermu",
            client_type="openai",
            base_url="https://rsxermu666.cn",
            api_key="secret-key",
            model="gpt-4.1-mini",
        )
        fake_response = MagicMock()
        fake_response.choices = [MagicMock(message=MagicMock(content='{"command":"finish"}'))]
        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value = fake_response

        with patch("main.OpenAI", return_value=fake_client) as openai_ctor:
            content = chat_with_provider(
                provider,
                messages=[{"role": "user", "content": "hi"}],
                schema={"type": "object"},
            )

        openai_ctor.assert_called_once_with(
            base_url="https://rsxermu666.cn",
            api_key="secret-key",
        )
        self.assertEqual(content, '{"command":"finish"}')


if __name__ == "__main__":
    unittest.main()
