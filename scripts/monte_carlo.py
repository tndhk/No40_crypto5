"""
Monte Carlo Simulation for Backtest Analysis

このモジュールは、バックテストのトレード順序をランダム化して、
結果の頑健性と統計的信頼区間を評価するモンテカルロシミュレーションを提供する。

設計原則:
- dataclassはfrozen=Trueで不変
- seedで再現性確保
- 純粋関数アプローチ（副作用なし）

実装ノート:
トレード順序のシャッフル（復元なしの順列）を使用しているため、
最終損益は常に全トレードの合計と等しくなる。したがって、
median_profit、ci_95_lower、ci_95_upperは全て同じ値になる。

信頼区間に幅を持たせるには、ブートストラップサンプリング（復元あり）が必要だが、
その場合は最終損益が元のトレード合計と異なる値になり、
test_simulation_preserves_trade_resultsの要件と矛盾する。

現在の実装は順序依存のメトリクス（ドローダウン）の分析に適している。
"""

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

import numpy as np


@dataclass(frozen=True)
class MonteCarloResult:
    """モンテカルロシミュレーション結果

    すべてのフィールドは必須で、イミュータブル。
    """
    median_profit: float
    ci_95_lower: float
    ci_95_upper: float
    worst_drawdown: float
    best_drawdown: float
    median_drawdown: float
    run_count: int


def _calculate_drawdown(cumulative_profits: np.ndarray) -> float:
    """累積損益配列から最大ドローダウンを計算

    Args:
        cumulative_profits: 累積損益の配列

    Returns:
        最大ドローダウン（正の値、ドローダウンがない場合は0.0）
    """
    if len(cumulative_profits) == 0:
        return 0.0

    # ランニング最大値を計算
    running_max = np.maximum.accumulate(cumulative_profits)

    # ドローダウン = ランニング最大値 - 現在値
    drawdown = running_max - cumulative_profits

    # 最大ドローダウンを返す
    max_drawdown = np.max(drawdown)

    return float(max_drawdown)


def run_monte_carlo(
    trade_results: Tuple[float, ...],
    num_simulations: int = 100,
    seed: int = 42
) -> MonteCarloResult:
    """モンテカルロシミュレーションを実行

    トレード順序をランダム化して複数回シミュレーションを実行し、
    統計的な信頼区間とドローダウン分布を計算する。

    Args:
        trade_results: トレード結果のタプル（各トレードの損益）
        num_simulations: シミュレーション回数（デフォルト: 100）
        seed: 乱数シード（再現性のため、デフォルト: 42）

    Returns:
        MonteCarloResult: シミュレーション結果

    Raises:
        ValueError: trade_resultsが空、またはnum_simulationsが0以下の場合
    """
    # 入力検証
    if len(trade_results) == 0:
        raise ValueError("trade_results cannot be empty")

    if num_simulations <= 0:
        raise ValueError(f"num_simulations must be positive, got {num_simulations}")

    # 再現性のためにRandomGeneratorを作成
    rng = np.random.RandomState(seed)

    # トレード結果をnumpy配列に変換
    trades = np.array(trade_results)

    # シミュレーション結果を格納するリスト
    final_profits = []
    max_drawdowns = []

    # 指定回数分シミュレーションを実行
    for _ in range(num_simulations):
        # トレード順序をシャッフル（順列をランダム化、復元なし）
        shuffled_trades = trades.copy()
        rng.shuffle(shuffled_trades)

        # 累積損益を計算
        cumulative_profits = np.cumsum(shuffled_trades)

        # 最終損益を記録
        final_profit = float(cumulative_profits[-1])
        final_profits.append(final_profit)

        # 最大ドローダウンを計算して記録
        # 累積損益に開始点0を追加してドローダウンを計算
        cumulative_with_start = np.concatenate(([0], cumulative_profits))
        max_dd = _calculate_drawdown(cumulative_with_start)
        max_drawdowns.append(max_dd)

    # 統計量を計算
    final_profits_array = np.array(final_profits)
    max_drawdowns_array = np.array(max_drawdowns)

    # 中央値
    median_profit = float(np.median(final_profits_array))

    # 95%信頼区間（2.5パーセンタイルと97.5パーセンタイル）
    ci_95_lower = float(np.percentile(final_profits_array, 2.5))
    ci_95_upper = float(np.percentile(final_profits_array, 97.5))

    # ドローダウン統計
    worst_drawdown = float(np.max(max_drawdowns_array))
    best_drawdown = float(np.min(max_drawdowns_array))
    median_drawdown = float(np.median(max_drawdowns_array))

    return MonteCarloResult(
        median_profit=median_profit,
        ci_95_lower=ci_95_lower,
        ci_95_upper=ci_95_upper,
        worst_drawdown=worst_drawdown,
        best_drawdown=best_drawdown,
        median_drawdown=median_drawdown,
        run_count=num_simulations,
    )


