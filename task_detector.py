"""
Task Detector Module

Scans TODO.md, PLAN.md, and CLAUDE.md for pending tasks and returns them
in a structured format for automated task processing.
"""

import re
from pathlib import Path


def parse_todo_md(path: Path) -> list[dict]:
    """
    Parse TODO.md for uncompleted items in Backlog/In Progress sections.

    Looks for:
    - Items in "## In Progress" section (if not "_No tasks currently in progress_")
    - Items in "## Backlog" section with task headers like "### [PRIORITY] @type - Title"

    Args:
        path: Path to the TODO.md file

    Returns:
        List of task dicts with source, title, priority, and type
    """
    if not path.exists():
        return []

    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return []

    tasks: list[dict] = []
    lines = content.split("\n")

    current_section = None
    in_progress_placeholder = "_No tasks currently in progress_"

    # Regex for backlog task headers: ### [HIGH] @feature - Title
    backlog_task_pattern = re.compile(
        r"^###\s+\[(\w+)\]\s+(@\w+)\s+-\s+(.+)$"
    )

    for line in lines:
        stripped = line.strip()

        # Track current section
        if stripped.startswith("## "):
            section_name = stripped[3:].strip()
            if section_name == "In Progress":
                current_section = "in_progress"
            elif section_name == "Backlog":
                current_section = "backlog"
            elif section_name == "Completed":
                current_section = "completed"
            else:
                current_section = section_name.lower()
            continue

        # Skip if we're in completed section
        if current_section == "completed":
            continue

        # Check for backlog tasks (### [PRIORITY] @type - Title)
        if current_section == "backlog":
            match = backlog_task_pattern.match(stripped)
            if match:
                priority, task_type, title = match.groups()
                tasks.append({
                    "source": "TODO.md",
                    "title": title.strip(),
                    "priority": priority.upper(),
                    "type": task_type,
                })
                continue

        # Check for in-progress tasks
        if current_section == "in_progress":
            # Skip the placeholder text
            if in_progress_placeholder in stripped:
                continue

            # Look for task headers in in_progress section
            match = backlog_task_pattern.match(stripped)
            if match:
                priority, task_type, title = match.groups()
                tasks.append({
                    "source": "TODO.md",
                    "title": title.strip(),
                    "priority": priority.upper(),
                    "type": task_type,
                })
                continue

            # Also check for simpler formats like "- [x] Task name" or "### Task name"
            if stripped.startswith("### ") and not stripped.startswith("### ["):
                # Simple header without priority/type
                title = stripped[4:].strip()
                if title:
                    tasks.append({
                        "source": "TODO.md",
                        "title": title,
                        "priority": None,
                        "type": None,
                    })

    return tasks


def parse_plan_md(path: Path) -> list[dict]:
    """
    Parse PLAN.md for unchecked items (- [ ]) in any section.

    Looks for lines matching the pattern "- [ ] Task description"

    Args:
        path: Path to the PLAN.md file

    Returns:
        List of task dicts with source, title, priority (None), and type (None)
    """
    if not path.exists():
        return []

    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return []

    tasks: list[dict] = []
    lines = content.split("\n")

    # Regex for unchecked items: - [ ] Task description
    unchecked_pattern = re.compile(r"^-\s+\[\s*\]\s+(.+)$")

    for line in lines:
        stripped = line.strip()

        # Check for unchecked items
        match = unchecked_pattern.match(stripped)
        if match:
            title = match.group(1).strip()
            tasks.append({
                "source": "PLAN.md",
                "title": title,
                "priority": None,
                "type": None,
            })

    return tasks


