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

This installs both runtime and development dependencies defined in `pyproject.toml`:

Runtime:
- freqtrade[all] >= 2024.1 (includes CCXT, TA-Lib, pandas, numpy, and exchange integrations)

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

#### Application-Level Variables

| Variable | Required (dry_run) | Required (live) | Description | Valid Values |
|----------|-------------------|-----------------|-------------|--------------|
| BINANCE_API_KEY | No | Yes | Binance Japan API key (spot trading, no withdrawal) | API key string |
| BINANCE_API_SECRET | No | Yes | Binance Japan API secret | Secret string |
| TELEGRAM_TOKEN | Yes | Yes | Telegram bot token for trade notifications | Bot token string |
| TELEGRAM_CHAT_ID | Yes | Yes | Telegram chat ID for receiving alerts | Numeric chat ID |
| ENVIRONMENT | Yes | Yes | Operating mode | `dry_run` or `live` |
| HEARTBEAT_URL | Optional | Optional | UptimeRobot monitoring endpoint URL | HTTPS URL |
| JWT_SECRET_KEY | Yes | Yes | Secret key for API server JWT authentication | Random string (32+ chars recommended) |
| API_PASSWORD | Yes | Yes | Password for Freqtrade API server access | Password string |

#### Freqtrade Config Override Variables (Recommended)

These environment variables override values in config JSON files at runtime. Config files keep secret fields as empty strings (""); actual values are injected via these variables. This prevents secrets from being committed to version control.

| Variable | Overrides Config Path | Purpose |
|----------|----------------------|---------|
| FREQTRADE__TELEGRAM__TOKEN | telegram.token | Telegram bot token |
| FREQTRADE__TELEGRAM__CHAT_ID | telegram.chat_id | Telegram chat ID |
| FREQTRADE__API_SERVER__JWT_SECRET_KEY | api_server.jwt_secret_key | API JWT auth key |
| FREQTRADE__API_SERVER__WS_TOKEN | api_server.ws_token | WebSocket token |
| FREQTRADE__API_SERVER__PASSWORD | api_server.password | API access password |

The double-underscore (`__`) notation is a Freqtrade convention for mapping nested JSON config paths to environment variables. For example, `FREQTRADE__TELEGRAM__TOKEN` maps to `config["telegram"]["token"]`.

Validate your environment configuration:

```bash
.venv/bin/python scripts/validate_env.py
```

The validator checks:
- Required variables are present (per mode: dry_run vs live)
- No placeholder values remain (e.g., "your_api_key_here")
- FREQTRADE__ override variables are set consistently with application-level vars
- Cross-validates config.json against .env for missing overrides

### 4. Configure Trading Settings

Configuration files are in `user_data/config/`. An example file is provided:

```bash
cp user_data/config/config.json.example user_data/config/config.json
```

Validate the configuration:

```bash
.venv/bin/python scripts/validate_config.py user_data/config/config.json
```

The config validator checks:
- Required fields are present (max_open_trades, stake_currency, stake_amount, dry_run)
- Value ranges are valid (positive stake, valid trade limits)
- Pair whitelist is not empty
- Hardcoded secrets are detected and flagged (secret fields should be empty in JSON)
- Live mode high-stake warnings (stake_amount > 50,000 JPY)

Configuration files by purpose:

