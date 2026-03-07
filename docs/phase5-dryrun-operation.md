# Phase 5: Dry Run 運用手順（Docker運用）

開始日: 2026-01-30
更新日: 2026-03-07

## 事前準備

監視スクリプト実行用依存をインストール:
```bash
python3 -m pip install -e .
```

## 現在の稼働状態（確認方法）

- コンテナ状態:
```bash
docker ps --filter name=freqtrade
```
- API Server: `http://127.0.0.1:8081`
- 設定: `user_data/config/config.dryrun.safe.json`
- 戦略: `DCAStrategyBalanced`
- モード: `dry_run: true`
- 1トレードあたり: `stake_amount = 100 USDT`
- 同時建玉上限: `max_open_trades = 2`
- クールダウン: `12 hours` after any losing trade
- DCA: disabled for the current recovery profile
- 取引ペア: 6ペア（BTC/USDT, ETH/USDT, SOL/USDT, XRP/USDT, DOGE/USDT, ADA/USDT）

---

## 起動・停止

### 起動（Preflight付き）
```bash
./scripts/start_dryrun.sh
```

### 起動（safeプロファイル / 現行推奨）
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

### Preflightのみ
```bash
./scripts/start_dryrun.sh --preflight-only
```

### 停止
```bash
docker stop freqtrade
```

---

## 日次タスク（毎日）

### 1. 日次レポート
```bash
python3 scripts/daily_report.py
```

### 2. 稼働ログ確認
```bash
docker logs --tail 200 freqtrade
```

### 3. 直近エラー確認
```bash
docker logs --tail 500 freqtrade | grep -i "error\|warning"
```

---

## API確認（認証あり）

`.env` の API パスワードを利用してトークン発行:

```bash
set -a; source .env; set +a
TOKEN=$(curl -sS -u "freqtrader:${FREQTRADE__API_SERVER__PASSWORD}" -X POST \
  http://127.0.0.1:8081/api/v1/token/login | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p')
```

疎通確認:
```bash
curl -sS http://127.0.0.1:8081/api/v1/ping
```

主要メトリクス:
```bash
curl -sS -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8081/api/v1/profit
curl -sS -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8081/api/v1/status
curl -sS -H "Authorization: Bearer $TOKEN" "http://127.0.0.1:8081/api/v1/logs?limit=300"
```

---

## 週次タスク

### 1. データバックアップ
```bash
./scripts/backup_db.sh
```

### 2. パフォーマンスレビュー
- 総トレード数
- 勝率
- 実現損益
- 最大ドローダウン
- `stop_loss` 比率
- 1トレード平均損益

---

## 合格判定

```bash
python3 scripts/check_dryrun_criteria.py
```

判定時は `Data source`（API/Database）を必ず確認し、`Database` の場合は表示される `Database path` が想定どおりか確認する。

---

## トラブルシューティング

### ボット停止時
1. `docker ps --filter name=freqtrade`
2. `docker logs --tail 200 freqtrade`
3. `./scripts/start_dryrun.sh`

### API認証エラー時
1. `.env` の `FREQTRADE__API_SERVER__PASSWORD` を確認
2. `docker restart freqtrade`
3. 再度トークン発行

### 実行エラー頻発時
1. `docker logs --tail 1000 freqtrade`
2. `python3 scripts/validate_config.py user_data/config/config.dryrun.safe.json`
3. `python3 scripts/validate_env.py`

### `docker-compose up` が失敗する場合（`KeyError: 'ContainerConfig'`）
1. 既存コンテナを削除: `docker rm -f freqtrade`
2. 本ドキュメントの `起動（safeプロファイル / 現行推奨）` を実行
