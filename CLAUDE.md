# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

暗号通貨DCA(Dollar Cost Averaging)トレーディングボット。Freqtradeフレームワークを使用してBinance Japanでの自動取引を実装。

Technology Stack:
- Python 3.11+
- Freqtrade 2024.x (cryptocurrency trading bot framework)
- CCXT (exchange integration)
- TA-Lib (technical analysis)
- pytest (testing framework, 80%+ coverage target)

## Common Commands

### Project Setup
```bash
# Create virtual environment
python3.11 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Verify installation
freqtrade --version
```

### Testing
```bash
# Run all tests with coverage (HTML + terminal output)
pytest

# Run specific test file
pytest tests/unit/test_dca_strategy.py

# Run specific test function
pytest tests/unit/test_dca_strategy.py::test_populate_indicators

# Run tests with verbose output
pytest -v

# Coverage target: 80%+ required
```

### Linting and Formatting
```bash
# Run ruff linter
ruff check .

# Auto-fix linting issues
ruff check --fix .

# Format code
ruff format .
```

### Freqtrade Operations

#### Development and Testing
```bash
# Validate environment variables before starting
.venv/bin/python scripts/validate_env.py

# Validate configuration file
.venv/bin/python scripts/validate_config.py user_data/config/config.json

# Start Dry Run with preflight checks
./scripts/start_dryrun.sh

# Preflight checks only (no start)
./scripts/start_dryrun.sh --preflight-only

# Manual Dry Run start (without script)
freqtrade trade --config user_data/config/config.json
```

#### Backtesting and Analysis
```bash
# Download historical data (BTC/JPY, ETH/JPY, etc. for 18+ months)
./scripts/download_data.sh

# Run backtest (20240301-20260131 = 18 months)
freqtrade backtesting --config user_data/config/config.backtest.json --strategy DCAStrategy --timerange 20240301-20260131

# Analyze backtest results
.venv/bin/python scripts/analyze_backtest.py user_data/backtest_results/backtest-result-*.json

# Walk-forward analysis (out-of-sample validation)
./scripts/walk_forward.sh

# Monte Carlo simulation (100+ runs)
.venv/bin/python scripts/monte_carlo.py user_data/backtest_results/backtest-result-*.json

# Plot backtest results
freqtrade plot-dataframe --config user_data/config/config.backtest.json --strategy DCAStrategy --pairs BTC/JPY
```

#### Hyperparameter Optimization
```bash
# Hyperopt: 500 epochs recommended
freqtrade hyperopt --config user_data/config/config.hyperopt.json --strategy DCAStrategy --hyperopt-loss SharpeHyperOptLoss --epochs 500

# Hyperopt with specific spaces
freqtrade hyperopt --config user_data/config/config.hyperopt.json --strategy DCAStrategy --hyperopt-loss SharpeHyperOptLoss --spaces buy sell --epochs 500
```

### Monitoring and Maintenance

#### Daily Operations
```bash
# Generate daily report (run once per day)
.venv/bin/python scripts/daily_report.py

# Check Dry Run criteria (for Phase 5 validation)
.venv/bin/python scripts/check_dryrun_criteria.py

# Check heartbeat monitoring
./scripts/heartbeat.sh

# View real-time logs
tail -f user_data/logs/freqtrade.log

# Check for errors/warnings
tail -100 user_data/logs/freqtrade.log | grep -i "error\|warning"
```

#### Database Operations
```bash
# Backup database (run weekly on Sundays)
./scripts/backup_db.sh

# Query recent trades
sqlite3 user_data/tradesv3.dryrun.sqlite "SELECT * FROM trades ORDER BY id DESC LIMIT 10;"

# Check database status
sqlite3 user_data/tradesv3.dryrun.sqlite ".tables"
```

#### API Server
```bash
# Check API server health
curl http://127.0.0.1:8081/api/v1/ping

# Get trading stats
curl http://127.0.0.1:8081/api/v1/stats

# Get current balance
curl http://127.0.0.1:8081/api/v1/balance
```

#### Telegram Commands
Available in Telegram chat with the bot:
- `/status` - Current trade status
- `/profit` - Total profit
- `/balance` - Wallet balance
- `/stats` - Trading statistics
- `/daily` - Daily report
- `/performance` - Performance by pair
- `/help` - Command list

