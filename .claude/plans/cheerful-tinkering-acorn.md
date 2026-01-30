# Codemap発見問題の一括改善計画

## 背景

コードマップ生成時に11件の問題が発見された。セキュリティ/データ整合性/ドキュメントの3カテゴリに分類し、全件を一括対応する。

---

## Phase 1: セキュリティ修正 (CRITICAL / 4件)

### 問題

- config.json(作業ツリー)に5つの秘密情報がハードコード（Telegram token, chat_id, JWT secret, WS token, API password）
- config.jsonは.gitignoreに記載あるが、gitignore追加前にcommit済みのため依然追跡中
- config.live.jsonは.gitignoreに未記載かつgit追跡中
- `${VAR}`プレースホルダーはFreqtradeが解釈しない（独自置換機構もない）

### 解決策: FREQTRADE__環境変数を使用

FreqtradeはFREQTRADE__プレフィクス付き環境変数でconfigの値を上書きする機能を持つ。
例: `FREQTRADE__TELEGRAM__TOKEN=xxx` -> `config["telegram"]["token"]` を上書き

### タスク

#### 1-1. validate_config.pyにハードコード秘密検出を追加 [TDD]

対象: `scripts/validate_config.py`, `tests/unit/test_validate_config.py`

テスト (RED):
- `test_hardcoded_telegram_token_detected` - Telegramトークンのパターン検出
- `test_hardcoded_api_password_detected` - APIパスワード検出
- `test_hardcoded_jwt_secret_detected` - JWT秘密鍵検出
- `test_placeholder_value_passes` - `${...}`パターンはパス
- `test_empty_secret_field_passes` - 空文字列はパス

実装 (GREEN):
- `check_hardcoded_secrets(config) -> tuple[str, ...]` 純粋関数を追加
- 対象フィールド: `telegram.token`, `telegram.chat_id`, `api_server.password`, `api_server.jwt_secret_key`, `api_server.ws_token`, `exchange.key`, `exchange.secret`
- 安全パターン: 空文字列、`${`で始まる、`your_`/`change_this_`で始まる
- `validate_config()`から呼び出し

#### 1-2. validate_env.pyにFREQTRADE__変数チェックとconfig整合性検証を追加 [TDD]

対象: `scripts/validate_env.py`, `tests/unit/test_validate_env.py`

テスト (RED):
- `test_freqtrade_env_vars_present_passes`
- `test_missing_freqtrade_env_vars_warns`
- `test_config_hardcoded_secret_with_env_cross_check_fails`
- `test_empty_config_with_freqtrade_env_override_passes`

実装 (GREEN):
- `validate_config_env_consistency(config, env_vars) -> EnvValidationResult` 関数追加
- FREQTRADE__変数のマッピング定義: `telegram.token` <-> `FREQTRADE__TELEGRAM__TOKEN` 等
- `validate_env()`にFREQTRADE__変数チェックを追加

#### 1-3. .env.exampleにFREQTRADE__変数を追加

対象: `.env.example`

```
# --- Freqtrade Config Overrides ---
FREQTRADE__TELEGRAM__TOKEN=your_telegram_bot_token_here
FREQTRADE__TELEGRAM__CHAT_ID=your_telegram_chat_id_here
FREQTRADE__API_SERVER__JWT_SECRET_KEY=change_this_to_random_string
FREQTRADE__API_SERVER__WS_TOKEN=change_this_to_random_string
FREQTRADE__API_SERVER__PASSWORD=change_this_password
```

#### 1-4. start_dryrun.shに.envのsource処理を追加

対象: `scripts/start_dryrun.sh`

`cd "$PROJECT_ROOT"` の後に追加:
```bash
if [[ -f ".env" ]]; then
    set -a
    source .env
    set +a
    echo "Loaded environment variables from .env"
fi
```

#### 1-5. config.jsonのハードコード秘密情報を空文字列に置換

対象: `user_data/config/config.json`

- `telegram.token`: `""` に変更
- `telegram.chat_id`: `""` に変更
- `api_server.jwt_secret_key`: `""` に変更
- `api_server.ws_token`: `""` に変更
- `api_server.password`: `""` に変更

#### 1-6. config.live.jsonのプレースホルダーを空文字列に統一

対象: `user_data/config/config.live.json`

全ての`${...}`プレースホルダーを空文字列に変更（FREQTRADE__変数で上書きされるため）

#### 1-7. git追跡解除と.gitignore更新

操作:
1. `git rm --cached user_data/config/config.json`
2. `git rm --cached user_data/config/config.live.json`
3. `.gitignore`に`user_data/config/config.live.json`を追加

#### 1-8. ユーザーアクション（手動）

- .envファイルに実際のFREQTRADE__変数値を設定
- ボット再起動: `./scripts/start_dryrun.sh`
- 秘密情報のローテーション推奨（Telegram token, JWT secret, API password）

---

## Phase 2: データ/設定整合性修正 (HIGH / 3件)

### 問題

- DOT/JPY, MATIC/JPY, UNI/JPYがconfig whitelistにあるが履歴データなし（Binance Japanに存在しない可能性）
- download_data.shが存在しないペアをダウンロード試行
- BTC/USDTの孤立データファイル

### タスク

#### 2-1. config.jsonから存在しない3ペアを削除

対象: `user_data/config/config.json`

`pair_whitelist`から`DOT/JPY`, `MATIC/JPY`, `UNI/JPY`を削除 -> 7ペアに

