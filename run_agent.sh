#!/bin/bash
# Run the Claude Continuous Agent

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "Error: Virtual environment not found. Run:"
    echo "  python3 -m venv venv && source venv/bin/activate && pip install claude-code-sdk watchdog"
    exit 1
fi

# Run the agent
python agent.py
