#!/usr/bin/env bash
set -euo pipefail

# ハートビート監視スクリプト（NFR-011）
# Freqtradeプロセスの稼働確認とUptimeRobotへの通知
# cron設定例: */5 * * * * /path/to/heartbeat.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 環境変数を読み込み
if [ -f "$PROJECT_ROOT/.env" ]; then
    # shellcheck disable=SC1090,SC1091
    source "$PROJECT_ROOT/.env"
fi

# HEARTBEAT_URLが設定されているか確認
if [ -z "${HEARTBEAT_URL:-}" ]; then
    echo "ERROR: HEARTBEAT_URL not set in .env" >&2
    exit 1
fi

# Freqtradeプロセスが稼働しているか確認
if pgrep -f "freqtrade trade" > /dev/null; then
    # プロセスが稼働中 - ハートビートを送信
    curl -fsS --retry 3 "$HEARTBEAT_URL" > /dev/null || {
        echo "WARNING: Failed to send heartbeat" >&2
        exit 1
    }
else
    echo "WARNING: Freqtrade process not running" >&2
    exit 1
fi
