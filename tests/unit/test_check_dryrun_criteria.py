"""Tests for Dry Run criteria evaluation."""

import json
import sqlite3
from datetime import date, timedelta
from unittest.mock import patch

import pytest

from scripts.check_dryrun_criteria import (
    DryRunCriteriaResult,
    DryRunMetrics,
    calculate_api_error_rate_from_logs,
    calculate_days_running,
    calculate_order_accuracy_from_trades,
    calculate_sharpe_deviation,
    calculate_uptime_from_logs,
    collect_metrics_from_api,
    collect_metrics_from_db,
    evaluate_dryrun,
    find_database_path,
)
from scripts.freqtrade_api_client import ApiClientConfig, ApiResponse


class TestDryRunCriteria:
    """Test Dry Run criteria evaluation."""

    def test_all_criteria_met(self):
        """All criteria met should pass validation."""
        metrics = DryRunMetrics(
            uptime_percent=99.5,
            api_error_rate=0.2,
            order_accuracy=100.0,
            sharpe_deviation=0.1,
            days_running=14,
        )
        result = evaluate_dryrun(metrics)
        assert result.passed is True
        assert len(result.details) >= 1
        assert any("PASS" in detail for detail in result.details)

    def test_low_uptime_fails(self):
        """Uptime below 99% should fail."""
        metrics = DryRunMetrics(
            uptime_percent=98.5,
            api_error_rate=0.2,
            order_accuracy=100.0,
            sharpe_deviation=0.1,
            days_running=14,
        )
        result = evaluate_dryrun(metrics)
        assert result.passed is False
        assert any("Uptime" in detail or "uptime" in detail for detail in result.details)

    def test_high_api_error_rate_fails(self):
        """API error rate >= 1% should fail."""
        metrics = DryRunMetrics(
            uptime_percent=99.5,
            api_error_rate=1.5,
            order_accuracy=100.0,
            sharpe_deviation=0.1,
            days_running=14,
        )
        result = evaluate_dryrun(metrics)
        assert result.passed is False
        assert any("API error" in detail or "error rate" in detail for detail in result.details)

    def test_insufficient_days_fails(self):
        """Less than 14 days should fail."""
        metrics = DryRunMetrics(
            uptime_percent=99.5,
            api_error_rate=0.2,
            order_accuracy=100.0,
            sharpe_deviation=0.1,
            days_running=13,
        )
        result = evaluate_dryrun(metrics)
        assert result.passed is False
        assert any("14 days" in detail or "days" in detail for detail in result.details)

    def test_high_sharpe_deviation_fails(self):
        """Sharpe deviation > 0.3 should fail."""
        metrics = DryRunMetrics(
            uptime_percent=99.5,
            api_error_rate=0.2,
            order_accuracy=100.0,
            sharpe_deviation=0.4,
            days_running=14,
        )
        result = evaluate_dryrun(metrics)
        assert result.passed is False
        assert any("Sharpe" in detail or "sharpe" in detail for detail in result.details)

    def test_low_order_accuracy_fails(self):
        """Order accuracy < 98% should fail."""
        metrics = DryRunMetrics(
            uptime_percent=99.5,
            api_error_rate=0.2,
            order_accuracy=97.0,
            sharpe_deviation=0.1,
            days_running=14,
        )
        result = evaluate_dryrun(metrics)
        assert result.passed is False
        assert any("Order accuracy" in detail or "accuracy" in detail for detail in result.details)

    def test_multiple_failures_reported(self):
        """Multiple criteria failures should all be reported."""
        metrics = DryRunMetrics(
            uptime_percent=98.0,
            api_error_rate=2.0,
            order_accuracy=95.0,
            sharpe_deviation=0.5,
            days_running=10,
        )
        result = evaluate_dryrun(metrics)
        assert result.passed is False
        assert len(result.details) >= 5

    def test_edge_case_exactly_at_minimum_threshold(self):
        """Exactly at minimum threshold should pass."""
        metrics = DryRunMetrics(
            uptime_percent=99.0,
            api_error_rate=0.99,
            order_accuracy=98.0,
            sharpe_deviation=0.3,
            days_running=14,
        )
        result = evaluate_dryrun(metrics)
        assert result.passed is True


