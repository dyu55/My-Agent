"""Browser Tools - Web browsing capabilities for the agent.

This module provides browser automation using Playwright.
Install with: pip install playwright && playwright install chromium
"""

from __future__ import annotations

import base64
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent.tools.base import BaseTool, ToolResult


@dataclass
class BrowserConfig:
    """Configuration for browser automation."""

    headless: bool = True
    timeout: int = 30000  # ms
    viewport_width: int = 1280
    viewport_height: int = 720
    user_agent: str | None = None


class BrowserTools:
    """
    Web browser automation tools using Playwright.

    Features:
    - Navigate to URLs
    - Take screenshots
    - Click elements
    - Type text
    - Extract page content
    - Evaluate JavaScript

    Usage:
        browser = BrowserTools()
        result = browser.navigate({"url": "https://example.com"})
        result = browser.screenshot({})
        result = browser.click({"selector": "#submit-btn"})
    """

    def __init__(
        self,
        workspace: str,
        config: BrowserConfig | None = None,
        enable_rollback: bool = False,
    ):
        self.workspace = workspace
        self.config = config or BrowserConfig()
        self._page = None
        self._browser = None
        self._context = None
        self._playwright = None

    def _ensure_browser(self):
        """Ensure browser is initialized."""
        if self._browser is None:
            try:
                from playwright.sync_api import sync_playwright

                self._playwright = sync_playwright().start()
                self._browser = self._playwright.chromium.launch(
                    headless=self.config.headless
                )
                self._context = self._browser.new_context(
                    viewport={
                        "width": self.config.viewport_width,
                        "height": self.config.viewport_height,
                    },
                    user_agent=self.config.user_agent,
                )
                self._page = self._context.new_page()
                self._page.set_default_timeout(self.config.timeout)
            except ImportError:
                raise ImportError(
                    "Playwright not installed. Run: pip install playwright && playwright install chromium"
                )

    def navigate(self, action: dict[str, Any]) -> ToolResult:
        """
        Navigate to a URL.

        Args:
            action["url"]: URL to navigate to

        Returns:
            ToolResult with navigation status and page title
        """
        url = action.get("url")

        if not url:
            return ToolResult.err("Missing url parameter", "Error: Missing url parameter")

        try:
            self._ensure_browser()
            response = self._page.goto(url, wait_until="domcontentloaded")

            # Get page info
            title = self._page.title()
            status = response.status if response else "unknown"

            return ToolResult.ok(
                f"✅ Navigated to {url}\n"
                f"   Status: {status}\n"
                f"   Title: {title}"
            )
        except Exception as e:
            return ToolResult.err(f"Navigation failed: {str(e)}", f"Error: {str(e)}")

    def screenshot(self, action: dict[str, Any]) -> ToolResult:
        """
        Take a screenshot of the current page.

        Args:
            action["path"]: Optional path to save screenshot (default: auto-generated)
            action["full_page"]: Capture full page (default: False)

        Returns:
            ToolResult with screenshot path or base64 data
        """
        try:
            self._ensure_browser()

            save_path = action.get("path")
            full_page = action.get("full_page", False)

            if save_path:
                # Ensure it's within workspace
                if not save_path.startswith("/"):
                    save_path = str(Path(self.workspace) / save_path)

                self._page.screenshot(path=save_path, full_page=full_page)
                return ToolResult.ok(f"✅ Screenshot saved to {save_path}")
            else:
                # Return base64 encoded screenshot
                screenshot_bytes = self._page.screenshot(full_page=full_page)
                b64 = base64.b64encode(screenshot_bytes).decode()
                return ToolResult.ok(f"Screenshot (base64, {len(b64)} bytes):\n{b64[:100]}...")

        except Exception as e:
            return ToolResult.err(f"Screenshot failed: {str(e)}", f"Error: {str(e)}")

    def click(self, action: dict[str, Any]) -> ToolResult:
        """
        Click an element on the page.

        Args:
            action["selector"]: CSS selector or XPath for element
            action["button"]: Mouse button (left, right, middle)
            action["click_count"]: Number of clicks

        Returns:
            ToolResult with click status
        """
        selector = action.get("selector")

        if not selector:
            return ToolResult.err("Missing selector parameter", "Error: Missing selector parameter")

        try:
            self._ensure_browser()

            button = action.get("button", "left")
            click_count = action.get("click_count", 1)

            element = self._page.locator(selector).first
            element.click(button=button, click_count=click_count)

            return ToolResult.ok(f"✅ Clicked element: {selector}")
        except Exception as e:
            return ToolResult.err(f"Click failed: {str(e)}", f"Error: {str(e)}")

    def type_text(self, action: dict[str, Any]) -> ToolResult:
        """
        Type text into an element or the page.

        Args:
            action["selector"]: Optional CSS selector for input element
            action["text"]: Text to type
            action["delay"]: Delay between keystrokes (ms)

        Returns:
            ToolResult with typing status
        """
        selector = action.get("selector")
        text = action.get("text")

        if not text:
            return ToolResult.err("Missing text parameter", "Error: Missing text parameter")

        try:
            self._ensure_browser()

            if selector:
                element = self._page.locator(selector).first
                delay = action.get("delay", 0)
                element.type(text, delay=delay)
            else:
                self._page.keyboard.type(text)

            return ToolResult.ok(f"✅ Typed text: {text[:50]}...")
        except Exception as e:
            return ToolResult.err(f"Type failed: {str(e)}", f"Error: {str(e)}")

    def evaluate(self, action: dict[str, Any]) -> ToolResult:
        """
        Evaluate JavaScript on the page.

        Args:
            action["script"]: JavaScript code to execute
            action["selector"]: Optional - extract from specific element

        Returns:
            ToolResult with script result
        """
        script = action.get("script")

        if not script:
            return ToolResult.err("Missing script parameter", "Error: Missing script parameter")

        try:
            self._ensure_browser()

            result = self._page.evaluate(script)

            # Format result
            if isinstance(result, dict):
                result_str = str(result)
            elif isinstance(result, list):
                result_str = f"Array({len(result)})"
            else:
                result_str = str(result)

            return ToolResult.ok(f"✅ Script executed\nResult: {result_str}")
        except Exception as e:
            return ToolResult.err(f"Script failed: {str(e)}", f"Error: {str(e)}")

    def extract_content(self, action: dict[str, Any]) -> ToolResult:
        """
        Extract content from the page.

        Args:
            action["selector"]: Optional CSS selector
            action["attribute"]: Optional attribute to extract
            action["inner_text"]: Extract inner text (default: True)

        Returns:
            ToolResult with extracted content
        """
        try:
            self._ensure_browser()

            selector = action.get("selector")
            attribute = action.get("attribute")
            inner_text = action.get("inner_text", True)

            if selector:
                element = self._page.locator(selector).first
                if attribute:
                    content = element.get_attribute(attribute)
                else:
                    content = element.inner_text() if inner_text else element.inner_html()
            else:
                content = self._page.content()

            # Truncate long content
            if len(content) > 5000:
                content = content[:5000] + f"\n... (truncated, {len(content)} total)"

            return ToolResult.ok(content)
        except Exception as e:
            return ToolResult.err(f"Extract failed: {str(e)}", f"Error: {str(e)}")

    def wait(self, action: dict[str, Any]) -> ToolResult:
        """
        Wait for a condition on the page.

        Args:
            action["selector"]: Wait for element to appear
            action["timeout"]: Max wait time in ms
            action["state"]: "visible", "hidden", "attached", "detached"

        Returns:
            ToolResult with wait status
        """
        selector = action.get("selector")
        timeout = action.get("timeout", 30000)
        state = action.get("state", "visible")

        if not selector:
            return ToolResult.err("Missing selector parameter", "Error: Missing selector parameter")

        try:
            self._ensure_browser()

            self._page.wait_for_selector(selector, timeout=timeout, state=state)
            return ToolResult.ok(f"✅ Element found: {selector}")
        except Exception as e:
            return ToolResult.err(f"Wait failed: {str(e)}", f"Error: {str(e)}")

    def get_page_info(self, action: dict[str, Any]) -> ToolResult:
        """Get information about the current page."""
        try:
            self._ensure_browser()

            info = {
                "url": self._page.url,
                "title": self._page.title(),
                "viewport": self._page.viewport_size,
            }

            return ToolResult.ok(str(info))
        except Exception as e:
            return ToolResult.err(f"Failed to get page info: {str(e)}", f"Error: {str(e)}")

    def back(self, action: dict[str, Any]) -> ToolResult:
        """Navigate back in browser history."""
        try:
            self._ensure_browser()
            self._page.go_back()
            return ToolResult.ok(f"✅ Navigated back to {self._page.url}")
        except Exception as e:
            return ToolResult.err(f"Back navigation failed: {str(e)}", f"Error: {str(e)}")

    def forward(self, action: dict[str, Any]) -> ToolResult:
        """Navigate forward in browser history."""
        try:
            self._ensure_browser()
            self._page.go_forward()
            return ToolResult.ok(f"✅ Navigated forward to {self._page.url}")
        except Exception as e:
            return ToolResult.err(f"Forward navigation failed: {str(e)}", f"Error: {str(e)}")

    def reload(self, action: dict[str, Any]) -> ToolResult:
        """Reload the current page."""
        try:
            self._ensure_browser()
            self._page.reload()
            return ToolResult.ok(f"✅ Reloaded {self._page.url}")
        except Exception as e:
            return ToolResult.err(f"Reload failed: {str(e)}", f"Error: {str(e)}")

    def close(self, action: dict[str, Any] | None = None) -> ToolResult:
        """Close the browser."""
        try:
            if self._browser:
                self._browser.close()
                self._browser = None
                self._context = None
                self._page = None
            if self._playwright:
                self._playwright.stop()
                self._playwright = None
            return ToolResult.ok("✅ Browser closed")
        except Exception as e:
            return ToolResult.err(f"Close failed: {str(e)}", f"Error: {str(e)}")

    def __del__(self):
        """Cleanup on deletion."""
        try:
            self.close()
        except Exception:
            pass


