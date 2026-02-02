"""Tests for bot diagnostic script."""

import sqlite3
import time
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.diagnose_bot import (
    DiagnosticReport,
    DiagnosticResult,
    check_api_server,
    check_database,
    check_db_path_consistency,
    check_env_variables,
    check_log_freshness,
    check_open_trades,
    check_process_running,
    check_telegram_token,
    format_diagnostic_report,
    run_all_diagnostics,
)


class TestDiagnosticResult:
    """Test DiagnosticResult frozen dataclass."""

    def test_create_ok_result(self):
        """DiagnosticResult can be created with OK status."""
        result = DiagnosticResult(name="test", status="OK", message="All good")
        assert result.name == "test"
        assert result.status == "OK"
        assert result.message == "All good"

    def test_create_error_result(self):
        """DiagnosticResult can be created with ERROR status."""
        result = DiagnosticResult(name="test", status="ERROR", message="Failed")
        assert result.status == "ERROR"

    def test_immutability(self):
        """DiagnosticResult should be immutable (frozen)."""
        result = DiagnosticResult(name="test", status="OK", message="msg")
        with pytest.raises(FrozenInstanceError):
            result.name = "changed"


class TestDiagnosticReport:
    """Test DiagnosticReport frozen dataclass."""

    def test_create_report(self):
        """DiagnosticReport can be created with results and overall_status."""
        r1 = DiagnosticResult(name="a", status="OK", message="ok")
        report = DiagnosticReport(results=(r1,), overall_status="HEALTHY")
        assert len(report.results) == 1
        assert report.overall_status == "HEALTHY"

    def test_immutability(self):
        """DiagnosticReport should be immutable (frozen)."""
        report = DiagnosticReport(results=(), overall_status="HEALTHY")
        with pytest.raises(FrozenInstanceError):
            report.overall_status = "UNHEALTHY"

    def test_overall_status_values(self):
        """DiagnosticReport overall_status accepts expected values."""
        for status in ("HEALTHY", "DEGRADED", "UNHEALTHY"):
            report = DiagnosticReport(results=(), overall_status=status)
            assert report.overall_status == status


class TestCheckProcessRunning:
    """Test check_process_running function."""

    @patch("scripts.diagnose_bot.subprocess.run")
    def test_process_found(self, mock_run):
        """Returns OK when freqtrade process is running."""
        mock_run.return_value = MagicMock(returncode=0)
        result = check_process_running()
        assert result.status == "OK"
        assert result.name == "process"

    @patch("scripts.diagnose_bot.subprocess.run")
    def test_process_not_found(self, mock_run):
        """Returns ERROR when freqtrade process is not running."""
        mock_run.return_value = MagicMock(returncode=1)
        result = check_process_running()
        assert result.status == "ERROR"
        assert result.name == "process"


class TestCheckApiServer:
    """Test check_api_server function."""

    @patch("scripts.diagnose_bot.fetch_ping")
    def test_api_responding(self, mock_ping):
        """Returns OK when API server responds."""
        mock_resp = MagicMock()
        mock_resp.success = True
        mock_resp.data = {"status": "pong"}
        mock_ping.return_value = mock_resp
        config = MagicMock()
        result = check_api_server(config)
        assert result.status == "OK"
        assert result.name == "api_server"

    @patch("scripts.diagnose_bot.fetch_ping")
    def test_api_not_responding(self, mock_ping):
        """Returns ERROR when API server does not respond."""
        mock_ping.side_effect = Exception("Connection refused")
        config = MagicMock()
        result = check_api_server(config)
        assert result.status == "ERROR"
        assert result.name == "api_server"


class TestCheckDatabase:
    """Test check_database function."""

    def test_valid_database(self, tmp_path):
        """Returns OK for a valid database with trades table."""
        db_path = str(tmp_path / "test.sqlite")
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE trades (id INTEGER PRIMARY KEY, pair TEXT, is_open INTEGER)")
        conn.execute("INSERT INTO trades (pair, is_open) VALUES ('BTC/JPY', 0)")
        conn.execute("INSERT INTO trades (pair, is_open) VALUES ('ETH/JPY', 0)")
        conn.commit()
        conn.close()

        result = check_database(db_path)
        assert result.status == "OK"
        assert result.name == "database"
        assert "2" in result.message  # 2 trades

    def test_file_not_found(self, tmp_path):
        """Returns ERROR when database file does not exist."""
        db_path = str(tmp_path / "nonexistent.sqlite")
        result = check_database(db_path)
        assert result.status == "ERROR"
        assert result.name == "database"

    def test_zero_byte_file(self, tmp_path):
        """Returns ERROR when database file is 0 bytes."""
        db_path = str(tmp_path / "empty.sqlite")
        Path(db_path).touch()
        result = check_database(db_path)
        assert result.status == "ERROR"
        assert result.name == "database"


