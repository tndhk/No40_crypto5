"""
バックテスト結果分析のユニットテスト (RED Phase)

このテストは、バックテスト結果が定義された基準を満たすかを検証する。
基準は2段階設定:
- 最低基準 (Minimum): これを下回ると即FAIL
- 目標値 (Target): 理想的な成績
"""

import json
import sys
import tempfile
from pathlib import Path

import pytest

from scripts.analyze_backtest import (
    BacktestMetrics,
    CriteriaResult,
    evaluate_backtest,
    main,
    parse_backtest_json,
)


class TestBacktestMetrics:
    """BacktestMetricsデータクラスのテストスイート"""

    def test_backtest_metrics_is_immutable(self):
        """BacktestMetricsはイミュータブル"""
        metrics = BacktestMetrics(
            win_rate=0.55,
            profit_factor=1.5,
            sharpe_ratio=0.8,
            max_drawdown=15.0,
            total_trades=50,
            total_profit_pct=10.5,
        )

        with pytest.raises(Exception):
            metrics.win_rate = 0.60

    def test_backtest_metrics_all_fields_required(self):
        """BacktestMetricsは全フィールド必須"""
        with pytest.raises(TypeError):
            BacktestMetrics(
                win_rate=0.55,
                profit_factor=1.5,
                # sharpe_ratio欠落
                max_drawdown=15.0,
                total_trades=50,
                total_profit_pct=10.5,
            )


class TestCriteriaResult:
    """CriteriaResultデータクラスのテストスイート"""

    def test_criteria_result_is_immutable(self):
        """CriteriaResultはイミュータブル"""
        result = CriteriaResult(
            passed_minimum=True, passed_target=False, details=("Test detail",)
        )

        with pytest.raises(Exception):
            result.passed_minimum = False

    def test_details_is_tuple(self):
        """detailsはtupleで不変"""
        result = CriteriaResult(
            passed_minimum=True, passed_target=False, details=("Detail 1", "Detail 2")
        )

        assert isinstance(result.details, tuple)
        with pytest.raises(AttributeError):
            result.details.append("Detail 3")