#### 2-2. config.backtest.jsonから存在しない3ペアを削除

対象: `user_data/config/config.backtest.json`

同様に3ペアを削除

#### 2-3. download_data.shのペアリストを更新

対象: `scripts/download_data.sh`

PAIRS配列を7ペアに変更:
```bash
PAIRS=("BTC/JPY" "ETH/JPY" "XRP/JPY" "ADA/JPY" "DOGE/JPY" "SOL/JPY" "LINK/JPY")
```

#### 2-4. 孤立BTC/USDTデータの削除

対象: `user_data/data/binance/BTC_USDT-15m.feather`

ローカルファイル削除（git管理外のためgit操作不要）

---

## Phase 3: ドキュメント/コード整合性修正 (MEDIUM / 4件)

### 問題

- CLAUDE.mdのペア数「7」vs config実態「10」 -> Phase 2完了後は一致
- CLAUDE.mdの「RSI <= 45 + bullish market regime」vs コード実態（regime filter削除済み）
- validate_config.pyに秘密検出なし -> Phase 1で対応済み
- validate_env.pyにconfig整合性チェックなし -> Phase 1で対応済み

### タスク

#### 3-1. CLAUDE.md: エントリーシグナル記述の修正

対象: `CLAUDE.md`

修正箇所:
- "Strategy Module Structure"セクション: `RSI-based oversold detection (RSI <= 30)` -> `RSI-based entry (RSI <= 45) with volume confirmation`
- "Strategy Settings"セクション: `RSI <= 45 (oversold) + bullish market regime` -> `RSI <= 45 (oversold) + volume filter (market regime filter removed for trade frequency)`
- "DCA Levels"セクション: `Initial entry at RSI <= 45 (bullish regime)` -> `Initial entry at RSI <= 45`
- "DCA execution constraint" 行を削除（コードに存在しない制約）

#### 3-2. CLAUDE.md: Secret Management セクションを追加

対象: `CLAUDE.md`

Configuration Files セクションの後に追加:
```
### Secret Management
Secrets are provided via Freqtrade's native FREQTRADE__ environment variable overrides.
Config files contain empty strings for secret fields.
See .env.example for required variables.
```

#### 3-3. docs/CODEMAPS/ の再生成

Phase 1-2の修正完了後、コードマップを再生成して正確な状態を反映。

---

## 実行順序（ボット稼働への影響を最小化）

```
[ボット稼働中 - 影響なし]
  1-1. validate_config.py テスト追加 + 秘密検出実装
  1-2. validate_env.py テスト追加 + 整合性検証実装
  1-3. .env.example 更新
  1-4. start_dryrun.sh に .env source 追加
  2-1. config.backtest.json ペア削除（dry runには影響しない）
  2-3. download_data.sh 更新
  3-1. CLAUDE.md エントリーシグナル修正
  3-2. CLAUDE.md Secret Management セクション追加

[ボット一時停止が必要]
  -> ユーザー: .envにFREQTRADE__変数を設定
  1-5. config.json 秘密情報を空文字列に
  2-1. config.json ペア削除
  -> ユーザー: ./scripts/start_dryrun.sh でボット再起動

[ボット再起動後]
  1-6. config.live.json プレースホルダー統一
  1-7. git rm --cached + .gitignore更新
  2-4. 孤立データ削除
  3-3. コードマップ再生成
```

---

## 修正対象ファイル一覧

| ファイル | 操作 |
|---------|------|
| `scripts/validate_config.py` | 秘密検出関数追加 |
| `tests/unit/test_validate_config.py` | テスト追加 (5件) |
| `scripts/validate_env.py` | FREQTRADE__検証 + 整合性チェック追加 |
| `tests/unit/test_validate_env.py` | テスト追加 (4件) |
| `.env.example` | FREQTRADE__変数セクション追加 |
| `scripts/start_dryrun.sh` | .env source処理追加 |
| `user_data/config/config.json` | 秘密情報削除 + 3ペア削除 |
| `user_data/config/config.backtest.json` | 3ペア削除 |
| `user_data/config/config.live.json` | プレースホルダー統一 |
| `scripts/download_data.sh` | ペアリスト更新 |
| `.gitignore` | config.live.json追加 |
| `CLAUDE.md` | エントリーシグナル + Secret Management修正 |

---

## 検証手順

### テスト実行
```bash
pytest -v tests/unit/test_validate_config.py tests/unit/test_validate_env.py
pytest  # 全テスト + カバレッジ80%以上
```

### セキュリティ検証
```bash
# config.jsonに秘密情報がないことを確認
.venv/bin/python scripts/validate_config.py user_data/config/config.json

# FREQTRADE__変数が.envに設定されていることを確認
.venv/bin/python scripts/validate_env.py

# gitで追跡されていないことを確認
git ls-files user_data/config/config.json    # 空出力
git ls-files user_data/config/config.live.json  # 空出力
```

### ボット動作検証
```bash
# Preflight checkのみ実行（ボット起動しない）
./scripts/start_dryrun.sh --preflight-only

# ボット起動後、Telegram通知が届くことを確認
# API Server応答確認
curl http://127.0.0.1:8081/api/v1/ping
```

### データ整合性検証
```bash
# ペア数が7であることを確認
python -c "import json; c=json.load(open('user_data/config/config.json')); print(len(c['exchange']['pair_whitelist']), 'pairs')"
# 期待: 7 pairs
```
