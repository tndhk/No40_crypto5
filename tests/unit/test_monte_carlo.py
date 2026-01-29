"""
Monte Carlo Simulation Tests (RED Phase)

このテストは、バックテストのトレード順序をランダム化して、
結果の頑健性と統計的信頼区間を評価するモンテカルロシミュレーションを検証する。

設計原則:
- dataclassはfrozen=Trueで不変
- seedで再現性確保
- 純粋関数アプローチ
"""

import pytest
from scripts.monte_carlo import MonteCarloResult, run_monte_carlo


class TestMonteCarloResult:
    """MonteCarloResultデータクラスのテストスイート"""

    def test_monte_carlo_result_is_immutable(self):
        """MonteCarloResultはイミュータブル"""
        result = MonteCarloResult(
            median_profit=100.0,
            ci_95_lower=80.0,
            ci_95_upper=120.0,
            worst_drawdown=25.0,
            best_drawdown=5.0,
            median_drawdown=15.0,
            run_count=100,
        )

        with pytest.raises(Exception):
            result.median_profit = 150.0

    def test_monte_carlo_result_all_fields_required(self):
        """MonteCarloResultは全フィールド必須"""
        with pytest.raises(TypeError):
            MonteCarloResult(
                median_profit=100.0,
                ci_95_lower=80.0,
                ci_95_upper=120.0,
                worst_drawdown=25.0,
                # best_drawdown欠落
                median_drawdown=15.0,
                run_count=100,
            )