class TestDryRunMetrics:
    """Test DryRunMetrics dataclass."""

    def test_dry_run_metrics_is_immutable(self):
        """DryRunMetrics should be immutable."""
        metrics = DryRunMetrics(
            uptime_percent=99.5,
            api_error_rate=0.2,
            order_accuracy=100.0,
            sharpe_deviation=0.1,
            days_running=14,
        )
        with pytest.raises(Exception):
            metrics.uptime_percent = 98.0

    def test_dry_run_metrics_all_fields_required(self):
        """All fields should be required."""
        with pytest.raises(TypeError):
            DryRunMetrics(
                uptime_percent=99.5,
                api_error_rate=0.2,
            )


class TestDryRunCriteriaResult:
    """Test DryRunCriteriaResult dataclass."""

    def test_criteria_result_is_immutable(self):
        """DryRunCriteriaResult should be immutable."""
        result = DryRunCriteriaResult(passed=True, details=("detail1",))
        with pytest.raises(Exception):
            result.passed = False

    def test_details_is_tuple(self):
        """Details should be stored as tuple."""
        result = DryRunCriteriaResult(
            passed=False,
            details=("detail1", "detail2"),
        )
        assert isinstance(result.details, tuple)
        assert len(result.details) == 2


# ---------------------------------------------------------------------------
# New test classes for data collection functions
# ---------------------------------------------------------------------------


class TestCalculateUptimeFromLogs:
    """Test uptime calculation from log entries."""

    def test_continuous_logs_returns_high_uptime(self):
        """Continuous log entries (no gaps > 5 min) should return ~100%."""
        logs = [
            {"timestamp": "2026-01-30 10:00:00", "message": "INFO: Heartbeat"},
            {"timestamp": "2026-01-30 10:01:00", "message": "INFO: Heartbeat"},
            {"timestamp": "2026-01-30 10:02:00", "message": "INFO: Heartbeat"},
            {"timestamp": "2026-01-30 10:03:00", "message": "INFO: Heartbeat"},
            {"timestamp": "2026-01-30 10:04:00", "message": "INFO: Heartbeat"},
        ]
        result = calculate_uptime_from_logs(logs)
        assert result == pytest.approx(100.0, abs=0.1)

    def test_empty_logs_returns_zero(self):
        """Empty log list should return 0.0."""
        result = calculate_uptime_from_logs([])
        assert result == 0.0

    def test_logs_with_gap_reduces_uptime(self):
        """A gap of >5 minutes in logs should reduce uptime."""
        # Total span: 20 minutes (10:00 -> 10:20)
        # Gap: 10:05 -> 10:15 = 10 minutes (minus 5 min threshold = 5 min gap)
        logs = [
            {"timestamp": "2026-01-30 10:00:00", "message": "INFO: Heartbeat"},
            {"timestamp": "2026-01-30 10:05:00", "message": "INFO: Heartbeat"},
            # 10-minute gap here (> 5 min threshold)
            {"timestamp": "2026-01-30 10:15:00", "message": "INFO: Heartbeat"},
            {"timestamp": "2026-01-30 10:20:00", "message": "INFO: Heartbeat"},
        ]
        result = calculate_uptime_from_logs(logs)
        # Total span = 20 min, gap = 10 min, uptime = (20-10)/20 * 100 = 50%
        assert result < 100.0
        assert result > 0.0

    def test_single_log_entry_returns_zero(self):
        """A single log entry cannot compute span, should return 0.0."""
        logs = [{"timestamp": "2026-01-30 10:00:00", "message": "INFO: Heartbeat"}]
        result = calculate_uptime_from_logs(logs)
        assert result == 0.0


