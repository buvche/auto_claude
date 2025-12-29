# Project Plan

## Overview

Build a continuous Claude agent that monitors a codebase for file changes, analyzes them for errors/issues, and proposes fixes with user approval before applying.

## Architecture

### System Design

```
┌─────────────────────────────────────────────────────────────────────┐
│                         auto_claude                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────┐     ┌───────────────────────────────────────┐ │
│  │     Watchdog     │────▶│         Claude Code SDK               │ │
│  │  File Observer   │     │                                       │ │
│  └──────────────────┘     │  1. Read changed files                │ │
│           │               │  2. Analyze for issues                │ │
│           ▼               │  3. Propose fixes                     │ │
│  ┌──────────────────┐     │  4. Apply with approval               │ │
│  │  ChangeTracker   │     └───────────────────────────────────────┘ │
│  │  (Debouncing)    │                    │                          │
│  └──────────────────┘                    ▼                          │
│                           ┌───────────────────────────────────────┐ │
│                           │    User Approval Prompt [y/n]         │ │
│                           └───────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────┤
│                         GitHub Actions                               │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────────┐ │
│  │   CI/CD      │   │  Scheduler   │   │    Envision Task         │ │
│  │  (ci.yml)    │   │  (hourly)    │──▶│  (codebase analysis)     │ │
│  └──────────────┘   └──────────────┘   └──────────────────────────┘ │
│         │                  │                       │                │
│         ▼                  ▼                       ▼                │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────────┐ │
│  │  Tests (67)  │   │ Task Detect  │   │  Improvement Proposals   │ │
│  │  Lint, Type  │   │   (idle?)    │   │  + Usage Tracking        │ │
│  └──────────────┘   └──────────────┘   └──────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### Technology Stack

- **Language**: Python 3.10+
- **AI SDK**: `claude-code-sdk` (official Claude Code SDK)
- **File Monitoring**: `watchdog` library
- **Async Runtime**: `asyncio`
- **CI/CD**: GitHub Actions
- **Testing**: pytest, ruff, mypy

### Components

| Component | File | Purpose |
|-----------|------|---------|
| FileChangeHandler | agent.py | Captures file system events |
| ChangeTracker | agent.py | Debounces rapid changes |
| analyze_changes() | agent.py | Sends files to Claude for analysis |
| apply_fixes() | agent.py | Applies approved fixes via Claude |
| extract_text_from_message() | agent.py | Helper for SDK message parsing |
| monitor_loop() | agent.py | Main async event loop |
| EnvisionResult | envision.py | Improvement analysis results |
| UsageStats | envision.py | API usage tracking |
| task_detector | task_detector.py | Detects pending tasks in markdown |

## Phases

### Phase 1: Foundation (Completed)

- [x] Set up project structure
- [x] Configure Python virtual environment
- [x] Install dependencies (claude-code-sdk, watchdog)
- [x] Create documentation files

### Phase 2: Core Development (Completed)

- [x] Implement file watcher with watchdog
- [x] Implement change debouncing
- [x] Integrate Claude Code SDK for analysis
- [x] Add user approval flow
- [x] Create runner script

### Phase 3: CI/CD & Testing (Completed)

- [x] Set up GitHub Actions CI pipeline
- [x] Configure Dependabot for dependency updates
- [x] Add pre-commit hooks configuration
- [x] Create issue and PR templates
- [x] Write unit tests (67 tests total)
- [x] Add ruff linting and mypy type checking

### Phase 4: Automation (Completed)

- [x] Implement envision task (codebase analysis)
- [x] Create task detector for markdown files
- [x] Add hourly scheduler workflow
- [x] Implement API usage tracking
- [x] Add GitHub Actions step summary output

### Phase 5: Enhancements (Future)

- [ ] Add configuration file support (YAML/JSON)
- [ ] Implement logging to file
- [ ] Add systemd service for daemon mode
- [ ] Support multiple watch directories
- [ ] Add Slack/Discord notifications

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| Python over TypeScript | Simpler setup, better async support for file watching |
| Watchdog library | Mature, cross-platform file monitoring |
| Semi-auto approval | Balance between automation and safety |
| Debouncing (2s) | Prevent redundant analysis during rapid edits |
| Read-only for analysis | Only use Edit tools after explicit approval |
| Hourly scheduler | Balance between responsiveness and API costs |
| Task detection before envision | Avoid running envision when work is available |

## Approval Flow

1. File change detected by watchdog
2. Change queued in ChangeTracker with timestamp
3. After 2s debounce, changes sent to Claude
4. Claude analyzes using read-only tools (Read, Glob, Grep)
5. If issues found → display proposed fix
6. User prompted: `Apply this fix? [y/n]`
7. If approved → Claude applies fix using Edit tools
8. Continue monitoring

## Envision Flow

1. Scheduler runs every hour
2. task_detector checks TODO.md, PLAN.md, CLAUDE.md
3. If pending tasks exist → skip envision
4. If no tasks → trigger envision workflow
5. envision.py analyzes codebase with Claude
6. Proposes improvements (code quality, tests, docs, bugs)
7. Reports usage stats and estimated cost
8. Writes summary to GitHub Actions

## Cost Estimation

- **Envision run**: ~$0.22 per run (based on Sonnet 3.5 pricing)
- **Hourly schedule**: $0-2.64/12h (depends on pending tasks)
- **CI runs**: Minimal (no Claude API calls)
