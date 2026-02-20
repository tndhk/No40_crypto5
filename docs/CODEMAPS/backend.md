# Backend Codemap

Last Updated: 2026-02-20
Framework/Runtime: Python 3.11+ / Freqtrade 2026.1
Entry Point: `user_data/strategies/dca_strategy.py`

## Strategy Modules (`user_data/strategies/`)

### DCAStrategy (`dca_strategy.py`)

Inherits from `freqtrade.strategy.IStrategy` (INTERFACE_VERSION = 3).

| Method | Purpose |
|---|---|
| `__init__(config)` | Initialize `MarketRegime`, `SlippageProtection`, `RiskManager` |
| `protections` | Return Freqtrade protection rules |
| `populate_indicators(df)` | Add RSI, volume SMA, EMA50/200, ADX |
| `populate_entry_trend(df)` | Entry when `rsi <= 55` and volume filter passes |
| `populate_exit_trend(df)` | Exit when `rsi >= 70` |
| `custom_stake_amount(...)` | Enforce position/portfolio limits, size DCA entries |
| `adjust_trade_position(...)` | DCA/partial take-profit logic |
| `confirm_trade_entry(...)` | Consecutive loss + slippage checks |
| `confirm_trade_exit(...)` | Record result, trigger cooldown on stop-loss paths |
| `custom_exit(...)` | No custom exit (returns `None`) |

Current defaults:
- `timeframe`: `15m`
- `stoploss`: `-0.10`
- `trailing_stop_positive`: `0.01`
- `trailing_stop_positive_offset`: `0.03`
- DCA defaults: `-0.02`, `-0.04`, `-0.06`
- Partial TP: `+8%`, sell `33%`

### DCAStrategyBalanced (`dca_strategy_balanced.py`)

`DCAStrategy` を継承した安全寄りプロファイル。

| Method/Field | Purpose |
|---|---|
| `minimal_roi` | `3.5%` / `1.8%` / `0.8%` へ短縮 |
| `stoploss` | `-8%` に変更 |
| `trailing_stop_positive(_offset)` | `0.8%` / `2%` へ変更 |
| `max_entry_position_adjustment` | `2` に削減 |
| `populate_entry_trend(df)` | RSI/出来高に加え `ema_50>=ema_200` と `adx>=18` を要求 |
| `populate_exit_trend(df)` | `rsi>=64` または `rsi>=58 && close<ema_50` で離脱 |
| `adjust_trade_position(...)` | 元ロジックのDCA額に上限をかけて資金拘束を抑制 |

### Indicators (`indicators.py`)

Pure functions returning copied DataFrames.

- `calculate_ema(df, period)`
- `calculate_rsi(df, period=14)`
- `calculate_bollinger_bands(df, period=20, std=2.0)`
- `calculate_volume_sma(df, period)`

### MarketRegime (`market_regime.py`)

- Adds `ema_50`, `ema_200`, `adx`.
- Can classify `bullish` / `bearish` / `sideways`.
- Provides strong-bear suppression helper (`should_suppress_entry`) for optional use.

### RiskManager (`risk_manager.py`)

Stateful guardrails:
- Position size cap
- Portfolio allocation cap
- Consecutive-loss gating
- Cooldown tracking
- Daily-loss tracking
- Drawdown circuit breaker tracking

### SlippageProtection (`slippage_protection.py`)

- Computes slippage percent from expected vs actual price.
- Blocks entries when absolute slippage exceeds configured threshold.

## Scripts (`scripts/`)

### Core Python scripts

| Script | Purpose |
|---|---|
| `validate_config.py` | Config schema/value + hardcoded secret detection |
| `validate_env.py` | `.env` validation and config/env consistency checks |
| `daily_report.py` | Daily metrics report (API first, DB fallback) |
| `check_dryrun_criteria.py` | Dry run acceptance evaluation (`PASSED`/`FAILED`/`INCONCLUSIVE`) |
| `diagnose_bot.py` | Health diagnostics (process/API/DB/log/env/trades) |
| `analyze_backtest.py` | Backtest criteria evaluation |
| `monte_carlo.py` | Trade-order Monte Carlo robustness checks |

Execution style (supported):
- Preferred: `python3 -m scripts.<name>`
- Compatible: `python3 scripts/<name>.py`

### Shell scripts

| Script | Purpose |
|---|---|
| `start_dryrun.sh` | Preflight and launch |
| `walk_forward.sh` | IS/OOS/final backtest workflow |
| `download_data.sh` | Historical OHLCV download |
| `backup_db.sh` | SQLite backup + retention cleanup |
| `heartbeat.sh` | Process heartbeat ping |

Current runtime profile:
- Config: `user_data/config/config.dryrun.safe.json`
- Strategy: `DCAStrategyBalanced`

## Test Coverage

Unit tests are under `tests/unit/` and cover strategy modules plus each operational script.

## Related Codemaps

- [architecture.md](./architecture.md)
- [data.md](./data.md)
