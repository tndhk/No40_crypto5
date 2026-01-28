"""
市場環境判定モジュール

EMA50/200とADXを使用してトレンドを判定し、
ベア相場でのエントリー抑制機能を提供。
"""

from typing import Literal
import pandas as pd
from pandas import DataFrame
import talib.abstract as ta
from user_data.strategies.indicators import calculate_ema


MarketRegimeType = Literal['bullish', 'bearish', 'sideways']


class MarketRegime:
    """
    市場環境判定クラス

    上昇トレンド（ブル）、下降トレンド（ベア）、
    サイドウェイ（レンジ）の3つの市場環境を判定。
    """

    def __init__(self, adx_threshold: float = 25.0):
        """
        Args:
            adx_threshold: ADXの閾値（デフォルト25.0）
                          この値以上でトレンド相場と判定
        """
        self.adx_threshold = adx_threshold

    def detect_regime(self, dataframe: DataFrame) -> MarketRegimeType:
        """
        市場環境を判定

        Args:
            dataframe: EMA50, EMA200, ADXを含むDataFrame

        Returns:
            'bullish', 'bearish', 'sideways'のいずれか
        """
        # 指標が不足している場合はsidewaysを返す
        required_columns = ['ema_50', 'ema_200', 'adx']
        if not all(col in dataframe.columns for col in required_columns):
            return 'sideways'

        # 最新の値を取得
        latest = dataframe.iloc[-1]
        ema_50 = latest['ema_50']
        ema_200 = latest['ema_200']
        adx = latest['adx']

        # ADXが閾値未満の場合はサイドウェイ
        if pd.isna(adx) or adx < self.adx_threshold:
            return 'sideways'

        # EMA50 > EMA200: 上昇トレンド
        if ema_50 > ema_200:
            return 'bullish'

        # EMA50 < EMA200: 下降トレンド
        if ema_50 < ema_200:
            return 'bearish'

        # その他（ほぼ等しい場合）はサイドウェイ
        return 'sideways'

    def should_suppress_entry(self, regime: MarketRegimeType) -> bool:
        """
        エントリー抑制の判定

        Args:
            regime: 市場環境（'bullish', 'bearish', 'sideways'）

        Returns:
            True: エントリー抑制, False: エントリー許可
        """
        # ベア相場の場合のみエントリーを抑制
        return regime == 'bearish'

    def add_regime_indicators(self, dataframe: DataFrame) -> DataFrame:
        """
        市場環境判定に必要な指標をデータフレームに追加

        Args:
            dataframe: OHLCVデータを含むDataFrame

        Returns:
            EMA50, EMA200, ADXが追加されたDataFrame
        """
        df = dataframe.copy()

        # EMA50を計算
        df = calculate_ema(df, period=50)

        # EMA200を計算
        df = calculate_ema(df, period=200)

        # ADXを計算
        df['adx'] = ta.ADX(df, timeperiod=14)

        return df
