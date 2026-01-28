"""
DCA（ドルコスト平均法）戦略

RSIベースのエントリーシグナルと、DCA（ドルコスト平均法）による
ポジション追加を行う戦略。
"""

from datetime import datetime
from typing import Optional
import pandas as pd
from pandas import DataFrame
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter
from freqtrade.persistence import Trade
from user_data.strategies.indicators import calculate_rsi
from user_data.strategies.market_regime import MarketRegime
from user_data.strategies.slippage_protection import SlippageProtection


class DCAStrategy(IStrategy):
    """
    DCA戦略クラス

    RSIが過売状態（30以下）でエントリーし、
    損失が拡大した場合にDCAで追加購入を行う。
    """

    # 戦略メタデータ
    INTERFACE_VERSION = 3
    can_short = False

    # 基本設定
    timeframe = '5m'
    stoploss = -0.25  # -25%
    minimal_roi = {
        "0": 0.15,    # 15%
        "60": 0.10,   # 1時間後: 10%
        "120": 0.05,  # 2時間後: 5%
    }

    # Hyperoptパラメータ
    dca_threshold_1 = DecimalParameter(
        -0.10, -0.05, default=-0.07, decimals=2, space='buy', optimize=True
    )
    dca_threshold_2 = DecimalParameter(
        -0.15, -0.08, default=-0.12, decimals=2, space='buy', optimize=True
    )
    dca_threshold_3 = DecimalParameter(
        -0.20, -0.12, default=-0.18, decimals=2, space='buy', optimize=True
    )

    take_profit_threshold = DecimalParameter(
        0.05, 0.15, default=0.08, decimals=2, space='sell', optimize=True
    )
    take_profit_sell_ratio = DecimalParameter(
        0.25, 0.50, default=0.33, decimals=2, space='sell', optimize=True
    )

    # ポジション調整設定
    position_adjustment_enable = True
    max_entry_position_adjustment = 3  # 最大3回のDCA

    def __init__(self, config: dict) -> None:
        """
        戦略の初期化

        Args:
            config: Freqtrade設定
        """
        super().__init__(config)

        # 市場環境判定モジュール
        self.market_regime = MarketRegime(adx_threshold=25.0)

        # スリッページ保護モジュール
        self.slippage_protection = SlippageProtection(max_slippage_percent=0.5)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        指標を計算してデータフレームに追加

        Args:
            dataframe: OHLCVデータ
            metadata: ペア情報

        Returns:
            指標が追加されたDataFrame
        """
        # RSIを計算
        dataframe_with_rsi = calculate_rsi(dataframe, period=14)
        dataframe['rsi'] = dataframe_with_rsi['rsi_14']

        # 市場環境判定指標を追加
        dataframe = self.market_regime.add_regime_indicators(dataframe)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        エントリーシグナルを生成

        Args:
            dataframe: 指標が計算されたDataFrame
            metadata: ペア情報

        Returns:
            エントリーシグナルが追加されたDataFrame
        """
        dataframe['enter_long'] = 0

        # 市場環境を判定
        regime = self.market_regime.detect_regime(dataframe)

        # ベア相場ではエントリーを抑制
        if self.market_regime.should_suppress_entry(regime):
            return dataframe

        # RSIが30以下（過売状態）でエントリー
        dataframe.loc[
            (dataframe['rsi'] <= 30),
            'enter_long'
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        エグジットシグナルを生成

        Args:
            dataframe: 指標が計算されたDataFrame
            metadata: ペア情報

        Returns:
            エグジットシグナルが追加されたDataFrame
        """
        dataframe['exit_long'] = 0

        # RSIが70以上（過買状態）でエグジット
        dataframe.loc[
            (dataframe['rsi'] >= 70),
            'exit_long'
        ] = 1

        return dataframe

    def custom_stake_amount(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_stake: float,
        min_stake: Optional[float],
        max_stake: float,
        leverage: float,
        entry_tag: Optional[str],
        side: str,
        **kwargs
    ) -> float:
        """
        カスタムステーク額を計算

        Args:
            pair: 通貨ペア
            current_time: 現在時刻
            current_rate: 現在のレート
            proposed_stake: 提案されたステーク額
            min_stake: 最小ステーク額
            max_stake: 最大ステーク額
            leverage: レバレッジ
            entry_tag: エントリータグ
            side: 'long' or 'short'
            **kwargs: その他のパラメータ

        Returns:
            カスタムステーク額
        """
        # DCAエントリーの場合は1.5倍のステーク
        if entry_tag and entry_tag.startswith('dca_'):
            return proposed_stake * 1.5

        # 初回エントリーは提案額をそのまま使用
        return proposed_stake

    def adjust_trade_position(
        self,
        trade: Optional[Trade],
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        min_stake: Optional[float],
        max_stake: float,
        current_entry_rate: float,
        current_exit_rate: float,
        current_entry_profit: float,
        current_exit_profit: float,
        side: str,
        **kwargs
    ) -> Optional[float]:
        """
        ポジション調整（DCA追加購入）

        Args:
            trade: トレードオブジェクト
            current_time: 現在時刻
            current_rate: 現在のレート
            current_profit: 現在の利益率
            min_stake: 最小ステーク額
            max_stake: 最大ステーク額
            current_entry_rate: 現在のエントリーレート
            current_exit_rate: 現在のエグジットレート
            current_entry_profit: 現在のエントリー利益率
            current_exit_profit: 現在のエグジット利益率
            side: 'long' or 'short'
            **kwargs: その他のパラメータ

        Returns:
            追加購入額（なしの場合None）
        """
        if not trade:
            return None

        # 利益が出ている場合はDCAなし
        if current_profit > 0:
            return None

        # DCA閾値チェック
        filled_entries = trade.nr_of_successful_entries

        if filled_entries == 1 and current_profit <= self.dca_threshold_1.value:
            # 1回目のDCA
            return max_stake * 0.5

        if filled_entries == 2 and current_profit <= self.dca_threshold_2.value:
            # 2回目のDCA
            return max_stake * 0.5

        if filled_entries == 3 and current_profit <= self.dca_threshold_3.value:
            # 3回目のDCA
            return max_stake * 0.5

        return None
