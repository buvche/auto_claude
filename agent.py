#!/usr/bin/env python3
"""
Continuous Claude Agent
Monitors files for changes and proposes fixes with user approval.
"""

import asyncio
import os
import sys
import time
from pathlib import Path
from typing import Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from claude_code_sdk import query, ClaudeCodeOptions


# Configuration
WATCH_DIR = Path(__file__).parent.resolve()
IGNORE_PATTERNS = {".git", "__pycache__", "venv", ".venv", "node_modules", ".pyc", ".pyo"}
DEBOUNCE_SECONDS = 2.0  # Wait for rapid changes to settle


class ChangeTracker:
    """Tracks file changes with debouncing."""

    def __init__(self):
        self.pending_changes: dict[str, float] = {}
        self.lock = asyncio.Lock()

    async def add_change(self, path: str):
        async with self.lock:
            self.pending_changes[path] = time.time()

    async def get_ready_changes(self) -> list[str]:
        """Get changes that have settled (no updates for DEBOUNCE_SECONDS)."""
        async with self.lock:
            now = time.time()
            ready = [
                path for path, timestamp in self.pending_changes.items()
                if now - timestamp >= DEBOUNCE_SECONDS
            ]
            for path in ready:
                del self.pending_changes[path]
            return ready


class FileChangeHandler(FileSystemEventHandler):
    """Handles file system events."""

    def __init__(self, tracker: ChangeTracker, loop: asyncio.AbstractEventLoop):
        self.tracker = tracker
        self.loop = loop

    def _should_ignore(self, path: str) -> bool:
        """Check if path should be ignored."""
        path_parts = Path(path).parts
        return any(pattern in path_parts or path.endswith(pattern)
                   for pattern in IGNORE_PATTERNS)

    def on_modified(self, event: FileSystemEvent):
        if event.is_directory or self._should_ignore(event.src_path):
            return
        asyncio.run_coroutine_threadsafe(
            self.tracker.add_change(event.src_path),
            self.loop
        )

    def on_created(self, event: FileSystemEvent):
        if event.is_directory or self._should_ignore(event.src_path):
            return
        asyncio.run_coroutine_threadsafe(
            self.tracker.add_change(event.src_path),
            self.loop
        )


def get_user_approval(prompt: str) -> bool:
    """Ask user for approval via terminal."""
    while True:
        response = input(f"\n{prompt} [y/n]: ").strip().lower()
        if response in ("y", "yes"):
            return True
        if response in ("n", "no"):
            return False
        print("Please enter 'y' or 'n'")


async def analyze_changes(changed_files: list[str]) -> None:
    """Use Claude to analyze changes and propose fixes."""

    files_list = "\n".join(f"  - {f}" for f in changed_files)
    prompt = f"""The following files were just modified:
{files_list}

Please:
1. Read these files to understand the changes
2. Check for any errors, bugs, or issues (syntax errors, logic errors, security issues, etc.)
3. If you find issues, describe them clearly and propose fixes
4. Wait for my approval before making any changes

If everything looks good, just say so."""

    print(f"\n{'='*60}")
    print("🔍 Analyzing changes...")
    print(f"{'='*60}")

    options = ClaudeCodeOptions(
        allowed_tools=["Read", "Glob", "Grep"],  # Read-only for analysis
        cwd=str(WATCH_DIR),
    )

    result_text = ""

    async for message in query(prompt=prompt, options=options):
        if hasattr(message, "content"):
            # AssistantMessage with content
            if isinstance(message.content, str):
                result_text += message.content
            elif isinstance(message.content, list):
                for block in message.content:
                    if hasattr(block, "text"):
                        result_text += block.text
        elif hasattr(message, "result"):
            # ResultMessage
            result_text = message.result

    print(f"\n{result_text}")

    # Check if fixes are needed
    if any(keyword in result_text.lower() for keyword in ["issue", "error", "bug", "fix", "problem", "should"]):
        if get_user_approval("Would you like me to apply the suggested fixes?"):
            await apply_fixes(changed_files, result_text)
        else:
            print("✓ Skipping fixes, continuing to monitor...")
    else:
        print("✓ No issues found, continuing to monitor...")


async def apply_fixes(changed_files: list[str], analysis: str) -> None:
    """Apply fixes with user approval for each change."""

    files_list = "\n".join(f"  - {f}" for f in changed_files)
    prompt = f"""Based on your previous analysis:
{analysis}

Please apply the fixes to these files:
{files_list}

Make the necessary edits to fix the issues you identified."""

    print(f"\n{'='*60}")
    print("🔧 Applying fixes...")
    print(f"{'='*60}")

    options = ClaudeCodeOptions(
        allowed_tools=["Read", "Edit", "Write", "Glob", "Grep"],
        cwd=str(WATCH_DIR),
    )

    async for message in query(prompt=prompt, options=options):
        if hasattr(message, "content"):
            if isinstance(message.content, str):
                print(message.content, end="", flush=True)
            elif isinstance(message.content, list):
                for block in message.content:
                    if hasattr(block, "text"):
                        print(block.text, end="", flush=True)
        elif hasattr(message, "result"):
            print(f"\n{message.result}")

    print("\n✓ Fixes applied!")


async def monitor_loop(tracker: ChangeTracker) -> None:
    """Main monitoring loop."""
    print(f"\n{'='*60}")
    print(f"👁️  Monitoring: {WATCH_DIR}")
    print(f"{'='*60}")
    print("Watching for file changes... (Ctrl+C to stop)\n")

    while True:
        ready_changes = await tracker.get_ready_changes()

        if ready_changes:
            # Filter to only existing files
            existing_files = [f for f in ready_changes if Path(f).exists()]
            if existing_files:
                await analyze_changes(existing_files)

        await asyncio.sleep(0.5)


async def main():
    """Main entry point."""
    print("""
╔═══════════════════════════════════════════════════════════╗
║           Claude Continuous Agent                         ║
║           Semi-Auto Mode (Approval Required)              ║
╚═══════════════════════════════════════════════════════════╝
    """)

    # Set up change tracker
    tracker = ChangeTracker()
    loop = asyncio.get_event_loop()

    # Set up file watcher
    event_handler = FileChangeHandler(tracker, loop)
    observer = Observer()
    observer.schedule(event_handler, str(WATCH_DIR), recursive=True)
    observer.start()

    try:
        await monitor_loop(tracker)
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down agent...")
    finally:
        observer.stop()
        observer.join()


if __name__ == "__main__":
    asyncio.run(main())