class TestMonteCarloSimulation:
    """モンテカルロシミュレーションのテストスイート"""

    def test_simulation_returns_correct_count(self):
        """指定回数分の結果を返す"""
        trade_results = (10.0, -5.0, 15.0, -3.0, 20.0)
        num_simulations = 100

        result = run_monte_carlo(
            trade_results=trade_results, num_simulations=num_simulations, seed=42
        )

        assert result.run_count == num_simulations

    def test_simulation_shuffles_trade_order(self):
        """各runでトレード順序がシャッフルされる"""
        # 順序依存の結果になるようなトレード系列
        # 最初に大きな利益があると累積利益が高くなる
        trade_results = (100.0, -10.0, -10.0, -10.0, -10.0)

        # 同じseedで実行すると同じ結果になることを確認
        result1 = run_monte_carlo(
            trade_results=trade_results, num_simulations=50, seed=42
        )
        result2 = run_monte_carlo(
            trade_results=trade_results, num_simulations=50, seed=42
        )

        assert result1.median_profit == result2.median_profit
        assert result1.ci_95_lower == result2.ci_95_lower
        assert result1.ci_95_upper == result2.ci_95_upper

        # 異なるseedで実行すると異なる結果になることを確認
        result3 = run_monte_carlo(
            trade_results=trade_results, num_simulations=50, seed=123
        )

        # 確率的に同一になる可能性は極めて低い
        assert (
            result1.median_profit != result3.median_profit
            or result1.ci_95_lower != result3.ci_95_lower
            or result1.ci_95_upper != result3.ci_95_upper
        )

    def test_confidence_interval_calculation(self):
        """95%信頼区間が正しく計算される"""
        # 単純なトレード系列
        trade_results = (10.0, -5.0, 15.0, -3.0, 20.0, 8.0, -2.0)
        num_simulations = 1000

        result = run_monte_carlo(
            trade_results=trade_results, num_simulations=num_simulations, seed=42
        )

        # 信頼区間の妥当性チェック
        assert result.ci_95_lower < result.median_profit
        assert result.median_profit < result.ci_95_upper

        # 中央値は全トレードの合計と同じはず（順序を変えても合計は同じ）
        expected_total = sum(trade_results)
        # 浮動小数点誤差を考慮
        assert abs(result.median_profit - expected_total) < 1.0

    def test_simulation_preserves_trade_results(self):
        """シャッフルしてもトレード結果自体は変わらない"""
        trade_results = (10.0, -5.0, 15.0, -3.0, 20.0)

        result = run_monte_carlo(
            trade_results=trade_results, num_simulations=100, seed=42
        )

        # 全シミュレーションの中央値は元のトレード結果の合計に近いはず
        expected_total = sum(trade_results)

        # トレードの順序を変えても、最終的な累積利益は同じ
        # （ドローダウンは変わるが、最終利益は不変）
        assert abs(result.median_profit - expected_total) < 1.0

    def test_worst_case_drawdown_reported(self):
        """最悪ケースのDDが報告される"""
        # ドローダウンが発生するトレード系列
        trade_results = (10.0, -15.0, 5.0, -8.0, 20.0)

        result = run_monte_carlo(
            trade_results=trade_results, num_simulations=100, seed=42
        )

        # ドローダウン統計が妥当な範囲
        assert result.worst_drawdown >= result.median_drawdown
        assert result.median_drawdown >= result.best_drawdown
        assert result.best_drawdown >= 0.0

    def test_best_case_drawdown_reported(self):
        """最良ケースのDDが報告される"""
        trade_results = (10.0, -5.0, 15.0, -3.0, 20.0)

        result = run_monte_carlo(
            trade_results=trade_results, num_simulations=100, seed=42
        )

        # 最良ケースでもドローダウンは非負
        assert result.best_drawdown >= 0.0

    def test_median_drawdown_between_best_and_worst(self):
        """中央ドローダウンがベストとワーストの間"""
        trade_results = (10.0, -5.0, 15.0, -3.0, 20.0, 8.0, -2.0)

        result = run_monte_carlo(
            trade_results=trade_results, num_simulations=100, seed=42
        )

        assert result.best_drawdown <= result.median_drawdown <= result.worst_drawdown

    def test_empty_trade_results_raises_error(self):
        """空のトレード結果はエラー"""
        with pytest.raises(ValueError):
            run_monte_carlo(trade_results=(), num_simulations=100, seed=42)

    def test_single_trade_result_works(self):
        """単一トレードでも動作"""
        trade_results = (10.0,)

        result = run_monte_carlo(
            trade_results=trade_results, num_simulations=100, seed=42
        )

        # 単一トレードの場合、順序を変えても結果は同じ
        assert result.median_profit == 10.0
        assert result.ci_95_lower == 10.0
        assert result.ci_95_upper == 10.0

        # ドローダウンは0（利益が出る場合）または-10.0（損失の場合）
        # この場合は利益なのでDD=0
        if trade_results[0] > 0:
            assert result.best_drawdown == 0.0
            assert result.worst_drawdown == 0.0
            assert result.median_drawdown == 0.0

    def test_all_profitable_trades_has_zero_drawdown(self):
        """全て利益のトレードはDDゼロ"""
        trade_results = (10.0, 15.0, 20.0, 5.0, 12.0)

        result = run_monte_carlo(
            trade_results=trade_results, num_simulations=100, seed=42
        )

        # 全て利益なので、どの順序でもドローダウンは発生しない
        assert result.best_drawdown == 0.0
        assert result.worst_drawdown == 0.0
        assert result.median_drawdown == 0.0

    def test_all_loss_trades_has_maximum_drawdown(self):
        """全て損失のトレードは最大DD"""
        trade_results = (-10.0, -15.0, -20.0, -5.0, -12.0)

        result = run_monte_carlo(
            trade_results=trade_results, num_simulations=100, seed=42
        )

        # 全て損失なので、最終的な累積損失に近いドローダウンになる
        total_loss = abs(sum(trade_results))
        assert result.worst_drawdown > 0.0
        # ドローダウンは累積損失と同等またはそれ以下
        assert result.worst_drawdown <= total_loss + 1.0

    def test_zero_simulations_raises_error(self):
        """シミュレーション回数0はエラー"""
        trade_results = (10.0, -5.0, 15.0)

        with pytest.raises(ValueError):
            run_monte_carlo(trade_results=trade_results, num_simulations=0, seed=42)

    def test_negative_simulations_raises_error(self):
        """シミュレーション回数負はエラー"""
        trade_results = (10.0, -5.0, 15.0)

        with pytest.raises(ValueError):
            run_monte_carlo(trade_results=trade_results, num_simulations=-10, seed=42)

    def test_deterministic_with_same_seed(self):
        """同じseedで実行すると決定的な結果"""
        trade_results = (10.0, -5.0, 15.0, -3.0, 20.0)

        result1 = run_monte_carlo(
            trade_results=trade_results, num_simulations=100, seed=999
        )
        result2 = run_monte_carlo(
            trade_results=trade_results, num_simulations=100, seed=999
        )

        # 完全に同じ結果になることを確認
        assert result1.median_profit == result2.median_profit
        assert result1.ci_95_lower == result2.ci_95_lower
        assert result1.ci_95_upper == result2.ci_95_upper
        assert result1.worst_drawdown == result2.worst_drawdown
        assert result1.best_drawdown == result2.best_drawdown
        assert result1.median_drawdown == result2.median_drawdown


