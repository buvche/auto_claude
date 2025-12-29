"""Tests for the Task Detector module."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Import from task_detector module
sys.path.insert(0, str(Path(__file__).parent.parent))

from task_detector import (
    get_pending_tasks,
    has_pending_tasks,
    parse_claude_md,
    parse_plan_md,
    parse_todo_md,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for test files."""
    return tmp_path


@pytest.fixture
def empty_todo_md(temp_dir):
    """Create an empty TODO.md file."""
    path = temp_dir / "TODO.md"
    path.write_text("")
    return path


@pytest.fixture
def empty_plan_md(temp_dir):
    """Create an empty PLAN.md file."""
    path = temp_dir / "PLAN.md"
    path.write_text("")
    return path


@pytest.fixture
def empty_claude_md(temp_dir):
    """Create an empty CLAUDE.md file."""
    path = temp_dir / "CLAUDE.md"
    path.write_text("")
    return path


@pytest.fixture
def whitespace_only_file(temp_dir):
    """Create a file with only whitespace."""
    path = temp_dir / "whitespace.md"
    path.write_text("   \n\t\n   \n\n   ")
    return path


@pytest.fixture
def todo_with_backlog_tasks(temp_dir):
    """Create a TODO.md with backlog tasks."""
    path = temp_dir / "TODO.md"
    path.write_text("""# TODO

## In Progress

_No tasks currently in progress_

---

## Backlog

### [HIGH] @config - Add configuration file support

**Goal:** Allow users to customize agent behavior.

### [MED] @feature - Support watching multiple directories

**Goal:** Monitor multiple projects.

### [LOW] @test - Add unit tests

**Goal:** Ensure reliability.

---

## Completed

- [x] @infra - Set up Python virtual environment
""")
    return path


@pytest.fixture
def todo_with_in_progress_tasks(temp_dir):
    """Create a TODO.md with in-progress tasks."""
    path = temp_dir / "TODO.md"
    path.write_text("""# TODO

## In Progress

### [HIGH] @feature - Implement file logging

**Goal:** Persist agent activity.

---

## Backlog

### [LOW] @test - Add unit tests

---

## Completed

- [x] Done task
""")
    return path


@pytest.fixture
def plan_with_unchecked_items(temp_dir):
    """Create a PLAN.md with unchecked items."""
    path = temp_dir / "PLAN.md"
    path.write_text("""# Project Plan

## Phase 1 (Completed)

- [x] Set up project structure
- [x] Configure virtual environment

## Phase 2 (Future)

- [ ] Add configuration file support
- [ ] Implement logging to file
- [x] Create documentation

## Phase 3

- [ ] Add notifications
""")
    return path


@pytest.fixture
def claude_with_action_items(temp_dir):
    """Create a CLAUDE.md with action items."""
    path = temp_dir / "CLAUDE.md"
    path.write_text("""# CLAUDE.md

## Action Items

- [ ] Update documentation
TODO: Add more examples

## Guidelines

Follow the style guide.
""")
    return path


# ============================================================================
# Tests for parse_todo_md
# ============================================================================


