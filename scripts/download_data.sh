#!/usr/bin/env bash
set -euo pipefail

# データダウンロードスクリプト
# BTC/JPY, ETH/JPYの履歴データを取得

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

log "Starting data download..."

# ペアのリスト（config.backtest.jsonと同期）
PAIRS=("BTC/JPY" "ETH/JPY" "XRP/JPY" "ADA/JPY" "DOGE/JPY" "SOL/JPY" "LINK/JPY")

# 時間足のリスト
TIMEFRAMES=("15m" "1h" "4h" "1d")

# 開始日（YYYYMMDD形式）
# JPYペアの最古データは2024年3月12日から
START_DATE="20240312"

# 現在日を取得
END_DATE=$(date '+%Y%m%d')

cd "$PROJECT_ROOT"

# 仮想環境のfreqtradeコマンドを使用
FREQTRADE_CMD="$PROJECT_ROOT/.venv/bin/freqtrade"

for PAIR in "${PAIRS[@]}"; do
    for TIMEFRAME in "${TIMEFRAMES[@]}"; do
        log "Downloading $PAIR $TIMEFRAME data from $START_DATE to $END_DATE"

        "$FREQTRADE_CMD" download-data \
            --exchange binance \
            --pairs "$PAIR" \
            --timeframes "$TIMEFRAME" \
            --timerange "${START_DATE}-${END_DATE}" \
            --prepend \
            --config user_data/config/config.json \
            --datadir user_data/data/binance || {
                log "ERROR: Failed to download $PAIR $TIMEFRAME"
                continue
            }

        log "Successfully downloaded $PAIR $TIMEFRAME"
    done
done

log "Data download completed"