class TestMonteCarloEdgeCases:
    """モンテカルロシミュレーションのエッジケース"""

    def test_very_large_trade_count(self):
        """大量のトレードでも動作"""
        # 1000トレード
        trade_results = tuple(
            float(i % 10 - 5) for i in range(1000)
        )  # -5から4の繰り返し

        result = run_monte_carlo(
            trade_results=trade_results, num_simulations=50, seed=42
        )

        # 基本的な妥当性チェック
        assert result.run_count == 50
        assert result.ci_95_lower <= result.median_profit <= result.ci_95_upper

    def test_extreme_profit_values(self):
        """極端な利益値でも動作"""
        trade_results = (1000000.0, -999999.0, 500000.0)

        result = run_monte_carlo(
            trade_results=trade_results, num_simulations=100, seed=42
        )

        # 合計は約500001
        expected_total = sum(trade_results)
        assert abs(result.median_profit - expected_total) < 10.0

    def test_mixed_positive_negative_trades(self):
        """正負混在のトレードで妥当な結果"""
        trade_results = (50.0, -30.0, 40.0, -20.0, 60.0, -10.0, 30.0)

        result = run_monte_carlo(
            trade_results=trade_results, num_simulations=200, seed=42
        )

        # 合計は120.0
        expected_total = sum(trade_results)
        assert abs(result.median_profit - expected_total) < 1.0

        # ドローダウンは発生するはず
        assert result.worst_drawdown > 0.0

        # 信頼区間の幅は正の値
        ci_width = result.ci_95_upper - result.ci_95_lower
        assert ci_width > 0.0


class TestMonteCarloStatisticalProperties:
    """モンテカルロシミュレーションの統計的特性"""

    def test_confidence_interval_covers_median(self):
        """95%信頼区間は常に中央値を含む"""
        trade_results = (10.0, -5.0, 15.0, -3.0, 20.0, 8.0, -2.0, 12.0, -4.0, 18.0)

        result = run_monte_carlo(
            trade_results=trade_results, num_simulations=500, seed=42
        )

        assert result.ci_95_lower <= result.median_profit <= result.ci_95_upper

    def test_larger_sample_size_narrows_confidence_interval(self):
        """サンプルサイズが大きいほど信頼区間が狭くなる傾向"""
        trade_results = (10.0, -5.0, 15.0, -3.0, 20.0, 8.0, -2.0)

        result_small = run_monte_carlo(
            trade_results=trade_results, num_simulations=50, seed=42
        )
        result_large = run_monte_carlo(
            trade_results=trade_results, num_simulations=1000, seed=42
        )

        ci_width_small = result_small.ci_95_upper - result_small.ci_95_lower
        ci_width_large = result_large.ci_95_upper - result_large.ci_95_lower

        # 大きいサンプルサイズの方が信頼区間が狭い傾向
        # （確率的にそうなるはずだが、100%保証ではない）
        # ここでは傾向の確認のみ（厳密な不等式ではない）
        assert ci_width_large <= ci_width_small * 1.5

    def test_variance_in_trade_sequence_affects_drawdown_distribution(self):
        """トレード順序の分散がドローダウン分布に影響"""
        # 高分散のトレード系列
        trade_results = (100.0, -80.0, 90.0, -70.0, 85.0)

        result = run_monte_carlo(
            trade_results=trade_results, num_simulations=200, seed=42
        )

        # ワーストとベストのドローダウンの差が大きいはず
        dd_range = result.worst_drawdown - result.best_drawdown
        assert dd_range > 0.0