class TestParseTodoMd:
    """Tests for the parse_todo_md function."""

    def test_parse_backlog_tasks(self, todo_with_backlog_tasks):
        """Test parsing tasks from backlog section."""
        tasks = parse_todo_md(todo_with_backlog_tasks)

        assert len(tasks) == 3
        assert tasks[0]["title"] == "Add configuration file support"
        assert tasks[0]["priority"] == "HIGH"
        assert tasks[0]["type"] == "@config"
        assert tasks[0]["source"] == "TODO.md"

    def test_parse_in_progress_tasks(self, todo_with_in_progress_tasks):
        """Test parsing tasks from in-progress section."""
        tasks = parse_todo_md(todo_with_in_progress_tasks)

        assert len(tasks) == 2
        assert tasks[0]["title"] == "Implement file logging"
        assert tasks[0]["priority"] == "HIGH"

    def test_empty_file_returns_empty_list(self, empty_todo_md):
        """Test that empty file returns empty list."""
        tasks = parse_todo_md(empty_todo_md)
        assert tasks == []

    def test_whitespace_only_file_returns_empty_list(self, temp_dir):
        """Test that file with only whitespace returns empty list."""
        path = temp_dir / "TODO.md"
        path.write_text("   \n\t\n   \n\n   ")
        tasks = parse_todo_md(path)
        assert tasks == []

    def test_missing_file_returns_empty_list(self, temp_dir):
        """Test that missing file returns empty list, not crash."""
        missing_path = temp_dir / "NONEXISTENT.md"
        tasks = parse_todo_md(missing_path)
        assert tasks == []

    def test_malformed_task_header_missing_priority(self, temp_dir):
        """Test that malformed task header without priority is ignored."""
        path = temp_dir / "TODO.md"
        path.write_text("""# TODO

## Backlog

### @feature - Missing priority bracket

Should not be parsed.
""")
        tasks = parse_todo_md(path)
        assert tasks == []

    def test_malformed_task_header_missing_type(self, temp_dir):
        """Test that malformed task header without type is ignored."""
        path = temp_dir / "TODO.md"
        path.write_text("""# TODO

## Backlog

### [HIGH] - Missing type

Should not be parsed.
""")
        tasks = parse_todo_md(path)
        assert tasks == []

    def test_malformed_task_header_missing_dash(self, temp_dir):
        """Test that malformed task header without dash separator is ignored."""
        path = temp_dir / "TODO.md"
        path.write_text("""# TODO

## Backlog

### [HIGH] @feature No dash separator

Should not be parsed.
""")
        tasks = parse_todo_md(path)
        assert tasks == []

    def test_unicode_emoji_in_task_title(self, temp_dir):
        """Test that Unicode/emoji in task titles are handled correctly."""
        path = temp_dir / "TODO.md"
        path.write_text("""# TODO

## Backlog

### [HIGH] @feature - Add rocket launch feature
### [MED] @test - Test  handling
### [LOW] @docs - Update with
""")
        tasks = parse_todo_md(path)

        assert len(tasks) == 3
        assert "rocket launch feature" in tasks[0]["title"]
        assert "handling" in tasks[1]["title"]
        assert tasks[0]["priority"] == "HIGH"

    def test_special_characters_in_task_title(self, temp_dir):
        """Test that special characters in task titles are handled correctly."""
        path = temp_dir / "TODO.md"
        path.write_text("""# TODO

## Backlog

### [HIGH] @feature - Support C++ & C# languages
### [MED] @config - Handle paths with spaces (e.g., "My Documents")
### [LOW] @test - Test regex patterns like .*\\.py$
""")
        tasks = parse_todo_md(path)

        assert len(tasks) == 3
        assert "C++ & C#" in tasks[0]["title"]
        assert "spaces" in tasks[1]["title"]
        assert "regex" in tasks[2]["title"]

    def test_simple_in_progress_header_format(self, temp_dir):
        """Test simple header format in in-progress section."""
        path = temp_dir / "TODO.md"
        path.write_text("""# TODO

## In Progress

### Simple task without priority

Working on this now.

## Backlog

### [LOW] @test - Test task
""")
        tasks = parse_todo_md(path)

        assert len(tasks) == 2
        # The simple header task should have None for priority and type
        simple_task = next((t for t in tasks if t["priority"] is None), None)
        assert simple_task is not None
        assert simple_task["title"] == "Simple task without priority"
        assert simple_task["type"] is None

    def test_tasks_in_completed_section_ignored(self, temp_dir):
        """Test that tasks in completed section are ignored."""
        path = temp_dir / "TODO.md"
        path.write_text("""# TODO

## In Progress

_No tasks currently in progress_

## Completed

### [HIGH] @feature - This should be ignored

- [x] Also ignored
""")
        tasks = parse_todo_md(path)
        assert tasks == []

    def test_lowercase_priority_normalized_to_uppercase(self, temp_dir):
        """Test that lowercase priorities are normalized to uppercase."""
        path = temp_dir / "TODO.md"
        path.write_text("""# TODO

## Backlog

### [high] @feature - Lowercase priority
### [Med] @test - Mixed case priority
""")
        tasks = parse_todo_md(path)

        assert len(tasks) == 2
        assert tasks[0]["priority"] == "HIGH"
        assert tasks[1]["priority"] == "MED"

    def test_placeholder_text_ignored(self, temp_dir):
        """Test that placeholder text in in-progress is ignored."""
        path = temp_dir / "TODO.md"
        path.write_text("""# TODO

## In Progress

_No tasks currently in progress_

## Backlog

### [LOW] @test - Real task
""")
        tasks = parse_todo_md(path)

        assert len(tasks) == 1
        assert tasks[0]["title"] == "Real task"


# ============================================================================
# Tests for parse_plan_md
# ============================================================================


