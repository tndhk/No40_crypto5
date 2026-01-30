# Backend Codemap

Last Updated: 2026-01-30
Framework/Runtime: Python 3.11+ / Freqtrade 2024.x
Entry Point: `user_data/strategies/dca_strategy.py`

## Strategy Modules (`user_data/strategies/`)

### DCAStrategy (`dca_strategy.py` -- 422 lines)

Inherits from `freqtrade.strategy.IStrategy` (INTERFACE_VERSION = 3).

| Method                      | Purpose                                          | Calls To                     |
|-----------------------------|--------------------------------------------------|------------------------------|
| `__init__(config)`          | Initialize sub-modules from config params        | MarketRegime, SlippageProtection, RiskManager |
| `protections` (property)    | Return Freqtrade protection rules                | --                           |
| `populate_indicators(df)`   | Add RSI, Volume SMA, EMA50/200, ADX              | calculate_rsi, calculate_volume_sma, MarketRegime.add_regime_indicators |
| `populate_entry_trend(df)`  | Set enter_long=1 when RSI<=45 and volume filter  | --                           |
| `populate_exit_trend(df)`   | Set exit_long=1 when RSI>=70                     | --                           |
| `custom_stake_amount()`     | Scale stake for DCA, check position/portfolio limits | RiskManager.check_position_size, check_portfolio_limit |
| `adjust_trade_position()`   | DCA buy at -7%/-12%/-18%, partial sell at +8%    | RiskManager.check_cooldown   |
| `confirm_trade_entry()`     | Block on consecutive losses or slippage          | RiskManager.check_consecutive_losses, SlippageProtection.check_slippage |
| `confirm_trade_exit()`      | Record result, trigger cooldown on stoploss      | RiskManager.record_trade_result, trigger_cooldown |
| `custom_exit()`             | No custom logic (returns None)                   | --                           |

Strategy Parameters:

| Parameter                    | Type            | Default | Optimize |
|------------------------------|-----------------|---------|----------|
| `timeframe`                  | str             | 15m     | No       |
| `stoploss`                   | float           | -0.20   | No       |
| `trailing_stop_positive`     | float           | 0.02    | No       |
| `trailing_stop_positive_offset` | float        | 0.05    | No       |
| `dca_threshold_1`            | DecimalParameter | -0.07  | Yes      |
| `dca_threshold_2`            | DecimalParameter | -0.12  | Yes      |
| `dca_threshold_3`            | DecimalParameter | -0.18  | Yes      |
| `take_profit_threshold`      | DecimalParameter | 0.08   | Yes      |
| `take_profit_sell_ratio`     | DecimalParameter | 0.33   | Yes      |

Protection Rules:

| Protection       | Config                                         |
|------------------|------------------------------------------------|
| CooldownPeriod   | 3 candles after stoploss                       |
| MaxDrawdown      | 15% over 48 candles, 20 trade limit            |
| StoplossGuard    | 3 stops in 24 candles                          |
| LowProfitPairs   | -5% profit, 2 trades in 48 candles             |

---

### Indicators (`indicators.py` -- 81 lines)

Pure functions. Each returns a new DataFrame (input not mutated).

| Function                | Output Column(s)                    | Library  |
|-------------------------|-------------------------------------|----------|
| `calculate_ema(df, period)` | `ema_{period}`                  | TA-Lib   |
| `calculate_rsi(df, period)` | `rsi_{period}`                  | TA-Lib   |
| `calculate_bollinger_bands(df, period, std)` | `bb_upper`, `bb_middle`, `bb_lower` | TA-Lib |
| `calculate_volume_sma(df, period)` | `volume_sma_{period}`      | pandas rolling |

---

### MarketRegime (`market_regime.py` -- 136 lines)

| Method                     | Returns          | Purpose                              |
|----------------------------|------------------|--------------------------------------|
| `__init__(adx_threshold)`  | --               | Set ADX threshold (default 25.0)     |
| `detect_regime(df)`        | `MarketRegimeType` ('bullish'/'bearish'/'sideways') | Classify using EMA50/200 crossover + ADX |
| `should_suppress_entry(df)` | bool            | Block entry in strong bear (ADX>35, EMA50<EMA200, RSI>=15) |
| `add_regime_indicators(df)` | DataFrame       | Add ema_50, ema_200, adx columns     |

Depends on: `indicators.calculate_ema`, `talib.ADX`

---

### RiskManager (`risk_manager.py` -- 219 lines)

Stateful class tracking consecutive losses, cooldown, daily losses, peak balance.