class TestCheckLogFreshness:
    """Test check_log_freshness function."""

    def test_fresh_log(self, tmp_path):
        """Returns OK when log file was recently modified."""
        log_path = str(tmp_path / "freqtrade.log")
        Path(log_path).write_text("log entry")
        result = check_log_freshness(log_path, max_age_minutes=10)
        assert result.status == "OK"
        assert result.name == "log_freshness"

    def test_stale_log(self, tmp_path):
        """Returns WARNING when log file is older than max_age_minutes."""
        log_path = str(tmp_path / "freqtrade.log")
        Path(log_path).write_text("old log entry")
        # Set mtime to 30 minutes ago
        old_time = time.time() - 1800
        import os

        os.utime(log_path, (old_time, old_time))
        result = check_log_freshness(log_path, max_age_minutes=10)
        assert result.status == "WARNING"
        assert result.name == "log_freshness"

    def test_log_file_not_found(self, tmp_path):
        """Returns ERROR when log file does not exist."""
        log_path = str(tmp_path / "missing.log")
        result = check_log_freshness(log_path)
        assert result.status == "ERROR"
        assert result.name == "log_freshness"


class TestCheckEnvVariables:
    """Test check_env_variables function."""

    def test_all_set(self):
        """Returns OK when all required env variables are set."""
        env_vars = {
            "FREQTRADE__TELEGRAM__TOKEN": "123456:ABC-DEF",
            "FREQTRADE__API_SERVER__PASSWORD": "password",
            "FREQTRADE__API_SERVER__JWT_SECRET_KEY": "secret",
        }
        result = check_env_variables(env_vars)
        assert result.status == "OK"
        assert result.name == "env_variables"

    def test_partial_missing(self):
        """Returns WARNING when some env variables are missing."""
        env_vars = {
            "FREQTRADE__TELEGRAM__TOKEN": "123456:ABC-DEF",
        }
        result = check_env_variables(env_vars)
        assert result.status == "WARNING"
        assert result.name == "env_variables"
        assert "FREQTRADE__API_SERVER__PASSWORD" in result.message
        assert "FREQTRADE__API_SERVER__JWT_SECRET_KEY" in result.message

    def test_none_env_uses_os_environ(self):
        """When env_vars is None, falls back to os.environ."""
        with patch.dict("os.environ", {}, clear=True):
            result = check_env_variables(None)
            assert result.status == "WARNING"


class TestCheckTelegramToken:
    """Test check_telegram_token function."""

    def test_valid_token(self):
        """Returns OK for correctly formatted Telegram token."""
        env_vars = {"FREQTRADE__TELEGRAM__TOKEN": "123456789:ABCdefGHI-jklMNO_pqr"}
        result = check_telegram_token(env_vars)
        assert result.status == "OK"
        assert result.name == "telegram_token"

    def test_invalid_format(self):
        """Returns ERROR for incorrectly formatted Telegram token."""
        env_vars = {"FREQTRADE__TELEGRAM__TOKEN": "not-a-valid-token"}
        result = check_telegram_token(env_vars)
        assert result.status == "ERROR"
        assert result.name == "telegram_token"

    def test_not_set(self):
        """Returns WARNING when Telegram token is not set."""
        env_vars = {}
        result = check_telegram_token(env_vars)
        assert result.status == "WARNING"
        assert result.name == "telegram_token"

    def test_none_env_uses_os_environ(self):
        """When env_vars is None, falls back to os.environ."""
        with patch.dict("os.environ", {}, clear=True):
            result = check_telegram_token(None)
            assert result.status == "WARNING"


