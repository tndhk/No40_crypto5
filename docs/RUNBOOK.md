# Runbook

Last Updated: 2026-01-30

Operational runbook for the Crypto DCA Trading Bot. Covers deployment, monitoring, troubleshooting, and rollback procedures.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Deployment Procedures](#deployment-procedures)
3. [Monitoring](#monitoring)
4. [Troubleshooting](#troubleshooting)
5. [Rollback Procedures](#rollback-procedures)
6. [Incident Response](#incident-response)
7. [Maintenance Tasks](#maintenance-tasks)
8. [Phase Transitions](#phase-transitions)

---

## System Overview

### Components

| Component | Technology | Port/Location |
|-----------|-----------|---------------|
| Trading Bot | Freqtrade 2024.x | Foreground process |
| API Server | Freqtrade built-in (Flask/uvicorn) | http://127.0.0.1:8081 |
| Database | SQLite | tradesv3.dryrun.sqlite (dry run) / tradesv3.sqlite (live) |
| Notifications | Telegram Bot API | Chat ID configured in .env |
| Monitoring | heartbeat.sh + UptimeRobot | HEARTBEAT_URL in .env |
| Exchange | Binance Japan via CCXT | API rate limit: 200ms/request |

### Current Operating State (Phase 5)

- Mode: Dry Run (paper trading)
- Initial Capital: 50,000 JPY
- Trading Pairs: BTC/JPY, ETH/JPY, XRP/JPY, ADA/JPY, DOGE/JPY, SOL/JPY, LINK/JPY
- Timeframe: 15m
- Max Open Trades: 3
- API Server: http://127.0.0.1:8081

### Strategy Parameters

| Parameter | Value |
|-----------|-------|
| Entry signal | RSI <= 45 + bullish market regime |
| Stoploss | -20% |
| Trailing stop | +2% trail after +5% profit |
| DCA Level 2 | -7% drawdown (1.25x multiplier) |
| DCA Level 3 | -12% drawdown (1.50x multiplier) |
| DCA Level 4 | -18% drawdown (1.75x multiplier) |
| Minimal ROI | 15% immediate, 10% after 45h, 5% after 90h |

---

## Deployment Procedures

### Pre-deployment Checklist

Before starting the bot in any mode:

- [ ] Virtual environment activated: `source .venv/bin/activate`
- [ ] Environment variables set: `.venv/bin/python scripts/validate_env.py`
- [ ] Configuration valid: `.venv/bin/python scripts/validate_config.py user_data/config/config.json`
- [ ] Freqtrade installed: `.venv/bin/freqtrade --version`
- [ ] Strategy file exists: `user_data/strategies/dca_strategy.py`
- [ ] All tests pass: `pytest`
- [ ] Network connectivity to Binance Japan confirmed

### Starting Dry Run (Phase 5)

Recommended method using the launcher script with preflight checks:

```bash
cd /Users/takahiko_tsunoda/work/dev/No40_Crypto5
./scripts/start_dryrun.sh
```

The script runs 5 preflight checks automatically:
1. Environment variable validation
2. Config.json validation
3. Freqtrade installation check
4. Database directory check
5. Strategy file check

To run preflight checks without starting the bot:

```bash
./scripts/start_dryrun.sh --preflight-only
```

Manual start (bypasses preflight checks -- not recommended):

```bash
.venv/bin/freqtrade trade --config user_data/config/config.json --strategy DCAStrategy
```

### Starting Live Trading (Phase 6 -- Future)

Prerequisites specific to live mode:
- [ ] Dry Run passed all acceptance criteria (14+ days)
- [ ] Binance API key with spot-only permissions, no withdrawal
- [ ] IP restriction enabled on Binance API key
- [ ] config.live.json reviewed and validated
- [ ] ENVIRONMENT=live in .env
- [ ] BINANCE_API_KEY and BINANCE_API_SECRET set to live keys

```bash
.venv/bin/freqtrade trade --config user_data/config/config.live.json --strategy DCAStrategy
```

### Stopping the Bot

The bot runs in the foreground. To stop:

1. Press Ctrl+C in the terminal running the bot
2. Or find and terminate the process:

```bash
ps aux | grep freqtrade
kill <PID>
```

Telegram will send a shutdown notification upon graceful stop.

---

## Monitoring

### Health Checks

#### API Server Ping

```bash
curl http://127.0.0.1:8081/api/v1/ping
```

Expected response: `{"status":"pong"}`

#### Process Check

```bash
ps aux | grep "freqtrade trade"
```

#### Heartbeat Monitoring

The heartbeat script checks process status and pings UptimeRobot:

```bash
./scripts/heartbeat.sh
```

Cron setup for every 5 minutes:

```cron
*/5 * * * * /Users/takahiko_tsunoda/work/dev/No40_Crypto5/scripts/heartbeat.sh
```

### Daily Monitoring Tasks

1. Generate daily report:

```bash
.venv/bin/python scripts/daily_report.py
```

Reports: uptime percentage, API error rate, trade count, daily P&L, cumulative P&L, open positions.

2. Check error logs:

```bash
tail -100 user_data/logs/freqtrade.log | grep -i "error\|warning"
```

3. Verify Telegram notifications are being received for:
   - Entry orders and fills
   - Exit orders and fills
   - Stoploss triggers
   - Protection activations

### Weekly Monitoring Tasks

1. Database backup:

```bash
./scripts/backup_db.sh
```

Backups stored in `backups/db/` with gzip compression, 30-day retention.

2. Performance review via Telegram `/stats` command or API:

```bash
curl http://127.0.0.1:8081/api/v1/stats
curl http://127.0.0.1:8081/api/v1/balance
```

3. Review trade history:

```bash
sqlite3 tradesv3.dryrun.sqlite "SELECT * FROM trades ORDER BY id DESC LIMIT 10;"
```

### Real-time Log Monitoring

```bash
tail -f user_data/logs/freqtrade.log
```

### Telegram Commands

| Command | Description |
|---------|-------------|
| /status | Current open trade status |
| /profit | Total accumulated profit |
| /balance | Wallet balance |
| /stats | Trading statistics summary |
| /daily | Daily performance summary |
| /performance | Performance breakdown by pair |
| /help | List all available commands |

### Key Metrics to Track

| Metric | Minimum | Target | Alarm Threshold |
|--------|---------|--------|-----------------|
| Uptime | 95% | 99%+ | < 90% |
| API error rate | <= 5% | < 1% | > 10% |
| Order accuracy | >= 98% | 100% | < 95% |
| Max drawdown | <= 20% | <= 15% | > 25% |
| Sharpe deviation (vs backtest) | <= 20% | <= 10% | > 30% |

---

## Troubleshooting

### Bot Not Running / Crashed

Symptom: No process found, no Telegram updates.

```bash
# 1. Check process
ps aux | grep freqtrade

# 2. Check last log entries
tail -50 user_data/logs/freqtrade.log

# 3. Run preflight checks
./scripts/start_dryrun.sh --preflight-only

# 4. Restart
./scripts/start_dryrun.sh
```

### API Server Not Responding

Symptom: `curl http://127.0.0.1:8081/api/v1/ping` returns connection refused.

```bash
# 1. API server runs within the Freqtrade process
#    If bot is running but API is not responding, check port conflict
lsof -i :8081

# 2. Verify API is enabled in config.json
#    "api_server": { "enabled": true, "listen_port": 8081 }

# 3. Restart the bot
kill <freqtrade_pid>
./scripts/start_dryrun.sh
```

### Configuration Errors

Symptom: Bot fails to start with config-related error.

```bash
# 1. Validate config
.venv/bin/python scripts/validate_config.py user_data/config/config.json

# 2. Validate environment
.venv/bin/python scripts/validate_env.py

# 3. Check for JSON syntax errors
python -m json.tool user_data/config/config.json > /dev/null
```

### Exchange Connection Issues

Symptom: Errors about exchange timeout, rate limiting, or network.

```bash
# 1. Check network connectivity
curl -s https://api.binance.com/api/v3/ping

# 2. Review rate limiting in logs
tail -200 user_data/logs/freqtrade.log | grep -i "rate\|timeout\|connection"

# 3. Config enforces 200ms per request (Binance compliance)
#    If errors persist, increase ccxt_sync_config.rateLimit in config
```

### Database Corruption

Symptom: SQLite errors in logs, trade data missing.

```bash
# 1. Check database integrity
sqlite3 tradesv3.dryrun.sqlite "PRAGMA integrity_check;"

# 2. If corrupted, restore from backup
ls -la backups/db/

# 3. Decompress latest backup
gunzip backups/db/tradesv3.dryrun_<timestamp>.sqlite.gz

# 4. Replace corrupted database (stop bot first)
cp backups/db/tradesv3.dryrun_<timestamp>.sqlite tradesv3.dryrun.sqlite
```

### Telegram Notifications Not Working

Symptom: No messages in Telegram chat.

```bash
# 1. Verify token and chat ID in .env
.venv/bin/python scripts/validate_env.py

# 2. Test Telegram API directly
curl "https://api.telegram.org/bot<TOKEN>/sendMessage?chat_id=<CHAT_ID>&text=test"

# 3. Check logs for Telegram errors
tail -200 user_data/logs/freqtrade.log | grep -i "telegram"
```

### High API Error Rate

Symptom: check_dryrun_criteria.py reports API error rate above threshold.

```bash
# 1. Identify error types in logs
tail -500 user_data/logs/freqtrade.log | grep -i "error" | sort | uniq -c | sort -rn

# 2. Common causes:
#    - Binance maintenance (check Binance status page)
#    - Rate limiting (reduce request frequency)
#    - Network instability (check ISP/router)
#    - API key expiration (regenerate on Binance)
```

### Insufficient Trade Frequency

Symptom: Very few trades generated during Dry Run.

This is a known characteristic of the current strategy. Entry requires RSI <= 45 in a bullish market regime, which is relatively restrictive.

Potential adjustments (requires backtesting validation):
- Loosen RSI threshold
- Add alternative entry signals
- Review market regime filter sensitivity

---

## Rollback Procedures

### Rollback Strategy Parameters

If a strategy change causes degraded performance:

1. Stop the bot: Ctrl+C or `kill <PID>`
2. Revert strategy file to previous version:

```bash
git log --oneline user_data/strategies/dca_strategy.py
git checkout <commit_hash> -- user_data/strategies/dca_strategy.py
```

3. Restart: `./scripts/start_dryrun.sh`

### Rollback Configuration

```bash
# View config history
git log --oneline user_data/config/config.json.example

# Restore previous config example
git checkout <commit_hash> -- user_data/config/config.json.example
cp user_data/config/config.json.example user_data/config/config.json
# Edit config.json to add actual API keys/secrets
```

### Rollback Database

```bash
# 1. Stop the bot
kill <PID>

# 2. List available backups
ls -la backups/db/

# 3. Restore from backup
gunzip -k backups/db/tradesv3.dryrun_<timestamp>.sqlite.gz
cp backups/db/tradesv3.dryrun_<timestamp>.sqlite tradesv3.dryrun.sqlite

# 4. Restart
./scripts/start_dryrun.sh
```

### Full Rollback (Code + Config + Database)

```bash
# 1. Stop the bot
kill <PID>

# 2. Revert all code to a known-good commit
git log --oneline
git checkout <known_good_commit>

# 3. Restore database backup
gunzip -k backups/db/tradesv3.dryrun_<timestamp>.sqlite.gz
cp backups/db/tradesv3.dryrun_<timestamp>.sqlite tradesv3.dryrun.sqlite

# 4. Validate and restart
.venv/bin/python scripts/validate_env.py
.venv/bin/python scripts/validate_config.py user_data/config/config.json
./scripts/start_dryrun.sh
```

---

## Incident Response

### Severity Levels

| Level | Definition | Response Time | Examples |
|-------|-----------|--------------|----------|
| P1 - Critical | Financial risk or data loss | Immediate | Live trading anomaly, database corruption, security breach |
| P2 - High | Service degraded | < 1 hour | Bot crashed, API server down, exchange connection lost |
| P3 - Medium | Non-critical issue | < 4 hours | Telegram not working, high error rate, missed heartbeat |
| P4 - Low | Informational | Next business day | Log warnings, suboptimal performance metrics |

### P1 Response Procedure (Critical)

1. STOP THE BOT IMMEDIATELY: `kill $(pgrep -f "freqtrade trade")`
2. Check for open positions: `sqlite3 tradesv3.dryrun.sqlite "SELECT * FROM trades WHERE is_open=1;"`
3. Assess damage (review logs, database, account balance)
4. Notify stakeholders
5. Follow rollback procedures if needed
6. Document incident and root cause

### P2 Response Procedure (High)

1. Check logs: `tail -200 user_data/logs/freqtrade.log`
2. Run diagnostics: `./scripts/start_dryrun.sh --preflight-only`
3. Restart if preflight passes: `./scripts/start_dryrun.sh`
4. Monitor closely for 1 hour after restart
5. Document incident

### Security Incident

If API keys may be compromised:

1. Immediately disable/delete API key on Binance Japan
2. Stop the bot
3. Rotate all secrets in .env (JWT_SECRET_KEY, API_PASSWORD)
4. Generate new API key on Binance with same restrictions (spot only, no withdrawal, IP restriction)
5. Update .env with new credentials
6. Review git history for accidental secret commits
7. Restart and verify

---

## Maintenance Tasks

### Cron Schedule

| Schedule | Task | Command |
|----------|------|---------|
| Every 5 min | Heartbeat | `./scripts/heartbeat.sh` |
| Daily | Performance report | `.venv/bin/python scripts/daily_report.py` |
| Weekly (Sunday 3am) | Database backup | `./scripts/backup_db.sh` |

Example crontab:

```cron
*/5 * * * * /Users/takahiko_tsunoda/work/dev/No40_Crypto5/scripts/heartbeat.sh >> /tmp/heartbeat.log 2>&1
0 9 * * * cd /Users/takahiko_tsunoda/work/dev/No40_Crypto5 && .venv/bin/python scripts/daily_report.py >> user_data/logs/daily_report.log 2>&1
0 3 * * 0 /Users/takahiko_tsunoda/work/dev/No40_Crypto5/scripts/backup_db.sh >> /tmp/backup.log 2>&1
```

### Historical Data Updates

Download fresh OHLCV data before running backtests:

```bash
./scripts/download_data.sh
```

Downloads 10 pairs across 4 timeframes (15m, 1h, 4h, 1d) from 2024-03-12 to present.

### Log Rotation

Freqtrade manages its own log rotation. Monitor log size:

```bash
ls -lh user_data/logs/freqtrade.log
```

If manual rotation is needed:

```bash
mv user_data/logs/freqtrade.log user_data/logs/freqtrade.log.$(date +%Y%m%d)
# Bot will create a new log file on next startup
```

### Dependency Updates

```bash
source .venv/bin/activate
pip install --upgrade -e ".[dev]"
freqtrade --version
pytest  # Verify nothing broke
```

---

## Phase Transitions

### Phase 5 (Dry Run) -> Phase 6 (Live)

Acceptance criteria (evaluated by `scripts/check_dryrun_criteria.py`):

| Criterion | Threshold |
|-----------|-----------|
| Uptime | >= 99% |
| API error rate | < 1% |
| Order accuracy | >= 98% |
| Sharpe ratio deviation (vs backtest) | <= 0.3 |
| Running period | >= 14 days |

Transition steps:

1. Run acceptance evaluation:

```bash
.venv/bin/python scripts/check_dryrun_criteria.py
```

2. If all criteria pass:
   - Create production API key on Binance Japan (spot only, no withdrawal, IP restricted)
   - Copy and customize live config: review `user_data/config/config.live.json`
   - Update .env: ENVIRONMENT=live, set production API credentials
   - Start with minimum capital allocation
   - Monitor intensively for first 48 hours

3. If criteria fail:
   - Identify root cause from logs and reports
   - Address issues (stability, strategy parameters, infrastructure)
   - Restart 14-day Dry Run cycle

### Emergency Revert (Live -> Dry Run)

```bash
# 1. Stop live trading immediately
kill $(pgrep -f "freqtrade trade")

# 2. Switch back to dry_run in .env
# ENVIRONMENT=dry_run

# 3. Start dry run
./scripts/start_dryrun.sh
```

---

Generated from codebase on 2026-01-30.
