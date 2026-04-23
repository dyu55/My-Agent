"""MCP (Model Context Protocol) tools integration."""

from typing import Any

from .base import ToolResult


class MCPTools:
    """Container for MCP-related tools."""

    def __init__(self, workspace: str):
        self.workspace = workspace
        self.mcp_client = None

    def set_mcp_client(self, client) -> None:
        """Set the MCP client for tool execution."""
        self.mcp_client = client

    def call_mcp_tool(self, action: dict[str, Any]) -> ToolResult:
        """Call an MCP tool."""
        tool_name = action.get("tool")
        tool_args = action.get("args", {})

        if not tool_name:
            return ToolResult.err("Missing tool name", "Error: Missing tool name")

        if self.mcp_client is None:
            return ToolResult.err("MCP client not initialized", "Error: MCP client not initialized")

        try:
            result = self.mcp_client.call_tool(tool_name, tool_args)
            return ToolResult.ok(str(result))
        except Exception as e:
            return ToolResult.err(f"Error calling MCP tool: {str(e)}", f"Error calling MCP tool: {str(e)}")

    def list_mcp_tools(self, action: dict[str, Any]) -> ToolResult:
        """List available MCP tools."""
        if self.mcp_client is None:
            return ToolResult.err("MCP client not initialized", "Error: MCP client not initialized")

        try:
            tools = self.mcp_client.list_tools()
            if not tools:
                return ToolResult.ok("No MCP tools available")

            tool_list = "\n".join(f"- {t['name']}: {t.get('description', 'No description')}" for t in tools)
            return ToolResult.ok(f"Available MCP tools:\n{tool_list}")
        except Exception as e:
            return ToolResult.err(f"Error listing MCP tools: {str(e)}", f"Error listing MCP tools: {str(e)}")


def get_mcp_tool_handlers(workspace: str) -> dict[str, callable]:
    """Get MCP tool handlers for ToolExecutor."""
    tools = MCPTools(workspace)
    return {
        "mcp_call": tools.call_mcp_tool,
        "mcp_list": tools.list_mcp_tools,
    }
