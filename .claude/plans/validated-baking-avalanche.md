# Phase 4: バックテストと最適化 実装計画

## 概要
Phase 4はバックテスト実行、ウォークフォワード分析、Hyperoptパラメータ最適化、モンテカルロシミュレーションを行う。
ただし、Phase 2/3で発見された残課題（Batch 0）を先に修正する。これらはバックテスト精度に直接影響するため必須。

## Phase 3完了状態
- 52テスト全PASS、カバレッジ87%
- 実装済み: indicators.py, risk_manager.py, dca_strategy.py, market_regime.py, slippage_protection.py, validate_config.py
- 設定ファイル: config.json, config.backtest.json, config.hyperopt.json, config.live.json
- 運用スクリプト: download_data.sh, heartbeat.sh, backup_db.sh

### Phase 2/3で発見された残課題（Batch 0で修正）
1. `stoploss = -0.25` → 要件では `-0.20`
2. `timeframe = '5m'` → 要件では `'1h'`（ユーザー確認済み）
3. `trailing_stop` 未実装（要件: trailing_stop=True, +5%到達後+2%）
4. Freqtrade `protections` プロパティ未定義（CooldownPeriod, MaxDrawdown, StoplossGuard, LowProfitPairs）
5. 出来高フィルタリング未実装（要件: エントリー条件に出来高確認を追加）
6. RiskManagerの未接続メソッド: check_portfolio_limit, check_daily_loss_limit, check_circuit_breaker, record_trade_result, check_consecutive_losses, trigger_cooldown

### バックテスト合格基準（要件 7.1）
| メトリクス | 最低基準 | 目標値 |
|-----------|---------|--------|
| 勝率 | >= 50% | >= 60% |
| プロフィットファクター | >= 1.2 | >= 1.5 |
| Sharpe比 | >= 0.5 | >= 1.0 |
| 最大ドローダウン | <= 20% | <= 15% |
| OOS劣化率 | <= 30% | <= 15% |
| 最低トレード数 | >= 30 | - |
| モンテカルロ | 100回以上 | - |

---

## Batch 0: Phase 2/3残課題の修正（TDD）

### タスク0-1: stoploss値の修正（TDD）
- ファイル: `user_data/strategies/dca_strategy.py`, `tests/unit/test_dca_strategy.py`
- RED: `test_stoploss_is_minus_twenty_percent` を追加
  ```python
  def test_stoploss_is_minus_twenty_percent(self, default_config):
      strategy = DCAStrategy(default_config)
      assert strategy.stoploss == -0.20
  ```
- GREEN: `stoploss = -0.25` → `stoploss = -0.20` に変更
- 検証: 全テストPASS

### タスク0-2: timeframe値の修正（TDD）
- ファイル: `user_data/strategies/dca_strategy.py`, `tests/unit/test_dca_strategy.py`
- RED: `test_timeframe_is_one_hour` を追加
  ```python
  def test_timeframe_is_one_hour(self, default_config):
      strategy = DCAStrategy(default_config)
      assert strategy.timeframe == '1h'
  ```
- GREEN: `timeframe = '5m'` → `timeframe = '1h'` に変更
- 検証: 全テストPASS

### タスク0-3: trailing_stopの実装（TDD）
- ファイル: `user_data/strategies/dca_strategy.py`, `tests/unit/test_dca_strategy.py`
- RED: `test_trailing_stop_configuration` を追加
  ```python
  def test_trailing_stop_configuration(self, default_config):
      strategy = DCAStrategy(default_config)
      assert strategy.trailing_stop is True
      assert strategy.trailing_stop_positive == 0.02
      assert strategy.trailing_stop_positive_offset == 0.05
      assert strategy.trailing_only_offset_is_reached is True
  ```
- GREEN: DCAStrategyクラスにtrailing_stop関連プロパティを追加
  ```python
  trailing_stop = True
  trailing_stop_positive = 0.02
  trailing_stop_positive_offset = 0.05
  trailing_only_offset_is_reached = True
  ```