class TestParsePlanMd:
    """Tests for the parse_plan_md function."""

    def test_parse_unchecked_items(self, plan_with_unchecked_items):
        """Test parsing unchecked items from PLAN.md."""
        tasks = parse_plan_md(plan_with_unchecked_items)

        assert len(tasks) == 3
        assert tasks[0]["title"] == "Add configuration file support"
        assert tasks[0]["source"] == "PLAN.md"
        assert tasks[0]["priority"] is None
        assert tasks[0]["type"] is None

    def test_empty_file_returns_empty_list(self, empty_plan_md):
        """Test that empty file returns empty list."""
        tasks = parse_plan_md(empty_plan_md)
        assert tasks == []

    def test_whitespace_only_file_returns_empty_list(self, temp_dir):
        """Test that file with only whitespace returns empty list."""
        path = temp_dir / "PLAN.md"
        path.write_text("   \n\t\n   \n\n   ")
        tasks = parse_plan_md(path)
        assert tasks == []

    def test_missing_file_returns_empty_list(self, temp_dir):
        """Test that missing file returns empty list, not crash."""
        missing_path = temp_dir / "NONEXISTENT.md"
        tasks = parse_plan_md(missing_path)
        assert tasks == []

    def test_checked_items_ignored(self, temp_dir):
        """Test that checked items are ignored."""
        path = temp_dir / "PLAN.md"
        path.write_text("""# Plan

- [x] Completed task 1
- [x] Completed task 2
- [ ] Unchecked task
""")
        tasks = parse_plan_md(path)

        assert len(tasks) == 1
        assert tasks[0]["title"] == "Unchecked task"

    def test_unicode_emoji_in_task_title(self, temp_dir):
        """Test that Unicode/emoji in task titles are handled correctly."""
        path = temp_dir / "PLAN.md"
        path.write_text("""# Plan

- [ ] Add rocket launch feature
- [ ] Test  handling
""")
        tasks = parse_plan_md(path)

        assert len(tasks) == 2
        assert "rocket" in tasks[0]["title"]

    def test_special_characters_in_task_title(self, temp_dir):
        """Test that special characters in task titles are handled correctly."""
        path = temp_dir / "PLAN.md"
        path.write_text("""# Plan

- [ ] Support C++ & C# languages
- [ ] Handle regex like .*\\.py$
- [ ] Parse URLs like https://example.com/path?query=1&other=2
""")
        tasks = parse_plan_md(path)

        assert len(tasks) == 3
        assert "C++ & C#" in tasks[0]["title"]
        assert "regex" in tasks[1]["title"]
        assert "https://" in tasks[2]["title"]

    def test_empty_checkbox_with_extra_spaces(self, temp_dir):
        """Test that checkbox with various spacing is handled correctly."""
        path = temp_dir / "PLAN.md"
        path.write_text("""# Plan

- [  ] Extra space in checkbox
-  [ ] Extra space before checkbox
- [ ]  Extra space after checkbox
""")
        tasks = parse_plan_md(path)

        # The regex pattern r"^-\s+\[\s*\]\s+(.+)$" is lenient with spaces:
        # - \s+ after dash allows multiple spaces
        # - \s* inside brackets allows extra spaces
        # - \s+ after ] allows multiple spaces
        # All three variations match the pattern
        assert len(tasks) == 3
        titles = [t["title"] for t in tasks]
        assert "Extra space in checkbox" in titles
        assert "Extra space before checkbox" in titles
        assert "Extra space after checkbox" in titles

    def test_nested_list_items(self, temp_dir):
        """Test nested unchecked items are also captured."""
        path = temp_dir / "PLAN.md"
        path.write_text("""# Plan

- [ ] Top level task
  - [ ] Nested task 1
    - [ ] Deeply nested task
""")
        tasks = parse_plan_md(path)

        # All unchecked items should be captured (they get stripped)
        assert len(tasks) == 3


# ============================================================================
# Tests for parse_claude_md
# ============================================================================


