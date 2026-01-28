"""
リスク管理モジュールのユニットテスト
"""

from datetime import datetime, timedelta

from user_data.strategies.risk_manager import RiskManager


class TestRiskManager:
    """RiskManagerクラスのテストスイート"""

    def test_max_position_size_check(self):
        """最大ポジションサイズチェック"""
        risk_manager = RiskManager(
            max_position_size=1000.0,
            max_portfolio_allocation=0.3,
            daily_loss_limit=0.05,
            circuit_breaker_drawdown=0.15,
            max_consecutive_losses=3,
            cooldown_hours=24
        )

        # 許容範囲内のポジションサイズ
        assert risk_manager.check_position_size(500.0) is True
        assert risk_manager.check_position_size(1000.0) is True

        # 上限超過
        assert risk_manager.check_position_size(1500.0) is False

    def test_portfolio_allocation_limit(self):
        """ポートフォリオ配分制限のチェック"""
        risk_manager = RiskManager(
            max_position_size=1000.0,
            max_portfolio_allocation=0.3,  # 30%
            daily_loss_limit=0.05,
            circuit_breaker_drawdown=0.15,
            max_consecutive_losses=3,
            cooldown_hours=24
        )

        total_portfolio_value = 10000.0

        # 30%以内（3000.0）
        assert risk_manager.check_portfolio_limit(2000.0, total_portfolio_value) is True
        assert risk_manager.check_portfolio_limit(3000.0, total_portfolio_value) is True

        # 30%超過
        assert risk_manager.check_portfolio_limit(3500.0, total_portfolio_value) is False

    def test_daily_loss_limit(self):
        """1日の損失上限チェック"""
        risk_manager = RiskManager(
            max_position_size=1000.0,
            max_portfolio_allocation=0.3,
            daily_loss_limit=0.05,  # 5%
            circuit_breaker_drawdown=0.15,
            max_consecutive_losses=3,
            cooldown_hours=24
        )

        starting_balance = 10000.0

        # 5%以内の損失（-500.0）
        assert risk_manager.check_daily_loss_limit(-300.0, starting_balance) is True
        assert risk_manager.check_daily_loss_limit(-500.0, starting_balance) is True

        # 5%超過の損失
        assert risk_manager.check_daily_loss_limit(-600.0, starting_balance) is False

    def test_circuit_breaker_on_drawdown(self):
        """ドローダウンでのサーキットブレーカー"""
        risk_manager = RiskManager(
            max_position_size=1000.0,
            max_portfolio_allocation=0.3,
            daily_loss_limit=0.05,
            circuit_breaker_drawdown=0.15,  # 15%
            max_consecutive_losses=3,
            cooldown_hours=24
        )

        peak_balance = 10000.0

        # 15%以内のドローダウン
        current_balance_1 = 8600.0  # -14%
        assert risk_manager.check_circuit_breaker(current_balance_1, peak_balance) is True

        # 15%を超えるドローダウン
        current_balance_2 = 8400.0  # -16%
        assert risk_manager.check_circuit_breaker(current_balance_2, peak_balance) is False

    def test_consecutive_loss_protection(self):
        """連続損失プロテクション"""
        risk_manager = RiskManager(
            max_position_size=1000.0,
            max_portfolio_allocation=0.3,
            daily_loss_limit=0.05,
            circuit_breaker_drawdown=0.15,
            max_consecutive_losses=3,
            cooldown_hours=24
        )

        # 3連続未満
        risk_manager.record_trade_result(is_loss=True)
        assert risk_manager.check_consecutive_losses() is True

        risk_manager.record_trade_result(is_loss=True)
        assert risk_manager.check_consecutive_losses() is True

        # 3連続到達
        risk_manager.record_trade_result(is_loss=True)
        assert risk_manager.check_consecutive_losses() is False

        # 利益で連続損失カウントリセット
        risk_manager.record_trade_result(is_loss=False)
        assert risk_manager.check_consecutive_losses() is True

    def test_cooldown_after_stoploss(self):
        """ストップロス後のクールダウン"""
        risk_manager = RiskManager(
            max_position_size=1000.0,
            max_portfolio_allocation=0.3,
            daily_loss_limit=0.05,
            circuit_breaker_drawdown=0.15,
            max_consecutive_losses=3,
            cooldown_hours=24
        )

        # クールダウン設定前
        assert risk_manager.check_cooldown() is True

        # ストップロス発生を記録
        current_time = datetime.now()
        risk_manager.trigger_cooldown(current_time)

        # クールダウン期間中
        assert risk_manager.check_cooldown(current_time) is False

        # 24時間後
        after_cooldown = current_time + timedelta(hours=24, minutes=1)
        assert risk_manager.check_cooldown(after_cooldown) is True