def get_browser_tool_handlers(workspace: str) -> dict[str, callable]:
    """Get browser tool handlers for ToolExecutor."""
    browser = BrowserTools(workspace)
    return {
        "browse": browser.navigate,
        "navigate": browser.navigate,
        "screenshot": browser.screenshot,
        "click": browser.click,
        "type": browser.type_text,
        "evaluate": browser.evaluate,
        "extract": browser.extract_content,
        "wait": browser.wait,
        "page_info": browser.get_page_info,
        "back": browser.back,
        "forward": browser.forward,
        "reload": browser.reload,
        "close_browser": browser.close,
    }


# Simplified browser without Playwright (for basic HTML fetching)
class SimpleBrowserTools:
    """
    Simple browser using requests + BeautifulSoup.

    Falls back when Playwright is not available.
    """

    def __init__(self, workspace: str):
        self.workspace = workspace

    def fetch(self, action: dict[str, Any]) -> ToolResult:
        """
        Fetch and parse a webpage.

        Args:
            action["url"]: URL to fetch
            action["selector"]: Optional CSS selector to extract

        Returns:
            ToolResult with page content
        """
        import re

        url = action.get("url")

        if not url:
            return ToolResult.err("Missing url parameter", "Error: Missing url parameter")

        try:
            import requests
            from bs4 import BeautifulSoup

            response = requests.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            selector = action.get("selector")
            if selector:
                elements = soup.select(selector)
                if elements:
                    content = "\n".join(el.get_text(strip=True) for el in elements[:10])
                else:
                    content = "No elements found"
            else:
                # Return page title and first paragraph
                title = soup.title.string if soup.title else "No title"
                paragraphs = soup.find_all("p")[:5]
                content = f"Title: {title}\n\n"
                content += "\n\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))

            # Truncate if too long
            if len(content) > 5000:
                content = content[:5000] + f"\n... (truncated)"

            return ToolResult.ok(content)
        except ImportError:
            return ToolResult.err(
                "requests/beautifulsoup4 not installed",
                "Error: Install with pip install requests beautifulsoup4"
            )
        except Exception as e:
            return ToolResult.err(f"Fetch failed: {str(e)}", f"Error: {str(e)}")


def get_simple_browser_handlers(workspace: str) -> dict[str, callable]:
    """Get simple browser tool handlers."""
    browser = SimpleBrowserTools(workspace)
    return {
        "fetch": browser.fetch,
        "get_page": browser.fetch,
    }