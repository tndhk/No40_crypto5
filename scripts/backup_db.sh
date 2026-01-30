#!/usr/bin/env bash
set -euo pipefail

# データベースバックアップスクリプト（NFR-012）
# tradesv3.sqlite/tradesv3.dryrun.sqliteをバックアップ
# cron設定例: 0 3 * * * /path/to/backup_db.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# バックアップディレクトリ
BACKUP_DIR="$PROJECT_ROOT/backups/db"
mkdir -p "$BACKUP_DIR"

# 保持期間（日）
RETENTION_DAYS=30

# タイムスタンプ
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

# データベースファイルのリスト
DB_FILES=(
    "$PROJECT_ROOT/user_data/tradesv3.sqlite"
    "$PROJECT_ROOT/user_data/tradesv3.dryrun.sqlite"
)

for DB_FILE in "${DB_FILES[@]}"; do
    if [ -f "$DB_FILE" ]; then
        DB_NAME=$(basename "$DB_FILE")
        BACKUP_FILE="$BACKUP_DIR/${DB_NAME%.sqlite}_${TIMESTAMP}.sqlite"

        log "Backing up $DB_NAME to $BACKUP_FILE"

        # SQLiteデータベースをバックアップ
        sqlite3 "$DB_FILE" ".backup '$BACKUP_FILE'" || {
            log "ERROR: Failed to backup $DB_NAME"
            continue
        }

        # バックアップファイルを圧縮
        gzip "$BACKUP_FILE" || {
            log "WARNING: Failed to compress $BACKUP_FILE"
        }

        log "Successfully backed up $DB_NAME"
    else
        log "INFO: $DB_FILE not found, skipping"
    fi
done

# 古いバックアップを削除
log "Cleaning up old backups (older than $RETENTION_DAYS days)"
find "$BACKUP_DIR" -name "*.sqlite.gz" -mtime +$RETENTION_DAYS -delete || {
    log "WARNING: Failed to clean up old backups"
}

log "Backup completed"
