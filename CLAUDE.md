# CLAUDE.md

This file provides context to Claude Code when working with this project.

## Project Overview

A Python-based continuous agent that monitors files for changes and uses Claude to analyze code for errors/issues. It proposes fixes and waits for user approval before applying them.

## Agent Specializations

When working on tasks, identify your role:

| Agent | Role | Focus Areas |
|-------|------|-------------|
| `@feature` | Feature development | agent.py, new functionality |
| `@config` | Configuration | config.yaml, settings, environment |
| `@infra` | Infrastructure | systemd, deployment, scripts |
| `@docs` | Documentation | README.md, PLAN.md, comments |
| `@test` | Testing | tests/, pytest, verification |
| `@refactor` | Code quality | Structure improvements, no behavior change |

## Commands

```bash
# Run the agent
./run_agent.sh

# Run manually
source venv/bin/activate
python agent.py

# Install dependencies
pip install claude-code-sdk watchdog

# Verify syntax
python -m py_compile agent.py

# Check imports
python -c "import agent; print('OK')"
```

## Verification Checklist

Before marking any task complete:

```bash
# 1. Syntax check
python -m py_compile agent.py

# 2. Import check
source venv/bin/activate && python -c "import agent"

# 3. Start test (should show banner, Ctrl+C to exit)
timeout 5 ./run_agent.sh || true

# 4. Run task-specific verify steps from TODO.md
```

## Architecture

```
auto_claude/
├── agent.py        # Main agent (file watcher + Claude SDK)
├── run_agent.sh    # Runner script (activates venv)
├── config.yaml     # User configuration (optional, future)
├── venv/           # Python virtual environment
├── README.md       # User documentation
├── PLAN.md         # Architecture and roadmap
├── TODO.md         # Task tracking (START HERE)
└── CLAUDE.md       # This file
```

## Key Components in agent.py

| Component | Line | Purpose |
|-----------|------|---------|
| `WATCH_DIR` | ~15 | Directory to monitor |
| `IGNORE_PATTERNS` | ~16 | Paths to skip |
| `DEBOUNCE_SECONDS` | ~17 | Wait time before processing |
| `ChangeTracker` | ~20 | Debounces rapid file changes |
| `FileChangeHandler` | ~40 | Watchdog event handler |
| `analyze_changes()` | ~70 | Read-only analysis via Claude |
| `apply_fixes()` | ~100 | Apply fixes after approval |
| `monitor_loop()` | ~120 | Main async event loop |
| `main()` | ~140 | Entry point, sets up watcher |

## Code Style

- Python 3.10+ with type hints
- Async/await for concurrent operations
- Classes for stateful components
- Functions for stateless operations
- No external formatting tools required

## Development Guidelines

1. **Read TODO.md first** - Check acceptance criteria before starting
2. **Keep analysis read-only** - Only Read, Glob, Grep during analysis phase
3. **Edit only after approval** - Use Edit/Write tools only when user confirms
4. **Maintain debouncing** - Don't remove or reduce debounce delay
5. **Test before completing** - Run verify steps from TODO.md
6. **Update docs** - If you change behavior, update README/CLAUDE.md

## Common Patterns

### Adding a new config option

```python
# 1. Add to load_config() with default
config = {
    "new_option": data.get("new_option", "default_value"),
}

# 2. Use in relevant function
if config["new_option"]:
    do_something()
```

### Adding a new async operation

```python
async def new_operation():
    # Use async with for I/O
    async with aiofiles.open(path) as f:
        content = await f.read()
```

## What NOT to Do

- Don't remove the debounce delay (causes API spam)
- Don't auto-approve changes (defeats safety purpose)
- Don't watch venv/ or .git/ (causes loops)
- Don't block the async loop with sync I/O
- Don't hardcode paths (use config or Path)

## Task Workflow

1. Read TODO.md → find highest priority unclaimed task
2. Read acceptance criteria and verify steps
3. Implement the feature
4. Run verification commands
5. Update TODO.md (move to Completed)
6. Update README.md if user-facing changes
