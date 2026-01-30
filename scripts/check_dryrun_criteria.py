"""Dry Run criteria evaluation for Freqtrade DCA bot."""

import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class DryRunMetrics:
    """Metrics collected during Dry Run."""

    uptime_percent: float
    api_error_rate: float
    order_accuracy: float
    sharpe_deviation: float
    days_running: int


@dataclass(frozen=True)
class DryRunCriteriaResult:
    """Result of Dry Run criteria evaluation."""

    passed: bool
    details: tuple[str, ...]


def evaluate_dryrun(metrics: DryRunMetrics) -> DryRunCriteriaResult:
    """Evaluate Dry Run metrics against acceptance criteria.

    Acceptance criteria:
    - Uptime >= 99%
    - API error rate < 1%
    - Order accuracy >= 98%
    - Sharpe ratio deviation <= 0.3
    - Running period >= 14 days

    Args:
        metrics: DryRunMetrics to evaluate

    Returns:
        DryRunCriteriaResult with pass/fail status and details

    """
    details = []
    passed = True

    # Check uptime
    if metrics.uptime_percent >= 99.0:
        details.append(f"✓ Uptime: {metrics.uptime_percent:.1f}% (>= 99%)")
    else:
        details.append(f"✗ Uptime: {metrics.uptime_percent:.1f}% (< 99%)")
        passed = False

    # Check API error rate
    if metrics.api_error_rate < 1.0:
        details.append(f"✓ API error rate: {metrics.api_error_rate:.2f}% (< 1%)")
    else:
        details.append(f"✗ API error rate: {metrics.api_error_rate:.2f}% (>= 1%)")
        passed = False

    # Check order accuracy
    if metrics.order_accuracy >= 98.0:
        details.append(f"✓ Order accuracy: {metrics.order_accuracy:.1f}% (>= 98%)")
    else:
        details.append(f"✗ Order accuracy: {metrics.order_accuracy:.1f}% (< 98%)")
        passed = False

    # Check Sharpe deviation
    if metrics.sharpe_deviation <= 0.3:
        details.append(f"✓ Sharpe deviation: {metrics.sharpe_deviation:.2f} (<= 0.3)")
    else:
        details.append(f"✗ Sharpe deviation: {metrics.sharpe_deviation:.2f} (> 0.3)")
        passed = False

    # Check days running
    if metrics.days_running >= 14:
        details.append(f"✓ Running period: {metrics.days_running} days (>= 14 days)")
    else:
        details.append(f"✗ Running period: {metrics.days_running} days (< 14 days)")
        passed = False

    # Add overall result
    if passed:
        details.append("\n✓ Dry Run PASSED - Ready for backtest")
    else:
        details.append("\n✗ Dry Run FAILED - Continue monitoring")

    return DryRunCriteriaResult(
        passed=passed,
        details=tuple(details),
    )


def main() -> int:
    """Main entry point for CLI usage.

    In production, this would fetch metrics from Freqtrade API or logs.
    For now, it's a placeholder for manual testing.

    """
    # Example usage (in production, fetch from Freqtrade API)
    print("Dry Run Criteria Checker")
    print("=" * 50)
    print("\nThis tool evaluates Dry Run metrics against acceptance criteria.")
    print("\nIn production mode, metrics would be fetched from:")
    print("  - Freqtrade API (http://127.0.0.1:8080/api/v1/)")
    print("  - Freqtrade logs")
    print("  - Database (trades.dryrun.db)")
    print("\nFor manual evaluation, use the evaluate_dryrun() function:")
    print("\n  from scripts.check_dryrun_criteria import DryRunMetrics, evaluate_dryrun")
    print("  metrics = DryRunMetrics(")
    print("      uptime_percent=99.5,")
    print("      api_error_rate=0.2,")
    print("      order_accuracy=100.0,")
    print("      sharpe_deviation=0.1,")
    print("      days_running=14,")
    print("  )")
    print("  result = evaluate_dryrun(metrics)")
    print("  print(result)")

    # Example evaluation
    print("\n" + "=" * 50)
    print("Example evaluation:")
    print("=" * 50)

    example_metrics = DryRunMetrics(
        uptime_percent=99.5,
        api_error_rate=0.2,
        order_accuracy=100.0,
        sharpe_deviation=0.1,
        days_running=14,
    )

    result = evaluate_dryrun(example_metrics)

    for detail in result.details:
        print(detail)

    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
