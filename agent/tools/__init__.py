"""Agent Tools Package - Modular tool implementations."""

from .base import BaseTool, ToolResult
from .file_tools import FileTools
from .exec_tools import ExecTools
from .search_tools import SearchTools
from .git_tools import GitTools

# Import new tools (lazy to avoid circular imports)
def get_all_tools():
    """Get all available tools."""
    from .test_tools import TestTools
    from .quality_tools import QualityTools
    from .dependency_tools import DependencyTools
    from .deploy_tools import DeployTools

    return {
        "file": FileTools,
        "exec": ExecTools,
        "search": SearchTools,
        "git": GitTools,
        "test": TestTools,
        "quality": QualityTools,
        "dependency": DependencyTools,
        "deploy": DeployTools,
    }

__all__ = [
    "BaseTool",
    "ToolResult",
    "FileTools",
    "ExecTools",
    "SearchTools",
    "GitTools",
]
