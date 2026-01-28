"""
スリッページ保護モジュール

期待価格と実際の注文価格の乖離をチェックし、
閾値を超える場合は注文をブロックする。
"""


class SlippageProtection:
    """
    スリッページ保護クラス

    注文時の価格スリッページを監視し、
    許容範囲を超える場合は注文を拒否する。
    """

    def __init__(self, max_slippage_percent: float = 0.5):
        """
        Args:
            max_slippage_percent: 最大許容スリッページ率（%）
                                 デフォルト0.5%
        """
        self.max_slippage_percent = max_slippage_percent

    def calculate_slippage_percentage(
        self,
        expected_price: float,
        actual_price: float
    ) -> float:
        """
        スリッページ率を計算

        Args:
            expected_price: 期待価格
            actual_price: 実際の価格

        Returns:
            スリッページ率（%）
            正の値: 期待より高い価格（不利）
            負の値: 期待より低い価格（有利）
        """
        if expected_price == 0:
            return 0.0

        slippage = ((actual_price - expected_price) / expected_price) * 100
        return slippage

    def check_slippage(
        self,
        expected_price: float,
        actual_price: float
    ) -> bool:
        """
        スリッページが許容範囲内かチェック

        Args:
            expected_price: 期待価格
            actual_price: 実際の価格

        Returns:
            True: 注文許可（許容範囲内）
            False: 注文拒否（許容範囲超過）
        """
        slippage_percent = self.calculate_slippage_percentage(
            expected_price, actual_price
        )

        # 絶対値で判定（プラスでもマイナスでも大きすぎる場合は拒否）
        return abs(slippage_percent) <= self.max_slippage_percent
