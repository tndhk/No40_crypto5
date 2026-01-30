# Contributing Guide

Last Updated: 2026-01-30

This document covers the development workflow, environment setup, scripts usage, and testing procedures for the Crypto DCA Trading Bot.

## Prerequisites

- Python 3.11 or later
- SQLite3 (for database operations)
- Binance Japan account (for live/dry-run trading)
- Telegram bot (for trade notifications)

## Environment Setup

### 1. Clone and Create Virtual Environment

```bash
git clone <repository-url>
cd No40_Crypto5

python3.11 -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -e ".[dev]"
```

This installs both runtime and development dependencies:

Runtime:
- freqtrade[all] >= 2024.1 (includes CCXT, TA-Lib, and exchange integrations)

Development:
- pytest >= 8.0.0
- pytest-mock >= 3.12.0
- pytest-cov >= 4.1.0
- ruff >= 0.1.0

### 3. Configure Environment Variables

Copy the example file and fill in actual values:

```bash
cp .env.example .env
```

| Variable | Required | Description | Valid Values |
|----------|----------|-------------|--------------|
| BINANCE_API_KEY | Live mode only | Binance Japan API key (spot trading, no withdrawal) | API key string |
| BINANCE_API_SECRET | Live mode only | Binance Japan API secret | Secret string |
| TELEGRAM_TOKEN | Yes | Telegram bot token for trade notifications | Bot token string |
| TELEGRAM_CHAT_ID | Yes | Telegram chat ID for receiving alerts | Numeric chat ID |
| ENVIRONMENT | Yes | Operating mode | `dry_run` or `live` |
| HEARTBEAT_URL | Optional | UptimeRobot monitoring endpoint URL | HTTPS URL |
| JWT_SECRET_KEY | Yes | Secret key for API server JWT authentication | Random string |
| API_PASSWORD | Yes | Password for Freqtrade API server access | Password string |

Validate your environment configuration:

```bash
.venv/bin/python scripts/validate_env.py
```

### 4. Configure Trading Settings

Configuration files are in `user_data/config/`. An example file is provided:

```bash
cp user_data/config/config.json.example user_data/config/config.json
```

Validate the configuration:

```bash
.venv/bin/python scripts/validate_config.py user_data/config/config.json
```

Configuration files by purpose:

| File | Purpose | Status |
|------|---------|--------|
| config.json | Development / Dry Run (50,000 JPY) | Active (Phase 5) |
| config.backtest.json | Historical backtesting | Available |
| config.hyperopt.json | Hyperparameter optimization | Available |
| config.live.json | Production deployment | Future (Phase 6) |

## Project Structure

```
.
├── user_data/
│   ├── config/                  # Configuration files
│   │   ├── config.json          # Dry run config (active, gitignored)
│   │   ├── config.json.example  # Example config (committed)
│   │   ├── config.backtest.json
│   │   ├── config.hyperopt.json
│   │   └── config.live.json
│   ├── strategies/              # Strategy modules
│   │   ├── dca_strategy.py      # Main strategy class (IStrategy)
│   │   ├── indicators.py        # Technical indicators (pure functions)
│   │   ├── risk_manager.py      # Risk management (frozen dataclass)
│   │   ├── market_regime.py     # Market regime detection (ADX + EMA)
│   │   └── slippage_protection.py  # Slippage validation
│   ├── backtest_results/        # Backtest output (gitignored)
│   ├── data/                    # OHLCV data (gitignored)
│   └── logs/                    # Application logs (gitignored)
├── scripts/                     # Utility and automation scripts
├── tests/
│   ├── conftest.py              # Shared fixtures
│   ├── unit/                    # Unit tests (52+ tests)
│   ├── integration/             # Integration tests
│   └── validation/              # Validation tests
├── docs/                        # Documentation
├── pyproject.toml               # Project metadata and tool config
├── .env                         # Environment variables (gitignored)
├── .env.example                 # Environment variable template
└── CLAUDE.md                    # AI assistant instructions
```

## Scripts Reference

