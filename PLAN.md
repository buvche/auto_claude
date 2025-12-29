# Project Plan

## Overview

Build a continuous Claude agent that monitors a codebase for file changes, analyzes them for errors/issues, and proposes fixes with user approval before applying.

## Architecture

### System Design

```
┌─────────────────────────────────────────────────────────────┐
│                       agent.py                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐     ┌───────────────────────────────┐ │
│  │     Watchdog     │────▶│      Claude Code SDK          │ │
│  │  File Observer   │     │                               │ │
│  └──────────────────┘     │  1. Read changed files        │ │
│           │               │  2. Analyze for issues        │ │
│           ▼               │  3. Propose fixes             │ │
│  ┌──────────────────┐     │  4. Apply with approval       │ │
│  │  ChangeTracker   │     └───────────────────────────────┘ │
│  │  (Debouncing)    │                    │                  │
│  └──────────────────┘                    ▼                  │
│                           ┌───────────────────────────────┐ │
│                           │    User Approval Prompt       │ │
│                           │    [y/n] in terminal          │ │
│                           └───────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack

- **Language**: Python 3.10+
- **AI SDK**: `claude-code-sdk` (official Claude Code SDK)
- **File Monitoring**: `watchdog` library
- **Async Runtime**: `asyncio`

### Components

| Component | File | Purpose |
|-----------|------|---------|
| FileChangeHandler | agent.py | Captures file system events |
| ChangeTracker | agent.py | Debounces rapid changes |
| analyze_changes() | agent.py | Sends files to Claude for analysis |
| apply_fixes() | agent.py | Applies approved fixes via Claude |
| monitor_loop() | agent.py | Main async event loop |

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

### Phase 3: Enhancements (Future)

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

## Approval Flow

1. File change detected by watchdog
2. Change queued in ChangeTracker with timestamp
3. After 2s debounce, changes sent to Claude
4. Claude analyzes using read-only tools (Read, Glob, Grep)
5. If issues found → display proposed fix
6. User prompted: `Apply this fix? [y/n]`
7. If approved → Claude applies fix using Edit tools
8. Continue monitoring