class TestParseClaudeMd:
    """Tests for the parse_claude_md function."""

    def test_typical_content_returns_empty_list(self, temp_dir):
        """Test that typical CLAUDE.md content returns no tasks."""
        path = temp_dir / "CLAUDE.md"
        path.write_text("""# CLAUDE.md

This file provides context to Claude Code.

## Project Overview

A Python-based agent.

## Commands

```bash
./run_agent.sh
```
""")
        tasks = parse_claude_md(path)
        assert tasks == []

    def test_parse_action_items(self, claude_with_action_items):
        """Test parsing action items from CLAUDE.md."""
        tasks = parse_claude_md(claude_with_action_items)

        assert len(tasks) == 2
        assert tasks[0]["source"] == "CLAUDE.md"

    def test_empty_file_returns_empty_list(self, empty_claude_md):
        """Test that empty file returns empty list."""
        tasks = parse_claude_md(empty_claude_md)
        assert tasks == []

    def test_whitespace_only_file_returns_empty_list(self, temp_dir):
        """Test that file with only whitespace returns empty list."""
        path = temp_dir / "CLAUDE.md"
        path.write_text("   \n\t\n   \n\n   ")
        tasks = parse_claude_md(path)
        assert tasks == []

    def test_missing_file_returns_empty_list(self, temp_dir):
        """Test that missing file returns empty list, not crash."""
        missing_path = temp_dir / "NONEXISTENT.md"
        tasks = parse_claude_md(missing_path)
        assert tasks == []

    def test_todo_pattern_case_insensitive(self, temp_dir):
        """Test that TODO: pattern is case insensitive."""
        path = temp_dir / "CLAUDE.md"
        path.write_text("""# CLAUDE.md

TODO: Uppercase todo
todo: Lowercase todo
Todo: Mixed case todo
""")
        tasks = parse_claude_md(path)

        assert len(tasks) == 3

    def test_unchecked_items_parsed(self, temp_dir):
        """Test that unchecked items are parsed."""
        path = temp_dir / "CLAUDE.md"
        path.write_text("""# CLAUDE.md

## Action Items

- [ ] First action item
- [x] Completed item (should be ignored)
- [ ] Second action item
""")
        tasks = parse_claude_md(path)

        assert len(tasks) == 2
        assert tasks[0]["title"] == "First action item"
        assert tasks[1]["title"] == "Second action item"

    def test_unicode_emoji_in_task_title(self, temp_dir):
        """Test that Unicode/emoji in task titles are handled correctly."""
        path = temp_dir / "CLAUDE.md"
        path.write_text("""# CLAUDE.md

- [ ] Add  feature
TODO: Update  documentation
""")
        tasks = parse_claude_md(path)

        assert len(tasks) == 2

    def test_special_characters_in_task_title(self, temp_dir):
        """Test that special characters in task titles are handled correctly."""
        path = temp_dir / "CLAUDE.md"
        path.write_text("""# CLAUDE.md

- [ ] Support C++ & C# languages
TODO: Handle paths with "quotes" and 'apostrophes'
""")
        tasks = parse_claude_md(path)

        assert len(tasks) == 2
        assert "C++ & C#" in tasks[0]["title"]
        assert "quotes" in tasks[1]["title"]


# ============================================================================
# Tests for get_pending_tasks
# ============================================================================


class TestGetPendingTasks:
    """Tests for the get_pending_tasks function."""

    def test_combines_all_sources(self, temp_dir):
        """Test that tasks from all sources are combined."""
        (temp_dir / "TODO.md").write_text("""# TODO

## Backlog

### [HIGH] @feature - Feature A
""")
        (temp_dir / "PLAN.md").write_text("""# Plan

- [ ] Plan item B
""")
        (temp_dir / "CLAUDE.md").write_text("""# Claude

TODO: Claude item C
""")
        tasks = get_pending_tasks(temp_dir)

        assert len(tasks) == 3
        sources = {t["source"] for t in tasks}
        assert sources == {"TODO.md", "PLAN.md", "CLAUDE.md"}

    def test_sorted_by_priority(self, temp_dir):
        """Test that tasks are sorted by priority (HIGH > MED > LOW > None)."""
        (temp_dir / "TODO.md").write_text("""# TODO

## Backlog

### [LOW] @test - Low task
### [HIGH] @feature - High task
### [MED] @config - Med task
""")
        (temp_dir / "PLAN.md").write_text("""# Plan

- [ ] No priority task
""")
        (temp_dir / "CLAUDE.md").write_text("")

        tasks = get_pending_tasks(temp_dir)

        assert len(tasks) == 4
        assert tasks[0]["priority"] == "HIGH"
        assert tasks[1]["priority"] == "MED"
        assert tasks[2]["priority"] == "LOW"
        assert tasks[3]["priority"] is None

    def test_empty_directory_returns_empty_list(self, temp_dir):
        """Test that empty directory returns empty list."""
        tasks = get_pending_tasks(temp_dir)
        assert tasks == []

    def test_all_files_missing_returns_empty_list(self, temp_dir):
        """Test that missing all files returns empty list."""
        tasks = get_pending_tasks(temp_dir)
        assert tasks == []

    def test_defaults_to_cwd_when_no_base_dir(self):
        """Test that None base_dir defaults to current working directory."""
        with patch("task_detector.Path.cwd") as mock_cwd:
            mock_path = Path("/mock/path")
            mock_cwd.return_value = mock_path
            # This will fail to find files but shouldn't crash
            tasks = get_pending_tasks(None)
            assert tasks == []

    def test_handles_string_path(self, temp_dir):
        """Test that string paths are handled correctly."""
        (temp_dir / "PLAN.md").write_text("- [ ] Task from string path")

        tasks = get_pending_tasks(str(temp_dir))

        assert len(tasks) == 1
        assert tasks[0]["title"] == "Task from string path"


