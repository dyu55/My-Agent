"""Schema utilities for structured LLM output."""

import json
import re
from typing import Any


class SchemaValidator:
    """Validates and parses structured output from LLMs."""

    def __init__(self, schema: dict[str, Any] | None = None):
        """
        Initialize schema validator.

        Args:
            schema: Optional JSON schema for validation
        """
        self.schema = schema

    def parse_json(self, response: str) -> dict[str, Any] | None:
        """
        Parse JSON from LLM response.

        Args:
            response: Raw response text

        Returns:
            Parsed JSON as dict, or None if parsing fails
        """
        # Try direct JSON parsing first
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # Try to extract JSON from markdown code blocks
        json_match = re.search(r"```(?:json)?\s*\n?([\s\S]*?)\n?```", response)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to extract JSON from response
        json_match = re.search(r"\{[\s\S]*\}", response)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        return None

    def extract_structured_output(
        self,
        response: str,
        required_fields: list[str] | None = None
    ) -> tuple[dict[str, Any] | None, str | None]:
        """
        Extract and validate structured output.

        Args:
            response: Raw LLM response
            required_fields: List of required field names

        Returns:
            Tuple of (parsed_data, error_message)
        """
        data = self.parse_json(response)

        if data is None:
            return None, "Failed to parse JSON from response"

        if required_fields:
            missing = [f for f in required_fields if f not in data]
            if missing:
                return None, f"Missing required fields: {', '.join(missing)}"

        return data, None

    def validate_command(self, data: dict[str, Any]) -> tuple[bool, str]:
        """
        Validate that data contains a valid command.

        Args:
            data: Parsed command data

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(data, dict):
            return False, "Command must be a dictionary"

        if "command" not in data:
            return False, "Missing 'command' field"

        command = data["command"]
        if not isinstance(command, str) or not command:
            return False, "Command must be a non-empty string"

        return True, ""


# Common schemas for agent commands
COMMAND_SCHEMA = {
    "type": "object",
    "properties": {
        "command": {
            "type": "string",
            "description": "Command name (write, edit, read, execute, etc.)"
        },
        "path": {
            "type": "string",
            "description": "File path for file operations"
        },
        "content": {
            "type": "string",
            "description": "File content or new text for edit"
        },
        "old_text": {
            "type": "string",
            "description": "Text to replace (for edit command)"
        },
        "script": {
            "type": "string",
            "description": "Script to execute"
        },
        "query": {
            "type": "string",
            "description": "Search query"
        },
        "url": {
            "type": "string",
            "description": "URL for web operations"
        }
    },
    "required": ["command"]
}

PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "task": {
            "type": "string",
            "description": "Task description"
        },
        "subtasks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "description": {"type": "string"},
                    "dependencies": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["id", "description"]
            }
        }
    },
    "required": ["task", "subtasks"]
}
