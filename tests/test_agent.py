import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from agent.executor import Action
from utils.conversation import ConversationMemory
from utils.logger import TraceLogger


class StructuredOutputTests(unittest.TestCase):
    def test_action_object_structure(self):
        action = Action(command="write", path="app.py", content="print('hello')")
        self.assertIsInstance(action, Action)
        self.assertEqual(action.command, "write")
        self.assertEqual(action.path, "app.py")


class ContextManagementTests(unittest.TestCase):
    def test_memory_summarizes_old_steps_and_keeps_recent_turns(self):
        memory = ConversationMemory(max_pairs=2)
        memory.add("assistant", "first thought")
        memory.add("user", "first observation")
        memory.add("assistant", "second thought")
        memory.add("user", "second observation")
        memory.add("assistant", "third thought")
        memory.add("user", "third observation")

        messages = memory.build_messages(
            system_prompt="system prompt",
            task="do something useful",
        )

        self.assertEqual(messages[0]["role"], "system")
        # Find summary message
        summary_messages = [
            m
            for m in messages
            if m["role"] == "system" and "Summary:" in m["content"]
        ]
        self.assertEqual(len(summary_messages), 1)
        # first observation should be in summary
        self.assertIn("first observation", summary_messages[0]["content"])
        # third observation should be in recent turns
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


if __name__ == "__main__":
    unittest.main()
