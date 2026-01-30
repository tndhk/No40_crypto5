"""
DCA（ドルコスト平均法）戦略

RSIベースのエントリーシグナルと、DCA（ドルコスト平均法）による
ポジション追加を行う戦略。
"""

from datetime import datetime
from typing import Optional

from freqtrade.persistence import Trade
from freqtrade.strategy import DecimalParameter, IStrategy
from pandas import DataFrame

from indicators import calculate_rsi, calculate_volume_sma
from market_regime import MarketRegime
from risk_manager import RiskManager
from slippage_protection import SlippageProtection


class DCAStrategy(IStrategy):
    """
    DCA戦略クラス

    RSIが過売状態（45以下）でエントリーし、
    損失が拡大した場合にDCAで追加購入を行う。
    """

    # 戦略メタデータ
    INTERFACE_VERSION = 3
    can_short = False

    # 基本設定
    timeframe = '15m'
    stoploss = -0.20  # -20%
    # minimal_roi: 15m足基準（暫定値、Hyperoptで最適化予定）
    minimal_roi = {
        "0": 0.15,      # 即座: 15%
        "180": 0.10,    # 180本後（45時間 = 12時間 × 48本/12h = 12時間）: 10%
        "360": 0.05,    # 360本後（90時間 = 24時間 × 48本/24h = 24時間）: 5%
    }

    # トレーリングストップ設定
    trailing_stop = True
    trailing_stop_positive = 0.02  # +2%でトレーリング
    trailing_stop_positive_offset = 0.05  # +5%到達後に発動
    trailing_only_offset_is_reached = True  # オフセット到達後のみトレーリング

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

    @property
    def protections(self):
        """
        Freqtrade protections設定

        Returns:
            protectionsの設定リスト
        """
        return [
            {"method": "CooldownPeriod", "stop_duration_candles": 3},
            {"method": "MaxDrawdown", "lookback_period_candles": 48,
             "trade_limit": 20, "max_allowed_drawdown": 0.15},
            {"method": "StoplossGuard", "lookback_period_candles": 24,
             "trade_limit": 3, "only_per_pair": False},
            {"method": "LowProfitPairs", "lookback_period_candles": 48,
             "trade_limit": 2, "required_profit": -0.05},
        ]

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
        self.slippage_protection = SlippageProtection(
            max_slippage_percent=config.get('max_slippage_percent', 0.5)
        )

        # リスク管理モジュール
        self.risk_manager = RiskManager(
            max_position_size=config.get('max_position_size', 100000),
            max_portfolio_allocation=config.get('max_portfolio_allocation', 0.2),
            daily_loss_limit=config.get('daily_loss_limit', 0.05),
            circuit_breaker_drawdown=config.get('circuit_breaker_drawdown', 0.15),
            max_consecutive_losses=config.get('max_consecutive_losses', 3),
            cooldown_hours=config.get('cooldown_hours', 24)
        )

        # 期待エントリー価格の記録用
        self.expected_entry_price = {}

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

        # 出来高SMAを計算
        dataframe_with_volume_sma = calculate_volume_sma(dataframe, period=20)
        dataframe['volume_sma_20'] = dataframe_with_volume_sma['volume_sma_20']

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

        # RSIが45以下（緩い過売状態）かつ出来高がSMA20の90%以上でエントリー
        # トレード頻度を確保するため、RSI閾値を45に設定
        # 市場環境フィルターは削除して、トレード頻度を最大化
        dataframe.loc[
            (dataframe['rsi'] <= 45) &
            (dataframe['volume'] > 0.9 * dataframe['volume_sma_20']),
            'enter_long'
        ] = 1

        # 期待エントリー価格を記録（最新のクローズ価格）
        if len(dataframe) > 0:
            pair = metadata.get('pair', '')
            self.expected_entry_price[pair] = dataframe['close'].iloc[-1]

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
    ) -> Optional[float]:
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
            カスタムステーク額（上限超過の場合None）
        """
        # DCAエントリーの場合は1.5倍のステーク
        stake_amount = proposed_stake
        if entry_tag and entry_tag.startswith('dca_'):
            stake_amount = proposed_stake * 1.5

        # ポジションサイズ上限チェック
        if not self.risk_manager.check_position_size(stake_amount):
            return None

        # ポートフォリオ配分上限チェック
        wallet_balance = kwargs.get('wallet_balance', 0)
        if wallet_balance > 0:
            if not self.risk_manager.check_portfolio_limit(stake_amount, wallet_balance):
                return None

        # 初回エントリーは提案額をそのまま使用
        return stake_amount

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

        # クールダウン期間中はDCAをブロック
        if not self.risk_manager.check_cooldown(current_time):
            return None

        # 部分利確チェック（利益が閾値を超えた場合）
        if current_profit >= self.take_profit_threshold.value:
            # 負の値を返すことで部分売却を指示
            # stake_amount * sell_ratioを売却
            sell_amount = trade.stake_amount * self.take_profit_sell_ratio.value
            return -sell_amount

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

    def confirm_trade_entry(
        self,
        pair: str,
        order_type: str,
        amount: float,
        rate: float,
        time_in_force: str,
        current_time: datetime,
        entry_tag: Optional[str],
        side: str,
        **kwargs
    ) -> bool:
        """
        エントリー注文の最終確認

        Args:
            pair: 通貨ペア
            order_type: 注文タイプ
            amount: 注文量
            rate: 注文レート
            time_in_force: 注文有効期限
            current_time: 現在時刻
            entry_tag: エントリータグ
            side: 'long' or 'short'
            **kwargs: その他のパラメータ

        Returns:
            True: 注文許可, False: 注文拒否
        """
        # 連続損失上限チェック
        if not self.risk_manager.check_consecutive_losses():
            return False

        # 期待価格が記録されている場合のみスリッページチェック
        if pair in self.expected_entry_price:
            expected_price = self.expected_entry_price[pair]
            if not self.slippage_protection.check_slippage(expected_price, rate):
                return False

        return True

    def confirm_trade_exit(
        self,
        pair: str,
        trade: Trade,
        order_type: str,
        amount: float,
        rate: float,
        time_in_force: str,
        exit_reason: str,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        side: str,
        **kwargs
    ) -> bool:
        """
        エグジット注文の最終確認（エグジット確定時に1回だけ呼ばれる）

        Args:
            pair: 通貨ペア
            trade: トレードオブジェクト
            order_type: 注文タイプ
            amount: 注文量
            rate: 注文レート
            time_in_force: 注文有効期限
            exit_reason: エグジット理由
            current_time: 現在時刻
            current_rate: 現在のレート
            current_profit: 現在の利益率
            side: 'long' or 'short'
            **kwargs: その他のパラメータ

        Returns:
            True: 注文許可, False: 注文拒否
        """
        # トレード結果を記録
        is_loss = current_profit < 0
        self.risk_manager.record_trade_result(is_loss)

        # ストップロスの場合はクールダウンをトリガー
        if exit_reason == 'stop_loss' or (is_loss and current_profit <= self.stoploss):
            self.risk_manager.trigger_cooldown(current_time)

        return True

    def custom_exit(
        self,
        pair: str,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        **kwargs
    ) -> Optional[str]:
        """
        カスタムエグジットロジック

        Args:
            pair: 通貨ペア
            trade: トレードオブジェクト
            current_time: 現在時刻
            current_rate: 現在のレート
            current_profit: 現在の利益率
            **kwargs: その他のパラメータ

        Returns:
            エグジット理由（なしの場合None）
        """
        # カスタムエグジット条件はなし（Freqtradeのデフォルトロジックを使用）
        return None
