# Claude Continuous Agent

A Python-based file monitoring agent that uses Claude to automatically analyze code changes and propose fixes with user approval.

## Features

- **File Monitoring**: Watches files for changes in real-time using `watchdog`
- **AI Analysis**: Analyzes modified code for errors, bugs, and issues using Claude
- **Semi-Automated**: Proposes fixes and waits for user approval before applying
- **Debouncing**: Prevents redundant analysis during rapid edits
- **Envision Mode**: Automatically proposes codebase improvements when idle
- **CI/CD Integration**: GitHub Actions for testing, linting, and scheduled analysis
- **API Usage Tracking**: Monitors Claude API token usage and costs

## Prerequisites

- Python 3.10+
- Claude Code CLI installed and authenticated (`claude login`)
- For GitHub Actions: `ANTHROPIC_API_KEY` secret (optional)

## Installation

```bash
# Clone the repository
git clone https://github.com/buvche/auto_claude.git
cd auto_claude

# Create virtual environment and install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# For development
pip install -r requirements-dev.txt
```

## Usage

### Local Agent

```bash
# Using the runner script
./run_agent.sh

# Or manually
source venv/bin/activate
python agent.py
```

Once running, the agent will:
1. Monitor all files in the project directory
2. When a file changes, analyze it for issues
3. If issues are found, display the proposed fix
4. Prompt you with `Apply this fix? [y/n]`
5. Apply fixes only if approved

Press `Ctrl+C` to stop the agent.

### Envision Mode

Analyze the codebase for improvement opportunities:

```bash
# Run locally
python envision.py

# With options
python envision.py --max-agents 3 --max-time 600 --output json
```

### Check Pending Tasks

```bash
python task_detector.py
```

## GitHub Actions Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `ci.yml` | Push/PR | Run tests, linting, type checks |
| `scheduler.yml` | Hourly | Check for tasks, trigger envision if idle |
| `envision.yml` | Manual | Analyze codebase, propose improvements |

### Setting Up Automated Envision

1. Go to **Settings → Secrets and variables → Actions**
2. Add secret: `ANTHROPIC_API_KEY` with your API key
3. The scheduler will run hourly and trigger envision when no tasks are pending

**Estimated cost**: ~$0.22 per envision run

## Configuration

Edit `agent.py` to customize behavior:

| Variable | Default | Description |
|----------|---------|-------------|
| `WATCH_DIR` | Script directory | Directory to monitor |
| `IGNORE_PATTERNS` | `.git`, `venv`, etc. | Paths to ignore |
| `DEBOUNCE_SECONDS` | `2.0` | Wait time before processing changes |

## Project Structure

```
auto_claude/
├── agent.py              # Main agent (file watcher + Claude SDK)
├── envision.py           # Codebase improvement analyzer
├── task_detector.py      # Detects pending tasks in markdown files
├── run_agent.sh          # Runner script (activates venv)
├── requirements.txt      # Production dependencies
├── requirements-dev.txt  # Development dependencies
├── pyproject.toml        # Project configuration
├── tests/                # Test suite (67 tests)
│   ├── test_agent.py
│   └── test_task_detector.py
├── .github/
│   ├── workflows/
│   │   ├── ci.yml        # CI pipeline
│   │   ├── envision.yml  # Envision workflow
│   │   └── scheduler.yml # Hourly task scheduler
│   ├── dependabot.yml    # Dependency updates
│   └── ISSUE_TEMPLATE/   # Issue templates
├── README.md             # This file
├── PLAN.md               # Architecture and design
├── TODO.md               # Task tracking
└── CLAUDE.md             # AI assistant context
```

## Development

```bash
# Run tests
pytest tests/ -v

# Run linting
ruff check .

# Type checking
mypy agent.py --ignore-missing-imports

# All checks
pytest && ruff check . && mypy agent.py --ignore-missing-imports
```

## License

MIT