- 検証: 全テストPASS

### タスク0-4: Freqtrade protectionsプロパティの実装（TDD）
- ファイル: `user_data/strategies/dca_strategy.py`, `tests/unit/test_dca_strategy.py`
- RED: `TestDCAStrategyProtections` クラスを追加
  ```python
  class TestDCAStrategyProtections:
      def test_protections_includes_cooldown_period(self, default_config):
          strategy = DCAStrategy(default_config)
          methods = [p["method"] for p in strategy.protections]
          assert "CooldownPeriod" in methods

      def test_protections_includes_max_drawdown(self, default_config):
          strategy = DCAStrategy(default_config)
          methods = [p["method"] for p in strategy.protections]
          assert "MaxDrawdown" in methods

      def test_protections_includes_stoploss_guard(self, default_config):
          strategy = DCAStrategy(default_config)
          methods = [p["method"] for p in strategy.protections]
          assert "StoplossGuard" in methods

      def test_protections_includes_low_profit_pairs(self, default_config):
          strategy = DCAStrategy(default_config)
          methods = [p["method"] for p in strategy.protections]
          assert "LowProfitPairs" in methods
  ```
- GREEN: DCAStrategyに`protections`プロパティを追加
  ```python
  @property
  def protections(self):
      return [
          {"method": "CooldownPeriod", "stop_duration_candles": 3},
          {"method": "MaxDrawdown", "lookback_period_candles": 48,
           "trade_limit": 20, "max_allowed_drawdown": 0.15},
          {"method": "StoplossGuard", "lookback_period_candles": 24,
           "trade_limit": 3, "only_per_pair": False},
          {"method": "LowProfitPairs", "lookback_period_candles": 48,
           "trade_limit": 2, "required_profit": -0.05},
      ]
  ```
- 検証: 全テストPASS

### タスク0-5: 出来高フィルタリングの実装（TDD）
- ファイル: `user_data/strategies/dca_strategy.py`, `tests/unit/test_dca_strategy.py`
- RED: `test_entry_requires_volume_above_sma` を追加
  ```python
  def test_entry_requires_volume_above_sma(self, default_config):
      """出来高がSMA以下の場合エントリーしない"""
      strategy = DCAStrategy(default_config)
      df = create_test_dataframe_with_low_volume()  # volume < volume_sma
      df['rsi'] = 25  # RSI条件は満たす
      result = strategy.populate_entry_trend(
          strategy.populate_indicators(df, {'pair': 'BTC/JPY'}),
          {'pair': 'BTC/JPY'}
      )
      assert result['enter_long'].sum() == 0
  ```
- GREEN:
  - `populate_indicators()` に `calculate_volume_sma()` を追加
  - `populate_entry_trend()` のエントリー条件に出来高フィルタを追加:
    `(dataframe['volume'] > dataframe['volume_sma_20'])`
- 検証: 全テストPASS（既存テストのDataFrameにvolume列が必要な場合は修正）

### タスク0-6: RiskManager追加メソッドの接続（TDD）
- ファイル: `user_data/strategies/dca_strategy.py`, `tests/unit/test_dca_strategy.py`
- RED: 以下のテストを追加
  ```python
  class TestDCAStrategyRiskManagerFull:
      def test_entry_blocked_by_consecutive_losses(self, default_config):
          """連続損失上限で新規エントリーをブロック"""

      def test_trade_result_recorded_on_exit(self, default_config):
          """エグジット時にトレード結果が記録される"""
  ```
- GREEN:
  - `confirm_trade_entry()` に `check_consecutive_losses()` チェックを追加
  - `custom_exit()` メソッドを追加し、`record_trade_result()` と必要に応じて `trigger_cooldown()` を呼び出す
