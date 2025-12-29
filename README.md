# Claude Continuous Agent

A Python-based file monitoring agent that uses Claude to automatically analyze code changes and propose fixes with user approval.

## Features

- Watches files for changes in real-time using `watchdog`
- Analyzes modified code for errors, bugs, and issues using Claude
- Semi-automated workflow: proposes fixes and waits for user approval
- Debounces rapid changes to avoid redundant analysis
- Ignores common non-source directories (`.git`, `venv`, `node_modules`, etc.)

## Prerequisites

- Python 3.10+
- Claude Code CLI installed and authenticated
- API access configured

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd auto_claude

# Create virtual environment and install dependencies
python3 -m venv venv
source venv/bin/activate
pip install claude-code-sdk watchdog
```

## Usage

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
├── agent.py        # Main agent script
├── run_agent.sh    # Runner script
├── venv/           # Python virtual environment
├── README.md       # This file
├── PLAN.md         # Architecture and design
├── TODO.md         # Task tracking
└── CLAUDE.md       # AI assistant context
```

## License

MIT
