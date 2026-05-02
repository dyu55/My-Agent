"""Browser Skill - Web browsing capabilities for the agent."""

from __future__ import annotations

from pathlib import Path

from skills.registry import BaseSkill, SkillContext


class BrowserSkill(BaseSkill):
    """Browse the web and extract information."""

    name = "browse"
    description = "Browse websites, take screenshots, and extract content"
    aliases = ["browser", "web", "fetch"]
    category = "tools"

    def execute(self, context: SkillContext, args: str) -> str:
        """Execute browser operations."""
        from agent.tools.browser_tools import BrowserTools

        params = self._parse_args(args)
        url = params.get("url") or params.get("_positional")

        if not url:
            return self._help()

        action_type = params.get("action", "fetch")

        browser = BrowserTools(str(context.workspace))

        if action_type == "fetch":
            result = browser.navigate({"url": url})
            if result.is_ok():
                # Also extract title
                info = browser.get_page_info({})
                return info.output
            return result.output

        elif action_type == "screenshot":
            browser.navigate({"url": url})
            path = params.get("path", "screenshot.png")
            result = browser.screenshot({"path": path})
            return result.output

        elif action_type == "extract":
            browser.navigate({"url": url})
            selector = params.get("selector", "body")
            result = browser.extract_content({"selector": selector})
            return result.output

        else:
            return self._help()

    def _parse_args(self, args: str) -> dict[str, str | None]:
        """Parse command-line style arguments."""
        params = {}
        if not args:
            return params

        parts = args.split()
        for i, part in enumerate(parts):
            if part.startswith("--"):
                param_name = part[2:].replace("-", "_")
                if i + 1 < len(parts) and not parts[i + 1].startswith("--"):
                    params[param_name] = parts[i + 1]
                else:
                    params[param_name] = None
            elif "=" in part:
                key, val = part.split("=", 1)
                params[key.replace("-", "_")] = val

        return params

    def _help(self) -> str:
        """Return help text."""
        return """🔍 Browser Skill Usage:

Browse a URL:
  /browse https://example.com

Fetch and extract:
  /browse https://example.com --action extract --selector h1

Take screenshot:
  /browse https://example.com --action screenshot --path screenshot.png

Options:
  --action fetch|screenshot|extract
  --selector CSS selector for extraction
  --path Save path for screenshots
"""