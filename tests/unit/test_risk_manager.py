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


class TestRiskManagerDailyLossTracking:
    """RiskManagerの日次損失追跡機能のテスト"""

    def test_record_daily_loss_accumulates(self):
        """同日の損失が累積される"""
        rm = RiskManager(100000, 0.2, 0.05, 0.15, 3, 24)
        t1 = datetime(2024, 6, 1, 10, 0)
        t2 = datetime(2024, 6, 1, 14, 0)
        rm.record_daily_loss(500.0, t1)
        rm.record_daily_loss(300.0, t2)
        assert rm.get_daily_loss(t2) == 800.0

    def test_record_daily_loss_resets_on_new_day(self):
        """日付が変わるとリセットされる"""
        rm = RiskManager(100000, 0.2, 0.05, 0.15, 3, 24)
        t1 = datetime(2024, 6, 1, 23, 0)
        t2 = datetime(2024, 6, 2, 1, 0)
        rm.record_daily_loss(500.0, t1)
        rm.record_daily_loss(100.0, t2)
        assert rm.get_daily_loss(t2) == 100.0

    def test_check_daily_loss_limit_tracked_passes(self):
        """日次損失が上限以内の場合True"""
        rm = RiskManager(100000, 0.2, 0.05, 0.15, 3, 24)
        rm.record_daily_loss(2000.0, datetime(2024, 6, 1))
        # starting_balance=50000, limit=0.05 -> max_loss=2500
        assert rm.check_daily_loss_limit_tracked(datetime(2024, 6, 1), 50000) is True

    def test_check_daily_loss_limit_tracked_fails(self):
        """日次損失が上限を超えた場合False"""
        rm = RiskManager(100000, 0.2, 0.05, 0.15, 3, 24)
        rm.record_daily_loss(3000.0, datetime(2024, 6, 1))
        # starting_balance=50000, limit=0.05 -> max_loss=2500
        assert rm.check_daily_loss_limit_tracked(datetime(2024, 6, 1), 50000) is False


class TestRiskManagerCircuitBreakerTracking:
    """RiskManagerのサーキットブレーカー追跡機能のテスト"""

    def test_update_balance_tracks_peak(self):
        """ピークバランスが更新される"""
        rm = RiskManager(100000, 0.2, 0.05, 0.15, 3, 24)
        rm.update_balance(50000)
        rm.update_balance(55000)
        rm.update_balance(52000)
        assert rm.peak_balance == 55000

    def test_check_circuit_breaker_tracked_passes(self):
        """ドローダウンが閾値以内の場合True"""
        rm = RiskManager(100000, 0.2, 0.05, 0.15, 3, 24)
        rm.update_balance(50000)
        # DD = (50000-45000)/50000 = 0.10 < 0.15
        assert rm.check_circuit_breaker_tracked(45000) is True

    def test_check_circuit_breaker_tracked_fails(self):
        """ドローダウンが閾値を超えた場合False"""
        rm = RiskManager(100000, 0.2, 0.05, 0.15, 3, 24)
        rm.update_balance(50000)
        # DD = (50000-42000)/50000 = 0.16 > 0.15
        assert rm.check_circuit_breaker_tracked(42000) is False

    def test_check_circuit_breaker_tracked_no_peak(self):
        """ピーク未設定時はTrue（取引可能）"""
        rm = RiskManager(100000, 0.2, 0.05, 0.15, 3, 24)
        assert rm.check_circuit_breaker_tracked(50000) is True
