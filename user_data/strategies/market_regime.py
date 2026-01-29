"""
市場環境判定モジュール

EMA50/200とADXを使用してトレンドを判定し、
ベア相場でのエントリー抑制機能を提供。
"""

from typing import Literal

import pandas as pd
import talib.abstract as ta
from pandas import DataFrame

from indicators import calculate_ema

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

    def should_suppress_entry(self, dataframe: DataFrame) -> bool:
        """
        エントリー抑制の判定

        Args:
            dataframe: EMA50, EMA200, ADX, RSIを含むDataFrame

        Returns:
            True: エントリー抑制, False: エントリー許可

        ロジック:
            - 非常に強いベア相場（EMA50 < EMA200 かつ ADX > 35 かつ RSI >= 15）のみエントリーを抑制
            - 中程度のベア相場（ADX <= 35）はエントリーを許可
            - RSIが極端に低い（RSI < 15）場合はベア相場でもエントリーを許可
        """
        # 指標が不足している場合はエントリーを許可（抑制しない）
        required_columns = ['ema_50', 'ema_200', 'adx']
        if not all(col in dataframe.columns for col in required_columns):
            return False

        # 最新の値を取得
        latest = dataframe.iloc[-1]
        ema_50 = latest['ema_50']
        ema_200 = latest['ema_200']
        adx = latest['adx']

        # RSIが存在する場合は取得、なければNone
        rsi = latest.get('rsi', None)

        # ベア相場でない場合はエントリーを許可
        if ema_50 >= ema_200:
            return False

        # ADXが35以下（中程度以下のトレンド）の場合はエントリーを許可
        if pd.isna(adx) or adx <= 35.0:
            return False

        # RSIが15未満（極端な過売）の場合はエントリーを許可
        if rsi is not None and not pd.isna(rsi) and rsi < 15.0:
            return False

        # 非常に強いベア相場（EMA50 < EMA200 かつ ADX > 35 かつ RSI >= 15）の場合はエントリーを抑制
        return True

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
