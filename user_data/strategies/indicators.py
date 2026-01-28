"""
テクニカル指標計算モジュール

Freqtrade戦略で使用するテクニカル指標を計算する関数群
"""
import pandas as pd
import numpy as np
from pandas import DataFrame
import talib.abstract as ta


def calculate_ema(dataframe: DataFrame, period: int) -> DataFrame:
    """
    EMA（指数移動平均）を計算

    Args:
        dataframe: OHLCVデータを含むDataFrame
        period: EMA期間

    Returns:
        EMAカラムが追加されたDataFrame
    """
    df = dataframe.copy()
    df[f'ema_{period}'] = ta.EMA(df, timeperiod=period)
    return df


def calculate_rsi(dataframe: DataFrame, period: int = 14) -> DataFrame:
    """
    RSI（相対力指数）を計算

    Args:
        dataframe: OHLCVデータを含むDataFrame
        period: RSI期間（デフォルト14）

    Returns:
        RSIカラムが追加されたDataFrame
    """
    df = dataframe.copy()
    df[f'rsi_{period}'] = ta.RSI(df, timeperiod=period)
    return df


def calculate_bollinger_bands(
    dataframe: DataFrame,
    period: int = 20,
    std: float = 2.0
) -> DataFrame:
    """
    ボリンジャーバンドを計算

    Args:
        dataframe: OHLCVデータを含むDataFrame
        period: 移動平均期間（デフォルト20）
        std: 標準偏差の倍数（デフォルト2.0）

    Returns:
        bb_upper, bb_middle, bb_lowerカラムが追加されたDataFrame
    """
    df = dataframe.copy()
    bollinger = ta.BBANDS(df, timeperiod=period, nbdevup=float(std), nbdevdn=float(std))

    df['bb_upper'] = bollinger['upperband']
    df['bb_middle'] = bollinger['middleband']
    df['bb_lower'] = bollinger['lowerband']

    return df


def calculate_volume_sma(dataframe: DataFrame, period: int) -> DataFrame:
    """
    出来高の単純移動平均を計算

    Args:
        dataframe: OHLCVデータを含むDataFrame
        period: SMA期間

    Returns:
        volume_sma_{period}カラムが追加されたDataFrame
    """
    df = dataframe.copy()
    df[f'volume_sma_{period}'] = df['volume'].rolling(window=period).mean()
    return df
