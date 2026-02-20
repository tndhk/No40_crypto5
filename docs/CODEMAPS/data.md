# Data Codemap

Last Updated: 2026-02-20
Framework/Runtime: Python 3.11+ / Freqtrade 2026.1

## Active Configuration Profile

Primary runtime config: `user_data/config/config.dryrun.safe.json`

Current key values:
- `max_open_trades`: `2`
- `stake_currency`: `USDT`
- `stake_amount`: `100`
- `dry_run`: `true`
- `dry_run_wallet`: `1000`
- API port: `8081`
- Strategy: `DCAStrategyBalanced`

Configured pair whitelist:
- `BTC/USDT`
- `ETH/USDT`
- `SOL/USDT`
- `XRP/USDT`
- `DOGE/USDT`
- `ADA/USDT`

## Config Validation Rules

`validate_config.py` enforces:
- Required fields: `max_open_trades`, `stake_currency`, `stake_amount`, `dry_run`
- `max_open_trades` must be positive integer
- `stake_amount` must be positive number or `"unlimited"`
- `exchange.pair_whitelist` cannot be empty
- Secret fields must not be hardcoded in JSON

## Secret Handling Model

Secrets are not stored in config files.

Expected runtime overrides:
- `FREQTRADE__TELEGRAM__TOKEN`
- `FREQTRADE__TELEGRAM__CHAT_ID`
- `FREQTRADE__API_SERVER__JWT_SECRET_KEY`
- `FREQTRADE__API_SERVER__WS_TOKEN`
- `FREQTRADE__API_SERVER__PASSWORD`

`validate_env.py` checks both:
- environment variable completeness/placeholder safety
- config vs env consistency for secret fields

## Database Files

| File | Purpose |
|---|---|
| `user_data/tradesv3.dryrun.sqlite` | Primary dry run trade/order state |
| `tradesv3.dryrun.sqlite` | Legacy path (stale snapshot risk) |

Freqtrade-managed tables include `trades` and `orders`.

## Metrics Data Model

### Dry Run criteria

`check_dryrun_criteria.py` evaluates:
- Uptime
- API error rate
- Order accuracy
- Sharpe deviation vs backtest reference
- Days running

Result states:
- `PASSED`
- `FAILED`
- `INCONCLUSIVE` (used when API uptime data is unavailable)

DB path resolution (scripts):
- Prefer `user_data/tradesv3.dryrun.sqlite`
- Fall back to root `tradesv3.dryrun.sqlite`

### Daily report

`daily_report.py` returns:
- `date`
- `uptime_percent`
- `total_trades`
- `daily_pnl`
- `cumulative_pnl`
- `open_positions`
- `api_errors`
- `api_total_calls`

## Environment Variables

### Base application vars

- `TELEGRAM_TOKEN`
- `TELEGRAM_CHAT_ID`
- `JWT_SECRET_KEY`
- `API_PASSWORD`
- `ENVIRONMENT` (`dry_run` or `live`)
- `HEARTBEAT_URL` (optional)
- `BINANCE_API_KEY` / `BINANCE_API_SECRET` (required in live mode)

### API client vars

- `FT_API_URL` (default `http://127.0.0.1:8081`)
- `FT_API_USERNAME` (default `freqtrader`)
- `FT_API_PASSWORD` (optional)

## Related Codemaps

- [architecture.md](./architecture.md)
- [backend.md](./backend.md)
