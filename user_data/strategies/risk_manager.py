"""
リスク管理モジュール

トレーディングにおけるリスク管理機能を提供する。
"""

from datetime import datetime, timedelta
from typing import Optional


class RiskManager:
    """
    リスク管理クラス

    最大ポジションサイズ、ポートフォリオ配分制限、1日の損失上限、
    ドローダウンサーキットブレーカー、連続損失プロテクション、
    ストップロス後のクールダウン機能を提供。
    """

    def __init__(
        self,
        max_position_size: float,
        max_portfolio_allocation: float,
        daily_loss_limit: float,
        circuit_breaker_drawdown: float,
        max_consecutive_losses: int,
        cooldown_hours: int
    ):
        """
        Args:
            max_position_size: 最大ポジションサイズ（絶対値）
            max_portfolio_allocation: 最大ポートフォリオ配分比率（0-1）
            daily_loss_limit: 1日の損失上限比率（0-1）
            circuit_breaker_drawdown: サーキットブレーカー発動ドローダウン比率（0-1）
            max_consecutive_losses: 最大連続損失回数
            cooldown_hours: クールダウン時間（時間単位）
        """
        self.max_position_size = max_position_size
        self.max_portfolio_allocation = max_portfolio_allocation
        self.daily_loss_limit = daily_loss_limit
        self.circuit_breaker_drawdown = circuit_breaker_drawdown
        self.max_consecutive_losses = max_consecutive_losses
        self.cooldown_hours = cooldown_hours

        # 内部状態
        self.consecutive_loss_count = 0
        self.cooldown_until: Optional[datetime] = None

    def check_position_size(self, position_size: float) -> bool:
        """
        最大ポジションサイズチェック

        Args:
            position_size: チェックするポジションサイズ

        Returns:
            True: 許容範囲内, False: 上限超過
        """
        return position_size <= self.max_position_size

    def check_portfolio_limit(self, position_size: float, total_portfolio_value: float) -> bool:
        """
        ポートフォリオ配分制限のチェック

        Args:
            position_size: チェックするポジションサイズ
            total_portfolio_value: ポートフォリオの総価値

        Returns:
            True: 許容範囲内, False: 上限超過
        """
        max_allowed = total_portfolio_value * self.max_portfolio_allocation
        return position_size <= max_allowed

    def check_daily_loss_limit(self, daily_loss: float, starting_balance: float) -> bool:
        """
        1日の損失上限チェック

        Args:
            daily_loss: 1日の損失額（負の値）
            starting_balance: 開始時の残高

        Returns:
            True: 許容範囲内, False: 上限超過
        """
        max_loss = starting_balance * self.daily_loss_limit
        return abs(daily_loss) <= max_loss

    def check_circuit_breaker(self, current_balance: float, peak_balance: float) -> bool:
        """
        ドローダウンでのサーキットブレーカー

        Args:
            current_balance: 現在の残高
            peak_balance: ピーク時の残高

        Returns:
            True: 取引可能, False: サーキットブレーカー発動
        """
        drawdown = (peak_balance - current_balance) / peak_balance
        return drawdown < self.circuit_breaker_drawdown

    def record_trade_result(self, is_loss: bool) -> None:
        """
        トレード結果を記録

        Args:
            is_loss: 損失トレードの場合True、利益トレードの場合False
        """
        if is_loss:
            self.consecutive_loss_count += 1
        else:
            self.consecutive_loss_count = 0

    def check_consecutive_losses(self) -> bool:
        """
        連続損失プロテクション

        Returns:
            True: 取引可能, False: 連続損失上限到達
        """
        return self.consecutive_loss_count < self.max_consecutive_losses

    def trigger_cooldown(self, current_time: datetime) -> None:
        """
        クールダウンを開始

        Args:
            current_time: 現在時刻
        """
        self.cooldown_until = current_time + timedelta(hours=self.cooldown_hours)

    def check_cooldown(self, current_time: Optional[datetime] = None) -> bool:
        """
        クールダウン期間チェック

        Args:
            current_time: チェックする時刻（デフォルトは現在時刻）

        Returns:
            True: 取引可能, False: クールダウン期間中
        """
        if self.cooldown_until is None:
            return True

        check_time = current_time if current_time else datetime.now()
        return check_time >= self.cooldown_until
