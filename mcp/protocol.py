"""MCP Protocol definitions - Model Context Protocol specification.

This module contains the protocol definitions for MCP (Model Context Protocol),
including message types, capabilities, and protocol constants.

Reference: https://modelcontextprotocol.io/
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# Protocol version
MCP_PROTOCOL_VERSION = "2024-11-05"


class MCPMethod(Enum):
    """MCP protocol methods."""
    INITIALIZE = "initialize"
    TOOLS_LIST = "tools/list"
    TOOLS_CALL = "tools/call"
    RESOURCES_LIST = "resources/list"
    RESOURCES_READ = "resources/read"
    RESOURCES_SUBSCRIBE = "resources/subscribe"
    PROMPTS_LIST = "prompts/list"
    PROMPTS_GET = "prompts/get"


@dataclass
class ClientCapabilities:
    """Client capabilities announcement."""
    roots: dict = field(default_factory=dict)
    sampling: dict = field(default_factory=dict)


@dataclass
class ServerCapabilities:
    """Server capabilities announcement."""
    tools: dict | None = None
    resources: dict | None = None
    prompts: dict | None = None


@dataclass
class InitializeResult:
    """Result of initialize request."""
    protocolVersion: str
    capabilities: ServerCapabilities
    serverInfo: dict

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocolVersion": self.protocolVersion,
            "capabilities": self.capabilities or {},
            "serverInfo": self.serverInfo,
        }


@dataclass
class ToolCallArguments:
    """Arguments for a tool call."""
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "arguments": self.arguments,
        }


@dataclass
class ToolResult:
    """Result of a tool call."""
    content: list[dict[str, Any]]
    isError: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "content": self.content,
            "isError": self.isError,
        }


@dataclass
class TextContent:
    """Text content for tool results."""
    type: str = "text"
    text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "text": self.text,
        }


@dataclass
class Resource:
    """MCP resource definition."""
    uri: str
    name: str
    description: str | None = None
    mimeType: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "uri": self.uri,
            "name": self.name,
            "description": self.description,
            "mimeType": self.mimeType,
        }


@dataclass
class Prompt:
    """MCP prompt definition."""
    name: str
    description: str | None = None
    arguments: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "arguments": self.arguments,
        }


class ErrorCode(Enum):
    """MCP error codes."""
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    TOOL_NOT_FOUND = -32001
    TOOL_EXECUTION_ERROR = -32002


@dataclass
class MCPError:
    """MCP error response."""
    code: int
    message: str
    data: Any | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "data": self.data,
        }


def create_error_response(code: ErrorCode, message: str, data: Any = None) -> dict[str, Any]:
    """Create a standardized error response."""
    return {
        "jsonrpc": "2.0",
        "error": {
            "code": code.value,
            "message": message,
            "data": data,
        }
    }


def create_success_response(id: int | str, result: Any) -> dict[str, Any]:
    """Create a standardized success response."""
    return {
        "jsonrpc": "2.0",
        "id": id,
        "result": result,
    }


# Tool content types
CONTENT_TYPE_TEXT = "text"
CONTENT_TYPE_IMAGE = "image"
CONTENT_TYPE_RESOURCE = "resource"


def create_text_content(text: str) -> dict[str, Any]:
    """Create a text content block."""
    return {
        "type": CONTENT_TYPE_TEXT,
        "text": text,
    }


def create_image_content(data: str, mimeType: str = "image/png") -> dict[str, Any]:
    """Create an image content block."""
    return {
        "type": CONTENT_TYPE_IMAGE,
        "data": data,
        "mimeType": mimeType,
    }


def create_resource_content(uri: str, mimeType: str | None = None) -> dict[str, Any]:
    """Create a resource content block."""
    result = {
        "type": CONTENT_TYPE_RESOURCE,
        "resource": {"uri": uri},
    }
    if mimeType:
        result["resource"]["mimeType"] = mimeType
    return result