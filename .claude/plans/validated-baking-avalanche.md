# Phase 2: DCA戦略のコア実装（TDD）実装計画

## 概要
要件定義書と実装ガイドに基づき、DCA戦略のコア機能をテスト駆動開発（TDD）で実装する。

## 現在の進捗状況

### 完了済みタスク
- [x] Phase 1: プロジェクト構造の作成
  - ディレクトリ構造作成（user_data/strategies/, tests/unit/等）
  - pyproject.toml, .gitignore, tests/conftest.py作成
  - Python仮想環境作成、依存関係インストール
- [x] タスク1: テクニカル指標モジュール（TDD完了）
  - tests/unit/test_indicators.py（6テスト）
  - user_data/strategies/indicators.py（EMA, RSI, ボリンジャーバンド, 出来高SMA）
  - 検証結果: 6 passed

### 残りのタスク
- [ ] タスク2: リスク管理モジュール
- [ ] タスク3: DCA戦略コア
- [ ] タスク4: 市場環境判定モジュール
- [ ] タスク5: スリッページ保護モジュール
- [ ] タスク6: DCA戦略への新機能統合
- [ ] タスク7: Hyperoptパラメータ化
- [ ] タスク8: テストカバレッジ確認
- [ ] タスク9: コミット

## 実装方針
TDDアプローチを採用:
1. RED: 失敗するテストを書く
2. GREEN: テストが通る最小実装
3. REFACTOR: リファクタリング

## 次のバッチ: タスク2-4の実装

### タスク2: リスク管理モジュール（TDD）
**目的**: トレーディングリスクを管理する機能の実装

**TDDサイクル**:
1. RED: `tests/unit/test_risk_manager.py`を作成（7テストケース）
   - test_max_position_size_check: 最大ポジションサイズチェック
   - test_portfolio_allocation_limit: ポートフォリオ配分制限
   - test_daily_loss_limit: 1日の損失上限チェック
   - test_circuit_breaker_on_drawdown: ドローダウンでのサーキットブレーカー
   - test_consecutive_loss_protection: 連続損失プロテクション
   - test_cooldown_after_stoploss: ストップロス後のクールダウン

2. GREEN: `user_data/strategies/risk_manager.py`を実装
   - RiskManagerクラス
   - check_position_size(), check_portfolio_limit()
   - check_daily_loss_limit(), check_circuit_breaker()
   - check_consecutive_losses(), check_cooldown()

3. REFACTOR: 必要に応じてリファクタリング

**参照**: 実装ガイド Step 2-3, 2-4

---

### タスク3: DCA戦略コア（TDD）
**目的**: Freqtrade IStrategyを継承したDCA戦略の実装

**TDDサイクル**:
1. RED: `tests/unit/test_dca_strategy.py`を作成
   - TestDCAStrategyEntrySignal: エントリーシグナルテスト
   - TestDCAStrategyCustomStakeAmount: カスタムステーク額テスト
   - TestDCAStrategyPositionAdjustment: DCA追加購入テスト
   - TestDCAStrategyExitSignal: エグジットシグナルテスト

2. GREEN: `user_data/strategies/dca_strategy.py`を実装
   - DCAStrategyクラス（IStrategy継承）
   - populate_indicators(), populate_entry_trend(), populate_exit_trend()
   - custom_stake_amount(), adjust_trade_position()
   - Hyperoptパラメータ（dca_threshold, take_profit）

3. REFACTOR: 必要に応じてリファクタリング

**参照**: 実装ガイド Step 2-5, 2-6

---

### タスク4: 市場環境判定モジュール（TDD）
**目的**: 新規要件FR-015に対応する市場環境判定機能

**TDDサイクル**:
1. RED: `tests/unit/test_market_regime.py`を作成
   - test_detects_bullish_regime: 上昇トレンド判定
   - test_detects_bearish_regime: 下降トレンド判定
   - test_detects_sideways_regime: サイドウェイ判定
   - test_entry_suppression_in_bear_market: ベア相場でのエントリー抑制

2. GREEN: `user_data/strategies/market_regime.py`を実装
   - MarketRegimeクラス
   - detect_regime(): EMA50/200とADXでトレンド判定
   - should_suppress_entry(): ベアトレンド時にエントリー抑制
   - add_regime_indicators(): 指標追加

3. REFACTOR: 必要に応じてリファクタリング

**参照**: 実装ガイド Step 2-8, 2-9

## 後続バッチ: タスク5-9の実装

### タスク5: スリッページ保護モジュール（TDD）
**目的**: 新規要件FR-014に対応するスリッページ保護機能

