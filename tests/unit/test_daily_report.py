"""Tests for daily report generation."""

import sqlite3
from unittest.mock import patch

import pytest

from scripts.daily_report import (
    DailyMetrics,
    collect_daily_metrics_from_api,
    collect_daily_metrics_from_db,
    format_daily_report,
    save_report_to_file,
)
from scripts.freqtrade_api_client import ApiClientConfig, ApiResponse


class TestDailyReport:
    """Test daily report generation."""

    def test_format_report_with_trades(self):
        """Report with trades should include all metrics."""
        metrics = DailyMetrics(
            date="2026-01-30",
            uptime_percent=99.5,
            total_trades=5,
            daily_pnl=1500.0,
            cumulative_pnl=3000.0,
            open_positions=2,
            api_errors=1,
            api_total_calls=500,
        )
        report = format_daily_report(metrics)

        assert "2026-01-30" in report
        assert "99.5" in report
        assert "5" in report
        assert "1500" in report or "1,500" in report
        assert "3000" in report or "3,000" in report
        assert "2" in report

    def test_format_report_no_trades(self):
        """Report with no trades should still show metrics."""
        metrics = DailyMetrics(
            date="2026-01-30",
            uptime_percent=100.0,
            total_trades=0,
            daily_pnl=0.0,
            cumulative_pnl=0.0,
            open_positions=0,
            api_errors=0,
            api_total_calls=100,
        )
        report = format_daily_report(metrics)

        assert "2026-01-30" in report
        assert "100.0" in report or "100" in report
        assert "0" in report

    def test_report_includes_all_metrics(self):
        """Report should include uptime, P&L, trades, and API stats."""
        metrics = DailyMetrics(
            date="2026-01-30",
            uptime_percent=99.2,
            total_trades=3,
            daily_pnl=-500.0,
            cumulative_pnl=2500.0,
            open_positions=1,
            api_errors=2,
            api_total_calls=300,
        )
        report = format_daily_report(metrics)

        # Check for key sections
        assert "Date" in report or "date" in report or "2026-01-30" in report
        assert "Uptime" in report or "uptime" in report
        assert "Trades" in report or "trades" in report
        assert "P&L" in report or "PnL" in report or "profit" in report

    def test_negative_pnl_formatting(self):
        """Negative P&L should be clearly formatted."""
        metrics = DailyMetrics(
            date="2026-01-30",
            uptime_percent=99.5,
            total_trades=2,
            daily_pnl=-1000.0,
            cumulative_pnl=-500.0,
            open_positions=1,
            api_errors=0,
            api_total_calls=200,
        )
        report = format_daily_report(metrics)

        assert "-1000" in report or "-1,000" in report
        assert "-500" in report

    def test_api_error_rate_calculation(self):
        """Report should show API error rate."""
        metrics = DailyMetrics(
            date="2026-01-30",
            uptime_percent=99.5,
            total_trades=5,
            daily_pnl=1000.0,
            cumulative_pnl=2000.0,
            open_positions=2,
            api_errors=5,
            api_total_calls=1000,
        )
        report = format_daily_report(metrics)

        # Error rate = 5/1000 = 0.5%
        assert "0.5" in report or "API" in report

    def test_zero_api_calls_handled(self):
        """Zero API calls should not cause division by zero."""
        metrics = DailyMetrics(
            date="2026-01-30",
            uptime_percent=0.0,
            total_trades=0,
            daily_pnl=0.0,
            cumulative_pnl=0.0,
            open_positions=0,
            api_errors=0,
            api_total_calls=0,
        )
        report = format_daily_report(metrics)

        assert report is not None
        assert len(report) > 0


class TestDailyMetrics:
    """Test DailyMetrics dataclass."""

    def test_daily_metrics_is_immutable(self):
        """DailyMetrics should be immutable."""
        metrics = DailyMetrics(
            date="2026-01-30",
            uptime_percent=99.5,
            total_trades=5,
            daily_pnl=1000.0,
            cumulative_pnl=2000.0,
            open_positions=2,
            api_errors=1,
            api_total_calls=500,
        )
        with pytest.raises(Exception):
            metrics.uptime_percent = 98.0

    def test_daily_metrics_all_fields_required(self):
        """All fields should be required."""
        with pytest.raises(TypeError):
            DailyMetrics(
                date="2026-01-30",
                uptime_percent=99.5,
            )


