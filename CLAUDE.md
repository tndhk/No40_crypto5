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

### Testing
```bash
# Run all tests with coverage
pytest

# Run specific test file
pytest tests/unit/test_dca_strategy.py

# Run specific test function
pytest tests/unit/test_dca_strategy.py::test_populate_indicators

# Run tests with verbose output
pytest -v

# Generate HTML coverage report
pytest --cov-report=html
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
```bash
# Dry run mode (development)
freqtrade trade --config user_data/config/config.json

# Backtesting
freqtrade backtesting --config user_data/config/config.backtest.json --strategy DCAStrategy --timerange 20240301-20260131

# Hyperparameter optimization
freqtrade hyperopt --config user_data/config/config.hyperopt.json --strategy DCAStrategy --hyperopt-loss SharpeHyperOptLoss --epochs 500

# Download historical data
./scripts/download_data.sh

# Validate configuration
python scripts/validate_config.py user_data/config/config.json

# Plot backtest results
freqtrade plot-dataframe --config user_data/config/config.backtest.json --strategy DCAStrategy --pairs BTC/JPY
```

### Data and Maintenance
```bash
# Backup database
./scripts/backup_db.sh

# Check heartbeat monitoring
./scripts/heartbeat.sh
```

## Code Architecture

### Strategy Module Structure

**DCAStrategy (user_data/strategies/dca_strategy.py)**
- Main strategy class inheriting from IStrategy
- Entry logic: RSI-based oversold detection (RSI <= 30)
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

### Test Structure
Tests follow AAA pattern (Arrange-Act-Assert):
- `conftest.py`: Shared fixtures (default_conf, mock_exchange, mock_trade)
- `tests/unit/`: Unit tests for each module
- Coverage reporting: HTML + terminal-missing format

## Development Workflow

### Phase 4 Known Issues (Batch 0)
CRITICAL fixes required before backtesting:
1. Stoploss value: Change from -0.25 to -0.20 (dca_strategy.py:70)
2. Timeframe: Change from 5m to 1h (dca_strategy.py:47)
3. Trailing stop: Implement +5% trigger, +2% trail (missing)
4. Protections: Add Freqtrade protection properties (CooldownPeriod, MaxDrawdown, StoplossGuard)
5. Volume filtering: Add volume > volume_sma check to entry conditions
6. Risk manager integration: Connect RiskManager.check_position_size() and check_circuit_breaker() to strategy workflow

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
- Trading pairs: BTC/JPY, ETH/JPY (Binance Japan)
- Timeframe: 1 hour (must be fixed from current 5m)
- Entry signal: RSI <= 30 (oversold)
- Take profit: +8% (close 33% position)
- Stoploss: -20% (must be fixed from current -25%)
- Trailing stop: After +5% profit, trail at +2% (not implemented)
- Max concurrent trades: 2-3
- Stake per trade: 10,000-50,000 JPY

### DCA Levels
- Level 1: Initial entry at RSI <= 30
- Level 2: Add 50% at -7% unrealized P&L
- Level 3: Add 75% at -12% unrealized P&L
- Level 4: Add 100% at -18% unrealized P&L
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