- 注意: check_portfolio_limit, check_daily_loss_limit, check_circuit_breaker はバックテストでは完全には使えない（リアルタイムのポートフォリオ情報が必要）。Dry Run/ライブ向けの接続はPhase 5以降で行う。
- 検証: 全テストPASS

### タスク0-7: minimal_roiのtimeframe整合性調整
- ファイル: `user_data/strategies/dca_strategy.py`
- 修正: 1h足に合わせてminimal_roiのキー値を調整
  - 現在: `{"0": 0.15, "60": 0.10, "120": 0.05}`（5m基準: 12本後、24本後）
  - 変更: `{"0": 0.15, "720": 0.10, "1440": 0.05}`（1h基準: 12時間後、24時間後）
- 注意: これはHyperoptで最適化されるため暫定値
- 検証: 全テストPASS

### タスク0-8: 全テスト実行 + カバレッジ確認
```bash
.venv/bin/python -m pytest -v
.venv/bin/python -m pytest --cov=user_data/strategies --cov=scripts --cov-report=term-missing
.venv/bin/ruff check user_data/strategies/ tests/ scripts/
```
- 全テストPASS、カバレッジ80%以上、Ruffエラーなし

---

## Batch 1: バックテスト分析インフラ構築（TDD）

### タスク1-1: RED - analyze_backtest.pyのテスト作成
- ファイル: `tests/unit/test_analyze_backtest.py`
- テストケース:
  ```python
  class TestBacktestCriteria:
      def test_passing_results_meet_all_criteria(self):
          """全基準を満たす結果はPASS"""

      def test_low_win_rate_fails(self):
          """勝率50%未満はFAIL"""

      def test_low_profit_factor_fails(self):
          """PF 1.2未満はFAIL"""

      def test_low_sharpe_ratio_fails(self):
          """Sharpe 0.5未満はFAIL"""

      def test_high_max_drawdown_fails(self):
          """最大DD 20%超はFAIL"""

      def test_insufficient_trades_fails(self):
          """トレード数30未満はFAIL"""

      def test_distinguishes_minimum_and_target(self):
          """最低基準と目標値を区別"""
  ```
- 設計:
  ```python
  @dataclass(frozen=True)
  class BacktestMetrics:
      win_rate: float
      profit_factor: float
      sharpe_ratio: float
      max_drawdown: float
      total_trades: int
      total_profit_pct: float

  @dataclass(frozen=True)
  class CriteriaResult:
      passed_minimum: bool
      passed_target: bool
      details: tuple[str, ...]

  def evaluate_backtest(metrics: BacktestMetrics) -> CriteriaResult  # 純粋関数
  def parse_backtest_json(json_path: str) -> BacktestMetrics
  ```

### タスク1-2: GREEN - analyze_backtest.pyの実装
- ファイル: `scripts/analyze_backtest.py`
- `evaluate_backtest()`: 純粋関数で合格基準判定
- `parse_backtest_json()`: Freqtradeのbacktest結果JSONを解析
- `main()`: CLI用エントリーポイント
- 検証: テストPASS

### タスク1-3: RED - monte_carlo.pyのテスト作成
- ファイル: `tests/unit/test_monte_carlo.py`
- テストケース:
  ```python
  class TestMonteCarloSimulation:
      def test_simulation_returns_correct_count(self):
          """指定回数分の結果を返す"""

      def test_simulation_shuffles_trade_order(self):
          """各runでトレード順序がシャッフルされる"""

      def test_confidence_interval_calculation(self):
          """95%信頼区間が正しく計算される"""

      def test_simulation_preserves_trade_results(self):
          """シャッフルしてもトレード結果自体は変わらない"""

      def test_worst_case_drawdown_reported(self):
          """最悪ケースのDDが報告される"""
  ```
- 設計:
  ```python
  @dataclass(frozen=True)
  class MonteCarloResult:
      median_profit: float
      ci_95_lower: float
      ci_95_upper: float
      worst_drawdown: float
      best_drawdown: float
      median_drawdown: float
      run_count: int

  def run_monte_carlo(
      trade_results: tuple[float, ...],
      num_simulations: int = 100,
      seed: int = 42
  ) -> MonteCarloResult  # 純粋関数（seedで再現性確保）
  ```