def parse_claude_md(path: Path) -> list[dict]:
    """
    Check CLAUDE.md for any action items.

    CLAUDE.md typically contains project context and guidelines,
    not actionable tasks. This function returns an empty list
    unless specific action item patterns are found.

    Args:
        path: Path to the CLAUDE.md file

    Returns:
        Empty list (CLAUDE.md typically has no tasks)
    """
    if not path.exists():
        return []

    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return []

    tasks: list[dict] = []
    lines = content.split("\n")

    # Look for explicit action items (uncommon in CLAUDE.md)
    # Pattern: - [ ] Action item or TODO: Action item
    unchecked_pattern = re.compile(r"^-\s+\[\s*\]\s+(.+)$")
    todo_pattern = re.compile(r"^TODO:\s+(.+)$", re.IGNORECASE)

    for line in lines:
        stripped = line.strip()

        # Check for unchecked items
        match = unchecked_pattern.match(stripped)
        if match:
            title = match.group(1).strip()
            tasks.append({
                "source": "CLAUDE.md",
                "title": title,
                "priority": None,
                "type": None,
            })
            continue

        # Check for TODO: items
        match = todo_pattern.match(stripped)
        if match:
            title = match.group(1).strip()
            tasks.append({
                "source": "CLAUDE.md",
                "title": title,
                "priority": None,
                "type": None,
            })

    return tasks


def get_pending_tasks(base_dir: Path | None = None) -> list[dict]:
    """
    Get all pending tasks from TODO.md, PLAN.md, and CLAUDE.md.

    Args:
        base_dir: Base directory containing the markdown files.
                  Defaults to current working directory.

    Returns:
        List of task dicts, sorted by priority (HIGH > MED > LOW > None)
    """
    if base_dir is None:
        base_dir = Path.cwd()

    base_dir = Path(base_dir)

    tasks: list[dict] = []

    # Parse all source files
    tasks.extend(parse_todo_md(base_dir / "TODO.md"))
    tasks.extend(parse_plan_md(base_dir / "PLAN.md"))
    tasks.extend(parse_claude_md(base_dir / "CLAUDE.md"))

    # Sort by priority: HIGH > MED > LOW > None
    priority_order = {"HIGH": 0, "MED": 1, "LOW": 2, None: 3}
    tasks.sort(key=lambda t: priority_order.get(t["priority"], 3))

    return tasks


def has_pending_tasks(base_dir: Path | None = None) -> bool:
    """
    Check if there are any pending tasks in TODO.md, PLAN.md, or CLAUDE.md.

    Args:
        base_dir: Base directory containing the markdown files.
                  Defaults to current working directory.

    Returns:
        True if there are pending tasks, False otherwise
    """
    return len(get_pending_tasks(base_dir)) > 0


