"""
DCA戦略のユニットテスト
"""

from datetime import datetime
from unittest.mock import MagicMock

import pandas as pd
import pytest

from user_data.strategies.dca_strategy import DCAStrategy


@pytest.fixture
def default_config():
    """デフォルトの戦略設定"""
    return {
        'stake_currency': 'JPY',
        'stake_amount': 10000,
        'dry_run': True,
    }


class TestDCAStrategyEntrySignal:
    """エントリーシグナルのテストスイート"""

    def test_generates_entry_signal_on_rsi_oversold(self, default_config):
        """RSIが30以下でエントリーシグナルを生成"""
        strategy = DCAStrategy(default_config)

        # テストデータ作成
        dataframe = pd.DataFrame({
            'close': [100.0, 99.0, 98.0],
            'rsi': [35.0, 28.0, 25.0],  # RSI < 30
            'volume': [1000.0, 1100.0, 1200.0],
        })

        metadata = {'pair': 'BTC/JPY'}
        result = strategy.populate_entry_trend(dataframe, metadata)

        # 最後の行でエントリーシグナルが立つことを確認
        assert result.iloc[-1]['enter_long'] == 1

    def test_no_entry_signal_when_rsi_not_oversold(self, default_config):
        """RSIが30以上ではエントリーシグナルなし"""
        strategy = DCAStrategy(default_config)

        dataframe = pd.DataFrame({
            'close': [100.0, 101.0, 102.0],
            'rsi': [50.0, 55.0, 60.0],  # RSI > 30
            'volume': [1000.0, 1100.0, 1200.0],
        })

        metadata = {'pair': 'BTC/JPY'}
        result = strategy.populate_entry_trend(dataframe, metadata)

        # エントリーシグナルが立たないことを確認
        assert result.iloc[-1]['enter_long'] == 0


class TestDCAStrategyCustomStakeAmount:
    """カスタムステーク額のテストスイート"""

    def test_initial_stake_amount(self, default_config):
        """初回エントリーのステーク額"""
        strategy = DCAStrategy(default_config)

        result = strategy.custom_stake_amount(
            pair='BTC/JPY',
            current_time=datetime.now(),
            current_rate=4000000.0,
            proposed_stake=10000,
            min_stake=1000,
            max_stake=100000,
            leverage=1.0,
            entry_tag=None,
            side='long',
            wallet_balance=1000000,
            wallet_currency='JPY'
        )

        # 提案されたステーク額をそのまま返す
        assert result == 10000

    def test_adjusted_stake_for_dca(self, default_config):
        """DCA追加購入時のステーク額調整"""
        strategy = DCAStrategy(default_config)

        # DCAエントリータグの場合
        result = strategy.custom_stake_amount(
            pair='BTC/JPY',
            current_time=datetime.now(),
            current_rate=4000000.0,
            proposed_stake=10000,
            min_stake=1000,
            max_stake=100000,
            leverage=1.0,
            entry_tag='dca_1',
            side='long',
            wallet_balance=1000000,
            wallet_currency='JPY'
        )

        # DCAの場合は1.5倍のステーク
        assert result == 15000


