# UnsubscribeError 調査レポート

## 結論（対処不要）

このエラーは Freqtrade + ccxt の既知の動作であり、ボットの取引機能に影響はない。
ユーザー確認済み: 運用中に発生し、自動復旧した。対処は不要。

---

## エラーの全体像

### 発生状況
- 日時: 2026-01-31 06:45:56〜06:46:01（約5秒間に集中）
- 対象: 7ペア中6ペア（LINK, SOL, ADA, XRP, ETH, BTC の /JPY）
- エラー: `ccxt.base.errors.UnsubscribeError: binance ohlcv::{PAIR}::15m`
- 付随エラー: ETH/JPY で `NetworkError`（REST API order book取得失敗、リトライ残4回）

### 根本原因

Binance WebSocket接続のリセットまたは一時的な切断が発生し、以下の連鎖が起きた:

1. BinanceのWebSocketサーバーが接続をリセット（24時間制限、またはネットワーク瞬断）
2. ccxt内部の `clean_unsubscription()` が呼ばれ、保留中のサブスクリプションFutureを `UnsubscribeError` で拒否
3. Freqtradeの `_continuously_async_watch_ohlcv` が `ccxt.BaseError` としてキャッチし、ログ出力
4. watchタスクが終了（"Task finished - done"）
5. 次のキャンドルリフレッシュサイクルで `schedule_ohlcv` が再呼び出しされ、自動的に再サブスクライブ

### なぜ自動復旧するのか

Freqtradeの `ExchangeWS.schedule_ohlcv()` は定期的に呼ばれ、`_klines_watching` に含まれないペアを検出すると新しいwatchタスクを起動する。
WebSocketエラーでwatchタスクが終了しても、次のサイクルで自動的に再起動される。

### 技術詳細

- Freqtrade: 2025.12
- ccxt: 4.5.34
- Python: 3.13
- WebSocket設定: デフォルト有効（`enable_ws` 未指定 = `true`）

#### エラー階層
```
ccxt.base.errors.BaseError
  +-- ExchangeError (取引所エラー)
  +-- OperationFailed > NetworkError (ネットワークエラー)
  +-- UnsubscribeError (サブスクリプション解除エラー) <-- 今回のエラー
```

`UnsubscribeError` は `BaseError` 直下にあり、`ExchangeError` や `NetworkError` とは別系統。
Freqtradeは `except ccxt.BaseError` でキャッチしているため、正しく処理されている。

#### Freqtradeのエラーハンドリング（exchange_ws.py:170-187）
```python
async def _continuously_async_watch_ohlcv(self, pair, timeframe, candle_type):
    try:
        while (pair, timeframe, candle_type) in self._klines_watching:
            data = await self._ccxt_object.watch_ohlcv(pair, timeframe)
            # ... データ処理 ...
    except ccxt.ExchangeClosedByUser:
        logger.debug("Exchange connection closed by user")
    except ccxt.BaseError:
        logger.exception(...)  # <-- UnsubscribeError はここでキャッチ
    finally:
        self._klines_watching.discard(...)  # ペアを監視リストから除外
```

リトライロジックはないが、上位の `schedule_ohlcv` が再スケジュールする仕組み。

### Phase 5 Dry Runへの影響

- 取引への影響: なし（自動復旧済み）
- API error rate: このエラーは一時的であり、5%閾値に影響する可能性は低い
- Uptime: ボットプロセス自体は継続動作しているため、95%閾値への影響なし

### 今後の監視ポイント

- このエラーが頻発する場合（1時間に複数回など）、Binance側のネットワーク不安定の兆候
- `NetworkError` のリトライ（4回）が全て失敗する場合、APIアクセス自体に問題がある可能性
- 長時間WebSocketが復旧しない場合のみ、`enable_ws: false` を検討

---

## 実装不要

調査のみの依頼のため、コード変更は行わない。
