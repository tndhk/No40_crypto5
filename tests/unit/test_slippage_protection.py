"""
スリッページ保護モジュールのユニットテスト
"""

import pytest
from user_data.strategies.slippage_protection import SlippageProtection


class TestSlippageProtection:
    """SlippageProtectionクラスのテストスイート"""

    def test_allows_order_within_threshold(self):
        """許容範囲内の注文を許可"""
        protection = SlippageProtection(max_slippage_percent=0.5)

        expected_price = 40000.0
        actual_price = 40100.0  # +0.25% (許容範囲内)

        result = protection.check_slippage(expected_price, actual_price)

        # 注文が許可されることを確認
        assert result is True

    def test_blocks_order_exceeding_threshold(self):
        """許容範囲超過の注文をブロック"""
        protection = SlippageProtection(max_slippage_percent=0.5)

        expected_price = 40000.0
        actual_price = 40300.0  # +0.75% (許容範囲超過)

        result = protection.check_slippage(expected_price, actual_price)

        # 注文がブロックされることを確認
        assert result is False

    def test_allows_order_at_exact_threshold(self):
        """閾値ちょうどの注文を許可"""
        protection = SlippageProtection(max_slippage_percent=0.5)

        expected_price = 40000.0
        actual_price = 40200.0  # +0.5% (閾値ちょうど)

        result = protection.check_slippage(expected_price, actual_price)

        # 注文が許可されることを確認
        assert result is True

    def test_negative_slippage_within_threshold(self):
        """マイナス方向のスリッページ（有利な価格）"""
        protection = SlippageProtection(max_slippage_percent=0.5)

        expected_price = 40000.0
        actual_price = 39900.0  # -0.25% (有利な方向)

        result = protection.check_slippage(expected_price, actual_price)

        # 注文が許可されることを確認（有利な方向は常に許可）
        assert result is True

    def test_negative_slippage_exceeding_threshold(self):
        """マイナス方向のスリッページが閾値超過"""
        protection = SlippageProtection(max_slippage_percent=0.5)

        expected_price = 40000.0
        actual_price = 39700.0  # -0.75% (不利な方向に大きい)

        result = protection.check_slippage(expected_price, actual_price)

        # 大きなマイナススリッページもブロック
        assert result is False

    def test_calculates_slippage_percentage(self):
        """スリッページ率の計算"""
        protection = SlippageProtection(max_slippage_percent=0.5)

        expected_price = 40000.0
        actual_price = 40200.0  # +0.5%

        slippage_percent = protection.calculate_slippage_percentage(
            expected_price, actual_price
        )

        # 0.5%のスリッページが計算されることを確認
        assert abs(slippage_percent - 0.5) < 0.01

    def test_calculates_negative_slippage_percentage(self):
        """マイナススリッページ率の計算"""
        protection = SlippageProtection(max_slippage_percent=0.5)

        expected_price = 40000.0
        actual_price = 39800.0  # -0.5%

        slippage_percent = protection.calculate_slippage_percentage(
            expected_price, actual_price
        )

        # -0.5%のスリッページが計算されることを確認
        assert abs(slippage_percent - (-0.5)) < 0.01

    def test_zero_slippage(self):
        """スリッページなし（価格一致）"""
        protection = SlippageProtection(max_slippage_percent=0.5)

        expected_price = 40000.0
        actual_price = 40000.0  # 0%

        result = protection.check_slippage(expected_price, actual_price)
        slippage_percent = protection.calculate_slippage_percentage(
            expected_price, actual_price
        )

        # スリッページなしで許可
        assert result is True
        assert slippage_percent == 0.0
