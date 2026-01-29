"""
バックテスト結果分析スクリプト

バックテスト結果が定義された基準を満たすかを検証する。
基準は2段階設定:
- 最低基準 (Minimum): これを下回ると即FAIL
- 目標値 (Target): 理想的な成績
"""

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class BacktestMetrics:
    """バックテスト結果のメトリクス（不変）"""

    win_rate: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float
    total_trades: int
    total_profit_pct: float


@dataclass(frozen=True)
class CriteriaResult:
    """基準評価結果（不変）"""

    passed_minimum: bool
    passed_target: bool
    details: tuple[str, ...]


def evaluate_backtest(metrics: BacktestMetrics) -> CriteriaResult:
    """
    バックテスト結果を評価する純粋関数

    Args:
        metrics: バックテストメトリクス

    Returns:
        CriteriaResult: 評価結果

    基準:
        最低基準 (Minimum):
        - win_rate >= 0.50
        - profit_factor >= 1.2
        - sharpe_ratio >= 0.5
        - max_drawdown <= 20.0
        - total_trades >= 30

        目標値 (Target):
        - win_rate >= 0.55
        - profit_factor >= 1.5
        - sharpe_ratio >= 0.8
        - max_drawdown <= 15.0
        - total_trades >= 50
    """
    details: list[str] = []
    passed_minimum = True
    passed_target = True

    # 最低基準チェック
    if metrics.win_rate < 0.50:
        passed_minimum = False
        details.append(
            f"win_rate {metrics.win_rate:.2%} is below minimum threshold 50.00%"
        )

    if metrics.profit_factor < 1.2:
        passed_minimum = False
        details.append(
            f"profit_factor {metrics.profit_factor:.2f} is below minimum threshold 1.20"
        )

    if metrics.sharpe_ratio < 0.5:
        passed_minimum = False
        details.append(
            f"sharpe_ratio {metrics.sharpe_ratio:.2f} is below minimum threshold 0.50"
        )

    if metrics.max_drawdown > 20.0:
        passed_minimum = False
        details.append(
            f"max_drawdown {metrics.max_drawdown:.2f}% exceeds minimum threshold 20.00%"
        )

    if metrics.total_trades < 30:
        passed_minimum = False
        details.append(
            f"total_trades {metrics.total_trades} is below minimum threshold 30"
        )

    # 目標値チェック
    if metrics.win_rate < 0.55:
        passed_target = False
        if metrics.win_rate >= 0.50:
            details.append(
                f"win_rate {metrics.win_rate:.2%} meets minimum but below target 55.00%"
            )

    if metrics.profit_factor < 1.5:
        passed_target = False
        if metrics.profit_factor >= 1.2:
            details.append(
                f"profit_factor {metrics.profit_factor:.2f} meets minimum but below target 1.50"
            )

    if metrics.sharpe_ratio < 0.8:
        passed_target = False
        if metrics.sharpe_ratio >= 0.5:
            details.append(
                f"sharpe_ratio {metrics.sharpe_ratio:.2f} meets minimum but below target 0.80"
            )

    if metrics.max_drawdown > 15.0:
        passed_target = False
        if metrics.max_drawdown <= 20.0:
            details.append(
                f"max_drawdown {metrics.max_drawdown:.2f}% meets minimum but exceeds target 15.00%"
            )

    if metrics.total_trades < 50:
        passed_target = False
        if metrics.total_trades >= 30:
            details.append(
                f"total_trades {metrics.total_trades} meets minimum but below target 50"
            )

    # 最低基準が失敗した場合、目標値も自動的に失敗
    if not passed_minimum:
        passed_target = False

    # 詳細情報が空の場合、成功メッセージを追加
    if not details:
        details.append("All criteria passed (both minimum and target)")

    return CriteriaResult(
        passed_minimum=passed_minimum, passed_target=passed_target, details=tuple(details)
    )


def parse_backtest_json(json_path: str) -> BacktestMetrics:
    """
    FreqtradeのバックテストJSON結果を解析する純粋関数

    Args:
        json_path: バックテスト結果JSONファイルのパス

    Returns:
        BacktestMetrics: 解析されたメトリクス

    Raises:
        FileNotFoundError: ファイルが存在しない場合
        json.JSONDecodeError: JSON構文エラーの場合
        KeyError: 必須フィールドが欠落している場合
        TypeError: データ型が不正な場合
        ValueError: データ型変換に失敗した場合
    """
    path = Path(json_path)
    if not path.exists():
        raise FileNotFoundError(f"Backtest JSON file not found: {json_path}")

    with open(path, "r", encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)

    # Freqtradeのバックテスト結果構造を解析
    # 例: {"strategy": {"DCATrendFollowStrategy": {"results_metrics": {...}}}}
    strategy_data = data["strategy"]

    # 最初のストラテジーのメトリクスを取得
    strategy_name = next(iter(strategy_data.keys()))
    metrics_data = strategy_data[strategy_name]["results_metrics"]

    # データ型検証を含むメトリクス抽出
    # 文字列として保存された数値を検出（JSONスキーマ違反）
    for key, value in metrics_data.items():
        if isinstance(value, str):
            raise TypeError(
                f"Invalid data type for '{key}': expected number, got string '{value}'"
            )

    try:
        win_rate = float(metrics_data["win_rate"])
        profit_factor = float(metrics_data["profit_factor"])
        sharpe = float(metrics_data["sharpe"])
        max_drawdown = float(metrics_data["max_drawdown"])
        trades = int(metrics_data["trades"])
        total_profit_pct = float(metrics_data["total_profit_pct"])
    except (TypeError, ValueError) as e:
        raise TypeError(f"Invalid data type in backtest metrics: {e}") from e

    return BacktestMetrics(
        win_rate=win_rate,
        profit_factor=profit_factor,
        sharpe_ratio=sharpe,
        max_drawdown=max_drawdown,
        total_trades=trades,
        total_profit_pct=total_profit_pct,
    )


def main() -> None:
    """CLIエントリーポイント"""
    if len(sys.argv) < 2:
        print("Usage: python analyze_backtest.py <backtest_results.json>")
        sys.exit(1)

    json_path = sys.argv[1]

    try:
        metrics = parse_backtest_json(json_path)
        result = evaluate_backtest(metrics)

        print("\n=== Backtest Metrics ===")
        print(f"Win Rate: {metrics.win_rate:.2%}")
        print(f"Profit Factor: {metrics.profit_factor:.2f}")
        print(f"Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
        print(f"Max Drawdown: {metrics.max_drawdown:.2f}%")
        print(f"Total Trades: {metrics.total_trades}")
        print(f"Total Profit: {metrics.total_profit_pct:.2f}%")

        print("\n=== Evaluation Result ===")
        print(f"Passed Minimum Criteria: {result.passed_minimum}")
        print(f"Passed Target Criteria: {result.passed_target}")

        print("\n=== Details ===")
        for detail in result.details:
            print(f"  - {detail}")

        # 最低基準を満たしていない場合はエラー終了
        if not result.passed_minimum:
            sys.exit(1)

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format - {e}", file=sys.stderr)
        sys.exit(1)
    except KeyError as e:
        print(f"Error: Missing required field in backtest results - {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
