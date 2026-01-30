# Architecture Codemap

Last Updated: 2026-01-30
Framework/Runtime: Python 3.11+ / Freqtrade 2024.x
Entry Point: `user_data/strategies/dca_strategy.py` (DCAStrategy class)

## Repository Structure

```
No40_Crypto5/
  pyproject.toml                    # Project config, deps, pytest, ruff
  user_data/
    strategies/                     # Trading strategy modules (core logic)
      dca_strategy.py               # 422 lines - Main strategy (IStrategy)
      indicators.py                 #  81 lines - Technical indicators (pure functions)
      market_regime.py              # 136 lines - Trend classification
      risk_manager.py               # 219 lines - Position/risk management
      slippage_protection.py        #  69 lines - Price deviation guard
    config/                         # Freqtrade JSON configs (4 profiles)
    data/binance/                   # Historical OHLCV data (.feather)
    backtest_results/               # Backtest output JSON
  scripts/                          # Utility and operations scripts
    analyze_backtest.py             # 254 lines - Evaluate backtest metrics
    monte_carlo.py                  # 250 lines - Monte Carlo simulation
    validate_config.py              # 160 lines - Config file validator
    validate_env.py                 # 145 lines - Env variable validator
    daily_report.py                 # 118 lines - Daily report generator
    check_dryrun_criteria.py        # 142 lines - Dry run acceptance checker
    start_dryrun.sh                 # 110 lines - Preflight + launcher
    walk_forward.sh                 # 337 lines - Walk-forward analysis
    download_data.sh                #  54 lines - Historical data fetch
    backup_db.sh                    #  61 lines - SQLite backup
    heartbeat.sh                    #  33 lines - Uptime monitor
  tests/
    conftest.py                     # Shared fixtures
    unit/                           # 11 test files, ~3,075 lines total
  docs/                             # Documentation
```

## Component Dependency Graph

```
                     Freqtrade Framework
                            |
                    +-------+-------+
                    |               |
               IStrategy       Trade/Exchange
                    |
             DCAStrategy (dca_strategy.py)
            /       |       \          \
           /        |        \          \
   Indicators  MarketRegime  RiskManager  SlippageProtection
   (indicators.py) (market_regime.py)  (risk_manager.py)  (slippage_protection.py)
        |            |
        +-----+------+
              |
        calculate_ema() --- used by MarketRegime.add_regime_indicators()
```

## Import Map

| Source Module               | Imports From                                    |
|-----------------------------|-------------------------------------------------|
| dca_strategy.py             | indicators, market_regime, risk_manager, slippage_protection, freqtrade.strategy, freqtrade.persistence |
| indicators.py               | talib.abstract, pandas                          |
| market_regime.py            | indicators (calculate_ema), talib.abstract, pandas |
| risk_manager.py             | datetime (stdlib only)                          |
| slippage_protection.py      | (no external imports)                           |
| analyze_backtest.py         | json, sys, dataclasses, pathlib                 |
| monte_carlo.py              | json, sys, numpy, dataclasses, pathlib          |
| validate_config.py          | json, sys, dataclasses, pathlib                 |
| validate_env.py             | sys, dataclasses, pathlib                       |
| daily_report.py             | sys, dataclasses, datetime                      |
| check_dryrun_criteria.py    | sys, dataclasses                                |

## Data Flow (Trading Cycle)

```
OHLCV Data (Binance via CCXT)
    |
    v
populate_indicators()
    |-- calculate_rsi() ---------> dataframe['rsi']
    |-- calculate_volume_sma() --> dataframe['volume_sma_20']
    |-- MarketRegime.add_regime_indicators()
    |       |-- calculate_ema(50) -> dataframe['ema_50']
    |       |-- calculate_ema(200) -> dataframe['ema_200']
    |       +-- ADX(14) -----------> dataframe['adx']
    v
populate_entry_trend()
    |-- RSI <= 45 AND volume > 0.9 * volume_sma_20
    v
confirm_trade_entry()
    |-- RiskManager.check_consecutive_losses()
    |-- SlippageProtection.check_slippage()
    v
custom_stake_amount()
    |-- RiskManager.check_position_size()
    |-- RiskManager.check_portfolio_limit()
    v
[TRADE OPEN]
    |
    v
adjust_trade_position()  (called each candle while trade is open)
    |-- RiskManager.check_cooldown()
    |-- Partial take-profit at +8% (sell 33%)
    |-- DCA levels at -7%, -12%, -18% (up to 3 additional entries)
    v
populate_exit_trend()
    |-- RSI >= 70
    v
confirm_trade_exit()
    |-- RiskManager.record_trade_result()
    |-- RiskManager.trigger_cooldown() (on stoploss)
    v
[TRADE CLOSED]
```

## Validation Pipeline (Pre-Deployment)

```
validate_env.py        --> Check .env variables
validate_config.py     --> Check config.json schema
    |
    v
start_dryrun.sh        --> Preflight checks + launch Freqtrade
    |
    v
[Dry Run for 14+ days]
    |
    v
check_dryrun_criteria.py  --> Uptime, API errors, order accuracy, Sharpe deviation
    |
    v
walk_forward.sh        --> IS/OOS/Final backtests + degradation analysis
    |-- analyze_backtest.py (evaluate metrics per period)
    v
monte_carlo.py         --> Robustness simulation (100+ runs)
```

## External Dependencies

| Package            | Purpose                                  |
|--------------------|------------------------------------------|
| freqtrade[all]     | Trading bot framework, exchange, UI      |
| talib (via freqtrade) | Technical analysis indicator library  |
| pandas             | DataFrame operations for OHLCV data      |
| numpy              | Monte Carlo simulation arrays            |
| ccxt (via freqtrade)  | Exchange API integration (Binance)    |
| pytest             | Test framework                           |
| pytest-cov         | Coverage reporting                       |
| pytest-mock        | Mocking utilities                        |
| ruff               | Linter and formatter                     |

## Design Principles

- Immutability: All dataclasses use `frozen=True`. Indicator functions return new DataFrames via `.copy()`.
- Pure functions: Scripts expose pure evaluation functions alongside CLI main() wrappers.
- Modular composition: DCAStrategy delegates to four independent modules (indicators, market_regime, risk_manager, slippage_protection).
- Configuration-driven: All risk thresholds are passed via Freqtrade config JSON, not hardcoded in strategy.

## Related Codemaps

- [backend.md](./backend.md) -- Strategy modules and scripts detail
- [data.md](./data.md) -- Configuration schema and database structure
