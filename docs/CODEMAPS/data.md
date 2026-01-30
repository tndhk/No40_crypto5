# Data Codemap

Last Updated: 2026-01-30
Framework/Runtime: Python 3.11+ / Freqtrade 2024.x

## Configuration Profiles

Four JSON config files in `user_data/config/`:

| File                  | Purpose              | dry_run | max_open_trades | Pairs | Telegram | API Server |
|-----------------------|----------------------|---------|-----------------|-------|----------|------------|
| `config.json`         | Development/Dry Run  | true    | 2               | 10    | Yes      | Yes (8081) |
| `config.backtest.json`| Historical testing   | true    | 6               | 10    | No       | No         |
| `config.hyperopt.json`| Parameter optimization | true  | 2               | 2     | No       | No         |
| `config.live.json`    | Production (live)    | false   | 2               | 2     | Yes      | Yes (8080) |

## Config Schema (Common Fields)

```
{
  // -- Core Trading --
  "max_open_trades": int,           // Max concurrent positions
  "stake_currency": "JPY",          // Always JPY (Binance Japan)
  "stake_amount": float,            // Per-trade stake (JPY)
  "dry_run": bool,                  // Paper trading mode
  "dry_run_wallet": float,          // Simulated balance (dry run only)
  "trading_mode": "spot",           // Spot only (no margin/futures)

  // -- Order Timing --
  "unfilledtimeout": {
    "entry": 10,                    // Cancel unfilled entry after 10 min
    "exit": 10,                     // Cancel unfilled exit after 10 min
    "unit": "minutes"
  },

  // -- Pricing --
  "entry_pricing": {
    "price_side": "same",           // Use same side of order book
    "use_order_book": true,
    "order_book_top": 1             // Best price from order book
  },
  "exit_pricing": { ... },          // Same structure as entry_pricing

  // -- Exchange --
  "exchange": {
    "name": "binance",
    "key": str,                     // API key (empty for dry run)
    "secret": str,                  // API secret (empty for dry run)
    "ccxt_config": {
      "rateLimit": 200,             // 200ms between requests
      "enableRateLimit": true
    },
    "pair_whitelist": [...],        // Allowed trading pairs
    "pair_blacklist": ["BNB/.*"]    // Blocked pairs (regex)
  },

  // -- Strategy --
  "strategy": "DCAStrategy",
  "strategy_path": "user_data/strategies/",

  // -- Order Types --
  "order_types": {
    "entry": "limit",
    "exit": "limit",
    "emergency_exit": "market",
    "stoploss": "market",
    "stoploss_on_exchange": false
  },
  "order_time_in_force": {
    "entry": "GTC",                 // Good Till Cancelled
    "exit": "GTC"
  },

  // -- Custom Risk Parameters (passed to strategy __init__) --
  "max_position_size": 100000,           // JPY - Max single position
  "max_portfolio_allocation": 0.2,       // 20% of total per position
  "daily_loss_limit": 0.05,             // 5% daily loss cap
  "circuit_breaker_drawdown": 0.15,     // 15% drawdown halts trading
  "max_consecutive_losses": 3,           // 3 consecutive stops -> cooldown
  "cooldown_hours": 24,                 // Hours to wait after cooldown trigger
  "max_slippage_percent": 0.5           // 0.5% max price deviation
}
```

## Trading Pairs

Whitelist (Dry Run / Backtest -- 10 pairs):
- BTC/JPY, ETH/JPY, XRP/JPY, ADA/JPY, DOGE/JPY
- DOT/JPY, MATIC/JPY, SOL/JPY, LINK/JPY, UNI/JPY

Whitelist (Hyperopt / Live -- 2 pairs):
- BTC/JPY, ETH/JPY

Blacklist (all configs): BNB/.*

## Historical Data (`user_data/data/binance/`)

Format: Apache Feather (`.feather`)
Source: Binance via `download_data.sh`
Start date: 2024-03-12

