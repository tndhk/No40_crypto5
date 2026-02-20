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

from dca_strategy import DCAStrategy


class DCAStrategyBalanced(DCAStrategy):
    """Lower-risk profile for Dry Run recovery."""

    minimal_roi = {
        "0": 0.035,
        "120": 0.018,
        "360": 0.008,
    }
    stoploss = -0.08

    trailing_stop_positive = 0.008
    trailing_stop_positive_offset = 0.02

    max_entry_position_adjustment = 2

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["enter_long"] = 0

        dataframe.loc[
            (dataframe["rsi"] <= 45)
            & (dataframe["volume"] > 0.9 * dataframe["volume_sma_20"])
            & (dataframe["ema_50"] >= dataframe["ema_200"])
            & (dataframe["adx"] >= 18),
            "enter_long",
        ] = 1

        if len(dataframe) > 0:
            pair = metadata.get("pair", "")
            self.expected_entry_price[pair] = dataframe["close"].iloc[-1]

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["exit_long"] = 0

        dataframe.loc[
            (dataframe["rsi"] >= 64)
            | ((dataframe["rsi"] >= 58) & (dataframe["close"] < dataframe["ema_50"])),
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
        adjustment = super().adjust_trade_position(
            trade=trade,
            current_time=current_time,
            current_rate=current_rate,
            current_profit=current_profit,
            min_stake=min_stake,
            max_stake=max_stake,
            current_entry_rate=current_entry_rate,
            current_exit_rate=current_exit_rate,
            current_entry_profit=current_entry_profit,
            current_exit_profit=current_exit_profit,
            side=side,
            **kwargs,
        )
        if adjustment is None or adjustment <= 0:
            return adjustment

        current_stake = getattr(trade, "stake_amount", 0.0) if trade else 0.0

        dca_cap = max(current_stake * 0.35, 0.0)
        if max_stake:
            dca_cap = min(dca_cap, max_stake * 0.2)

        if dca_cap <= 0:
            return None
        return min(adjustment, dca_cap)