class TestCheckDbPathConsistency:
    """Test check_db_path_consistency function."""

    def test_ghost_file_detected(self, tmp_path):
        """Returns WARNING when user_data db is 0 bytes but root db has data."""
        # Create user_data directory structure
        user_data = tmp_path / "user_data"
        user_data.mkdir()
        # Ghost file: 0 bytes in user_data
        ghost_db = user_data / "tradesv3.dryrun.sqlite"
        ghost_db.touch()
        # Real file in project root
        real_db = tmp_path / "tradesv3.dryrun.sqlite"
        conn = sqlite3.connect(str(real_db))
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.commit()
        conn.close()

        result = check_db_path_consistency(str(tmp_path))
        assert result.status == "WARNING"
        assert result.name == "db_path_consistency"

    def test_no_ghost_file(self, tmp_path):
        """Returns OK when there is no ghost file issue."""
        user_data = tmp_path / "user_data"
        user_data.mkdir()
        result = check_db_path_consistency(str(tmp_path))
        assert result.status == "OK"
        assert result.name == "db_path_consistency"

    def test_root_only_real_data(self, tmp_path):
        """Returns OK when only root has data and no user_data ghost."""
        user_data = tmp_path / "user_data"
        user_data.mkdir()
        # Root has a real DB, but user_data does NOT have ghost
        real_db = tmp_path / "tradesv3.dryrun.sqlite"
        conn = sqlite3.connect(str(real_db))
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.commit()
        conn.close()
        result = check_db_path_consistency(str(tmp_path))
        assert result.status == "OK"
        assert result.name == "db_path_consistency"


class TestCheckOpenTrades:
    """Test check_open_trades function."""

    def test_no_open_trades(self, tmp_path):
        """Returns OK when there are no open trades."""
        db_path = str(tmp_path / "test.sqlite")
        conn = sqlite3.connect(db_path)
        conn.execute(
            "CREATE TABLE trades ("
            "id INTEGER PRIMARY KEY, pair TEXT, is_open INTEGER, "
            "open_date TEXT)"
        )
        conn.execute(
            "INSERT INTO trades (pair, is_open, open_date) VALUES ('BTC/JPY', 0, ?)",
            (datetime.now(timezone.utc).isoformat(),),
        )
        conn.commit()
        conn.close()
        result = check_open_trades(db_path)
        assert result.status == "OK"
        assert result.name == "open_trades"

    def test_open_trade_within_7_days(self, tmp_path):
        """Returns OK when open trades are within 7 days."""
        db_path = str(tmp_path / "test.sqlite")
        conn = sqlite3.connect(db_path)
        conn.execute(
            "CREATE TABLE trades ("
            "id INTEGER PRIMARY KEY, pair TEXT, is_open INTEGER, "
            "open_date TEXT)"
        )
        recent = datetime.now(timezone.utc) - timedelta(hours=12)
        conn.execute(
            "INSERT INTO trades (pair, is_open, open_date) VALUES ('BTC/JPY', 1, ?)",
            (recent.isoformat(),),
        )
        conn.commit()
        conn.close()
        result = check_open_trades(db_path)
        assert result.status == "OK"
        assert result.name == "open_trades"

    def test_stale_open_trade(self, tmp_path):
        """Returns WARNING when open trade is older than 7 days."""
        db_path = str(tmp_path / "test.sqlite")
        conn = sqlite3.connect(db_path)
        conn.execute(
            "CREATE TABLE trades ("
            "id INTEGER PRIMARY KEY, pair TEXT, is_open INTEGER, "
            "open_date TEXT)"
        )
        old_date = datetime.now(timezone.utc) - timedelta(days=10)
        conn.execute(
            "INSERT INTO trades (pair, is_open, open_date) VALUES ('BTC/JPY', 1, ?)",
            (old_date.isoformat(),),
        )
        conn.commit()
        conn.close()
        result = check_open_trades(db_path)
        assert result.status == "WARNING"
        assert result.name == "open_trades"

    def test_db_not_found(self, tmp_path):
        """Returns ERROR when database file does not exist."""
        db_path = str(tmp_path / "nonexistent.sqlite")
        result = check_open_trades(db_path)
        assert result.status == "ERROR"
        assert result.name == "open_trades"