class TestCalculateApiErrorRate:
    """Test API error rate calculation from logs."""

    def test_no_errors(self):
        """Logs with no ERROR messages should return 0.0."""
        logs = [
            {"timestamp": "2026-01-30 10:00:00", "message": "INFO: Trade opened"},
            {"timestamp": "2026-01-30 10:01:00", "message": "INFO: Heartbeat"},
        ]
        result = calculate_api_error_rate_from_logs(logs)
        assert result == 0.0

    def test_some_errors(self):
        """Logs with some ERROR messages should calculate correct rate."""
        logs = [
            {"timestamp": "2026-01-30 10:00:00", "message": "INFO: Trade opened"},
            {"timestamp": "2026-01-30 10:01:00", "message": "ERROR: Connection failed"},
            {"timestamp": "2026-01-30 10:02:00", "message": "INFO: Heartbeat"},
            {"timestamp": "2026-01-30 10:03:00", "message": "ERROR: Timeout"},
        ]
        result = calculate_api_error_rate_from_logs(logs)
        # 2 errors out of 4 = 50%
        assert result == pytest.approx(50.0)

    def test_empty_logs(self):
        """Empty log list should return 0.0."""
        result = calculate_api_error_rate_from_logs([])
        assert result == 0.0


class TestCalculateOrderAccuracy:
    """Test order accuracy calculation from trades."""

    def test_all_normal_exits(self):
        """All normal exits should return 100%."""
        trades = [
            {"close_profit_abs": 100, "exit_reason": "roi"},
            {"close_profit_abs": -50, "exit_reason": "stop_loss"},
            {"close_profit_abs": 200, "exit_reason": "trailing_stop_loss"},
        ]
        result = calculate_order_accuracy_from_trades(trades)
        assert result == pytest.approx(100.0)

    def test_some_force_exits(self):
        """Force exits should reduce accuracy."""
        trades = [
            {"close_profit_abs": 100, "exit_reason": "roi"},
            {"close_profit_abs": -50, "exit_reason": "force_exit"},
            {"close_profit_abs": 200, "exit_reason": "trailing_stop_loss"},
            {"close_profit_abs": -20, "exit_reason": "emergency_exit"},
        ]
        result = calculate_order_accuracy_from_trades(trades)
        # 2 normal out of 4 closed = 50%
        assert result == pytest.approx(50.0)

    def test_no_trades(self):
        """No trades should return 100.0."""
        result = calculate_order_accuracy_from_trades([])
        assert result == 100.0

    def test_dca_replaced_is_normal(self):
        """DCA-replaced trades should be treated as normal."""
        trades = [
            {"close_profit_abs": 0, "exit_reason": "replaced"},
            {"close_profit_abs": 100, "exit_reason": "roi"},
        ]
        result = calculate_order_accuracy_from_trades(trades)
        assert result == pytest.approx(100.0)

    def test_open_trades_ignored(self):
        """Trades without close_profit_abs (open) should be ignored."""
        trades = [
            {"exit_reason": ""},  # open trade, no close_profit_abs
            {"close_profit_abs": 100, "exit_reason": "roi"},
        ]
        result = calculate_order_accuracy_from_trades(trades)
        assert result == pytest.approx(100.0)


