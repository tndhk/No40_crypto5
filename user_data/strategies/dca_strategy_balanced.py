"""
Balanced variant of DCAStrategy.

Designed for Dry Run stabilization:
- tighter entries in trend-favorable conditions
- faster exits to reduce capital lock
- smaller DCA increments to avoid wallet exhaustion
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from freqtrade.persistence import Trade
from pandas import DataFrame

try:
    from dca_strategy import DCAStrategy
except ModuleNotFoundError:
    from .dca_strategy import DCAStrategy


class DCAStrategyBalanced(DCAStrategy):
    """Lower-risk profile for Dry Run recovery."""

    minimal_roi = {
        "0": 0.025,
        "90": 0.012,
        "240": 0.005,
    }
    stoploss = -0.05

    trailing_stop_positive = 0.006
    trailing_stop_positive_offset = 0.015

    max_entry_position_adjustment = 0

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["enter_long"] = 0

        dataframe.loc[
            (dataframe["rsi"] <= 42)
            & (dataframe["volume"] >= dataframe["volume_sma_20"])
            & (dataframe["ema_50"] > dataframe["ema_200"])
            & (dataframe["adx"] >= 20)
            & (dataframe["close"] > dataframe["open"])
            & (dataframe["close"] > dataframe["close"].shift(1))
            & (dataframe["volatility_ratio"] <= self.custom_info["volatility_threshold"]),
            "enter_long",
        ] = 1

        if len(dataframe) > 0:
            pair = metadata.get("pair", "")
            self.expected_entry_price[pair] = dataframe["close"].iloc[-1]

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["exit_long"] = 0

        dataframe.loc[
            (dataframe["rsi"] >= 62)
            | ((dataframe["rsi"] >= 56) & (dataframe["close"] < dataframe["ema_50"])),
            "exit_long",
        ] = 1

        return dataframe

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
        side: str = "long",
        **kwargs,
    ) -> Optional[float]:
        return None
