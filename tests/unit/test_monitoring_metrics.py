"""Tests for shared monitoring helpers."""

import pytest

from scripts.monitoring_metrics import calculate_api_error_stats, is_ignored_api_error


class TestIgnoredApiErrors:
    """Known websocket churn should not count as API instability."""

    def test_ignores_binance_ws_1008_disconnects(self):
        message = (
            "ERROR Exception in continuously_async_watch_ohlcv for BTC/USDT, 15m\n"
            "ccxt.base.errors.NetworkError: Connection closed by remote server, closing code 1008"
        )
        assert is_ignored_api_error(message) is True

    def test_does_not_ignore_strategy_type_error(self):
        message = (
            'ERROR Unexpected error TypeError("DCAStrategy.confirm_trade_exit() '
            'missing 3 required positional arguments")'
        )
        assert is_ignored_api_error(message) is False

    def test_calculate_api_error_stats_excludes_ignored_errors(self):
        log_entries = [
            {"timestamp": "2026-03-17 04:15:02", "message": "INFO Heartbeat"},
            {
                "timestamp": "2026-03-17 04:15:03",
                "message": (
                    "ERROR Exception in _unwatch_ohlcv\n"
                    "ccxt.base.errors.NetworkError: Connection closed by remote server, closing code 1008"
                ),
            },
            {
                "timestamp": "2026-03-17 04:16:03",
                "message": 'ERROR Unexpected error TypeError("confirm_trade_exit")',
            },
        ]

        errors, total, rate = calculate_api_error_stats(log_entries)

        assert errors == 1
        assert total == 3
        assert rate == pytest.approx(100 / 3)