# ---------------------------------------------------------------------------
# New test classes for data collection functions
# ---------------------------------------------------------------------------


class TestCollectDailyMetricsFromApi:
    """Test collect_daily_metrics_from_api function."""

    @patch("scripts.daily_report.fetch_logs")
    @patch("scripts.daily_report.fetch_trades")
    @patch("scripts.daily_report.fetch_status")
    @patch("scripts.daily_report.fetch_profit")
    def test_successful_collection(self, mock_profit, mock_status, mock_trades, mock_logs):
        """Should return DailyMetrics when all API calls succeed."""
        mock_profit.return_value = ApiResponse(
            success=True,
            data={"profit_all_coin": 1500.0},
            error="",
            status_code=200,
        )
        mock_status.return_value = ApiResponse(
            success=True,
            data=[{"trade_id": 1}, {"trade_id": 2}],
            error="",
            status_code=200,
        )
        mock_trades.return_value = ApiResponse(
            success=True,
            data={
                "trades": [
                    {"close_date": "2026-02-01 10:00:00"},
                    {"close_date": "2026-02-01 14:30:00"},
                    {"close_date": "2026-01-31 09:00:00"},
                ]
            },
            error="",
            status_code=200,
        )
        mock_logs.return_value = ApiResponse(
            success=True,
            data={
                "logs": [
                    ["2026-02-01 10:00:00", "INFO", "All good"],
                    ["2026-02-01 10:01:00", "ERROR", "Something failed"],
                    ["2026-02-01 10:02:00", "INFO", "Recovered"],
                ]
            },
            error="",
            status_code=200,
        )

        config = ApiClientConfig()
        result = collect_daily_metrics_from_api(config, "2026-02-01")

        assert result is not None
        assert isinstance(result, DailyMetrics)
        assert result.date == "2026-02-01"
        assert result.daily_pnl == 1500.0
        assert result.cumulative_pnl == 1500.0
        assert result.open_positions == 2
        assert result.total_trades == 2  # Only trades with close_date on 2026-02-01
        assert result.api_errors == 1
        assert result.api_total_calls == 3

    @patch("scripts.daily_report.fetch_profit")
    def test_returns_none_on_api_failure(self, mock_profit):
        """Should return None when the profit API call fails."""
        mock_profit.return_value = ApiResponse(
            success=False,
            data=None,
            error="Connection refused",
            status_code=0,
        )

        config = ApiClientConfig()
        result = collect_daily_metrics_from_api(config, "2026-02-01")

        assert result is None

    @patch("scripts.daily_report.fetch_logs")
    @patch("scripts.daily_report.fetch_trades")
    @patch("scripts.daily_report.fetch_status")
    @patch("scripts.daily_report.fetch_profit")
    def test_handles_empty_trades(self, mock_profit, mock_status, mock_trades, mock_logs):
        """Should handle empty trade list gracefully."""
        mock_profit.return_value = ApiResponse(
            success=True,
            data={"profit_all_coin": 0.0},
            error="",
            status_code=200,
        )
        mock_status.return_value = ApiResponse(
            success=True,
            data=[],
            error="",
            status_code=200,
        )
        mock_trades.return_value = ApiResponse(
            success=True,
            data={"trades": []},
            error="",
            status_code=200,
        )
        mock_logs.return_value = ApiResponse(
            success=True,
            data={"logs": []},
            error="",
            status_code=200,
        )

        config = ApiClientConfig()
        result = collect_daily_metrics_from_api(config, "2026-02-01")

        assert result is not None
        assert result.total_trades == 0
        assert result.open_positions == 0
        assert result.api_errors == 0
        assert result.api_total_calls == 0


def _create_test_db(db_path: str, trades: list[dict] | None = None):
    """Helper to create a test SQLite database with trades table."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE trades (
            id INTEGER PRIMARY KEY,
            pair TEXT,
            is_open INTEGER,
            close_date TEXT,
            close_profit_abs REAL
        )
        """
    )
    if trades:
        for trade in trades:
            cursor.execute(
                "INSERT INTO trades (pair, is_open, close_date, close_profit_abs) "
                "VALUES (?, ?, ?, ?)",
                (
                    trade.get("pair", "BTC/JPY"),
                    trade.get("is_open", 0),
                    trade.get("close_date"),
                    trade.get("close_profit_abs", 0.0),
                ),
            )
    conn.commit()
    conn.close()