### タスク1-4: GREEN - monte_carlo.pyの実装
- ファイル: `scripts/monte_carlo.py`
- `run_monte_carlo()`: numpy.random.shuffle + 累積損益シミュレーション
- `main()`: CLI用（バックテスト結果JSONからトレードリストを読み込み）
- 検証: テストPASS

### タスク1-5: walk_forward.shの作成
- ファイル: `scripts/walk_forward.sh`
- 処理:
  1. IS期間（2024/03-2025/06）でバックテスト実行
  2. OOS期間（2025/07-2025/12）でバックテスト実行
  3. 最終検証期間（2026/01）でバックテスト実行
  4. 各期間の結果を`scripts/analyze_backtest.py`で分析
  5. OOS劣化率を計算・表示
- set -euo pipefail、タイムスタンプ付きログ

### タスク1-6: pyproject.toml更新 + 全テスト + カバレッジ確認
```bash
.venv/bin/python -m pytest -v
.venv/bin/python -m pytest --cov=user_data/strategies --cov=scripts --cov-report=term-missing
```
- 全テストPASS、カバレッジ80%以上

---

## Batch 2: データダウンロードとバックテスト実行

### 前提条件
- Freqtrade CLIが利用可能であること（未確認の場合はセットアップ手順を実行）
- `.venv` にfreqtradeがインストール済み

### タスク2-1: Freqtrade CLI動作確認
```bash
.venv/bin/freqtrade --version
```
- 利用不可の場合: `pip install freqtrade[all]` またはDocker経由で実行

### タスク2-2: OHLCVデータダウンロード
```bash
./scripts/download_data.sh
```
- 対象: BTC/JPY, ETH/JPY
- 期間: 20240301〜現在
- 時間足: 1h, 4h, 1d
- ダウンロード先: `user_data/data/binance/`

### タスク2-3: 初回バックテスト実行
```bash
.venv/bin/freqtrade backtesting \
  --config user_data/config/config.backtest.json \
  --strategy DCAStrategy \
  --timerange 20240301-20260127
```
- 結果: `user_data/backtest_results/` に保存

### タスク2-4: バックテスト結果分析
```bash
.venv/bin/python scripts/analyze_backtest.py user_data/backtest_results/<latest_result>.json
```
- 合格基準チェック（最低基準/目標値）

### タスク2-5: ウォークフォワード分析実行
```bash
./scripts/walk_forward.sh
```
- IS/OOS/最終検証期間の結果比較
- OOS劣化率 <= 30% を確認

### タスク2-6: モンテカルロシミュレーション実行
```bash
.venv/bin/python scripts/monte_carlo.py user_data/backtest_results/<latest_result>.json --runs 100
```
- 95%信頼区間と最悪ケースDDを確認

### Batch 2判定ポイント
- 合格基準を満たす場合 → Batch 3（Hyperopt）へ進む
- 合格基準を満たさない場合 → 戦略の調整が必要（ユーザーと相談）

---

## Batch 3: Hyperoptパラメータ最適化

### タスク3-1: Hyperopt実行
```bash
.venv/bin/freqtrade hyperopt \
  --config user_data/config/config.hyperopt.json \
  --strategy DCAStrategy \
  --hyperopt-loss SharpeHyperOptLoss \
  --spaces buy sell \
  --epochs 500 \
  --timerange 20240301-20250630 \
  --job-workers 4
```
- IS期間のみで最適化（OOSでのオーバーフィット防止）

### タスク3-2: 最適化パラメータの確認と適用
- Hyperopt結果から最良パラメータを取得
- `dca_strategy.py` のDecimalParameterデフォルト値を更新:
  - dca_threshold_1, dca_threshold_2, dca_threshold_3
  - take_profit_threshold, take_profit_sell_ratio
