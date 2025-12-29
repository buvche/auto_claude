#!/usr/bin/env python3
"""
Continuous Claude Agent
Monitors files for changes and proposes fixes with user approval.
"""

import asyncio
import time
from pathlib import Path

from claude_code_sdk import ClaudeCodeOptions, query
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer


def extract_text_from_message(message) -> str:
    """Extract text content from a Claude SDK message.

    Handles both AssistantMessage (with content) and ResultMessage formats.

    Args:
        message: A message object from the Claude SDK query() stream.

    Returns:
        Extracted text content, or empty string if no text found.
    """
    if hasattr(message, "content"):
        if isinstance(message.content, str):
            return message.content
        elif isinstance(message.content, list):
            return "".join(
                block.text for block in message.content if hasattr(block, "text")
            )
    elif hasattr(message, "result") and message.result:
        return str(message.result)
    return ""


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
        """Get changes that have settled (no updates for DEBOUNCE_SECONDS).

        Uses single-pass pop() to atomically collect and remove ready items,
        avoiding potential race conditions from two-phase collect-then-delete.
        """
        async with self.lock:
            now = time.time()
            ready = []
            # Single-pass: identify and remove in one operation per item
            paths_to_remove = [
                path for path, timestamp in self.pending_changes.items()
                if now - timestamp >= DEBOUNCE_SECONDS
            ]
            for path in paths_to_remove:
                self.pending_changes.pop(path, None)  # Atomic remove, ignores if missing
                ready.append(path)
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
        if event.is_directory or self._should_ignore(str(event.src_path)):
            return
        asyncio.run_coroutine_threadsafe(
            self.tracker.add_change(str(event.src_path)),
            self.loop
        )

    def on_created(self, event: FileSystemEvent):
        if event.is_directory or self._should_ignore(str(event.src_path)):
            return
        asyncio.run_coroutine_threadsafe(
            self.tracker.add_change(str(event.src_path)),
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
    """Analyze changed files using Claude and propose fixes.

    Uses Claude SDK with read-only tools (Read, Glob, Grep) to analyze
    the modified files for errors, bugs, or issues. If problems are found,
    prompts the user for approval before applying fixes.

    Args:
        changed_files: List of absolute paths to files that were modified.

    Side Effects:
        - Prints analysis results to stdout
        - Prompts user for input via get_user_approval() if issues found
        - Calls apply_fixes() if user approves the suggested changes

    Note:
        Analysis is read-only; no modifications are made until user approval.
    """
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

    try:
        async for message in query(prompt=prompt, options=options):
            result_text += extract_text_from_message(message)
    except Exception as e:
        print(f"\n⚠️ Analysis failed: {e}. Continuing to monitor...")
        return

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
    """Apply fixes to files based on previous analysis.

    Uses Claude SDK with edit tools (Read, Edit, Write, Glob, Grep) to
    implement the fixes identified during analysis.

    Args:
        changed_files: List of absolute paths to files needing fixes.
        analysis: The analysis text from analyze_changes() describing
            the issues found and proposed solutions.

    Side Effects:
        - Modifies files on disk via Claude's Edit/Write tools
        - Streams progress output to stdout in real-time

    Note:
        Should only be called after user approval in analyze_changes().
    """
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

    try:
        async for message in query(prompt=prompt, options=options):
            text = extract_text_from_message(message)
            if text:
                print(text, end="", flush=True)
    except Exception as e:
        print(f"\n⚠️ Applying fixes failed: {e}. Continuing to monitor...")
        return

    print("\n✓ Fixes applied!")


async def monitor_loop(tracker: ChangeTracker) -> None:
    """Main monitoring loop that processes file changes.

    Continuously polls the ChangeTracker for debounced file changes
    and triggers analysis when files are ready. Runs indefinitely
    until interrupted.

    Args:
        tracker: ChangeTracker instance collecting file system events.

    Side Effects:
        - Prints monitoring status to stdout
        - Calls analyze_changes() for each batch of changed files
        - Sleeps 0.5s between polling cycles to reduce CPU usage

    Note:
        Only processes files that still exist (handles deletions gracefully).
    """
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
