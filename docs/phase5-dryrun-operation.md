# Phase 5: Dry Run 運用手順（14日間）

開始日: 2026-01-30
完了予定日: 2026-02-13（14日後）

## 現在の稼働状態

- Freqtrade Dry Run: 稼働中
- プロセスID: 確認方法 `ps aux | grep freqtrade`
- API Server: http://127.0.0.1:8081
- Telegram通知: 有効（Chat ID: 8462100859）
- 初期資金: 50,000 JPY
- 取引ペア: 7ペア（BTC/JPY, ETH/JPY, XRP/JPY, ADA/JPY, DOGE/JPY, SOL/JPY, LINK/JPY）

---

## 日次タスク（毎日実行）

### 1. 日次レポート生成

毎日1回実行:
```bash
cd /Users/takahiko_tsunoda/work/dev/No40_Crypto5
.venv/bin/python scripts/daily_report.py
```

記録される内容:
- 稼働率（Uptime）
- APIエラー率
- トレード数
- 日次P&L
- 未決済ポジション数

### 2. Telegram通知確認

以下のイベントで通知が届くことを確認:
- [ ] エントリー注文（entry）
- [ ] エントリー約定（entry_fill）
- [ ] エグジット注文（exit）
- [ ] エグジット約定（exit_fill）
- [ ] ストップロス発動
- [ ] プロテクション発動

### 3. ログ確認（エラーがないか）

```bash
tail -100 user_data/logs/freqtrade.log | grep -i "error\|warning"
```

---

## 週次タスク（毎週実行）

### 1. データベースバックアップ

毎週日曜日実行推奨:
```bash
./scripts/backup_db.sh
```

バックアップ場所: `backups/db_backup_YYYYMMDD_HHMMSS/`

### 2. パフォーマンスレビュー

以下を確認:
- [ ] 総トレード数（最低30トレード目標）
- [ ] 勝率（目標: >= 50%）
- [ ] 平均P&L
- [ ] 最大ドローダウン（目標: <= 20%）

Telegramで `/stats` コマンドを実行、または:
```bash
# API経由で確認
curl http://127.0.0.1:8081/api/v1/stats
```

---

## トラブルシューティング

### ボットが停止した場合

1. プロセス確認:
```bash
ps aux | grep freqtrade
```

2. 再起動:
```bash
./scripts/start_dryrun.sh
```

3. Telegram通知で起動確認

### エラーが頻発する場合

1. ログ詳細確認:
```bash
tail -200 user_data/logs/freqtrade.log
```

2. config.json検証:
```bash
.venv/bin/python scripts/validate_config.py user_data/config/config.json
```

3. 環境変数確認:
```bash
.venv/bin/python scripts/validate_env.py
```

### API Serverが応答しない場合

```bash
curl http://127.0.0.1:8081/api/v1/ping
```

応答なしの場合、ボットを再起動。

---

## 14日後の合格判定（2026-02-13）

### 合格基準チェック

```bash
.venv/bin/python scripts/check_dryrun_criteria.py
```

必須条件:
- [ ] 稼働率 >= 95%
- [ ] APIエラー率 <= 5%
- [ ] 注文精度 >= 98%
- [ ] Sharpe ratio偏差 <= 20%（バックテスト結果との比較）
- [ ] 運用日数 >= 14日

### 合格した場合

Phase 6（本番運用）へ進む準備:
1. Binance Japan APIキー取得（本番用、出金権限なし）
2. config.jsonをlive設定にコピー（config.live.json）
3. 本番資金の入金
4. `dry_run: false` に変更

### 不合格の場合

問題を特定して修正:
- 稼働率低下 → サーバー安定性の改善
- APIエラー多発 → レート制限、ネットワーク確認
- 注文精度低下 → スリッページ設定見直し
- Sharpe偏差大 → ストラテジーパラメータ調整

再度14日間のDry Runを実施。

---

## 有用なコマンド

### Telegramコマンド

ボットとの会話で使用可能:
- `/status` - 現在の取引状況
- `/profit` - 総利益
- `/balance` - ウォレット残高
- `/stats` - 統計情報
- `/daily` - 日次レポート
- `/performance` - ペア別パフォーマンス
- `/help` - コマンド一覧

### データベース確認

```bash
sqlite3 user_data/tradesv3.dryrun.sqlite "SELECT * FROM trades ORDER BY id DESC LIMIT 10;"
```

### リアルタイムログ監視

```bash
tail -f user_data/logs/freqtrade.log
```

---

## 注意事項

1. **Dry Runは本番環境ではありません**
   - 実際の資金は使用されません
   - 取引所への注文は送信されません
   - 価格データは実際のものを使用

2. **プロセスは常時稼働が必要**
   - PCをスリープさせない
   - ネットワーク接続を維持
   - 電源を切らない

3. **データは貴重**
   - 定期的にバックアップ
   - ログファイルは削除しない
   - 14日分の全データが合格判定に必要

4. **問題があれば早めに対処**
   - エラーを放置しない
   - 疑問点があれば調査
   - 必要に応じてストラテジー調整

---

## チェックリスト（印刷用）

### 毎日
- [ ] daily_report.py実行
- [ ] Telegram通知確認
- [ ] エラーログ確認

### 毎週
- [ ] backup_db.sh実行
- [ ] パフォーマンスレビュー
- [ ] トレード記録確認

### 14日後
- [ ] check_dryrun_criteria.py実行
- [ ] 全基準クリア確認
- [ ] Phase 6準備（合格の場合）