if __name__ == "__main__":
    # Run tests when executed directly
    import tempfile

    print("=" * 60)
    print("Task Detector - Unit Tests")
    print("=" * 60)

    # Test 1: parse_todo_md with sample content
    print("\n[Test 1] parse_todo_md - Backlog tasks")
    with tempfile.TemporaryDirectory() as tmpdir:
        todo_path = Path(tmpdir) / "TODO.md"
        todo_path.write_text("""# TODO

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

        tasks = parse_todo_md(todo_path)
        assert len(tasks) == 3, f"Expected 3 tasks, got {len(tasks)}"
        assert tasks[0]["title"] == "Add configuration file support"
        assert tasks[0]["priority"] == "HIGH"
        assert tasks[0]["type"] == "@config"
        assert tasks[1]["priority"] == "MED"
        assert tasks[2]["priority"] == "LOW"
        print(f"  PASS: Found {len(tasks)} tasks with correct priorities")

    # Test 2: parse_todo_md with in-progress task
    print("\n[Test 2] parse_todo_md - In Progress tasks")
    with tempfile.TemporaryDirectory() as tmpdir:
        todo_path = Path(tmpdir) / "TODO.md"
        todo_path.write_text("""# TODO

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

        tasks = parse_todo_md(todo_path)
        assert len(tasks) == 2, f"Expected 2 tasks, got {len(tasks)}"
        assert tasks[0]["title"] == "Implement file logging"
        assert tasks[0]["priority"] == "HIGH"
        print(f"  PASS: Found in-progress task: '{tasks[0]['title']}'")

    # Test 3: parse_plan_md with unchecked items
    print("\n[Test 3] parse_plan_md - Unchecked items")
    with tempfile.TemporaryDirectory() as tmpdir:
        plan_path = Path(tmpdir) / "PLAN.md"
        plan_path.write_text("""# Project Plan

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

        tasks = parse_plan_md(plan_path)
        assert len(tasks) == 3, f"Expected 3 tasks, got {len(tasks)}"
        assert tasks[0]["title"] == "Add configuration file support"
        assert tasks[0]["source"] == "PLAN.md"
        assert tasks[0]["priority"] is None
        print(f"  PASS: Found {len(tasks)} unchecked items")

    # Test 4: parse_claude_md returns empty for typical content
    print("\n[Test 4] parse_claude_md - No tasks in typical content")
    with tempfile.TemporaryDirectory() as tmpdir:
        claude_path = Path(tmpdir) / "CLAUDE.md"
        claude_path.write_text("""# CLAUDE.md

This file provides context to Claude Code.

## Project Overview

A Python-based agent.

## Commands

```bash
./run_agent.sh
```
""")

        tasks = parse_claude_md(claude_path)
        assert len(tasks) == 0, f"Expected 0 tasks, got {len(tasks)}"
        print("  PASS: No tasks found (as expected)")

    # Test 5: parse_claude_md with action items
    print("\n[Test 5] parse_claude_md - With action items")
    with tempfile.TemporaryDirectory() as tmpdir:
        claude_path = Path(tmpdir) / "CLAUDE.md"
        claude_path.write_text("""# CLAUDE.md

## Action Items

- [ ] Update documentation
TODO: Add more examples

## Guidelines

Follow the style guide.
""")

        tasks = parse_claude_md(claude_path)
        assert len(tasks) == 2, f"Expected 2 tasks, got {len(tasks)}"
        print(f"  PASS: Found {len(tasks)} action items")

    # Test 6: Missing files handled gracefully
    print("\n[Test 6] Missing files - Graceful handling")
    with tempfile.TemporaryDirectory() as tmpdir:
        missing_path = Path(tmpdir) / "MISSING.md"

        tasks = parse_todo_md(missing_path)
        assert tasks == [], "Expected empty list for missing file"

        tasks = parse_plan_md(missing_path)
        assert tasks == [], "Expected empty list for missing file"

        tasks = parse_claude_md(missing_path)
        assert tasks == [], "Expected empty list for missing file"
        print("  PASS: All parsers return empty list for missing files")

    # Test 7: get_pending_tasks combines all sources
    print("\n[Test 7] get_pending_tasks - Combined results")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        (tmpdir / "TODO.md").write_text("""# TODO

## Backlog

### [HIGH] @feature - Feature A

### [LOW] @test - Test B
""")

        (tmpdir / "PLAN.md").write_text("""# Plan

- [ ] Plan item C
- [x] Done item
""")

        (tmpdir / "CLAUDE.md").write_text("""# Claude

Context only, no tasks.
""")

        tasks = get_pending_tasks(tmpdir)
        assert len(tasks) == 3, f"Expected 3 tasks, got {len(tasks)}"
        # Check sorting: HIGH first
        assert tasks[0]["priority"] == "HIGH"
        assert tasks[1]["priority"] == "LOW"
        assert tasks[2]["priority"] is None  # PLAN.md task
        print(f"  PASS: Combined {len(tasks)} tasks from all sources, sorted by priority")

    # Test 8: has_pending_tasks
    print("\n[Test 8] has_pending_tasks - Boolean check")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Empty directory - no tasks
        assert has_pending_tasks(tmpdir) is False

        # Add a task
        (tmpdir / "PLAN.md").write_text("- [ ] Do something")
        assert has_pending_tasks(tmpdir) is True
        print("  PASS: has_pending_tasks returns correct boolean")

    # Test 9: Run on actual project files
    print("\n[Test 9] Real project files")
    project_dir = Path(__file__).parent
    tasks = get_pending_tasks(project_dir)
    print(f"  Found {len(tasks)} pending tasks in project:")
    for i, task in enumerate(tasks[:5], 1):  # Show first 5
        priority_str = f"[{task['priority']}]" if task['priority'] else "[---]"
        type_str = task['type'] or "---"
        print(f"    {i}. {priority_str} {type_str}: {task['title'][:50]}...")
    if len(tasks) > 5:
        print(f"    ... and {len(tasks) - 5} more")

    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60)
