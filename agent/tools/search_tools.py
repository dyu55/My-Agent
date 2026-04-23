"""Search tools - file search, web search, URL fetch."""

import json
import re
from pathlib import Path
from typing import Any

from .base import ToolResult

try:
    import requests
except ImportError:
    requests = None


class SearchTools:
    """Container for search tools."""

    def __init__(self, workspace: str):
        self.workspace = workspace

    def search_files(self, action: dict[str, Any]) -> ToolResult:
        """Search for text in files."""
        query = action.get("query")

        if not query:
            return ToolResult.err("Missing query", "Error: Missing query")

        matches = []
        search_path = Path(self.workspace)
        lowered = query.lower()

        for file_path in search_path.rglob("*"):
            if file_path.is_file():
                try:
                    for line_no, line in enumerate(
                        file_path.read_text(encoding="utf-8").splitlines(), start=1
                    ):
                        if lowered in line.lower():
                            matches.append(
                                f"{file_path.relative_to(search_path)}:{line_no}: {line}"
                            )
                except Exception:
                    continue

        return ToolResult.ok("\n".join(matches) if matches else "No matches found")

    def search_web(self, action: dict[str, Any]) -> ToolResult:
        """Search the web for information."""
        query = action.get("query")

        if not query:
            return ToolResult.err("Missing query", "Error: Missing query")

        if requests is None:
            return ToolResult.err("requests library not installed", "Error: requests library not installed")

        try:
            import urllib.parse

            encoded = urllib.parse.quote(query)
            url = f"https://api.duckduckgo.com/?format=json&q={encoded}&t=harness_agent"

            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("AbstractText"):
                    return ToolResult.ok(f"Answer: {data['AbstractText']}")

                results = []
                for topic in data.get("RelatedTopics", [])[:5]:
                    if "Text" in topic:
                        results.append(f"- {topic['Text']}")

                if results:
                    return ToolResult.ok(f"Search results for '{query}':\n" + "\n".join(results))
                return ToolResult.ok(f"No results found for: {query}")
            return ToolResult.err(f"Search failed with status {response.status_code}", f"Error: Search failed with status {response.status_code}")
        except Exception as e:
            return ToolResult.err(f"Error during web search: {str(e)}", f"Error during web search: {str(e)}")

    def fetch_url(self, action: dict[str, Any]) -> ToolResult:
        """Fetch content from a URL."""
        url = action.get("url")

        if not url:
            return ToolResult.err("Missing URL", "Error: Missing URL")

        if requests is None:
            return ToolResult.err("requests library not installed", "Error: requests library not installed")

        try:
            response = requests.get(
                url,
                timeout=15,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                },
            )
            if response.status_code != 200:
                return ToolResult.err(f"Fetch failed with status {response.status_code}", f"Error: Fetch failed with status {response.status_code}")

            # Try JSON first
            try:
                data = response.json()
                return ToolResult.ok(f"=== JSON Response ===\n{json.dumps(data, ensure_ascii=False, indent=2)[:3000]}")
            except Exception:
                pass

            # Clean HTML
            text = re.sub(r"<[^>]+>", " ", response.text)
            text = re.sub(r"\s+", " ", text).strip()
            return ToolResult.ok(f"=== Page Content ===\n{text[:3000]}")
        except Exception as e:
            return ToolResult.err(f"Error fetching page: {str(e)}", f"Error fetching page: {str(e)}")


def get_search_tool_handlers(workspace: str) -> dict[str, callable]:
    """Get search tool handlers for ToolExecutor."""
    tools = SearchTools(workspace)
    return {
        "search": tools.search_files,
        "search_web": tools.search_web,
        "web_fetch": tools.fetch_url,
    }
