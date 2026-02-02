#!/bin/bash
# launchd_wrapper.sh - Freqtrade DCA Bot launcher for macOS launchd
# This script is invoked by launchd (com.freqtrade.dca-bot) to start
# the freqtrade dry run bot with proper environment setup.
# It loads environment variables from .env, activates the Python venv,
# and exec's into the freqtrade process.

set -e

# Move to project root (dynamically resolved)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# Load environment variables from .env if present
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# Activate Python virtual environment
source .venv/bin/activate

# Start freqtrade (exec replaces shell process for proper signal handling)
exec freqtrade trade --config user_data/config/config.json