| File | Purpose | Status |
|------|---------|--------|
| config.json | Development / Dry Run (50,000 JPY) | Active (Phase 5) |
| config.json.example | Template for config.json (committed) | Reference |
| config.backtest.json | Historical backtesting (6 max trades, 7 pairs) | Available |
| config.hyperopt.json | Hyperparameter optimization (2 pairs, deferred) | Available |
| config.live.json | Production deployment (2 pairs, future) | Future (Phase 6) |

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
│   ├── strategies/              # Strategy modules (927 lines total)
│   │   ├── dca_strategy.py      # 422 lines - Main strategy class (IStrategy)
│   │   ├── indicators.py        #  81 lines - Technical indicators (pure functions)
│   │   ├── risk_manager.py      # 219 lines - Risk management (frozen dataclass)
│   │   ├── market_regime.py     # 136 lines - Market regime detection (ADX + EMA)
│   │   └── slippage_protection.py #  69 lines - Slippage validation
│   ├── backtest_results/        # Backtest output (gitignored)
│   ├── data/                    # OHLCV data (gitignored)
│   └── logs/                    # Application logs (gitignored)
├── scripts/                     # Utility and automation scripts (1,849 lines total)
│   ├── analyze_backtest.py      # 254 lines - Backtest result evaluator
│   ├── monte_carlo.py           # 250 lines - Monte Carlo simulation
│   ├── validate_config.py       # 239 lines - Config file validator + secret detection
│   ├── validate_env.py          # 243 lines - Env variable validator + FREQTRADE__ checks
│   ├── check_dryrun_criteria.py # 142 lines - Dry run acceptance checker
│   ├── daily_report.py          # 118 lines - Daily report generator
│   ├── start_dryrun.sh          # 118 lines - Preflight + launcher
│   ├── walk_forward.sh          # 337 lines - Walk-forward analysis
│   ├── backup_db.sh             #  61 lines - SQLite backup
│   ├── download_data.sh         #  54 lines - Historical data fetch
│   └── heartbeat.sh             #  33 lines - Uptime monitor
├── tests/                       # Test suite (3,312 lines total, 11 test files)
│   ├── conftest.py              #  43 lines - Shared fixtures
│   └── unit/                    # Unit tests
│       ├── test_dca_strategy.py         # 747 lines
│       ├── test_monte_carlo.py          # 507 lines
│       ├── test_analyze_backtest.py     # 494 lines
│       ├── test_validate_config.py      # 376 lines
│       ├── test_validate_env.py         # 244 lines
│       ├── test_risk_manager.py         # 208 lines
│       ├── test_market_regime.py        # 187 lines
│       ├── test_check_dryrun_criteria.py# 156 lines
│       ├── test_daily_report.py         # 146 lines
│       ├── test_slippage_protection.py  # 113 lines
│       └── test_indicators.py           #  91 lines
├── docs/                        # Documentation
│   ├── CONTRIB.md               # This file
│   ├── RUNBOOK.md               # Operational runbook
│   ├── phase5-dryrun-operation.md # Phase 5 daily/weekly tasks (Japanese)
│   ├── backtest_summary.md      # Backtest results analysis
│   ├── hyperopt_assessment.md   # Hyperopt skip decision rationale
│   ├── CODEMAPS/                # Architectural documentation
│   │   ├── architecture.md      # High-level architecture + data flow
│   │   ├── backend.md           # Strategy modules + scripts detail
│   │   └── data.md              # Config schema + database structure
│   ├── initial/                 # Requirements and design docs
│   │   ├── crypto_dca_bot_requirements.md
│   │   ├── crypto_dca_bot_implementation_guide.md
│   │   └── 20260127_crypto_trading_automation.md
│   └── plans/                   # Implementation plans
│       └── 2026-01-29-cli-integration-tests.md
├── pyproject.toml               # Project metadata, deps, pytest + ruff config
├── .env                         # Environment variables (gitignored)
├── .env.example                 # Environment variable template
├── .gitignore                   # Git exclusion rules
└── CLAUDE.md                    # AI assistant instructions
```

## Scripts Reference

All scripts are located in the `scripts/` directory. Shell scripts must be run from the project root or use their built-in path resolution.

### Validation Scripts

| Script | Command | Description |
|--------|---------|-------------|
| validate_env.py | `.venv/bin/python scripts/validate_env.py` | Validates .env file completeness and placeholder detection. Checks required vs optional variables per mode (dry_run/live). Verifies FREQTRADE__ override variables and cross-checks config-env consistency. |
| validate_config.py | `.venv/bin/python scripts/validate_config.py <config_file>` | Validates Freqtrade config JSON: required fields, value ranges, pair whitelist, hardcoded secret detection, live mode stake warnings. Returns ValidationResult (frozen dataclass). |

### Analysis Scripts

| Script | Command | Description |
|--------|---------|-------------|
| analyze_backtest.py | `.venv/bin/python scripts/analyze_backtest.py <backtest_result.json>` | Parses Freqtrade backtest JSON and evaluates against minimum (win rate >= 50%, PF >= 1.2, Sharpe >= 0.5, DD <= 20%, trades >= 30) and target criteria (win rate >= 55%, PF >= 1.5, Sharpe >= 0.8, DD <= 15%, trades >= 50). |
| monte_carlo.py | `.venv/bin/python scripts/monte_carlo.py <backtest_result.json> [--simulations N] [--seed S]` | Runs Monte Carlo simulation (default: 100 runs, seed 42). Shuffles trade order to assess drawdown distribution and profit confidence intervals. Returns MonteCarloResult. |
| walk_forward.sh | `./scripts/walk_forward.sh` | Walk-forward analysis: In-Sample (2024/03-2025/06), Out-of-Sample (2025/07-2025/12), Final (2026/01). Checks OOS degradation < 30%. Env vars: STRATEGY, TIMEFRAME, STAKE_AMOUNT. |

### Monitoring Scripts

| Script | Command | Description |
|--------|---------|-------------|
| daily_report.py | `.venv/bin/python scripts/daily_report.py` | Generates daily performance report: uptime, API error rate, trade count, daily P&L, cumulative P&L, open positions. Returns DailyMetrics (frozen dataclass). |
| check_dryrun_criteria.py | `.venv/bin/python scripts/check_dryrun_criteria.py` | Evaluates Phase 5 Dry Run acceptance criteria: uptime >= 99%, API errors < 1%, order accuracy >= 98%, Sharpe deviation <= 0.3, days >= 14. Returns DryRunCriteriaResult. |
| heartbeat.sh | `./scripts/heartbeat.sh` | Checks if Freqtrade process is running (`pgrep -f "freqtrade trade"`), sends heartbeat ping to UptimeRobot URL from HEARTBEAT_URL env var. Cron: `*/5 * * * *`. |

### Maintenance Scripts

| Script | Command | Description |
|--------|---------|-------------|
| backup_db.sh | `./scripts/backup_db.sh` | Backs up SQLite databases (tradesv3.sqlite, tradesv3.dryrun.sqlite) to `backups/db/` with gzip compression. Retention: 30 days. Cron: `0 3 * * *`. |
| download_data.sh | `./scripts/download_data.sh` | Downloads OHLCV data for trading pairs across 4 timeframes (15m, 1h, 4h, 1d) from Binance. Start date: 2024-03-12. |
| start_dryrun.sh | `./scripts/start_dryrun.sh [--preflight-only]` | Runs 5 preflight checks (env vars, config, Freqtrade install, DB dir, strategy file) then launches Freqtrade Dry Run. Use `--preflight-only` to skip the actual launch. |

### Freqtrade Built-in Commands

| Command | Description |
|---------|-------------|
| `freqtrade trade --config user_data/config/config.json` | Start trading (dry run or live, per config) |
| `freqtrade backtesting --config user_data/config/config.backtest.json --strategy DCAStrategy --timerange 20240301-20260131` | Run backtest over 18-month range |
| `freqtrade hyperopt --config user_data/config/config.hyperopt.json --strategy DCAStrategy --hyperopt-loss SharpeHyperOptLoss --epochs 500` | Hyperparameter optimization (500 epochs, currently deferred) |
| `freqtrade plot-dataframe --config user_data/config/config.backtest.json --strategy DCAStrategy --pairs BTC/JPY` | Plot backtest results |

## Testing

### Test Framework

Tests use pytest with the following conventions (configured in `pyproject.toml`):
- Test files: `test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`
- Pattern: AAA (Arrange-Act-Assert)
- Coverage target: 80%+ (auto-measured for `user_data/strategies/` and `scripts/`)
- Coverage output: HTML (`htmlcov/`) + terminal-missing format

### Running Tests

```bash
# Run all tests with coverage report (HTML + terminal)
pytest