class TestBacktestCriteria:
    """バックテスト基準評価のテストスイート"""

    def test_passing_results_meet_all_criteria(self):
        """全基準を満たす結果はPASS（最低基準と目標値の両方）"""
        metrics = BacktestMetrics(
            win_rate=0.60,  # Target: 55%+
            profit_factor=1.8,  # Target: 1.5+
            sharpe_ratio=1.0,  # Target: 0.8+
            max_drawdown=12.0,  # Target: 15%未満
            total_trades=100,  # Target: 50+
            total_profit_pct=20.0,  # 追加情報
        )

        result = evaluate_backtest(metrics)

        assert result.passed_minimum is True
        assert result.passed_target is True
        assert len(result.details) > 0

    def test_low_win_rate_fails(self):
        """勝率50%未満はFAIL（最低基準違反）"""
        metrics = BacktestMetrics(
            win_rate=0.45,  # < 50% (Minimum)
            profit_factor=1.5,
            sharpe_ratio=0.8,
            max_drawdown=15.0,
            total_trades=50,
            total_profit_pct=5.0,
        )

        result = evaluate_backtest(metrics)

        assert result.passed_minimum is False
        assert result.passed_target is False
        assert any("win_rate" in detail.lower() for detail in result.details)

    def test_low_profit_factor_fails(self):
        """プロフィットファクター1.2未満はFAIL（最低基準違反）"""
        metrics = BacktestMetrics(
            win_rate=0.55,
            profit_factor=1.1,  # < 1.2 (Minimum)
            sharpe_ratio=0.8,
            max_drawdown=15.0,
            total_trades=50,
            total_profit_pct=5.0,
        )

        result = evaluate_backtest(metrics)

        assert result.passed_minimum is False
        assert result.passed_target is False
        assert any("profit_factor" in detail.lower() for detail in result.details)

    def test_low_sharpe_ratio_fails(self):
        """シャープレシオ0.5未満はFAIL（最低基準違反）"""
        metrics = BacktestMetrics(
            win_rate=0.55,
            profit_factor=1.5,
            sharpe_ratio=0.4,  # < 0.5 (Minimum)
            max_drawdown=15.0,
            total_trades=50,
            total_profit_pct=5.0,
        )

        result = evaluate_backtest(metrics)

        assert result.passed_minimum is False
        assert result.passed_target is False
        assert any("sharpe_ratio" in detail.lower() for detail in result.details)

    def test_high_max_drawdown_fails(self):
        """最大ドローダウン20%超はFAIL（最低基準違反）"""
        metrics = BacktestMetrics(
            win_rate=0.55,
            profit_factor=1.5,
            sharpe_ratio=0.8,
            max_drawdown=25.0,  # > 20% (Minimum)
            total_trades=50,
            total_profit_pct=5.0,
        )

        result = evaluate_backtest(metrics)

        assert result.passed_minimum is False
        assert result.passed_target is False
        assert any("max_drawdown" in detail.lower() for detail in result.details)

    def test_insufficient_trades_fails(self):
        """トレード数30未満はFAIL（最低基準違反）"""
        metrics = BacktestMetrics(
            win_rate=0.55,
            profit_factor=1.5,
            sharpe_ratio=0.8,
            max_drawdown=15.0,
            total_trades=25,  # < 30 (Minimum)
            total_profit_pct=5.0,
        )

        result = evaluate_backtest(metrics)

        assert result.passed_minimum is False
        assert result.passed_target is False
        assert any("total_trades" in detail.lower() for detail in result.details)

    def test_distinguishes_minimum_and_target(self):
        """最低基準と目標値を区別（最低基準PASS、目標値FAIL）"""
        metrics = BacktestMetrics(
            win_rate=0.52,  # Minimum: 50%+, Target: 55%+
            profit_factor=1.3,  # Minimum: 1.2+, Target: 1.5+
            sharpe_ratio=0.6,  # Minimum: 0.5+, Target: 0.8+
            max_drawdown=18.0,  # Minimum: 20%未満, Target: 15%未満
            total_trades=40,  # Minimum: 30+, Target: 50+
            total_profit_pct=5.0,
        )

        result = evaluate_backtest(metrics)

        assert result.passed_minimum is True
        assert result.passed_target is False
        assert len(result.details) > 0

    def test_multiple_criteria_violations_reported(self):
        """複数の基準違反がすべて報告される"""
        metrics = BacktestMetrics(
            win_rate=0.40,  # 違反1
            profit_factor=1.0,  # 違反2
            sharpe_ratio=0.3,  # 違反3
            max_drawdown=25.0,  # 違反4
            total_trades=20,  # 違反5
            total_profit_pct=-5.0,
        )

        result = evaluate_backtest(metrics)

        assert result.passed_minimum is False
        assert result.passed_target is False
        # 少なくとも5つの違反が報告されること
        assert len(result.details) >= 5

    def test_edge_case_exactly_at_minimum_threshold(self):
        """閾値ちょうどの値はPASSとして扱う"""
        metrics = BacktestMetrics(
            win_rate=0.50,  # 最低基準ちょうど
            profit_factor=1.2,  # 最低基準ちょうど
            sharpe_ratio=0.5,  # 最低基準ちょうど
            max_drawdown=20.0,  # 最低基準ちょうど
            total_trades=30,  # 最低基準ちょうど
            total_profit_pct=0.0,
        )

        result = evaluate_backtest(metrics)

        assert result.passed_minimum is True
        # 目標値には達していない
        assert result.passed_target is False


