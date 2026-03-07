"""
DCA戦略のユニットテスト
"""

from datetime import datetime
from unittest.mock import MagicMock

import pandas as pd
import pytest

from user_data.strategies.dca_strategy import DCAStrategy
from user_data.strategies.dca_strategy_balanced import DCAStrategyBalanced


@pytest.fixture
def default_config():
    """デフォルトの戦略設定"""
    return {
        'stake_currency': 'USDT',
        'stake_amount': 100,
        'dry_run': True,
        'dry_run_wallet': 1000,
        'max_portfolio_allocation': 0.2,
        'max_position_size': 1000,
        'daily_loss_limit': 0.05,
        'circuit_breaker_drawdown': 0.15,
        'max_consecutive_losses': 3,
        'cooldown_hours': 12,
        'max_slippage_percent': 0.5,
    }


def _balanced_dataframe(
    *,
    close: float = 103.0,
    previous_close: float = 101.0,
    open_price: float = 100.0,
    volume: float = 1200.0,
    volume_sma: float = 1000.0,
    rsi: float = 40.0,
    ema_50: float = 102.0,
    ema_200: float = 100.0,
    adx: float = 22.0,
    high: float = 104.0,
    low: float = 100.5,
) -> pd.DataFrame:
    """Balanced戦略向けの最小DataFrameを作成"""
    return pd.DataFrame(
        {
            'close': [previous_close, close],
            'open': [99.0, open_price],
            'high': [previous_close + 1.0, high],
            'low': [previous_close - 1.0, low],
            'volume': [1000.0, volume],
            'volume_sma_20': [1000.0, volume_sma],
            'rsi': [45.0, rsi],
            'ema_50': [101.0, ema_50],
            'ema_200': [100.0, ema_200],
            'adx': [20.0, adx],
            'volatility_ratio': [0.01, (high - low) / close],
        }
    )


class TestDCAStrategyBalancedEntrySignal:
    """Balanced戦略のエントリーシグナルのテスト"""

    def test_entry_requires_rebound_confirmation(self, default_config):
        strategy = DCAStrategyBalanced(default_config)
        dataframe = _balanced_dataframe()

        result = strategy.populate_entry_trend(dataframe, {'pair': 'BTC/USDT'})

        assert result.iloc[-1]['enter_long'] == 1

    def test_entry_is_blocked_without_green_candle(self, default_config):
        strategy = DCAStrategyBalanced(default_config)
        dataframe = _balanced_dataframe(open_price=104.0)

        result = strategy.populate_entry_trend(dataframe, {'pair': 'BTC/USDT'})

        assert result.iloc[-1]['enter_long'] == 0

    def test_entry_is_blocked_when_close_does_not_reclaim_previous_close(self, default_config):
        strategy = DCAStrategyBalanced(default_config)
        dataframe = _balanced_dataframe(close=100.5, previous_close=101.0)

        result = strategy.populate_entry_trend(dataframe, {'pair': 'BTC/USDT'})

        assert result.iloc[-1]['enter_long'] == 0

    def test_entry_is_blocked_on_high_volatility(self, default_config):
        strategy = DCAStrategyBalanced(default_config)
        dataframe = _balanced_dataframe(high=110.0, low=95.0, close=100.0)

        result = strategy.populate_entry_trend(dataframe, {'pair': 'BTC/USDT'})

        assert result.iloc[-1]['enter_long'] == 0


class TestDCAStrategyBalancedExitSignal:
    """Balanced戦略のエグジットシグナルのテスト"""

    def test_exit_on_rsi_strength(self, default_config):
        strategy = DCAStrategyBalanced(default_config)
        dataframe = _balanced_dataframe(rsi=63.0)

        result = strategy.populate_exit_trend(dataframe, {'pair': 'BTC/USDT'})

        assert result.iloc[-1]['exit_long'] == 1

    def test_exit_on_trend_loss(self, default_config):
        strategy = DCAStrategyBalanced(default_config)
        dataframe = _balanced_dataframe(rsi=56.0, close=100.0, ema_50=101.0)

        result = strategy.populate_exit_trend(dataframe, {'pair': 'BTC/USDT'})

        assert result.iloc[-1]['exit_long'] == 1

    def test_custom_exit_returns_trend_loss_exit(self, default_config):
        strategy = DCAStrategyBalanced(default_config)
        strategy.dp = MagicMock()
        strategy.dp.get_analyzed_dataframe.return_value = (
            pd.DataFrame([{'close': 100.0, 'ema_50': 101.0}]),
            None,
        )

        result = strategy.custom_exit(
            pair='BTC/USDT',
            trade=MagicMock(),
            current_time=datetime.now(),
            current_rate=100.0,
            current_profit=-0.01,
        )

        assert result == 'trend_loss_exit'