# ============================================================================
# Tests for has_pending_tasks
# ============================================================================


class TestHasPendingTasks:
    """Tests for the has_pending_tasks function."""

    def test_returns_true_when_tasks_exist(self, temp_dir):
        """Test that True is returned when tasks exist."""
        (temp_dir / "PLAN.md").write_text("- [ ] A task")

        assert has_pending_tasks(temp_dir) is True

    def test_returns_false_when_no_tasks(self, temp_dir):
        """Test that False is returned when no tasks exist."""
        assert has_pending_tasks(temp_dir) is False

    def test_returns_false_for_empty_files(self, temp_dir):
        """Test that False is returned for empty files."""
        (temp_dir / "TODO.md").write_text("")
        (temp_dir / "PLAN.md").write_text("")
        (temp_dir / "CLAUDE.md").write_text("")

        assert has_pending_tasks(temp_dir) is False

    def test_returns_false_for_only_completed_tasks(self, temp_dir):
        """Test that False is returned when only completed tasks exist."""
        (temp_dir / "PLAN.md").write_text("""# Plan

- [x] Completed task 1
- [x] Completed task 2
""")
        assert has_pending_tasks(temp_dir) is False

    def test_returns_false_for_missing_directory(self, temp_dir):
        """Test behavior with non-existent directory."""
        missing_dir = temp_dir / "nonexistent"
        # This will try to find files in a non-existent directory
        # The parsers should handle missing files gracefully
        assert has_pending_tasks(missing_dir) is False


# ============================================================================
# Tests for OSError Handling
# ============================================================================


class TestOSErrorHandling:
    """Tests for OSError handling when reading files."""

    def test_parse_todo_md_handles_os_error(self, temp_dir):
        """Test that OSError during file read returns empty list."""
        path = temp_dir / "TODO.md"
        path.write_text("# TODO")

        with patch.object(Path, "read_text", side_effect=OSError("Permission denied")):
            # Need a real path that exists for the exists() check to pass
            tasks = parse_todo_md(path)
            # The mock will raise OSError, function should catch it
            assert tasks == []

    def test_parse_plan_md_handles_os_error(self, temp_dir):
        """Test that OSError during file read returns empty list."""
        path = temp_dir / "PLAN.md"
        path.write_text("# Plan")

        with patch.object(Path, "read_text", side_effect=OSError("Permission denied")):
            tasks = parse_plan_md(path)
            assert tasks == []

    def test_parse_claude_md_handles_os_error(self, temp_dir):
        """Test that OSError during file read returns empty list."""
        path = temp_dir / "CLAUDE.md"
        path.write_text("# Claude")

        with patch.object(Path, "read_text", side_effect=OSError("Permission denied")):
            tasks = parse_claude_md(path)
            assert tasks == []


# ============================================================================
# Tests for Module Import
# ============================================================================


class TestModuleImport:
    """Tests for module import and exports."""

    def test_module_imports_correctly(self):
        """Test that the task_detector module imports without errors."""
        import task_detector

        assert hasattr(task_detector, "parse_todo_md")
        assert hasattr(task_detector, "parse_plan_md")
        assert hasattr(task_detector, "parse_claude_md")
        assert hasattr(task_detector, "get_pending_tasks")
        assert hasattr(task_detector, "has_pending_tasks")

    def test_functions_are_callable(self):
        """Test that all exported functions are callable."""
        assert callable(parse_todo_md)
        assert callable(parse_plan_md)
        assert callable(parse_claude_md)
        assert callable(get_pending_tasks)
        assert callable(has_pending_tasks)
