"""Daily report generation for Freqtrade DCA bot Dry Run monitoring."""

import sys
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class DailyMetrics:
    """Daily metrics collected from Freqtrade."""

    date: str
    uptime_percent: float
    total_trades: int
    daily_pnl: float
    cumulative_pnl: float
    open_positions: int
    api_errors: int
    api_total_calls: int


def format_daily_report(metrics: DailyMetrics) -> str:
    """Format daily metrics into a report string.

    Args:
        metrics: DailyMetrics to format

    Returns:
        Formatted report string

    """
    # Calculate API error rate
    if metrics.api_total_calls > 0:
        api_error_rate = (metrics.api_errors / metrics.api_total_calls) * 100
    else:
        api_error_rate = 0.0

    # Format P&L with sign and comma separators
    daily_pnl_str = f"{metrics.daily_pnl:+,.0f}"
    cumulative_pnl_str = f"{metrics.cumulative_pnl:+,.0f}"

    # Build report
    report_lines = [
        "=" * 60,
        f"Daily Report - {metrics.date}",
        "=" * 60,
        "",
        "UPTIME & STABILITY",
        f"  Uptime:           {metrics.uptime_percent:.1f}%",
        f"  API Error Rate:   {api_error_rate:.2f}% ({metrics.api_errors}/{metrics.api_total_calls} calls)",
        "",
        "TRADING ACTIVITY",
        f"  Total Trades:     {metrics.total_trades}",
        f"  Open Positions:   {metrics.open_positions}",
        "",
        "PROFIT & LOSS (JPY)",
        f"  Daily P&L:        {daily_pnl_str}",
        f"  Cumulative P&L:   {cumulative_pnl_str}",
        "",
        "=" * 60,
    ]

    return "\n".join(report_lines)


def main() -> int:
    """Main entry point for CLI usage.

    In production, this would fetch metrics from Freqtrade API or logs.
    For now, it's a placeholder for manual testing.

    """
    print("Daily Report Generator")
    print("=" * 60)
    print("\nThis tool generates daily reports for Dry Run monitoring.")
    print("\nIn production mode, metrics would be fetched from:")
    print("  - Freqtrade API (http://127.0.0.1:8080/api/v1/)")
    print("  - Freqtrade logs")
    print("  - Database (trades.dryrun.db)")
    print("\nFor manual report generation, use the format_daily_report() function:")
    print("\n  from scripts.daily_report import DailyMetrics, format_daily_report")
    print("  metrics = DailyMetrics(")
    print("      date='2026-01-30',")
    print("      uptime_percent=99.5,")
    print("      total_trades=5,")
    print("      daily_pnl=1500.0,")
    print("      cumulative_pnl=3000.0,")
    print("      open_positions=2,")
    print("      api_errors=1,")
    print("      api_total_calls=500,")
    print("  )")
    print("  report = format_daily_report(metrics)")
    print("  print(report)")

    # Example report
    print("\n" + "=" * 60)
    print("Example report:")
    print("=" * 60 + "\n")

    example_metrics = DailyMetrics(
        date=datetime.now().strftime("%Y-%m-%d"),
        uptime_percent=99.5,
        total_trades=5,
        daily_pnl=1500.0,
        cumulative_pnl=3000.0,
        open_positions=2,
        api_errors=1,
        api_total_calls=500,
    )

    report = format_daily_report(example_metrics)
    print(report)

    return 0


if __name__ == "__main__":
    sys.exit(main())