**TDDサイクル**:
1. RED: `tests/unit/test_slippage_protection.py`を作成
   - test_allows_order_within_threshold: 許容範囲内の注文
   - test_blocks_order_exceeding_threshold: 許容範囲超過のブロック
   - test_negative_slippage_within_threshold: マイナス方向のスリッページ
   - test_calculates_slippage_percentage: スリッページ率計算

2. GREEN: `user_data/strategies/slippage_protection.py`を実装
   - SlippageProtectionクラス
   - check_slippage(): 0.5%許容範囲のチェック
   - calculate_slippage_percentage(): 価格乖離計算

3. REFACTOR: 必要に応じてリファクタリング

**参照**: 実装ガイド Step 2-10, 2-11

---

### タスク6: DCA戦略への新機能統合
**目的**: 市場環境判定とスリッページ保護をDCA戦略に統合

**実装内容**:
1. dca_strategy.pyに以下をインポート:
   - MarketRegimeクラス
   - SlippageProtectionクラス

2. __init__メソッドでインスタンス化

3. populate_indicators()に市場環境指標を追加

4. populate_entry_trend()に市場環境フィルタを追加

**参照**: 実装ガイド Step 2-12

---

### タスク7: Hyperoptパラメータ化
**目的**: 要件FR-002/FR-003の修正対応

**実装内容**:
1. DCA閾値の拡張:
   - dca_threshold_1: -5%〜-10%（デフォルト-7%）
   - dca_threshold_2: -8%〜-15%（デフォルト-12%）
   - dca_threshold_3: -12%〜-20%（デフォルト-18%）

2. 利確閾値の拡張:
   - take_profit_threshold: +5%〜+15%（デフォルト+8%）
   - take_profit_sell_ratio: 25%〜50%（デフォルト33%）

3. adjust_trade_position()の更新

**参照**: 実装ガイド Step 2-13

---

### タスク8: テストカバレッジ確認
**目的**: 80%以上のカバレッジを確保

**実行コマンド**:
```bash
.venv/bin/python -m pytest --cov=user_data/strategies --cov-report=term-missing
```

**合格基準**: カバレッジ80%以上

---

### タスク9: コミット
**実行コマンド**:
```bash
git init  # まだ初期化されていない場合
git add .
git commit -m "Phase 2: Implement DCA strategy with TDD"
```

## 重要ファイルパス

### 実装済みファイル
- [x] `user_data/strategies/indicators.py`
- [x] `tests/unit/test_indicators.py`
- [x] `pyproject.toml`
- [x] `.gitignore`
- [x] `tests/conftest.py`

### 実装予定のファイル
- [ ] `user_data/strategies/risk_manager.py`
- [ ] `user_data/strategies/dca_strategy.py`
- [ ] `user_data/strategies/market_regime.py`
- [ ] `user_data/strategies/slippage_protection.py`

### テストファイル（予定）
- [ ] `tests/unit/test_risk_manager.py`
- [ ] `tests/unit/test_dca_strategy.py`
- [ ] `tests/unit/test_market_regime.py`
- [ ] `tests/unit/test_slippage_protection.py`

## 検証方法

### テスト実行
```bash
# 全テスト実行
.venv/bin/python -m pytest -v

# カバレッジ確認
.venv/bin/python -m pytest --cov=user_data/strategies --cov-report=term-missing

# 個別モジュールのテスト
.venv/bin/python -m pytest tests/unit/test_risk_manager.py -v
.venv/bin/python -m pytest tests/unit/test_dca_strategy.py -v
```

### コードスタイルチェック
```bash
.venv/bin/ruff check user_data/strategies/ tests/
```

### 合格基準
- 全テストがPASS
- カバレッジ80%以上
- Ruffのエラーなし

## 制約事項
- CLAUDE.mdの指示に従い、実装はsubagent（tdd-guide等）に委託
- TDDアプローチを厳守（テスト → 実装の順）
- イミュータビリティを保持（オブジェクトの変更ではなく新規作成）

## バッチ実行計画

### Batch 2（次回実行）
- タスク2: リスク管理モジュール
- タスク3: DCA戦略コア
- タスク4: 市場環境判定モジュール

### Batch 3
- タスク5: スリッページ保護モジュール
- タスク6: DCA戦略への新機能統合
- タスク7: Hyperoptパラメータ化

### Batch 4（最終）
- タスク8: テストカバレッジ確認
- タスク9: コミット

## 次のステップ
Phase 2完了後、Phase 3（パラメータ設計と設定ファイル）に進む
