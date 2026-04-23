"""MCP Client - Model Context Protocol client for tool integration."""

import json
import subprocess
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable
import asyncio


class MCPConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class MCPMessage:
    """Message for MCP communication."""

    jsonrpc: str = "2.0"
    id: str | int | None = None
    method: str | None = None
    params: dict[str, Any] | None = None
    result: Any | None = None
    error: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        result = {"jsonrpc": self.jsonrpc}
        if self.id is not None:
            result["id"] = self.id
        if self.method:
            result["method"] = self.method
        if self.params:
            result["params"] = self.params
        if self.result is not None:
            result["result"] = self.result
        if self.error:
            result["error"] = self.error
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MCPMessage":
        return cls(
            jsonrpc=data.get("jsonrpc", "2.0"),
            id=data.get("id"),
            method=data.get("method"),
            params=data.get("params"),
            result=data.get("result"),
            error=data.get("error"),
        )


@dataclass
class MCPTool:
    """Represents a tool available through MCP."""

    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[..., Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


@dataclass
class MCPServer:
    """Represents an MCP server connection."""

    name: str
    command: list[str]
    env: dict[str, str] = field(default_factory=dict)
    state: MCPConnectionState = MCPConnectionState.DISCONNECTED
    tools: list[MCPTool] = field(default_factory=list)
    process: subprocess.Popen | None = None


class MCPClient:
    """
    MCP Client for connecting to MCP servers.

    MCP (Model Context Protocol) allows connecting to external tools
    that can be called by the agent.
    """

    def __init__(self):
        self.servers: dict[str, MCPServer] = {}
        self.tools: dict[str, MCPTool] = {}
        self._message_id = 0
        self._lock = threading.Lock()

    def add_server(self, name: str, command: list[str], env: dict[str, str] | None = None) -> None:
        """Add an MCP server configuration."""
        self.servers[name] = MCPServer(
            name=name,
            command=command,
            env=env or {},
        )

    def connect(self, name: str) -> bool:
        """Connect to an MCP server."""
        if name not in self.servers:
            return False

        server = self.servers[name]
        try:
            env = dict(__import__("os").environ)
            env.update(server.env)

            server.process = subprocess.Popen(
                server.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=True,
            )

            # Initialize the connection
            if self._initialize_server(server):
                server.state = MCPConnectionState.CONNECTED
                self._discover_tools(server)
                return True

        except Exception as e:
            server.state = MCPConnectionState.ERROR
            print(f"Failed to connect to MCP server {name}: {e}")

        return False

    def _initialize_server(self, server: MCPServer) -> bool:
        """Send initialization request to MCP server."""
        try:
            # Send initialize
            init_request = MCPMessage(
                id=self._next_id(),
                method="initialize",
                params={
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "michael",
                        "version": "0.1.0",
                    },
                },
            )

            response = self._send_request(server, init_request)
            return response is not None and response.error is None

        except Exception:
            return False

    def _discover_tools(self, server: MCPServer) -> None:
        """Discover available tools from the server."""
        try:
            request = MCPMessage(id=self._next_id(), method="tools/list")
            response = self._send_request(server, request)

            if response and response.result:
                for tool in response.result.get("tools", []):
                    mcp_tool = MCPTool(
                        name=tool["name"],
                        description=tool.get("description", ""),
                        input_schema=tool.get("inputSchema", {}),
                    )
                    server.tools.append(mcp_tool)
                    self.tools[f"{server.name}/{mcp_tool.name}"] = mcp_tool

        except Exception:
            pass

    def _send_request(self, server: MCPServer, message: MCPMessage) -> MCPMessage | None:
        """Send a request to the MCP server."""
        if not server.process:
            return None

        try:
            request_json = json.dumps(message.to_dict()) + "\n"
            server.process.stdin.write(request_json)
            server.process.stdin.flush()

            # Wait for response
            response_line = server.process.stdout.readline()
            if response_line:
                return MCPMessage.from_dict(json.loads(response_line))

        except Exception:
            pass

        return None

    def call_tool(self, server_name: str, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Call a tool on an MCP server."""
        key = f"{server_name}/{tool_name}"
        if key not in self.tools:
            return {"error": f"Tool {tool_name} not found on {server_name}"}

        if server_name not in self.servers:
            return {"error": f"Server {server_name} not found"}

        server = self.servers[server_name]

        request = MCPMessage(
            id=self._next_id(),
            method="tools/call",
            params={
                "name": tool_name,
                "arguments": arguments,
            },
        )

        response = self._send_request(server, request)
        if response and response.result:
            return response.result
        return {"error": response.error if response else "No response"}

    def disconnect(self, name: str) -> None:
        """Disconnect from an MCP server."""
        if name not in self.servers:
            return

        server = self.servers[name]
        if server.process:
            server.process.terminate()
            server.process = None

        server.state = MCPConnectionState.DISCONNECTED

    def list_tools(self) -> list[dict[str, Any]]:
        """List all available tools."""
        return [tool.to_dict() for tool in self.tools.values()]

    def _next_id(self) -> int:
        """Generate next message ID."""
        with self._lock:
            self._message_id += 1
            return self._message_id

    def get_status(self) -> dict[str, Any]:
        """Get connection status for all servers."""
        return {
            name: {
                "state": server.state.value,
                "tools": [t.name for t in server.tools],
            }
            for name, server in self.servers.items()
        }


# Built-in MCP servers configuration
DEFAULT_MCP_SERVERS = {
    "filesystem": {
        "command": ["npx", "-y", "@modelcontextprotocol/server-filesystem", "."],
        "description": "File system operations",
    },
    "github": {
        "command": ["npx", "-y", "@modelcontextprotocol/server-github"],
        "description": "GitHub integration",
    },
}


def create_mcp_client(enabled_servers: list[str] | None = None) -> MCPClient:
    """Create an MCP client with default servers."""
    client = MCPClient()

    for server_name in (enabled_servers or ["filesystem"]):
        if server_name in DEFAULT_MCP_SERVERS:
            config = DEFAULT_MCP_SERVERS[server_name]
            client.add_server(
                name=server_name,
                command=config["command"],
                env=config.get("env", {}),
            )

    return client