- 注意: DecimalParameter自体は変更せず、`default=` 値のみ更新

### タスク3-3: 最適化後のフルバックテスト
```bash
.venv/bin/freqtrade backtesting \
  --config user_data/config/config.backtest.json \
  --strategy DCAStrategy \
  --timerange 20240301-20260127
```

### タスク3-4: 最適化後のウォークフォワード分析
```bash
./scripts/walk_forward.sh
```
- OOS劣化率が最適化前より悪化していないことを確認

### タスク3-5: 最適化後のモンテカルロシミュレーション
```bash
.venv/bin/python scripts/monte_carlo.py user_data/backtest_results/<latest_result>.json --runs 100
```

---

## Batch 4: 最終検証とコミット

### タスク4-1: 全テスト実行
```bash
.venv/bin/python -m pytest -v
```

### タスク4-2: カバレッジ確認（80%以上）
```bash
.venv/bin/python -m pytest --cov=user_data/strategies --cov=scripts --cov-report=term-missing
```

### タスク4-3: Ruffリント
```bash
.venv/bin/ruff check user_data/strategies/ tests/ scripts/
```

### タスク4-4: シェルスクリプト構文検証
```bash
bash -n scripts/*.sh
```

### タスク4-5: バックテスト結果サマリ作成
- 最終バックテスト結果を記録（合格基準との比較表）
- ウォークフォワードOOS劣化率
- モンテカルロ95%信頼区間

### タスク4-6: コミット
```bash
git add user_data/strategies/dca_strategy.py tests/unit/ scripts/ pyproject.toml
git commit -m "Phase 4: Complete backtesting, walk-forward analysis, and hyperparameter optimization"
```

---

## 重要ファイルパス

### 新規作成
- `scripts/analyze_backtest.py`
- `scripts/monte_carlo.py`
- `scripts/walk_forward.sh`
- `tests/unit/test_analyze_backtest.py`
- `tests/unit/test_monte_carlo.py`

### 修正対象
- `user_data/strategies/dca_strategy.py`（stoploss, timeframe, trailing_stop, protections, volume filter, RiskManager接続, minimal_roi）
- `tests/unit/test_dca_strategy.py`（新テスト追加、既存テストのDataFrame修正）
- `pyproject.toml`（カバレッジ対象にscriptsが既に含まれているか確認）

### 参照のみ
- `user_data/strategies/indicators.py`（calculate_volume_sma関数）
- `user_data/strategies/risk_manager.py`（未接続メソッド確認）
- `user_data/config/config.backtest.json`（バックテスト設定）
- `user_data/config/config.hyperopt.json`（Hyperopt設定）
- `crypto_dca_bot_requirements.md`（合格基準）
- `crypto_dca_bot_implementation_guide.md`（Phase 4手順）

---

## 合格基準
- 全テストPASS
- カバレッジ80%以上
- Ruffエラーなし
- 全シェルスクリプト構文正常
- バックテスト結果が最低基準を満たす（勝率>=50%, PF>=1.2, Sharpe>=0.5, DD<=20%, トレード数>=30）
- ウォークフォワードOOS劣化率 <= 30%
- モンテカルロシミュレーション100回以上実施
- 最適化パラメータがdca_strategy.pyに反映済み

---

## 注意事項
- Batch 0/1はTDD必須（RED→GREEN→REFACTOR）
- Batch 2/3はFreqtrade CLI依存（未インストールの場合はタスク2-1で対応）
- バックテスト結果が合格基準を満たさない場合、Batch 2完了後にユーザーと相談
- Hyperoptのepochs数は計算リソースに応じて調整可（最低100、推奨500）
- check_portfolio_limit, check_daily_loss_limit, check_circuit_breaker のDCAStrategy接続はPhase 5（Dry Run）で実装（リアルタイムポートフォリオ情報が必要なため）