class TestCalculateSharpeDeviation:
    """Test Sharpe ratio deviation calculation."""

    def test_with_enough_trades(self):
        """With 5+ closed trades, should calculate deviation from backtest."""
        trades = [
            {"is_open": False, "close_profit": 0.05},
            {"is_open": False, "close_profit": 0.03},
            {"is_open": False, "close_profit": -0.02},
            {"is_open": False, "close_profit": 0.04},
            {"is_open": False, "close_profit": 0.01},
        ]
        result = calculate_sharpe_deviation(trades, backtest_sharpe=0.28)
        assert isinstance(result, float)
        assert result >= 0.0

    def test_too_few_trades(self):
        """With fewer than 5 closed trades, should return 1.0."""
        trades = [
            {"is_open": False, "close_profit": 0.05},
            {"is_open": False, "close_profit": 0.03},
        ]
        result = calculate_sharpe_deviation(trades, backtest_sharpe=0.28)
        assert result == 1.0

    def test_zero_std_returns_backtest_sharpe(self):
        """If all returns are the same (std=0), Sharpe=0, deviation=backtest_sharpe."""
        trades = [
            {"is_open": False, "close_profit": 0.05},
            {"is_open": False, "close_profit": 0.05},
            {"is_open": False, "close_profit": 0.05},
            {"is_open": False, "close_profit": 0.05},
            {"is_open": False, "close_profit": 0.05},
        ]
        result = calculate_sharpe_deviation(trades, backtest_sharpe=0.28)
        assert result == pytest.approx(0.28)

    def test_open_trades_excluded(self):
        """Open trades should be excluded from calculation."""
        trades = [
            {"is_open": True, "close_profit": 0.0},
            {"is_open": False, "close_profit": 0.05},
            {"is_open": False, "close_profit": 0.03},
        ]
        # Only 2 closed trades => too few => return 1.0
        result = calculate_sharpe_deviation(trades, backtest_sharpe=0.28)
        assert result == 1.0


class TestCalculateDaysRunning:
    """Test days running calculation."""

    def test_calculates_days(self):
        """Should calculate correct number of days from start date to today."""
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        result = calculate_days_running(yesterday)
        assert result == 1

    def test_same_day_returns_zero(self):
        """Same day should return 0 days."""
        today = date.today().isoformat()
        result = calculate_days_running(today)
        assert result == 0

    def test_many_days(self):
        """Should handle many days correctly."""
        start = (date.today() - timedelta(days=14)).isoformat()
        result = calculate_days_running(start)
        assert result == 14


class TestFindDatabasePath:
    """Test database path discovery."""

    def test_finds_root_db(self, tmp_path):
        """Should find database file at project root."""
        db_file = tmp_path / "tradesv3.dryrun.sqlite"
        db_file.write_bytes(b"some data")  # non-zero file
        result = find_database_path(str(tmp_path))
        assert result == str(db_file)

    def test_finds_user_data_db(self, tmp_path):
        """Should find database in user_data directory."""
        user_data = tmp_path / "user_data"
        user_data.mkdir()
        db_file = user_data / "tradesv3.dryrun.sqlite"
        db_file.write_bytes(b"some data")
        result = find_database_path(str(tmp_path))
        assert result == str(db_file)

    def test_returns_none_when_no_db(self, tmp_path):
        """Should return None when no database file exists."""
        result = find_database_path(str(tmp_path))
        assert result is None

    def test_skips_zero_byte_file(self, tmp_path):
        """Should skip zero-byte database files."""
        db_file = tmp_path / "tradesv3.dryrun.sqlite"
        db_file.write_bytes(b"")  # zero-byte file
        result = find_database_path(str(tmp_path))
        assert result is None

    def test_reads_config_db_url(self, tmp_path):
        """Should use db_url from config.json if present."""
        config_dir = tmp_path / "user_data" / "config"
        config_dir.mkdir(parents=True)
        db_file = tmp_path / "custom.sqlite"
        db_file.write_bytes(b"some data")
        config = {"db_url": f"sqlite:///{db_file}"}
        (config_dir / "config.json").write_text(json.dumps(config))
        result = find_database_path(str(tmp_path))
        assert result == str(db_file)


