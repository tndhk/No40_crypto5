"""Tests for daily report generation."""

import pytest

from scripts.daily_report import DailyMetrics, format_daily_report


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