## Code Architecture

### Strategy Module Structure

**DCAStrategy (user_data/strategies/dca_strategy.py)**
- Main strategy class inheriting from IStrategy
- Entry logic: RSI-based entry (RSI <= 45) with volume confirmation
- DCA position adjustments: 3 additional buys at -7%, -12%, -18% drawdowns
- Partial take-profit: 33% position at +8% profit
- Risk management integration via RiskManager
- Market regime filtering via MarketRegime
- Slippage protection via SlippageProtection

**Modular Components (pure functions/classes):**
- `indicators.py`: Technical indicator calculations (EMA, RSI, Bollinger Bands, Volume SMA)
- `risk_manager.py`: Position sizing, portfolio limits, circuit breaker, consecutive loss tracking
- `market_regime.py`: Trend classification (bullish/bearish/sideways) using ADX and EMA crossovers
- `slippage_protection.py`: Price deviation validation (max 0.5% slippage)

### Immutability Pattern
All modules follow immutable design:
- Indicators return new DataFrames (never mutate input)
- RiskManager returns frozen dataclass results
- No in-place modifications of data structures

### Configuration Files
- `config.json`: Development/dry run (50,000 JPY initial wallet)
- `config.backtest.json`: Historical testing configuration
- `config.hyperopt.json`: Parameter optimization setup
- `config.live.json`: Production deployment (higher stakes)

All configs stored in `user_data/config/`

### Secret Management
Secrets are provided via Freqtrade's native FREQTRADE__ environment variable overrides.
Config files contain empty strings for secret fields.
See .env.example for required variables.

### Test Structure
Tests follow AAA pattern (Arrange-Act-Assert):
- `conftest.py`: Shared fixtures (default_conf, mock_exchange, mock_trade)
- `tests/unit/`: Unit tests for each module (52+ tests)
- Coverage reporting: HTML + terminal-missing format
- Coverage target: 80%+ (configured in pyproject.toml)

## Development Workflow

### Current Phase: Phase 5 (Dry Run - 14 days)
Started: 2026-01-30
Expected completion: 2026-02-13

Current configuration:
- Freqtrade Dry Run: Active
- API Server: http://127.0.0.1:8081
- Initial capital: 50,000 JPY
- Trading pairs: 7 pairs (BTC/JPY, ETH/JPY, XRP/JPY, ADA/JPY, DOGE/JPY, SOL/JPY, LINK/JPY)
- Timeframe: 15m
- Telegram notifications: Enabled

Phase 5 success criteria (verified via `scripts/check_dryrun_criteria.py`):
- Uptime >= 95%
- API error rate <= 5%
- Order accuracy >= 98%
- Sharpe ratio deviation <= 20% (vs backtest)
- Operation days >= 14

See `docs/phase5-dryrun-operation.md` for daily/weekly tasks.

### TDD Workflow (Required)
1. Write failing test first (RED)
2. Implement minimal code (GREEN)
3. Refactor (IMPROVE)
4. Verify 80%+ coverage maintained

### Testing Before Deployment
Mandatory validation sequence:
1. Unit tests: All 52+ tests passing
2. Config validation: `python scripts/validate_config.py`
3. Backtest: 18+ months historical data (20240301-20260131)
4. Walk-forward analysis: Out-of-sample validation
5. Hyperopt: 500 epochs for parameter tuning
6. Monte Carlo: 100+ simulations
7. Dry run: Minimum 2 weeks before live

Success criteria:
- Win rate >= 50% (target 60%)
- Profit factor >= 1.2 (target 1.5)
- Sharpe ratio >= 0.5 (target 1.0)
- Max drawdown <= 20% (target 15%)
- Minimum 30+ trades

## Key Trading Parameters

### Strategy Settings
- Trading pairs: BTC/JPY, ETH/JPY, XRP/JPY, ADA/JPY, DOGE/JPY, SOL/JPY, LINK/JPY (Binance Japan)
- Timeframe: 15m (currently active)
- Entry signal: RSI <= 45 (oversold) + volume filter (market regime filter removed for trade frequency)
- Exit signal: Minimal ROI (15% immediate, 10% after 45h, 5% after 90h)
- Stoploss: -20%
- Trailing stop: +2% trail after +5% profit reached
- Max concurrent trades: 2-3
- Stake per trade: 10,000-50,000 JPY