def main() -> None:
    """CLI用メイン関数

    Usage:
        python scripts/monte_carlo.py <backtest_result.json> [--simulations N] [--seed S]
    """
    if len(sys.argv) < 2:
        print("Usage: python scripts/monte_carlo.py <backtest_result.json> [--simulations N] [--seed S]")
        print("Example: python scripts/monte_carlo.py data/backtest_results/result.json --simulations 1000 --seed 42")
        sys.exit(1)

    # コマンドライン引数を解析
    backtest_file = Path(sys.argv[1])

    num_simulations = 100
    seed = 42

    # オプション引数を解析
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--simulations" and i + 1 < len(sys.argv):
            num_simulations = int(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == "--seed" and i + 1 < len(sys.argv):
            seed = int(sys.argv[i + 1])
            i += 2
        else:
            print(f"Unknown argument: {sys.argv[i]}")
            sys.exit(1)

    # バックテスト結果を読み込み
    if not backtest_file.exists():
        print(f"Error: File not found: {backtest_file}")
        sys.exit(1)

    try:
        with open(backtest_file, "r", encoding="utf-8") as f:
            backtest_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {backtest_file}: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file {backtest_file}: {e}")
        sys.exit(1)

    # トレードリストを抽出（新旧フォーマット両対応）
    trades = backtest_data.get("trades", [])

    # 新しいフォーマット（strategy.DCAStrategy.trades）の確認
    if not trades and "strategy" in backtest_data:
        for strategy_name, strategy_data in backtest_data["strategy"].items():
            if "trades" in strategy_data and strategy_data["trades"]:
                trades = strategy_data["trades"]
                break

    if not trades:
        print("Error: No trades found in backtest result")
        sys.exit(1)

    # 各トレードの損益を抽出（profit_absを使用）
    trade_results = tuple(
        float(trade.get("profit_abs", 0.0)) for trade in trades
    )

    if len(trade_results) == 0:
        print("Error: No valid trade results found")
        sys.exit(1)

    # モンテカルロシミュレーションを実行
    try:
        result = run_monte_carlo(
            trade_results=trade_results,
            num_simulations=num_simulations,
            seed=seed
        )
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # 結果を表示
    print("\n=== Monte Carlo Simulation Results ===")
    print(f"Number of trades: {len(trade_results)}")
    print(f"Number of simulations: {result.run_count}")
    print("\nProfit Statistics:")
    print(f"  Median profit: ${result.median_profit:.2f}")
    print(f"  95% CI: [${result.ci_95_lower:.2f}, ${result.ci_95_upper:.2f}]")
    print("\nDrawdown Statistics:")
    print(f"  Best case DD: ${result.best_drawdown:.2f}")
    print(f"  Median DD: ${result.median_drawdown:.2f}")
    print(f"  Worst case DD: ${result.worst_drawdown:.2f}")
    print()


if __name__ == "__main__":
    main()