class TestRunAllDiagnostics:
    """Test run_all_diagnostics function."""

    @patch("scripts.diagnose_bot.check_open_trades")
    @patch("scripts.diagnose_bot.check_db_path_consistency")
    @patch("scripts.diagnose_bot.check_telegram_token")
    @patch("scripts.diagnose_bot.check_env_variables")
    @patch("scripts.diagnose_bot.check_log_freshness")
    @patch("scripts.diagnose_bot.check_database")
    @patch("scripts.diagnose_bot.check_api_server")
    @patch("scripts.diagnose_bot.check_process_running")
    def test_all_ok_returns_healthy(
        self,
        mock_proc,
        mock_api,
        mock_db,
        mock_log,
        mock_env,
        mock_tg,
        mock_dbpath,
        mock_open,
    ):
        """Returns HEALTHY when all checks pass."""
        ok = DiagnosticResult(name="test", status="OK", message="ok")
        mock_proc.return_value = ok
        mock_api.return_value = ok
        mock_db.return_value = ok
        mock_log.return_value = ok
        mock_env.return_value = ok
        mock_tg.return_value = ok
        mock_dbpath.return_value = ok
        mock_open.return_value = ok

        config = MagicMock()
        report = run_all_diagnostics("/tmp/project", config)
        assert report.overall_status == "HEALTHY"

    @patch("scripts.diagnose_bot.check_open_trades")
    @patch("scripts.diagnose_bot.check_db_path_consistency")
    @patch("scripts.diagnose_bot.check_telegram_token")
    @patch("scripts.diagnose_bot.check_env_variables")
    @patch("scripts.diagnose_bot.check_log_freshness")
    @patch("scripts.diagnose_bot.check_database")
    @patch("scripts.diagnose_bot.check_api_server")
    @patch("scripts.diagnose_bot.check_process_running")
    def test_warning_returns_degraded(
        self,
        mock_proc,
        mock_api,
        mock_db,
        mock_log,
        mock_env,
        mock_tg,
        mock_dbpath,
        mock_open,
    ):
        """Returns DEGRADED when there are warnings but no errors."""
        ok = DiagnosticResult(name="test", status="OK", message="ok")
        warn = DiagnosticResult(name="test", status="WARNING", message="warn")
        mock_proc.return_value = ok
        mock_api.return_value = ok
        mock_db.return_value = ok
        mock_log.return_value = warn
        mock_env.return_value = ok
        mock_tg.return_value = ok
        mock_dbpath.return_value = ok
        mock_open.return_value = ok

        config = MagicMock()
        report = run_all_diagnostics("/tmp/project", config)
        assert report.overall_status == "DEGRADED"

    @patch("scripts.diagnose_bot.check_open_trades")
    @patch("scripts.diagnose_bot.check_db_path_consistency")
    @patch("scripts.diagnose_bot.check_telegram_token")
    @patch("scripts.diagnose_bot.check_env_variables")
    @patch("scripts.diagnose_bot.check_log_freshness")
    @patch("scripts.diagnose_bot.check_database")
    @patch("scripts.diagnose_bot.check_api_server")
    @patch("scripts.diagnose_bot.check_process_running")
    def test_error_returns_unhealthy(
        self,
        mock_proc,
        mock_api,
        mock_db,
        mock_log,
        mock_env,
        mock_tg,
        mock_dbpath,
        mock_open,
    ):
        """Returns UNHEALTHY when there is at least one error."""
        ok = DiagnosticResult(name="test", status="OK", message="ok")
        err = DiagnosticResult(name="test", status="ERROR", message="fail")
        mock_proc.return_value = err
        mock_api.return_value = ok
        mock_db.return_value = ok
        mock_log.return_value = ok
        mock_env.return_value = ok
        mock_tg.return_value = ok
        mock_dbpath.return_value = ok
        mock_open.return_value = ok

        config = MagicMock()
        report = run_all_diagnostics("/tmp/project", config)
        assert report.overall_status == "UNHEALTHY"


class TestFormatDiagnosticReport:
    """Test format_diagnostic_report function."""

    def test_format_contains_status_prefixes(self):
        """Output contains [OK], [WARNING], [ERROR] prefixes."""
        results = (
            DiagnosticResult(name="proc", status="OK", message="running"),
            DiagnosticResult(name="api", status="WARNING", message="slow"),
            DiagnosticResult(name="db", status="ERROR", message="missing"),
        )
        report = DiagnosticReport(results=results, overall_status="UNHEALTHY")
        output = format_diagnostic_report(report)
        assert "[OK]" in output
        assert "[WARNING]" in output
        assert "[ERROR]" in output

    def test_format_contains_overall_status(self):
        """Output contains the overall status."""
        results = (DiagnosticResult(name="test", status="OK", message="ok"),)
        report = DiagnosticReport(results=results, overall_status="HEALTHY")
        output = format_diagnostic_report(report)
        assert "HEALTHY" in output

    def test_format_contains_result_names(self):
        """Output contains the name of each diagnostic result."""
        results = (
            DiagnosticResult(name="process", status="OK", message="running"),
            DiagnosticResult(name="database", status="OK", message="ok"),
        )
        report = DiagnosticReport(results=results, overall_status="HEALTHY")
        output = format_diagnostic_report(report)
        assert "process" in output
        assert "database" in output

    def test_format_contains_messages(self):
        """Output contains the message from each diagnostic result."""
        results = (DiagnosticResult(name="test", status="ERROR", message="connection refused"),)
        report = DiagnosticReport(results=results, overall_status="UNHEALTHY")
        output = format_diagnostic_report(report)
        assert "connection refused" in output