| Pair     | Timeframes Available    |
|----------|-------------------------|
| BTC/JPY  | 15m, 1h, 4h, 1d        |
| ETH/JPY  | 15m, 1h, 4h, 1d        |
| XRP/JPY  | 15m, 1h, 4h, 1d        |
| ADA/JPY  | 15m, 1h, 4h, 1d        |
| DOGE/JPY | 15m, 1h, 4h, 1d        |
| SOL/JPY  | 15m, 1h, 4h, 1d        |
| LINK/JPY | 15m, 1h, 4h, 1d        |
| BTC/USDT | 15m (only)              |

DOT/JPY, MATIC/JPY, UNI/JPY data not yet downloaded.

## Database Schema

SQLite databases managed by Freqtrade (not custom schema):

| File                        | Purpose                     |
|-----------------------------|-----------------------------|
| `tradesv3.dryrun.sqlite`   | Dry run trade records       |
| `tradesv3.sqlite`          | Live trade records (future) |

Freqtrade manages these tables internally:
- `trades` -- Open and closed trade records
- `orders` -- Individual order records per trade

Backup: `scripts/backup_db.sh` (daily cron, 30-day retention, gzip compressed)

## Immutable Data Classes

All dataclasses in the project use `frozen=True`:

| Class                 | Module                   | Fields                                                     |
|-----------------------|--------------------------|------------------------------------------------------------|
| `ValidationResult`    | validate_config.py       | is_valid, errors, warnings                                 |
| `EnvValidationResult` | validate_env.py          | valid, errors, warnings                                    |
| `BacktestMetrics`     | analyze_backtest.py      | win_rate, profit_factor, sharpe_ratio, max_drawdown, total_trades, total_profit_pct |
| `CriteriaResult`      | analyze_backtest.py      | passed_minimum, passed_target, details                     |
| `MonteCarloResult`    | monte_carlo.py           | median_profit, ci_95_lower, ci_95_upper, worst_drawdown, best_drawdown, median_drawdown, run_count |
| `DailyMetrics`        | daily_report.py          | date, uptime_percent, total_trades, daily_pnl, cumulative_pnl, open_positions, api_errors, api_total_calls |
| `DryRunMetrics`       | check_dryrun_criteria.py | uptime_percent, api_error_rate, order_accuracy, sharpe_deviation, days_running |
| `DryRunCriteriaResult`| check_dryrun_criteria.py | passed, details                                            |

## Evaluation Criteria

### Backtest Criteria (analyze_backtest.py)

| Metric         | Minimum  | Target   |
|----------------|----------|----------|
| Win Rate       | >= 50%   | >= 55%   |
| Profit Factor  | >= 1.2   | >= 1.5   |
| Sharpe Ratio   | >= 0.5   | >= 0.8   |
| Max Drawdown   | <= 20%   | <= 15%   |
| Total Trades   | >= 30    | >= 50    |

### Dry Run Criteria (check_dryrun_criteria.py)

| Metric           | Threshold  |
|------------------|------------|
| Uptime           | >= 99%     |
| API Error Rate   | < 1%       |
| Order Accuracy   | >= 98%     |
| Sharpe Deviation | <= 0.3     |
| Running Period   | >= 14 days |

## Environment Variables (`.env`)

| Variable            | Required (dry_run) | Required (live) | Purpose                     |
|---------------------|--------------------|-----------------|-----------------------------|
| TELEGRAM_TOKEN      | Yes                | Yes             | Telegram bot notifications  |
| TELEGRAM_CHAT_ID    | Yes                | Yes             | Telegram chat target        |
| JWT_SECRET_KEY      | Yes                | Yes             | API server auth             |
| API_PASSWORD        | Yes                | Yes             | API access control          |
| BINANCE_API_KEY     | No                 | Yes             | Exchange API key            |
| BINANCE_API_SECRET  | No                 | Yes             | Exchange API secret         |
| HEARTBEAT_URL       | Optional           | Optional        | Uptime monitoring endpoint  |
| ENVIRONMENT         | Optional           | Optional        | "dry_run" or "live"         |

## Related Codemaps

- [architecture.md](./architecture.md) -- High-level overview and data flow
- [backend.md](./backend.md) -- Strategy modules and scripts detail
