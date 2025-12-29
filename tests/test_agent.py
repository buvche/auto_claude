"""Tests for the Claude Continuous Agent."""

import asyncio
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Import from agent module
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent import DEBOUNCE_SECONDS, IGNORE_PATTERNS, ChangeTracker, FileChangeHandler


class TestChangeTracker:
    """Tests for the ChangeTracker class."""

    @pytest.fixture
    def tracker(self):
        """Create a fresh ChangeTracker for each test."""
        return ChangeTracker()

    @pytest.mark.asyncio
    async def test_add_change_stores_path(self, tracker):
        """Test that add_change stores the file path."""
        await tracker.add_change("/path/to/file.py")
        assert "/path/to/file.py" in tracker.pending_changes

    @pytest.mark.asyncio
    async def test_add_change_updates_timestamp(self, tracker):
        """Test that adding the same path updates its timestamp."""
        await tracker.add_change("/path/to/file.py")
        first_time = tracker.pending_changes["/path/to/file.py"]

        await asyncio.sleep(0.01)
        await tracker.add_change("/path/to/file.py")
        second_time = tracker.pending_changes["/path/to/file.py"]

        assert second_time > first_time

    @pytest.mark.asyncio
    async def test_get_ready_changes_respects_debounce(self, tracker):
        """Test that changes aren't returned before debounce period."""
        await tracker.add_change("/path/to/file.py")

        # Should be empty immediately (debounce not elapsed)
        ready = await tracker.get_ready_changes()
        assert ready == []

    @pytest.mark.asyncio
    async def test_get_ready_changes_returns_after_debounce(self, tracker):
        """Test that changes are returned after debounce period."""
        # Manually set an old timestamp
        tracker.pending_changes["/path/to/file.py"] = time.time() - DEBOUNCE_SECONDS - 1

        ready = await tracker.get_ready_changes()
        assert "/path/to/file.py" in ready

    @pytest.mark.asyncio
    async def test_get_ready_changes_removes_returned_items(self, tracker):
        """Test that returned changes are removed from pending."""
        tracker.pending_changes["/path/to/file.py"] = time.time() - DEBOUNCE_SECONDS - 1

        await tracker.get_ready_changes()

        assert "/path/to/file.py" not in tracker.pending_changes

    @pytest.mark.asyncio
    async def test_multiple_changes_tracked_separately(self, tracker):
        """Test that multiple files are tracked independently."""
        await tracker.add_change("/path/to/file1.py")
        await tracker.add_change("/path/to/file2.py")

        assert len(tracker.pending_changes) == 2
        assert "/path/to/file1.py" in tracker.pending_changes
        assert "/path/to/file2.py" in tracker.pending_changes


class TestFileChangeHandler:
    """Tests for the FileChangeHandler class."""

    @pytest.fixture
    def handler(self):
        """Create a FileChangeHandler with mocked dependencies."""
        tracker = MagicMock()
        loop = MagicMock()
        return FileChangeHandler(tracker, loop)

    def test_should_ignore_git_directory(self, handler):
        """Test that .git paths are ignored."""
        assert handler._should_ignore("/project/.git/config") is True
        assert handler._should_ignore("/project/.git/objects/abc") is True

    def test_should_ignore_pycache(self, handler):
        """Test that __pycache__ paths are ignored."""
        assert handler._should_ignore("/project/__pycache__/module.pyc") is True

    def test_should_ignore_venv(self, handler):
        """Test that venv paths are ignored."""
        assert handler._should_ignore("/project/venv/lib/python3.12/site.py") is True
        assert handler._should_ignore("/project/.venv/bin/python") is True

    def test_should_ignore_node_modules(self, handler):
        """Test that node_modules paths are ignored."""
        assert handler._should_ignore("/project/node_modules/package/index.js") is True

    def test_should_ignore_pyc_files(self, handler):
        """Test that .pyc files are ignored."""
        assert handler._should_ignore("/project/module.pyc") is True

    def test_should_not_ignore_regular_python_files(self, handler):
        """Test that regular Python files are not ignored."""
        assert handler._should_ignore("/project/agent.py") is False
        assert handler._should_ignore("/project/src/main.py") is False

    def test_should_not_ignore_regular_files(self, handler):
        """Test that regular source files are not ignored."""
        assert handler._should_ignore("/project/README.md") is False
        assert handler._should_ignore("/project/config.yaml") is False


class TestIgnorePatterns:
    """Tests for the IGNORE_PATTERNS configuration."""

    def test_ignore_patterns_contains_expected_items(self):
        """Test that default ignore patterns include common items."""
        expected = {".git", "__pycache__", "venv", ".venv", "node_modules"}
        assert expected.issubset(IGNORE_PATTERNS)

    def test_ignore_patterns_is_set(self):
        """Test that IGNORE_PATTERNS is a set for O(1) lookup."""
        assert isinstance(IGNORE_PATTERNS, set)


class TestDebounceConfig:
    """Tests for debounce configuration."""

    def test_debounce_seconds_is_positive(self):
        """Test that debounce delay is a positive number."""
        assert DEBOUNCE_SECONDS > 0

    def test_debounce_seconds_is_reasonable(self):
        """Test that debounce delay is within reasonable bounds."""
        assert 0.5 <= DEBOUNCE_SECONDS <= 10.0


class TestModuleImports:
    """Tests to verify module can be imported correctly."""

    def test_agent_module_imports(self):
        """Test that the agent module imports without errors."""
        import agent
        assert hasattr(agent, 'ChangeTracker')
        assert hasattr(agent, 'FileChangeHandler')
        assert hasattr(agent, 'analyze_changes')
        assert hasattr(agent, 'apply_fixes')
        assert hasattr(agent, 'monitor_loop')
        assert hasattr(agent, 'main')

    def test_agent_has_watch_dir(self):
        """Test that WATCH_DIR is defined and is a Path."""
        import agent
        assert hasattr(agent, 'WATCH_DIR')
        assert isinstance(agent.WATCH_DIR, Path)
