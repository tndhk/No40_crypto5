#!/usr/bin/env bash
#
# Start Dry Run with preflight checks
#
# Usage:
#   ./scripts/start_dryrun.sh             # Run preflight checks and start Dry Run
#   ./scripts/start_dryrun.sh --preflight-only  # Run preflight checks only
#

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Load environment variables from .env file
if [[ -f ".env" ]]; then
    set -a
    source .env
    set +a
    echo "Loaded environment variables from .env"
fi

# Check if preflight-only mode
PREFLIGHT_ONLY=false
if [[ "${1:-}" == "--preflight-only" ]]; then
    PREFLIGHT_ONLY=true
fi

echo "========================================"
echo "Freqtrade DCA Bot - Dry Run Launcher"
echo "========================================"
echo ""

# Preflight Check 1: Environment variable validation
echo "1. Validating environment variables..."
if .venv/bin/python scripts/validate_env.py; then
    echo -e "${GREEN}✓ Environment validation passed${NC}"
else
    echo -e "${RED}✗ Environment validation failed${NC}"
    exit 1
fi
echo ""

# Preflight Check 2: Config validation
echo "2. Validating config.json..."
if .venv/bin/python scripts/validate_config.py user_data/config/config.json; then
    echo -e "${GREEN}✓ Config validation passed${NC}"
else
    echo -e "${RED}✗ Config validation failed${NC}"
    exit 1
fi
echo ""

# Preflight Check 3: Freqtrade installation check
echo "3. Checking Freqtrade installation..."
if .venv/bin/freqtrade --version > /dev/null 2>&1; then
    FREQTRADE_VERSION=$(.venv/bin/freqtrade --version 2>&1 | head -1)
    echo -e "${GREEN}✓ Freqtrade found: ${FREQTRADE_VERSION}${NC}"
else
    echo -e "${RED}✗ Freqtrade not found${NC}"
    exit 1
fi
echo ""

# Preflight Check 4: Database directory check
echo "4. Checking database directory..."
DB_DIR="user_data"
if [[ ! -d "$DB_DIR" ]]; then
    echo -e "${YELLOW}! Creating database directory: $DB_DIR${NC}"
    mkdir -p "$DB_DIR"
fi
echo -e "${GREEN}✓ Database directory exists: $DB_DIR${NC}"
echo ""

# Preflight Check 5: Strategy file check
echo "5. Checking strategy file..."
STRATEGY_FILE="user_data/strategies/dca_strategy.py"
if [[ -f "$STRATEGY_FILE" ]]; then
    echo -e "${GREEN}✓ Strategy file found: $STRATEGY_FILE${NC}"
else
    echo -e "${RED}✗ Strategy file not found: $STRATEGY_FILE${NC}"
    exit 1
fi
echo ""

# If preflight-only mode, exit here
if [[ "$PREFLIGHT_ONLY" == true ]]; then
    echo "========================================"
    echo -e "${GREEN}All preflight checks passed!${NC}"
    echo "========================================"
    exit 0
fi

# Start Dry Run
echo "========================================"
echo "Starting Dry Run..."
echo "========================================"
echo ""
echo "Config: user_data/config/config.json"
echo "Strategy: DCAStrategy"
echo "Mode: Dry Run (paper trading)"
echo ""
echo "Press Ctrl+C to stop the bot"
echo ""
echo "========================================"
echo ""

# Launch Freqtrade
exec .venv/bin/freqtrade trade \
    --config user_data/config/config.json \
    --strategy DCAStrategy