class TestCollectDailyMetricsFromDb:
    """Test collect_daily_metrics_from_db function."""

    def test_reads_from_database(self, tmp_path):
        """Should read trades from SQLite database and compute metrics."""
        db_path = str(tmp_path / "trades.sqlite")
        _create_test_db(
            db_path,
            trades=[
                {
                    "pair": "BTC/JPY",
                    "is_open": 0,
                    "close_date": "2026-02-01 10:00:00",
                    "close_profit_abs": 500.0,
                },
                {
                    "pair": "ETH/JPY",
                    "is_open": 0,
                    "close_date": "2026-02-01 14:00:00",
                    "close_profit_abs": -200.0,
                },
                {
                    "pair": "XRP/JPY",
                    "is_open": 1,
                    "close_date": None,
                    "close_profit_abs": None,
                },
                {
                    "pair": "ADA/JPY",
                    "is_open": 0,
                    "close_date": "2026-01-31 12:00:00",
                    "close_profit_abs": 100.0,
                },
            ],
        )

        result = collect_daily_metrics_from_db(db_path, None, "2026-02-01")

        assert result is not None
        assert result.date == "2026-02-01"
        assert result.total_trades == 2  # Only 2026-02-01 trades
        assert result.daily_pnl == 300.0  # 500 + (-200)
        assert result.cumulative_pnl == 400.0  # 500 + (-200) + 100
        assert result.open_positions == 1
        assert result.uptime_percent == 95.0  # Fixed value for DB source

    def test_returns_none_for_invalid_db(self, tmp_path):
        """Should return None if database file is not valid SQLite."""
        invalid_db = tmp_path / "invalid.sqlite"
        invalid_db.write_text("not a database")

        result = collect_daily_metrics_from_db(str(invalid_db), None, "2026-02-01")

        assert result is None

    def test_handles_no_trades_for_date(self, tmp_path):
        """Should return metrics with zero trades when no trades match date."""
        db_path = str(tmp_path / "trades.sqlite")
        _create_test_db(
            db_path,
            trades=[
                {
                    "pair": "BTC/JPY",
                    "is_open": 0,
                    "close_date": "2026-01-30 10:00:00",
                    "close_profit_abs": 500.0,
                },
            ],
        )

        result = collect_daily_metrics_from_db(db_path, None, "2026-02-01")

        assert result is not None
        assert result.total_trades == 0
        assert result.daily_pnl == 0.0
        assert result.cumulative_pnl == 500.0  # All closed trades

    def test_reads_log_for_api_errors(self, tmp_path):
        """Should count ERROR lines from log file."""
        db_path = str(tmp_path / "trades.sqlite")
        _create_test_db(db_path, trades=[])

        log_path = str(tmp_path / "freqtrade.log")
        log_lines = [
            "2026-02-01 10:00:00 INFO Starting bot\n",
            "2026-02-01 10:01:00 ERROR Connection failed\n",
            "2026-02-01 10:02:00 INFO Retrying\n",
            "2026-02-01 10:03:00 ERROR Timeout\n",
            "2026-02-01 10:04:00 INFO Success\n",
        ]
        with open(log_path, "w") as f:
            f.writelines(log_lines)

        result = collect_daily_metrics_from_db(db_path, log_path, "2026-02-01")

        assert result is not None
        assert result.api_errors == 2
        assert result.api_total_calls == 5


class TestSaveReportToFile:
    """Test save_report_to_file function."""

    def test_saves_report(self, tmp_path):
        """Should write report content to file."""
        output_dir = str(tmp_path / "reports")
        report_content = "Test report content\nLine 2"

        save_report_to_file(report_content, output_dir, "2026-02-01")

        saved_file = tmp_path / "reports" / "daily_report_2026-02-01.txt"
        assert saved_file.exists()
        assert saved_file.read_text() == report_content

    def test_creates_output_dir(self, tmp_path):
        """Should create output directory if it does not exist."""
        output_dir = str(tmp_path / "new" / "nested" / "dir")

        save_report_to_file("report", output_dir, "2026-02-01")

        assert (tmp_path / "new" / "nested" / "dir").is_dir()

    def test_returns_file_path(self, tmp_path):
        """Should return the path of the saved file."""
        output_dir = str(tmp_path)

        result = save_report_to_file("report", output_dir, "2026-02-01")

        expected = str(tmp_path / "daily_report_2026-02-01.txt")
        assert result == expected