class TestCollectMetricsFromApi:
    """Test API-based metrics collection."""

    @patch("scripts.check_dryrun_criteria.fetch_trades")
    @patch("scripts.check_dryrun_criteria.fetch_logs")
    def test_successful_collection(self, mock_logs, mock_trades):
        """Should collect metrics successfully from API."""
        mock_trades.return_value = ApiResponse(
            success=True,
            data={
                "trades": [
                    {
                        "close_profit_abs": 100,
                        "close_profit": 0.05,
                        "exit_reason": "roi",
                        "is_open": False,
                    },
                    {
                        "close_profit_abs": -50,
                        "close_profit": -0.02,
                        "exit_reason": "stop_loss",
                        "is_open": False,
                    },
                    {
                        "close_profit_abs": 200,
                        "close_profit": 0.08,
                        "exit_reason": "roi",
                        "is_open": False,
                    },
                    {
                        "close_profit_abs": 150,
                        "close_profit": 0.06,
                        "exit_reason": "trailing_stop_loss",
                        "is_open": False,
                    },
                    {
                        "close_profit_abs": 80,
                        "close_profit": 0.03,
                        "exit_reason": "roi",
                        "is_open": False,
                    },
                ],
            },
            error="",
            status_code=200,
        )
        mock_logs.return_value = ApiResponse(
            success=True,
            data={
                "logs": [
                    {"timestamp": "2026-01-30 10:00:00", "message": "INFO: Heartbeat"},
                    {"timestamp": "2026-01-30 10:01:00", "message": "INFO: Trade opened"},
                    {"timestamp": "2026-01-30 10:02:00", "message": "INFO: Heartbeat"},
                ],
            },
            error="",
            status_code=200,
        )

        config = ApiClientConfig()
        result = collect_metrics_from_api(config)
        assert result is not None
        assert isinstance(result, DryRunMetrics)
        assert result.order_accuracy == pytest.approx(100.0)

    @patch("scripts.check_dryrun_criteria.fetch_trades")
    @patch("scripts.check_dryrun_criteria.fetch_logs")
    def test_returns_none_on_api_failure(self, mock_logs, mock_trades):
        """Should return None when API call fails."""
        mock_trades.return_value = ApiResponse(
            success=False,
            data=None,
            error="Connection refused",
            status_code=0,
        )
        mock_logs.return_value = ApiResponse(
            success=False,
            data=None,
            error="Connection refused",
            status_code=0,
        )

        config = ApiClientConfig()
        result = collect_metrics_from_api(config)
        assert result is None

    @patch("scripts.check_dryrun_criteria.fetch_trades")
    @patch("scripts.check_dryrun_criteria.fetch_logs")
    def test_handles_list_format_logs(self, mock_logs, mock_trades):
        """Should handle list-format log entries returned by the REST API."""
        mock_trades.return_value = ApiResponse(
            success=True,
            data={
                "trades": [
                    {
                        "close_profit_abs": 100,
                        "close_profit": 0.05,
                        "exit_reason": "roi",
                        "is_open": False,
                    },
                    {
                        "close_profit_abs": -50,
                        "close_profit": -0.02,
                        "exit_reason": "stop_loss",
                        "is_open": False,
                    },
                    {
                        "close_profit_abs": 200,
                        "close_profit": 0.08,
                        "exit_reason": "roi",
                        "is_open": False,
                    },
                    {
                        "close_profit_abs": 150,
                        "close_profit": 0.06,
                        "exit_reason": "trailing_stop_loss",
                        "is_open": False,
                    },
                    {
                        "close_profit_abs": 80,
                        "close_profit": 0.03,
                        "exit_reason": "roi",
                        "is_open": False,
                    },
                ],
            },
            error="",
            status_code=200,
        )
        # Simulate list-format log entries as returned by the Freqtrade REST API:
        # [timestamp_str, epoch, logger_name, log_level, message]
        mock_logs.return_value = ApiResponse(
            success=True,
            data={
                "logs": [
                    ["2026-01-30 10:00:00", 1770024949849.93, "freqtrade.main", "INFO", "Heartbeat"],
                    ["2026-01-30 10:01:00", 1770024950000.00, "uvicorn.access", "INFO", 'GET /api/v1/trades'],
                    ["2026-01-30 10:02:00", 1770024950100.00, "freqtrade.main", "INFO", "Heartbeat"],
                ],
            },
            error="",
            status_code=200,
        )

        config = ApiClientConfig()
        result = collect_metrics_from_api(config)
        assert result is not None
        assert isinstance(result, DryRunMetrics)
        assert result.uptime_percent == pytest.approx(100.0, abs=0.1)
        assert result.api_error_rate == pytest.approx(0.0)
        assert result.order_accuracy == pytest.approx(100.0)


