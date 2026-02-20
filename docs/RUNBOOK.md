# Runbook

Last Updated: 2026-02-20

Operational runbook for the Crypto DCA Trading Bot.

## System Overview

### Components

| Component | Technology | Port/Location |
|-----------|-----------|---------------|
| Trading Bot | Freqtrade 2026.1 (Python 3.11+) | Foreground process / container |
| API Server | Freqtrade built-in API | http://127.0.0.1:8081 |
| Database | SQLite | `tradesv3.dryrun.sqlite` |
| Notifications | Telegram Bot API | via `FREQTRADE__TELEGRAM__*` |
| Monitoring | `heartbeat.sh`, `daily_report.py`, `diagnose_bot.py` | local scripts |
| Exchange | Binance Spot (USDT pairs) | CCXT |

### Current Dry Run Profile

- Mode: `dry_run`
- Stake currency: `USDT`
- Runtime config: `user_data/config/config.dryrun.safe.json`
- Stake amount: `100`
- Dry run wallet: `1000`
- Max open trades: `2`
- Pairs: `BTC/USDT`, `ETH/USDT`, `SOL/USDT`, `XRP/USDT`, `DOGE/USDT`, `ADA/USDT`
- Timeframe: `15m`
- Strategy: `DCAStrategyBalanced`

### Strategy Parameters (from `DCAStrategyBalanced`)

| Parameter | Value |
|-----------|-------|
| Entry signal | `RSI <= 45`, `volume > 0.9 * volume_sma_20`, `ema_50 >= ema_200`, `adx >= 18` |
| Stoploss | `-8%` |
| Trailing stop | `+0.8%` with `+2%` offset |
| DCA thresholds | `-2%`, `-4%`, `-6%` (defaults) |
| Partial take-profit | `33%` at `+8%` |
| Exit signal | `RSI >= 64` or (`RSI >= 58` and `close < ema_50`) |
| Minimal ROI | `3.5%` at 0, `1.8%` at 120 candles, `0.8%` at 360 candles |

## Secret Management

Use layered secret handling:

1. `user_data/config/config.dryrun.safe.json`: secret fields must be empty strings.
2. `.env`: local secret values.
3. `FREQTRADE__*` env vars: runtime overrides (recommended).

Required runtime overrides:
- `FREQTRADE__TELEGRAM__TOKEN`
- `FREQTRADE__TELEGRAM__CHAT_ID`
- `FREQTRADE__API_SERVER__JWT_SECRET_KEY`
- `FREQTRADE__API_SERVER__WS_TOKEN`
- `FREQTRADE__API_SERVER__PASSWORD`

## Deployment Procedures

### Preflight Checklist

- Virtual environment active.
- `python3 -m scripts.validate_env` passes.
- `python3 -m scripts.validate_config user_data/config/config.dryrun.safe.json` passes.
- Secret fields in config are empty.
- `FREQTRADE__*` vars are provided in runtime environment.
- `freqtrade --version` works.
- `user_data/strategies/dca_strategy_balanced.py` exists.

### Start Dry Run

Recommended:

```bash
./scripts/start_dryrun.sh
```

Preflight only:

```bash
./scripts/start_dryrun.sh --preflight-only
```

Manual start (recommended current profile):

```bash
docker run -d --name freqtrade --restart unless-stopped \
  -v "$PWD/user_data:/freqtrade/user_data" \
  -p 127.0.0.1:8081:8081 \
  --env-file .env \
  -e ENVIRONMENT=dry_run \
  freqtradeorg/freqtrade:stable \
  trade --config /freqtrade/user_data/config/config.dryrun.safe.json \
  --strategy DCAStrategyBalanced
```

### Stop Bot

```bash
docker stop freqtrade
```

## Monitoring

### Health Checks

```bash
curl http://127.0.0.1:8081/api/v1/ping
pgrep -af "freqtrade trade"
```

### Daily Operations

```bash
python3 -m scripts.daily_report
python3 -m scripts.diagnose_bot
```

### Dry Run Acceptance Evaluation

```bash
python3 -m scripts.check_dryrun_criteria
```

Interpretation:
- `PASSED`: all acceptance criteria met.
- `FAILED`: one or more criteria failed.
- `INCONCLUSIVE`: API metrics unavailable (typically DB fallback); rerun when API is reachable.

### Logs

Primary log path is discovered from `user_data/logs/freqtrade*.log`.
If no matching file exists, checks fall back to `user_data/logs/freqtrade.log`.

## Troubleshooting

### API unreachable

1. Confirm process is running.
2. Check port exposure/conflicts on `8081`.
3. Verify API secrets are set via `FREQTRADE__API_SERVER__*`.
4. Run diagnostics:

```bash
python3 -m scripts.diagnose_bot
```

### Config/Env validation failures

```bash
python3 -m scripts.validate_config user_data/config/config.dryrun.safe.json
python3 -m scripts.validate_env
```

### Database issues

```bash
sqlite3 user_data/tradesv3.dryrun.sqlite "PRAGMA integrity_check;"
./scripts/backup_db.sh
```

## Maintenance

### Suggested Cron

```cron
*/5 * * * * /path/to/project/scripts/heartbeat.sh >> /tmp/heartbeat.log 2>&1
0 9 * * * cd /path/to/project && python3 -m scripts.daily_report >> user_data/logs/daily_report.log 2>&1
0 3 * * 0 /path/to/project/scripts/backup_db.sh >> /tmp/backup.log 2>&1
```

### Data refresh

```bash
./scripts/download_data.sh
```
