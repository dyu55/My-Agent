"""Tests for agent/tools/browser_tools.py."""

import pytest
from pathlib import Path

from agent.tools.browser_tools import (
    BrowserTools,
    BrowserConfig,
    SimpleBrowserTools,
    get_browser_tool_handlers,
    get_simple_browser_handlers,
)


class TestBrowserConfig:
    """Tests for BrowserConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = BrowserConfig()
        assert config.headless is True
        assert config.timeout == 30000
        assert config.viewport_width == 1280
        assert config.viewport_height == 720

    def test_custom_config(self):
        """Test custom configuration."""
        config = BrowserConfig(
            headless=False,
            timeout=60000,
            viewport_width=1920,
            viewport_height=1080,
        )
        assert config.headless is False
        assert config.timeout == 60000
        assert config.viewport_width == 1920


class TestBrowserTools:
    """Tests for BrowserTools."""

    @pytest.fixture
    def browser(self, tmp_path):
        """Create BrowserTools instance."""
        return BrowserTools(str(tmp_path))

    def test_initialization(self, browser):
        """Test BrowserTools initialization."""
        assert browser.workspace is not None
        assert browser._page is None  # Not started yet
        assert browser._browser is None

    def test_browser_config(self, tmp_path):
        """Test BrowserTools with custom config."""
        config = BrowserConfig(headless=True)
        browser = BrowserTools(str(tmp_path), config=config)
        assert browser.config.headless is True

    def test_close_when_not_started(self, browser):
        """Test closing browser when not started."""
        result = browser.close()
        assert result.success
        assert "closed" in result.output.lower()


class TestSimpleBrowserTools:
    """Tests for SimpleBrowserTools."""

    @pytest.fixture
    def browser(self, tmp_path):
        """Create SimpleBrowserTools instance."""
        return SimpleBrowserTools(str(tmp_path))

    def test_initialization(self, browser):
        """Test SimpleBrowserTools initialization."""
        assert browser.workspace is not None

    def test_fetch_missing_url(self, browser):
        """Test fetch without URL returns error."""
        result = browser.fetch({})
        assert not result.success
        assert "url" in result.output.lower()

    def test_fetch_with_url_check(self, browser):
        """Test fetch with invalid URL returns error."""
        result = browser.fetch({"url": "not-a-valid-url"})
        # Should fail with connection/request error
        assert not result.success


class TestToolHandlers:
    """Tests for tool handler registration."""

    def test_browser_handlers_exist(self):
        """Test that all browser handlers are registered."""
        handlers = get_browser_tool_handlers("/tmp")

        expected = [
            "browse", "navigate", "screenshot", "click",
            "type", "evaluate", "extract", "wait",
            "page_info", "back", "forward", "reload", "close_browser"
        ]

        for name in expected:
            assert name in handlers, f"Missing handler: {name}"

    def test_simple_browser_handlers_exist(self):
        """Test that simple browser handlers are registered."""
        handlers = get_simple_browser_handlers("/tmp")

        expected = ["fetch", "get_page"]

        for name in expected:
            assert name in handlers, f"Missing handler: {name}"


class TestIntegration:
    """Integration tests for browser tools."""

    def test_full_handler_integration(self, tmp_path):
        """Test that handlers are callable."""
        handlers = get_browser_tool_handlers(str(tmp_path))

        # close_browser should work even without browser started
        result = handlers["close_browser"]({})
        assert result.success

    def test_simple_handler_integration(self, tmp_path):
        """Test simple browser handlers."""
        handlers = get_simple_browser_handlers(str(tmp_path))

        # Test with invalid URL
        result = handlers["fetch"]({"url": "invalid"})
        assert not result.success  # Should fail, not crash