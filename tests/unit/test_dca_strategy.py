"""
DCA戦略のユニットテスト
"""

import pytest
import pandas as pd
from datetime import datetime
from unittest.mock import MagicMock
from user_data.strategies.dca_strategy import DCAStrategy


@pytest.fixture
def default_config():
    """デフォルトの戦略設定"""
    return {
        'stake_currency': 'USDT',
        'stake_amount': 100.0,
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

        metadata = {'pair': 'BTC/USDT'}
        result = strategy.populate_entry_trend(dataframe, metadata)

        # 最後の行でエントリーシグナルが立つことを確認
        assert result.iloc[-1]['enter_long'] == 1

    def test_no_entry_signal_when_rsi_not_oversold(self):
        """RSIが30以上ではエントリーシグナルなし"""
        strategy = DCAStrategy(default_config)

        dataframe = pd.DataFrame({
            'close': [100.0, 101.0, 102.0],
            'rsi': [50.0, 55.0, 60.0],  # RSI > 30
            'volume': [1000.0, 1100.0, 1200.0],
        })

        metadata = {'pair': 'BTC/USDT'}
        result = strategy.populate_entry_trend(dataframe, metadata)

        # エントリーシグナルが立たないことを確認
        assert result.iloc[-1]['enter_long'] == 0


class TestDCAStrategyCustomStakeAmount:
    """カスタムステーク額のテストスイート"""

    def test_initial_stake_amount(self):
        """初回エントリーのステーク額"""
        strategy = DCAStrategy(default_config)

        result = strategy.custom_stake_amount(
            pair='BTC/USDT',
            current_time=datetime.now(),
            current_rate=40000.0,
            proposed_stake=100.0,
            min_stake=10.0,
            max_stake=1000.0,
            leverage=1.0,
            entry_tag=None,
            side='long',
            wallet_balance=10000.0,
            wallet_currency='USDT'
        )

        # 提案されたステーク額をそのまま返す
        assert result == 100.0

    def test_adjusted_stake_for_dca(self):
        """DCA追加購入時のステーク額調整"""
        strategy = DCAStrategy(default_config)

        # DCAエントリータグの場合
        result = strategy.custom_stake_amount(
            pair='BTC/USDT',
            current_time=datetime.now(),
            current_rate=40000.0,
            proposed_stake=100.0,
            min_stake=10.0,
            max_stake=1000.0,
            leverage=1.0,
            entry_tag='dca_1',
            side='long',
            wallet_balance=10000.0,
            wallet_currency='USDT'
        )

        # DCAの場合は1.5倍のステーク
        assert result == 150.0


class TestDCAStrategyPositionAdjustment:
    """ポジション調整（DCA追加購入）のテストスイート"""

    def test_no_adjustment_when_no_trade(self):
        """トレードがない場合は調整なし"""
        strategy = DCAStrategy(default_config)

        result = strategy.adjust_trade_position(
            trade=None,
            current_time=datetime.now(),
            current_rate=40000.0,
            current_profit=0.0,
            min_stake=10.0,
            max_stake=1000.0,
            current_entry_rate=40000.0,
            current_exit_rate=40000.0,
            current_entry_profit=0.0,
            current_exit_profit=0.0,
            side='long',
            pair='BTC/USDT'
        )

        assert result is None

    def test_dca_adjustment_on_threshold(self):
        """DCA閾値到達時に追加購入"""
        strategy = DCAStrategy(default_config)

        # モックトレードオブジェクト
        mock_trade = MagicMock()
        mock_trade.nr_of_successful_entries = 1

        result = strategy.adjust_trade_position(
            trade=mock_trade,
            current_time=datetime.now(),
            current_rate=40000.0,
            current_profit=-0.08,  # -8% (DCA閾値-7%を超過)
            min_stake=10.0,
            max_stake=1000.0,
            current_entry_rate=43200.0,
            current_exit_rate=40000.0,
            current_entry_profit=-0.08,
            current_exit_profit=-0.08,
            side='long',
            pair='BTC/USDT'
        )

        # 追加購入が行われることを確認
        assert result is not None
        assert result > 0

    def test_no_dca_when_profit_positive(self):
        """利益が出ている場合はDCAなし"""
        strategy = DCAStrategy(default_config)

        mock_trade = MagicMock()
        mock_trade.nr_of_successful_entries = 1

        result = strategy.adjust_trade_position(
            trade=mock_trade,
            current_time=datetime.now(),
            current_rate=42000.0,
            current_profit=0.05,  # +5% (利益)
            min_stake=10.0,
            max_stake=1000.0,
            current_entry_rate=40000.0,
            current_exit_rate=42000.0,
            current_entry_profit=0.05,
            current_exit_profit=0.05,
            side='long',
            pair='BTC/USDT'
        )

        assert result is None


class TestDCAStrategyExitSignal:
    """エグジットシグナルのテストスイート"""

    def test_generates_exit_signal_on_profit_target(self):
        """利確目標到達でエグジットシグナルを生成"""
        strategy = DCAStrategy(default_config)

        dataframe = pd.DataFrame({
            'close': [100.0, 105.0, 110.0],
            'rsi': [50.0, 65.0, 75.0],  # RSI > 70
            'volume': [1000.0, 1100.0, 1200.0],
        })

        metadata = {'pair': 'BTC/USDT'}
        result = strategy.populate_exit_trend(dataframe, metadata)

        # RSI > 70でエグジットシグナルが立つことを確認
        assert result.iloc[-1]['exit_long'] == 1

    def test_no_exit_signal_when_below_target(self):
        """利確目標未到達ではエグジットシグナルなし"""
        strategy = DCAStrategy(default_config)

        dataframe = pd.DataFrame({
            'close': [100.0, 101.0, 102.0],
            'rsi': [50.0, 55.0, 60.0],  # RSI < 70
            'volume': [1000.0, 1100.0, 1200.0],
        })

        metadata = {'pair': 'BTC/USDT'}
        result = strategy.populate_exit_trend(dataframe, metadata)

        # エグジットシグナルが立たないことを確認
        assert result.iloc[-1]['exit_long'] == 0
