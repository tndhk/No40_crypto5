"""
市場環境判定モジュールのユニットテスト
"""

import pytest
import pandas as pd
from pandas import DataFrame
from user_data.strategies.market_regime import MarketRegime


class TestMarketRegime:
    """MarketRegimeクラスのテストスイート"""

    def test_detects_bullish_regime(self):
        """上昇トレンド（ブル相場）を検出"""
        market_regime = MarketRegime()

        # 上昇トレンドのテストデータ
        dataframe = pd.DataFrame({
            'close': [100.0, 102.0, 105.0, 108.0, 110.0],
            'ema_50': [98.0, 99.0, 100.0, 102.0, 104.0],
            'ema_200': [95.0, 96.0, 97.0, 98.0, 99.0],
            'adx': [30.0, 32.0, 35.0, 38.0, 40.0],  # ADX > 25
        })

        regime = market_regime.detect_regime(dataframe)

        # 'bullish'が返されることを確認
        assert regime == 'bullish'

    def test_detects_bearish_regime(self):
        """下降トレンド（ベア相場）を検出"""
        market_regime = MarketRegime()

        # 下降トレンドのテストデータ
        dataframe = pd.DataFrame({
            'close': [110.0, 108.0, 105.0, 102.0, 100.0],
            'ema_50': [112.0, 110.0, 108.0, 106.0, 104.0],
            'ema_200': [115.0, 114.0, 113.0, 112.0, 111.0],
            'adx': [30.0, 32.0, 35.0, 38.0, 40.0],  # ADX > 25
        })

        regime = market_regime.detect_regime(dataframe)

        # 'bearish'が返されることを確認
        assert regime == 'bearish'

    def test_detects_sideways_regime(self):
        """サイドウェイ（レンジ相場）を検出"""
        market_regime = MarketRegime()

        # レンジ相場のテストデータ（ADX < 25）
        dataframe = pd.DataFrame({
            'close': [100.0, 101.0, 100.5, 99.5, 100.0],
            'ema_50': [100.0, 100.2, 100.1, 99.9, 100.0],
            'ema_200': [100.0, 100.1, 100.0, 99.9, 100.0],
            'adx': [15.0, 16.0, 18.0, 20.0, 22.0],  # ADX < 25
        })

        regime = market_regime.detect_regime(dataframe)

        # 'sideways'が返されることを確認
        assert regime == 'sideways'

    def test_entry_suppression_in_bear_market(self):
        """ベア相場でのエントリー抑制"""
        market_regime = MarketRegime()

        # ベア相場
        should_suppress = market_regime.should_suppress_entry('bearish')
        assert should_suppress is True

        # ブル相場（エントリー許可）
        should_not_suppress = market_regime.should_suppress_entry('bullish')
        assert should_not_suppress is False

        # サイドウェイ（エントリー許可）
        should_not_suppress_sideways = market_regime.should_suppress_entry('sideways')
        assert should_not_suppress_sideways is False

    def test_add_regime_indicators(self):
        """市場環境指標をデータフレームに追加"""
        market_regime = MarketRegime()

        # 基本的なOHLCVデータ
        dataframe = pd.DataFrame({
            'open': [100.0, 101.0, 102.0, 103.0, 104.0],
            'high': [102.0, 103.0, 104.0, 105.0, 106.0],
            'low': [99.0, 100.0, 101.0, 102.0, 103.0],
            'close': [101.0, 102.0, 103.0, 104.0, 105.0],
            'volume': [1000.0, 1100.0, 1200.0, 1300.0, 1400.0],
        })

        result = market_regime.add_regime_indicators(dataframe)

        # EMA50, EMA200, ADXが追加されていることを確認
        assert 'ema_50' in result.columns
        assert 'ema_200' in result.columns
        assert 'adx' in result.columns

    def test_detect_regime_with_missing_indicators_returns_sideways(self):
        """指標が不足している場合はsidewaysを返す"""
        market_regime = MarketRegime()

        # 指標が不足しているデータフレーム
        dataframe = pd.DataFrame({
            'close': [100.0, 101.0, 102.0],
        })

        regime = market_regime.detect_regime(dataframe)

        # デフォルトで'sideways'が返されることを確認
        assert regime == 'sideways'
