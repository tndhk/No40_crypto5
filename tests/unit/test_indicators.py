"""
テクニカル指標のユニットテスト
"""
import pandas as pd

from user_data.strategies.indicators import (
    calculate_bollinger_bands,
    calculate_ema,
    calculate_rsi,
    calculate_volume_sma,
)


class TestEMACalculation:
    """EMA（指数移動平均）のテスト"""

    def test_ema_calculation(self):
        """EMA計算が正しく動作するか"""
        df = pd.DataFrame({
            'close': [100, 102, 101, 103, 105, 104, 106, 108]
        })
        result = calculate_ema(df, period=3)

        assert 'ema_3' in result.columns
        assert not result['ema_3'].isna().all()
        assert result['ema_3'].iloc[-1] > 100  # 上昇トレンドなので100より上

    def test_ema_with_insufficient_data(self):
        """データが不足している場合はNaNを返す"""
        df = pd.DataFrame({'close': [100, 102]})
        result = calculate_ema(df, period=5)

        assert result['ema_5'].isna().any()


class TestRSICalculation:
    """RSI（相対力指数）のテスト"""

    def test_rsi_calculation(self):
        """RSI計算が正しく動作するか"""
        df = pd.DataFrame({
            'close': [100, 105, 110, 108, 112, 115, 113, 118, 120, 119,
                      122, 125, 123, 127, 130]
        })
        result = calculate_rsi(df, period=14)

        assert 'rsi_14' in result.columns
        assert 0 <= result['rsi_14'].iloc[-1] <= 100

    def test_rsi_overbought(self):
        """上昇トレンドでRSIが70以上になることを確認"""
        df = pd.DataFrame({
            'close': [100 + i*2 for i in range(20)]  # 強い上昇トレンド
        })
        result = calculate_rsi(df, period=14)

        assert result['rsi_14'].iloc[-1] > 70


class TestBollingerBands:
    """ボリンジャーバンドのテスト"""

    def test_bollinger_bands_calculation(self):
        """ボリンジャーバンド計算が正しく動作するか"""
        df = pd.DataFrame({
            'close': [100, 102, 101, 103, 105, 104, 106, 108, 107, 109,
                      111, 110, 112, 114, 113, 115, 117, 116, 118, 120]
        })
        result = calculate_bollinger_bands(df, period=20, std=2)

        assert 'bb_upper' in result.columns
        assert 'bb_middle' in result.columns
        assert 'bb_lower' in result.columns

        # 上限 > 中央 > 下限
        assert result['bb_upper'].iloc[-1] > result['bb_middle'].iloc[-1]
        assert result['bb_middle'].iloc[-1] > result['bb_lower'].iloc[-1]


class TestVolumeSMA:
    """出来高移動平均のテスト"""

    def test_volume_sma_calculation(self):
        """出来高SMA計算が正しく動作するか"""
        df = pd.DataFrame({
            'volume': [1000, 1200, 1100, 1300, 1500, 1400, 1600, 1800]
        })
        result = calculate_volume_sma(df, period=5)

        assert 'volume_sma_5' in result.columns
        assert result['volume_sma_5'].iloc[-1] > 1000