class TestDCAStrategyPositionAdjustment:
    """ポジション調整（DCA追加購入）のテストスイート"""

    def test_no_adjustment_when_no_trade(self, default_config):
        """トレードがない場合は調整なし"""
        strategy = DCAStrategy(default_config)

        result = strategy.adjust_trade_position(
            trade=None,
            current_time=datetime.now(),
            current_rate=4000000.0,
            current_profit=0.0,
            min_stake=1000,
            max_stake=100000,
            current_entry_rate=4000000.0,
            current_exit_rate=4000000.0,
            current_entry_profit=0.0,
            current_exit_profit=0.0,
            side='long',
            pair='BTC/JPY'
        )

        assert result is None

    def test_dca_adjustment_on_threshold(self, default_config):
        """DCA閾値到達時に追加購入"""
        strategy = DCAStrategy(default_config)

        # モックトレードオブジェクト
        mock_trade = MagicMock()
        mock_trade.nr_of_successful_entries = 1

        result = strategy.adjust_trade_position(
            trade=mock_trade,
            current_time=datetime.now(),
            current_rate=4000000.0,
            current_profit=-0.08,  # -8% (DCA閾値-7%を超過)
            min_stake=1000,
            max_stake=100000,
            current_entry_rate=4320000.0,
            current_exit_rate=4000000.0,
            current_entry_profit=-0.08,
            current_exit_profit=-0.08,
            side='long',
            pair='BTC/JPY'
        )

        # 追加購入が行われることを確認
        assert result is not None
        assert result > 0

    def test_no_dca_when_profit_positive(self, default_config):
        """利益が出ている場合はDCAなし"""
        strategy = DCAStrategy(default_config)

        mock_trade = MagicMock()
        mock_trade.nr_of_successful_entries = 1

        result = strategy.adjust_trade_position(
            trade=mock_trade,
            current_time=datetime.now(),
            current_rate=4200000.0,
            current_profit=0.05,  # +5% (利益)
            min_stake=1000,
            max_stake=100000,
            current_entry_rate=4000000.0,
            current_exit_rate=4200000.0,
            current_entry_profit=0.05,
            current_exit_profit=0.05,
            side='long',
            pair='BTC/JPY'
        )

        assert result is None


class TestDCAStrategyExitSignal:
    """エグジットシグナルのテストスイート"""

    def test_generates_exit_signal_on_profit_target(self, default_config):
        """利確目標到達でエグジットシグナルを生成"""
        strategy = DCAStrategy(default_config)

        dataframe = pd.DataFrame({
            'close': [100.0, 105.0, 110.0],
            'rsi': [50.0, 65.0, 75.0],  # RSI > 70
            'volume': [1000.0, 1100.0, 1200.0],
        })

        metadata = {'pair': 'BTC/JPY'}
        result = strategy.populate_exit_trend(dataframe, metadata)

        # RSI > 70でエグジットシグナルが立つことを確認
        assert result.iloc[-1]['exit_long'] == 1

    def test_no_exit_signal_when_below_target(self, default_config):
        """利確目標未到達ではエグジットシグナルなし"""
        strategy = DCAStrategy(default_config)

        dataframe = pd.DataFrame({
            'close': [100.0, 101.0, 102.0],
            'rsi': [50.0, 55.0, 60.0],  # RSI < 70
            'volume': [1000.0, 1100.0, 1200.0],
        })

        metadata = {'pair': 'BTC/JPY'}
        result = strategy.populate_exit_trend(dataframe, metadata)

        # エグジットシグナルが立たないことを確認
        assert result.iloc[-1]['exit_long'] == 0


class TestDCAStrategyRiskManagement:
    """リスク管理統合のテストスイート"""

    def test_dca_respects_position_size_limit(self, default_config):
        """ポジションサイズ上限を超える場合はステーク額を制限"""
        config = default_config.copy()
        config['max_position_size'] = 5000  # 上限5000JPY
        strategy = DCAStrategy(config)

        # 提案額10000JPYは上限超過のため、Noneが返される想定
        result = strategy.custom_stake_amount(
            pair='BTC/JPY',
            current_time=datetime.now(),
            current_rate=4000000.0,
            proposed_stake=10000,
            min_stake=1000,
            max_stake=100000,
            leverage=1.0,
            entry_tag=None,
            side='long',
            wallet_balance=1000000,
            wallet_currency='JPY'
        )

        # 上限を超える場合はNoneを返す
        assert result is None

    def test_dca_blocked_during_cooldown(self, default_config):
        """クールダウン期間中はDCA追加購入をブロック"""
        config = default_config.copy()
        config['cooldown_hours'] = 24
        strategy = DCAStrategy(config)

        # クールダウンを設定
        now = datetime.now()
        strategy.risk_manager.trigger_cooldown(now)

        mock_trade = MagicMock()
        mock_trade.nr_of_successful_entries = 1

        result = strategy.adjust_trade_position(
            trade=mock_trade,
            current_time=now,
            current_rate=4000000.0,
            current_profit=-0.08,  # DCA閾値を超過
            min_stake=1000,
            max_stake=100000,
            current_entry_rate=4320000.0,
            current_exit_rate=4000000.0,
            current_entry_profit=-0.08,
            current_exit_profit=-0.08,
            side='long',
            pair='BTC/JPY'
        )

        # クールダウン中はNoneを返す
        assert result is None