class TestDCAStrategyRiskManagement:
    """リスク管理統合のテスト"""

    def test_custom_stake_rejects_over_portfolio_limit(self, default_config):
        strategy = DCAStrategy(default_config)

        result = strategy.custom_stake_amount(
            pair='BTC/USDT',
            current_time=datetime.now(),
            current_rate=40000.0,
            proposed_stake=300.0,
            min_stake=10.0,
            max_stake=1000.0,
            leverage=1.0,
            entry_tag=None,
            side='long',
            wallet_balance=1000.0,
        )

        assert result is None

    def test_adjust_trade_position_is_disabled(self, default_config):
        strategy = DCAStrategyBalanced(default_config)

        result = strategy.adjust_trade_position(
            trade=MagicMock(),
            current_time=datetime.now(),
            current_rate=100.0,
            current_profit=-0.04,
            min_stake=10.0,
            max_stake=1000.0,
            current_entry_rate=104.0,
            current_exit_rate=100.0,
            current_entry_profit=-0.04,
            current_exit_profit=-0.04,
            side='long',
        )

        assert result is None

    def test_confirm_trade_entry_blocks_during_cooldown(self, default_config):
        strategy = DCAStrategy(default_config)
        now = datetime.now()
        strategy.risk_manager.trigger_cooldown(now)

        result = strategy.confirm_trade_entry(
            pair='BTC/USDT',
            order_type='limit',
            amount=1.0,
            rate=100.0,
            time_in_force='GTC',
            current_time=now,
            entry_tag=None,
            side='long',
            wallet_balance=1000.0,
        )

        assert result is False

    def test_confirm_trade_entry_blocks_on_tracked_daily_loss_limit(self, default_config):
        strategy = DCAStrategy(default_config)
        now = datetime.now()
        strategy.risk_manager.record_daily_loss(60.0, now)

        result = strategy.confirm_trade_entry(
            pair='BTC/USDT',
            order_type='limit',
            amount=1.0,
            rate=100.0,
            time_in_force='GTC',
            current_time=now,
            entry_tag=None,
            side='long',
            wallet_balance=1000.0,
        )

        assert result is False

    def test_confirm_trade_entry_blocks_on_drawdown(self, default_config):
        strategy = DCAStrategy(default_config)

        result = strategy.confirm_trade_entry(
            pair='BTC/USDT',
            order_type='limit',
            amount=1.0,
            rate=100.0,
            time_in_force='GTC',
            current_time=datetime.now(),
            entry_tag=None,
            side='long',
            wallet_balance=800.0,
        )

        assert result is False

    def test_confirm_trade_entry_respects_slippage(self, default_config):
        strategy = DCAStrategy(default_config)
        strategy.expected_entry_price = {'BTC/USDT': 100.0}

        result = strategy.confirm_trade_entry(
            pair='BTC/USDT',
            order_type='limit',
            amount=1.0,
            rate=101.0,
            time_in_force='GTC',
            current_time=datetime.now(),
            entry_tag=None,
            side='long',
            wallet_balance=1000.0,
        )

        assert result is False

    def test_confirm_trade_exit_tracks_loss_and_triggers_cooldown(self, default_config):
        strategy = DCAStrategy(default_config)
        trade = MagicMock()
        trade.stake_amount = 100.0

        now = datetime.now()
        result = strategy.confirm_trade_exit(
            pair='BTC/USDT',
            trade=trade,
            order_type='limit',
            amount=1.0,
            rate=95.0,
            time_in_force='GTC',
            exit_reason='exit_signal',
            current_time=now,
            current_rate=95.0,
            current_profit=-0.03,
            side='long',
            wallet_balance=970.0,
        )

        assert result is True
        assert strategy.risk_manager.get_daily_loss(now) == pytest.approx(3.0)
        assert strategy.risk_manager.check_cooldown(now) is False


class TestDCAStrategyBasicConfiguration:
    """基本設定のテスト"""

    def test_base_timeframe_is_fifteen_minutes(self, default_config):
        strategy = DCAStrategy(default_config)
        assert strategy.timeframe == '15m'

    def test_balanced_configuration_uses_tighter_risk(self, default_config):
        strategy = DCAStrategyBalanced(default_config)
        assert strategy.stoploss == -0.05
        assert strategy.trailing_stop_positive == 0.006
        assert strategy.trailing_stop_positive_offset == 0.015