All scripts are located in the `scripts/` directory. Shell scripts must be run from the project root or use their built-in path resolution.

### Validation Scripts

| Script | Command | Description |
|--------|---------|-------------|
| validate_env.py | `.venv/bin/python scripts/validate_env.py` | Validates .env file completeness and placeholder detection. Checks required vs optional variables per mode (dry_run/live). |
| validate_config.py | `.venv/bin/python scripts/validate_config.py <config_file>` | Validates Freqtrade config JSON: required fields, value ranges, pair whitelist, live mode stake warnings. |

### Analysis Scripts

| Script | Command | Description |
|--------|---------|-------------|
| analyze_backtest.py | `.venv/bin/python scripts/analyze_backtest.py <backtest_result.json>` | Parses Freqtrade backtest JSON and evaluates against minimum (win rate >= 50%, PF >= 1.2, Sharpe >= 0.5, DD <= 20%, trades >= 30) and target criteria. |
| monte_carlo.py | `.venv/bin/python scripts/monte_carlo.py <backtest_result.json> [--simulations N] [--seed S]` | Runs Monte Carlo simulation (default: 100 runs, seed 42). Shuffles trade order to assess drawdown distribution and profit confidence intervals. |
| walk_forward.sh | `./scripts/walk_forward.sh` | Walk-forward analysis: In-Sample (2024/03-2025/06), Out-of-Sample (2025/07-2025/12), Final (2026/01). Checks OOS degradation < 30%. Env vars: STRATEGY, TIMEFRAME, STAKE_AMOUNT. |

### Monitoring Scripts

| Script | Command | Description |
|--------|---------|-------------|
| daily_report.py | `.venv/bin/python scripts/daily_report.py` | Generates daily performance report (uptime, API error rate, trade count, P&L). Currently outputs example data; production mode fetches from Freqtrade API. |
| check_dryrun_criteria.py | `.venv/bin/python scripts/check_dryrun_criteria.py` | Evaluates Phase 5 Dry Run acceptance criteria: uptime >= 99%, API errors < 1%, order accuracy >= 98%, Sharpe deviation <= 0.3, days >= 14. |
| heartbeat.sh | `./scripts/heartbeat.sh` | Checks if Freqtrade process is running (`pgrep -f "freqtrade trade"`), sends heartbeat ping to UptimeRobot URL. Cron: `*/5 * * * *`. |

### Maintenance Scripts

| Script | Command | Description |
|--------|---------|-------------|
| backup_db.sh | `./scripts/backup_db.sh` | Backs up SQLite databases (tradesv3.sqlite, tradesv3.dryrun.sqlite) to `backups/db/` with gzip compression. Retention: 30 days. Cron: `0 3 * * *`. |
| download_data.sh | `./scripts/download_data.sh` | Downloads OHLCV data for 10 pairs (BTC/JPY, ETH/JPY, XRP/JPY, ADA/JPY, DOGE/JPY, DOT/JPY, MATIC/JPY, SOL/JPY, LINK/JPY, UNI/JPY) across 4 timeframes (15m, 1h, 4h, 1d) from 2024-03-12. |
| start_dryrun.sh | `./scripts/start_dryrun.sh [--preflight-only]` | Runs 5 preflight checks (env vars, config, Freqtrade install, DB dir, strategy file) then launches Freqtrade Dry Run. Use `--preflight-only` to skip the actual launch. |

### Freqtrade Built-in Commands

| Command | Description |
|---------|-------------|
| `freqtrade trade --config user_data/config/config.json` | Start trading (dry run or live, per config) |
| `freqtrade backtesting --config user_data/config/config.backtest.json --strategy DCAStrategy --timerange 20240301-20260131` | Run backtest over 18-month range |
| `freqtrade hyperopt --config user_data/config/config.hyperopt.json --strategy DCAStrategy --hyperopt-loss SharpeHyperOptLoss --epochs 500` | Hyperparameter optimization (500 epochs) |
| `freqtrade plot-dataframe --config user_data/config/config.backtest.json --strategy DCAStrategy --pairs BTC/JPY` | Plot backtest results |