class TestCollectMetricsFromDb:
    """Test database-based metrics collection."""

    def test_reads_from_database(self, tmp_path):
        """Should read trade data from SQLite database."""
        db_path = tmp_path / "trades.sqlite"
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            """CREATE TABLE trades (
                id INTEGER PRIMARY KEY,
                pair TEXT,
                is_open INTEGER,
                close_profit REAL,
                close_profit_abs REAL,
                exit_reason TEXT
            )"""
        )
        conn.execute("INSERT INTO trades VALUES (1, 'BTC/JPY', 0, 0.05, 100, 'roi')")
        conn.execute("INSERT INTO trades VALUES (2, 'ETH/JPY', 0, -0.02, -50, 'stop_loss')")
        conn.execute("INSERT INTO trades VALUES (3, 'XRP/JPY', 0, 0.03, 80, 'roi')")
        conn.execute("INSERT INTO trades VALUES (4, 'ADA/JPY', 0, 0.04, 120, 'roi')")
        conn.execute("INSERT INTO trades VALUES (5, 'SOL/JPY', 0, 0.06, 200, 'trailing_stop_loss')")
        conn.commit()
        conn.close()

        result = collect_metrics_from_db(str(db_path))
        assert result is not None
        assert isinstance(result, DryRunMetrics)
        assert result.uptime_percent == 95.0  # fixed estimate
        assert result.order_accuracy == pytest.approx(100.0)

    def test_returns_none_for_invalid_db(self, tmp_path):
        """Should return None when database is invalid."""
        db_path = tmp_path / "invalid.sqlite"
        db_path.write_text("not a database")

        result = collect_metrics_from_db(str(db_path))
        assert result is None

    def test_reads_log_file_for_error_rate(self, tmp_path):
        """Should calculate error rate from log file if provided."""
        db_path = tmp_path / "trades.sqlite"
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            """CREATE TABLE trades (
                id INTEGER PRIMARY KEY,
                pair TEXT,
                is_open INTEGER,
                close_profit REAL,
                close_profit_abs REAL,
                exit_reason TEXT
            )"""
        )
        conn.execute("INSERT INTO trades VALUES (1, 'BTC/JPY', 0, 0.05, 100, 'roi')")
        conn.execute("INSERT INTO trades VALUES (2, 'ETH/JPY', 0, -0.02, -50, 'stop_loss')")
        conn.execute("INSERT INTO trades VALUES (3, 'XRP/JPY', 0, 0.03, 80, 'roi')")
        conn.execute("INSERT INTO trades VALUES (4, 'ADA/JPY', 0, 0.04, 120, 'roi')")
        conn.execute("INSERT INTO trades VALUES (5, 'SOL/JPY', 0, 0.06, 200, 'trailing_stop_loss')")
        conn.commit()
        conn.close()

        log_path = tmp_path / "freqtrade.log"
        log_path.write_text(
            "2026-01-30 10:00:00 INFO: Heartbeat\n"
            "2026-01-30 10:01:00 ERROR: Connection failed\n"
            "2026-01-30 10:02:00 INFO: Trade opened\n"
            "2026-01-30 10:03:00 INFO: Heartbeat\n"
        )

        result = collect_metrics_from_db(str(db_path), str(log_path))
        assert result is not None
        # 1 error out of 4 lines = 25%
        assert result.api_error_rate == pytest.approx(25.0)
