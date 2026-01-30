"""Tests for Dry Run criteria evaluation."""

import pytest

from scripts.check_dryrun_criteria import DryRunCriteriaResult, DryRunMetrics, evaluate_dryrun


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