class TestDCAStrategySlippageProtection:
    """スリッページ保護統合のテストスイート"""

    def test_slippage_blocks_entry_on_excessive_slippage(self, default_config):
        """過大なスリッページ発生時にエントリーをブロック"""
        config = default_config.copy()
        config['max_slippage_percent'] = 0.5  # 0.5%まで許容
        strategy = DCAStrategy(config)

        # 期待価格を設定（最後に見た価格をシミュレート）
        strategy.expected_entry_price = {'BTC/JPY': 4000000.0}

        # 実際の注文レート: 4050000 JPY（1.25%のスリッページ = 許容範囲超過）
        result = strategy.confirm_trade_entry(
            pair='BTC/JPY',
            order_type='limit',
            amount=0.01,
            rate=4050000.0,
            time_in_force='GTC',
            current_time=datetime.now(),
            entry_tag=None,
            side='long'
        )

        # スリッページ超過のためFalse（エントリーブロック）
        assert result is False

    def test_slippage_allows_entry_within_tolerance(self, default_config):
        """許容範囲内のスリッページではエントリーを許可"""
        config = default_config.copy()
        config['max_slippage_percent'] = 0.5  # 0.5%まで許容
        strategy = DCAStrategy(config)

        # 期待価格を設定（最後に見た価格をシミュレート）
        strategy.expected_entry_price = {'BTC/JPY': 4000000.0}

        # 実際の注文レート: 4010000 JPY（0.25%のスリッページ = 許容範囲内）
        result = strategy.confirm_trade_entry(
            pair='BTC/JPY',
            order_type='limit',
            amount=0.01,
            rate=4010000.0,
            time_in_force='GTC',
            current_time=datetime.now(),
            entry_tag=None,
            side='long'
        )

        # 許容範囲内のためTrue（エントリー許可）
        assert result is True


class TestDCAStrategyBasicConfiguration:
    """基本設定のテストスイート"""

    def test_stoploss_is_minus_twenty_percent(self, default_config):
        """stoploss値が-0.20であることを確認"""
        strategy = DCAStrategy(default_config)
        assert strategy.stoploss == -0.20


class TestDCAStrategyPartialTakeProfit:
    """部分利確のテストスイート"""

    def test_partial_take_profit_at_threshold(self, default_config):
        """利益閾値到達時に部分利確を実行"""
        strategy = DCAStrategy(default_config)

        mock_trade = MagicMock()
        mock_trade.nr_of_successful_entries = 1
        mock_trade.stake_amount = 10000

        # 8%の利益（take_profit_thresholdのデフォルト値）
        result = strategy.adjust_trade_position(
            trade=mock_trade,
            current_time=datetime.now(),
            current_rate=4320000.0,
            current_profit=0.08,
            min_stake=1000,
            max_stake=100000,
            current_entry_rate=4000000.0,
            current_exit_rate=4320000.0,
            current_entry_profit=0.08,
            current_exit_profit=0.08,
            side='long',
            pair='BTC/JPY'
        )

        # 負の値を返す（部分売却）
        # take_profit_sell_ratio=0.33 → stake_amount * 0.33 = 10000 * 0.33 = 3300
        assert result is not None
        assert result < 0
        assert result == -3300

    def test_no_partial_take_profit_below_threshold(self, default_config):
        """利益が閾値未満では部分利確なし"""
        strategy = DCAStrategy(default_config)

        mock_trade = MagicMock()
        mock_trade.nr_of_successful_entries = 1
        mock_trade.stake_amount = 10000

        # 5%の利益（閾値8%未満）
        result = strategy.adjust_trade_position(
            trade=mock_trade,
            current_time=datetime.now(),
            current_rate=4200000.0,
            current_profit=0.05,
            min_stake=1000,
            max_stake=100000,
            current_entry_rate=4000000.0,
            current_exit_rate=4200000.0,
            current_entry_profit=0.05,
            current_exit_profit=0.05,
            side='long',
            pair='BTC/JPY'
        )

        # 閾値未満のためNone
        assert result is None