| Method                            | Returns | Purpose                                    |
|-----------------------------------|---------|--------------------------------------------|
| `check_position_size(size)`       | bool    | Size <= max_position_size                  |
| `check_portfolio_limit(size, total)` | bool | Size <= total * max_portfolio_allocation   |
| `check_daily_loss_limit(loss, balance)` | bool | abs(loss) <= balance * daily_loss_limit |
| `check_circuit_breaker(current, peak)` | bool | drawdown < circuit_breaker_drawdown     |
| `record_trade_result(is_loss)`    | None    | Increment/reset consecutive loss counter   |
| `check_consecutive_losses()`      | bool    | count < max_consecutive_losses             |
| `trigger_cooldown(time)`          | None    | Set cooldown_until = time + cooldown_hours |
| `check_cooldown(time)`            | bool    | time >= cooldown_until                     |
| `record_daily_loss(amount, time)` | None    | Accumulate daily loss                      |
| `get_daily_loss(time)`            | float   | Return daily cumulative loss               |
| `check_daily_loss_limit_tracked(time, balance)` | bool | Internal daily loss within limit |
| `update_balance(balance)`         | None    | Track peak balance                         |
| `check_circuit_breaker_tracked(balance)` | bool | Internal peak-based circuit breaker   |

Constructor Parameters: `max_position_size`, `max_portfolio_allocation`, `daily_loss_limit`, `circuit_breaker_drawdown`, `max_consecutive_losses`, `cooldown_hours`

---

### SlippageProtection (`slippage_protection.py` -- 69 lines)

| Method                          | Returns | Purpose                              |
|---------------------------------|---------|--------------------------------------|
| `calculate_slippage_percentage(expected, actual)` | float | Percentage deviation     |
| `check_slippage(expected, actual)` | bool  | abs(deviation) <= max_slippage_percent |

Constructor: `max_slippage_percent` (default 0.5%)

---

## Scripts (`scripts/`)

### Python Scripts

| Script                   | Lines | Data Classes          | Key Function                   | Purpose                            |
|--------------------------|-------|-----------------------|--------------------------------|------------------------------------|
| `analyze_backtest.py`    | 254   | BacktestMetrics, CriteriaResult | `evaluate_backtest(metrics)` | Evaluate backtest against min/target criteria |
| `monte_carlo.py`         | 250   | MonteCarloResult      | `run_monte_carlo(trades, n, seed)` | Shuffle trade order, compute drawdown distribution |
| `validate_config.py`     | 160   | ValidationResult      | `validate_config(config)`      | Check required fields, value ranges, warnings |
| `validate_env.py`        | 145   | EnvValidationResult   | `validate_env(vars, mode)`     | Verify .env variables for dry_run/live |
| `daily_report.py`        | 118   | DailyMetrics          | `format_daily_report(metrics)` | Generate daily text report          |
| `check_dryrun_criteria.py` | 142 | DryRunMetrics, DryRunCriteriaResult | `evaluate_dryrun(metrics)` | Check uptime/errors/accuracy/Sharpe/days |

### Shell Scripts

| Script              | Lines | Purpose                                          |
|---------------------|-------|--------------------------------------------------|
| `start_dryrun.sh`   | 110   | 5 preflight checks (env, config, freqtrade, db dir, strategy) then launch |
| `walk_forward.sh`   | 337   | IS/OOS/Final backtest + degradation analysis     |
| `download_data.sh`  |  54   | Fetch OHLCV for 10 pairs, 4 timeframes from Binance |
| `backup_db.sh`      |  61   | SQLite backup with gzip, 30-day retention        |
| `heartbeat.sh`      |  33   | Check freqtrade process, ping HEARTBEAT_URL      |

---

## Test Coverage (`tests/unit/`)

| Test File                      | Lines | Tests Module             |
|--------------------------------|-------|--------------------------|
| `test_dca_strategy.py`         | 747   | DCAStrategy              |
| `test_monte_carlo.py`          | 507   | monte_carlo              |
| `test_analyze_backtest.py`     | 494   | analyze_backtest         |
| `test_validate_config.py`      | 292   | validate_config          |
| `test_risk_manager.py`         | 208   | risk_manager             |
| `test_market_regime.py`        | 187   | market_regime            |
| `test_check_dryrun_criteria.py`| 156   | check_dryrun_criteria    |
| `test_daily_report.py`         | 146   | daily_report             |
| `test_validate_env.py`         | 134   | validate_env             |
| `test_slippage_protection.py`  | 113   | slippage_protection      |
| `test_indicators.py`           |  91   | indicators               |

Shared fixtures in `conftest.py`: `default_conf`, `mock_exchange`, `mock_trade`

---

## Related Codemaps

- [architecture.md](./architecture.md) -- High-level overview and data flow
- [data.md](./data.md) -- Config schema and database structure
