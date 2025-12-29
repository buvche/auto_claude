# TODO

## Agent Specializations

Define which agent type should handle each task:

| Agent | Role | Capabilities |
|-------|------|--------------|
| `@feature` | Feature development | Add new functionality, modify agent.py |
| `@config` | Configuration | Config files, environment setup, settings |
| `@infra` | Infrastructure | Systemd, deployment, CI/CD, Docker |
| `@docs` | Documentation | README, PLAN, inline comments |
| `@test` | Testing | Write tests, verify functionality |
| `@refactor` | Code quality | Improve structure without changing behavior |

---

## In Progress

_No tasks currently in progress_

---

## Backlog

### [HIGH] @config - Add configuration file support

**Goal:** Allow users to customize agent behavior without editing code.

**Acceptance Criteria:**
- [ ] Create `config.yaml` in project root with schema:
  ```yaml
  watch_dir: "."
  ignore_patterns: [".git", "venv", "__pycache__"]
  debounce_seconds: 2.0
  log_file: null  # or path like "agent.log"
  ```
- [ ] Add `pyyaml` to dependencies
- [ ] Create `load_config()` function in agent.py
- [ ] Replace hardcoded `WATCH_DIR`, `IGNORE_PATTERNS`, `DEBOUNCE_SECONDS` with config values
- [ ] Fall back to current defaults if config.yaml missing

**Verify:**
```bash
# Create config with custom debounce
echo "debounce_seconds: 5.0" > config.yaml
./run_agent.sh
# Should show "Debounce: 5.0s" or similar in startup output
```

---

### [HIGH] @feature - Implement file logging

**Goal:** Persist agent activity for debugging and audit.

**Acceptance Criteria:**
- [ ] Add `logging` module setup in agent.py
- [ ] Log to both console and file (if configured)
- [ ] Log levels: INFO for normal ops, DEBUG for file changes, ERROR for failures
- [ ] Include timestamps in log format
- [ ] Rotate logs or cap file size (optional)

**Verify:**
```bash
# Set log_file in config.yaml
echo "log_file: agent.log" >> config.yaml
./run_agent.sh &
# Make a file change
touch test.py
# Check log file exists and has entries
cat agent.log | grep "test.py"
```

---

### [MED] @infra - Create systemd service for daemon mode

**Goal:** Run agent as a background service that starts on boot.

**Acceptance Criteria:**
- [ ] Create `claude-agent.service` file for systemd
- [ ] Service should:
  - Run as current user (not root)
  - Restart on failure
  - Use absolute paths
  - Set working directory correctly
- [ ] Add install/uninstall commands to README
- [ ] Create `install-service.sh` helper script

**Verify:**
```bash
./install-service.sh
systemctl --user status claude-agent
# Should show "active (running)"
```

---

### [MED] @feature - Support watching multiple directories

**Goal:** Monitor multiple project directories from single agent instance.

**Acceptance Criteria:**
- [ ] Change `watch_dir` config to `watch_dirs` (list)
- [ ] Backwards compatible: accept string or list
- [ ] Create separate Observer per directory
- [ ] Show which directory a change came from in output

**Verify:**
```yaml
# config.yaml
watch_dirs:
  - /home/user/project1
  - /home/user/project2
```
```bash
./run_agent.sh
# Modify file in project2
# Should see "Change in /home/user/project2: ..."
```

---

### [MED] @feature - Add notification support

**Goal:** Send alerts to external services when issues are found.

**Acceptance Criteria:**
- [ ] Support webhook URLs in config (Slack/Discord compatible)
- [ ] Send notification when issues detected (before approval prompt)
- [ ] Include: file name, issue summary, timestamp
- [ ] Make notifications optional (disabled by default)
- [ ] Don't block main loop on notification failures

**Config:**
```yaml
notifications:
  webhook_url: "https://hooks.slack.com/..."
  enabled: true
```

**Verify:**
```bash
# Use webhook.site for testing
# Set webhook_url to test URL
# Make a file change with an error
# Check webhook.site received the POST
```

---

### [LOW] @config - Add custom ignore patterns via config

**Goal:** Let users specify additional patterns to ignore.

**Acceptance Criteria:**
- [ ] Merge user patterns with defaults (don't replace)
- [ ] Support glob patterns (e.g., `*.log`, `temp_*`)
- [ ] Document pattern syntax in README

**Verify:**
```yaml
ignore_patterns:
  - "*.log"
  - "temp_*"
```
```bash
./run_agent.sh &
touch test.log  # Should be ignored
touch temp_file  # Should be ignored
touch real.py   # Should trigger analysis
```

---

### [LOW] @feature - Implement session persistence

**Goal:** Maintain Claude conversation context across agent restarts.

**Acceptance Criteria:**
- [ ] Store session ID to file (`.claude_session`)
- [ ] On startup, attempt to resume previous session
- [ ] If resume fails, start fresh session
- [ ] Add `--new-session` flag to force fresh start

**Verify:**
```bash
./run_agent.sh  # Start agent, make some changes
# Ctrl+C to stop
cat .claude_session  # Should have session ID
./run_agent.sh  # Should say "Resuming session..."
```

---

### [LOW] @test - Add unit tests

**Goal:** Ensure reliability with automated tests.

**Acceptance Criteria:**
- [ ] Create `tests/` directory
- [ ] Add `pytest` to dev dependencies
- [ ] Test `ChangeTracker` debouncing logic
- [ ] Test `_should_ignore()` pattern matching
- [ ] Test config loading with various inputs
- [ ] Add test command to README

**Verify:**
```bash
source venv/bin/activate
pip install pytest
pytest tests/ -v
# All tests should pass
```

---

## Completed

- [x] @infra - Set up Python virtual environment
- [x] @infra - Install dependencies (claude-code-sdk, watchdog)
- [x] @feature - Implement file watcher with watchdog
- [x] @feature - Implement change debouncing (ChangeTracker)
- [x] @feature - Integrate Claude Code SDK for analysis
- [x] @feature - Add user approval prompt flow
- [x] @infra - Create runner script (run_agent.sh)
- [x] @docs - Update project documentation
- [x] @infra - Set up CI/CD (GitHub Actions, Dependabot, pre-commit)
- [x] @test - Add unit tests (19 tests for ChangeTracker, FileChangeHandler)
- [x] @feature - Implement envision task (GitHub issue #3)
  - Created `envision.py` - analyzes codebase and proposes improvements
  - Created `task_detector.py` - detects pending tasks in TODO/PLAN/CLAUDE.md
  - Created `.github/workflows/envision.yml` - triggers on manual dispatch
- [x] @infra - Add hourly task scheduler workflow
  - Created `.github/workflows/scheduler.yml` - runs every hour
  - Checks for pending tasks, triggers envision if none found
- [x] @feature - Add API error handling in agent.py
  - Wrapped query() calls in try-except
  - Graceful failure, continues monitoring
- [x] @docs - Add docstrings to core async functions
- [x] @test - Add pytest tests for task_detector.py (48 tests)
- [x] @refactor - Extract message parsing helper function
- [x] @refactor - Fix race condition in ChangeTracker
- [x] @feature - Add Claude API usage tracking to envision.py
  - Tracks input/output tokens and estimated cost
  - Writes GitHub Actions step summary

---

## How to Pick a Task

1. Check **In Progress** - don't start if something's active
2. Pick highest priority (`[HIGH]` > `[MED]` > `[LOW]`)
3. Match your specialization (`@feature`, `@config`, etc.)
4. Read **Acceptance Criteria** carefully
5. Run **Verify** steps when done
6. Move task to **Completed** when all criteria met