# Run specific test file
pytest tests/unit/test_dca_strategy.py

# Run specific test function
pytest tests/unit/test_dca_strategy.py::test_populate_indicators

# Run specific test class
pytest tests/unit/test_monte_carlo.py::TestMonteCarloMain

# Verbose output
pytest -v

# Generate HTML coverage report only
pytest --cov-report=html
```

### Test Files

| Test File | Lines | Module Under Test |
|-----------|-------|-------------------|
| test_dca_strategy.py | 747 | DCAStrategy (main strategy class) |
| test_monte_carlo.py | 507 | Monte Carlo simulation + CLI main() |
| test_analyze_backtest.py | 494 | Backtest result parsing + evaluation + CLI main() |
| test_validate_config.py | 376 | Config file validation + CLI main() |
| test_validate_env.py | 244 | Environment variable validation |
| test_risk_manager.py | 208 | Position sizing, circuit breaker, portfolio limits |
| test_market_regime.py | 187 | Trend classification (bullish/bearish/sideways) |
| test_check_dryrun_criteria.py | 156 | Dry Run acceptance criteria |
| test_daily_report.py | 146 | Daily report generation |
| test_slippage_protection.py | 113 | Price deviation validation |
| test_indicators.py | 91 | Technical indicator calculations |

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
- Script output classes use `@dataclass(frozen=True)`
- No in-place modifications of data structures

### File Size

- Typical: 200-400 lines
- Maximum: 800 lines
- Current module range: 69-422 lines (all within targets)
- Current test range: 91-747 lines

### Error Handling

All scripts use comprehensive error handling with typed results (frozen dataclasses with `valid`/`errors`/`warnings` fields or similar structured patterns).

### Pure Functions

Scripts expose pure evaluation functions alongside CLI `main()` wrappers. This separation enables unit testing of logic without CLI side effects.

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
- `user_data/config/config.live.json` (production config)
- `user_data/data/` (large OHLCV data files)
- `user_data/logs/` (runtime logs)
- `user_data/backtest_results/` (generated output)
- `*.sqlite`, `*.dryrun.sqlite` (database files)
- `.venv/` (virtual environment)
- `htmlcov/`, `.coverage` (test artifacts)
- `__pycache__/` (Python bytecode cache)

### Security: Never Commit Secrets

- Config JSON files must keep all secret fields as empty strings `""`
- All secrets must be set via `.env` or `FREQTRADE__*` environment variables
- The `validate_config.py` script detects hardcoded secrets in JSON files
- The `validate_env.py` script checks config-env consistency

## Current Phase: Phase 5 (Dry Run)

Started: 2026-01-30
Expected completion: 2026-02-13

See `docs/phase5-dryrun-operation.md` for the complete operation manual, including daily tasks, weekly tasks, troubleshooting, and acceptance criteria.

See `docs/RUNBOOK.md` for deployment, monitoring, troubleshooting, and rollback procedures.

---

Generated from codebase on 2026-01-30.