class TestParseBacktestJson:
    """バックテストJSON解析のテストスイート"""

    def test_parse_valid_backtest_json(self):
        """正常なバックテストJSONを解析"""
        backtest_data = {
            "strategy": {
                "DCATrendFollowStrategy": {
                    "results_metrics": {
                        "win_rate": 0.55,
                        "profit_factor": 1.5,
                        "sharpe": 0.8,
                        "max_drawdown": 15.0,
                        "trades": 50,
                        "total_profit_pct": 10.5,
                    }
                }
            }
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(backtest_data, f)
            temp_path = f.name

        try:
            metrics = parse_backtest_json(temp_path)

            assert metrics.win_rate == 0.55
            assert metrics.profit_factor == 1.5
            assert metrics.sharpe_ratio == 0.8
            assert metrics.max_drawdown == 15.0
            assert metrics.total_trades == 50
            assert metrics.total_profit_pct == 10.5
        finally:
            Path(temp_path).unlink()

    def test_parse_nonexistent_file_raises_error(self):
        """存在しないファイルはエラー"""
        with pytest.raises(FileNotFoundError):
            parse_backtest_json("/nonexistent/path/backtest.json")

    def test_parse_invalid_json_raises_error(self):
        """不正なJSON構文はエラー"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            f.write("{invalid json")
            temp_path = f.name

        try:
            with pytest.raises(json.JSONDecodeError):
                parse_backtest_json(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_parse_missing_required_field_raises_error(self):
        """必須フィールド欠落はエラー"""
        backtest_data = {
            "strategy": {
                "DCATrendFollowStrategy": {
                    "results_metrics": {
                        "win_rate": 0.55,
                        # profit_factor欠落
                        "sharpe": 0.8,
                        "max_drawdown": 15.0,
                        "trades": 50,
                        "total_profit_pct": 10.5,
                    }
                }
            }
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(backtest_data, f)
            temp_path = f.name

        try:
            with pytest.raises(KeyError):
                parse_backtest_json(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_parse_wrong_data_type_raises_error(self):
        """データ型不正はエラー"""
        backtest_data = {
            "strategy": {
                "DCATrendFollowStrategy": {
                    "results_metrics": {
                        "win_rate": "0.55",  # 文字列（本来はfloat）
                        "profit_factor": 1.5,
                        "sharpe": 0.8,
                        "max_drawdown": 15.0,
                        "trades": 50,
                        "total_profit_pct": 10.5,
                    }
                }
            }
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(backtest_data, f)
            temp_path = f.name

        try:
            with pytest.raises((TypeError, ValueError)):
                parse_backtest_json(temp_path)
        finally:
            Path(temp_path).unlink()


class TestAnalyzeBacktestMain:
    """Analyze Backtest CLIメイン関数のテストスイート"""

    def test_main_with_passing_results(self, monkeypatch, capsys):
        """基準を満たすバックテスト結果で正常終了"""
        backtest_data = {
            "strategy": {
                "DCATrendFollowStrategy": {
                    "results_metrics": {
                        "win_rate": 0.60,
                        "profit_factor": 1.8,
                        "sharpe": 1.0,
                        "max_drawdown": 12.0,
                        "trades": 100,
                        "total_profit_pct": 20.0,
                    }
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(backtest_data, f)
            temp_path = f.name

        try:
            monkeypatch.setattr(sys, "argv", ["analyze_backtest.py", temp_path])
            main()

            captured = capsys.readouterr()
            assert "Backtest Metrics" in captured.out
            assert "Passed Minimum Criteria: True" in captured.out
            assert "Passed Target Criteria: True" in captured.out
        finally:
            Path(temp_path).unlink()

    def test_main_with_failing_results(self, monkeypatch, capsys):
        """基準を満たさないバックテスト結果でエラー終了"""
        backtest_data = {
            "strategy": {
                "DCATrendFollowStrategy": {
                    "results_metrics": {
                        "win_rate": 0.40,
                        "profit_factor": 1.0,
                        "sharpe": 0.3,
                        "max_drawdown": 25.0,
                        "trades": 20,
                        "total_profit_pct": -5.0,
                    }
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(backtest_data, f)
            temp_path = f.name

        try:
            monkeypatch.setattr(sys, "argv", ["analyze_backtest.py", temp_path])

            with pytest.raises(SystemExit) as excinfo:
                main()

            assert excinfo.value.code == 1
            captured = capsys.readouterr()
            assert "Passed Minimum Criteria: False" in captured.out
        finally:
            Path(temp_path).unlink()

    def test_main_with_file_not_found(self, monkeypatch, capsys):
        """ファイルが存在しない場合はエラー終了"""
        monkeypatch.setattr(
            sys, "argv", ["analyze_backtest.py", "/nonexistent/path/backtest.json"]
        )

        with pytest.raises(SystemExit) as excinfo:
            main()

        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert "Error:" in captured.err

    def test_main_with_invalid_json(self, monkeypatch, capsys):
        """不正なJSON形式の場合はエラー終了"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{invalid json")
            temp_path = f.name

        try:
            monkeypatch.setattr(sys, "argv", ["analyze_backtest.py", temp_path])

            with pytest.raises(SystemExit) as excinfo:
                main()

            assert excinfo.value.code == 1
            captured = capsys.readouterr()
            assert "Invalid JSON" in captured.err
        finally:
            Path(temp_path).unlink()

    def test_main_with_no_arguments(self, monkeypatch, capsys):
        """引数なしで実行すると使い方を表示して終了"""
        monkeypatch.setattr(sys, "argv", ["analyze_backtest.py"])

        with pytest.raises(SystemExit) as excinfo:
            main()

        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert "Usage:" in captured.out

    def test_main_with_missing_field(self, monkeypatch, capsys):
        """必須フィールドが欠落している場合はエラー終了"""
        backtest_data = {
            "strategy": {
                "DCATrendFollowStrategy": {
                    "results_metrics": {
                        "win_rate": 0.55,
                        # profit_factor欠落
                        "sharpe": 0.8,
                        "max_drawdown": 15.0,
                        "trades": 50,
                        "total_profit_pct": 10.5,
                    }
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(backtest_data, f)
            temp_path = f.name

        try:
            monkeypatch.setattr(sys, "argv", ["analyze_backtest.py", temp_path])

            with pytest.raises(SystemExit) as excinfo:
                main()

            assert excinfo.value.code == 1
            captured = capsys.readouterr()
            assert "Error:" in captured.err
        finally:
            Path(temp_path).unlink()