## Testing

### Test Framework

Tests use pytest with the following conventions:
- Test files: `test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`
- Pattern: AAA (Arrange-Act-Assert)
- Coverage target: 80%+ (configured in pyproject.toml)

### Running Tests

```bash
# Run all tests with coverage report (HTML + terminal)
pytest

# Run specific test file
pytest tests/unit/test_dca_strategy.py

# Run specific test function
pytest tests/unit/test_dca_strategy.py::test_populate_indicators

# Verbose output
pytest -v

# Generate HTML coverage report only
pytest --cov-report=html
```

Coverage is automatically measured for `user_data/strategies/` and `scripts/` and reported to both terminal and `htmlcov/`.

### Test Files

| Test File | Module Under Test |
|-----------|-------------------|
| test_dca_strategy.py | DCAStrategy (main strategy class) |
| test_indicators.py | Technical indicator calculations |
| test_risk_manager.py | Position sizing, circuit breaker, portfolio limits |
| test_market_regime.py | Trend classification (bullish/bearish/sideways) |
| test_slippage_protection.py | Price deviation validation |
| test_validate_config.py | Configuration file validation |
| test_validate_env.py | Environment variable validation |
| test_analyze_backtest.py | Backtest result parsing and evaluation |
| test_check_dryrun_criteria.py | Dry Run acceptance criteria |
| test_daily_report.py | Daily report generation |
| test_monte_carlo.py | Monte Carlo simulation |

### Shared Test Fixtures (conftest.py)

| Fixture | Description |
|---------|-------------|
| default_conf | Default config dict (JPY, 10000 stake, dry_run, binance, BTC/JPY + ETH/JPY) |
| mock_exchange | Mocked Freqtrade Exchange with min_pair_stake_amount = 1000 |
| mock_trade | Mocked Trade with open_rate = 1,000,000, amount = 0.01, stake = 10,000 |

### TDD Workflow (Required for All Changes)

1. RED: Write a failing test
2. GREEN: Write minimal code to pass
3. IMPROVE: Refactor while keeping tests green
4. VERIFY: Ensure 80%+ coverage maintained

## Linting and Formatting

Configured via pyproject.toml using ruff:
- Line length: 100 characters
- Target: Python 3.11
- Selected rules: E (pycodestyle errors), F (pyflakes), I (isort), N (naming), W (warnings)
- Ignored: E501 (line too long, handled by formatter)

```bash
# Check for linting issues
ruff check .

# Auto-fix linting issues
ruff check --fix .

# Format code
ruff format .
```

## Code Style Requirements

### Immutability

All strategy modules use immutable patterns:
- Indicators return new DataFrames (never mutate input)
- RiskManager uses frozen dataclasses for results
- No in-place modifications of data structures

### File Size

- Typical: 200-400 lines
- Maximum: 800 lines
- Current modules: 69-389 lines (within targets)

### Error Handling

All scripts use comprehensive error handling with typed results (frozen dataclasses with `valid`/`errors`/`warnings` fields).

## Git Workflow

### Commit Messages

```
<type>: <description>
```

Types: feat, fix, refactor, docs, test, chore, perf, ci

### Files Never Committed

The following are in `.gitignore`:
- `.env`, `.env.local` (secrets)
- `user_data/config/config.json` (may contain API keys)
- `user_data/data/` (large OHLCV data files)
- `user_data/logs/` (runtime logs)
- `user_data/backtest_results/` (generated output)
- `*.sqlite`, `*.dryrun.sqlite` (database files)
- `.venv/` (virtual environment)
- `htmlcov/`, `.coverage` (test artifacts)

## Current Phase: Phase 5 (Dry Run)

Started: 2026-01-30
Expected completion: 2026-02-13

See `docs/phase5-dryrun-operation.md` for the complete operation manual, including daily tasks, weekly tasks, troubleshooting, and acceptance criteria.

---

Generated from codebase on 2026-01-30.
