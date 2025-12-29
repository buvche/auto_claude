# CLAUDE.md

This file provides context to Claude Code when working with this project.

## Project Overview

A Python-based continuous agent that monitors files for changes and uses Claude to analyze code for errors/issues. It proposes fixes and waits for user approval before applying them. Includes automated codebase improvement analysis via GitHub Actions.

## Agent Specializations

When working on tasks, identify your role:

| Agent | Role | Focus Areas |
|-------|------|-------------|
| `@feature` | Feature development | agent.py, envision.py, new functionality |
| `@config` | Configuration | config.yaml, settings, environment |
| `@infra` | Infrastructure | GitHub Actions, deployment, scripts |
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

# Run envision analysis
python envision.py --max-agents 3 --max-time 600

# Check for pending tasks
python task_detector.py

# Install dependencies
pip install -r requirements.txt

# Development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/ -v

# Lint
ruff check .

# Type check
mypy agent.py --ignore-missing-imports
```

## Verification Checklist

Before marking any task complete:

```bash
# 1. Syntax check
python -m py_compile agent.py envision.py task_detector.py

# 2. Import check
source venv/bin/activate && python -c "import agent; import envision; import task_detector"

# 3. Run tests
pytest tests/ -v

# 4. Lint check
ruff check .

# 5. Start test (should show banner, Ctrl+C to exit)
timeout 5 ./run_agent.sh || true
```

## Architecture

```
auto_claude/
├── agent.py              # Main agent (file watcher + Claude SDK)
├── envision.py           # Codebase improvement analyzer
├── task_detector.py      # Detects pending tasks in markdown
├── run_agent.sh          # Runner script (activates venv)
├── requirements.txt      # Production dependencies
├── requirements-dev.txt  # Dev dependencies (pytest, ruff, mypy)
├── pyproject.toml        # Project config (pytest, ruff settings)
├── tests/
│   ├── test_agent.py     # Tests for agent.py (19 tests)
│   └── test_task_detector.py  # Tests for task_detector.py (48 tests)
├── .github/
│   ├── workflows/
│   │   ├── ci.yml        # CI: tests, lint, type check
│   │   ├── envision.yml  # Envision: codebase analysis
│   │   └── scheduler.yml # Scheduler: hourly task check
│   ├── dependabot.yml
│   └── ISSUE_TEMPLATE/
├── README.md             # User documentation
├── PLAN.md               # Architecture and roadmap
├── TODO.md               # Task tracking (START HERE)
└── CLAUDE.md             # This file
```

## Key Components

### agent.py

| Component | Line | Purpose |
|-----------|------|---------|
| `extract_text_from_message()` | ~16 | Helper for SDK message parsing |
| `WATCH_DIR` | ~40 | Directory to monitor |
| `IGNORE_PATTERNS` | ~41 | Paths to skip |
| `DEBOUNCE_SECONDS` | ~42 | Wait time before processing |
| `ChangeTracker` | ~45 | Debounces rapid file changes |
| `FileChangeHandler` | ~76 | Watchdog event handler |
| `analyze_changes()` | ~106 | Read-only analysis via Claude |
| `apply_fixes()` | ~170 | Apply fixes after approval |
| `monitor_loop()` | ~218 | Main async event loop |

### envision.py

| Component | Purpose |
|-----------|---------|
| `Improvement` | Dataclass for proposed improvements |
| `UsageStats` | Tracks API token usage and costs |
| `EnvisionResult` | Analysis results container |
| `run_analysis()` | Runs Claude analysis with usage tracking |
| `analyze_codebase()` | Main analysis orchestrator |
| `write_github_summary()` | Writes GitHub Actions step summary |

### task_detector.py

| Function | Purpose |
|----------|---------|
| `has_pending_tasks()` | Returns True if tasks exist |
| `get_pending_tasks()` | Returns list of all pending tasks |
| `parse_todo_md()` | Parses TODO.md backlog/in-progress |
| `parse_plan_md()` | Parses PLAN.md unchecked items |
| `parse_claude_md()` | Parses CLAUDE.md action items |

## Code Style

- Python 3.10+ with type hints
- Async/await for concurrent operations
- Classes for stateful components
- Functions for stateless operations
- Dataclasses for structured data
- ruff for linting, mypy for type checking

## Development Guidelines

1. **Read TODO.md first** - Check acceptance criteria before starting
2. **Keep analysis read-only** - Only Read, Glob, Grep during analysis phase
3. **Edit only after approval** - Use Edit/Write tools only when user confirms
4. **Maintain debouncing** - Don't remove or reduce debounce delay
5. **Test before completing** - Run pytest and ruff
6. **Update docs** - If you change behavior, update README/CLAUDE.md

## GitHub Actions Workflows

| Workflow | File | Trigger | Purpose |
|----------|------|---------|---------|
| CI | ci.yml | push/PR | Tests, lint, type check |
| Scheduler | scheduler.yml | hourly | Check tasks, trigger envision |
| Envision | envision.yml | manual/called | Analyze codebase |

**To enable envision**: Add `ANTHROPIC_API_KEY` secret to repository settings.

## What NOT to Do

- Don't remove the debounce delay (causes API spam)
- Don't auto-approve changes (defeats safety purpose)
- Don't watch venv/ or .git/ (causes loops)
- Don't block the async loop with sync I/O
- Don't hardcode paths (use config or Path)
- Don't skip tests before committing

## Task Workflow

1. Read TODO.md → find highest priority unclaimed task
2. Read acceptance criteria and verify steps
3. Implement the feature
4. Run verification commands (pytest, ruff)
5. Update TODO.md (move to Completed)
6. Update README.md if user-facing changes
