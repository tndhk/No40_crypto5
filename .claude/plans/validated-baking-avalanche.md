# Phase 5: Dry Run（ペーパートレード） 実装計画

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Phase 4で発見されたバグ修正、RiskManager完全接続、監視インフラ構築を行い、14日間のDry Run実行準備を完了する

**Tech Stack:** Python 3.11, Freqtrade, pytest, bash

---

## 現在の状態（Batch 1完了後）
- 171テスト全PASS、カバレッジ83%
- Batch 0完了: custom_exit修正、RiskManager日次損失/ピークバランス追跡、portfolio_limit接続、backup_db.shパス修正
- Batch 1完了: config.json設定追加、validate_env.py、check_dryrun_criteria.py、daily_report.py、start_dryrun.sh
- Ruffエラーなし、全シェルスクリプト構文正常

---

## [完了] Batch 0: バグ修正とRiskManager完全接続（TDD）

全タスク（0-1〜0-10）完了済み。141テスト全PASS、カバレッジ94%。

---

## [完了] Batch 1: 設定修正とDry Run監視インフラ（TDD）

全タスク（1-1〜1-9）完了済み。171テスト全PASS、カバレッジ83%。

成果物:
- config.json: max_open_trades=2, tradable_balance_ratio, fiat_display_currency, enableRateLimit, 10ペア拡張
- scripts/validate_env.py + tests/unit/test_validate_env.py (10テスト)
- scripts/check_dryrun_criteria.py + tests/unit/test_check_dryrun_criteria.py (12テスト)
- scripts/daily_report.py + tests/unit/test_daily_report.py (8テスト)
- scripts/start_dryrun.sh（プリフライトチェック付き）

---

## Batch 3: 最終検証とコミット

> Batch 2（14日間Dry Run運用）はユーザーが手動で実施するフェーズのため、先にBatch 3でコミットを行う

### タスク3-1: 全テスト実行
```bash
.venv/bin/python -m pytest -v
```

### タスク3-2: カバレッジ確認
```bash
.venv/bin/python -m pytest --cov=user_data/strategies --cov=scripts --cov-report=term-missing
```

### タスク3-3: Ruffリント + シェルスクリプト構文
```bash
.venv/bin/ruff check user_data/strategies/ tests/ scripts/
bash -n scripts/*.sh
```

### タスク3-4: コミット
```bash
git add user_data/strategies/ tests/unit/ scripts/ user_data/config/
git commit -m "feat: Phase 5 Dry Run monitoring infrastructure

- Fix config.json: max_open_trades=2, add tradable_balance_ratio, fiat_display_currency, enableRateLimit, expand pair_whitelist to 10 pairs
- Add validate_env.py: environment variable validation with dry_run mode support
- Add check_dryrun_criteria.py: Dry Run acceptance criteria evaluation (uptime, API error rate, order accuracy, Sharpe deviation, days)
- Add daily_report.py: daily monitoring report generation
- Add start_dryrun.sh: preflight checks and Dry Run launcher
- Tests: 30 new tests (171 total), coverage 83%"
```

---

## Batch 2: Dry Run実行（14日間）- ユーザー手動実施

> このバッチはコミット後にユーザーが手動で実施する

### タスク2-1: プリフライトチェック実行
```bash
./scripts/start_dryrun.sh --preflight-only
```
- .envファイルに正しい値を設定してから実行
- 全チェックPASSを確認

### タスク2-2: Dry Run起動
```bash
./scripts/start_dryrun.sh
```
- Telegram通知の受信確認
- API serverの動作確認: `curl http://127.0.0.1:8080/api/v1/ping`

### タスク2-3: 日次モニタリング（14日間）
```bash
.venv/bin/python scripts/daily_report.py
```
- 毎日実行して稼働率、エラー率、トレード状況を記録

### タスク2-4: Dry Run合格基準チェック
```bash
.venv/bin/python scripts/check_dryrun_criteria.py
```
- 14日経過後に全基準を確認

---

## 合格基準（Batch 3コミット前）
- [x] 全テストPASS（171テスト）
- [x] カバレッジ80%以上（83%）
- [x] Ruffエラーなし
- [x] 全シェルスクリプト構文正常
- [x] custom_exit()バグ修正完了（Batch 0）
- [x] RiskManager全メソッド接続完了（Batch 0）
- [x] backup_db.shパス修正完了（Batch 0）
- [x] config.json設定追加完了（Batch 1）
- [x] 監視スクリプト4本 + テスト完備（Batch 1）
- [x] start_dryrun.sh動作確認（Batch 1）

---

## 検証手順（実装後の確認）
```bash
# 1. 全テスト
.venv/bin/python -m pytest -v

# 2. カバレッジ
.venv/bin/python -m pytest --cov=user_data/strategies --cov=scripts --cov-report=term-missing

# 3. Ruff
.venv/bin/ruff check user_data/strategies/ tests/ scripts/

# 4. シェルスクリプト構文
bash -n scripts/*.sh

# 5. config検証
.venv/bin/python scripts/validate_config.py user_data/config/config.json
```