### DCA Levels
- Level 1: Initial entry at RSI <= 45
- Level 2: Add at -7% unrealized P&L (multiplier: base x 1.25)
- Level 3: Add at -12% unrealized P&L (multiplier: base x 1.50)
- Level 4: Add at -18% unrealized P&L (multiplier: base x 1.75)
- Max 3 additional entries (trade.nr_of_successful_entries <= 3)

### Risk Management Thresholds
- Portfolio allocation: Max 20% per position
- Daily loss limit: Max 5% of total capital
- Circuit breaker: 15% portfolio drawdown
- Consecutive stoploss: Max 3 losses trigger cooldown
- Cooldown period: 24 hours after stoploss
- Slippage tolerance: 0.5%

## Environment Variables

Required in `.env` (see `.env.example`):
- `BINANCE_API_KEY`: Exchange API key (spot trading only, no withdrawal)
- `BINANCE_API_SECRET`: Exchange API secret
- `TELEGRAM_TOKEN`: Telegram bot token for notifications
- `TELEGRAM_CHAT_ID`: Telegram chat ID for alerts
- `JWT_SECRET_KEY`: API server authentication
- `API_PASSWORD`: API access control
- `HEARTBEAT_URL`: Uptime monitoring endpoint
- `ENVIRONMENT`: dry_run or live

NEVER commit `.env` file (already in .gitignore)

## Security Constraints

- API keys: Spot trading only, withdrawal disabled
- IP restrictions: Enable for live mode
- Rate limiting: 200ms per request (Binance compliance)
- API timeout: 10 seconds max
- Log filtering: Prevent secret leakage in Telegram notifications

## File Size and Organization

Target module sizes:
- Typical: 200-400 lines
- Maximum: 800 lines
- Current modules: 69-389 lines (within targets)

Organize by feature/domain, not by type.

## Critical Scripts

### Validation Scripts (Pre-flight checks)
- `scripts/validate_env.py`: Environment variable validation (checks .env completeness)
- `scripts/validate_config.py`: Configuration file validation (Freqtrade config schema)

### Analysis Scripts
- `scripts/analyze_backtest.py`: Parse and analyze backtest JSON results
- `scripts/monte_carlo.py`: Monte Carlo simulation for risk assessment (100+ runs)
- `scripts/walk_forward.sh`: Walk-forward analysis for out-of-sample validation

### Monitoring Scripts
- `scripts/daily_report.py`: Generate daily performance report (uptime, trades, P&L)
- `scripts/check_dryrun_criteria.py`: Verify Phase 5 success criteria (95% uptime, 5% error rate, etc.)
- `scripts/heartbeat.sh`: Uptime monitoring integration

### Maintenance Scripts
- `scripts/backup_db.sh`: Database backup (creates timestamped backup in `backups/`)
- `scripts/download_data.sh`: Download historical OHLCV data from Binance
- `scripts/start_dryrun.sh`: Preflight checks + Dry Run launcher

## Project Structure

```
.
├── user_data/
│   ├── config/              # Configuration files
│   │   ├── config.json      # Dry run config (active)
│   │   ├── config.backtest.json
│   │   ├── config.hyperopt.json
│   │   └── config.live.json # Production config (future)
│   ├── strategies/          # Strategy modules
│   │   ├── dca_strategy.py  # Main strategy class
│   │   ├── indicators.py    # Technical indicators (pure functions)
│   │   ├── risk_manager.py  # Risk management (frozen dataclass)
│   │   ├── market_regime.py # Market regime detection
│   │   └── slippage_protection.py # Slippage validation
│   ├── backtest_results/    # Backtest outputs
│   └── logs/                # Application logs
├── scripts/                 # Utility scripts (see above)
├── tests/
│   ├── unit/                # Unit tests (52+ tests)
│   └── conftest.py          # Shared test fixtures
├── docs/                    # Documentation
│   ├── phase5-dryrun-operation.md # Current phase manual
│   ├── backtest_summary.md
│   └── hyperopt_assessment.md
├── pyproject.toml           # Project dependencies + pytest config
└── .env                     # Environment variables (never commit)
```
